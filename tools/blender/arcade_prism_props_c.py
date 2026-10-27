# SPDX-License-Identifier: MIT
"""Prismheart arcade batch c (blender-team, 2026-10-26c, Richey "next" via buffffff). Same conventions as arcade_prism_props_b.py.
  Prop_Arcade_PrizeCounter     glass-front counter + back shelf: SOCKET_Prize_0..8 (shelf), SOCKET_Clerk, SOCKET_Customer, SOCKET_Till
  Prop_Arcade_Plush_Shardling / _Waystoad / _Glimmermoth   low-poly plush prizes (original critters), SOCKET_Shelf (base), SOCKET_Hand
  Prop_Arcade_FloorTile_Starfield / _Checker / _PrismRay   2 x 2 m tiles, tile edges match (SOCKET_TileE/TileN), carpet colours on slots
  Prop_Arcade_TokenMachine     change machine: SOCKET_CoinIn, SOCKET_TokenOut, SOCKET_Screen, SOCKET_Floor
  Prop_Arcade_Cab_ClawCrane    claw cab with a separate claw node: SOCKET_ClawRail (gantry origin, X/Y travel in spec), SOCKET_Claw,
                               SOCKET_PrizeChute, SOCKET_PrizePit_0..5, SOCKET_Floor, SOCKET_Player1, SOCKET_CoinSlot
  Decal_Arcade_Neon_Arcade / _Prize / _Prism   neon wall signs (decalkit, emissive GlowPower/FlickerHz MI params), 120 x 40 cm
Usage: python arcade_prism_props_c.py --kit data/contest/arcade_prism_c.kit.json --out <staging dir>"""
import argparse, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arcade_prism_props_b as AB
K, DK, A = AB.K, AB.DK, AB.A
CAB, CHROME, PRISM, GOLD, BLACK, RED, BLUE, YEL = AB.CAB, AB.CHROME, AB.PRISM, AB.GOLD, AB.BLACK, AB.RED, AB.BLUE, AB.YEL
GLASSC = "B8E0F0"
SEED = 2610263


def prize_counter():
    a = "Prop_Arcade_PrizeCounter"; W = 2.4
    P = [K.box("Base", (W, 0.6, 0.9), (0, -0.6, 0.45), 0), K.box("Glass", (W - 0.1, 0.02, 0.7), (0, -0.91, 0.5), 2, bevel=False), K.box("Top", (W + 0.1, 0.65, 0.05), (0, -0.6, 0.925), 1),
         K.box("ShelfBack", (W, 0.05, 2.2), (0, 0.6, 1.1), 0)]
    S = []
    for r in range(3):
        z = 1.0 + 0.45 * r; P.append(K.box("Shelf%d" % r, (W, 0.35, 0.03), (0, 0.42, z), 1))
        for c in range(3):
            x = -0.7 + 0.7 * c; S.append(K.socket("Prize_%d" % (r * 3 + c), (x, 0.42, z + 0.015)))
    P.append(K.box("Sign", (1.2, 0.04, 0.3), (0, 0.55, 2.35), 3))
    S += [K.socket("Clerk", (0, 0.0, 0)), K.socket("Customer", (0, -1.4, 0)), K.socket("Till", (0.8, -0.6, 0.95)), K.socket("Sign", (0, 0.52, 2.35))]
    return A(a, P, [("counter (cab colour)", CAB, 0.5), ("chrome trim", CHROME, 0.3, 0.9), ("glass", GLASSC, 0.1), ("sign (neon decal target)", PRISM, 0.4, 0.0, True)], S,
             [K.ucx_box(a, 0, (W, 0.6, 0.95), (0, -0.6, 0.475)), K.ucx_box(a, 1, (W, 0.4, 2.2), (0, 0.5, 1.1))], "2.4 x 1.6 x 2.5 m; 9 prize sockets")


def ball(name, c, r, slot, seg=8):
    prof = [(round(r * math.sin(math.pi * k / 4), 4), round(-r * math.cos(math.pi * k / 4), 4)) for k in range(5)]
    return K.lathe(name, prof, c, slot, segments=seg)


def plush(kind):
    a = "Prop_Arcade_Plush_" + kind
    if kind == "Shardling":      # round crystal sprite
        P = [ball("Body", (0, 0, 0.12), 0.12, 0), K.cyl("Crystal", "z", 0.05, 0.0, 0.14, (0, 0, 0.29), 1, 6), ball("EyeL", (0.05, -0.1, 0.15), 0.018, 2, 6), ball("EyeR", (-0.05, -0.1, 0.15), 0.018, 2, 6)]
        mats = [("plush blue", "6AB8F0", 0.95), ("felt crystal", "E0B8FF", 0.9), ("button eyes", BLACK, 0.4)]
    elif kind == "Waystoad":     # squat toad with a rune on its back
        P = [ball("Body", (0, 0, 0.09), 0.1, 0), ball("Head", (0, -0.1, 0.13), 0.07, 0), ball("EyeL", (0.04, -0.14, 0.19), 0.025, 2, 6), ball("EyeR", (-0.04, -0.14, 0.19), 0.025, 2, 6),
             K.box("Rune", (0.06, 0.06, 0.01), (0, 0.02, 0.19), 1, bevel=False)] + [ball("Foot%d" % i, (0.08 * (1 if i % 2 else -1), 0.06 * (1 if i > 1 else -1), 0.025), 0.03, 0, 6) for i in range(4)]
        mats = [("plush moss green", "7AB060", 0.95), ("gold rune", GOLD, 0.6), ("eyes", BLACK, 0.4)]
    else:                         # Glimmermoth
        P = [ball("Body", (0, 0, 0.1), 0.06, 0), ball("Head", (0, -0.08, 0.13), 0.045, 0)]
        for s in (-1, 1):
            P.append(K.slab("Wing%d" % s, [(0, 0), (0.16, -0.04), (0.18, 0.08), (0.04, 0.1)], 0.02, (s * 0.04, 0, 0.12), 1, rot=(0, 0, 0 if s > 0 else 180)))
        mats = [("plush cream", "F0E6D0", 0.95), ("glimmer wings", "F2C0E8", 0.8), ("eyes", BLACK, 0.4)]
    return A(a, P, mats, [K.socket("Shelf", (0, 0, 0)), K.socket("Hand", (0, 0, 0.12)), K.socket("Grab", (0, 0, 0.2))], [], "~25 cm plush prize")


TILES = {"Starfield": ("1A1630", "F2D24A", "6AC8FF"), "Checker": ("2A2240", "D04AA0", "4AD0C8"), "PrismRay": ("101828", "A6E6FF", "E6B3FF")}


def floor_tile(kind):
    a = "Prop_Arcade_FloorTile_" + kind; base, c1, c2 = TILES[kind]; T = 2.0
    P = [K.box("Base", (T, T, 0.02), (0, 0, 0.01), 0, bevel=False)]
    if kind == "Checker":
        for i in range(4):
            for j in range(4):
                if (i + j) % 2 == 0:
                    P.append(K.box("Sq%d%d" % (i, j), (0.5, 0.5, 0.002), (-0.75 + 0.5 * i, -0.75 + 0.5 * j, 0.021), 1 + (i // 2 + j // 2) % 2, bevel=False))
    elif kind == "Starfield":
        r = K.rng(SEED, a)
        for k in range(14):
            x, y = round(r.uniform(-0.9, 0.9), 3), round(r.uniform(-0.9, 0.9), 3); s = round(r.uniform(0.04, 0.1), 3)
            P.append(K.box("Star%d" % k, (s, s, 0.002), (x, y, 0.021), 1 + k % 2, rot=(0, 0, 45), bevel=False))
    else:
        for k in range(6):
            P.append(K.box("Ray%d" % k, (T, 0.08, 0.002), (0, 0, 0.021), 1 + k % 2, rot=(0, 0, 30 * k), bevel=False))
    return A(a, P, [("carpet base", base, 0.95), ("pattern A", c1, 0.9), ("pattern B (UV-glow MI)", c2, 0.9, 0.0, True)],
             [K.socket("TileE", (T, 0, 0)), K.socket("TileN", (0, T, 0)), K.socket("Centre", (0, 0, 0.02))], [K.ucx_box(a, 0, (T, T, 0.02), (0, 0, 0.01))],
             "2 x 2 m tile; patterns stay inside the tile so any rotation/variant tiles edge to edge")


def token_machine():
    a = "Prop_Arcade_TokenMachine"
    P = [K.box("Body", (0.6, 0.5, 1.5), (0, 0, 0.75), 0), K.box("Face", (0.5, 0.02, 0.9), (0, -0.26, 0.95), 1), K.box("Screen", (0.3, 0.01, 0.18), (0, -0.272, 1.25), 2, bevel=False),
         K.box("BillSlot", (0.16, 0.01, 0.02), (0, -0.272, 1.05), 3, bevel=False), K.box("Tray", (0.3, 0.12, 0.08), (0, -0.31, 0.55), 1), K.box("Crown", (0.62, 0.52, 0.12), (0, 0, 1.56), 4)]
    return A(a, P, [("cabinet (cab colour)", CAB, 0.5), ("chrome face", CHROME, 0.3, 0.9), ("screen", "203040", 0.2, 0.0, True), ("slot", BLACK, 0.5), ("crown glow", GOLD, 0.4, 0.0, True)],
             [K.socket("CoinIn", (0, -0.275, 1.05)), K.socket("TokenOut", (0, -0.3, 0.58)), K.socket("Screen", (0, -0.28, 1.25)), K.socket("Floor", (0, 0, 0)), K.socket("Customer", (0, -0.8, 0))],
             [K.ucx_box(a, 0, (0.62, 0.52, 1.62), (0, 0, 0.81))], "0.6 x 0.5 x 1.62 m")


def claw_cab():
    a = "Prop_Arcade_Cab_ClawCrane"; W, D = 0.9, 0.9
    body = [K.box("Base", (W, D, 0.9), (0, 0, 0.45), 0), K.box("Roof", (W, D, 0.3), (0, 0, 2.05), 0), K.box("Marquee", (W, 0.05, 0.25), (0, -D / 2 - 0.02, 2.05), 3)]
    for x in (-W / 2 + 0.03, W / 2 - 0.03):
        for y in (-D / 2 + 0.03, D / 2 - 0.03): body.append(K.box("Pillar%+.2f%+.2f" % (x, y), (0.05, 0.05, 1.0), (x, y, 1.4), 1))
    body += [K.box("GlassF", (W - 0.06, 0.01, 0.98), (0, -D / 2 + 0.01, 1.4), 2, bevel=False), K.box("Pit", (W - 0.1, D - 0.1, 0.04), (0, 0, 0.92), 0),
             K.box("Chute", (0.25, 0.25, 0.3), (0.28, -0.28, 1.05), 1), K.box("Panel", (W, 0.2, 0.05), (0, -D / 2 - 0.08, 0.95), 1), K.box("Rail", (W - 0.1, 0.04, 0.04), (0, 0, 1.86), 1)]
    claw = [K.cyl("Cable", "z", 0.004, 0.004, 0.3, (0, 0, 0.15), 1, 4), K.cyl("Hub", "z", 0.04, 0.03, 0.06, (0, 0, -0.03), 1, 8)]
    for k in range(3):
        an = k * 2 * math.pi / 3; claw.append(K.box("Prong%d" % k, (0.012, 0.012, 0.14), (0.04 * math.cos(an), 0.04 * math.sin(an), -0.12), 1, rot=(math.degrees(0.4 * math.sin(an)), -math.degrees(0.4 * math.cos(an)), 0)))
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Player1", (0, -D / 2 - 0.6, 0)), K.socket("CoinSlot", (0.3, -D / 2 - 0.01, 0.6)), K.socket("ClawRail", (0, 0, 1.84)),
         K.socket("Claw", (0, 0, 1.84), parent="Prop_Arcade_Cab_ClawCrane_Claw"), K.socket("PrizeChute", (0.28, -0.28, 1.2)), K.socket("PrizeOut", (0.28, -D / 2 - 0.02, 0.3)), K.socket("Marquee", (0, -D / 2 - 0.05, 2.05)),
         K.socket("Stick", (-0.15, -D / 2 - 0.08, 0.98)), K.socket("Button", (0.15, -D / 2 - 0.08, 0.98))] + [K.socket("PrizePit_%d" % i, (-0.25 + 0.2 * (i % 3), -0.05 + 0.25 * (i // 3), 0.94)) for i in range(6)]
    m = {"asset": a, "kind": "Prop", "seed": SEED, "spec": dict(AB.SPEC, size_m="0.9 x 0.9 x 2.2 m", tri_cap=5000, claw="child node _Claw at SOCKET_ClawRail; travel X +-0.3 m, Y +-0.3 m, drop 0.8 m (gameplay drives the node)",
                                                              sockets=[s["name"] for s in S]),
         "materials": [K.material(a, i, *mm) for i, mm in enumerate([("cab body", CAB, 0.5), ("chrome", CHROME, 0.3, 0.9), ("glass", GLASSC, 0.1), ("marquee glow", PRISM, 0.4, 0.0, True)])],
         "objects": [K.obj(a, body), K.obj(a + "_Claw", claw, parent=a, pivot=(0, 0, 1.84), role="mover")], "sockets": S,
         "collision": [K.ucx_box(a, 0, (W, D, 2.2), (0, 0, 1.1))], "nanite": True}
    return K.finish(m)


def assets():
    return [prize_counter()] + [plush(k) for k in ("Shardling", "Waystoad", "Glimmermoth")] + [floor_tile(k) for k in TILES] + [token_machine(), claw_cab()]


NEON = {"Arcade": "FF4AD0", "Prize": "FFE04A", "Prism": "6AE8FF"}


def neon_signs(out, wpx=600, hpx=200):
    res = []
    for nm, hx in NEON.items():
        a = "Decal_Arcade_Neon_" + nm; rng = np.random.default_rng(SEED + len(nm)); c = np.array([int(hx[i:i + 2], 16) for i in (0, 2, 4)], float)
        y, x = np.mgrid[0:hpx, 0:wpx][0] / hpx, np.mgrid[0:hpx, 0:wpx][1] / wpx
        d = np.full((hpx, wpx), 1.0)
        def seg(x0, y0, x1, y1):
            nonlocal d
            px, py = x * 3, y; ax, ay, bx, by = x0 * 3, y0, x1 * 3, y1; vx, vy = bx - ax, by - ay
            t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
            d = np.minimum(d, np.hypot(px - ax - t * vx, py - ay - t * vy))
        # border tube + a glyph per sign (original shapes: diamond, star, prism)
        for (x0, y0, x1, y1) in ((0.05, 0.12, 0.95, 0.12), (0.95, 0.12, 0.95, 0.88), (0.95, 0.88, 0.05, 0.88), (0.05, 0.88, 0.05, 0.12)): seg(x0, y0, x1, y1)
        if nm == "Arcade":
            for (x0, y0, x1, y1) in ((0.5, 0.25, 0.62, 0.5), (0.62, 0.5, 0.5, 0.75), (0.5, 0.75, 0.38, 0.5), (0.38, 0.5, 0.5, 0.25)): seg(x0, y0, x1, y1)
        elif nm == "Prize":
            for k in range(5):
                a0, a1 = -math.pi / 2 + k * 4 * math.pi / 5, -math.pi / 2 + (k + 1) * 4 * math.pi / 5
                seg(0.5 + 0.1 * math.cos(a0), 0.5 + 0.3 * math.sin(a0), 0.5 + 0.1 * math.cos(a1), 0.5 + 0.3 * math.sin(a1))
        else:
            for (x0, y0, x1, y1) in ((0.4, 0.75, 0.5, 0.25), (0.5, 0.25, 0.6, 0.75), (0.6, 0.75, 0.4, 0.75), (0.6, 0.5, 0.85, 0.4), (0.6, 0.5, 0.85, 0.55), (0.6, 0.5, 0.85, 0.7)): seg(x0, y0, x1, y1)
        tube = np.clip(1 - d / 0.012, 0, 1); glow = np.clip(1 - d / 0.06, 0, 1) ** 2
        col = np.clip(c[None, None, :] * (glow[..., None] * 0.6) + np.array([255, 255, 255]) * tube[..., None] * 0.7 + c * tube[..., None] * 0.3, 0, 255)
        mask = np.clip(np.maximum(tube, glow * 0.8), 0, 1); hgt = tube * 0.8
        n = DK.normals(hgt, 1.0, 120.0, 40.0); dd = os.path.join(out, a)
        files, sha = DK.write_textures(dd, a, col, n, mask)
        man = DK.manifest(a, SEED, "tools/blender/arcade_prism_props_c.py", files, sha, wpx, hpx, [120.0, 40.0], 5.0, "M_Decal_ArcadeNeon", 0.3,
                          "wall decal, 120 x 40 cm; on Prop_Arcade_PrizeCounter SOCKET_Sign or any arcade wall",
                          extra_params={"GlowPower": 8.0, "FlickerHz": 0.0, "Tint": hx, "Emissive": "BaseColorTex * GlowPower * OpacityTex"})
        DK.write_manifest(dd, man); res.append(a)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    M_ = assets(); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
    print("neon", neon_signs(os.path.join(o.out, "decals")))
