# SPDX-License-Identifier: MIT
"""Pure-Python checks for Prop_PracticeCrate's recipe against the 48146 spec (no Blender). python test_crate_recipe.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crate_recipe as C

PINNED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "practice", "Prop_PracticeCrate.recipe.json")
m = C.recipe(); p = m["predicted"]; ok = 0; checks = [
    ("triangles == 132", p["triangles"] == 132),
    ("triangles <= tri_cap 500", p["triangles"] <= C.SPEC["tri_cap"]),
    ("size 0.52 x 0.52 x 0.5 m", p["dimensions"] == C.SPEC["size_m"]),
    ("stands on z=0", p["bounds_min"][2] == 0),
    ("centred on x/y", p["bounds_min"][0] == -p["bounds_max"][0] and p["bounds_min"][1] == -p["bounds_max"][1]),
    ("2 slots wood/dark", [x["hex"] for x in m["materials"]] == ["9A6B3F", "4A4D57"]),
    ("slot names Prop_PracticeCrate_M0/M1", [x["name"] for x in m["materials"]] == ["Prop_PracticeCrate_M0", "Prop_PracticeCrate_M1"]),
    ("every part uses a real slot", all(0 <= x["slot"] < len(m["materials"]) for x in m["parts"])),
    ("socket SOCKET_Top at (0,0,0.5)", [(s["name"], s["location"]) for s in m["sockets"]] == [("SOCKET_Top", [0.0, 0.0, 0.5])]),
    ("deterministic", C.recipe() == m),
    ("pinned manifest matches", json.load(open(PINNED, encoding="utf-8")) == m),
]
for n, r in checks:
    ok += bool(r); print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
