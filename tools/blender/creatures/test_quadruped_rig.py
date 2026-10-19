# SPDX-License-Identifier: MIT
"""Pure-Python checks for quadruped_rig.py (no Blender). python test_quadruped_rig.py"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quadruped_rig as Q
checks = []
add = lambda n, ok, d="": checks.append((n, bool(ok), d))
m = Q.recipe("Mob_Test_Quad", 7); m2 = Q.recipe("Mob_Test_Quad", 7); m3 = Q.recipe("Mob_Test_Quad", 8)
add("deterministic per seed", m == m2); add("seed changes body params", m["params"] != m3["params"])
B = {b["name"]: b for b in m["bones"]}
add("15 bones, one root", len(B) == 15 and [b for b in B.values() if b["parent"] is None] == [B["Root"]])
add("parents exist (tree)", all(b["parent"] in B for b in B.values() if b["parent"]))
add("no zero-length bones", all(math.dist(b["head"], b["tail"]) > 0.01 for b in B.values()))
add("every part bound to an existing bone", all(p["bone"] in B for p in m["parts"]))
add("legs: L on +X (own left facing -Y), F at -Y", B["LegFL_Upper"]["head"][0] > 0 and B["LegFR_Upper"]["head"][0] < 0 and B["LegFL_Upper"]["head"][1] < 0 and B["LegBL_Upper"]["head"][1] > 0)
d = m["predicted"]["dimensions"]
add("~1.6 m long (1.5-1.7) along Y", 1.5 <= d[1] <= 1.7, d)
add("stands on z=0", abs(m["predicted"]["bounds_min"][2]) < 1e-6, m["predicted"]["bounds_min"])
add("centred in x", abs(m["predicted"]["bounds_min"][0] + m["predicted"]["bounds_max"][0]) < 0.01)
add("tris <= 6000 (Mob)", m["predicted"]["triangles"] <= 6000, m["predicted"]["triangles"])
add("LOD1 35-65%", 0.35 <= m["predicted"]["lod1_ratio"] <= 0.65, m["predicted"]["lod1_ratio"])
add("<= 3 materials, all slots defined", len(m["materials"]) <= 3 and all(p["slot"] < len(m["materials"]) for p in m["parts"]))
C = m["clips"]
add("clips Idle, Walk, Run", sorted(C) == ["Idle", "Run", "Walk"])
for n, c in C.items():
    tr = c["tracks"]
    add("%s tracks name real bones" % n, all(b in B for b in tr))
    add("%s loops (first key == last key)" % n, all(k[0][1] == k[-1][1] and k[0][0] == 0 and k[-1][0] == c["frames"] for t in tr.values() for k in t.values()))
    add("%s keys inside the clip, ascending" % n, all([f for f, _ in k] == sorted({f for f, _ in k}) for t in tr.values() for k in t.values()))
def swing(clip, leg):
    return [v[0] for _, v in C[clip]["tracks"]["Leg%s_Upper" % leg]["rot"]]
add("Idle keeps legs still", not any(k.startswith("Leg") for k in C["Idle"]["tracks"]))
add("Walk: diagonal pairs in phase", swing("Walk", "FL") == swing("Walk", "BR") and swing("Walk", "FR") == swing("Walk", "BL"))
add("Walk: left/right antiphase", all(abs(a + b) < 1e-4 for a, b in zip(swing("Walk", "FL"), swing("Walk", "FR"))))
add("Run: front pair vs hind pair offset (bound)", abs(max(swing("Run", "FL")) - max(swing("Run", "BL"))) < 1e-3 and swing("Run", "FL") != swing("Run", "BL"))
add("Run faster and bigger than Walk", C["Run"]["seconds"] < C["Walk"]["seconds"] and max(swing("Run", "FL")) > max(swing("Walk", "FL")))
add("swing within +/-40 deg", all(abs(v) <= math.radians(40) for c in ("Walk", "Run") for l in Q.LEGS for v in swing(c, l)))
add("hops helper", Q.hops(m["bones"], "LegFL_Lower", "Chest") == 2 and Q.hops(m["bones"], "Head", "Head") == 0)
# body params + antler generator (G58 elk); defaults must stay the Hornback
import json
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools", "blender", "contest"))
import g03_hornback, g58_elk
pin = json.load(open(os.path.join(ROOT, "data", "contest", "g03_hornback.quad.json"), encoding="utf-8"))
add("defaults unchanged: Hornback == its pin", json.loads(json.dumps(g03_hornback.hornback())) == pin)
add("body={} same as no body", Q.recipe("Mob_Test_Quad", 7, body={}) == m)
try:
    Q.params(1, "x", body={"wings": 2}); add("unknown body param refused", False)
except ValueError:
    add("unknown body param refused", True)
try:
    Q.params(1, "x", body={"ornament": "tusks"}); add("bad ornament refused", False)
except ValueError:
    add("bad ornament refused", True)
e = g58_elk.elk(); E = {b["name"]: b for b in e["bones"]}; ep = {p["name"]: p for p in e["parts"]}
epin = json.load(open(os.path.join(ROOT, "data", "contest", "g58_elk.quad.json"), encoding="utf-8"))
add("elk == its pin", json.loads(json.dumps(e)) == epin)
ed = e["predicted"]["dimensions"]
add("elk ~2.2 m nose to tail (2.1-2.3)", 2.1 <= ed[1] <= 2.3, ed)
add("elk stands on z=0, centred in x", abs(e["predicted"]["bounds_min"][2]) < 1e-6 and abs(e["predicted"]["bounds_min"][0] + e["predicted"]["bounds_max"][0]) < 0.01)
add("elk same 15-bone skeleton names as the Hornback", sorted(E) == sorted(B))
add("elk tris <= 6000, LOD1 35-65%", e["predicted"]["triangles"] <= 6000 and 0.35 <= e["predicted"]["lod1_ratio"] <= 0.65, e["predicted"])
add("elk: no horns, no back plates", not any(n.startswith(("Horn", "Plate")) for n in ep))
ant = [p for n, p in ep.items() if n.startswith("Antler")]
add("antlers: 3 beam segments + tines per side", sum(1 for p in ant if "_Beam" in p["name"]) == 6 and sum(1 for p in ant if "_Tine" in p["name"]) == 2 * e["params"]["tines"])
add("antlers bound to Head", all(p["bone"] == "Head" for p in ant))
add("antlers mirror L/R", all(abs(ep[n]["centre"][0] + ep[n.replace("AntlerL", "AntlerR")]["centre"][0]) < 1e-6 and ep[n]["centre"][1:] == ep[n.replace("AntlerL", "AntlerR")]["centre"][1:]
                              for n in ep if n.startswith("AntlerL")))
add("antlers rise above the head", min(p["centre"][2] for p in ant) > ep["Head"]["centre"][2])
add("elk clips loop and match the Hornback set", sorted(e["clips"]) == ["Idle", "Run", "Walk"] and all(k[0][1] == k[-1][1] for c in e["clips"].values() for t in c["tracks"].values() for k in t.values()))
add("elk head bone lifted vs body", E["Head"]["head"][2] > E["Chest"]["tail"][2] + 0.2)
ok = 0
for n, r, dd in checks:
    ok += r
    if not r: print("FAIL", n, dd)
print("%d/%d" % (ok, len(checks))); sys.exit(ok != len(checks))
