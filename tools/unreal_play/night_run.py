# SPDX-License-Identifier: MIT
"""The editor turn, unattended (Richey 2026-10-13: "full permissions to automate and streamline production").

    python tools/unreal_play/night_run.py [--after-job <pc-job id>] [--no-build] [--realms GALLERY-CITY,PARCELS,...]

Runs, in order, with every step's result on the hub and in the job log:
  1. wait for a running pc-job (the materials run) to print DONE;
  2. unreal-job.ps1 -Start -Fast (pull main, build the plugin, reopen the editor) and wait for the bridge;
  3. hot-copy Content/Python + Casts + Inventory from D2-build into the live plugin, reload, re-register;
  4. lay what is new: World Zero cast, portals in every realm (daedalus.steps);
  5. district sublevels for the four realms (daedalus_districts.steps) and islands.json;
  6. the Play suite: realm_switch realm_ground realm_host mounts portals cast control;
  7. one hub status with sha, n/m, errors=/warnings=.
Stops at the first failed step and says which. Everything it runs is idempotent, so a rerun resumes.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

LIVE = r"C:\Unreal\DaedalusRealm\Plugins\DaedalusLink\Content"
PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def say(msg):
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def ps(cmd, timeout=600):
    r = subprocess.run(PS + [cmd], capture_output=True, text=True, timeout=timeout, cwd=REPO)
    return (r.stdout or "") + (r.stderr or "")


def hub(kind, text, topic="night-run"):
    try:
        out = subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", kind, "--topic", topic, "--text", text],
                             capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
        return out.stdout.strip()[-40:]
    except Exception as e:  # the hub is never load-bearing
        return "hub: %s" % e


def wait_job(job_id, max_s=7200):
    t0 = time.time()
    while time.time() - t0 < max_s:
        out = ps(r".\engines\unreal\pc-job.ps1 -Wait -Id %s -Seconds 50 -Lines 2" % job_id, 120)
        if "DONE" in out or "FAIL" in out:
            return out.strip()[-300:]
    return "timeout"


def bridge_up(max_s=600):
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            st = wire.call(wire.UNREAL, "ping", timeout=10)
            if st:
                return st
        except Exception:
            time.sleep(5)
    return None


def hot_copy():
    cmds = [
        r"Copy-Item engines\unreal\DaedalusLink\Content\Python\*.py '%s\Python\' -Force" % LIVE,
        r"Copy-Item engines\unreal\DaedalusLink\Content\Casts\*.dcs '%s\Casts\' -Force" % LIVE,
        r"Copy-Item engines\unreal\DaedalusLink\Content\Inventory\*.dic '%s\Inventory\' -Force" % LIVE,
    ]
    for c in cmds:
        ps(c, 60)
    code = ("import sys, importlib, os\n"
            "live = r'%s\\Python'\n"
            "sys.path[:] = [p for p in sys.path if 'Documents' not in p or 'Codex' not in p]\n"
            "if live not in sys.path: sys.path.insert(0, live)\n"
            "for m in [m for m in list(sys.modules) if m.startswith('daedalus_') and os.path.exists(os.path.join(live, m + '.py'))]:\n"
            "    importlib.reload(sys.modules[m])\n"
            "import daedalus_bridge_commands as B\nB.install()\nprint('reloaded')\n") % LIVE
    r = wire.call(wire.UNREAL, "execute_python", code=code, timeout=120)
    return (r.get("stdout") or "").strip()[-200:]


def steps(expr, label, timeout=3600):
    code = "def steps():\n    return (yield from %s)\n" % expr
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, timeout=timeout)
    return r


def require_stage(reply, label):
    if (not isinstance(reply, dict) or 'error' not in reply or reply['error'] is not None or
            not isinstance(reply.get('result'), dict) or not reply['result']):
        raise RuntimeError(label+' lacks a successful terminal stage result; no subsequent mutation')
    return reply['result']


def assess_run(text, returncode, report):
    """A missing summary/log observation is unverified, never an empty successful run."""
    totals = re.findall(r'^TOTAL (\d+)/(\d+)\s*$', text, re.MULTILINE)
    counts = None
    if len(totals) == 1:
        passed, total = map(int, totals[0])
        if 0 <= passed <= total and total > 0:
            counts = {'passed': passed, 'total': total}
    failures = [line.strip() for line in text.splitlines() if line.strip().startswith('FAIL')]
    interrupted = [line.strip() for line in text.splitlines() if 'INTERRUPTED' in line]
    log_valid = isinstance(report, dict) and all(type(report.get(key)) is int and report[key] >= 0
                                               for key in ('errors', 'warnings'))
    reasons = []
    if returncode != 0: reasons.append('scenario-process-exit:'+str(returncode))
    if failures: reasons.append('scenario-failures')
    if interrupted: reasons.append('scenario-interrupted')
    if counts and counts['passed'] != counts['total']: reasons.append('scenario-count-failed')
    if log_valid and report['errors']: reasons.append('editor-errors')
    known_failure = bool(reasons)
    if counts is None: reasons.append('missing-or-invalid-total')
    if not log_valid: reasons.append('log-report-unavailable-or-invalid')
    status = 'failed' if known_failure else 'unverified' if reasons else 'passed'
    return {'status': status, 'passed': status == 'passed', 'exit_code': 0 if status == 'passed' else 1 if known_failure else 2,
            'scenario_returncode': returncode, 'counts': counts, 'reasons': reasons,
            'editor_errors': report['errors'] if log_valid else None,
            'editor_warnings': report['warnings'] if log_valid else None}


def main(argv):
    after = argv[argv.index("--after-job") + 1] if "--after-job" in argv else ""
    build = "--no-build" not in argv
    realms = (argv[argv.index("--realms") + 1] if "--realms" in argv else "GALLERY-CITY,PARCELS,BRICKS,LABYRINTH").split(",")
    sha = ps("git rev-parse --short HEAD", 30).strip()
    hub("status", "NIGHT RUN start on %s: after=%s build=%s realms=%s" % (sha, after or "-", build, ",".join(realms)))

    if after:
        say("waiting for job %s" % after)
        out = wait_job(after)
        say("job %s: %s" % (after, out.splitlines()[0] if out else out))
        if "DONE 0" not in out:
            hub("status", "NIGHT RUN stopped: job %s ended '%s'" % (after, out[:120]))
            return 1

    if build:
        say("building")
        out = ps(r".\engines\unreal\unreal-job.ps1 -Start -Fast", 120)
        job = out.strip().splitlines()[-1] if out.strip() else "?"
        say(job)
        t0 = time.time()
        res = ""
        while time.time() - t0 < 1800:
            res = ps(r".\engines\unreal\unreal-job.ps1 -Wait", 120)
            if "BUILD OK" in res or "BUILD FAILED" in res:
                break
        if "BUILD OK" not in res:
            hub("status", "NIGHT RUN stopped: build on %s failed: %s" % (sha, res.strip()[-300:]))
            print(res[-2000:])
            return 1
        say("build ok")
    sha = ps("git rev-parse --short HEAD", 30).strip()

    say("waiting for the bridge")
    st = bridge_up()
    if not st:
        hub("status", "NIGHT RUN stopped: bridge not up after the build")
        return 1
    say("bridge up: " + hot_copy())

    # lay what is new: first any cast folders waiting for import (one GLB per tick), then the cast, portals, districts
    lay = []
    folders = [a for a in argv[argv.index("--import") + 1:] if not a.startswith("--")][:8] if "--import" in argv else []
    for folder in folders:
        out = subprocess.run([sys.executable, os.path.join(HERE, "import_cast.py"), folder], capture_output=True, text=True, timeout=1800, cwd=REPO)
        last = [l for l in (out.stdout or "").splitlines() if l.startswith("import:")]
        lay.append("import %s: %s" % (os.path.basename(os.path.dirname(folder)), last[-1] if last else (out.stderr or "")[-200:]))
        terminal = re.fullmatch(r'import: (\d+) imported, (\d+) skipped, (\d+) failed',last[-1] if last else '')
        if out.returncode != 0 or not terminal or int(terminal[3]) != 0 or sum(map(int,terminal.groups())) == 0:
            hub('status','NIGHT RUN stopped at import %s: code=%s; %s; no retry' % (folder,out.returncode,lay[-1]))
            return 1
    try:
        r = steps("__import__('daedalus_realm_ground').lay_cast_steps(['WORLD-ZERO'] + %r)" % realms, "lay_cast")
        result = require_stage(r,'cast')
        lay.append('cast: '+str(result))
        if not set(['WORLD-ZERO']+realms)<=set(result):
            raise RuntimeError('cast omitted a requested realm')
        if any(not isinstance(row,dict) or not isinstance(row.get('unbound'),list) or row['unbound'] or
               type(row.get('roles')) is not int or row['roles'] <= 0 or
               type(row.get('bound')) is not int or row['bound'] != row['roles'] for row in result.values()):
            raise RuntimeError('cast contains unbound or unavailable script roles')
        r = steps("__import__('daedalus_realm_ground').lay_portals_steps(['WORLD-ZERO'] + %r)" % realms, "lay_portals")
        lay.append('portals: '+str(require_stage(r,'portals')))
        for realm in realms:
            r = steps("__import__('daedalus_districts').steps(%r)" % realm, "districts " + realm)
            lay.append('districts %s: %s' % (realm,require_stage(r,'districts '+realm)))
    except Exception as error:
        hub('status','NIGHT RUN stopped during layout: %s; no next mutation or Play' % error)
        return 1
    for line in lay:
        say(line)
    hub("status", "NIGHT RUN laid on %s: %s" % (sha, " | ".join(lay)))

    say("play suite")
    out = subprocess.run([sys.executable, os.path.join(HERE, "run_scenarios.py"), "realm_switch", "realm_ground", "realm_host", "mounts", "portals", "bestiary", "cast", "control"],
                         capture_output=True, text=True, timeout=1800, cwd=REPO)
    text = (out.stdout or "") + (out.stderr or "")
    print(text[-6000:])
    total = next((l for l in reversed(text.splitlines()) if l.startswith("TOTAL")), "TOTAL ?")
    fails = [l.strip() for l in text.splitlines() if l.strip().startswith("FAIL")]
    rep = None
    try:
        rep = wire.call(wire.UNREAL, "daedalus.log_report", all=False, timeout=60)
        ew = "errors=%s warnings=%s" % (rep.get("errors"), rep.get("warnings"))
    except Exception as e:
        ew = "log_report: %s" % e
    outcome = assess_run(text, out.returncode, rep)
    hub("status", "NIGHT RUN end on %s: status=%s %s %s; fails: %s" % (sha, outcome['status'], total, ew, "; ".join(fails)[:900] or "none"))
    say("%s %s" % (total, ew))
    # J: a machine-readable receipt beside the job log (BASE-LAYER's "Laid down" table is regenerated from these)
    interrupted = [l.strip() for l in text.splitlines() if "INTERRUPTED" in l]
    per = {}
    for l in text.splitlines():
        if " passed=" in l and " error=" in l:
            name = l.split()[0]
            per[name] = l.split("passed=")[1].strip()
    receipt = {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "sha": sha, "build": build, "laid": lay, "scenarios": per,
               "total": total, "log_report": ew, "fails": fails, "interrupted": interrupted}
    receipt['outcome'] = outcome
    out_dir = os.path.join(os.environ.get("LOCALAPPDATA", REPO), "Daedalus", "jobs")
    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "night-run-%s.json" % time.strftime("%m%d-%H%M%S"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=1)
        with open(os.path.join(REPO, "docs", "production", "night-run-latest.json"), "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=1)
        say("receipt " + path)
    except OSError as e:
        say("receipt not written: %s" % e)
    return outcome['exit_code']


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
