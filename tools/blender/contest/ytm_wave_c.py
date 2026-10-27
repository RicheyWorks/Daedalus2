# SPDX-License-Identifier: MIT
"""youtube-master YTM wave c (G204..G245, asks 54746..54989, 2026-10-26 19:03-20:57 PT), blender-kit/v1, G66 island palette.
Built from reusable part helpers (table, stool, board, boat, stall, pole) shared with backlog_20261026.asset/M. Every asset is
origin bottom-centre, Blender front -Y (place yaw -90), sockets for the Daedalus hook, UCX where it is walk-into furniture.
Sets that are "the same mesh with a different face" (letter tiles a-z, flag cloths, shells' tints) are one mesh + an MI list in
the kit spec (spec.mi_set), not 26 meshes.
Usage: python ytm_wave_c.py --gap G204 --out data/contest/ytm_c_g204.kit.json      (--list prints the gaps)"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
from backlog_20261026 import M, asset, TIMBER, SIGN, CLOTH, IRON, STONE, EMBER, GLASS, SAND, ROPE, PAPER, BRASS

ASK = {"G204": 54746, "G209": 54769, "G212": 54789, "G215": 54811, "G219": 54835, "G223": 54854, "G226": 54871, "G229": 54900,
       "G232": 54913, "G235": 54930, "G238": 54947, "G242": 54971, "G245": 54989}
CLOTH4 = CLOTH + [CLOTH[0]] * max(0, 4 - len(CLOTH))
WATER_W = "D8D0B8"


def Y(g):
    return (g, "youtube-master %d" % ASK[g])


def legs4(P, w, d, h, slot=0, t=0.07):
    for x in (-w / 2 + t / 2, w / 2 - t / 2):
        for y in (-d / 2 + t / 2, d / 2 - t / 2):
            P.append(K.box("Leg%+.2f%+.2f" % (x, y), (t, t, h), (x, y, h / 2), slot))


def table(a, g, w, d, h, places=0, extra=None, note=""):
    P = [K.box("Top", (w, d, 0.05), (0, 0, h - 0.025), 0)]; legs4(P, w - 0.1, d - 0.1, h - 0.05)
    S = [K.socket("Top", (0, 0, h))]
    for i in range(places):
        x = -w / 2 + w * (i // 2 + 0.5) / max(1, places // 2); S.append(K.socket("Place_%d" % i, (x, (-1 if i % 2 == 0 else 1) * (d / 2 + 0.3), 0)))
    P += extra or []
    return asset(a, *Y(g), P, [M(a, 0, "timber (G66)", TIMBER), M(a, 1, "cloth (G66)", CLOTH4[1]), M(a, 2, "detail", SIGN)], S, [K.ucx_box(a, 0, (w, d, h), (0, 0, h / 2))], "%.1f x %.1f x %.2f m %s" % (w, d, h, note))


def stool(a, g, h=0.45):
    P = [K.box("Seat", (0.36, 0.3, 0.05), (0, 0, h - 0.025), 0)]; legs4(P, 0.3, 0.24, h - 0.05, t=0.05)
    return asset(a, *Y(g), P, [M(a, 0, "timber (G66)", TIMBER)], [K.socket("Seat", (0, 0, h))], [K.ucx_box(a, 0, (0.36, 0.3, h), (0, 0, h / 2))], "0.36 x 0.3 x %.2f m" % h)


def board(a, g, w, h, z0, slots, prefix, slot_col=None, legs=True, note=""):
    P = [K.box("Board", (w, 0.05, h), (0, 0, z0 + h / 2), 1)]
    if legs:
        for s in (-1, 1): P.append(K.box("Post%d" % s, (0.07, 0.07, z0 + h), (s * (w / 2 + 0.035), 0, (z0 + h) / 2), 0))
    S = [K.socket("Text", (0, -0.03, z0 + h - 0.08))]
    for i in range(slots):
        z = z0 + h - 0.2 - (h - 0.28) * i / max(1, slots - 1) if slots > 1 else z0 + h / 2
        P.append(K.box("Slot%d" % i, (w * 0.7, 0.01, 0.06), (0, -0.03, z), 2, bevel=False)); S.append(K.socket("%s_%d" % (prefix, i), (0, -0.036, z)))
    return asset(a, *Y(g), P, [M(a, 0, "posts (G66 timber)", TIMBER), M(a, 1, "board (G66 sign board)", SIGN), M(a, 2, "slot plates (text = MI/decal)", slot_col or PAPER)],
                 S, [K.ucx_box(a, 0, (w + 0.14, 0.1, z0 + h), (0, 0, (z0 + h) / 2))] if legs else [], "%.1f x %.1f m board %s" % (w, h, note))


def boat_parts(L, W, mast=0.0, sail_slot=2):
    P = [K.box("Keel", (0.08, L, 0.08), (0, 0, 0.04), 0), K.box("Bottom", (W - 0.3, L - 0.4, 0.03), (0, 0, 0.09), 0),
         K.box("Transom", (W - 0.2, 0.04, 0.38), (0, L / 2 - 0.14, 0.27), 0), K.cyl("Stem", "z", 0.05, 0.03, 0.55, (0, -L / 2 + 0.05, 0.27), 0, 8)]
    for s in (-1, 1):
        P.append(K.box("Side%d" % s, (0.04, L - 0.3, 0.35), (s * (W / 2 - 0.08), 0, 0.28), 0, rot=(0, s * -18, 0)))
        P.append(K.box("Gunwale%d" % s, (0.06, L - 0.3, 0.04), (s * (W / 2 - 0.02), 0, 0.46), 1))
    if mast:
        P += [K.cyl("Mast", "z", 0.05, 0.04, mast, (0, -L * 0.15, mast / 2 + 0.1), 0, 8), K.slab("Sail", [(0, 0), (0, mast * 0.8), (L * 0.35, 0)], 0.01, (0, -L * 0.15 + 0.05, 0.4), sail_slot, rot=(90, 0, 90))]
    return P


def stall(a, g, w, cloth, note="", extra_s=None, extra_p=None):
    d, h = 1.2, 2.2; P = [K.box("Counter", (w, 0.5, 0.9), (0, -d / 2 + 0.25, 0.45), 0)]
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (-d / 2 + 0.04, d / 2 - 0.04): P.append(K.box("Pole%+.1f%+.1f" % (x, y), (0.07, 0.07, h), (x, y, h / 2), 0))
    P.append(K.box("Awning", (w + 0.2, d + 0.3, 0.04), (0, -0.15, h + 0.05), 1, rot=(-10, 0, 0))); P += extra_p or []
    S = [K.socket("Counter", (0, -d / 2 + 0.25, 0.9)), K.socket("Keeper", (0, d / 2 - 0.2, 0)), K.socket("Customer", (0, -d / 2 - 0.5, 0))] + (extra_s or [])
    return asset(a, *Y(g), P, [M(a, 0, "stall timber (G66)", TIMBER), M(a, 1, "awning cloth (G66)", cloth), M(a, 2, "sign board (G66)", SIGN), M(a, 3, "goods", ROPE)],
                 S, [K.ucx_box(a, 0, (w, d, h), (0, 0, h / 2))], "%.1f x 1.2 x 2.3 m stall %s" % (w, note))


def lantern_pole(a, g, h):
    P = [K.box("Foot", (0.3, 0.3, 0.06), (0, 0, 0.03), 0), K.cyl("Pole", "z", 0.035, 0.03, h, (0, 0, h / 2), 0, 8), K.box("Arm", (0.04, 0.35, 0.04), (0, -0.16, h - 0.05), 0),
         K.box("Lantern", (0.16, 0.16, 0.22), (0, -0.3, h - 0.2), 2), K.box("LanternCap", (0.2, 0.2, 0.04), (0, -0.3, h - 0.07), 1)]
    return asset(a, *Y(g), P, [M(a, 0, "pole (G66 timber)", TIMBER), M(a, 1, "cap iron", IRON, 0.5, 0.8), M(a, 2, "lit paper lantern (G66 cloth, emissive)", "FFC870", 0.6, glow=True)],
                 [K.socket("Light", (0, -0.3, h - 0.2)), K.socket("Floor", (0, 0, 0))], [K.ucx_prism(a, 0, "z", 0.15, h, (0, 0, h / 2))], "%.1f m lit lantern pole" % h)


def small(a, g, parts, mats, socks, size):
    return asset(a, *Y(g), parts, [M(a, i, *m) for i, m in enumerate(mats)], socks, [], size)


def g204():
    g = "G204"; a = "Prop_YTM_SternBoard"; L = 1.6
    sb = asset(a, *Y(g), [K.box("Plank", (L, 0.06, 0.32), (0, 0, 0.16), 0)] + [K.box("Line%d" % i, (L * 0.8, 0.004, 0.04), (0, -0.032, 0.25 - 0.07 * i), 1, bevel=False) for i in range(3)],
               [M(a, 0, "stern plank (G66 timber)", TIMBER), M(a, 1, "carved verse lines (decal/MI per verse)", SIGN)],
               [K.socket("Verse_%d" % i, (0, -0.035, 0.25 - 0.07 * i)) for i in range(3)] + [K.socket("Mount", (0, 0.03, 0.16))], [K.ucx_box(a, 0, (L, 0.06, 0.32), (0, 0, 0.16))], "1.6 x 0.32 m carved plank")
    b = "Prop_YTM_LetterTile"
    lt = small(b, g, [K.box("Tile", (0.08, 0.08, 0.02), (0, 0, 0.01), 0), K.box("Glyph", (0.05, 0.05, 0.002), (0, 0, 0.021), 1, bevel=False)],
               [("tile (G66 timber)", TIMBER), ("letter glyph (MI per letter a-z)", SIGN)], [K.socket("Glyph", (0, 0, 0.022)), K.socket("Hand", (0, 0, 0.01))], "8 cm tile")
    lt["spec"]["mi_set"] = ["MI_YTM_LetterTile_%s" % chr(97 + i) for i in range(26)]; lt["spec"]["mi_param"] = "Glyph (letter index 0..25 into T_YTM_LetterAtlas)"
    c = "Prop_YTM_BeachFire"; P = []
    for i in range(10):
        an = i * math.pi / 5; P.append(K.box("Stone%d" % i, (0.16, 0.12, 0.1), (0.42 * math.cos(an), 0.42 * math.sin(an), 0.05), 0, rot=(0, 0, math.degrees(an))))
    for i in range(4):
        an = i * math.pi / 2; P.append(K.cyl("Log%d" % i, "x", 0.04, 0.04, 0.5, (0, 0, 0.1), 1, 6, rot=(0, -25, math.degrees(an))))
    P.append(K.cyl("Embers", "z", 0.22, 0.22, 0.03, (0, 0, 0.015), 2, 10))
    bf = asset(c, *Y(g), P, [M(c, 0, "beach stones", STONE), M(c, 1, "driftwood", "9A8460"), M(c, 2, "embers (emissive)", EMBER, glow=True)],
               [K.socket("Fire", (0, 0, 0.15))] + [K.socket("Sit_%d" % i, (0.9 * math.cos(i * math.pi / 2 + 0.4), 0.9 * math.sin(i * math.pi / 2 + 0.4), 0)) for i in range(4)],
               [K.ucx_prism(c, 0, "z", 0.5, 0.2, (0, 0, 0.1))], "1.0 m stone ring")
    return [sb, lt, bf]


def g209():
    out = [lantern_pole("Prop_YTM_LanternPole_H%d" % (i + 1), "G209", h) for i, h in enumerate((1.2, 1.6, 2.0, 2.4, 2.8))]
    a = "Prop_YTM_SitOutMat"
    out.append(small(a, "G209", [K.box("Mat", (1.2, 0.8, 0.015), (0, 0, 0.0075), 0, bevel=False)] + [K.box("Stripe%d" % i, (1.2, 0.08, 0.017), (0, -0.3 + 0.2 * i, 0.0085), 1, bevel=False) for i in range(4)],
                     [("woven mat (G66 cloth)", CLOTH4[0]), ("stripes (G66 cloth)", CLOTH4[2])], [K.socket("Sit_0", (-0.3, 0, 0.015)), K.socket("Sit_1", (0.3, 0, 0.015))], "1.2 x 0.8 m"))
    return out


def g212():
    g = "G212"; pb = [K.box("PriceBoard", (0.9, 0.04, 0.5), (0, -0.62, 1.7), 2)]
    rs = stall("Prop_YTM_RopeStall", g, 2.0, CLOTH4[0], "with price board", [K.socket("Price_%d" % i, (-0.3 + 0.2 * i, -0.645, 1.7)) for i in range(4)], pb)
    a = "Prop_YTM_MeasuringBench"; L = 2.0; P = []
    ex = [K.box("Rule", (L, 0.04, 0.005), (0, -0.2, 0.8), 2, bevel=False)] + [K.box("Mark%d" % i, (0.01, 0.06, 0.007), (-L / 2 + 0.1 + 0.3 * i, -0.2, 0.802), 1, bevel=False) for i in range(7)]
    mb = table(a, g, L, 0.5, 0.8, 0, ex, "bench with a 1.8 m rule"); mb["sockets"] += [K.socket("Mark_%d" % i, (-L / 2 + 0.1 + 0.3 * i, -0.2, 0.805)) for i in range(7)]; mb["spec"]["sockets"] = [s["name"] for s in mb["sockets"]]
    b = "Prop_YTM_RopeCoil"
    coil = small(b, g, [K.cyl("Turn%d" % i, "z", 0.22 - 0.02 * i, 0.22 - 0.02 * i, 0.04, (0, 0, 0.02 + 0.04 * i), 0, 14) for i in range(4)], [("rope", ROPE)], [K.socket("Hand", (0, 0, 0.16)), K.socket("End", (0.22, 0, 0.02))], "0.44 m coil")
    cuts = [small("Prop_YTM_RopeCut_%s" % n, g, [K.cyl("Rope", "x", 0.015, 0.015, l, (0, 0, 0.015), 0, 6)], [("rope", ROPE)], [K.socket("EndA", (-l / 2, 0, 0.015)), K.socket("EndB", (l / 2, 0, 0.015))], "%.1f m cut" % l)
            for n, l in (("Short", 0.5), ("Medium", 1.0), ("Long", 1.5))]
    return [rs, mb, coil] + cuts


def g215():
    g = "G215"; out = [stall("Prop_YTM_MarketStall_%s" % v, g, w, CLOTH4[i % len(CLOTH4)], v) for i, (v, w) in enumerate((("A", 1.6), ("B", 2.0), ("C", 2.4)))]
    a = "Prop_YTM_HarbourGate"; P = [K.box("PostL", (0.3, 0.3, 3.0), (-1.6, 0, 1.5), 0), K.box("PostR", (0.3, 0.3, 3.0), (1.6, 0, 1.5), 0), K.box("Lintel", (3.6, 0.35, 0.3), (0, 0, 3.15), 1),
        K.box("LeafL", (1.45, 0.06, 2.2), (-0.75, 0, 1.15), 0), K.box("LeafR", (1.45, 0.06, 2.2), (0.75, 0, 1.15), 0), K.box("Sign", (1.2, 0.04, 0.3), (0, -0.2, 3.15), 2)]
    out.append(asset(a, *Y(g), P, [M(a, 0, "gate timber (G66)", TIMBER), M(a, 1, "lintel stone", STONE), M(a, 2, "harbour sign (G66 sign board)", SIGN)],
                     [K.socket("HingeL", (-1.47, 0, 0.05)), K.socket("HingeR", (1.47, 0, 0.05)), K.socket("Text", (0, -0.23, 3.15)), K.socket("Lamp_L", (-1.6, -0.2, 2.6)), K.socket("Lamp_R", (1.6, -0.2, 2.6))],
                     [K.ucx_box(a, 0, (0.3, 0.3, 3.0), (-1.6, 0, 1.5)), K.ucx_box(a, 1, (0.3, 0.3, 3.0), (1.6, 0, 1.5)), K.ucx_box(a, 2, (3.6, 0.35, 0.3), (0, 0, 3.15))],
                     "3.6 m wide, 3.3 m; leaves hinge at SOCKET_HingeL/R (split leaves in UE or swap open mesh)"))
    b = "Prop_YTM_InnDoor"
    out.append(asset(b, *Y(g), [K.box("FrameL", (0.1, 0.15, 2.2), (-0.55, 0, 1.1), 0), K.box("FrameR", (0.1, 0.15, 2.2), (0.55, 0, 1.1), 0), K.box("FrameTop", (1.2, 0.15, 0.12), (0, 0, 2.26), 0),
                     K.box("Door", (1.0, 0.05, 2.15), (0, 0, 1.08), 1), K.cyl("Ring", "y", 0.05, 0.05, 0.01, (0.35, -0.035, 1.05), 2, 10), K.box("InnSign", (0.6, 0.03, 0.3), (0, -0.1, 2.55), 1)],
                     [M(b, 0, "frame (G66 timber)", TIMBER), M(b, 1, "door + inn sign (G66 sign board)", SIGN), M(b, 2, "iron ring", IRON, 0.5, 0.8)],
                     [K.socket("Door", (-0.5, 0, 0)), K.socket("Handle", (0.35, -0.04, 1.05)), K.socket("Text", (0, -0.12, 2.55))], [K.ucx_box(b, 0, (1.2, 0.15, 2.32), (0, 0, 1.16))], "1.2 x 2.3 m; leaf hinges at SOCKET_Door"))
    return out


def g219():
    g = "G219"; out = []
    for n, parts, col in (("Cowrie", [K.lathe("Body", [(0.0, 0.0), (0.022, 0.008), (0.026, 0.02), (0.018, 0.03), (0.0, 0.032)], (0, 0, 0), 0, segments=10)], "E8D0A8"),
                          ("Whelk", [K.cyl("Whorl%d" % i, "z", 0.03 - 0.008 * i, 0.024 - 0.008 * i, 0.025, (0, 0, 0.0125 + 0.022 * i), 0, 10) for i in range(3)], "C8A880"),
                          ("Scallop", [K.slab("Fan", [(0, 0)] + [(0.04 * math.cos(math.pi * k / 8), 0.04 * math.sin(math.pi * k / 8) + 0.0) for k in range(9)], 0.006, (0, 0, 0.003), 0)], "E89C78"),
                          ("Periwinkle", [K.lathe("Body", [(0.0, 0.0), (0.012, 0.004), (0.014, 0.012), (0.006, 0.022), (0.0, 0.024)], (0, 0, 0), 0, segments=8)], "6A6A78")):
        out.append(small("Prop_YTM_Shell_" + n, g, parts, [(n.lower() + " shell (tint = MI)", col)], [K.socket("String", (0, 0, 0.01)), K.socket("Hand", (0, 0, 0.01))], "%s shell" % n))
    a = "Prop_YTM_ShellString"; L = 1.2
    out.append(small(a, g, [K.cyl("Cord", "x", 0.004, 0.004, L, (0, 0, 0.004), 0, 6)], [("cord", ROPE)],
                     [K.socket("EndA", (-L / 2, 0, 0.004)), K.socket("EndB", (L / 2, 0, 0.004))] + [K.socket("Bead_%d" % i, (-L / 2 + 0.1 + (L - 0.2) * i / 7, 0, 0.004)) for i in range(8)], "1.2 m cord, 8 shell sockets"))
    out.append(table("Prop_YTM_InnTable", g, 1.4, 0.8, 0.76, 4, None, "inn table"))
    return out


def g223():
    g = "G223"; out = [board("Prop_YTM_FareBoard", g, 1.0, 0.8, 0.6, 4, "Fare")]
    a = "Prop_YTM_Ferry"; P = boat_parts(5.0, 2.0, mast=3.2) + [K.box("Bench%d" % i, (1.6, 0.25, 0.05), (0, -0.8 + 1.0 * i, 0.38), 1) for i in range(3)]
    out.append(asset(a, *Y(g), P, [M(a, 0, "hull (G66 timber)", TIMBER), M(a, 1, "benches (G66 sign board)", SIGN), M(a, 2, "sail (G66 cloth)", CLOTH4[1])],
                     [K.socket("Seat_%d" % i, (0, -0.8 + 1.0 * i, 0.41)) for i in range(3)] + [K.socket("Helm", (0, 2.2, 0.4)), K.socket("Mooring_Bow", (0, -2.5, 0.45)), K.socket("Mooring_Stern", (0, 2.4, 0.45))],
                     [K.ucx_box(a, 0, (2.0, 5.0, 0.5), (0, 0, 0.25))], "5 x 2 m sail ferry, 3.2 m mast"))
    b = "Prop_YTM_InnDock"; P = [K.box("Deck", (2.0, 4.0, 0.08), (0, 0, 0.56), 0)]
    for x in (-0.9, 0.9):
        for y in (-1.8, 0.0, 1.8): P.append(K.cyl("Pile%+.1f%+.1f" % (x, y), "z", 0.1, 0.1, 1.0, (x, y, 0.3), 1, 8))
    out.append(asset(b, *Y(g), P, [M(b, 0, "deck planks (G66 timber)", TIMBER), M(b, 1, "piles", "6A5A48")],
                     [K.socket("Mooring_0", (1.0, -1.0, 0.65)), K.socket("Mooring_1", (1.0, 1.0, 0.65)), K.socket("Board", (0, 2.0, 0.6)), K.socket("Shore", (0, 2.0, 0.6))],
                     [K.ucx_box(b, 0, (2.0, 4.0, 0.6), (0, 0, 0.3))], "2 x 4 m dock, deck 0.6 m above water line z=0"))
    return out


def g226():
    g = "G226"; a = "Prop_YTM_FlagLocker"; P = [K.box("Carcass", (0.9, 0.45, 1.6), (0, 0, 0.8), 0)]
    S = []
    for i in range(6):
        x, z = (-0.22 if i % 2 == 0 else 0.22), 0.3 + 0.45 * (i // 2)
        P.append(K.box("Cubby%d" % i, (0.38, 0.02, 0.38), (x, -0.226, z + 0.19), 1, bevel=False)); S.append(K.socket("Flag_%d" % i, (x, -0.1, z)))
    loc = asset(a, *Y(g), P, [M(a, 0, "locker (G66 timber)", TIMBER), M(a, 1, "cubby backs (G66 sign board)", SIGN)], S + [K.socket("Door", (-0.45, -0.23, 0))],
                [K.ucx_box(a, 0, (0.9, 0.45, 1.6), (0, 0, 0.8))], "0.9 x 0.45 x 1.6 m, 6 folded-flag cubbies")
    b = "Prop_YTM_DyePot"
    pot = small(b, g, [K.cyl("Pot", "z", 0.25, 0.22, 0.4, (0, 0, 0.2), 0, 14), K.cyl("Dye", "z", 0.22, 0.22, 0.02, (0, 0, 0.35), 1, 14), K.cyl("Stick", "z", 0.015, 0.015, 0.6, (0.1, 0, 0.5), 2, 6, rot=(0, 20, 0))],
                [("clay pot", "A86040"), ("dye (colour = MI)", CLOTH4[2]), ("stir stick (G66 timber)", TIMBER)], [K.socket("Dye", (0, 0, 0.36)), K.socket("Fire", (0, 0, 0))], "0.5 m dye pot")
    c = "Prop_YTM_Flagpole"; h = 4.0
    pole = asset(c, *Y(g), [K.box("Base", (0.4, 0.4, 0.2), (0, 0, 0.1), 0), K.cyl("Pole", "z", 0.05, 0.035, h, (0, 0, h / 2), 0, 8), K.cyl("Finial", "z", 0.05, 0.0, 0.12, (0, 0, h + 0.06), 2, 8),
                  K.box("Flag", (0.02, 0.9, 0.6), (0, 0.47, h - 0.35), 1, bevel=False)],
                 [M(c, 0, "pole (G66 timber)", TIMBER), M(c, 1, "flag cloth (swappable MI per island)", CLOTH4[0]), M(c, 2, "brass finial", BRASS, 0.3, 0.9)],
                 [K.socket("Flag", (0, 0.02, h - 0.05)), K.socket("Halyard", (0.05, 0, 1.0))], [K.ucx_prism(c, 0, "z", 0.2, h, (0, 0, h / 2))], "4 m pole, 0.9 x 0.6 m flag on its own slot")
    pole["spec"]["mi_set"] = ["MI_YTM_Flag_Island_%d" % i for i in range(1, 9)]
    return [loc, pot, pole]


def g229():
    g = "G229"; a = "Prop_YTM_AlmanacLectern"
    lec = asset(a, *Y(g), [K.box("Base", (0.45, 0.4, 0.05), (0, 0, 0.025), 0), K.box("Post", (0.08, 0.08, 1.0), (0, 0, 0.55), 0), K.box("Desk", (0.55, 0.42, 0.04), (0, 0, 1.08), 0, rot=(-20, 0, 0)),
                  K.box("Almanac", (0.46, 0.34, 0.06), (0, -0.01, 1.12), 1, rot=(-20, 0, 0))],
                [M(a, 0, "lectern (G66 timber)", TIMBER), M(a, 1, "almanac (G66 cloth binding)", CLOTH4[3])], [K.socket("Text", (0, -0.08, 1.16)), K.socket("Reader", (0, -0.6, 0))],
                [K.ucx_box(a, 0, (0.55, 0.42, 1.2), (0, 0, 0.6))], "0.55 x 1.2 m")
    b = "Prop_YTM_Weathervane"; h = 2.5
    wv = asset(b, *Y(g), [K.box("Foot", (0.3, 0.3, 0.06), (0, 0, 0.03), 0), K.cyl("Mast", "z", 0.03, 0.025, h, (0, 0, h / 2), 0, 8)]
               + [K.box("Arm%s" % d, (0.5 if d in "EW" else 0.02, 0.02 if d in "EW" else 0.5, 0.02), (0, 0, h - 0.3), 1, bevel=False) for d in "EN"]
               + [K.slab("Vane", [(-0.35, 0), (0.25, 0), (0.35, 0.06), (0.25, 0.12), (-0.35, 0.12), (-0.25, 0.06)], 0.01, (0, 0, h + 0.05), 2, rot=(90, 0, 0))],
               [M(b, 0, "mast (G66 timber)", TIMBER), M(b, 1, "compass arms iron", IRON, 0.5, 0.8), M(b, 2, "vane (G66 cloth tint, copper)", "B87A48", 0.4, 0.7)],
               [K.socket("Vane", (0, 0, h + 0.05)), K.socket("Compass", (0, 0, h - 0.3))], [K.ucx_prism(b, 0, "z", 0.15, h, (0, 0, h / 2))], "2.5 m vane; spin yaw about SOCKET_Vane")
    return [lec, wv]


def g232():
    g = "G232"; a = "Prop_YTM_CaveMouth"; P = []
    for s in (-1, 1):
        P.append(K.box("Jamb%d" % s, (0.9, 1.2, 2.6), (s * 1.45, 0, 1.3), 0, rot=(0, s * 6, 0)))
    P += [K.box("Brow", (3.8, 1.3, 0.9), (0, 0, 2.9), 0), K.box("Floor", (2.0, 1.2, 0.05), (0, 0, 0.025), 1), K.box("Dark", (2.0, 0.02, 2.4), (0, 0.55, 1.2), 2, bevel=False)]
    cm = asset(a, *Y(g), P, [M(a, 0, "cave rock", STONE), M(a, 1, "sand floor", SAND), M(a, 2, "cave dark (unlit black)", "101010")],
               [K.socket("Entrance", (0, -0.6, 0)), K.socket("Inside", (0, 0.6, 0)), K.socket("Echo", (0, 0.5, 1.6))],
               [K.ucx_box(a, 0, (0.9, 1.2, 2.6), (-1.45, 0, 1.3)), K.ucx_box(a, 1, (0.9, 1.2, 2.6), (1.45, 0, 1.3)), K.ucx_box(a, 2, (3.8, 1.3, 0.9), (0, 0, 2.9))], "3.8 x 3.35 m arch, 2 m walk-through")
    b = "Prop_YTM_MarkWall"; W = 2.5; S = []
    P = [K.box("Wall", (W, 0.4, 2.0), (0, 0, 1.0), 0)]
    for i in range(5):
        x = -W / 2 + 0.35 + (W - 0.7) * i / 4; z = 1.0 + 0.35 * math.sin(i * 1.3)
        P.append(K.cyl("Mark%d" % i, "y", 0.08, 0.08, 0.01, (x, -0.205, z), 1, 10)); S.append(K.socket("Mark_%d" % i, (x, -0.21, z)))
    mw = asset(b, *Y(g), P, [M(b, 0, "cave rock", STONE), M(b, 1, "glow mark (emissive, MI per mark)", "9AF0E0", 0.5, glow=True)], S, [K.ucx_box(b, 0, (W, 0.4, 2.0), (0, 0, 1.0))], "2.5 x 2.0 m wall, 5 glow-mark sockets")
    return [cm, mw]


def g235():
    g = "G235"; out = []
    for v, holes in (("Torn", 3), ("Mended", 0)):
        a = "Prop_YTM_NetFrame_" + v; W, H = 1.6, 1.4; P = [K.box("Top", (W, 0.06, 0.06), (0, 0, H), 0), K.box("Bot", (W, 0.06, 0.06), (0, 0, 0.3), 0)]
        for s in (-1, 1): P.append(K.box("Post%d" % s, (0.07, 0.07, H + 0.05), (s * W / 2, 0, (H + 0.05) / 2), 0))
        for i in range(9): P.append(K.box("V%d" % i, (0.008, 0.01, H - 0.3), (-W / 2 + 0.16 * (i + 1), 0, (H + 0.3) / 2), 1, bevel=False))
        for j in range(6): P.append(K.box("H%d" % j, (W, 0.01, 0.008), (0, 0, 0.45 + 0.16 * j), 1, bevel=False))
        S = [K.socket("Mender", (0, -0.7, 0))] + [K.socket("Tear_%d" % k, (-0.4 + 0.4 * k, -0.01, 0.6 + 0.2 * k)) for k in range(3)]
        if holes: P.append(K.box("TearMask", (0.01, 0.002, 0.01), (0, -0.04, 0.8), 2, bevel=False))
        m = asset(a, *Y(g), P, [M(a, 0, "frame (G66 timber)", TIMBER), M(a, 1, "net twine", ROPE), M(a, 2, "torn flag", ROPE)], S, [K.ucx_box(a, 0, (W + 0.07, 0.1, H), (0, 0, H / 2))],
                  "1.6 x 1.4 m frame; %s (tears at SOCKET_Tear_k; torn = opacity-mask MI holes)" % v.lower())
        m["spec"]["state"] = v; out.append(m)
    out.append(stool("Prop_YTM_MenderStool", g, 0.4))
    out.append(board("Prop_YTM_KnotBoard", g, 0.9, 0.6, 0.9, 6, "Knot", ROPE, note="6 knot pegs"))
    return out


def g238():
    g = "G238"; out = [table("Prop_YTM_LongTable", g, 4.0, 1.0, 0.76, 10, [K.box("Runner", (3.8, 0.4, 0.004), (0, 0, 0.762), 1, bevel=False)], "feast table, 10 places")]
    a = "Prop_YTM_HallBook"
    out.append(small(a, g, [K.box("Cover", (0.42, 0.3, 0.07), (0, 0, 0.035), 0), K.box("Pages", (0.4, 0.28, 0.06), (0.005, 0, 0.04), 1)], [("leather (G66 cloth)", CLOTH4[3]), ("pages", PAPER)],
                     [K.socket("Text", (0, 0, 0.071)), K.socket("Hand", (0, 0, 0.035))], "0.42 x 0.3 m hall book"))
    b = "Prop_YTM_HarvestGarland"; L = 3.0; P = [K.cyl("Rope", "x", 0.01, 0.01, L, (0, 0, 0.0), 0, 6)]
    for i in range(10):
        x = -L / 2 + 0.15 + (L - 0.3) * i / 9; sag = -0.25 * (1 - (2 * x / L) ** 2)
        P.append(K.cyl("Sheaf%d" % i, "z", 0.04, 0.07, 0.18, (x, 0, sag - 0.09), 1 + i % 2, 8))
    out.append(small(b, g, P, [("garland rope", ROPE), ("wheat sheaf", "D8B860"), ("apple / ribbon (G66 cloth)", CLOTH4[0])],
                     [K.socket("EndA", (-L / 2, 0, 0)), K.socket("EndB", (L / 2, 0, 0))], "3 m garland, hang EndA/EndB between posts"))
    return out


def g242():
    g = "G242"; a = "Prop_YTM_SmallLighthouse"; P = [K.cyl("Base", "z", 1.2, 1.2, 0.4, (0, 0, 0.2), 0, 14), K.cyl("Tower", "z", 0.9, 0.6, 5.0, (0, 0, 2.9), 1, 14),
        K.cyl("Gallery", "z", 0.85, 0.85, 0.1, (0, 0, 5.45), 0, 14), K.cyl("Lantern", "z", 0.45, 0.45, 0.8, (0, 0, 5.9), 2, 12), K.cyl("Roof", "z", 0.55, 0.05, 0.5, (0, 0, 6.55), 3, 12),
        K.box("Door", (0.6, 0.05, 1.1), (0, -0.85, 0.95), 3)]
    lh = asset(a, *Y(g), P, [M(a, 0, "stone base", STONE), M(a, 1, "whitewash (G66 stripe via MI)", "EDE6D6"), M(a, 2, "lamp glass (emissive)", "FFE8A0", 0.2, glow=True), M(a, 3, "roof + door (G66 cloth)", CLOTH4[0])],
               [K.socket("Lamp", (0, 0, 5.9)), K.socket("Shutter", (0, -0.47, 5.9)), K.socket("Door", (-0.3, -0.88, 0.4)), K.socket("Gallery", (0, -0.7, 5.5))],
               [K.ucx_prism(a, 0, "z", 1.2, 6.8, (0, 0, 3.4))], "2.4 m dia x 6.8 m; SignalShutter mounts at SOCKET_Shutter")
    b = "Prop_YTM_SignalShutter"
    sh = small(b, g, [K.box("Frame", (0.7, 0.04, 0.7), (0, 0, 0.35), 0)] + [K.box("Slat%d" % i, (0.62, 0.015, 0.12), (0, -0.01, 0.1 + 0.13 * i), 1, rot=(30, 0, 0)) for i in range(5)],
               [("frame (G66 timber)", TIMBER), ("slats (open/closed = rotate about SOCKET_Slat_k)", IRON)],
               [K.socket("Hinge", (0, 0.02, 0.35)), K.socket("Mount", (0, 0.02, 0.35))] + [K.socket("Slat_%d" % i, (0, -0.01, 0.1 + 0.13 * i)) for i in range(5)], "0.7 m shutter, 5 slats")
    return [lh, sh]


def g245():
    g = "G245"; a = "Prop_YTM_PostBoat"; P = boat_parts(3.2, 1.2) + [K.box("MailBox", (0.5, 0.4, 0.35), (0, -0.4, 0.27), 2)]
    pb = asset(a, *Y(g), P, [M(a, 0, "hull (G66 timber)", TIMBER), M(a, 1, "gunwale (G66 sign board)", SIGN), M(a, 2, "post chest (G66 cloth red)", CLOTH4[0])],
               [K.socket("Seat", (0, 0.4, 0.38)), K.socket("Bag", (0, -0.4, 0.45)), K.socket("Oar_L", (-0.6, 0.4, 0.48)), K.socket("Oar_R", (0.6, 0.4, 0.48)), K.socket("Mooring", (0, -1.6, 0.45))],
               [K.ucx_box(a, 0, (1.2, 3.2, 0.5), (0, 0, 0.25))], "3.2 x 1.2 m post boat")
    b = "Prop_YTM_LetterBag"
    bag = small(b, g, [K.box("Bag", (0.4, 0.15, 0.3), (0, 0, 0.15), 0), K.box("Flap", (0.4, 0.16, 0.1), (0, -0.005, 0.27), 0), K.box("Strap", (0.03, 0.01, 0.4), (0, 0.08, 0.45), 1), K.box("Badge", (0.06, 0.005, 0.06), (0, -0.083, 0.2), 2, bevel=False)],
                [("canvas (G66 cloth)", CLOTH4[1]), ("strap leather", "6A4A30"), ("post badge brass", BRASS)], [K.socket("Hand", (0, 0.08, 0.64)), K.socket("Letters", (0, 0, 0.2))], "0.4 x 0.3 m satchel")
    c = "Prop_YTM_JettyPostBox"
    box_ = asset(c, *Y(g), [K.box("Post", (0.12, 0.12, 1.0), (0, 0, 0.5), 0), K.box("Box", (0.4, 0.3, 0.45), (0, 0, 1.2), 1), K.box("Roof", (0.46, 0.36, 0.06), (0, 0, 1.45), 0, rot=(8, 0, 0)), K.box("Slot", (0.2, 0.01, 0.025), (0, -0.152, 1.3), 2, bevel=False)],
                 [M(c, 0, "post (G66 timber)", TIMBER), M(c, 1, "post box (G66 cloth red)", CLOTH4[0]), M(c, 2, "slot", "1A1A1A")],
                 [K.socket("Slot", (0, -0.16, 1.3)), K.socket("Door", (-0.2, 0.15, 1.0)), K.socket("Letters", (0, 0, 1.0))], [K.ucx_box(c, 0, (0.4, 0.3, 1.48), (0, 0, 0.74))], "0.4 x 1.48 m jetty post box")
    return [pb, bag, box_]


GAPS = {"G204": g204, "G209": g209, "G212": g212, "G215": g215, "G219": g219, "G223": g223, "G226": g226, "G229": g229, "G232": g232, "G235": g235, "G238": g238, "G242": g242, "G245": g245}
STAGE = {"G204": "g204-ytm-verse", "G209": "g209-ytm-parade", "G212": "g212-ytm-rope", "G215": "g215-ytm-lanes", "G219": "g219-ytm-shells", "G223": "g223-ytm-ferry", "G226": "g226-ytm-flags",
         "G229": "g229-ytm-winds", "G232": "g232-ytm-echo", "G235": "g235-ytm-nets", "G238": "g238-ytm-feasts", "G242": "g242-ytm-relay", "G245": "g245-ytm-post"}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gap", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = GAPS[o.gap](); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
