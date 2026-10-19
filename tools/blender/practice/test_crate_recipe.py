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
A, B = C.recipe("A"), C.recipe("B"); D = C.delta(A, B); D_PIN = os.path.join(os.path.dirname(PINNED), "Prop_PracticeCrate.%s.recipe.json")
ucx = lambda v: v["collision"][0]
checks += [
    ("base recipe has no collision/variant (original bytes path unchanged)", "collision" not in m and "variant" not in m),
    ("A = base geometry + UCX only", A["parts"] == m["parts"] and A["materials"] == m["materials"] and A["sockets"] == m["sockets"]),
    ("A UCX named UCX_Prop_PracticeCrate, convex box, 12 tris", (ucx(A)["name"], ucx(A)["shape"], ucx(A)["tris"], ucx(A)["convex"]) == ("UCX_Prop_PracticeCrate", "box", 12, True)),
    ("A UCX covers the bounds", ucx(A)["size"] == A["predicted"]["dimensions"] and ucx(A)["centre"] == [0.0, 0.0, 0.25]),
    ("B keeps asset name, materials, socket", B["asset"] == A["asset"] == "Prop_PracticeCrate" and B["materials"] == A["materials"] and B["sockets"] == A["sockets"]),
    ("B keeps the pivot (z=0, centred)", B["predicted"]["bounds_min"][2] == 0 and B["predicted"]["bounds_min"][0] == -B["predicted"]["bounds_max"][0]),
    ("B tris 264 (A 132, delta +132)", (A["predicted"]["triangles"], B["predicted"]["triangles"], D["triangles"]) == (132, 264, 132)),
    ("B bounds delta y +0.01 m only", D["dimensions"] == [0.0, 0.01, 0.0]),
    ("B UCX resized to B bounds", ucx(B)["size"] == B["predicted"]["dimensions"]),
    ("B under tri_cap", B["predicted"]["triangles"] <= C.SPEC["tri_cap"]),
    ("variants deterministic", C.recipe("A") == A and C.recipe("B") == B),
    ("A/B recipe hashes differ", A["recipe_sha256"] != B["recipe_sha256"] != m["recipe_sha256"]),
    ("pinned A manifest matches", json.load(open(D_PIN % "A", encoding="utf-8")) == A),
    ("pinned B manifest matches", json.load(open(D_PIN % "B", encoding="utf-8")) == B),
]
for n, r in checks:
    ok += bool(r); print(("ok   " if r else "FAIL ") + n)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
