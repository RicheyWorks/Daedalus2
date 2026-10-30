# SPDX-License-Identifier: MIT
"""Contest row 8, second half (G03 calm route; buffffff 48312 / pythagoras G03), blender-kit/v1.
Prop_Lab_PassageMarker  1.2 m calm-route marker: seeded stone cairn base, wooden post with a pale calm-blue band, and an arrow
    board pointing front (Blender -Y; turn it with actor yaw). UCX box. No sockets (row 8's SOCKET_Water is the trough's).
REUSE check: Prop_Island_Cairn_K*V* are ~0.5 m stone piles with no post (too low for a 1.2 m route marker); the trough half of
row 8 already shipped as Prop_Lab_HornbackTrough_Wood. -> new.
Usage: python lab_marker.py --out data/contest/lab_marker.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 303
MK = "Prop_Lab_PassageMarker"
CAPS = {MK: 3000}
SOCKETS = {MK: []}


def marker(seed=SEED):
    a = MK; r = K.rng(seed, a)
    mats = [K.material(a, 0, "cairn stone", "7D786F", 0.95), K.material(a, 1, "post wood", "7A5232", 0.9), K.material(a, 2, "calm blue paint", "8FC3D9", 0.7)]
    P = []
    for i in range(7):                                         # cairn base: seeded stones in two rings + a cap stone
        ring = 0 if i < 5 else 1; n = 5 if ring == 0 else 2
        ang = 2 * math.pi * (i if ring == 0 else i - 5) / n + r.uniform(-0.2, 0.2); rad = 0.17 if ring == 0 else 0.07
        s = r.uniform(0.15, 0.22) if ring == 0 else r.uniform(0.13, 0.17)
        P.append(K.box("Stone%d" % i, (s, s * 0.9, s * 0.6), (round(rad * math.cos(ang), 5), round(rad * math.sin(ang), 5), round(s * 0.3 + 0.12 * ring, 5)), 0,
                       rot=(0, 0, round(r.uniform(0, 90), 3)), lod1={"drop": i in (1, 3, 5, 6)}))
    P += [K.box("Post", (0.09, 0.09, 1.0), (0, 0, 0.7), 1), K.box("Band", (0.1, 0.1, 0.12), (0, 0, 0.95), 2, bevel=False),
          K.box("Arrow", (0.07, 0.36, 0.14), (0, -0.14, 1.1), 1), K.box("ArrowTipL", (0.07, 0.14, 0.04), (0, -0.33, 1.13), 2, rot=(-35, 0, 0), bevel=False),
          K.box("ArrowTipR", (0.07, 0.14, 0.04), (0, -0.33, 1.07), 2, rot=(35, 0, 0), bevel=False), K.box("Cap", (0.12, 0.12, 0.03), (0, 0, 1.2 - 0.015), 1, bevel=False, lod1={"drop": True})]
    m = {"off_centre_ok": "the arrow points along -Y from the post; origin stays at the post base", "asset": a, "kind": "Prop", "seed": seed, "spec": {"row": 8, "gap": "G03", "size_m": "marker 1.2 m", "tri_cap": 3000, "lod": "LOD0/1", "collision": "UCX box"},
         "materials": mats, "objects": [K.obj(a, P)], "sockets": [], "collision": [K.ucx_box(a, 0, (0.5, 0.5, 0.3), (0, 0, 0.15)), K.ucx_box(a, 1, (0.12, 0.12, 0.9), (0, 0, 0.75))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [marker(seed)]


def extra_checks(A):
    m = A[MK]
    return [("marker 1.2 m tall", abs(m["predicted"]["dimensions"][2] - 1.2) < 0.005, m["predicted"]["dimensions"]),
            ("marker arrow points front (-Y)", m["predicted"]["bounds_min"][1] < -0.35)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
