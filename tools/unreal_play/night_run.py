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
Stops at the first failed step and preserves evidence. Reconcile unknown native outcomes before rerunning.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402
from asset_pipeline.ship import write_report  # noqa: E402

LIVE = r"C:\Unreal\DaedalusRealm\Plugins\DaedalusLink\Content"
PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def say(msg):
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def ps(cmd, timeout=600):
    r = subprocess.run(PS + ["$ErrorActionPreference = 'Stop'; " + cmd], capture_output=True, text=True, timeout=timeout, cwd=REPO)
    output = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        raise RuntimeError('PowerShell step exited %d: %s' % (r.returncode, output[-2000:]))
    return output


def hub(kind, text, topic="night-run"):
    try:
        out = subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", kind, "--topic", topic, "--text", text],
                             capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
        return out.stdout.strip()[-40:]
    except Exception as e:  # the hub is never load-bearing
        return "hub: %s" % e


def jobs_directory():
    base = os.environ.get('LOCALAPPDATA')
    if not base:
        raise RuntimeError('LOCALAPPDATA unavailable; cannot identify local job markers')
    return Path(base)/'Daedalus'/'jobs'


def wait_terminal(job_id, max_s=7200, directory=None):
    if not re.fullmatch(r'(?:job|build)-[A-Za-z0-9-]+', job_id):
        raise ValueError('Unsafe job ID')
    marker = (directory or jobs_directory())/(job_id+'.exit')
    deadline = time.monotonic()+max_s
    while True:
        try:
            value = marker.read_text(encoding='utf-8-sig').strip()
        except FileNotFoundError:
            value = None
        if value is not None:
            match = re.fullmatch(r'done (-?\d+)', value, flags=re.IGNORECASE)
            if not match:
                raise RuntimeError('Invalid terminal marker for '+job_id)
            return int(match.group(1))
        if time.monotonic() >= deadline:
            raise TimeoutError('Job still lacks terminal marker: '+job_id)
        time.sleep(min(3, max(0, deadline-time.monotonic())))


def wait_job(job_id, max_s=7200):
    return 'DONE %d' % wait_terminal(job_id, max_s)


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
    if not isinstance(r,dict) or r.get('error') or r.get('stderr'):
        raise RuntimeError('Content reload failed; no layout or Play will follow')
    output = (r.get('stdout') or '').strip()
    if 'reloaded' not in output.splitlines():
        raise RuntimeError('Content reload completion marker missing; no layout or Play will follow')
    return output[-200:]


def steps(expr, label, timeout=3600):
    code = "def steps():\n    return (yield from %s)\n" % expr
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, timeout=timeout)
    return r


def require_stage(reply, label):
    if (not isinstance(reply, dict) or 'error' not in reply or reply['error'] is not None or
            not isinstance(reply.get('result'), dict) or not reply['result']):
        raise RuntimeError(label+' lacks a successful terminal stage result; no subsequent mutation')
    return reply['result']


def require_import_receipt(path,folder,expected):
    from handoff_status import read,cast_summary
    value=read(Path(path))
    summary=cast_summary(Path(path),value)
    if summary['recorded_state']!='completed' or summary['counts']['failed'] or summary['reconciliation_required']:
        raise RuntimeError('Import receipt is not a complete successful terminal record')
    planned=[{'id':row['id'],'sha256':row['sha256']} for row in expected['assets']]
    if value.get('planned')!=planned or value.get('folder')!=os.path.abspath(folder) or value.get('root')!='/Game/Daedalus/Art/Cast':
        raise RuntimeError('Import receipt differs from the preflighted handoff')
    return summary


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


def publish_receipt(receipt,out_dir,latest_path):
    """Use the existing atomic report writer; archive first, then update latest."""
    os.makedirs(out_dir,exist_ok=True)
    receipt=dict(receipt,run_id=uuid.uuid4().hex)
    path=os.path.join(out_dir,'night-run-%s-%s.json' % (time.strftime('%m%d-%H%M%S'),receipt['run_id']))
    write_report(path,receipt)
    write_report(latest_path,receipt)
    return path


def checkpoint_run(progress,phase,**values):
    progress.update(values,phase=phase,updated=time.strftime('%Y-%m-%dT%H:%M:%S'))
    write_report(progress['_checkpoint_path'],{key:value for key,value in progress.items() if not key.startswith('_')})


def parse_options(argv):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after-job',default='')
    parser.add_argument('--no-build',action='store_true')
    parser.add_argument('--realms',default='GALLERY-CITY,PARCELS,BRICKS,LABYRINTH')
    parser.add_argument('--import',dest='imports',nargs='+',action='append',default=[])
    args=parser.parse_args(argv)
    args.realms=args.realms.split(',')
    allowed={'GALLERY-CITY','PARCELS','BRICKS','LABYRINTH'}
    if not args.realms or len(set(args.realms))!=len(args.realms) or not set(args.realms)<=allowed:
        parser.error('--realms requires unique supported district realms')
    if args.after_job and not re.fullmatch(r'job-[A-Za-z0-9-]+',args.after_job):
        parser.error('invalid dependency job ID')
    args.imports=[folder for group in args.imports for folder in group]
    if len(args.imports)>8 or len(set(os.path.normcase(os.path.abspath(p)) for p in args.imports))!=len(args.imports):
        parser.error('at most8 distinct import folders allowed; none are silently dropped')
    if any(not os.path.isdir(folder) for folder in args.imports):
        parser.error('every import folder must exist before any build is started')
    if args.imports:
        from import_cast import IC,preflight
        args.import_plans={}
        for folder in args.imports:
            try:args.import_plans[os.path.abspath(folder)]=preflight(IC.plan(folder),IC.CAST_ROOT)
            except (OSError,ValueError,TypeError) as error:
                parser.error('import preflight failed before build: '+str(error))
    return args


def run_options(options,progress):
    after=options.after_job
    build=not options.no_build
    realms=options.realms
    sha = ps("git rev-parse --short HEAD", 30).strip()
    checkpoint_run(progress,'preflight',sha=sha)
    hub("status", "NIGHT RUN start on %s: after=%s build=%s realms=%s" % (sha, after or "-", build, ",".join(realms)))

    if after:
        checkpoint_run(progress,'dependency',dependency_job=after)
        say("waiting for job %s" % after)
        try:
            out = wait_job(after)
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            hub('status', 'NIGHT RUN stopped observing %s: %s; no build or restart' % (after, exc))
            return 1
        say("job %s: %s" % (after, out.splitlines()[0] if out else out))
        if out != "DONE 0":
            hub("status", "NIGHT RUN stopped: job %s ended '%s'" % (after, out[:120]))
            return 1

    if build:
        checkpoint_run(progress,'build')
        say("building")
        directory = jobs_directory()
        previous = {path.stem for path in directory.glob('build-*')}
        out = ps(r".\engines\unreal\unreal-job.ps1 -Start -Fast", 120)
        launch = re.findall(r'^started (build-[A-Za-z0-9-]+) pid=([1-9]\d*)\s*$', out, re.MULTILINE)
        if len(launch) != 1 or launch[0][0] in previous:
            hub('status', 'NIGHT RUN stopped: missing, ambiguous or reused build job identity')
            return 1
        job = launch[0][0]
        checkpoint_run(progress,'build-wait',build_job=job,build_pid=int(launch[0][1]))
        say(job)
        try:
            code = wait_terminal(job, 1800, directory)
        except (OSError, RuntimeError, TimeoutError) as exc:
            hub('status', 'NIGHT RUN stopped observing %s: %s; no restart' % (job, exc))
            return 1
        res = ps(r".\engines\unreal\unreal-job.ps1 -Wait -Id %s -Seconds 0" % job, 120)
        if code != 0 or not re.search(r'^BUILD OK '+re.escape(job)+r'\s*$', res, re.MULTILINE):
            hub("status", "NIGHT RUN stopped: build %s code=%d: %s" % (job, code, res.strip()[-300:]))
            print(res[-2000:])
            return 1
        say("build ok")
    sha = ps("git rev-parse --short HEAD", 30).strip()
    progress['sha']=sha

    say("waiting for the bridge")
    checkpoint_run(progress,'bridge-observation')
    st = bridge_up()
    if not st:
        hub("status", "NIGHT RUN stopped: bridge not up after the build")
        return 1
    try:
        checkpoint_run(progress,'content-sync')
        say("bridge up: " + hot_copy())
    except Exception as error:
        hub('status','NIGHT RUN stopped during content copy/reload: %s; no layout or Play' % error)
        return 1

    # lay what is new: first any cast folders waiting for import (one GLB per tick), then the cast, portals, districts
    lay = []
    progress['laid']=lay
    folders = options.imports
    for folder in folders:
        import_receipt=os.path.join(os.path.dirname(progress['_checkpoint_path']),'cast-import-'+uuid.uuid4().hex+'.json')
        pinned_plan=import_receipt+'.plan.json'
        write_report(pinned_plan,options.import_plans[os.path.abspath(folder)])
        progress.setdefault('import_receipts',[]).append(import_receipt)
        checkpoint_run(progress,'import',import_folder=folder,import_receipt=import_receipt,import_expected_plan=pinned_plan)
        out = subprocess.run([sys.executable, os.path.join(HERE, "import_cast.py"), folder,'--report',import_receipt,'--expected-plan',pinned_plan], capture_output=True, text=True, timeout=1800, cwd=REPO)
        last = [l for l in (out.stdout or "").splitlines() if l.startswith("import:")]
        lay.append("import %s: %s" % (os.path.basename(os.path.dirname(folder)), last[-1] if last else (out.stderr or "")[-200:]))
        terminal = re.fullmatch(r'import: (\d+) imported, (\d+) skipped, (\d+) failed',last[-1] if last else '')
        if out.returncode != 0 or not terminal or int(terminal[3]) != 0 or sum(map(int,terminal.groups())) == 0:
            hub('status','NIGHT RUN stopped at import %s: code=%s; %s; no retry' % (folder,out.returncode,lay[-1]))
            return 1
        try:
            accepted=require_import_receipt(import_receipt,folder,options.import_plans[os.path.abspath(folder)])
            if [accepted['counts'][key] for key in ('imported','skipped','failed')]!=list(map(int,terminal.groups())):
                raise RuntimeError('Import stdout differs from retained terminal receipt')
        except (OSError,ValueError,RuntimeError,TypeError,KeyError) as error:
            hub('status','NIGHT RUN stopped: import receipt unavailable/inconsistent: %s; no layout or Play' % error)
            return 2
    try:
        checkpoint_run(progress,'cast')
        r = steps("__import__('daedalus_realm_ground').lay_cast_steps(['WORLD-ZERO'] + %r)" % realms, "lay_cast")
        result = require_stage(r,'cast')
        lay.append('cast: '+str(result))
        if not set(['WORLD-ZERO']+realms)<=set(result):
            raise RuntimeError('cast omitted a requested realm')
        if any(not isinstance(row,dict) or not isinstance(row.get('unbound'),list) or row['unbound'] or
               type(row.get('roles')) is not int or row['roles'] <= 0 or
               type(row.get('bound')) is not int or row['bound'] != row['roles'] for row in result.values()):
            raise RuntimeError('cast contains unbound or unavailable script roles')
        checkpoint_run(progress,'portals')
        r = steps("__import__('daedalus_realm_ground').lay_portals_steps(['WORLD-ZERO'] + %r)" % realms, "lay_portals")
        lay.append('portals: '+str(require_stage(r,'portals')))
        for realm in realms:
            checkpoint_run(progress,'districts',district_realm=realm)
            r = steps("__import__('daedalus_districts').steps(%r)" % realm, "districts " + realm)
            lay.append('districts %s: %s' % (realm,require_stage(r,'districts '+realm)))
    except Exception as error:
        hub('status','NIGHT RUN stopped during layout: %s; no next mutation or Play' % error)
        return 1
    for line in lay:
        say(line)
    hub("status", "NIGHT RUN laid on %s: %s" % (sha, " | ".join(lay)))

    say("play suite")
    checkpoint_run(progress,'play-scenarios')
    out = subprocess.run([sys.executable, os.path.join(HERE, "run_scenarios.py"), "realm_switch", "realm_ground", "realm_host", "mounts", "portals", "bestiary", "cast", "control"],
                         capture_output=True, text=True, timeout=1800, cwd=REPO)
    text = (out.stdout or "") + (out.stderr or "")
    print(text[-6000:])
    total = next((l for l in reversed(text.splitlines()) if l.startswith("TOTAL")), "TOTAL ?")
    fails = [l.strip() for l in text.splitlines() if l.strip().startswith("FAIL")]
    rep = None
    checkpoint_run(progress,'log-report')
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
    receipt['import_receipts']=progress.get('import_receipts',[])
    receipt['checkpoint_run_id']=progress['run_id']
    out_dir = os.path.join(os.environ.get("LOCALAPPDATA", REPO), "Daedalus", "jobs")
    try:
        path=publish_receipt(receipt,out_dir,os.path.join(REPO,'docs','production','night-run-latest.json'))
        say("receipt " + path)
        checkpoint_run(progress,'completed',outcome=outcome,terminal_receipt=path,total=total)
        progress['_terminal_published']=True
    except OSError as e:
        say("receipt not written: %s" % e)
        hub('status','NIGHT RUN receipt publication failed on %s: %s; result evidence incomplete' % (sha,e))
        return outcome['exit_code'] or 2
    return outcome['exit_code']


def main(argv):
    options=parse_options(argv)
    run_id=uuid.uuid4().hex
    out_dir=os.path.join(os.environ.get('LOCALAPPDATA',REPO),'Daedalus','jobs')
    progress={'run_id':run_id,'when':time.strftime('%Y-%m-%dT%H:%M:%S'),'sha':None,
              'build':not options.no_build,'realms':options.realms,'laid':[],'scenarios':{},
              'total':'TOTAL ?','log_report':'unavailable','fails':[],'interrupted':[],
              'outcome':{'status':'running','passed':False},
              '_checkpoint_path':os.path.join(out_dir,'night-progress-'+run_id+'.json')}
    try:
        checkpoint_run(progress,'starting')
        code=run_options(options,progress)
    except Exception as error:
        code=2
        progress['stopped_error']={'type':type(error).__name__,'message':str(error)[-2000:]}
        hub('status','NIGHT RUN stopped during %s: %s; no automatic restart' % (progress.get('phase'),error))
    if not progress.get('_terminal_published'):
        progress['stopped_phase']=progress.get('phase')
        outcome={'status':'failed' if code==1 else 'unverified','passed':False,'exit_code':code or 2}
        try:
            checkpoint_run(progress,'stopped',outcome=outcome)
            receipt={key:value for key,value in progress.items() if not key.startswith('_')}
            publish_receipt(receipt,out_dir,os.path.join(REPO,'docs','production','night-run-latest.json'))
        except OSError as error:
            say('partial receipt unavailable: '+str(error))
        return code or 2
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
