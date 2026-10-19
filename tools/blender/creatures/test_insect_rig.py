# SPDX-License-Identifier: MIT
"""Checks for creatures/insect_rig.py (blender-insect/v1) and the kitlib slab shape it uses. python test_insect_rig.py"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "kit"))
import kitlib as K, insect_rig as I

checks = []
def add(n, r, d=""): checks.append((n, bool(r), d))
m = I.recipe("Mob_Test_Insect", 7); B = {b["name"]: b for b in m["bones"]}; P = {p["name"]: p for p in m["parts"]}; pr = m["predicted"]
add("10 bones, one root", len(B) == 10 and [b for b in B.values() if b["parent"] is None] == [B["Root"]])
add("parents exist", all(b["parent"] is None or b["parent"] in B for b in B.values()))
add("wing + antenna bones mirrored L/R", all(B[n + "_L"]["head"][0] == -B[n + "_R"]["head"][0] and B[n + "_L"]["head"][1:] == B[n + "_R"]["head"][1:] for n in ("WingF", "WingH", "Antenna")))
add("wing bones lie along +-X (clean flap about the body axis)", all(B[n]["head"][1:] == B[n]["tail"][1:] and (B[n]["tail"][0] - B[n]["head"][0]) * (1 if n.endswith("_L") else -1) > 0
                                                                   for n in B if n.startswith("Wing")))
add("every part bound to an existing bone, all rigid", all(p["bone"] in B and p.get("rigid") for p in P.values()) and m["bind_mode"] == "rigid")
add("wings are slabs on their own wing bones", all(P[n]["shape"] == "slab" and P[n]["bone"] == n for n in ("WingF_L", "WingF_R", "WingH_L", "WingH_R")))
add("default span 4.5 cm apex to apex", abs(pr["dimensions"][0] - 0.045) < 1e-4, pr["dimensions"])
add("perches on z=0 (feet), body above", abs(pr["bounds_min"][2]) < 2e-4 and P["Thorax"]["centre"][2] > 0, pr["bounds_min"])
add("front is -Y (head ahead of thorax)", P["Head"]["centre"][1] < P["Thorax"]["centre"][1] < P["Abdomen"]["centre"][1])
add("forewing over hindwing", P["WingF_L"]["centre"][2] > P["WingH_L"]["centre"][2])
add("tris <= 1500, LOD1 35-65%", pr["triangles"] <= 1500 and 0.35 <= pr["lod1_ratio"] <= 0.65, pr)
add("clips Idle + Flutter, looping", sorted(m["clips"]) == ["Flutter", "Idle"] and all(c["loop"] and all(k[0][1] == k[-1][1] for t in c["tracks"].values() for k in t.values()) for c in m["clips"].values()))
add("Idle keeps the wings flat (no wing tracks)", not any(n.startswith("Wing") for n in m["clips"]["Idle"]["tracks"]))
fl = m["clips"]["Flutter"]["tracks"]; amp = max(abs(k[1][0]) for k in fl["WingF_L"]["rot"])
add("Flutter flaps the wings > 40 deg", math.degrees(amp) > 40, math.degrees(amp))
add("Flutter symmetric flap (same local-X angle both sides)", [k[1][0] for k in fl["WingF_L"]["rot"]] == [k[1][0] for k in fl["WingF_R"]["rot"]])
add("Flutter bobs the body off the perch", min(k[1][2] for k in fl["Root"]["loc"]) > 0)
add("clip tracks only name real bones", all(b in B for c in m["clips"].values() for b in c["tracks"]))
add("deterministic", I.recipe("Mob_Test_Insect", 7) == m)
add("seed changes the sway only, not the skeleton", I.recipe("Mob_Test_Insect", 8)["bones"] == m["bones"])
try:
    I.recipe("x", 1, body={"stinger": 1}); add("unknown body param refused", False)
except ValueError:
    add("unknown body param refused", True)
bf = I.recipe("Mob_Test_Butterfly", 3, body={"wing": "butterfly", "antenna": "clubbed", "span": 0.06})
add("butterfly variant: clubbed antennae, 6 cm", any(p["name"].startswith("AntennaClub") for p in bf["parts"]) and abs(bf["predicted"]["dimensions"][0] - 0.06) < 1e-3, bf["predicted"]["dimensions"])
add("hops helper", I.hops(m["bones"], "WingF_L", "Abdomen") == 2)
s = K.slab("S", [(0, 0), (1, 0), (1, 1), (0.5, 1.5), (0, 1)], 0.1, (0, 0, 0), 0, lod1={"segments": 3})
add("slab: tris 4n-4, LOD1 halves the outline", (K.part_tris(s), K.part_tris(s, 1), len(K.local_verts(s)), len(K.local_verts(s, 1))) == (16, 8, 10, 6))
ok = 0
for n, r, dd in checks:
    ok += r
    if not r: print("FAIL", n, dd)
print("%d/%d" % (ok, len(checks))); sys.exit(0 if ok == len(checks) else 1)
