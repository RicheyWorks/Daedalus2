# SPDX-License-Identifier: MIT
"""Tests for bird_rig (blender-bird/v1). No Blender. Prints ok/FAIL lines and n/m."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import bird_rig as R, kitlib as K

res = []


def t(name, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  %s" % (info,)))


m = R.recipe("Char_YTM_Gull", 13939); B = {b["name"]: b for b in m["bones"]}; Pd = m["predicted"]
t("10 bones, one root", len(B) == 10 and [b for b in B.values() if b["parent"] is None] == [B["Root"]])
t("every parent exists", all(b["parent"] in B for b in B.values() if b["parent"]))
t("beak hinge under the head", B["Beak_Lower"]["parent"] == "Head" and B["Head"]["parent"] == "Neck")
t("every part on a real bone, rigid", all(p["bone"] in B and p["rigid"] for p in m["parts"]) and m["bind_mode"] == "rigid")
t("gull about 0.6 m beak to tail", abs(Pd["dimensions"][1] - 0.6) < 0.02, Pd["dimensions"])
t("feet on z=0", abs(Pd["bounds_min"][2]) < 1e-6, Pd["bounds_min"])
t("beak in front (-Y), tail behind", min(p["centre"][1] for p in m["parts"] if p["bone"] == "Beak_Lower") < -0.22 and [p for p in m["parts"] if p["name"] == "Tail"][0]["centre"][1] > 0.2)
t("head above the body", B["Head"]["head"][2] > B["Body"]["head"][2] + 0.1)
t("symmetric: L/R bones mirror in X", all(abs(B[n + "_L"]["head"][0] + B[n + "_R"]["head"][0]) < 1e-9 for n in ("Wing", "Leg")))
t("wings lie along the flanks (long in Y, thin in X)", all((lambda v: (max(y for _, y, _ in v) - min(y for _, y, _ in v)) > 5 * (max(x for x, _, _ in v) - min(x for x, _, _ in v)))(K.part_points(p)) for p in m["parts"] if p["name"].startswith("Wing_")))
t("low poly (< 600 tris), LOD1 35-65%", Pd["triangles"] < 600 and 0.35 <= Pd["lod1_ratio"] <= 0.65, Pd)
C = m["clips"]
t("clips Idle + Squawk only", sorted(C) == ["Idle", "Squawk"])
t("clips loop (first key == last key)", all(tr[k][0][1] == tr[k][-1][1] for c in C.values() for tr in c["tracks"].values() for k in tr))
t("clip tracks use real bones", all(b in B for c in C.values() for b in c["tracks"]))
gape = max(v[1][0] for v in C["Squawk"]["tracks"]["Beak_Lower"]["rot"])
t("squawk opens the beak > 30 deg", math.degrees(gape) > 30, math.degrees(gape))
t("squawk lifts both wings, mirrored", all(abs(a[1][1] + b[1][1]) < 1e-9 for a, b in zip(C["Squawk"]["tracks"]["Wing_L"]["rot"], C["Squawk"]["tracks"]["Wing_R"]["rot"])) and max(abs(k[1][1]) for k in C["Squawk"]["tracks"]["Wing_L"]["rot"]) > math.radians(20))
t("idle keeps the beak shut", "Beak_Lower" not in C["Idle"]["tracks"])
t("squawk holds open mid-clip", min(k[1][0] for k in C["Squawk"]["tracks"]["Beak_Lower"]["rot"] if 0.4 * 36 <= k[0] <= 0.6 * 36) > math.radians(20))
t("deterministic", R.recipe("Char_YTM_Gull", 13939) == m)
try:
    R.recipe("X", 1, body={"wingspan": 1}); t("unknown body params refused", False)
except ValueError:
    t("unknown body params refused", True)
small = R.recipe("Char_Pigeon", 2, body={"length": 0.32})
t("length param scales the bird", abs(small["predicted"]["dimensions"][1] - 0.32) < 0.015, small["predicted"]["dimensions"])
t("every slab keeps >= 3 outline points at LOD1 (kitlib halves the outline)", all(len(K._slab_outline(p, 1)) >= 3 for p in m["parts"] if p["shape"] == "slab" and K.in_lod(p, 1)))
print("%d/%d" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
