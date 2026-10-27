# SPDX-License-Identifier: MIT
"""Prismheart arcade batch b (blender-team, 2026-10-26b, Richey order relayed by buffffff). Companion to arcade_prism_props.py.
  Facet states   MI param manifest per facet (Prop_Prism_ShardFacet_<E>): MI_..._Cracked / _Charged / _Dormant on the SAME mesh
                 (no new meshes): params Tint, Emissive, EmissivePulseHz, CrackAmount, Desaturate + shared T_Prism_Facet_CrackMask.
  Prop_Prism_HeartSphere_Pedestal  stepped stone pedestal; SOCKET_Sphere (= HeartSphere SOCKET_Base), SOCKET_Rune_0..5, UCX.
  Accessories (blender-kit/v1, modular, sockets):
    Prop_Arcade_CoinCup        SOCKET_Coins, SOCKET_Mount (clips to cab SOCKET_CoinSlot)
    Prop_Arcade_TicketSpool    SOCKET_Axle, SOCKET_Mount;  Prop_Arcade_TicketDispenser  SOCKET_Spool, SOCKET_TicketOut, SOCKET_Mount
    Prop_Arcade_Stool          SOCKET_Seat, SOCKET_Floor (place at cab SOCKET_Player1)
    Prop_Arcade_ControlPanel   SOCKET_Stick, SOCKET_Button_0..5, SOCKET_Start, SOCKET_Mount (cab control deck)
    Prop_Arcade_Joystick       SOCKET_Base (-> panel SOCKET_Stick), SOCKET_Grip;  Prop_Arcade_Button  SOCKET_Base, SOCKET_Press
  Marquees (decalkit, daedalus.decal/v1): Decal_Arcade_Marquee_Prismheart / _Shardring / _Waystone, 70 x 20 cm, project onto
    cab SOCKET_Marquee; attract mode = MI params ScrollSpeed / FlashHz / GlowPower.
Usage: python arcade_prism_props_b.py --kit data/contest/arcade_prism_b.kit.json --out <staging dir>   (then build_kit.py on the kit)"""
import argparse, hashlib, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("kit", "decals"):
    sys.path.insert(0, os.path.join(HERE, d))
import kitlib as K
import decalkit as DK

SEED = 2610262
ELEMENTS = {"Fire": "FF6B2E", "Tide": "338CFF", "Gale": "73F28C", "Stone": "BF8C59", "Light": "FFF299", "Shade": "7340B2"}
STONE, STONE_D, PRISM, GOLD, CAB, CHROME, RED, BLUE, YEL, BLACK, PAPER = ("B8B3AD", "807A78", "A6E6FF", "F2C740", "2A2240", "C8CCD4",
    "E63333", "3373F2", "FAD933", "141418", "F2E8D0")
SPEC = {"gap": "ARCADE-B", "ask": "buffffff (Richey order) 2026-10-26", "lod": "LOD0/1", "realm": "prismheart_realm arcade_plaza"}


def A(a, parts, mats, socks, ucx, size):
    return K.finish({"asset": a, "kind": "Prop", "seed": SEED, "spec": dict(SPEC, size_m=size, tri_cap=4000, sockets=[s["name"] for s in socks]),
                     "materials": [K.material(a, i, *m) for i, m in enumerate(mats)], "objects": [K.obj(a, parts)], "sockets": socks, "collision": ucx, "nanite": True})


def pedestal():
    a = "Prop_Prism_HeartSphere_Pedestal"; P = []; S = []
    for i, (r, h, z) in enumerate(((0.75, 0.15, 0.0), (0.62, 0.15, 0.15), (0.5, 0.35, 0.3))):
        P.append(K.cyl("Step%d" % i, "z", r, r, h, (0, 0, z + h / 2), i % 2, 12))
    P.append(K.cyl("Collar", "z", 0.36, 0.42, 0.08, (0, 0, 0.69), 2, 12))
    for k in range(6):
        an = k * math.pi / 3; x, y = 0.505 * math.cos(an), 0.505 * math.sin(an)
        P.append(K.box("Rune%d" % k, (0.1, 0.02, 0.16), (x, y, 0.47), 3, rot=(0, 0, math.degrees(an) + 90), bevel=False)); S.append(K.socket("Rune_%d" % k, (x, y, 0.47)))
    S.insert(0, K.socket("Sphere", (0, 0, 0.73)))
    return A(a, P, [("stone", STONE, 0.9), ("dark stone", STONE_D, 0.9), ("gold collar", GOLD, 0.3, 0.9), ("rune glow (element colour = MI)", PRISM, 0.4, 0.0, True)],
             S, [K.ucx_prism(a, 0, "z", 0.75, 0.73, (0, 0, 0.365))], "1.5 m dia x 0.73 m; HeartSphere SOCKET_Base -> SOCKET_Sphere")


def coin_cup():
    a = "Prop_Arcade_CoinCup"
    return A(a, [K.box("Back", (0.12, 0.01, 0.1), (0, 0.045, 0.05), 0), K.box("Cup", (0.12, 0.08, 0.01), (0, 0.005, 0.005), 0),
                 K.box("Lip", (0.12, 0.01, 0.04), (0, -0.035, 0.02), 0), K.cyl("Coin", "z", 0.012, 0.012, 0.003, (0.02, 0.0, 0.012), 1, 10)],
             [("chrome", CHROME, 0.3, 0.9), ("brass coin", GOLD, 0.3, 0.9)], [K.socket("Coins", (0, 0, 0.012)), K.socket("Mount", (0, 0.05, 0.08))], [], "12 x 9 x 10 cm")


def ticket_spool():
    a = "Prop_Arcade_TicketSpool"
    return A(a, [K.cyl("Roll", "x", 0.07, 0.07, 0.06, (0, 0, 0.07), 0, 16), K.cyl("Core", "x", 0.02, 0.02, 0.07, (0, 0, 0.07), 1, 8),
                 K.box("Tail", (0.05, 0.002, 0.1), (0, -0.07, 0.02), 0, bevel=False)],
             [("ticket paper (print = MI)", "F28C8C", 0.8), ("card core", PAPER, 0.8)], [K.socket("Axle", (0, 0, 0.07)), K.socket("Mount", (0, 0, 0.07))], [], "14 cm roll")


def ticket_dispenser():
    a = "Prop_Arcade_TicketDispenser"
    return A(a, [K.box("Body", (0.14, 0.18, 0.2), (0, 0, 0.1), 0), K.box("Slot", (0.07, 0.01, 0.01), (0, -0.091, 0.04), 1, bevel=False),
                 K.box("Window", (0.1, 0.005, 0.08), (0, -0.0905, 0.13), 2, bevel=False)],
             [("dispenser shell", CAB, 0.5), ("slot", BLACK, 0.6), ("window", PRISM, 0.1)],
             [K.socket("Spool", (0, 0.0, 0.11)), K.socket("TicketOut", (0, -0.095, 0.04)), K.socket("Mount", (0, 0.09, 0.1))], [K.ucx_box(a, 0, (0.14, 0.18, 0.2), (0, 0, 0.1))], "14 x 18 x 20 cm")


def stool():
    a = "Prop_Arcade_Stool"; P = [K.cyl("Seat", "z", 0.18, 0.18, 0.08, (0, 0, 0.66), 0, 16), K.cyl("Post", "z", 0.03, 0.03, 0.58, (0, 0, 0.33), 1, 8),
        K.cyl("Ring", "z", 0.16, 0.16, 0.02, (0, 0, 0.25), 1, 12), K.cyl("Foot", "z", 0.22, 0.24, 0.04, (0, 0, 0.02), 1, 12)]
    return A(a, P, [("vinyl seat (cab colour = MI)", "8A2BE2", 0.6), ("chrome", CHROME, 0.3, 0.9)], [K.socket("Seat", (0, 0, 0.7)), K.socket("Floor", (0, 0, 0))],
             [K.ucx_prism(a, 0, "z", 0.24, 0.7, (0, 0, 0.35))], "0.48 m dia x 0.7 m")


BTN = [(-0.06, 0.03), (0.0, 0.035), (0.06, 0.03), (-0.06, -0.03), (0.0, -0.025), (0.06, -0.03)]


def panel():
    a = "Prop_Arcade_ControlPanel"; P = [K.box("Deck", (0.6, 0.25, 0.03), (0, 0, 0.015), 0), K.box("Trim", (0.62, 0.02, 0.05), (0, -0.125, 0.0), 1)]
    S = [K.socket("Stick", (-0.17, 0, 0.03))]
    for i, (x, y) in enumerate(BTN):
        S.append(K.socket("Button_%d" % i, (0.12 + x, y, 0.03)))
    S += [K.socket("Start", (0.0, 0.09, 0.03)), K.socket("Mount", (0, 0.125, 0.0))]
    return A(a, P, [("deck (art = MI)", CAB, 0.5), ("T-molding", PRISM, 0.4)], S, [K.ucx_box(a, 0, (0.62, 0.25, 0.05), (0, 0, 0.0))], "60 x 25 cm; modular: Joystick at SOCKET_Stick, Button at SOCKET_Button_k/Start")


def joystick():
    a = "Prop_Arcade_Joystick"
    return A(a, [K.cyl("Dust", "z", 0.03, 0.03, 0.004, (0, 0, 0.002), 1, 12), K.cyl("Shaft", "z", 0.006, 0.006, 0.06, (0, 0, 0.03), 1, 8),
                 K.lathe("Ball", [(0.0, -0.018), (0.014, -0.012), (0.018, 0.0), (0.014, 0.012), (0.0, 0.018)], (0, 0, 0.075), 0, segments=12)],
             [("ball top (colour = MI)", RED, 0.4), ("shaft", BLACK, 0.5)], [K.socket("Base", (0, 0, 0)), K.socket("Grip", (0, 0, 0.075))], [], "3.6 cm ball, 9 cm tall; tilt about SOCKET_Base")


def button():
    a = "Prop_Arcade_Button"
    return A(a, [K.cyl("Bezel", "z", 0.015, 0.015, 0.006, (0, 0, 0.003), 1, 14), K.cyl("Cap", "z", 0.012, 0.011, 0.008, (0, 0, 0.01), 0, 14)],
             [("cap (colour = MI: red/blue/yellow)", BLUE, 0.4), ("bezel", BLACK, 0.5)], [K.socket("Base", (0, 0, 0)), K.socket("Press", (0, 0, 0.014))], [], "3 cm; press travels -Z 4 mm")


def assets():
    return [pedestal(), coin_cup(), ticket_spool(), ticket_dispenser(), stool(), panel(), joystick(), button()]


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 6) for v in c] + [1.0]


def facet_states(out, w=256):
    from PIL import Image
    os.makedirs(out, exist_ok=True); rng = np.random.default_rng(SEED)
    f1, f2, _ = DK.voronoi(rng, w, w, 40); crack = np.clip(1 - (f2 - f1) / 3.0, 0, 1)                 # thin lines on cell edges
    fn = "T_Prism_Facet_CrackMask.png"; Image.fromarray(np.round(crack * 255).astype(np.uint8), "L").save(os.path.join(out, fn), optimize=True)
    sha = hashlib.sha256(open(os.path.join(out, fn), "rb").read()).hexdigest()
    STATES = {"Cracked": {"CrackAmount": 1.0, "Emissive": 0.2, "EmissivePulseHz": 0.0, "Desaturate": 0.35},
              "Charged": {"CrackAmount": 0.0, "Emissive": 6.0, "EmissivePulseHz": 1.5, "Desaturate": 0.0},
              "Dormant": {"CrackAmount": 0.0, "Emissive": 0.0, "EmissivePulseHz": 0.0, "Desaturate": 0.7}}
    mans = []
    for e, hx in ELEMENTS.items():
        a = "Prop_Prism_ShardFacet_" + e
        inst = {"MI_%s_%s" % (a, s): {"state": s, "params": dict(v, Tint={"srgb_hex": hx, "linear_rgba": lin(hx)}, CrackMask=fn)} for s, v in STATES.items()}
        man = {"schema": "bb-material-variants/1", "asset": a, "status": "NOT READY", "slot": 0, "new_meshes": False,
               "parent_material": {"name": "M_PrismFacet (UE side)", "graph": "BaseColor = lerp(Tint, grey(Tint), Desaturate) * (1 - CrackMask*CrackAmount*0.8); Emissive = Tint * Emissive * (0.6 + 0.4 * sin(2pi*EmissivePulseHz*t)) + CrackMask*CrackAmount*Tint*2"},
               "mask": {"file": fn, "sha256": sha, "projection": "triplanar in local space (voxel facet carries no UVs)"},
               "hook": "game state -> MI swap: Dormant (inactive) / Charged (resonating) / Cracked (failed)", "instances": inst}
        with open(os.path.join(out, a + ".states.material_variants.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, indent=1); f.write("\n")
        mans.append(man)
    return mans


MARQUEES = {"Prismheart": ("2A1E52", "A6E6FF", "E6B3FF"), "Shardring": ("10303D", "73F2D9", "FFF299"), "Waystone": ("33302B", "FFE68C", "F28C40")}


def marquees(out, wpx=700, hpx=200):
    res = []
    for nm, (bg, c1, c2) in MARQUEES.items():
        a = "Decal_Arcade_Marquee_" + nm; rng = np.random.default_rng(SEED + len(nm))
        y, x = np.mgrid[0:hpx, 0:wpx][0] / hpx, np.mgrid[0:hpx, 0:wpx][1] / wpx
        rgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)
        col = np.ones((hpx, wpx, 3)) * rgb(bg); g = DK.vnoise(rng, hpx, wpx, 3, 10)
        col = col * (0.75 + 0.5 * g[..., None] * (1 - y[..., None]))
        hgt = np.zeros((hpx, wpx))
        for k in range(5):                                     # gem row: diamond shapes (attract mode lights them in turn: SlotCount 5)
            cx = 0.15 + 0.175 * k; d = np.abs(x - cx) * 3.5 + np.abs(y - 0.5)
            m = d < 0.32; col[m] = rgb(c1 if k % 2 == 0 else c2) * (1.1 - d[m, None]); hgt += np.clip(0.32 - d, 0, None)
        band = (np.abs(y - 0.1) < 0.03) | (np.abs(y - 0.9) < 0.03); col[band] = rgb(c2); hgt[band] += 0.05
        mask = np.ones((hpx, wpx))                             # full-rectangle marquee
        n = DK.normals(hgt, 2.0, 70.0, 20.0); d = os.path.join(out, a)
        files, sha = DK.write_textures(d, a, np.clip(col, 0, 255), n, mask)
        man = DK.manifest(a, SEED, "tools/blender/arcade_prism_props_b.py", files, sha, wpx, hpx, [70.0, 20.0], 5.0, "M_Decal_ArcadeMarquee", 0.4,
                          "project onto Prop_Arcade_Cab_* SOCKET_Marquee (cab front -Y), size 70 x 20 cm, depth 5 cm",
                          extra_params={"ScrollSpeed": 0.25, "FlashHz": 2.0, "GlowPower": 4.0, "SlotCount": 5, "AttractMode": "gems light in turn at FlashHz; band scrolls at ScrollSpeed"})
        DK.write_manifest(d, man); res.append(a)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    M = assets(); K.write(M, o.kit)
    for m in M: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
    print("facet MIs", len(facet_states(os.path.join(o.out, "facet_states"))), "manifests"); print("marquees", marquees(os.path.join(o.out, "decals")))
