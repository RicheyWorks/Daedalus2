# SPDX-License-Identifier: MIT
"""Contest backlog static props, Oct 19 asks resumed 2026-10-26 (blender-team), blender-kit/v1, one module, one kit per gap.
Static props only; rigged mobs (Mob_Thistle_Hare G156, Mob_Silverfin_Shoal G176, Mob_Ember_Fritillary G183) and the
MI_Mob_Lab_Hornback_Sick variant (G172) are a follow-up on creatures/*_rig.py. YTM props use the G66 stall palette (ytm_g116).
  G156 pythagoras 50322  Prop_Live_Trap (SOCKET_Door hinge, UCX), Prop_Ear_Tag (SOCKET_Tag)
  G163 pythagoras 50406  Prop_Studbook_Ledger (lectern, SOCKET_Text, SOCKET_Diversity bar origin), Prop_Leg_Band (SOCKET_LegBand)
  G167 youtube-master 50423  Prop_YTM_OrderRail (SOCKET_Card_0..7), Prop_YTM_CrateOfJars (SOCKET_Jar_0..1, SOCKET_Hand)
  G172 pythagoras 50449  Prop_Vaccine_Kit (SOCKET_Hand), Prop_Quarantine_Fence (2 m hurdle, SOCKET_EndA/EndB, UCX)
  G174 youtube-master 50492  Prop_YTM_Brazier_Lit / _Unlit (SOCKET_Fire), Prop_YTM_SeaMapTable (SOCKET_Peg_0..5, SOCKET_Map)
  G176 pythagoras 50545  Prop_Harbour_Ledger (SOCKET_DialQuota/DialShare/Text), Prop_Fishing_Skiff (~5 m, SOCKET_Net, UCX)
  G181 youtube-master 50597  Prop_YTM_SeaChest_Closed/_Open (SOCKET_Lid hinge, SOCKET_Item_0..4), Prop_YTM_Quilt/Kettle/Fiddle/SeedTin/JarOfSand
  G183 pythagoras 50603  Prop_Field_Furrows (10 x 10 m tileable ploughed patch, SOCKET_TileE/TileN)
Daedalus hook: every asset is origin bottom-centre, Blender front -Y (place yaw -90); sockets go to <Asset>.sockets.json via build_kit.
Usage: python backlog_20261026.py --gap G167 --out data/contest/backlog_g167.kit.json"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
import ytm_g116

SEED = 26102026
TIMBER, SIGN, CLOTH = ytm_g116.TIMBER, ytm_g116.BOARD, ytm_g116.CLOTH
IRON, WIRE, STONE, EMBER, GLASS, SAND, SOIL, SOIL_D, ROPE, PAPER, BRASS = ("3A3A40", "8A8C90", "8E8478", "F07A28", "B8D8E0",
    "E2C98E", "6B4A2E", "4E3420", "B89A62", "EDE3C8", "C8A040")


def M(a, slot, name, hexv, r=0.8, metal=0.0, glow=False):
    return K.material(a, slot, name, hexv, r, metal, glow)


def asset(a, gap, ask, parts, mats, socks, ucx, size):
    spec = {"gap": gap, "ask": ask, "lod": "LOD0/1", "size_m": size, "tri_cap": 6000, "sockets": [s["name"] for s in socks]}
    if a.startswith("Prop_YTM_"):
        spec["style"] = "G66 stall palette (ytm_g116)"
    return K.finish({"asset": a, "kind": "Prop", "seed": SEED, "spec": spec, "materials": mats, "objects": [K.obj(a, parts)],
                     "sockets": socks, "collision": ucx, "nanite": True})


def g156():
    a = "Prop_Live_Trap"; W, D, H, P = 0.7, 0.25, 0.25, []
    for x in (-W / 2, W / 2):
        for y in (-D / 2, D / 2):
            P.append(K.box("Edge%.2f%.2f" % (x, y), (0.012, 0.012, H), (x, y, H / 2), 0, bevel=False))
    for i in range(8):
        x = -W / 2 + W * i / 7
        P.append(K.box("HoopT%d" % i, (0.006, D, 0.006), (x, 0, H), 0, bevel=False, lod1={"drop": True} if i % 2 else None))
    P.append(K.box("Floor", (W, D, 0.01), (0, 0, 0.005), 1, bevel=False))
    P.append(K.box("Door", (0.006, D - 0.02, H - 0.02), (-W / 2 - 0.006, 0, H / 2), 0, bevel=False))
    P.append(K.box("Handle", (0.12, 0.02, 0.06), (0, 0, H + 0.03), 1, bevel=False))
    trap = asset(a, "G156", "pythagoras 50322", P, [M(a, 0, "galvanised wire", WIRE, 0.5, 0.8), M(a, 1, "trap floor/handle", TIMBER)],
                 [K.socket("Door", (-W / 2, 0, H - 0.01)), K.socket("Bait", (W / 4, 0, 0.01))], [K.ucx_box(a, 0, (W, D, H), (0, 0, H / 2))], "0.7 x 0.25 x 0.25 m")
    b = "Prop_Ear_Tag"
    tag = asset(b, "G156", "pythagoras 50322", [K.box("Tag", (0.02, 0.003, 0.025), (0, 0, 0.0125), 0), K.cyl("Stud", "y", 0.003, 0.003, 0.008, (0, 0, 0.022), 1, 8)],
                [M(b, 0, "tag plastic (number = decal/MI)", "F2C230", 0.6), M(b, 1, "stud", IRON, 0.4, 0.9)],
                [K.socket("Tag", (0, 0, 0.022)), K.socket("Number", (0, -0.002, 0.01))], [], "2 x 2.5 cm")
    return [trap, tag]


def g163():
    a = "Prop_Studbook_Ledger"; P = [K.box("Base", (0.45, 0.4, 0.05), (0, 0, 0.025), 0), K.box("Post", (0.08, 0.08, 1.0), (0, 0, 0.55), 0),
        K.box("Desk", (0.55, 0.42, 0.04), (0, 0, 1.08), 0, rot=(-20, 0, 0)), K.box("Book", (0.5, 0.36, 0.05), (0, -0.01, 1.12), 1, rot=(-20, 0, 0)),
        K.box("BarFrame", (0.42, 0.012, 0.05), (0, -0.215, 1.0), 0), K.box("Bar", (0.4, 0.01, 0.035), (0, -0.222, 1.0), 2)]
    led = asset(a, "G163", "pythagoras 50406", P, [M(a, 0, "lectern timber", TIMBER), M(a, 1, "ledger pages", PAPER), M(a, 2, "Diversity bar (scalar 0..1 MI param)", "3EAA5A", 0.5, glow=True)],
                [K.socket("Text", (0, -0.08, 1.16)), K.socket("Diversity", (-0.2, -0.23, 1.0))], [K.ucx_box(a, 0, (0.45, 0.42, 1.2), (0, 0, 0.6))], "0.55 x 0.42 x 1.2 m")
    b = "Prop_Leg_Band"
    band = asset(b, "G163", "pythagoras 50406", [K.cyl("Band", "z", 0.012, 0.012, 0.03, (0, 0, 0.015), 0, 12)], [M(b, 0, "band (lineage colour = MI param)", "D04040", 0.5)],
                 [K.socket("LegBand", (0, 0, 0.015))], [], "2.4 x 3 cm; fits Mob_Sky_Crane SOCKET_LegBand")
    return [led, band]


def g167():
    a = "Prop_YTM_OrderRail"; P = [K.box("Rail", (1.6, 0.04, 0.06), (0, 0, 1.6), 0)]; S = []
    for i in range(8):
        x = -0.7 + 0.2 * i
        P.append(K.cyl("Hook%d" % i, "y", 0.006, 0.006, 0.05, (x, -0.04, 1.58), 1, 6))
        P.append(K.box("Card%d" % i, (0.12, 0.004, 0.16), (x, -0.07, 1.48), 2, bevel=False))
        S.append(K.socket("Card_%d" % i, (x, -0.07, 1.56)))
    rail = asset(a, "G167", "youtube-master 50423", P, [M(a, 0, "rail (G66 timber)", TIMBER), M(a, 1, "hooks", IRON, 0.4, 0.9), M(a, 2, "order cards (G66 sign board)", SIGN)],
                 S, [K.ucx_box(a, 0, (1.6, 0.1, 0.3), (0, -0.03, 1.5))], "1.6 m rail at 1.6 m, 8 cards")
    b = "Prop_YTM_CrateOfJars"; P = [K.box("Floor", (0.4, 0.22, 0.02), (0, 0, 0.01), 0)]
    for s in (-1, 1):
        P.append(K.box("SideX%d" % s, (0.02, 0.22, 0.14), (s * 0.19, 0, 0.07), 0)); P.append(K.box("SideY%d" % s, (0.4, 0.02, 0.1), (0, s * 0.1, 0.05), 0))
    P += [K.box("Divider", (0.02, 0.18, 0.1), (0, 0, 0.05), 0), K.box("HandleBar", (0.4, 0.03, 0.03), (0, 0, 0.3), 0), K.box("HandlePost", (0.03, 0.03, 0.16), (0, 0, 0.22), 0)]
    crate = asset(b, "G167", "youtube-master 50423", P, [M(b, 0, "crate (G66 timber)", TIMBER)],
                  [K.socket("Jar_0", (-0.095, 0, 0.02)), K.socket("Jar_1", (0.095, 0, 0.02)), K.socket("Hand", (0, 0, 0.3))],
                  [K.ucx_box(b, 0, (0.4, 0.22, 0.32), (0, 0, 0.16))], "0.4 x 0.22 x 0.32 m, 2 jar slots")
    return [rail, crate]


def g172():
    a = "Prop_Vaccine_Kit"
    kit = asset(a, "G172", "pythagoras 50449", [K.box("Satchel", (0.34, 0.12, 0.24), (0, 0, 0.12), 0), K.box("Flap", (0.34, 0.13, 0.08), (0, -0.005, 0.2), 0),
        K.box("Strap", (0.03, 0.01, 0.3), (0, -0.065, 0.35), 0), K.cyl("DrenchBarrel", "x", 0.03, 0.03, 0.2, (0.27, 0, 0.08), 1), K.cyl("Nozzle", "x", 0.008, 0.004, 0.08, (0.41, 0, 0.08), 2),
        K.box("Grip", (0.03, 0.03, 0.1), (0.22, 0, 0.02), 2)],
        [M(a, 0, "canvas satchel", "6E7A4A"), M(a, 1, "dose barrel", GLASS, 0.2), M(a, 2, "gun metal", IRON, 0.4, 0.9)],
        [K.socket("Hand", (0.22, 0, 0.02), attach=((1, 0, 0), (0, 0, 1))), K.socket("Tip", (0.45, 0, 0.08))], [K.ucx_box(a, 0, (0.34, 0.12, 0.28), (0, 0, 0.14))], "0.4 m satchel + drench gun")
    b = "Prop_Quarantine_Fence"; L, H = 2.0, 1.0; P = []
    for i in range(5):
        x = -L / 2 + L * i / 4
        P.append(K.cyl("Stake%d" % i, "z", 0.025, 0.02, H + 0.15, (x, 0, (H + 0.15) / 2 - 0.15 + 0.15 / 2), 0, 8))
    for j in range(6):
        P.append(K.box("Weave%d" % j, (L, 0.035, 0.1), (0, 0.012 * (1 if j % 2 else -1), 0.12 + j * 0.15), 1, lod1={"drop": True} if j % 2 else None))
    fence = asset(b, "G172", "pythagoras 50449", P, [M(b, 0, "hazel stakes", TIMBER), M(b, 1, "woven withies", "8C7350")],
                  [K.socket("EndA", (-L / 2, 0, 0)), K.socket("EndB", (L / 2, 0, 0))], [K.ucx_box(b, 0, (L, 0.08, H), (0, 0, H / 2))], "2.0 x 1.0 m hurdle, tiles EndB->EndA")
    return [kit, fence]


def _brazier(lit):
    a = "Prop_YTM_Brazier_" + ("Lit" if lit else "Unlit")
    P = [K.cyl("StoneBase", "z", 0.4, 0.34, 0.5, (0, 0, 0.25), 0, 10), K.cyl("Neck", "z", 0.12, 0.12, 0.4, (0, 0, 0.7), 1, 8),
         K.cyl("Bowl", "z", 0.22, 0.45, 0.3, (0, 0, 1.05), 1, 12), K.cyl("Coals", "z", 0.4, 0.4, 0.05, (0, 0, 1.18), 2, 12)]
    if lit:
        P += [K.cyl("Flame%d" % i, "z", 0.16 - 0.04 * i, 0.0, 0.35 + 0.1 * i, (0.06 * (i - 1), 0.04 * (i % 2), 1.35 + 0.05 * i), 3, 6) for i in range(3)]
    mats = [M(a, 0, "stone base", STONE), M(a, 1, "iron bowl", IRON, 0.5, 0.8), M(a, 2, "coals" if lit else "cold ash", EMBER if lit else "4A4440", 0.9, glow=lit)]
    if lit:
        mats.append(M(a, 3, "flame (G66 warm cloth tone, emissive)", "FFB040", 0.5, glow=True))
    return asset(a, "G174", "youtube-master 50492", P, mats, [K.socket("Fire", (0, 0, 1.2))], [K.ucx_prism(a, 0, "z", 0.45, 1.2, (0, 0, 0.6))], "0.9 m wide, 1.2 m bowl rim")


def g174():
    a = "Prop_YTM_SeaMapTable"; P = [K.box("Top", (1.4, 0.9, 0.05), (0, 0, 0.82), 0), K.box("Map", (1.3, 0.8, 0.004), (0, 0, 0.847), 1, bevel=False)]
    for x in (-0.62, 0.62):
        for y in (-0.38, 0.38):
            P.append(K.box("Leg%.1f%.1f" % (x, y), (0.07, 0.07, 0.8), (x, y, 0.4), 0))
    S = [K.socket("Map", (0, 0, 0.849))]
    for i in range(6):
        x, y = -0.5 + 0.2 * i, (-0.25 if i % 2 else 0.2)
        P.append(K.cyl("Peg%d" % i, "z", 0.012, 0.012, 0.05, (x, y, 0.87), 2, 6)); S.append(K.socket("Peg_%d" % i, (x, y, 0.895)))
    return [_brazier(True), _brazier(False), asset(a, "G174", "youtube-master 50492", P,
            [M(a, 0, "table (G66 timber)", TIMBER), M(a, 1, "painted sea map (decal slot)", "C8D8C0"), M(a, 2, "cord pegs (G66 cloth)", CLOTH[0])],
            S, [K.ucx_box(a, 0, (1.4, 0.9, 0.85), (0, 0, 0.425))], "1.4 x 0.9 x 0.85 m; cords span SOCKET_Peg_i")]


def g176():
    a = "Prop_Harbour_Ledger"
    led = asset(a, "G176", "pythagoras 50545", [K.box("Board", (1.0, 0.05, 0.8), (0, 0, 1.0), 0), K.box("PostL", (0.08, 0.08, 1.4), (-0.46, 0.04, 0.7), 0),
        K.box("PostR", (0.08, 0.08, 1.4), (0.46, 0.04, 0.7), 0), K.cyl("DialQ", "y", 0.14, 0.14, 0.02, (-0.25, -0.035, 0.95), 1, 16), K.cyl("DialS", "y", 0.14, 0.14, 0.02, (0.25, -0.035, 0.95), 1, 16)],
        [M(a, 0, "rule board timber", TIMBER), M(a, 1, "brass dials", BRASS, 0.3, 0.9)],
        [K.socket("DialQuota", (-0.25, -0.046, 0.95)), K.socket("DialShare", (0.25, -0.046, 0.95)), K.socket("Text", (0, -0.026, 1.3))],
        [K.ucx_box(a, 0, (1.0, 0.13, 1.4), (0, 0.02, 0.7))], "1.0 x 1.4 m rule board")
    b = "Prop_Fishing_Skiff"; P = [K.box("Keel", (0.12, 5.0, 0.1), (0, 0, 0.05), 0)]
    for s in (-1, 1):
        P.append(K.box("Strake%d" % s, (0.05, 4.6, 0.45), (s * 0.7, 0, 0.35), 0, rot=(0, s * -15, 0)))
    P += [K.box("Bottom", (1.2, 4.6, 0.04), (0, 0, 0.12), 0), K.box("Thwart", (1.4, 0.2, 0.04), (0, 0.6, 0.42), 1), K.box("Transom", (1.3, 0.05, 0.45), (0, 2.3, 0.33), 0),
          K.cyl("Stem", "z", 0.06, 0.04, 0.7, (0, -2.45, 0.35), 0, 8), K.box("NetPile", (0.8, 0.9, 0.18), (0, 1.5, 0.23), 2)]
    skiff = asset(b, "G176", "pythagoras 50545", P, [M(b, 0, "planking", TIMBER), M(b, 1, "thwart", SIGN), M(b, 2, "net", "6A7C70")],
                  [K.socket("Net", (0, 1.5, 0.32)), K.socket("Oar_L", (-0.72, 0.6, 0.6)), K.socket("Oar_R", (0.72, 0.6, 0.6)), K.socket("Seat", (0, 0.6, 0.44))],
                  [K.ucx_box(b, 0, (1.5, 5.0, 0.6), (0, 0, 0.3))], "5.0 x 1.5 m skiff, bow -Y")
    return [led, skiff]


def _chest(opened):
    a = "Prop_YTM_SeaChest_" + ("Open" if opened else "Closed"); W, D, H = 0.9, 0.5, 0.45
    lid = K.box("Lid", (W, D, 0.12), (0, D / 2 + 0.06, H + D / 2) if opened else (0, 0, H + 0.06), 0, rot=(90, 0, 0) if opened else None)
    P = [K.box("Body", (W, D, H), (0, 0, H / 2), 0), lid]
    for x in (-0.3, 0.3):
        P.append(K.box("Band%.1f" % x, (0.04, D + 0.01, H + 0.01), (x, 0, H / 2), 1, bevel=False))
        if not opened:
            P.append(K.box("RopeTie%.1f" % x, (0.03, D + 0.03, 0.03), (x, 0, H + 0.13), 2, bevel=False))
    S = [K.socket("Lid", (0, D / 2, H))] + [K.socket("Item_%d" % i, (-0.32 + 0.16 * i, 0, 0.04)) for i in range(5)]
    return asset(a, "G181", "youtube-master 50597", P, [M(a, 0, "chest (G66 timber)", TIMBER), M(a, 1, "iron bands", IRON, 0.5, 0.8), M(a, 2, "rope ties", ROPE)],
                 S, [K.ucx_box(a, 0, (W, D, H + 0.12), (0, 0, (H + 0.12) / 2))], "0.9 x 0.5 x 0.57 m; lid hinge SOCKET_Lid, open 90 deg")


def g181():
    out = [_chest(False), _chest(True)]
    def small(n, parts, mats, size):
        a = "Prop_YTM_" + n
        return asset(a, "G181", "youtube-master 50597", parts, [M(a, i, *mm) for i, mm in enumerate(mats)], [K.socket("Hand", (0, 0, 0.02))], [], size)
    out.append(small("Quilt", [K.box("Fold%d" % i, (0.4, 0.3, 0.03), (0, 0, 0.015 + 0.03 * i), i % 2) for i in range(4)], [("patch A (G66 cloth)", CLOTH[0], 0.9), ("patch B (G66 cloth)", CLOTH[1], 0.9)], "0.4 x 0.3 m folded"))
    out.append(small("Kettle", [K.cyl("Pot", "z", 0.1, 0.07, 0.16, (0, 0, 0.08), 0, 14), K.cyl("Spout", "y", 0.02, 0.01, 0.1, (0, -0.12, 0.1), 0, 8, rot=(30, 0, 0)), K.box("BailL", (0.01, 0.01, 0.04), (-0.07, 0, 0.17), 1, bevel=False), K.box("BailR", (0.01, 0.01, 0.04), (0.07, 0, 0.17), 1, bevel=False), K.box("Bail", (0.15, 0.01, 0.01), (0, 0, 0.19), 1)], [("copper", "B06A3A", 0.4), ("handle", IRON, 0.5)], "0.2 m"))
    out.append(small("Fiddle", [K.box("Body", (0.2, 0.06, 0.36), (0, 0, 0.18), 0), K.box("Neck", (0.04, 0.03, 0.24), (0, 0, 0.48), 1), K.box("Scroll", (0.05, 0.04, 0.06), (0, 0, 0.62), 1)], [("spruce (G66 timber)", TIMBER, 0.6), ("ebony", "2A2018", 0.5)], "0.65 m"))
    out.append(small("SeedTin", [K.cyl("Tin", "z", 0.06, 0.06, 0.1, (0, 0, 0.05), 0, 14), K.cyl("Lid", "z", 0.062, 0.062, 0.02, (0, 0, 0.11), 1, 14)], [("tin (G66 cloth tint)", CLOTH[2], 0.4, 0.6), ("lid", BRASS, 0.4, 0.8)], "0.12 m"))
    out.append(small("JarOfSand", [K.cyl("Jar", "z", 0.06, 0.05, 0.14, (0, 0, 0.07), 0, 14), K.cyl("Sand", "z", 0.055, 0.045, 0.09, (0, 0, 0.05), 1, 14), K.cyl("Cork", "z", 0.03, 0.03, 0.03, (0, 0, 0.155), 2, 8)], [("glass", GLASS, 0.1), ("sand", SAND, 0.9), ("cork", ROPE, 0.9)], "0.17 m"))
    return out


def g183():
    a = "Prop_Field_Furrows"; N, L = 10, 10.0; P = [K.box("Bed", (L, L, 0.05), (0, 0, 0.025), 1, bevel=False)]
    for i in range(N):
        x = -L / 2 + (i + 0.5) * L / N
        P.append(K.box("Ridge%d" % i, (0.45, L, 0.14), (x, 0, 0.1), 0, lod1={"drop": True} if i % 2 else None))
    return [asset(a, "G183", "pythagoras 50603", P, [M(a, 0, "ploughed ridge soil", SOIL, 0.95), M(a, 1, "furrow soil", SOIL_D, 0.95)],
                  [K.socket("TileE", (L, 0, 0)), K.socket("TileN", (0, L, 0))], [K.ucx_box(a, 0, (L, L, 0.17), (0, 0, 0.085))], "10 x 10 m, 1 m furrow pitch, tiles at SOCKET_TileE/TileN")]


GAPS = {"G156": g156, "G163": g163, "G167": g167, "G172": g172, "G174": g174, "G176": g176, "G181": g181, "G183": g183}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gap", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = GAPS[o.gap](); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
