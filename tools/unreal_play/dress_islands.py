# SPDX-License-Identifier: MIT
"""Finish the islands' look (Richey 2026-10-14 01:19): heights, thickness, rock undersides, kit props, every realm.

    python tools/unreal_play/dress_islands.py [WORLD-ZERO,GALLERY-CITY,...]
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def hub(text):
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text", text],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass


def main(argv):
    realms = (argv[0] if argv else "WORLD-ZERO,GALLERY-CITY,PARCELS,BRICKS,LABYRINTH").split(",")
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "stop", timeout=60)
        time.sleep(3)
    t0 = time.time()
    for realm in realms:
        code = ("import importlib, daedalus_plots, daedalus_districts, daedalus_realm_ground\nimportlib.reload(daedalus_plots)\nimportlib.reload(daedalus_districts)\n"
                "def steps():\n    return (yield from daedalus_districts.dress_islands_steps([%r]))\n" % realm)
        r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="dress " + realm, timeout=3600)
        for line in r.get("yielded", [])[-2:]:
            print("  " + line, flush=True)
        print("%s: steps=%s seconds=%s error=%s result=%s" % (realm, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-400:], r.get("result")), flush=True)
        hub("ISLANDS dressed %s: %s %.0f s error=%s" % (realm, r.get("result"), time.time() - t0, (r.get("error") or "-")[-120:]))
        if r.get("error"):
            return 1
    print("done in %.0f s" % (time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
