# SPDX-License-Identifier: MIT
"""Contest row 3 (G06 hatching; BOARD\\BLENDER-ASKS-CONTEST-20261019.md, buffffff 48312), blender-kit/v1.
Prop_WZ_EggNest: warm 0.6 m nest (straw bowl + seeded twig ring + leaves), holds 1 egg: SOCKET_Egg in the bowl, SOCKET_Glow above.
Prop_WZ_EggIncubator: 0.8 m lantern incubator (wood frame, glass panes, straw cushion, pyramid roof) with the lamp as a
  separate child node Prop_WZ_EggIncubator_Lamp (glowing, so Unreal can drive it); SOCKET_Egg on the cushion, SOCKET_Glow at the lamp.
Both: UCX box, LOD1 ~50%. REUSE check: Daedalus2 tools/blender/voxel_eggs.py only fuses a small nest under each Prop_Egg_*
  (no standalone nest/incubator, no sockets, no UCX), so these are new.
Usage: python wz_eggs.py [--seed N] --out data/contest/wz_eggs.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 606
NEST, INC = "Prop_WZ_EggNest", "Prop_WZ_EggIncubator"
SPEC = {"row": 3, "gap": "G06", "size_m": "nest 0.6 m; incubator 0.8 m tall", "tri_cap": 3000, "lod": "LOD0/1", "collision": "UCX box",
        "sockets": ["Egg", "Glow"], "holds": "1 egg"}


def nest(seed=SEED):
    r = K.rng(seed, NEST); a = NEST
    mats = [K.material(a, 0, "sand", "E2D08C", 0.95), K.material(a, 1, "log", "7A5232", 0.9), K.material(a, 2, "leaves", "4AA44F", 0.9)]
    P = [K.lathe("Bowl", [(0.14, 0.0), (0.22, 0.03), (0.25, 0.08), (0.2, 0.11), (0.15, 0.07)], (0, 0, 0), 0, 16, True, False, lod1={"segments": 8})]
    n = 18
    for i in range(n):                                   # twig ring: tangent boxes, seeded jitter in angle, height and tilt
        ang = 2 * math.pi * i / n + r.uniform(-0.08, 0.08); rad = 0.235
        z = 0.06 + r.uniform(0, 0.06); tilt = r.uniform(-12, 12)
        P.append(K.box("Twig%02d" % i, (0.16, 0.025, 0.025), (rad * math.cos(ang), rad * math.sin(ang), z), 1,
                       rot=(tilt, 0, math.degrees(ang) + 90), lod1={"drop": True} if i % 2 else None))
    for i in range(5):                                   # a few leaves tucked in the rim
        ang = 2 * math.pi * (i + 0.5) / 5 + r.uniform(-0.2, 0.2)
        P.append(K.box("Leaf%d" % i, (0.08, 0.04, 0.008), (0.2 * math.cos(ang), 0.2 * math.sin(ang), 0.12), 2,
                       rot=(0, r.uniform(-20, 20), math.degrees(ang)), lod1={"drop": True}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC, "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Egg", (0, 0, 0.07), forward=(0, 0, 1)), K.socket("Glow", (0, 0, 0.35), forward=(0, 0, -1))]}
    K.finish(m)
    lo, hi = m["predicted"]["bounds_min"], m["predicted"]["bounds_max"]
    m["collision"] = [K.ucx_box(a, 0, [hi[i] - lo[i] for i in range(3)], [(hi[i] + lo[i]) / 2 for i in range(3)])]
    return K.finish(m)


def incubator(seed=SEED):
    a = INC; lamp = a + "_Lamp"
    mats = [K.material(a, 0, "wood", "9A6B3F", 0.85), K.material(a, 1, "glass", "A8D8E8", 0.2), K.material(a, 2, "sand", "E2D08C", 0.95),
            K.material(a, 3, "orange", "F87818", 0.5, glow=True), K.material(a, 4, "steel", "C9D4E0", 0.5, 0.6)]
    P = [K.box("Base", (0.5, 0.5, 0.12), (0, 0, 0.06), 0)]
    for i, (x, y) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        P.append(K.box("Post%d" % i, (0.05, 0.05, 0.5), (0.215 * x, 0.215 * y, 0.37), 0, lod1={"drop": True}))
    for i, (x, y, sx, sy) in enumerate([(0, -0.215, 0.38, 0.01), (0, 0.215, 0.38, 0.01), (-0.215, 0, 0.01, 0.38), (0.215, 0, 0.01, 0.38)]):
        P.append(K.box("Pane%d" % i, (sx, sy, 0.46), (x, y, 0.37), 1, bevel=False))
    P += [K.box("Cushion", (0.3, 0.3, 0.05), (0, 0, 0.145), 2),
          K.box("TopRail", (0.5, 0.5, 0.04), (0, 0, 0.64), 0, lod1={"drop": True}),
          K.lathe("Roof", [(0.37, 0.62), (0.02, 0.8)], (0, 0, 0), 0, 4, True, True, rot=(0, 0, 45))]
    L = [K.cyl("Bulb", "z", 0.05, 0.05, 0.08, (0, 0, 0.53), 3, 12, lod1={"segments": 6}),
         K.cyl("Cap", "z", 0.03, 0.03, 0.04, (0, 0, 0.59), 4, 8, lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": SPEC, "materials": mats,
         "objects": [K.obj(a, P), K.obj(lamp, L, parent=a, pivot=(0, 0, 0.59), role="lamp (glow; Unreal drives it)")],
         "sockets": [K.socket("Egg", (0, 0, 0.17), forward=(0, 0, 1)), K.socket("Glow", (0, 0, 0.53), parent=lamp, forward=(0, 0, -1))],
         "collision": [K.ucx_box(a, 0, (0.5, 0.5, 0.8), (0, 0, 0.4))]}
    return K.finish(m)


def assets(seed=SEED):
    return [nest(seed), incubator(seed)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
