# SPDX-License-Identifier: MIT
"""Offline test of turn_unreal_team.py with a fake bridge, shell and team link: the order of steps, a failed
preflight stopping before the editor is touched, a failed build stopping before placing, scenarios polled to the end."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import turn_unreal_team as T  # noqa: E402

ok = total = 0


def check(name, cond, detail=""):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("ok    " if cond else "FAIL  ") + name + ("" if cond else "  " + str(detail)))


class Fake:
    def __init__(self, fail_run=None, polls=2):
        self.calls, self.runs, self.links, self.t, self.polls, self.fail_run = [], [], [], 0.0, polls, fail_run

    def call(self, kind, timeout=600, **p):
        self.calls.append(kind)
        if kind == "daedalus.play_status":
            self.polls -= 1
            if self.polls > 0:
                return {"running": True}
            self.polls = 2
            return {"running": False, "result": {"passed": 9, "total": 9, "checks": [{"check": "x", "pass": True}]}}
        return {"ok": True}

    def run(self, cmd):
        self.runs.append(" ".join(cmd))
        if self.fail_run and self.fail_run in " ".join(cmd):
            raise RuntimeError("boom " + self.fail_run)
        return "BUILD OK" if "-Wait" in cmd else "fine"

    def now(self):
        self.t += 1.0
        return self.t


def turn(f):
    return T.Turn(f.call, f.run, lambda: {"free_gb": 5.0, "editor_private_gb": 9.0}, f.links.append, now=f.now, sleep=lambda s: None)


f = Fake()
r = turn(f).go()
names = [s["step"] for s in r["steps"]]
check("all steps run in order", names[:5] == ["ram before", "preflight", "build", "bridge up", "place isles + islands.json"], names)
check("every scenario played, polled until done and stopped",
      [n for n in names if n.startswith("scenario")] == ["scenario " + s for s in T.SCENARIOS]
      and f.calls.count("daedalus.play_scenario") == len(T.SCENARIOS) and f.calls.count("stop") >= len(T.SCENARIOS), f.calls)
check("scenario results carry passed/total", [s for s in r["steps"] if s["step"] == "scenario tactics"][0]["result"]["passed"] == 9)
check("saves and posts DONE + HANDOFF", "save" in f.calls and f.links[0].startswith("TURN DONE") and f.links[1].startswith("HANDOFF"), f.links)
check("the build waits for BUILD OK from the clean worktree", any("D2-build" in x and "-Start" in x for x in f.runs)
      and any("checkout -q --detach origin/main" in x for x in f.runs), f.runs)

f = Fake()
r = turn(f).go(light=True)
names = [s["step"] for s in r["steps"]]
check("a light turn never builds, plays or relaunches", "build" not in names and not any(n.startswith("scenario") for n in names)
      and not any("unreal-job" in x for x in f.runs) and "play" not in f.calls and "save" in f.calls, (names, f.calls))
check("a light turn audits RAM and writes islands.json/.dsb", "ram audit (registry tags, nothing loaded)" in names
      and "islands.json + islands.dsb" in names and f.links[0].startswith("TURN DONE"), names)

f = Fake(fail_run="preflight.py")
r = turn(f).go()
check("a failed preflight stops before the editor is touched", r["stopped"].startswith("preflight") and f.calls == [], f.calls)
check("...and still posts the result", f.links and "stopped: preflight" in f.links[0], f.links)

f = Fake(fail_run="-Start")
r = turn(f).go()
check("a failed build stops before placing anything", r["stopped"] == "build failed" and "execute_python" not in f.calls, f.calls)

check("dry run only plans", T.Turn(None, None, None, None).go(dry=True)["plan"][0] == "ram")
print("%d/%d" % (ok, total))
sys.exit(0 if ok == total else 1)
