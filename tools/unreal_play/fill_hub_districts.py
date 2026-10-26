# SPDX-License-Identifier: MIT
"""Fill the holes round each realm's hub (Richey 01:50: "fix the holes in the floor of that island"): the four hub
districts (44, 45, 54, 55) were skipped when the districts were laid, so every cell of them beyond ring 6 was a
gap. Lay those cells as instanced plots (the hub island's own 3x3 cells and the existing Land_ actors are skipped
by label), dress them, apply the cull/shadow pass, save.

    python tools/unreal_play/fill_hub_districts.py [GALLERY-CITY,PARCELS,...]
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

HUB = [44, 45, 54, 55]


def steps(expr, label, timeout=1800):
    code = ("import importlib, daedalus_plots, daedalus_districts, daedalus_realm_ground\nimportlib.reload(daedalus_plots)\nimportlib.reload(daedalus_districts)\n"
            "def steps():\n    return (yield from %s)\n" % expr)
    r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, timeout=timeout)
    for line in r.get("yielded", [])[-2:]:
        print("  " + line, flush=True)
    print("%s: steps=%s seconds=%s error=%s result=%s" % (label, r.get("steps"), r.get("seconds"), (r.get("error") or "-")[-300:], str(r.get("result"))[:300]), flush=True)
    return r


def main(argv):
    realms = (argv[0] if argv else "GALLERY-CITY,PARCELS,BRICKS,LABYRINTH").split(",")
    while wire.call(wire.UNREAL, "ping", timeout=10).get("playing"):   # wait for the tour to land
        time.sleep(10)
    t0 = time.time()
    summary = []
    for realm in realms:
        r = steps("daedalus_districts.lay_district_steps(%r, %r, taken=set(daedalus_realm_ground.hub_cells()))" % (realm, HUB), "hub districts " + realm)
        summary.append("%s +%s plots" % (realm, (r.get("result") or {}).get("plots")))
        if r.get("error"):
            return 1
    steps("daedalus_districts.dress_islands_steps(%r)" % realms, "dress hubs")
    steps("daedalus_districts.perf_steps()", "perf")
    msg = "ISLANDS hub holes filled: %s in %.0f s" % ("; ".join(summary), time.time() - t0)
    print(msg, flush=True)
    try:
        subprocess.run([sys.executable, "-m", "asset_pipeline.teamlink", "send", "--to", "*", "--type", "status", "--topic", "islands", "--text", msg],
                       capture_output=True, text=True, timeout=20, cwd=os.path.join(REPO, "connectors", "claude-asset-pipeline"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
