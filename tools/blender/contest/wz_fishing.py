# SPDX-License-Identifier: MIT
"""Contest row 1-2 (G07 sky-island fishing; BOARD\\BLENDER-ASKS-CONTEST-20261019.md, buffffff 48312), blender-kit/v1.
Tool_WZ_FishingRod: 1.8 m, upright (butt at z=0, tip at z=1.8), 3 cm grip, reel and guides on the front (-Y) side;
  sockets Grip/Tip/Reel; UCX convex 8-sided prism on the grip (a capsule would be UCP_); LOD1 drops guides, fewer sides.
Prop_WZ_FishingFloat_Rest / _Dip: 8 cm bobber, two state assets with the same pivot (bottom centre) and SOCKET_Line;
  Dip is the Rest float tilted 30 deg forward about the pivot; USP_ sphere collision; LOD0 only.
Usage: python wz_fishing.py [--seed N] --out data/contest/wz_fishing.kit.json"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 707
ROD = "Tool_WZ_FishingRod"; FLOAT = "Prop_WZ_FishingFloat"
SPEC_ROD = {"row": 1, "gap": "G07", "size_m": "1.8 m long, grip 3 cm", "tri_cap": 2000, "lod": "LOD0/1", "collision": "UCX capsule on grip",
            "sockets": ["Grip", "Tip", "Reel"]}
SPEC_FLOAT = {"row": 2, "gap": "G07", "size_m": "8 cm dia", "tri_cap": 400, "lod": "LOD0 only", "collision": "sphere", "sockets": ["Line"],
              "states": ["Rest", "Dip"]}


def rod(seed=SEED):
    r = K.rng(seed, ROD); a = ROD
    mats = [K.material(a, 0, "dark", "4A4D57", 0.6), K.material(a, 1, "wood", "9A6B3F", 0.9), K.material(a, 2, "steel", "C9D4E0", 0.5, 0.6)]
    P = [K.cyl("ButtCap", "z", 0.017, 0.017, 0.02, (0, 0, 0.01), 2, 8),
         K.cyl("Grip", "z", 0.015, 0.015, 0.30, (0, 0, 0.17), 1, 12, lod1={"segments": 8}),
         K.cyl("ReelSeat", "z", 0.011, 0.011, 0.10, (0, 0, 0.37), 2, 8, lod1={"segments": 6}),
         K.cyl("ForeGrip", "z", 0.013, 0.013, 0.08, (0, 0, 0.46), 1, 12, lod1={"segments": 8})]
    z0, z1, rads = 0.50, 1.79, [0.009, 0.0072, 0.0054, 0.0036, 0.0022]
    L = (z1 - z0) / 4
    for i in range(4):
        P.append(K.cyl("Blank%d" % i, "z", rads[i], rads[i + 1], L, (0, 0, z0 + L * (i + 0.5)), 0, 8, lod1={"segments": 6}))
    P.append(K.cyl("TipTop", "z", 0.003, 0.003, 0.01, (0, 0, 1.795), 2, 6, lod1={"drop": True}))
    P += [K.cyl("ReelBody", "x", 0.035, 0.035, 0.03, (0, -0.045, 0.37), 2, 12, lod1={"segments": 8}),
          K.box("ReelFoot", (0.012, 0.03, 0.02), (0, -0.02, 0.37), 2),
          K.box("ReelHandle", (0.04, 0.008, 0.008), (0.035, -0.045, 0.37), 0, lod1={"drop": True})]
    z = 0.62
    for i in range(6):                                   # guides, seeded spacing jitter, shrinking toward the tip
        z += 0.17 + r.uniform(-0.015, 0.015) - i * 0.006
        P.append(K.box("Guide%d" % i, (0.006, 0.02 - i * 0.002, 0.006), (0, -0.012 + i * 0.0008, round(z, 4)), 2, lod1={"drop": True}))
    m = {"asset": a, "kind": "Tool", "seed": seed, "spec": SPEC_ROD, "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Grip", (0, 0, 0.17), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0))), K.socket("Tip", (0, 0, 1.8), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0))), K.socket("Reel", (0, -0.045, 0.37))],
         "collision": [K.ucx_prism(a, 0, "z", 0.016, 0.30, (0, 0, 0.17))]}
    return K.finish(m)


def float_state(state, seed=SEED):
    a = "%s_%s" % (FLOAT, state); tilt = (30, 0, 0) if state == "Dip" else None   # forward (-Y) tip-over about the pivot
    mats = [K.material(a, 0, "white", "F8F8F8", 0.7), K.material(a, 1, "red", "D82800", 0.7), K.material(a, 2, "orange", "F87818", 0.6)]
    P = [K.lathe("Lower", [(0.004, 0.0), (0.025, 0.012), (0.04, 0.035)], (0, 0, 0), 0, 16, True, False),
         K.lathe("Upper", [(0.04, 0.035), (0.035, 0.05), (0.012, 0.065), (0.004, 0.07)], (0, 0, 0), 1, 16, False, True),
         K.cyl("Antenna", "z", 0.003, 0.003, 0.05, (0, 0, 0.095), 2, 8),
         K.box("Eye", (0.006, 0.006, 0.006), (0, 0, 0.003), 2, bevel=False)]
    sock, col = [0, 0, 0.003], [0, 0, 0.035]
    if tilt:   # rotate everything about the pivot, then lift so the tilted float still stands on z=0
        M = K.rot_matrix(tilt); rot = lambda c: [sum(M[i][k] * c[k] for k in range(3)) for i in range(3)]
        for p in P:
            p["centre"] = rot(p["centre"]); p["rot"] = list(tilt)
        sock, col = rot(sock), rot(col)
        dz = -K.bounds(P)[0][2]
        for p in P:
            p["centre"] = [round(p["centre"][0], 5), round(p["centre"][1], 5), round(p["centre"][2] + dz, 5)]
        sock = [sock[0], sock[1], sock[2] + dz]; col = [col[0], col[1], col[2] + dz]
    m = {"asset": a, "kind": "Prop", "seed": seed, "state": state, "state_of": FLOAT, "spec": SPEC_FLOAT, "materials": mats,
         "objects": [K.obj(a, P)], "sockets": [K.socket("Line", sock, forward=(0, 0, -1))],
         "collision": [K.usp_sphere(a, 0, 0.04, col)], "lod1": False}
    return K.finish(m)


def assets(seed=SEED):
    return [rod(seed), float_state("Rest", seed), float_state("Dip", seed)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["dimensions"])
