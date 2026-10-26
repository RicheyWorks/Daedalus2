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

MAX_WAIT_S = int(os.environ.get("DAEDALUS_SCENARIO_WAIT_S", "900"))

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

ALL = ("realm", "inventory", "dialogue", "cast", "realm_switch", "control", "shiny", "shoot", "dig", "fall", "armor")


def main(argv):
    names = [a for a in argv if not a.startswith("--")]
    if "--all" in argv or not names:
        names = list(ALL[:6])
    keep = "--keep" in argv
    for _ in range(60):   # the editor may still be opening after a build
        try:
            wire.call(wire.UNREAL, "ping", timeout=10)
            break
        except Exception:
            time.sleep(5)
    # Pick up a hot-copied daedalus_play.py: the bridge registered play_scenario at editor start and reload()
    # re-executes the module in place, so the registered function sees the new SCENARIOS (2026-10-13: "unknown
    # scenario" for a scenario added after the editor opened).
    # Also drop any private checkout another bot prepended to sys.path (22:10: Poot's Documents\Codex\...\Content\Python
    # shadowed the live plugin seven times over), so the live plugin's modules are the ones that run.
    code = (
        "import sys, importlib, os\n"
        "live = r'C:\\Unreal\\DaedalusRealm\\Plugins\\DaedalusLink\\Content\\Python'\n"
        "sys.path[:] = [p for p in sys.path if 'Documents' not in p or 'Codex' not in p]\n"
        "if live not in sys.path: sys.path.insert(0, live)\n"
        "for m in [m for m in list(sys.modules) if m.startswith('daedalus_') and os.path.exists(os.path.join(live, m + '.py'))]:\n"
        "    importlib.reload(sys.modules[m])\n"
        "import daedalus_play, daedalus_control\n"
        "print(daedalus_play.__file__)\nprint(sorted(daedalus_play.SCENARIOS))\n")
    rl = wire.call(wire.UNREAL, "execute_python", code=code, timeout=60)
    print("scenarios:", (rl.get("stdout") or "").strip()[-400:], flush=True)
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
        for _ in range(MAX_WAIT_S):   # 01:35: the airship tour flies ~5 min; 180 s abandoned it mid-flight
            time.sleep(1)
            s = wire.call(wire.UNREAL, "daedalus.play_status", timeout=20)
            if not s.get("running"):
                break
        r = s.get("result") or {}
        if r.get("interrupted"):   # a person drove the Play window: rerun this one once, hands off
            print("%s INTERRUPTED: %s -> rerunning once" % (name, r["interrupted"]), flush=True)
            time.sleep(5)
            wire.call(wire.UNREAL, "daedalus.play_scenario", name=name, timeout=20)
            for _ in range(MAX_WAIT_S):
                time.sleep(1)
                s = wire.call(wire.UNREAL, "daedalus.play_status", timeout=20)
                if not s.get("running"):
                    break
            r = s.get("result") or {}
            if r.get("interrupted"):
                print("%s INTERRUPTED again: counted as not run" % name, flush=True)
                continue
        print("%s error= %s passed=%s/%s fps=%s frames=%s seconds=%s" % (name, s.get("error"), r.get("passed"), r.get("total"), r.get("fps"), r.get("frames"), r.get("seconds")), flush=True)
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
