# SPDX-License-Identifier: MIT
"""Cull distances + shadow trims on every district actor, then a 40 s Play to measure fps (play_status frames).

    python tools/unreal_play/perf_pass.py [--no-measure]
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def fps(seconds=10):
    a = wire.call(wire.UNREAL, "daedalus.play_status", timeout=20).get("frames") or 0
    time.sleep(seconds)
    b = wire.call(wire.UNREAL, "daedalus.play_status", timeout=20).get("frames") or 0
    return (b - a) / float(seconds)


def main(argv):
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "stop", timeout=60)
        time.sleep(3)
    code = ("import importlib, daedalus_plots, daedalus_districts\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from daedalus_districts.perf_steps())\n")
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="perf", timeout=1800)
    print("perf: steps=%s seconds=%s error=%s result=%s" % (r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:], r.get("result")), flush=True)
    out = "PERF cull/shadow pass: %s" % r.get("result")
    if "--no-measure" not in argv and not r.get("error"):
        wire.call(wire.UNREAL, "play", timeout=30)
        time.sleep(12)
        wire.call(wire.UNREAL, "daedalus.play_scenario", name="fall", timeout=20)   # any light scenario keeps frames counting
        time.sleep(8)
        f = fps(10)
        wire.call(wire.UNREAL, "stop", timeout=30)
        print("fps after pass: %.1f" % f, flush=True)
        out += "; PIE fps after = %.1f (was 6.2)" % f
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "pootscoot", "--type", "note", "--topic", "harness-needs", "--text", out],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 1 if r.get("error") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
