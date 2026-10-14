# SPDX-License-Identifier: MIT
"""Headless checks for daedalus_realm_ground: origins apart, the kit on the hub, markers where the rules say."""
import json
import os

import daedalus_land_grid as G
import daedalus_realm_ground as R

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


os_ = sorted(R.ORIGINS.values())
dists = [max(abs(a[0] - b[0]), abs(a[1] - b[1])) for i, a in enumerate(os_) for b in os_[i + 1:]]
check("five realms, every pair at least 40 km apart (a 25.6 km grid never touches another)", len(R.ORIGINS) == 5 and min(dists) >= 100 * G.SIDE * G.PITCH_M)
check("the hub estate is the 9 cells round (50,50)", R.hub_cells() == {G.number(x, y) for x in range(49, 52) for y in range(49, 52)})
here = os.path.dirname(os.path.abspath(__file__))
man = os.path.join(here, "..", "..", "..", "..", "..", "data", "art", "gallery", "environment-manifest.json")
ids = [a["id"] for a in json.load(open(man))["assets"]] if os.path.exists(man) else ["Prop_Gallery_FloorTile", "Prop_Gallery_RainbowFrame", "Prop_Gallery_DroneDock", "Prop_Gallery_AirlockEntry", "Prop_Gallery_ConcertPlatform"] + ["Prop_Gallery_X%d" % i for i in range(19)]
o = R.ORIGINS["GALLERY-CITY"]
lay = R.layout(ids, o)
half = R.hub_half_cm()
check("every kit prop is placed", set(lay) == set(ids))
check("every prop stands on the hub slab", all(abs(p[0] - o[0]) <= half and abs(p[1] - o[1]) <= half for p in lay.values()))
pts = list(lay.values())
near = min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for i, a in enumerate(pts) for b in pts[i + 1:])
check("no two props closer than 8 m (the largest radius is 3.7 m)", near >= 800.0)
check("the rainbow frame stands at the south edge", lay["Prop_Gallery_RainbowFrame"][1] < o[1] - half * 0.7)
check("the drone dock stands at the west edge", lay["Prop_Gallery_DroneDock"][0] < o[0] - half * 0.7)
m = R.markers(o)
check("spawn, gate, dock, sub dock and mount markers exist", set(m) == {"Spawn", "Gate", "Dock", "SubDock", "Mount"})
check("the gate marker is just north of the rainbow frame", 0 < m["Gate"][1] - lay["Prop_Gallery_RainbowFrame"][1] <= 600.0)
check("the dock marker is on the east edge", m["Dock"][0] > o[0] + half * 0.7)
check("kind() strips the realm prefix", R.kind("Prop_Gallery_FloorTile") == "FloorTile" and R.kind("Prop_Parcels_AMF_Trough_V12") == "AMF_Trough_V12")
roles = R.cast_roles("DCS 1\nwho Postmaster Grue\nvoice x\nstep a\n  say hi\nwho Lost-Letter Ghost\n")
check("cast_roles reads the who lines in order", roles == ["Postmaster Grue", "Lost-Letter Ghost"])
ring = R.cast_ring(12, (0.0, 0.0))
check("twelve talkers stand 60 m from the spawn", len(ring) == 12 and all(abs((p[0] ** 2 + p[1] ** 2) ** 0.5 - R.CAST_RADIUS_CM) < 1e-6 for p in ring))
check("each faces the spawn", abs(ring[0][3] - 180.0) < 1e-6 and abs(ring[3][3] - (-90.0)) < 1e-6)
check("the ring sits on the hub", all(abs(p[0]) < half and abs(p[1]) < half for p in ring))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
