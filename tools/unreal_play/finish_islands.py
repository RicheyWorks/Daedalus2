# SPDX-License-Identifier: MIT
"""Finish the islands (Richey 2026-10-13 23:50: "finish all the islands real fast", "add ground"):
ground under the hub districts of every realm, then every district (0..99) of the four 3D realms laid as plots
into streamed sublevels, each with its ground slab. One daedalus.steps call per realm; prints progress.

    python tools/unreal_play/finish_islands.py [GALLERY-CITY,PARCELS,...]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

HUB = [44, 45, 54, 55]


def steps(expr, label, timeout=7200):
    code = "import importlib, daedalus_plots, daedalus_districts\nimportlib.reload(daedalus_plots)\nimportlib.reload(daedalus_districts)\ndef steps():\n    return (yield from %s)\n" % expr
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, timeout=timeout)
    for line in r.get("yielded", [])[-3:]:
        print("  " + line, flush=True)
    print("%s: steps=%s seconds=%s error=%s result=%s" % (label, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:], r.get("result")), flush=True)
    return r


def main(argv):
    realms = (argv[0] if argv else "GALLERY-CITY,PARCELS,BRICKS,LABYRINTH").split(",")
    if wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):
        wire.call(wire.UNREAL, "stop", timeout=60)
        time.sleep(3)
    t0 = time.time()
    for realm in ["WORLD-ZERO"] + realms:
        steps("daedalus_districts.lay_ground_steps(%r, %r)" % (realm, HUB), "ground " + realm, 1800)
    for realm in realms:
        rest = [d for d in range(100) if d not in HUB]
        steps("daedalus_districts.lay_district_steps(%r, %r)" % (realm, rest), "districts " + realm, 7200)
    print("done in %.0f s" % (time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
