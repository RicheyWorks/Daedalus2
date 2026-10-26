# SPDX-License-Identifier: MIT
"""G03 Calm the Hornbacks art (pythagoras 48506 pyth-g03-assets-20261019; board rows 15-16; code d8f4f11b).
  Mob_Lab_Hornback  ~1.6 m stocky horned grazer, skinned: tools/blender/creatures/quadruped_rig.py recipe (15 bones, Idle/Walk/Run),
                    pinned at data/contest/g03_hornback.quad.json, built by creatures/build_quadruped.py.
  Prop_Lab_HornbackTrough_Wood  1.2 m wooden trough (blender-kit/v1) with the water surface as a separate named child node
                    Prop_Lab_HornbackTrough_Wood_Water (pivot at the surface so Unreal can raise/lower or swap it), SOCKET_Water; UCX box.
REUSE: labyrinth-cast Mob_Lab_HornbackBull is rigged but ~1.3 m with 8 joints and only Idle/Move clips (no Walk/Run split);
  buffffff livestock (Gruffsheep/Puffgoat) are unrigged 132-tri blocks; labyrinth-cast Prop_Lab_HornbackTrough (264 tris) has no
  child water node. So both are new; the bull is the style reference (dusty hide, ivory horns).
Usage: python g03_hornback.py --out data/contest/g03_hornback.kit.json   (also writes the .quad.json next to it)"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, os.path.join(HERE, "..", "creatures"))
import kitlib as K
import quadruped_rig as Q

SEED = 303
HB, TR = "Mob_Lab_Hornback", "Prop_Lab_HornbackTrough_Wood"
SPEC_HB = {"row": 15, "gap": "G03", "size_m": "~1.6 m long", "tri_cap": 6000, "lod": "LOD0/1", "collision": "none (capsule in UE)",
           "rig": "skinned; baked Idle, Walk, Run", "asker": "pythagoras 48506"}
SPEC_TR = {"row": 16, "gap": "G03", "size_m": "~1.2 m long", "tri_cap": 3000, "lod": "LOD0/1", "collision": "UCX box", "sockets": ["Water"],
           "water": "separate named child node", "asker": "pythagoras 48506"}
CAPS = {TR: 3000}
SOCKETS = {TR: ["SOCKET_Water"]}


def hornback(seed=SEED):
    return Q.recipe(HB, seed, 1.6, spec=SPEC_HB)


def trough(seed=SEED):
    a = TR; w = a + "_Water"
    mats = [K.material(a, 0, "weathered wood", "8A6440", 0.9), K.material(a, 1, "iron", "3A3A3E", 0.8, 0.3), K.material(a, 2, "water (opaque)", "3E7CA8", 0.1)]
    P = [K.box("Bottom", (1.1, 0.42, 0.05), (0, 0, 0.125), 0),
         K.box("SideFront", (1.2, 0.04, 0.3), (0, -0.22, 0.25), 0), K.box("SideBack", (1.2, 0.04, 0.3), (0, 0.22, 0.25), 0),
         K.box("EndL", (0.04, 0.4, 0.3), (0.58, 0, 0.25), 0), K.box("EndR", (0.04, 0.4, 0.3), (-0.58, 0, 0.25), 0)]
    for i, x in enumerate((-0.45, 0.45)):
        P += [K.box("Foot%d" % i, (0.1, 0.6, 0.1), (x, 0, 0.05), 0, lod1={"drop": True}),
              K.box("FootLOD1_%d" % i, (0.1, 0.6, 0.1), (x, 0, 0.05), 0, bevel=False, lod1={"only": True}),
              K.box("Band%d" % i, (0.03, 0.47, 0.32), (x, 0, 0.25), 1, lod1={"drop": True})]
    W = [K.box("Surface", (1.1, 0.4, 0.02), (0, 0, 0.33), 2, bevel=False)]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC_TR, "materials": mats,
         "objects": [K.obj(a, P), K.obj(w, W, parent=a, pivot=(0, 0, 0.34), role="water surface (separate node; Unreal may raise/lower or swap the material)")],
         "sockets": [K.socket("Water", (0, 0, 0.34), parent=w, forward=(0, 0, 1))],
         "collision": [K.ucx_box(a, 0, (1.2, 0.6, 0.4), (0, 0, 0.2))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [trough(seed)]


def extra_checks(A):
    t = A[TR]; h = hornback()
    pin = os.path.join(HERE, "..", "..", "..", "data", "contest", "g03_hornback.quad.json")
    return [("trough ~1.2 m long", abs(t["predicted"]["dimensions"][0] - 1.2) < 0.01, t["predicted"]["dimensions"]),
            ("water is a separate named child node", [o["name"] for o in t["objects"]] == [TR, TR + "_Water"] and t["objects"][1]["parent"] == TR, ""),
            ("water node holds only the water material", {p["slot"] for p in t["objects"][1]["parts"]} == {2}, ""),
            ("SOCKET_Water on the water node", t["sockets"][0]["parent"] == TR + "_Water", ""),
            ("trough materials opaque (no masked/translucent)", all("alpha" not in m for m in t["materials"]), ""),
            ("hornback pinned recipe matches", os.path.exists(pin) and json.load(open(pin, encoding="utf-8")) == h, pin),
            ("hornback 1.5-1.7 m, <= 6000 tris, 3 clips", 1.5 <= h["predicted"]["dimensions"][1] <= 1.7 and h["predicted"]["triangles"] <= 6000 and sorted(h["clips"]) == ["Idle", "Run", "Walk"], h["predicted"])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    q = os.path.join(os.path.dirname(os.path.abspath(o.out)), "g03_hornback.quad.json")
    with open(q, "w", encoding="utf-8", newline="\n") as f:
        json.dump(hornback(o.seed), f, indent=1); f.write("\n")
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
