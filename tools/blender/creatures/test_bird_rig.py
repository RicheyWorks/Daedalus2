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
# G142 crane: long-bird params, Walk / Fly / Dance, bone socket SOCKET_LegBand; gull defaults unchanged
import json as _json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "contest"))
import crane_g142, gull_g139
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
t("gull == its pin (new params/clips are opt-in)", _json.loads(_json.dumps(gull_g139.gull())) == _json.load(open(os.path.join(ROOT, "data", "contest", "g139_gull.quad.json"), encoding="utf-8")))
c = crane_g142.crane(); cb = {b["name"]: b for b in c["bones"]}; cp = c["predicted"]; CC = c["clips"]
t("crane == its pin", _json.loads(_json.dumps(c)) == _json.load(open(os.path.join(ROOT, "data", "contest", "g142_crane.quad.json"), encoding="utf-8")))
t("crane ~1.2 m tall (1.1-1.3), feet on z=0, centred", 1.1 <= cp["dimensions"][2] <= 1.3 and abs(cp["bounds_min"][2]) < 1e-6 and abs(cp["bounds_min"][0] + cp["bounds_max"][0]) < 0.01, cp["dimensions"])
t("crane legs ~half its height", 0.45 <= cb["Leg_L"]["head"][2] / cp["dimensions"][2] <= 0.6)
t("crane clips Idle, Walk, Fly, Dance", sorted(CC) == ["Dance", "Fly", "Idle", "Walk"])
t("crane clips loop on real bones", all(b in cb for k in CC.values() for b in k["tracks"]) and all(x[0][1] == x[-1][1] for k in CC.values() for tr in k["tracks"].values() for x in tr.values()))
t("Walk: legs in antiphase, body drops to keep the stance foot down", all(abs(a[1][0] + b[1][0]) < 1e-9 for a, b in zip(CC["Walk"]["tracks"]["Leg_L"]["rot"], CC["Walk"]["tracks"]["Leg_R"]["rot"])) and max(v[1][2] for v in CC["Walk"]["tracks"]["Body"]["loc"]) <= 0 < -min(v[1][2] for v in CC["Walk"]["tracks"]["Body"]["loc"]))
fw = CC["Fly"]["tracks"]
t("Fly: wings spread sideways (mirrored) and flap, legs trail", fw["Wing_L"]["rot"][0][1][2] < -math.radians(80) and fw["Wing_R"]["rot"][0][1][2] > math.radians(80) and max(v[1][0] for v in fw["Wing_L"]["rot"]) - min(v[1][0] for v in fw["Wing_L"]["rot"]) > math.radians(90) and fw["Leg_L"]["rot"][0][1][0] > math.radians(60))
dw = CC["Dance"]["tracks"]
t("Dance: hops (body up >= 0.15 m), wings half open (40-70 deg) throughout", max(v[1][2] for v in dw["Body"]["loc"]) >= 0.15 and all(math.radians(40) <= abs(v[1][2]) <= math.radians(70) for v in dw["Wing_L"]["rot"]))
t("Dance: lands between hops (body back on the ground)", min(v[1][2] for v in dw["Body"]["loc"]) == 0)
S = {x["name"]: x for x in c.get("sockets", [])}
t("SOCKET_LegBand on bone Leg_L", list(S) == ["SOCKET_LegBand"] and S["SOCKET_LegBand"]["bone"] == "Leg_L")
lb = S["SOCKET_LegBand"]["location"]; lh, lt = cb["Leg_L"]["head"], cb["Leg_L"]["tail"]
t("leg band sits on the lower leg, between foot and hip", lt[2] < lb[2] < 0.5 * lh[2] and abs(lb[0] - lh[0]) < 1e-9 and S["SOCKET_LegBand"]["offset_from_bone_head"] == [round(lb[i] - lh[i], 6) + 0.0 for i in range(3)])
try:
    R.recipe("x", 1, clip_names=("Idle", "Moonwalk")); t("unknown clip refused", False)
except ValueError:
    t("unknown clip refused", True)
try:
    R.recipe("x", 1, sockets=[("X", "Wing_Q", (0, 0, 0))]); t("socket on an unknown bone refused", False)
except ValueError:
    t("socket on an unknown bone refused", True)
t("crane LOD1 35-65%, <= 6000 tris", 0.35 <= cp["lod1_ratio"] <= 0.65 and cp["triangles"] <= 6000)

# ---- proportion presets + perch posture + owl face (2026-10-29)
import json as _j2
def _ratios(P):
    g = R._g(P); L = P["L"]
    return P["leg"] / L, (g["head"][1] - g["neck0"][1]) / L
Pd0 = R.params(5, "Def"); dleg, dneck = _ratios(Pd0)
for pr in ("raptor", "owl", "small"):
    want = R.PROPORTIONS[pr]; Pp = R.params(5, "X_" + pr, {"proportions": pr}); leg, neck = _ratios(Pp)
    t("preset %s: leg ratio == %.2f" % (pr, want["leg_frac"]), abs(leg - want["leg_frac"]) < 1e-6, leg)
    t("preset %s: neck rise ratio == %.2f" % (pr, want["neck_len"]), abs(neck - want["neck_len"]) < 1e-6, neck)
    t("preset %s: legs and neck shorter than the default bird" % pr, leg < dleg and neck < dneck, (leg, dleg, neck, dneck))
    t("preset %s: head_scale %.2f, preset key not left in params" % (pr, want["head_scale"]), Pp["head_scale"] == want["head_scale"] and "proportions" not in Pp)
    mp = R.recipe("X_" + pr, 5, body={"proportions": pr}, clip_names=("Idle", "Walk", "Fly"))
    t("preset %s: feet on z=0, head above body" % pr, abs(mp["predicted"]["bounds_min"][2]) < 1e-6 and {b["name"]: b for b in mp["bones"]}["Head"]["head"][2] > {b["name"]: b for b in mp["bones"]}["Body"]["head"][2])
t("explicit leg_frac beats the preset", R.params(5, "X", {"proportions": "raptor", "leg_frac": 0.3})["leg"] == round(0.3 * 0.6, 6))
try:
    R.params(5, "X", {"proportions": "penguin"}); t("unknown preset refused", False)
except ValueError:
    t("unknown preset refused", True)
t("default bird unchanged: no new keys in params", not ({"neck_len", "proportions", "posture", "perch_deg", "facial_disc"} & set(Pd0)))
t("default bird unchanged: recipe(body=None) == recipe(body={})", R.recipe("Def", 5) == R.recipe("Def", 5, body={}))
t("juvenile crane == its pin", (lambda M: _j2.loads(_j2.dumps(M.juvenile())) == _j2.load(open(os.path.join(ROOT, "data", "contest", "g504_crane_juvenile.quad.json"), encoding="utf-8")))(__import__("marsh_g504")))
st = R.recipe("Perch", 7, body={"proportions": "raptor"}, sockets=[("Head", "Head", (0, -0.1, 0.2)), ("Talon", "Leg_L", (0.03, 0.0, 0.01))])
pe = R.recipe("Perch", 7, body={"proportions": "raptor", "posture": "perch", "perch_deg": 35.0}, sockets=[("Head", "Head", (0, -0.1, 0.2)), ("Talon", "Leg_L", (0.03, 0.0, 0.01))])
sb = {b["name"]: b for b in st["bones"]}; pb = {b["name"]: b for b in pe["bones"]}
t("perch: legs, feet and leg sockets unchanged", all(sb[n] == pb[n] for n in ("Leg_L", "Leg_R", "Root")) and [p for p in st["parts"] if p["bone"].startswith("Leg_")] == [p for p in pe["parts"] if p["bone"].startswith("Leg_")] and st["sockets"][1] == pe["sockets"][1])
t("perch: head higher, tail lower, body pitched ~35 deg", pb["Head"]["head"][2] > sb["Head"]["head"][2] + 0.03 and pb["Tail"]["tail"][2] < sb["Tail"]["tail"][2]
  and abs(math.degrees(math.atan2(pb["Body"]["tail"][2] - pb["Body"]["head"][2], pb["Body"]["tail"][1] - pb["Body"]["head"][1])) + 35) < 0.5)
t("perch: nothing below the ground", pe["predicted"]["bounds_min"][2] > -1e-6, pe["predicted"]["bounds_min"])
t("perch: head socket moves with the head", pe["sockets"][0]["location"] != st["sockets"][0]["location"])
try:
    R.recipe("X", 1, body={"posture": "lying"}); t("unknown posture refused", False)
except ValueError:
    t("unknown posture refused", True)
ow = R.recipe("Owl", 8, body={"proportions": "owl", "beak_style": "owl", "facial_disc": True}); L8 = ow["params"]["L"]
bk = [q for p in ow["parts"] if p["name"].startswith("Beak") for q in K.part_points(p)]
hd = [q for p in ow["parts"] if p["name"] == "Head" for q in K.part_points(p)]
t("owl beak short (< 0.06 L past the face)", min(q[1] for q in hd) - min(q[1] for q in bk) < 0.06 * L8, (min(q[1] for q in hd), min(q[1] for q in bk)))
t("owl has a facial disc (2 halves) and forward eyes", sum(p["name"].startswith("FaceDisc_") for p in ow["parts"]) == 2 and all(p["axis"] == "y" for p in ow["parts"] if p["name"].startswith("Eye_")))
ot = R.recipe("Owl", 8, body={"proportions": "owl", "beak_style": "owl", "facial_disc": True, "ear_tufts": True, "feet": "talons"})
tuf = [p for p in ot["parts"] if p["name"].startswith("EarTuft_")]
t("ear tufts: 2, on the Head bone, above the head top", len(tuf) == 2 and all(p["bone"] == "Head" for p in tuf) and min(q[2] for p in tuf for q in K.part_points(p)) > {b["name"]: b for b in ot["bones"]}["Head"]["head"][2])
t("ear tufts opt-in (absent by default)", not any(p["name"].startswith("EarTuft_") for p in ow["parts"]))
for nm_, bd_ in (("talons", {"feet": "talons"}), ("perch talons", {"feet": "talons", "proportions": "raptor", "posture": "perch"}), ("webbed", {})):
    t("base: %s bird sits exactly on z=0 (nothing below the ground)" % nm_, R.recipe("G", 3, body=bd_)["predicted"]["bounds_min"][2] >= 0.0, R.recipe("G", 3, body=bd_)["predicted"]["bounds_min"])
print("%d/%d" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
