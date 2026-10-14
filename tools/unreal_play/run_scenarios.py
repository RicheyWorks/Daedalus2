# SPDX-License-Identifier: MIT
"""Run Play scenarios through the Claude Unreal Bridge and print one line per check.

    python tools/unreal_play/run_scenarios.py cast realm_switch        (started by engines/unreal/pc-job.ps1 -Start)
    python tools/unreal_play/run_scenarios.py --all

Starts Play if it isn't running, runs each scenario to its end, prints PASS/FAIL lines and a TOTAL, stops Play
unless --keep. Exit 0 when every check passed. Lives in the repo so Norton sees a known file (ADR-045).
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

ALL = ("realm", "inventory", "dialogue", "cast", "realm_switch", "shiny", "shoot", "dig", "fall", "armor")


def main(argv):
    names = [a for a in argv if not a.startswith("--")]
    if "--all" in argv or not names:
        names = list(ALL[:5])
    keep = "--keep" in argv
    for _ in range(60):   # the editor may still be opening after a build
        try:
            wire.call(wire.UNREAL, "ping", timeout=10)
            break
        except Exception:
            time.sleep(5)
    st = wire.call(wire.UNREAL, "ping", timeout=10)
    if not st.get("playing"):
        print(wire.call(wire.UNREAL, "play", timeout=30), flush=True)
        time.sleep(16)
    ok = tot = 0
    for name in names:
        r0 = wire.call(wire.UNREAL, "daedalus.play_scenario", name=name, timeout=20)
        if r0.get("error"):
            print("%s error= %s" % (name, r0["error"]), flush=True)
            tot += 1
            continue
        s = {}
        for _ in range(180):
            time.sleep(1)
            s = wire.call(wire.UNREAL, "daedalus.play_status", timeout=20)
            if not s.get("running"):
                break
        r = s.get("result") or {}
        print("%s error= %s passed=%s/%s" % (name, s.get("error"), r.get("passed"), r.get("total")), flush=True)
        for c in r.get("checks", []):
            print("  %s %s :: %s" % ("PASS" if c["pass"] else "FAIL", c["check"], (c.get("detail") or "")[:260]), flush=True)
        tot += r.get("total") or 0
        ok += r.get("passed") or 0
        time.sleep(2)
    print("TOTAL %d/%d" % (ok, tot), flush=True)
    if not keep:
        print(wire.call(wire.UNREAL, "stop", timeout=30), flush=True)
    return 0 if ok == tot and tot > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
