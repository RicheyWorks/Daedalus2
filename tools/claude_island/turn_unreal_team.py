# SPDX-License-Identifier: MIT
"""unreal-team's whole editor turn in one run, so a 10-minute slot proves everything that waited for the editor.

    python tools/claude_island/turn_unreal_team.py            # on Richey's PC, after posting CLAIM
    python tools/claude_island/turn_unreal_team.py --dry-run  # print the plan only
    python tools/claude_island/turn_unreal_team.py --light    # a short slot in the RUNNING editor: no build, no
                                                              # relaunch; RAM + audit + islands.json/.dsb + save

Steps (each one is timed and reported; a step that fails is recorded and the turn moves on unless it was the build):
  1. RAM before: free RAM and the editor's private bytes.
  2. Preflight (P1-P7). A failure stops here, and the editor is left as it was.
  3. Fast build from the clean worktree (..\\D2-build at origin/main) through unreal-job.ps1, then wait for the bridge.
     This compiles the merged-mesh isles, LODs, the island streamer, tactics (DTO/DTE/DTR) and the casualty roster.
  4. Re-place Claude Island and the Reach (merged meshes now) and write Saved/Daedalus/islands.json.
  5. RAM after: the same numbers, so ADR-064 gets its first real measurement. Then the RAM audit: texture and mesh
     sizes per owner folder from asset-registry tags (daedalus_ram_audit, read-only, loads nothing).
  6. Play scenarios: tactics, wild, orrery. Each is started and polled for up to 90 s.
  7. Astra's three-npc.dto (PR32) applied to a live squad through ApplyOrders, when the file is present.
  8. Stop Play, save only unreal-team's levels, write turn-report.json, post DONE + HANDOFF on the team link.
Nothing here deletes files or closes other programs.
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

REPORT = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "Daedalus", "jobs", "turn-report.json")
SCENARIOS = ["tactics", "tactics_remote", "wild", "orrery"]
PYDIR = os.path.join(REPO, "engines", "unreal", "DaedalusLink", "Content", "Python").replace("\\", "\\\\")
THREE_NPC = os.path.join(REPO, "docs", "benchmarks", "adaptive-initial", "three-npc.dto")

PLACE = r'''
import sys, types, importlib
for n in ("bpy", "bmesh"):
    sys.modules.setdefault(n, types.ModuleType(n))
for p in (r"%s", r"%s"):   # tools/claude_island (orr_*) and the plugin's Content/Python (daedalus_*), freshest first
    if p not in sys.path: sys.path.insert(0, p)
import orr_build, orr_place, orr_reach, daedalus_dsb, daedalus_islands
for m in (orr_build, orr_place, orr_reach, daedalus_dsb, daedalus_islands): importlib.reload(m)
result = {"place": str(orr_place.run())[:300], "reach": {k: v for k, v in orr_reach.run().items()},
          "islands": daedalus_islands.write()}
'''

AUDIT = r'''
import sys, importlib
p = r"%s"
if p not in sys.path: sys.path.insert(0, p)
import daedalus_ram_audit
importlib.reload(daedalus_ram_audit)
result = daedalus_ram_audit.run()
'''

ISLANDS = r'''
import sys, importlib
p = r"%s"
if p not in sys.path: sys.path.insert(0, p)
import daedalus_dsb, daedalus_islands
for m in (daedalus_dsb, daedalus_islands): importlib.reload(m)
r = daedalus_islands.write()
result = {"path": r["path"], "dsb": r.get("dsb"), "rows": [{k: v for k, v in x.items() if k != "package"} for x in r["rows"]][:20],
          "notes": r["notes"][:20]}
'''

APPLY_DTO = r'''
import unreal
w = unreal.EditorLevelLibrary.get_game_world()
tac = unreal.DaedalusTactics.get_tactics(w) if w else None
spec = %s
out = {"world": bool(w)}
if tac:
    foes = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DaedalusTarget)]
    ids = [l.split()[1] for l in spec.splitlines() if l.startswith("order ")]
    for f, uid in zip(foes, ids):
        f.set_editor_property("squad", spec.splitlines()[1].split()[1])
        f.set_editor_property("unit_id", uid)
    out.update(applied=tac.apply_orders(spec), roster=tac.take_roster(spec.splitlines()[1].split()[1])[:400],
               stats=tac.stats(), foes=len(foes))
result = out
'''


def ps(cmd, timeout=600):
    """Run PowerShell and return stdout (Windows only)."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()


def ram():
    """Free RAM (GB) and the editor's private bytes (GB), or Nones off Windows."""
    if os.name != "nt":
        return {"free_gb": None, "editor_private_gb": None}
    out = ps("[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2);"
             "$e=Get-Process UnrealEditor -ErrorAction SilentlyContinue | Select -First 1;"
             "if($e){[math]::Round($e.PrivateMemorySize64/1GB,2)}else{''}").splitlines()
    return {"free_gb": float(out[0]) if out and out[0] else None,
            "editor_private_gb": float(out[1]) if len(out) > 1 and out[1] else None}


class Turn:
    def __init__(self, call, run, ram_fn, link, now=time.time, sleep=time.sleep):
        self.call, self.run, self.ram, self.link, self.now, self.sleep = call, run, ram_fn, link, now, sleep
        self.steps = []

    def step(self, name, fn):
        t0 = self.now()
        try:
            out = {"ok": True, "result": fn()}
        except Exception as e:  # recorded, and the turn decides whether to go on
            out = {"ok": False, "error": repr(e)[:400]}
        out.update(step=name, seconds=round(self.now() - t0, 1))
        self.steps.append(out)
        return out

    def build(self, tries=8):
        """unreal-job.ps1 -Start -Fast from the clean worktree, then -Wait (50 s each) until BUILD OK or FAILED."""
        job = os.path.join(REPO, "..", "D2-build", "engines", "unreal", "unreal-job.ps1")
        self.run(["git", "-C", os.path.join(REPO, "..", "D2-build"), "fetch", "-q", "origin"])
        self.run(["git", "-C", os.path.join(REPO, "..", "D2-build"), "checkout", "-q", "--detach", "origin/main"])
        started = self.run(["powershell", "-NoProfile", "-File", job, "-Start", "-Fast"])
        m = re.search(r"(build-\d{4}-\d{6})", started or "")
        jid = ["-Id", m.group(1)] if m else []   # wait on THIS job: an older log's BUILD OK once let a turn run on early
        self.sleep(5)
        for _ in range(tries):
            out = self.run(["powershell", "-NoProfile", "-File", job, "-Wait"] + jid)
            if "BUILD FAILED" in out:
                raise RuntimeError(out[-600:])
            if "BUILD OK" in out:
                return {"started": started.strip()[-80:], "result": "BUILD OK"}
        raise RuntimeError("build still running after %d waits" % tries)

    def scenario(self, name, limit=90):
        self.call("play", timeout=120)
        self.call("daedalus.play_scenario", name=name)
        t0 = self.now()
        status = {}
        while self.now() - t0 < limit:
            status = self.call("daedalus.play_status") or {}
            if not status.get("running"):
                break
            self.sleep(2)
        self.call("stop")
        res = (status or {}).get("result") or {}
        return {"passed": res.get("passed"), "total": res.get("total"), "error": status.get("error"),
                "failed": [c["check"] for c in res.get("checks", []) if not c.get("pass")]}

    def light(self):
        """A short turn that needs no C++ build, so the running editor is never closed: measure RAM, audit what holds
        it (registry tags only), write islands.json + islands.dsb, save, hand off."""
        before = self.step("ram", self.ram)
        pre = self.step("preflight", lambda: self.run([sys.executable, os.path.join(REPO, "tools", "unreal_preflight", "preflight.py")]))
        if not pre["ok"]:
            return self.finish("preflight failed; the editor was not touched")
        self.step("bridge up", lambda: self.call("ping", timeout=60))
        py = os.path.join(REPO, "engines", "unreal", "DaedalusLink", "Content", "Python").replace("\\", "\\\\")
        self.step("ram audit (registry tags, nothing loaded)", lambda: self.call(
            "execute_python", code=AUDIT % py, unattended=False, bridge_timeout=300))
        self.step("islands.json + islands.dsb", lambda: self.call("execute_python", code=ISLANDS % py, unattended=False,
                                                                   bridge_timeout=120))
        self.step("save", lambda: self.call("save"))
        return self.finish(None, before.get("result"), before.get("result"))

    def after_build(self):
        """The turn from 'bridge up' on, for when the build already ran (or ran outside this script)."""
        before = self.step("ram before", self.ram)
        self.step("bridge up", lambda: self.call("ping", timeout=180))
        self.step("place isles + islands.json", lambda: self.call("execute_python", code=PLACE % (PYDIR, HERE.replace("\\", "\\\\")),
                                                                  unattended=False, bridge_timeout=300))
        after = self.step("ram after", self.ram)
        self.step("ram audit (registry tags, nothing loaded)", lambda: self.call(
            "execute_python", code=AUDIT % PYDIR, unattended=False, bridge_timeout=300))
        for s in SCENARIOS:
            self.step("scenario " + s, lambda s=s: self.scenario(s))
        self.step("save", lambda: self.call("save"))
        return self.finish(None, before.get("result"), after.get("result"))

    def go(self, dry=False, light=False, after_build=False):
        if after_build and not dry:
            return self.after_build()
        plan = ["ram", "preflight", "build", "place", "ram", "ram audit", "scenarios: " + ", ".join(SCENARIOS), "three-npc", "save", "post"]
        if light:
            plan = ["ram", "preflight", "ram audit", "islands.json + islands.dsb", "save", "post"]
        if dry:
            return {"plan": plan}
        if light:
            return self.light()
        before = self.step("ram before", self.ram)
        pre = self.step("preflight", lambda: self.run([sys.executable, os.path.join(REPO, "tools", "unreal_preflight", "preflight.py")]))
        if not pre["ok"]:
            return self.finish("preflight failed; the editor was not touched")
        build = self.step("build", self.build)
        if not build["ok"]:
            return self.finish("build failed")
        self.step("bridge up", lambda: self.call("ping", timeout=180))
        self.step("place isles + islands.json", lambda: self.call("execute_python", code=PLACE % (PYDIR, HERE.replace("\\", "\\\\")),
                                                                  unattended=False, bridge_timeout=300))
        after = self.step("ram after", self.ram)
        self.step("ram audit (registry tags, nothing loaded)", lambda: self.call(
            "execute_python", code=AUDIT % os.path.join(REPO, "engines", "unreal", "DaedalusLink", "Content", "Python").replace("\\", "\\\\"),
            unattended=False, bridge_timeout=300))
        for s in SCENARIOS:
            self.step("scenario " + s, lambda s=s: self.scenario(s))
        if os.path.exists(THREE_NPC):
            spec = open(THREE_NPC, encoding="utf-8").read()
            self.step("three-npc.dto", lambda: (self.call("play", timeout=120),
                                                self.call("execute_python", code=APPLY_DTO % json.dumps(spec), unattended=False),
                                                self.call("stop"))[1])
        self.step("save", lambda: self.call("save"))
        return self.finish(None, before.get("result"), after.get("result"))

    def finish(self, stop_reason, before=None, after=None):
        report = {"stopped": stop_reason, "ram_before": before, "ram_after": after, "steps": self.steps}
        ok = sum(1 for s in self.steps if s["ok"])
        text = ("TURN DONE unreal-team: %d/%d steps ok%s. RAM before %s, after %s. Report: turn-report.json"
                % (ok, len(self.steps), "" if not stop_reason else " (stopped: %s)" % stop_reason, before, after))
        self.link(text)
        self.link("HANDOFF -> next in the referee's order from unreal-team. Editor is free, Play stopped.")
        return report


def main(argv):
    from asset_pipeline import wire
    dry = "--dry-run" in argv
    light = "--light" in argv
    after_build = "--after-build" in argv

    def call(kind, timeout=600, **params):
        return wire.call(wire.UNREAL, kind, timeout=timeout, side="Unreal", **params)

    def run(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise RuntimeError((r.stdout + r.stderr)[-600:])
        return r.stdout[-400:]

    def link(text):
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--me", "unreal-team", "--to", "*",
                        "--type", "note", "--text", text], cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))

    report = Turn(call, run, ram, link).go(dry, light, after_build)
    if not dry:
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
