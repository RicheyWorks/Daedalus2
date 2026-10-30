# SPDX-License-Identifier: MIT
"""Game Blender items for the Unreal queue (blender-team, Richey 2026-10-30 via buffffff 59024/59099). blender-kit/v1, headless.
One function per Items-sheet row (bot-team\\GAMES\\<game>\\<game>.xlsx is authoritative). Every asset: origin bottom-centre, front -Y,
metres, UCX hulls, SOCKET_ hooks (sidecar via build_kit). All staged NOT READY until the editor turn.
  cabinet(...)   shared upright arcade cab (0.8 x 0.85 x 1.95 m): SOCKET_Floor/Screen/Marquee/Player1/CoinSlot; per-game styling.
  npc(...)       static humanoid PLACEHOLDER (~1.75 m, A-pose, no armature yet): SOCKET_Floor/Head/HandR/HandL/Speak. Rig = later pass.
Usage: python game_items.py --game glowmoss --kit data/games/glowmoss.kit.json      (then build_kit.py / check_kit.py / contact_sheet.py)"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "kit"))
import kitlib as K

SEED = 20261030
BLACK, CHROME, SCREEN, GOLD, WOOD, STONE, ROPE, SKIN = "1A1A22", "C8CCD4", "1A2A40", "F2C740", "8A6440", "8C8A88", "B89A6A", "D9A982"
HUES = ["FF6B2E", "338CFF", "73F28C", "FFF299", "B36BFF", "FF4AD0"]


def A(a, parts, mats, socks, ucx, size, spec=None, objects=None):
    return K.finish({"asset": a, "kind": "Prop", "seed": SEED, "spec": dict(spec or {}, size_m=size, tri_cap=8000, sockets=[s["name"] for s in socks], status="NOT READY"),
                     "materials": [K.material(a, i, *m) for i, m in enumerate(mats)], "objects": objects or [K.obj(a, parts)], "sockets": socks, "collision": ucx, "nanite": True})


def ball(name, c, r, slot, seg=8):
    return K.lathe(name, [(0, -r)] + [(r * math.sin(math.pi * i / 4), -r * math.cos(math.pi * i / 4)) for i in range(1, 4)] + [(0, r)], c, slot, seg)


# ---------------------------------------------------------------- shared arcade cabinet
def cabinet(a, body, trim, marquee, extra=(), extra_mats=(), note=""):
    W, D = 0.8, 0.85
    P = [K.box("Plinth", (W + 0.04, D + 0.04, 0.1), (0, 0, 0.05), 4), K.box("Lower", (W, D * 0.7, 0.85), (0, 0.1, 0.525), 0),
         K.box("Deck", (W, 0.38, 0.08), (0, -0.25, 0.97), 1, rot=(-12, 0, 0)), K.box("Upper", (W, D * 0.6, 0.85), (0, 0.15, 1.375), 0),
         K.box("Bezel", (W - 0.1, 0.03, 0.6), (0, -0.12, 1.33), 4, bevel=False), K.box("Screen", (W - 0.2, 0.02, 0.48), (0, -0.135, 1.33), 3, bevel=False),
         K.box("MarqueeBox", (W + 0.04, 0.4, 0.26), (0, 0.05, 1.93), 1), K.box("Marquee", (W - 0.06, 0.02, 0.18), (0, -0.155, 1.93), 2, bevel=False),
         K.box("SideL", (0.03, D * 0.75, 1.9), (-W / 2 - 0.015, 0.08, 1.0), 1, bevel=False), K.box("SideR", (0.03, D * 0.75, 1.9), (W / 2 + 0.015, 0.08, 1.0), 1, bevel=False),
         K.cyl("Stick", "z", 0.012, 0.012, 0.08, (-0.2, -0.3, 1.05), 4, 6), ball("StickBall", (-0.2, -0.3, 1.1), 0.025, 2, 6),
         K.box("CoinDoor", (0.22, 0.02, 0.3), (0, -0.255, 0.45), 1)]
    P += [K.cyl("Btn%d" % i, "z", 0.022, 0.022, 0.02, (0.02 + 0.08 * i, -0.28 - 0.01 * i, 1.03), 2, 8) for i in range(3)]
    P += list(extra)
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Screen", (0, -0.15, 1.33)), K.socket("Marquee", (0, -0.17, 1.93)), K.socket("Player1", (0, -0.75, 0)), K.socket("CoinSlot", (0, -0.27, 0.5))]
    mats = [("cabinet body", body, 0.5), ("trim / side art panel", trim, 0.45), ("marquee + buttons (emissive)", marquee, 0.3, 0.0, True), ("screen", SCREEN, 0.1), ("black fittings", BLACK, 0.5)] + list(extra_mats)
    return A(a, P, mats, S, [K.ucx_box(a, 0, (W + 0.06, D + 0.04, 2.06), (0, 0.02, 1.03))], "0.86 x 0.89 x 2.06 m upright arcade cabinet" + (": " + note if note else ""))


# ---------------------------------------------------------------- shared NPC placeholder
def npc(a, coat, accent, held=(), held_mats=(), note=""):
    P = [K.box("Torso", (0.42, 0.26, 0.55), (0, 0, 1.2), 0), K.box("Pelvis", (0.4, 0.26, 0.16), (0, 0, 0.88), 1), ball("Head", (0, -0.01, 1.63), 0.13, 2, 10),
         K.box("Belt", (0.43, 0.27, 0.05), (0, 0, 0.97), 1)]
    for s in (-1, 1):
        P += [K.cyl("Thigh%d" % s, "z", 0.08, 0.07, 0.42, (s * 0.11, 0, 0.6), 1, 8), K.cyl("Shin%d" % s, "z", 0.065, 0.055, 0.38, (s * 0.11, 0, 0.21), 1, 8),
              K.box("Boot%d" % s, (0.12, 0.22, 0.08), (s * 0.11, -0.04, 0.04), 3), K.cyl("Arm%d" % s, "z", 0.06, 0.05, 0.55, (s * 0.31, 0, 1.17), 0, 8, rot=(0, s * 12, 0)),
              ball("Hand%d" % s, (s * 0.37, 0, 0.88), 0.05, 2, 6), K.box("Eye%d" % s, (0.03, 0.01, 0.03), (s * 0.045, -0.135, 1.65), 3, bevel=False)]
    P += list(held)
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Head", (0, 0, 1.76)), K.socket("HandR", (-0.37, 0, 0.88)), K.socket("HandL", (0.37, 0, 0.88)), K.socket("Speak", (0, -0.15, 1.6))]
    mats = [("coat", coat, 0.85), ("accent / trousers", accent, 0.8), ("skin", SKIN, 0.7), ("dark (boots, eyes)", BLACK, 0.6)] + list(held_mats)
    return A(a, P, mats, S, [K.ucx_box(a, 0, (0.5, 0.35, 1.78), (0, 0, 0.89))], "~1.78 m NPC placeholder (static, rig pending)" + (": " + note if note else ""))


def lantern(name, c, glass_slot, metal_slot, h=0.3):
    x, y, z = c
    return [K.box(name + "Base", (0.16, 0.16, 0.03), (x, y, z + 0.015), metal_slot), K.cyl(name + "Glass", "z", 0.06, 0.06, h * 0.6, (x, y, z + 0.03 + h * 0.3), glass_slot, 8),
            K.cyl(name + "Cap", "z", 0.02, 0.09, 0.06, (x, y, z + 0.06 + h * 0.6), metal_slot, 8)] + \
           [K.box(name + "Post%d" % s, (0.01, 0.01, 0.07), (x + s * 0.035, y, z + 0.12 + h * 0.6), metal_slot, bevel=False) for s in (-1, 1)] + \
           [K.box(name + "Handle", (0.08, 0.012, 0.012), (x, y, z + 0.16 + h * 0.6), metal_slot, bevel=False)]


def crystal(name, c, h, slot, rot=(0, 0, 0)):
    x, y, z = c
    return K.lathe(name, [(0, 0), (h * 0.18, h * 0.08), (h * 0.18, h * 0.75), (0, h)], (x, y, z), slot, 6, rot=rot)


def rock(name, c, r, slot, seed_k=0):
    x, y, z = c; R = K.rng(SEED + seed_k, name)
    prof = [(0, -r * 0.9)] + [(r * (0.7 + 0.3 * R.random()) * math.sin(math.pi * i / 5), -r * math.cos(math.pi * i / 5) * 0.9) for i in range(1, 5)] + [(0, r * 0.5)]
    return K.lathe(name, prof, (x, y, z), slot, 7)


GAMES = {}


def game(name):
    def deco(fn):
        GAMES[name] = fn; return fn
    return deco


# ================================================================ glowmoss (prism-shard-dev, READY 58989)
@game("glowmoss")
def glowmoss():
    G = "Prop_Glowmoss_"; MOSS, CRY, DARK = "7CFF8A", "9AE8FF", "202838"; out = []
    rocks = [rock("Arch%d" % i, (s * (0.48 - 0.02 * i), -0.16, 0.25 + 0.35 * i), 0.14, 5, i) for i, s in ((0, -1), (1, -1), (2, -1), (0, 1), (1, 1), (2, 1))]
    gauge = [K.box("Gauge%d" % i, (0.06, 0.012, 0.08), (-0.3 + 0.075 * i, -0.17, 1.93), 6 if i < 6 else 4, bevel=False) for i in range(9)]
    out.append(cabinet("Prop_Arcade_Cab_GlowmossDelve", "2A2A30", "4A4A44", MOSS, rocks + [rock("ArchTop", (0, -0.16, 2.12), 0.2, 5, 9)] + gauge,
                       [("cave rock", "5A564E", 0.95), ("lamp gauge (emissive amber)", "FFB347", 0.3, 0.0, True)], "cave-mouth styling, lamp-gauge marquee"))
    # crystal shaft ledge kit: ledge tile, clusters 1..5, darkness decal cards 0..2
    P = [K.box("Slab", (1.0, 1.0, 0.25), (0, 0, 0.125), 0), K.box("Lip", (1.0, 0.08, 0.06), (0, -0.46, 0.28), 0)] + [rock("Pebble%d" % i, (-0.35 + 0.23 * i, 0.38, 0.27), 0.05, 0, i) for i in range(4)]
    out.append(A(G + "LedgeTile", P, [("shaft stone", "6A6560", 0.95)], [K.socket("Cluster", (0, 0, 0.25)), K.socket("Climb", (0, 0.45, 0.25)), K.socket("Floor", (0, 0, 0))],
                 [K.ucx_box(G + "LedgeTile", 0, (1.0, 1.0, 0.31), (0, 0, 0.155))], "1 x 1 m shaft ledge tile (grid cell)"))
    for n in range(1, 6):
        a = G + "CrystalCluster_%d" % n; R = K.rng(SEED + n, a); P = [rock("Root", (0, 0, 0.03), 0.09, 1, n)]
        for k in range(n):
            an = 2 * math.pi * k / n + R.random() * 0.4; d = 0.0 if n == 1 else 0.07
            P.append(crystal("Gem%d" % k, (d * math.cos(an), d * math.sin(an), 0.02), 0.16 + 0.06 * R.random(), 0, rot=(d * 160 * math.sin(an), -d * 160 * math.cos(an), 0)))
        out.append(A(a, P, [("crystal (emissive cyan)", CRY, 0.15, 0.0, True), ("root stone", "5A564E", 0.95)], [K.socket("Base", (0, 0, 0)), K.socket("Glow", (0, 0, 0.12))],
                     [K.ucx_box(a, 0, (0.24, 0.24, 0.22), (0, 0, 0.11))], "crystal cluster, %d gem%s (score unit)" % (n, "s" if n > 1 else "")))
    for dk in range(3):
        a = G + "DarknessCard_%d" % dk
        out.append(A(a, [K.box("Card", (1.0, 1.0, 0.004), (0, 0, 0.002), 0, bevel=False)], [("darkness %d (masked decal, opacity = MI %.2f)" % (dk, 0.3 * dk), DARK, 1.0)],
                     [K.socket("Base", (0, 0, 0))], [], "1 x 1 m darkness overlay card, level %d (decal target)" % dk))
    a = G + "Patch"; R = K.rng(SEED, a)
    P = [K.slab("Mat", [(0.3 * math.cos(t) * (0.8 + 0.2 * R.random()), 0.3 * math.sin(t) * (0.8 + 0.2 * R.random())) for t in [i * math.pi / 5 for i in range(10)]], 0.03, (0, 0, 0.015), 0)]
    P += [ball("Tuft%d" % i, (0.18 * math.cos(i * 1.3), 0.18 * math.sin(i * 1.3), 0.04), 0.035 + 0.01 * (i % 3), 0, 6) for i in range(7)]
    out.append(A(a, P, [("glowmoss (emissive green)", MOSS, 0.6, 0.0, True)], [K.socket("Base", (0, 0, 0)), K.socket("Glow", (0, 0, 0.06))], [], "0.6 m glowmoss patch (lamp refill)"))
    a = G + "LedgeTile_Unstable"; P = []
    for i, (x, y, rz) in enumerate(((-0.26, -0.24, 3), (0.25, -0.26, -4), (-0.25, 0.25, -2), (0.26, 0.25, 5))):
        P.append(K.box("Shard%d" % i, (0.47, 0.47, 0.25), (x, y, 0.125 - 0.01 * i), 0, rot=(0, 0, rz)))
    P += [K.box("Crack%d" % i, (0.02, 1.0, 0.02), (0, 0, 0.255), 1, bevel=False, rot=(0, 0, 90 * i)) for i in range(2)]
    out.append(A(a, P, [("shaft stone", "6A6560", 0.95), ("crack glow (emissive ember)", "FF8A3A", 0.4, 0.0, True)], [K.socket("Cluster", (0, 0, 0.25)), K.socket("Floor", (0, 0, 0))],
                 [K.ucx_box(a, 0, (1.0, 1.0, 0.27), (0, 0, 0.135))], "1 x 1 m unstable ledge, cracked into 4 (crumble = swap / physics)"))
    a = G + "DelversLamp"
    P = lantern("L", (0, 0, 0), 0, 1, 0.3)
    out.append(A(a, P, [("lamp glow (emissive amber)", "FFB347", 0.2, 0.0, True), ("brass", "B08D3C", 0.4, 0.8)], [K.socket("Grip", (0, 0, 0.34)), K.socket("Light", (0, 0, 0.13)), K.socket("Base", (0, 0, 0))],
                 [K.ucx_box(a, 0, (0.18, 0.18, 0.35), (0, 0, 0.175))], "0.35 m hand lantern (light budget)"))
    a = G + "ClimbRopeWinch"
    P = [K.box("Frame%d" % s, (0.08, 0.08, 0.9), (s * 0.4, 0, 0.45), 0) for s in (-1, 1)] + [K.box("Beam", (0.9, 0.1, 0.1), (0, 0, 0.92), 0), K.cyl("Drum", "x", 0.12, 0.12, 0.6, (0, 0, 0.7), 1, 12),
         K.cyl("Crank", "x", 0.02, 0.02, 0.2, (0.52, 0, 0.7), 2, 6), K.box("Handle", (0.03, 0.03, 0.15), (0.62, 0, 0.63), 2), K.cyl("Rope", "z", 0.015, 0.015, 0.7, (0, -0.12, 0.35), 1, 6)]
    out.append(A(a, P, [("timber", WOOD, 0.85), ("rope", ROPE, 0.95), ("iron", "3A3A3E", 0.6, 0.6)], [K.socket("RopeEnd", (0, -0.12, 0.0)), K.socket("Crank", (0.62, 0, 0.7)), K.socket("Floor", (0, 0, 0))],
                 [K.ucx_box(a, 0, (0.9, 0.3, 0.97), (0, 0, 0.485))], "0.9 m rope winch (climb out)"))
    out.append(npc("Mob_Glowmoss_DelverGuide", "6A5A40", "3A3A3A", lantern("Lamp", (-0.37, 0, 0.72), 4, 5, 0.25) + [K.cyl("Helmet", "z", 0.15, 0.14, 0.08, (0, 0, 1.74), 5, 10), K.cyl("HelmetLamp", "y", 0.035, 0.035, 0.03, (0, -0.14, 1.75), 4, 8)],
                   [("lamp glow (emissive amber)", "FFB347", 0.2, 0.0, True), ("brass", "B08D3C", 0.4, 0.8)], "lamp-bearing miner"))
    return out


# ================================================================ spiritkite (prism-shard-dev, READY 58990)
@game("spiritkite")
def spiritkite():
    G = "Prop_Spiritkite_"; SKY, KITE = "8CCBFF", "F7F2E6"; out = []
    kite = [K.slab("KiteSail", [(0, 0.16), (0.11, 0), (0, -0.2), (-0.11, 0)], 0.006, (0, -0.16, 2.17), 5, rot=(90, 0, 0)), K.cyl("KiteSpar", "z", 0.004, 0.004, 0.36, (0, -0.17, 2.15), 4, 4)]
    kite += [K.box("Tail%d" % i, (0.03, 0.006, 0.03), (0.04 * math.sin(i * 1.2), -0.17, 1.96 - 0.05 * i), 2, rot=(0, 45, 0), bevel=False) for i in range(4)]
    out.append(cabinet("Prop_Arcade_Cab_SpiritkiteWeave", "4A7FB8", "DDEEFF", SKY, kite, [("kite cloth", KITE, 0.8)], "sky-blue, kite marquee"))
    a = G + "SpiritKite"
    P = [K.slab("Sail", [(0, 0.45), (0.3, 0.05), (0, -0.5), (-0.3, 0.05)], 0.008, (0, 0, 0.5), 0), K.cyl("Spine", "y", 0.008, 0.008, 0.95, (0, -0.025, 0.51), 1, 6), K.cyl("Spar", "x", 0.008, 0.008, 0.6, (0, 0.05, 0.51), 1, 6)]
    tail = [K.box("TailSeg%d" % i, (0.06, 0.06, 0.006), (0, -0.55 - 0.1 * i, 0.5), 2, rot=(0, 0, 45), bevel=False) for i in range(5)]
    objs = [K.obj(a, P)]
    for i, p in enumerate(tail):
        objs.append(K.obj(a + "_Tail%d" % i, [p], parent=a if i == 0 else a + "_Tail%d" % (i - 1), pivot=(0, -0.5 - 0.1 * i, 0.5), role="tail segment (chain; sway driven in UE or via a later armature)"))
    out.append(A(a, None, [("spirit cloth (emissive soft)", KITE, 0.7, 0.0, True), ("frame (bamboo)", "C8A86A", 0.7), ("tail ribbons", "FF4AD0", 0.7)],
                 [K.socket("Line", (0, 0.05, 0.5)), K.socket("TailRoot", (0, -0.5, 0.5))], [K.ucx_box(a, 0, (0.6, 0.95, 0.03), (0, -0.025, 0.5))], "0.6 x 1.45 m spirit kite; tail = 5 chained child nodes",
                 objects=objs))
    for v in range(3):
        a = G + "SkyIsle_%d" % v; R = K.rng(SEED + v, a); r = 0.9 + 0.35 * v
        P = [K.lathe("Rock", [(0, -r * 1.1), (r * 0.5, -r * 0.7), (r * 0.95, -r * 0.15), (r, 0), (0, 0)], (0, 0, 0), 0, 9), K.cyl("Turf", "z", r * 1.02, r * 1.0, 0.08, (0, 0, 0.04), 1, 9)]
        P += [rock("Boulder%d" % i, (r * 0.5 * math.cos(i * 2.1 + v), r * 0.5 * math.sin(i * 2.1 + v), 0.12), 0.1 + 0.05 * R.random(), 0, i) for i in range(2 + v)]
        out.append(A(a, P, [("floating rock", "7A7470", 0.95), ("sky turf", "6FBF5A", 0.9)], [K.socket("Land", (0, 0, 0.08)), K.socket("Lantern", (r * 0.4, 0, 0.08)), K.socket("Lane", (0, 0, 0.3))],
                     [K.ucx_box(a, 0, (2 * r, 2 * r, r * 1.2), (0, 0, -r * 0.5))], "floating isle variant %d, %.1f m across (graph node)" % (v, 2 * r)))
    mats = [("paper shade (emissive, tint = value MI)", "FFF0C0", 0.6, 0.0, True), ("frame", "3A2A20", 0.7)]
    a = G + "SpiritLantern"
    P = [K.cyl("Shade", "z", 0.1, 0.12, 0.26, (0, 0, 0.16), 0, 10), K.cyl("Top", "z", 0.05, 0.1, 0.03, (0, 0, 0.305), 1, 10), K.cyl("Bottom", "z", 0.12, 0.1, 0.03, (0, 0, 0.015), 1, 10), K.cyl("Hook", "z", 0.006, 0.006, 0.08, (0, 0, 0.36), 1, 4)]
    m = A(a, P, mats, [K.socket("Base", (0, 0, 0)), K.socket("Glow", (0, 0, 0.16)), K.socket("Hang", (0, 0, 0.4))], [K.ucx_box(a, 0, (0.24, 0.24, 0.4), (0, 0, 0.2))], "0.4 m spirit lantern; value 1-6 = MI tint")
    m["material_variants"] = {"MI_%s_V%d" % (a, i + 1): {"Tint": HUES[i], "Value": i + 1} for i in range(6)}
    out.append(m)
    a = G + "SkiffMooringPost"
    P = [K.cyl("Post", "z", 0.1, 0.12, 1.3, (0, 0, 0.65), 0, 10), K.cyl("Cap", "z", 0.14, 0.12, 0.08, (0, 0, 1.34), 1, 10), K.cyl("Cleat", "x", 0.025, 0.025, 0.3, (0, -0.12, 1.0), 1, 6),
         K.cyl("RopeCoil", "z", 0.15, 0.15, 0.05, (0, 0, 0.3), 2, 10), crystal("Prism", (0, 0, 1.38), 0.18, 3)]
    out.append(A(a, P, [("weathered post", WOOD, 0.85), ("iron fittings", "3A3A3E", 0.6, 0.6), ("rope", ROPE, 0.95), ("prism (emissive)", "A6E6FF", 0.2, 0.0, True)],
                 [K.socket("Mooring", (0, -0.15, 1.0)), K.socket("Floor", (0, 0, 0)), K.socket("Beacon", (0, 0, 1.5))], [K.ucx_box(a, 0, (0.3, 0.3, 1.56), (0, 0, 0.78))], "1.56 m Prism Skiff mooring post (anchor isle)"))
    wings = [K.slab("Wing%d" % s, [(0, 0), (s * 0.5, 0.15), (s * 0.45, -0.05)], 0.01, (s * 0.2, 0.1, 1.35), 4) for s in (-1, 1)]
    out.append(npc("Mob_Spiritkite_SkyLarkSpirit", "BFE6FF", "8CCBFF", wings + [K.cyl("KiteLine", "z", 0.004, 0.004, 0.5, (-0.37, 0, 1.12), 4, 4)],
                   [("spirit wings (emissive soft)", "E6F6FF", 0.6, 0.0, True)], "Sky Lark Spirit, kite-flier"))
    return out



def simple(a, parts, mats, socks, size, ucx_size=None, ucx_c=None):
    ucx = [K.ucx_box(a, 0, ucx_size, ucx_c)] if ucx_size else []
    return A(a, parts, mats, socks, ucx, size)


def shard_set(prefix, hues, h=0.14, mats_extra=()):
    out = []
    for i, hx in enumerate(hues):
        a = "%s_%d" % (prefix, i + 1)
        out.append(simple(a, [crystal("Shard", (0, 0, 0), h, 0)], [("shard (emissive)", hx, 0.15, 0.0, True)], [K.socket("Base", (0, 0, 0)), K.socket("Glow", (0, 0, h / 2))],
                          "%.2f m shard, hue %s" % (h, hx), (h * 0.4, h * 0.4, h), (0, 0, h / 2)))
    return out


def pouch(a, cloth, tie):
    P = [ball("Bag", (0, 0, 0.09), 0.09, 0, 8), K.cyl("Neck", "z", 0.035, 0.05, 0.05, (0, 0, 0.19), 0, 8), K.cyl("Tie", "z", 0.04, 0.04, 0.015, (0, 0, 0.18), 1, 8)]
    return simple(a, P, [("cloth", cloth, 0.95), ("tie cord", tie, 0.9)], [K.socket("Base", (0, 0, 0)), K.socket("Belt", (0, 0.09, 0.15)), K.socket("Grab", (0, 0, 0.2))],
                  "0.2 m pouch", (0.19, 0.19, 0.22), (0, 0, 0.11))


def plinth(a, top_hex, glyph_hex, h=0.9):
    P = [K.box("Base", (0.5, 0.5, 0.1), (0, 0, 0.05), 0), K.cyl("Column", "z", 0.16, 0.18, h - 0.2, (0, 0, 0.1 + (h - 0.2) / 2), 0, 8), K.box("Top", (0.42, 0.42, 0.1), (0, 0, h - 0.05), 0),
         K.box("Glyph", (0.2, 0.01, 0.2), (0, -0.175, h * 0.55), 1, bevel=False), ball("Spirit", (0, 0, h + 0.14), 0.11, 2, 8)]
    return simple(a, P, [("stone", STONE, 0.9), ("glyph (emissive)", glyph_hex, 0.3, 0.0, True), ("spirit (emissive)", top_hex, 0.3, 0.0, True)],
                  [K.socket("Spirit", (0, 0, h + 0.14)), K.socket("Floor", (0, 0, 0))], "%.2f m spirit plinth" % (h + 0.25), (0.5, 0.5, h), (0, 0, h / 2))


# ================================================================ glimmerloom (READY 58991)
@game("glimmerloom")
def glimmerloom():
    G = "Prop_Glimmerloom_"; out = []
    awn = [K.box("Awning%d" % i, (0.88 / 5, 0.5, 0.02), (-0.352 + 0.176 * i, -0.3, 2.12), 5 + i % 2, rot=(-15, 0, 0), bevel=False) for i in range(5)]
    out.append(cabinet("Prop_Arcade_Cab_GlimmerloomLedger", "7A4A2A", "C8A86A", "FFD27A", awn, [("awning red", "C8402A", 0.9), ("awning cream", "F2E6C8", 0.9)], "market-stall styling"))
    P = [K.box("Counter", (2.0, 0.7, 0.9), (0, 0, 0.45), 0), K.box("Top", (2.1, 0.75, 0.05), (0, 0, 0.925), 0)] + [K.box("Pole%d" % i, (0.06, 0.06, 2.2), (x, y, 1.1), 0) for i, (x, y) in enumerate(((-1, -0.35), (1, -0.35), (-1, 0.35), (1, 0.35)))]
    P += [K.box("Canopy", (2.2, 0.9, 0.04), (0, 0, 2.22), 1, rot=(-6, 0, 0)), K.box("LoomFrame", (0.9, 0.08, 0.9), (0.4, 0.2, 1.45), 0), K.box("Warp", (0.8, 0.02, 0.8), (0.4, 0.2, 1.45), 2, bevel=False),
          K.cyl("Beam", "x", 0.03, 0.03, 0.9, (0.4, 0.12, 1.0), 0, 8)]
    out.append(simple(G + "MarketStallLoom", P, [("stall wood", WOOD, 0.85), ("canopy cloth", "C8402A", 0.9), ("woven glimmer (emissive)", "E6B3FF", 0.4, 0.0, True)],
                      [K.socket("Trader", (0, 0.6, 0)), K.socket("Customer", (0, -0.9, 0)), K.socket("Loom", (0.4, 0.15, 1.45)), K.socket("Tray", (-0.5, 0, 0.95))], "2.2 m market stall with loom", (2.2, 0.9, 2.26), (0, 0, 1.13)))
    out += shard_set(G + "HuedShard", HUES[:5])
    out.append(simple(G + "Satchel", [K.box("Body", (0.32, 0.12, 0.24), (0, 0, 0.12), 0), K.box("Flap", (0.33, 0.13, 0.1), (0, -0.005, 0.2), 0, rot=(10, 0, 0)), K.box("StrapL", (0.03, 0.01, 0.28), (-0.13, 0, 0.36), 1, bevel=False), K.box("StrapR", (0.03, 0.01, 0.28), (0.13, 0, 0.36), 1, bevel=False), K.box("StrapTop", (0.29, 0.01, 0.03), (0, 0, 0.49), 1, bevel=False)],
                      [("leather", "7A4A2A", 0.8), ("strap", "4A2A1A", 0.8)], [K.socket("Shoulder", (0, 0, 0.5)), K.socket("Base", (0, 0, 0))], "0.32 m satchel", (0.34, 0.14, 0.5), (0, 0, 0.25)))
    P = [K.box("Board", (1.0, 0.05, 0.7), (0, 0, 1.35), 0), K.box("Leg%d" % 0, (0.05, 0.05, 1.0), (-0.45, 0, 0.5), 1), K.box("Leg1", (0.05, 0.05, 1.0), (0.45, 0, 0.5), 1)]
    S = [K.socket("Floor", (0, 0, 0))]
    for i in range(5):
        P += [K.box("Slot%d" % i, (0.16, 0.01, 0.5), (-0.38 + 0.19 * i, -0.03, 1.33), 2, bevel=False), K.box("Chip%d" % i, (0.08, 0.012, 0.08), (-0.38 + 0.19 * i, -0.035, 1.58), 3 + 0, bevel=False)]
        S.append(K.socket("Price_%d" % i, (-0.38 + 0.19 * i, -0.04, 1.33)))
    out.append(simple(G + "PriceBoard", P, [("chalkboard frame", WOOD, 0.85), ("legs", "4A2A1A", 0.8), ("chalk slot (text = widget)", "2A3A2A", 0.95), ("hue chip (MI tint)", "FFFFFF", 0.4, 0.0, True)],
                      S, "1.0 x 1.7 m price board, 5 slots", (1.0, 0.1, 1.7), (0, 0, 0.85)))
    out.append(pouch(G + "CoinPurse", "8A5A2A", GOLD))
    out.append(npc("Mob_Glimmerloom_ShardTrader", "8A3A6A", "4A2A1A", [K.box("Apron", (0.4, 0.02, 0.5), (0, -0.14, 1.0), 4)], [("apron", "E6D8B0", 0.9)], "Shard trader"))
    out.append(npc("Mob_Glimmerloom_WhisperingWarden", "3A3A5A", "2A2A3A", [K.cyl("Hood", "z", 0.16, 0.08, 0.3, (0, 0.02, 1.72), 4, 8), K.box("Veil", (0.3, 0.02, 0.2), (0, -0.14, 1.58), 5, bevel=False)],
                   [("hood", "2A2A4A", 0.9), ("veil glow (emissive)", "B3A6FF", 0.5, 0.0, True)], "Whispering Warden"))
    return out


# ================================================================ shadewatch (READY 58992)
@game("shadewatch")
def shadewatch():
    G = "Prop_Shadewatch_"; out = []
    stars = [ball("Star%d" % i, (-0.3 + 0.12 * i, -0.17, 2.1 + 0.03 * (i % 2)), 0.015, 5, 4) for i in range(6)] + [K.cyl("Moon", "y", 0.06, 0.06, 0.02, (0.32, -0.16, 2.12), 5, 10)]
    out.append(cabinet("Prop_Arcade_Cab_ShadewatchVigil", "141A30", "2A3A6A", "7A9CFF", stars, [("stars / moon (emissive)", "FFF2C8", 0.3, 0.0, True)], "night styling"))
    a = G + "HeartCrystal"; P = [K.cyl("Base", "z", 0.35, 0.4, 0.15, (0, 0, 0.075), 1, 8), crystal("Heart", (0, 0, 0.15), 0.9, 0), K.box("Rune", (0.2, 0.02, 0.06), (0, -0.37, 0.1), 2, bevel=False)]
    m = simple(a, P, [("heart crystal (emissive, state = MI)", "FF4A7A", 0.15, 0.0, True), ("plinth stone", STONE, 0.9), ("rune", "FFD27A", 0.3, 0.0, True)],
               [K.socket("Glow", (0, 0, 0.6)), K.socket("Floor", (0, 0, 0)), K.socket("Hit", (0, -0.2, 0.6))], "1.05 m heart-crystal; states via MI", (0.8, 0.8, 1.05), (0, 0, 0.525))
    m["material_variants"] = {"MI_%s_Whole" % a: {"Emissive": 6.0, "Crack": 0.0}, "MI_%s_Cracked" % a: {"Emissive": 3.0, "Crack": 0.6}, "MI_%s_Shattered" % a: {"Emissive": 0.5, "Crack": 1.0}}
    out.append(m)
    for k, nm in enumerate(("Straight", "Fork", "End")):
        a = G + "LaneTile_" + nm; P = [K.box("Slab", (2.0, 2.0, 0.1), (0, 0, 0.05), 0), K.box("Path", (0.6, 2.0 if nm != "End" else 1.2, 0.02), (0, 0 if nm != "End" else -0.4, 0.11), 1, bevel=False)]
        if nm == "Fork": P.append(K.box("Branch", (0.6, 1.2, 0.02), (0.5, 0.5, 0.11), 1, bevel=False, rot=(0, 0, -45)))
        out.append(simple(a, P, [("night ground", "2A3028", 0.95), ("lane path (faint glow)", "4A5A8A", 0.7, 0.0, True)], [K.socket("Entry", (0, -1.0, 0.1)), K.socket("Exit", (0, 1.0, 0.1))],
                          "2 x 2 m lane tile (%s)" % nm.lower(), (2.0, 2.0, 0.12), (0, 0, 0.06)))
    a = "Mob_Shadewatch_ShadeCreature"; P = [ball("Core", (0, 0, 0.7), 0.25, 0, 10)] + [K.lathe("Wisp%d" % i, [(0, 0), (0.08, 0.15), (0.03, 0.5), (0, 0.6)], (0.15 * math.cos(i * 2.1), 0.15 * math.sin(i * 2.1), 0.1), 0, 6, rot=(10 * math.cos(i), 10 * math.sin(i), 0)) for i in range(3)]
    P += [ball("Eye%d" % s, (s * 0.08, -0.22, 0.78), 0.035, 1, 6) for s in (-1, 1)]
    out.append(simple(a, P, [("shade body (dissolve = MI param)", "1A1030", 0.9), ("eyes (emissive)", "B3FF4A", 0.3, 0.0, True)], [K.socket("Core", (0, 0, 0.7)), K.socket("Floor", (0, 0, 0))],
                      "0.95 m wispy shade (dissolvable via MI Dissolve 0..1)", (0.6, 0.6, 0.95), (0, 0, 0.475)))
    a = G + "FlareTorch"; P = [K.cyl("Handle", "z", 0.02, 0.025, 0.4, (0, 0, 0.2), 0, 8), K.cyl("Head", "z", 0.04, 0.03, 0.1, (0, 0, 0.45), 1, 8), K.lathe("Flare", [(0, 0), (0.035, 0.03), (0, 0.12)], (0, 0, 0.5), 2, 6)]
    out.append(simple(a, P, [("handle", WOOD, 0.85), ("iron head", "3A3A3E", 0.6, 0.6), ("flare (emissive red)", "FF5A3A", 0.3, 0.0, True)], [K.socket("Grip", (0, 0, 0.15)), K.socket("Flame", (0, 0, 0.56))],
                      "0.62 m flare torch", (0.1, 0.1, 0.62), (0, 0, 0.31)))
    a = G + "NovaBurstMesh"; P = [ball("Core", (0, 0, 0), 0.15, 0, 10)] + [K.lathe("Ray%d" % i, [(0, 0), (0.04, 0.05), (0, 0.6)], (0, 0, 0), 0, 4, rot=(90 * (i // 4) + 45 * (i % 2), 0, 90 * (i % 4))) for i in range(8)]
    out.append(simple(a, P, [("nova (emissive, scale/fade in VFX)", "FFF2C8", 0.2, 0.0, True)], [K.socket("Centre", (0, 0, 0))], "1.2 m nova burst VFX mesh (origin = centre)"))
    out.append(npc("Mob_Shadewatch_WardenWatcher", "2A3A6A", "1A1A2A", [K.cyl("Spear", "z", 0.015, 0.015, 1.9, (-0.37, 0, 0.95), 4, 6), K.lathe("Tip", [(0, 0), (0.03, 0.03), (0, 0.15)], (-0.37, 0, 1.9), 5, 4)],
                   [("spear shaft", WOOD, 0.85), ("spear tip (emissive)", "7A9CFF", 0.3, 0.0, True)], "Warden watcher"))
    return out


# ================================================================ shardfall (READY 58993)
@game("shardfall")
def shardfall():
    G = "Prop_Shardfall_"; out = []
    falls = [crystal("Fall%d" % i, (-0.3 + 0.12 * i, -0.17, 2.0 + 0.08 * (i % 3)), 0.09, 5, rot=(180, 0, 0)) for i in range(6)]
    out.append(cabinet("Prop_Arcade_Cab_ShardfallGamble", "3A2A20", "8A6A3A", "FFB347", falls, [("falling shards (emissive)", "A6E6FF", 0.2, 0.0, True)], "seam-mine styling"))
    a = G + "SeamRockFace"; R = K.rng(SEED, a); P = [K.box("Face", (3.0, 0.6, 2.4), (0, 0.3, 1.2), 0)] + [rock("Lump%d" % i, (-1.2 + 0.6 * i, 0.0, 0.4 + 0.5 * (i % 3)), 0.25, 0, i) for i in range(5)]
    S = [K.socket("Floor", (0, 0, 0))]
    for i in range(5):
        x, z = -1.0 + 0.5 * i, 0.8 + 0.35 * ((i * 3) % 4); P.append(K.box("Seam%d" % i, (0.35, 0.03, 0.06), (x, -0.01, z), 1, rot=(0, 20 - 10 * i, 0), bevel=False)); S.append(K.socket("Seam_%d" % i, (x, -0.03, z)))
    out.append(simple(a, P, [("rock face", "6A5A4A", 0.95), ("seam glint (emissive)", "A6E6FF", 0.3, 0.0, True)], S, "3 x 2.4 m shard seam rock face, 5 seam sockets", (3.0, 0.8, 2.4), (0, 0.2, 1.2)))
    out.append(pouch(G + "SeamBag", "6A5A3A", ROPE))
    out += shard_set(G + "ValuedShard", ["8CA0B0", "73F28C", "338CFF", "B36BFF", "FFD27A"], 0.12)
    a = G + "CrackedShard"; P = [crystal("Half%d" % s, (s * 0.02, 0, 0), 0.12, 0, rot=(0, s * 12, 0)) for s in (-1, 1)]
    out.append(simple(a, P, [("cracked shard (dull, low emissive)", "8A8A9A", 0.4, 0.0, True)], [K.socket("Base", (0, 0, 0))], "0.12 m cracked shard (bust)", (0.1, 0.06, 0.12), (0, 0, 0.06)))
    a = G + "PotBowl"; P = [K.lathe("Bowl", [(0, 0), (0.12, 0.0), (0.2, 0.08), (0.22, 0.12), (0.19, 0.12), (0.17, 0.08), (0.0, 0.03)], (0, 0, 0), 0, 14)]
    out.append(simple(a, P, [("hammered copper", "B87333", 0.4, 0.8)], [K.socket("Pot", (0, 0, 0.05)), K.socket("Base", (0, 0, 0))], "0.44 m pot bowl", (0.44, 0.44, 0.12), (0, 0, 0.06)))
    out.append(npc("Mob_Shardfall_SeamMiner", "6A5A40", "3A3A3A", [K.cyl("Pick", "x", 0.015, 0.015, 0.5, (-0.37, 0, 0.88), 4, 6), K.box("PickHead", (0.04, 0.35, 0.04), (-0.6, 0, 0.88), 5)],
                   [("pick handle", WOOD, 0.85), ("pick iron", "3A3A3E", 0.6, 0.6)], "Seam miner"))
    return out


# ================================================================ prismcairn (READY 58994)
@game("prismcairn")
def prismcairn():
    G = "Prop_Prismcairn_"; out = []
    cairn = [K.box("Stone%d" % i, (0.3 - 0.06 * i, 0.12, 0.08), (0, -0.16, 2.08 + 0.08 * i), 5, rot=(0, 0, 8 * (-1) ** i)) for i in range(4)]
    out.append(cabinet("Prop_Arcade_Cab_PrismcairnDuel", "4A4A5A", "8A8A9A", "A6E6FF", cairn, [("cairn stone", STONE, 0.9)], "cairn-stack topper"))
    for i, (w, h) in enumerate(((0.5, 0.18), (0.42, 0.16), (0.34, 0.14), (0.26, 0.12), (0.18, 0.1))):
        a = G + "CairnPiece_%d" % (i + 1)
        P = [K.box("Stone", (w, w * 0.8, h), (0, 0, h / 2), 0), K.box("Inlay", (w * 0.5, 0.01, h * 0.4), (0, -w * 0.4 - 0.004, h / 2), 1, bevel=False)]
        out.append(simple(a, P, [("cairn stone", STONE, 0.9), ("prism inlay (emissive)", HUES[i], 0.3, 0.0, True)], [K.socket("Bottom", (0, 0, 0)), K.socket("Top", (0, 0, h))],
                          "cairn piece %d, %.2f m wide (stack via SOCKET_Top)" % (i + 1, w), (w, w * 0.8, h), (0, 0, h / 2)))
    a = G + "CairnCircleBase"; P = [K.cyl("Disc", "z", 1.5, 1.55, 0.12, (0, 0, 0.06), 0, 16)]; S = [K.socket("Centre", (0, 0, 0.12))]
    for i in range(6):
        an = i * math.pi / 3; P.append(K.box("Marker%d" % i, (0.18, 0.18, 0.3), (1.3 * math.cos(an), 1.3 * math.sin(an), 0.27), 1, rot=(0, 0, math.degrees(an)))); S.append(K.socket("Seat_%d" % i, (0.8 * math.cos(an), 0.8 * math.sin(an), 0.12)))
    out.append(simple(a, P, [("flagstone", "8A8680", 0.9), ("standing marker", STONE, 0.9)], S, "3.1 m cairn circle base, 6 seats", (3.1, 3.1, 0.42), (0, 0, 0.21)))
    out.append(npc("Mob_Prismcairn_CairnWarden", "5A5A6A", "3A3A4A", [K.cyl("Staff", "z", 0.02, 0.02, 1.7, (-0.37, 0, 0.85), 4, 6), crystal("StaffGem", (-0.37, 0, 1.7), 0.15, 5)],
                   [("staff", WOOD, 0.85), ("staff gem (emissive)", "A6E6FF", 0.2, 0.0, True)], "Cairn Warden"))
    return out


# ================================================================ wardens_accord (READY 58995)
SPIRITS = {"CinderWisp": "FF6B2E", "MereSprite": "338CFF", "Thornkin": "73F28C", "SkyLarkSpirit": "BFE6FF", "HollowMoth": "B36BFF"}


@game("wardens_accord")
def wardens_accord():
    G = "Prop_WardensAccord_"; out = []
    seal = [K.cyl("Seal", "y", 0.12, 0.12, 0.03, (0, -0.17, 2.1), 5, 12)]
    out.append(cabinet("Prop_Arcade_Cab_WardensAccord", "3A2A4A", "8A6AA0", "E6B3FF", seal, [("accord seal (gold)", GOLD, 0.3, 0.9)], "accord-seal topper"))
    a = G + "WardenAltar"; P = [K.box("Base", (1.6, 0.8, 0.2), (0, 0, 0.1), 0), K.box("Table", (1.4, 0.6, 0.7), (0, 0, 0.55), 0), K.box("Top", (1.5, 0.7, 0.06), (0, 0, 0.93), 1)]
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Warden", (0, 0.7, 0))]
    for i in range(3):
        x = -0.45 + 0.45 * i; P.append(K.cyl("Offer%d" % i, "z", 0.13, 0.11, 0.04, (x, -0.05, 0.98), 2, 12)); S.append(K.socket("Offer_%d" % i, (x, -0.05, 1.0)))
    out.append(simple(a, P, [("altar stone", "7A7484", 0.9), ("altar cap", "5A5464", 0.85), ("offer bowls (emissive rim)", GOLD, 0.3, 0.0, True)], S, "1.6 m Warden altar, 3 offer slots", (1.6, 0.8, 1.0), (0, 0, 0.5)))
    out.append(pouch(G + "ShardPouch", "5A3A6A", GOLD))
    for nm, hx in SPIRITS.items():
        out.append(plinth(G + "SpiritPlinth_" + nm, hx, hx))
    out.append(npc("Mob_WardensAccord_AltarWarden", "5A3A6A", "2A1A3A", [K.box("Stole", (0.1, 0.02, 0.6), (0, -0.14, 1.15), 4, bevel=False)], [("stole (gold)", GOLD, 0.4, 0.6)], "Altar Warden"))
    return out


# ================================================================ facetlock (READY 58996)
@game("facetlock")
def facetlock():
    G = "Prop_Facetlock_"; out = []
    lat = [K.box("Lat%d" % i, (0.06, 0.012, 0.06), (-0.08 + 0.08 * (i % 3), -0.17, 2.03 + 0.07 * (i // 3)), 5, bevel=False) for i in range(6)]
    out.append(cabinet("Prop_Arcade_Cab_FacetlockLattice", "2A2A3A", "6A6A8A", "73F28C", lat, [("lattice tiles (emissive)", "A6E6FF", 0.3, 0.0, True)], "vault-lattice topper"))
    for n in (3, 4, 5):
        a = G + "VaultDoor_%dx%d" % (n, n); W = 0.4 * n + 0.4
        P = [K.box("Frame", (W + 0.4, 0.4, W + 0.4), (0, 0.2, (W + 0.4) / 2), 0), K.box("Door", (W, 0.1, W), (0, -0.05, (W + 0.4) / 2), 1)]
        S = [K.socket("Floor", (0, 0, 0))]
        for r in range(n):
            for c in range(n):
                x, z = -0.2 * (n - 1) + 0.4 * c, (W + 0.4) / 2 + 0.2 * (n - 1) - 0.4 * r; P.append(K.box("Recess%d%d" % (r, c), (0.36, 0.02, 0.36), (x, -0.105, z), 2, bevel=False)); S.append(K.socket("Tile_%d_%d" % (r, c), (x, -0.12, z)))
        out.append(simple(a, P, [("vault stone", "6A6A7A", 0.9), ("vault door (bronze)", "8A6A3A", 0.5, 0.8), ("tile recess", "1A1A2A", 0.9)], S, "%.1f m vault door, %dx%d facet lattice" % (W + 0.4, n, n), (W + 0.4, 0.4, W + 0.4), (0, 0.2, (W + 0.4) / 2)))
    for i, hx in enumerate(HUES[:5]):
        a = G + "FacetTile_%d" % (i + 1); P = [K.box("Tile", (0.34, 0.04, 0.34), (0, 0, 0.17), 0), K.lathe("Facet", [(0, 0), (0.12, 0.0), (0, 0.04)], (0, -0.02, 0.17), 1, 6, rot=(90, 0, 0))]
        out.append(simple(a, P, [("tile body", "3A3A4A", 0.6), ("facet (emissive)", hx, 0.2, 0.0, True)], [K.socket("Mount", (0, 0.02, 0.17))], "0.34 m facet tile, hue %d" % (i + 1), (0.34, 0.08, 0.34), (0, 0, 0.17)))
    out.append(npc("Mob_Facetlock_VaultKeeper", "4A4A3A", "2A2A2A", [K.cyl("KeyRing", "y", 0.06, 0.06, 0.01, (-0.37, 0, 0.8), 4, 10)], [("brass keys", "B08D3C", 0.4, 0.8)], "Vault keeper"))
    return out


# ================================================================ prismvault (READY 58997)
@game("prismvault")
def prismvault():
    G = "Prop_Prismvault_"; out = []
    sc = [K.box("Beam", (0.4, 0.02, 0.02), (0, -0.17, 2.12), 5), K.cyl("PanL", "z", 0.06, 0.05, 0.02, (-0.18, -0.17, 2.05), 5, 8), K.cyl("PanR", "z", 0.06, 0.05, 0.02, (0.18, -0.17, 2.05), 5, 8)]
    out.append(cabinet("Prop_Arcade_Cab_PrismvaultWeigh", "2A3A3A", "6A8A8A", "FFD27A", sc, [("scale brass", "B08D3C", 0.4, 0.8)], "balance-scale topper"))
    a = G + "BalanceScale"; P = [K.box("Base", (0.6, 0.4, 0.08), (0, 0, 0.04), 0), K.cyl("Post", "z", 0.04, 0.05, 1.1, (0, 0, 0.63), 0, 8), K.box("Arm", (1.2, 0.05, 0.05), (0, 0, 1.2), 0)]
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Pivot", (0, 0, 1.2))]
    for s, nm in ((-1, "L"), (1, "R")):
        P += [K.cyl("Chain%s" % nm, "z", 0.005, 0.005, 0.4, (s * 0.55, 0, 0.98), 0, 4), K.lathe("Pan%s" % nm, [(0, 0), (0.18, 0.02), (0.2, 0.06), (0.17, 0.06), (0, 0.02)], (s * 0.55, 0, 0.72), 0, 12)]; S.append(K.socket("Pan_" + nm, (s * 0.55, 0, 0.76)))
    out.append(simple(a, P, [("brass", "B08D3C", 0.35, 0.9)], S, "1.2 m Warden's balance scale (two pans; tilt in UE)", (1.2, 0.4, 1.23), (0, 0, 0.615)))
    a = G + "ShardTray"; P = [K.box("Tray", (0.9, 0.9, 0.05), (0, 0, 0.025), 0)]; S = [K.socket("Base", (0, 0, 0))]
    for i in range(27):
        r, c = divmod(i, 6) if i < 24 else (4, i - 24)
        x, y = -0.375 + 0.15 * c, 0.3 - 0.15 * r; P.append(K.cyl("Well%d" % i, "z", 0.05, 0.05, 0.01, (x, y, 0.055), 1, 6)); S.append(K.socket("Slot_%02d" % i, (x, y, 0.06)))
    out.append(simple(a, P, [("velvet tray", "3A1A2A", 0.95), ("slot wells", "1A0A12", 0.95)], S, "0.9 m shard tray, 27 slots", (0.9, 0.9, 0.06), (0, 0, 0.03)))
    a = G + "HollowShard"; P = [crystal("Shell", (0, 0, 0), 0.14, 0)]
    out.append(simple(a, P, [("hollow shard (subtly dimmer, 0.9 emissive)", "C8E6F0", 0.25, 0.0, True)], [K.socket("Base", (0, 0, 0))], "0.14 m hollow shard (subtle variant)", (0.05, 0.05, 0.14), (0, 0, 0.07)))
    out.append(npc("Mob_Prismvault_VaultWarden", "2A4A4A", "1A2A2A", [K.box("Ledger", (0.2, 0.03, 0.26), (-0.37, -0.05, 0.95), 4)], [("ledger", "6A2A1A", 0.8)], "Vault Warden"))
    return out


# ================================================================ lumenpath (READY 58998)
@game("lumenpath")
def lumenpath():
    G = "Prop_Lumenpath_"; out = []
    beam = [K.box("Beam%d" % i, (0.16, 0.012, 0.02), (-0.2 + 0.14 * i, -0.17, 2.0 + 0.06 * (i % 2)), 5, rot=(0, 30 * (-1) ** i, 0), bevel=False) for i in range(4)]
    out.append(cabinet("Prop_Arcade_Cab_LumenpathRefraction", "1A2A3A", "4A6A8A", "FFF299", beam, [("light beam (emissive)", "FFF2C8", 0.2, 0.0, True)], "refraction-beam topper"))
    a = G + "LatticeFloorGrid"; P = [K.box("Slab", (4.0, 4.0, 0.08), (0, 0, 0.04), 0)] + [K.box("LineX%d" % i, (4.0, 0.03, 0.01), (0, -2 + 0.8 * i, 0.085), 1, bevel=False) for i in range(6)] + [K.box("LineY%d" % i, (0.03, 4.0, 0.01), (-2 + 0.8 * i, 0, 0.085), 1, bevel=False) for i in range(6)]
    out.append(simple(a, P, [("lattice floor", "2A2A3A", 0.8), ("grid lines (emissive)", "4A8AFF", 0.4, 0.0, True)], [K.socket("Origin", (-2, -2, 0.08)), K.socket("Floor", (0, 0, 0))], "4 x 4 m lattice floor, 0.8 m cells (5x5)", (4.0, 4.0, 0.09), (0, 0, 0.045)))
    for nm, rz in (("Slash", 45), ("Backslash", -45)):
        a = G + "ShardMirror_" + nm; P = [K.box("Base", (0.3, 0.3, 0.06), (0, 0, 0.03), 0), K.box("Mirror", (0.6, 0.04, 0.5), (0, 0, 0.33), 1, rot=(0, 0, rz)), K.box("Frame", (0.64, 0.03, 0.54), (0, 0, 0.33), 0, rot=(0, 0, rz))]
        out.append(simple(a, P, [("frame", "6A6A7A", 0.5, 0.6), ("mirror", "D8F0FF", 0.05, 1.0)], [K.socket("Floor", (0, 0, 0)), K.socket("Reflect", (0, 0, 0.33))], "0.6 m shard mirror (%s)" % nm.lower(), (0.5, 0.5, 0.6), (0, 0, 0.3)))
    for st, hx, glow in (("Lit", "FFF299", True), ("Unlit", "6A7A8A", False)):
        a = G + "Crystal_" + st; P = [K.cyl("Base", "z", 0.15, 0.17, 0.06, (0, 0, 0.03), 1, 8), crystal("Crystal", (0, 0, 0.06), 0.5, 0)]
        out.append(simple(a, P, [("crystal" + (" (emissive)" if glow else ""), hx, 0.15, 0.0, glow), ("base", STONE, 0.9)], [K.socket("Floor", (0, 0, 0)), K.socket("Glow", (0, 0, 0.3))], "0.56 m crystal, %s" % st.lower(), (0.34, 0.34, 0.56), (0, 0, 0.28)))
    a = G + "CrackedStoneBlock"; P = [K.box("Half%d" % s, (0.39, 0.8, 0.8), (s * 0.205, 0, 0.4), 0, rot=(0, 0, s * 2)) for s in (-1, 1)] + [K.box("Crack", (0.02, 0.82, 0.82), (0, 0, 0.4), 1, bevel=False)]
    out.append(simple(a, P, [("stone block", STONE, 0.9), ("crack (dark)", "1A1A1A", 0.9)], [K.socket("Floor", (0, 0, 0))], "0.8 m cracked stone block (beam blocker)", (0.82, 0.82, 0.8), (0, 0, 0.4)))
    a = G + "BeamEmitter"; P = [K.box("Base", (0.4, 0.4, 0.2), (0, 0, 0.1), 0), K.cyl("Barrel", "y", 0.09, 0.07, 0.35, (0, -0.15, 0.32), 0, 10), K.cyl("Lens", "y", 0.06, 0.06, 0.02, (0, -0.33, 0.32), 1, 10)]
    out.append(simple(a, P, [("emitter brass", "B08D3C", 0.4, 0.8), ("lens (emissive)", "FFF2C8", 0.2, 0.0, True)], [K.socket("Floor", (0, 0, 0)), K.socket("Beam", (0, -0.35, 0.32))], "0.5 m beam emitter (fires -Y)", (0.4, 0.55, 0.42), (0, -0.075, 0.21)))
    out.append(npc("Mob_Lumenpath_LatticeKeeper", "3A4A6A", "2A2A3A", [crystal("Lens", (-0.37, 0, 0.9), 0.12, 4)], [("lens shard (emissive)", "FFF299", 0.2, 0.0, True)], "Lattice keeper"))
    return out


# ================================================================ shardring (READY 58999)
@game("shardring")
def shardring():
    G = "Prop_Shardring_"; out = []
    roof = [K.lathe("ShrineRoof", [(0, 0), (0.5, 0.0), (0.3, 0.12), (0, 0.22)], (0, 0.05, 2.06), 5, 4, rot=(0, 0, 45))]
    out.append(cabinet("Prop_Arcade_Cab_ShardringResonance", "5A4A3A", "C8B48A", "A6E6FF", roof, [("shrine roof", "4A3A5A", 0.8)], "Windmere shrine styling"))
    a = G + "PrismSphereRing"; P = [ball("Sphere", (0, 0, 1.0), 0.35, 0, 12), K.cyl("Stand", "z", 0.25, 0.35, 0.65, (0, 0, 0.325), 1, 10)]; S = [K.socket("Floor", (0, 0, 0)), K.socket("Core", (0, 0, 1.0))]
    for i in range(6):
        an = i * math.pi / 3; x, y = 0.55 * math.cos(an), 0.55 * math.sin(an); P.append(crystal("Facet%d" % i, (x, y, 0.88), 0.28, 2)); S.append(K.socket("Facet_%d" % i, (x, y, 0.88)))
        P.append(K.box("Spoke%d" % i, (0.42, 0.04, 0.04), (0.36 * math.cos(an), 0.36 * math.sin(an), 0.86), 3, rot=(0, 0, math.degrees(an))))
    out.append(simple(a, P, [("prism sphere (emissive)", "A6E6FF", 0.15, 0.0, True), ("stone stand", STONE, 0.9), ("facet ring (emissive)", "E6B3FF", 0.2, 0.0, True), ("ring spokes (gold)", GOLD, 0.3, 0.9)], S, "1.35 m prism sphere with 6-facet ring", (1.3, 1.3, 1.35), (0, 0, 0.675)))
    out += shard_set(G + "PrismShard", HUES[:3])
    out.append(pouch(G + "ShardPouch", "3A5A6A", GOLD))
    for nm, hx in SPIRITS.items():
        a = "Prop_Shardring_SummonFigure_" + nm; P = [K.cyl("Base", "z", 0.06, 0.07, 0.03, (0, 0, 0.015), 1, 8), ball("Body", (0, 0, 0.11), 0.06, 0, 8), ball("Head", (0, -0.01, 0.2), 0.04, 0, 8)]
        out.append(simple(a, P, [("spirit figure (emissive)", hx, 0.4, 0.0, True), ("base", "3A3A3A", 0.8)], [K.socket("Base", (0, 0, 0))], "0.24 m summon figure: %s" % nm, (0.14, 0.14, 0.24), (0, 0, 0.12)))
    out.append(npc("Mob_Shardring_ShrineWarden", "C8B48A", "5A4A3A", [K.cyl("Bell", "z", 0.06, 0.04, 0.08, (-0.37, 0, 0.8), 4, 8)], [("shrine bell", GOLD, 0.3, 0.9)], "Shrine Warden"))
    return out


# ================================================================ star_mesh (art-master-flex, READY 59021)
@game("star_mesh")
def star_mesh():
    G = "Prop_StarMesh_"; out = []
    top = [K.cyl("OrreryPost", "z", 0.015, 0.015, 0.14, (0, 0.05, 2.13), 5, 6), ball("OrreryGlobe", (0, 0.05, 2.27), 0.09, 6, 10),
           K.box("OrreryRing", (0.32, 0.015, 0.015), (0, 0.05, 2.27), 5, bevel=False, rot=(0, 20, 0))]
    out.append(cabinet("Prop_Arcade_Cab_StarMeshOrrery", "6A4A28", "B08D3C", "BFD9FF", top, [("brass", "B08D3C", 0.35, 0.9), ("orrery glass (emissive)", "A6C8FF", 0.1, 0.0, True)], "brass/glass, orrery topper"))
    a = G + "StarChartTable"; P = [K.cyl("Top", "z", 0.7, 0.7, 0.05, (0, 0, 0.775), 0, 24), K.cyl("Leg", "z", 0.08, 0.1, 0.7, (0, 0, 0.4), 0, 10), K.cyl("Foot", "z", 0.35, 0.4, 0.05, (0, 0, 0.025), 0, 12)]
    for i in range(-3, 4):
        L = 2 * math.sqrt(max(0.0, 0.62 ** 2 - (i * 0.17) ** 2))
        P += [K.box("GridX%d" % i, (L, 0.008, 0.004), (0, i * 0.17, 0.802), 1, bevel=False), K.box("GridY%d" % i, (0.008, L, 0.004), (i * 0.17, 0, 0.802), 1, bevel=False)]
    out.append(simple(a, P, [("wood", WOOD, 0.7), ("inlaid grid (brass)", "C8A65A", 0.35, 0.8)], [K.socket("Floor", (0, 0, 0)), K.socket("ChartCentre", (0, 0, 0.805))],
                      "1.4 m round star chart table, inlaid 0.17 m grid", (1.4, 1.4, 0.8), (0, 0, 0.4)))
    for st, hx, glow in (("Lit", "FFF2B3", True), ("Unlit", "4A5468", False)):
        a = G + "StarPeg_" + st; P = [K.cyl("Pin", "z", 0.006, 0.006, 0.03, (0, 0, 0.015), 1, 6), ball("Star", (0, 0, 0.04), 0.015, 0, 8)]
        out.append(simple(a, P, [("star" + (" (emissive)" if glow else ""), hx, 0.2, 0.0, glow), ("pin brass", "B08D3C", 0.35, 0.9)], [K.socket("Base", (0, 0, 0)), K.socket("Thread", (0, 0, 0.04))],
                          "5.5 cm star peg, %s" % st.lower(), (0.03, 0.03, 0.055), (0, 0, 0.0275)))
    a = G + "ChartThread"; out.append(simple(a, [K.cyl("Thread", "x", 0.002, 0.002, 1.0, (0.5, 0, 0.002), 0, 6)], [("silver thread", "D8DCE4", 0.2, 1.0)],
                                             [K.socket("Start", (0, 0, 0.002)), K.socket("End", (1.0, 0, 0.002))], "1 m taut silver thread (scale X to edge length; pivot at Start)", (1.0, 0.01, 0.01), (0.5, 0, 0.005)))
    a = G + "SightingGlass"; P = [K.cyl("Tube", "y", 0.022, 0.03, 0.26, (0, 0, 0.05), 0, 10), K.cyl("Eyepiece", "y", 0.016, 0.016, 0.04, (0, 0.15, 0.05), 0, 8),
                                  K.cyl("Objective", "y", 0.032, 0.032, 0.01, (0, -0.135, 0.05), 1, 10), K.box("Grip", (0.025, 0.04, 0.05), (0, 0.04, 0.0), 2)]
    out.append(simple(a, P, [("brass", "B08D3C", 0.35, 0.9), ("lens glass", "A6C8FF", 0.05), ("leather grip", "5A3A22", 0.85)], [K.socket("Grip", (0, 0.04, 0.0)), K.socket("Eye", (0, 0.17, 0.05)), K.socket("Aim", (0, -0.14, 0.05))],
                      "0.3 m handheld brass sighting scope (aims -Y)", (0.07, 0.31, 0.11), (0, 0, 0.03)))
    a = G + "FlipTallyBoard"; P = [K.box("Frame", (0.5, 0.04, 0.36), (0, 0, 0.18), 0), K.box("Slate", (0.44, 0.01, 0.3), (0, -0.022, 0.18), 1, bevel=False)]
    P += [K.box("Tally%d" % i, (0.008, 0.004, 0.07), (-0.17 + 0.03 * i, -0.028, 0.25), 2, bevel=False) for i in range(4)] + [K.box("TallyX", (0.14, 0.004, 0.008), (-0.125, -0.029, 0.25), 2, bevel=False, rot=(0, -25, 0))]
    out.append(simple(a, P, [("wood frame", WOOD, 0.7), ("slate", "2A2E30", 0.9), ("chalk", "E8E8E0", 0.95)], [K.socket("Floor", (0, 0, 0)), K.socket("Flips", (-0.12, -0.03, 0.25)), K.socket("Answer", (0.1, -0.03, 0.12))],
                      "0.5 m slate tally board", (0.5, 0.04, 0.36), (0, 0, 0.18)))
    coat = [K.box("CoatTail", (0.44, 0.28, 0.4), (0, 0.0, 0.72), 0), K.cyl("Hat", "z", 0.15, 0.12, 0.08, (0, -0.01, 1.78), 1, 10)]
    out.append(npc("Mob_StarMesh_NavigatorWren", "4A3A2A", "2A3A4A", coat + [K.cyl("Scope", "y", 0.02, 0.025, 0.2, (-0.37, -0.05, 0.86), 4, 8)], [("brass scope", "B08D3C", 0.35, 0.9)], "Navigator Wren, long coat"))
    return out



def bird(a, body_hex, wing_hex, beak_hex, s=1.0, note="", pose="perch"):
    """Static bird placeholder (rig pending). s = scale; ~0.4 m long at s=1. Front -Y."""
    P = [ball("Body", (0, 0, 0.12 * s), 0.09 * s, 0, 10), ball("Head", (0, -0.1 * s, 0.2 * s), 0.05 * s, 0, 8),
         K.cyl("Beak", "y", 0.018 * s, 0.002 * s, 0.06 * s, (0, -0.17 * s, 0.195 * s), 2, 6), K.box("Tail", (0.06 * s, 0.1 * s, 0.015 * s), (0, 0.12 * s, 0.13 * s), 1, bevel=False, rot=(15, 0, 0))]
    if pose == "glide":
        P += [K.box("Wing%d" % k, (0.32 * s, 0.09 * s, 0.012 * s), (k * 0.2 * s, 0, 0.15 * s), 1, bevel=False, rot=(0, -k * 8, 0)) for k in (-1, 1)]
    else:
        P += [K.box("Wing%d" % k, (0.02 * s, 0.16 * s, 0.07 * s), (k * 0.085 * s, 0.02 * s, 0.13 * s), 1, bevel=False) for k in (-1, 1)]
        P += [K.cyl("Leg%d" % k, "z", 0.006 * s, 0.006 * s, 0.05 * s, (k * 0.03 * s, 0, 0.025 * s), 2, 4) for k in (-1, 1)]
    S = [K.socket("Perch", (0, 0, 0)), K.socket("Head", (0, -0.1 * s, 0.22 * s)), K.socket("Beak", (0, -0.2 * s, 0.195 * s))]
    w = 0.7 * s if pose == "glide" else 0.2 * s
    return simple(a, P, [("feathers", body_hex, 0.9), ("wings / tail", wing_hex, 0.9), ("beak / legs", beak_hex, 0.6)], S,
                  "%.2f m bird, %s pose (static, rig pending)%s" % (0.3 * s, pose, ": " + note if note else ""), (w, 0.32 * s, 0.26 * s), (0, -0.02 * s, 0.13 * s))


# ================================================================ fog_channel_pilot (2hot2trot, READY 59012)
@game("fog_channel_pilot")
def fog_channel_pilot():
    G = "Prop_FogChannel_"; out = []; LANE = ["E04040", "F2C740", "40B060", "3A7AE0"]
    horn = [K.cyl("HornBell", "y", 0.12, 0.04, 0.3, (0, -0.05, 2.18), 5, 12, rot=(0, 0, 0)), K.cyl("HornPost", "z", 0.02, 0.02, 0.12, (0, 0.1, 2.12), 5, 6)]
    out.append(cabinet("Prop_Arcade_Cab_FogChannelPilot", "6A7078", "C8CCD4", "FFB03A", horn, [("brass horn", "B08D3C", 0.35, 0.9)], "fog-grey hull, foghorn topper"))
    a = G + "PilotBoat"; P = [K.lathe("Hull", [(0, 0), (0.7, 0.05), (0.85, 0.5), (0, 0.5)], (0, 0, 0), 0, 8, rot=(0, 0, 22.5)), K.box("Deck", (1.4, 3.6, 0.05), (0, 0, 0.52), 1),
                              K.box("Wheelhouse", (1.0, 1.0, 0.9), (0, 0.4, 1.0), 2), K.box("Roof", (1.15, 1.15, 0.06), (0, 0.4, 1.48), 0), K.box("Window", (0.8, 0.02, 0.35), (0, -0.11, 1.15), 3, bevel=False)]
    P[0] = K.box("Hull", (1.6, 4.0, 0.5), (0, 0, 0.25), 0)
    P += [K.box("Bow", (1.6 * 0.7, 0.8, 0.5), (0, -2.2, 0.3), 0, rot=(0, 0, 45))]
    P += [K.box("Rail%d" % k, (0.03, 3.4, 0.03), (k * 0.75, 0, 0.85), 4, bevel=False) for k in (-1, 1)] + [K.box("Stanchion%d_%d" % (k, j), (0.03, 0.03, 0.33), (k * 0.75, -1.5 + 0.75 * j, 0.7), 4, bevel=False) for k in (-1, 1) for j in range(5)]
    out.append(simple(a, P, [("hull", "2A3A4A", 0.6), ("deck", WOOD, 0.8), ("wheelhouse", "E8E4D8", 0.7), ("window", "1A2A3A", 0.1), ("rail", CHROME, 0.3, 0.9)],
                      [K.socket("Floor", (0, 0, 0)), K.socket("Helm", (0, 0.0, 0.55)), K.socket("Bow", (0, -2.3, 0.6)), K.socket("Waterline", (0, 0, 0.2))], "4.6 m wheelhouse launch with deck rail", (1.6, 4.6, 1.5), (0, -0.3, 0.75)))
    for i, hx in enumerate(LANE):
        a = G + "Buoy_Lane%d" % i; P = [K.cyl("Float", "z", 0.35, 0.3, 0.5, (0, 0, 0.25), 0, 10), K.cyl("Mast", "z", 0.08, 0.05, 0.9, (0, 0, 0.95), 0, 8), K.box("Number", (0.22, 0.01, 0.22), (0, -0.31, 0.3), 1, bevel=False), ball("Lamp", (0, 0, 1.45), 0.07, 2, 8)]
        P += [K.box("Num%d" % k, (0.03, 0.012, 0.14), (-0.045 * i / 2 + 0.045 * k, -0.316, 0.3), 3, bevel=False) for k in range(i + 1)]
        out.append(simple(a, P, [("buoy paint", hx, 0.5), ("number plate", "F2F2F2", 0.6), ("lamp (emissive)", hx, 0.2, 0.0, True), ("number marks", BLACK, 0.6)],
                          [K.socket("Pivot", (0, 0, 0.2)), K.socket("Lamp", (0, 0, 1.45)), K.socket("Mooring", (0, 0, 0))], "1.5 m lane %d buoy (bob about Pivot)" % i, (0.7, 0.7, 1.52), (0, 0, 0.76)))
    a = G + "Foghorn"; P = [K.cyl("Post", "z", 0.06, 0.08, 1.4, (0, 0, 0.7), 1, 8), K.cyl("Bell", "y", 0.28, 0.06, 0.7, (0, -0.25, 1.5), 0, 14), K.box("Valve", (0.16, 0.16, 0.16), (0, 0.15, 1.5), 1)]
    out.append(simple(a, P, [("brass horn", "B08D3C", 0.35, 0.9), ("iron post", "3A3A40", 0.6)], [K.socket("Floor", (0, 0, 0)), K.socket("Blast", (0, -0.62, 1.5))], "1.8 m brass foghorn on post (blast anim hook at Blast)", (0.56, 0.95, 1.78), (0, -0.2, 0.89)))
    for nm, hx, n in (("Dull", "8A8A9A", 1), ("Ring", "7AD8FF", 2), ("Clang", "FFB03A", 3), ("Silence", "3A3A48", 0)):
        a = G + "EchoMarker_" + nm; P = [K.cyl("Disc", "y", 0.12, 0.12, 0.02, (0, 0, 0.12), 0, 16)]
        P += [K.cyl("Ring%d" % k, "y", 0.035 + 0.03 * k, 0.035 + 0.03 * k, 0.012, (0, -0.012 - 0.003 * (n - k), 0.12), 1 if (n - 1 - k) % 2 == 0 else 0, 16) for k in range(n)] or [K.box("Bar", (0.16, 0.012, 0.025), (0, -0.012, 0.12), 1, bevel=False)]
        out.append(simple(a, P, [("disc", "1A1E26", 0.6), ("glyph (emissive)", hx, 0.3, 0.0, True)], [K.socket("Centre", (0, 0, 0.12))], "0.24 m echo glyph disc: %s" % nm.lower(), (0.24, 0.04, 0.24), (0, 0, 0.12)))
    a = G + "DriftingShip"; P = [K.box("Hull", (2.4, 9.0, 1.4), (0, 0, 0.7), 0), K.box("Bow", (1.7, 1.7, 1.4), (0, -4.5, 0.7), 0, rot=(0, 0, 45)), K.box("Cabin", (1.8, 3.0, 1.6), (0, 2.0, 2.2), 0), K.cyl("Funnel", "z", 0.4, 0.4, 2.0, (0, 1.0, 3.6), 0, 8), K.cyl("Mast", "z", 0.08, 0.06, 4.5, (0, -2.5, 3.6), 0, 6)]
    out.append(simple(a, P, [("fog silhouette (unlit-friendly, flat)", "4A5058", 1.0)], [K.socket("Floor", (0, 0, 0)), K.socket("Bow", (0, -5.7, 1.0)), K.socket("Light", (0, -2.5, 5.8))], "10 m low-detail ship silhouette for fog", (2.4, 10.2, 5.9), (0, -0.6, 2.95)))
    for nm, op in (("Calm", "C8CCD0"), ("Fog", "A0A8B0"), ("PeaSoup", "8A9078")):
        a = G + "FogBankCard_" + nm; out.append(simple(a, [K.box("Card", (8.0, 0.01, 4.0), (0, 0, 2.0), 0, bevel=False)], [("fog card %s (translucent in UE)" % nm, op, 1.0)], [K.socket("Base", (0, 0, 0))], "8 x 4 m fog volume card, %s density" % nm, (8.0, 0.01, 4.0), (0, 0, 2.0)))
    a = G + "LaneChartBoard"; P = [K.box("Frame", (1.8, 0.06, 0.8), (0, 0, 1.2), 0), K.box("Slate", (1.7, 0.01, 0.7), (0, -0.031, 1.2), 1, bevel=False)] + [K.box("Leg%d" % k, (0.05, 0.05, 0.85), (k * 0.8, 0, 0.425), 0) for k in (-1, 1)]
    P += [K.box("Row%d" % r, (1.6, 0.004, 0.006), (0, -0.037, 1.0 + 0.14 * r), 2, bevel=False) for r in range(4)] + [K.box("Col%d" % c, (0.004, 0.004, 0.56), (-0.8 + 0.1 * c, -0.037, 1.21), 2, bevel=False) for c in range(17)]
    P += [K.box("Swatch%d" % r, (0.05, 0.004, 0.05), (-0.84, -0.038, 1.0 + 0.14 * r), 3 + r, bevel=False) for r in range(4)]
    mats = [("wood frame", WOOD, 0.7), ("chalkboard", "1E2A24", 0.9), ("chalk grid", "D8D8D0", 0.95)] + [("lane %d swatch" % i, hx, 0.6) for i, hx in enumerate(LANE)]
    out.append(simple(a, P, mats, [K.socket("Floor", (0, 0, 0)), K.socket("Grid_TopLeft", (-0.75, -0.04, 1.42))], "1.8 m chalk lane chart, 4 lanes x 16 blasts (cell 0.1 x 0.14 m)", (1.8, 0.06, 1.6), (0, 0, 0.8)))
    a = G + "StarPlaque"; P = [K.box("Plaque", (0.6, 0.04, 0.24), (0, 0, 0.12), 0)]; S = [K.socket("Wall", (0, 0.02, 0.12))]
    for k in range(3):
        x = -0.18 + 0.18 * k; P += [K.lathe("Star%d" % k, [(0, 0), (0.06, 0.0), (0.06, 0.01), (0, 0.012)], (x, -0.02, 0.12), 1, 5, rot=(90, 0, 0))]; S.append(K.socket("Star_%d" % k, (x, -0.035, 0.12)))
    out.append(simple(a, P, [("brass plaque", "B08D3C", 0.35, 0.9), ("star sockets (emissive fill in UE)", "FFE680", 0.3, 0.0, True)], S, "0.6 m 3-star plaque", (0.6, 0.06, 0.24), (0, 0, 0.12)))
    out.append(bird("Mob_FogChannel_HarbourGull_Perch", "F2F2F0", "8A9098", "F2B03A", 1.0, "harbour gull"))
    out.append(bird("Mob_FogChannel_HarbourGull_Glide", "F2F2F0", "8A9098", "F2B03A", 1.0, "harbour gull", "glide"))
    out.append(npc("Mob_FogChannel_HarbourPilot", "C8A830", "2A3A4A", [K.cyl("Spyglass", "y", 0.02, 0.028, 0.3, (-0.37, -0.1, 0.88), 4, 8), K.cyl("SouWester", "z", 0.2, 0.13, 0.08, (0, 0.02, 1.76), 0, 10)], [("brass spyglass", "B08D3C", 0.35, 0.9)], "oilskin coat, spyglass"))
    out.append(npc("Mob_FogChannel_Dockhand", "5A6A4A", "3A3A48", [K.cyl("RopeCoil", "y", 0.14, 0.14, 0.06, (0.4, -0.02, 0.9), 4, 12)], [("rope", ROPE, 0.95)], "rival, rope coil"))
    return out



def strip(a, ground_hex, parts, mats_extra, note, h=0.3):
    """10 m tileable habitat module (X = along the crossing, 10 m; Y = 4 m wide). Ends at x = +-5 for snapping."""
    P = [K.box("Ground", (10.0, 4.0, 0.2), (0, 0, -0.1), 0, bevel=False)] + list(parts)
    return simple(a, P, [("ground", ground_hex, 0.95)] + list(mats_extra), [K.socket("Start", (-5, 0, 0)), K.socket("End", (5, 0, 0)), K.socket("Centre", (0, 0, 0))],
                  "10 x 4 m tileable habitat strip: " + note, (10.0, 4.0, h + 0.2), (0, 0, (h - 0.2) / 2))


def scatter(name, n, seed, fn, xr=4.6, yr=1.7):
    R = K.rng(SEED + seed, name); return [fn("%s%d" % (name, i), R.uniform(-xr, xr), R.uniform(-yr, yr), R) for i in range(n)]


# ================================================================ shardsong_crossing (prometheus, READY 59004)
@game("shardsong_crossing")
def shardsong_crossing():
    G = "Prop_Shardsong_"; out = []
    birds = [ball("MarqBirdL", (-0.28, -0.18, 2.1), 0.035, 5, 8), ball("MarqBirdR", (0.28, -0.18, 2.1), 0.035, 5, 8),
             crystal("MarqShardL", (-0.3, -0.12, 1.98), 0.1, 6, rot=(180, 0, 0)), crystal("MarqShardR", (0.3, -0.12, 1.98), 0.1, 6, rot=(180, 0, 0))]
    out.append(cabinet("Prop_Arcade_Cab_ShardsongCrossing", "4A3A5A", "D89A7A", "FFC89A", birds, [("songbirds", "F2D04A", 0.6), ("shard rock", "6A5A7A", 0.8)], "dusk palette, two birds calling across a shard gap"))
    for i, (b, w) in enumerate((("E8B040", "8A5A2A"), ("6AB0E0", "2A4A7A"), ("E07070", "6A2A3A"))):
        out.append(bird("Mob_Shardsong_Songbird_Caller_%d" % (i + 1), b, w, "F2A030", 0.5, "caller, open-beak call pose, colour variant %d" % (i + 1)))
    m = bird("Mob_Shardsong_Songbird_Mate", "D8C8A0", "7A6A4A", "F2A030", 0.5, "mate, listen pose (head tilt in rig)")
    out.append(m)
    for v in (1, 2):
        a = G + "IslandShard_%d" % v; R = K.rng(SEED + v, a)
        P = [K.lathe("Rock", [(0, -2.2 + 0.3 * v), (0.4, -1.6), (1.0, -0.9), (1.4, -0.3), (1.5, 0.0), (0, 0.0)], (0, 0, 0), 0, 7 + v), K.cyl("Top", "z", 1.5, 1.5, 0.12, (0, 0, 0.06), 1, 7 + v)]
        P += [rock("Boulder%d" % k, (R.uniform(-0.9, 0.9), R.uniform(-0.9, 0.9), 0.17), 0.12, 0, k) for k in range(3)] + [K.cyl("Perch", "z", 0.03, 0.03, 0.6, (0.6, 0, 0.42), 2, 6)]
        out.append(simple(a, P, [("shard rock", "5A4A6A", 0.9), ("moss top", "5A8A4A", 0.95), ("perch branch", WOOD, 0.8)], [K.socket("Perch", (0.6, 0, 0.72)), K.socket("Top", (0, 0, 0.12))],
                          "3 m floating island shard v%d, flat top, perch branch" % v, (3.0, 3.0, 2.3), (0, 0, -0.9)))
    tree = lambda n, x, y, R: [K.cyl(n + "Trunk", "z", 0.12, 0.09, 1.8, (x, y, 0.9), 1, 6), K.lathe(n + "Crown", [(0, 0), (0.9, 0.2), (0.6, 1.2), (0, 1.8)], (x, y, 1.4), 2, 7)]
    P = sum(scatter("Tree", 7, 1, tree, 4.0, 1.0), []) + sum(scatter("Bush", 6, 2, lambda n, x, y, R: [ball(n, (x, y, 0.2), 0.3, 2, 6)]), [])
    out.append(strip(G + "Habitat_Forest", "4A3A22", P, [("trunk", "5A3A22", 0.9), ("foliage", "2E6A34", 0.95)], "forest", 3.2))
    P = sum(scatter("Tuft", 18, 3, lambda n, x, y, R: [K.lathe(n, [(0, 0), (0.12, 0.0), (0, 0.25)], (x, y, 0), 1, 4)]), [])
    out.append(strip(G + "Habitat_Grass", "6A9A4A", P, [("tufts", "8AB85A", 0.95)], "open grass", 0.25))
    P = [K.box("Water", (10.0, 3.2, 0.02), (0, 0, 0.01), 1, bevel=False)] + [K.box("Surf%d" % k, (10.0, 0.25, 0.04), (0, k * 1.65, 0.02), 2, bevel=False) for k in (-1, 1)]
    out.append(strip(G + "Habitat_Water", "8A7A5A", P, [("water (animated shader in UE)", "2A6A9A", 0.05), ("surf foam", "E8F0F2", 0.6)], "calm open water, low surf at edges", 0.04))
    P = sum(scatter("Scrub", 12, 4, lambda n, x, y, R: [ball(n, (x, y, 0.15), 0.22 + 0.1 * R.random(), 1, 6)]), [])
    out.append(strip(G + "Habitat_Scrub", "A89060", P, [("dry bush", "7A7A40", 0.95)], "scrub, low bushes on dry ground", 0.4))
    P = [K.box("Pool%d" % k, (1.6, 1.0, 0.02), (-3 + 3 * k, (-1) ** k * 0.6, 0.01), 2, bevel=False) for k in range(3)]
    P += sum(scatter("Reed", 16, 5, lambda n, x, y, R: [K.cyl(n, "z", 0.04, 0.01, 1.2, (x, y, 0.6), 1, 4)]), [])
    out.append(strip(G + "Habitat_Marsh", "4A5A3A", P, [("reeds", "8A9A4A", 0.95), ("shallow pool", "3A5A6A", 0.1)], "marsh, reed beds and shallow pools (V2)", 1.2))
    P = sum(scatter("Slab", 8, 6, lambda n, x, y, R: [rock(n, (x, y, 0.15), 0.4 + 0.3 * R.random(), 1, int(R.random() * 9))]), [])
    out.append(strip(G + "Habitat_Rock", "6A6A6A", P, [("rock", "8A8A88", 0.9)], "bare rock faces and slabs (V2)", 0.6))
    a = G + "FlockSilhouette"; P = []
    for k, (x, z) in enumerate(((0, 0.4), (-0.5, 0.3), (0.5, 0.32), (-1.0, 0.15), (1.0, 0.2), (-0.2, 0.0), (0.3, 0.05))):
        P += [K.box("Bird%dL" % k, (0.22, 0.01, 0.03), (x - 0.09, 0, z + 0.03), 0, bevel=False, rot=(0, -20, 0)), K.box("Bird%dR" % k, (0.22, 0.01, 0.03), (x + 0.09, 0, z + 0.03), 0, bevel=False, rot=(0, 20, 0))]
    out.append(simple(a, P, [("silhouette (flat dark)", "2A2A34", 1.0)], [K.socket("Centre", (0, 0, 0.2))], "2.4 m distant flock silhouette (flock-masking indicator, V2)", (2.4, 0.02, 0.55), (0, 0, 0.25)))
    out.append(npc("Mob_Shardsong_WarblerKeeper", "5A6A3A", "4A3A2A", [ball("PerchBird", (-0.37, -0.02, 0.95), 0.04, 4, 8)], [("perched bird", "E8B040", 0.6)], "Shard Warbler keeper"))
    return out



# ================================================================ translocation_plan (pythagoras, READY 59018)
@game("translocation_plan")
def translocation_plan():
    G = "Prop_Translocation_"; out = []
    reeds = [K.cyl("MarqReed%d" % k, "z", 0.012, 0.004, 0.25, (-0.3 + 0.12 * k, 0.05, 2.18), 5, 4) for k in range(6)]
    out.append(cabinet("Prop_Arcade_Cab_TranslocationPlan", "3A5A4A", "C8B48A", "9AE0A0", reeds, [("reeds", "8A9A4A", 0.95)], "TRANS01, marsh reed topper"))
    a = G + "Crate"; P = [K.box("Box", (0.7, 0.5, 0.45), (0, 0, 0.225), 0), K.box("Lid", (0.74, 0.54, 0.05), (0, 0, 0.475), 0), K.box("Handle", (0.3, 0.04, 0.06), (0, 0, 0.53), 1)]
    P += [K.box("Vent%d" % k, (0.5, 0.01, 0.025), (0, -0.252, 0.12 + 0.07 * k), 1, bevel=False) for k in range(4)]
    out.append(simple(a, P, [("crate wood", "A07A4A", 0.8), ("vents / handle", "3A2A1A", 0.8)], [K.socket("Floor", (0, 0, 0)), K.socket("Lid", (0, 0, 0.5)), K.socket("Grab", (0, 0, 0.56))], "0.7 m ventilated bird crate", (0.74, 0.54, 0.56), (0, 0, 0.28)))
    a = G + "ReleasePen"; P = []
    for k in range(4):
        an = k * math.pi / 2; x, y = 1.5 * math.cos(an), 1.5 * math.sin(an)
        P += [K.box("Mesh%d" % k, (3.0 if k % 2 else 0.03, 0.03 if k % 2 else 3.0, 1.2), (x, y, 0.6), 1, bevel=False)]
    P += [K.cyl("Post%d" % k, "z", 0.05, 0.05, 1.3, (sx * 1.5, sy * 1.5, 0.65), 0, 6) for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1)))]
    P += [K.box("Gate", (0.9, 0.04, 1.0), (0, -1.53, 0.5), 2)]
    out.append(simple(a, P, [("posts", WOOD, 0.8), ("netting (masked in UE)", "8A8A80", 0.9), ("gate", "A07A4A", 0.8)], [K.socket("Floor", (0, 0, 0)), K.socket("Gate", (0, -1.55, 0)), K.socket("Inside", (0, 0, 0))], "3 m soft-release pen with gate (-Y)", (3.1, 3.1, 1.3), (0, 0, 0.65)))
    a = G + "PlanningBoard"; P = [K.box("Frame", (1.6, 0.06, 1.0), (0, 0, 1.3), 0), K.box("Face", (1.5, 0.01, 0.9), (0, -0.031, 1.3), 1, bevel=False)] + [K.box("Leg%d" % k, (0.05, 0.05, 0.85), (k * 0.7, 0, 0.425), 0) for k in (-1, 1)]
    P += [K.box("Cell%d_%d" % (r, c), (0.2, 0.004, 0.16), (-0.6 + 0.24 * c, -0.037, 1.6 - 0.2 * r), 2 + (r + c) % 2, bevel=False) for r in range(4) for c in range(6)]
    out.append(simple(a, P, [("frame", WOOD, 0.7), ("board", "E8E4D8", 0.8), ("cell A", "C8DCC0", 0.8), ("cell B", "B0C8B8", 0.8)], [K.socket("Floor", (0, 0, 0)), K.socket("Grid_TopLeft", (-0.7, -0.04, 1.68))], "1.6 m planning board, 6 years x 4 cohorts", (1.6, 0.06, 1.8), (0, 0, 0.9)))
    a = G + "RiskGauge"; P = [K.cyl("Dial", "y", 0.3, 0.3, 0.06, (0, 0, 1.3), 0, 20), K.cyl("Face", "y", 0.27, 0.27, 0.01, (0, -0.035, 1.3), 1, 20), K.cyl("Post", "z", 0.04, 0.05, 1.0, (0, 0.02, 0.5), 0, 6),
                             K.box("Band", (0.24, 0.006, 0.05), (0, -0.042, 1.45), 2, bevel=False), K.box("Needle", (0.015, 0.008, 0.22), (0, -0.048, 1.38), 3, bevel=False, rot=(0, 30, 0))]
    out.append(simple(a, P, [("brass case", "B08D3C", 0.35, 0.9), ("dial face", "F2EEE0", 0.6), ("95% interval band (emissive)", "E0A040", 0.4, 0.0, True), ("needle", "C03030", 0.5)],
                      [K.socket("Floor", (0, 0, 0)), K.socket("NeedlePivot", (0, -0.05, 1.3))], "1.6 m risk gauge with needle + 95% band (rotate in UE)", (0.6, 0.1, 1.6), (0, 0, 0.8)))
    P = [K.box("Pool%d" % k, (1.6, 1.0, 0.02), (-3 + 3 * k, (-1) ** k * 0.6, 0.01), 2, bevel=False) for k in range(3)]
    P += sum(scatter("Reed", 22, 7, lambda n, x, y, R: [K.cyl(n, "z", 0.04, 0.01, 1.3, (x, y, 0.65), 1, 4)]), [])
    out.append(strip(G + "ReedMarsh", "4A5A3A", P, [("reeds", "8A9A4A", 0.95), ("shallow pool", "3A5A6A", 0.1)], "reed marsh destination", 1.3))
    for st, s in (("Chick", 0.35), ("Juvenile", 0.6), ("Subadult", 0.8), ("Adult", 1.0)):
        out.append(bird("Mob_Translocation_MarshBird_" + st, "8A6A4A" if st != "Chick" else "C8B08A", "4A3A2A", "D8A040", s * 1.2, "marsh bird " + st.lower()))
    out.append(npc("Mob_Translocation_Warden", "4A5A3A", "3A3A2A", [K.box("Clipboard", (0.2, 0.02, 0.28), (-0.37, -0.06, 0.95), 4)], [("clipboard", "C8B48A", 0.8)], "wildlife warden"))
    return out



# ================================================================ prismchime (unreal-team, READY 59142/59143)
@game("prismchime")
def prismchime():
    G = "Prop_Prismchime_"; out = []
    hoop = [K.cyl("TopHoop%d" % k, "y", 0.16 - 0.005 * k, 0.16 - 0.005 * k, 0.02, (0, -0.02 - 0.005 * k, 2.25), 5 + k % 2, 16) for k in range(2)] + [K.cyl("TopBell", "z", 0.05, 0.03, 0.08, (0, -0.02, 2.2), 5, 8)]
    out.append(cabinet("Prop_Arcade_Cab_Prismchime", "2A3A5A", "A6C8E6", "C8A6FF", hoop, [("chime brass", "B08D3C", 0.35, 0.9), ("hoop inner", "2A3A5A", 0.5)], "chime-hoop topper"))
    a = G + "Hoop"; R0, Z0 = 0.8, 0.85; P = []; SILVER = "D0D4DC"
    for ring, r in enumerate((R0, R0 - 0.08)):
        for k in range(24):
            an = 2 * math.pi * k / 24; P.append(K.box("Ring%d_%d" % (ring, k), (2 * math.pi * r / 24 + 0.01, 0.035, 0.035), (r * math.cos(an), 0, Z0 + r * math.sin(an)), 0, bevel=False, rot=(0, -math.degrees(an) - 90, 0)))
    P += [K.box("Tie%d" % k, (0.1, 0.03, 0.03), (0.76 * math.cos(k * math.pi / 4), 0, Z0 + 0.76 * math.sin(k * math.pi / 4)), 0, bevel=False, rot=(0, -math.degrees(k * math.pi / 4), 0)) for k in range(8)]
    P += [K.cyl("Link%d" % k, "x" if k % 2 else "y", 0.03, 0.03, 0.012, (0, 0, Z0 + R0 + 0.05 + 0.05 * k), 1, 8) for k in range(5)]
    S = [K.socket("Hang", (0, 0, Z0 + R0 + 0.28)), K.socket("Centre", (0, 0, Z0))] + [K.socket("Bell_%d" % k, (0.76 * math.cos(math.pi / 2 + k * math.pi / 4), -0.03, Z0 + 0.76 * math.sin(math.pi / 2 + k * math.pi / 4))) for k in range(8)]
    out.append(simple(a, P, [("silver hoop", SILVER, 0.25, 1.0), ("chain", "8A8A90", 0.4, 1.0)], S, "1.6 m silver double hoop on short chain, 8 bell sockets (scale for 6/10 variants); hang from Hang", (1.64, 0.04, 1.93), (0, 0, 0.965)))
    for st, hx, glow in (("Dark", "8AA8C8", False), ("Lit", "FFB84A", True)):
        a = G + "Bell_" + st; P = [K.cyl("Rod", "z", 0.006, 0.006, 0.12, (0, 0, 0.2), 1, 6), K.lathe("Bell", [(0, 0.15), (0.03, 0.145), (0.05, 0.1), (0.07, 0.02), (0.08, 0.0), (0, 0.0)], (0, 0, 0), 0, 6), ball("Clapper", (0, 0, 0.02), 0.012, 1, 6)]
        S = [K.socket("Hang", (0, 0, 0.26)), K.socket("Strike", (0, -0.075, 0.05))]
        for k in range(3):
            z = 0.06 + 0.03 * k; P.append(ball("Pip%d" % k, (0, -0.07 + 0.012 * k, z), 0.008, 2, 6)); S.append(K.socket("Pip_%d" % k, (0, -0.075 + 0.012 * k, z)))
        out.append(simple(a, P, [("crystal bell" + (" (emissive amber)" if glow else ""), hx, 0.1, 0.0, glow), ("rod / clapper", SILVER, 0.25, 1.0), ("pip slot", "2A2A34", 0.5)], S,
                          "0.26 m crystal bell on rod, 3 pip slots, %s" % st.lower(), (0.16, 0.16, 0.26), (0, 0, 0.13)))
    a = G + "Mallet"; P = [K.cyl("Handle", "z", 0.012, 0.014, 0.26, (0, 0, 0.13), 0, 8), crystal("Head", (-0.07, 0, 0.27), 0.14, 1, rot=(0, 90, 0))]
    out.append(simple(a, P, [("silver handle", SILVER, 0.25, 1.0), ("prism head (emissive)", "C8A6FF", 0.15, 0.0, True)], [K.socket("Grip", (0, 0, 0.06)), K.socket("Tip", (0.07, 0, 0.27))], "0.3 m prism-headed tap mallet (head along X)", (0.14, 0.06, 0.3), (0, 0, 0.15)))
    out.append(npc("Mob_Prismchime_Warden", "4A3A6A", "2A2A3A", [K.cyl("WMallet", "z", 0.012, 0.012, 0.26, (-0.37, -0.03, 0.95), 4, 6), crystal("WMalletHead", (-0.37, -0.03, 1.08), 0.1, 5)], [("silver", "D0D4DC", 0.25, 1.0), ("prism (emissive)", "C8A6FF", 0.15, 0.0, True)], "Prismchime Warden (static; shared 8-bone rig pending)"))
    return out



# ---------------------------------------------------------------- Disk Saver shared kit
def slate(a, note):
    P = [K.box("Frame", (1.0, 0.06, 1.5), (0, 0, 1.25), 0), K.box("Slate", (0.9, 0.01, 1.4), (0, -0.031, 1.25), 1, bevel=False)] + [K.box("Leg%d" % k, (0.06, 0.06, 0.5), (k * 0.42, 0, 0.25), 0) for k in (-1, 1)]
    P += [K.box("ChalkTray", (0.9, 0.08, 0.03), (0, -0.05, 0.53), 0)]
    return simple(a, P, [("wood frame", WOOD, 0.7), ("slate (runtime chalk UI over this face)", "2A2E30", 0.9)], [K.socket("Floor", (0, 0, 0)), K.socket("UI_Face", (0, -0.037, 1.25)), K.socket("ChalkTray", (0, -0.05, 0.56))],
                  "1 x 1.5 m slate on legs: " + note, (1.0, 0.1, 2.0), (0, 0, 1.0))


def flag(a, cloth_hex, note, pole=4.0, w=1.0, h=0.6, ragged=False):
    P = [K.cyl("Pole", "z", 0.035, 0.03, pole, (0, 0, pole / 2), 0, 8), ball("Finial", (0, 0, pole + 0.04), 0.05, 0, 6)]
    if ragged:
        P += [K.box("Cloth%d" % k, (w / 4, 0.01, h * (1 - 0.15 * (k % 2))), (0.04 + w / 8 + k * w / 4, 0, pole - 0.05 - h / 2 + 0.03 * (k % 2)), 1, bevel=False) for k in range(4)]
    else:
        P += [K.box("Cloth", (w, 0.01, h), (0.04 + w / 2, 0, pole - 0.05 - h / 2), 1, bevel=False)]
    return simple(a, P, [("pole", "E8E4D8", 0.6), ("cloth", cloth_hex, 0.95)], [K.socket("Floor", (0, 0, 0)), K.socket("Cloth", (0.04, 0, pole - 0.05))],
                  "%.1f x %.1f m flag on %.0f m pole: %s" % (w, h, pole, note), (w + 0.1, 0.07, pole + 0.1), (w / 2, 0, (pole + 0.1) / 2))


def pennant(a, cloth_hex, note, w=1.0, h=0.5):
    P = [K.cyl("Batten", "x", 0.015, 0.015, w + 0.1, (0, 0, h), 0, 6), K.box("Cloth", (w, 0.01, h * 0.6), (0, 0, h * 0.68), 1, bevel=False)]
    P += [K.box("Tail%d" % s, (w / 2, 0.01, h * 0.35), (s * w / 4, 0, h * 0.22), 1, bevel=False, rot=(0, s * 25, 0)) for s in (-1, 1)]
    return simple(a, P, [("batten", WOOD, 0.7), ("cloth", cloth_hex, 0.95)], [K.socket("Hang", (0, 0, h)), K.socket("Name", (0, -0.01, h * 0.68))], "%.1f x %.1f m pennant: %s" % (w, h, note), (w + 0.1, 0.03, h), (0, 0, h / 2))


def signal_lamp(a, hx, note, h=0.3):
    P = [K.box("Base", (0.14, 0.14, 0.04), (0, 0, 0.02), 1), K.cyl("Glass", "z", 0.07, 0.07, h * 0.55, (0, 0, 0.04 + h * 0.275), 0, 10), K.cyl("Cap", "z", 0.03, 0.09, 0.05, (0, 0, 0.065 + h * 0.55), 1, 10),
         K.box("Hood", (0.16, 0.06, 0.02), (0, -0.05, 0.05 + h * 0.55), 1, bevel=False)]
    return simple(a, P, [("lamp glass (emissive)", hx, 0.15, 0.0, True), ("iron", "2A2A30", 0.5, 0.8)], [K.socket("Base", (0, 0, 0)), K.socket("Light", (0, 0, 0.04 + h * 0.275))], "%.2f m signal lamp: %s" % (h, note), (0.18, 0.18, h), (0, 0, h / 2))


def hull(a, L, hull_hex, masts=1, cabin=False, hatch=None, note="", sail_hex="E8DCC0"):
    W = max(1.4, L * 0.26); H = max(0.8, L * 0.1)
    P = [K.box("Hull", (W, L * 0.8, H), (0, L * 0.1, H / 2), 0), K.box("Bow", (W * 0.71, W * 0.71, H), (0, -L * 0.3, H / 2), 0, rot=(0, 0, 45)), K.box("Deck", (W - 0.1, L * 0.8 - 0.1, 0.05), (0, L * 0.1, H + 0.02), 1),
         K.box("Rail", (W, 0.05, 0.25), (0, L * 0.5 - 0.03, H + 0.15), 0)]
    S = [K.socket("Floor", (0, 0, 0)), K.socket("Bow", (0, -L * 0.3 - W * 0.5, H)), K.socket("Stern", (0, L * 0.5, H)), K.socket("Deck", (0, L * 0.1, H + 0.05)), K.socket("Pennant", (0, 0, H + L * 0.45))]
    for m in range(masts):
        y = L * (0.1 - 0.25 * (m - (masts - 1) / 2)); mh = L * 0.45
        P += [K.cyl("Mast%d" % m, "z", 0.06 + L * 0.003, 0.04, mh, (0, y, H + mh / 2), 2, 6), K.box("Sail%d" % m, (W * 1.1, 0.02, mh * 0.55), (0, y + 0.05, H + mh * 0.5), 3, bevel=False)]
    if cabin:
        P += [K.box("Cabin", (W * 0.7, L * 0.18, H * 0.9), (0, L * 0.38, H * 1.45), 1)]
    if hatch:
        open_ = hatch == "Open"; P += [K.box("HatchCoaming", (W * 0.5, L * 0.15, 0.15), (0, L * 0.05, H + 0.1), 2)]
        P += [K.box("HatchLid", (W * 0.5, L * 0.15, 0.05), (W * 0.27 + 0.02, L * 0.05, H + 0.3), 2, rot=(0, 75, 0))] if open_ else [K.box("HatchLid", (W * 0.52, L * 0.16, 0.05), (0, L * 0.05, H + 0.2), 2)]
        S.append(K.socket("Hatch", (0, L * 0.05, H + 0.2)))
    mats = [("hull", hull_hex, 0.7), ("deck", WOOD, 0.8), ("spars / hatch", "5A3A22", 0.8), ("sail", sail_hex, 0.95)]
    return simple(a, P, mats, S, "%.0f m moored hull: %s" % (L, note), (W, L, H + L * 0.45), (0, 0, (H + L * 0.45) / 2))


def crate(a, s):
    P = [K.box("Box", (s, s, s), (0, 0, s / 2), 0)] + [K.box("Band%d" % k, (s + 0.02, s + 0.02, s * 0.06), (0, 0, s * (0.2 + 0.6 * k)), 1, bevel=False) for k in range(2)] + [K.cyl("Eye", "y", s * 0.06, s * 0.06, s * 0.03, (0, 0, s + s * 0.05), 1, 8)]
    return simple(a, P, [("crate wood", "A07A4A", 0.8), ("iron bands", "3A3A40", 0.6, 0.8)], [K.socket("Floor", (0, 0, 0)), K.socket("HookAttach", (0, 0, s + s * 0.1))], "%.1f m cargo crate (hook on top)" % s, (s + 0.02, s + 0.02, s * 1.1), (0, 0, s * 0.55))


def tick_board(a, cols, rows, note, w=2.0, h=1.2):
    P = [K.box("Frame", (w, 0.06, h), (0, 0, 1.0 + h / 2), 0), K.box("Face", (w - 0.1, 0.01, h - 0.1), (0, -0.031, 1.0 + h / 2), 1, bevel=False)] + [K.box("Leg%d" % k, (0.07, 0.07, 1.0), (k * (w / 2 - 0.1), 0, 0.5), 0) for k in (-1, 1)]
    cw = (w - 0.2) / cols
    P += [K.box("Tick%d" % c, (0.006, 0.004, 0.06 if c % 10 else 0.12), (-(w - 0.2) / 2 + c * cw, -0.037, 1.0 + h - 0.15), 2, bevel=False) for c in range(cols + 1)]
    P += [K.box("Row%d" % r, (w - 0.2, 0.004, 0.006), (0, -0.037, 1.0 + h - 0.25 - r * (h - 0.35) / rows), 2, bevel=False) for r in range(rows)]
    return simple(a, P, [("wood frame", WOOD, 0.7), ("board", "1E2A24", 0.9), ("chalk ticks", "E8E8E0", 0.95)], [K.socket("Floor", (0, 0, 0)), K.socket("Tick0", (-(w - 0.2) / 2, -0.04, 1.0 + h - 0.15)), K.socket("UI_Face", (0, -0.04, 1.0 + h / 2))],
                  "%.1f x %.1f m board: %s" % (w, h, note), (w, 0.08, 1.0 + h), (0, 0, (1.0 + h) / 2))


# ================================================================ gantry_sweep (disk-saver, READY 59154)
@game("gantry_sweep")
def gantry_sweep():
    G = "Prop_GantrySweep_"; out = []
    top = [K.box("MarqRail", (0.84, 0.04, 0.03), (0, -0.05, 2.1), 5, bevel=False), K.box("MarqGantry", (0.06, 0.06, 0.18), (-0.1, -0.05, 2.2), 6), K.box("MarqBeam", (0.3, 0.05, 0.04), (0, -0.05, 2.3), 6, bevel=False)]
    out.append(cabinet("Prop_Arcade_Cab_GantrySweep", "3A4A5A", "D8C8A0", "FFB03A", top, [("rail steel", "6A6A70", 0.4, 0.9), ("crane yellow", "E0B030", 0.5)], "rail-and-crane marquee, tick-board side art"))
    a = G + "GantryCrane"; Y = "E0B030"
    P = [K.box("Leg%d%d" % (sx, sy), (0.35, 0.35, 7.4), (sx * 2.8, sy * 1.0, 3.7), 0) for sx in (-1, 1) for sy in (-1, 1)]
    P += [K.box("Bogie%d" % sx, (0.6, 2.8, 0.5), (sx * 2.8, 0, 0.25), 1) for sx in (-1, 1)] + [K.box("Girder%d" % sy, (6.2, 0.4, 0.6), (0, sy * 1.0, 7.6), 0) for sy in (-1, 1)]
    P += [K.box("Brace%d" % sx, (0.15, 2.0, 0.15), (sx * 2.8, 0, 5.0), 0, bevel=False) for sx in (-1, 1)]
    P += [K.box("Trolley", (0.9, 2.4, 0.5), (0.8, 0, 8.15), 1), K.box("CraneCab", (1.0, 1.0, 1.0), (-2.2, -1.5, 6.7), 2), K.box("CabWindow", (0.8, 0.02, 0.5), (-2.2, -2.01, 6.8), 3, bevel=False),
          K.cyl("Cable", "z", 0.02, 0.02, 3.0, (0.8, 0, 6.4), 1, 4), K.box("HookBlock", (0.3, 0.2, 0.35), (0.8, 0, 4.75), 1), K.lathe("Hook", [(0.0, 0.0), (0.05, 0.02), (0.04, 0.25), (0, 0.27)], (0.8, 0, 4.3), 1, 6)]
    S = [K.socket("RailCentre", (0, 0, 0)), K.socket("Trolley", (0.8, 0, 7.9)), K.socket("Hook", (0.8, 0, 4.3)), K.socket("CabLamp", (-2.2, -2.05, 7.3))]
    out.append(simple(a, P, [("crane yellow", Y, 0.5), ("steel", "4A4A50", 0.5, 0.8), ("cab", "E8E4D8", 0.7), ("glass", "1A2A3A", 0.1)], S,
                      "8.4 m gantry crane spanning the rail (travel along Y, hoist the Hook socket; rig pending)", (6.2, 3.2, 8.4), (0, -0.3, 4.2)))
    a = G + "QuayRail"; P = [K.box("Quay", (8.0, 4.0, 0.3), (0, 0, -0.15), 0, bevel=False)] + [K.box("Rail%d" % sx, (0.15, 4.0, 0.15), (sx * 2.8, 0, 0.075), 1, bevel=False) for sx in (-1, 1)]
    P += [K.box("Sleeper%d" % k, (6.2, 0.25, 0.05), (0, -1.5 + 1.0 * k, 0.02), 2, bevel=False) for k in range(4)] + [K.box("Stencil", (0.8, 0.5, 0.01), (-3.5, 0, 0.005), 3, bevel=False)]
    out.append(simple(a, P, [("quay stone", STONE, 0.9), ("rail steel", "6A6A70", 0.4, 0.9), ("sleepers", "4A3A2A", 0.9), ("berth number stencil (decal)", "F2F2E8", 0.8)],
                      [K.socket("Start", (0, -2, 0)), K.socket("End", (0, 2, 0)), K.socket("BerthStencil", (-3.5, 0, 0.01)), K.socket("Bollard", (3.6, 0, 0))], "4 m quay rail segment (one berth, tile along Y)", (8.0, 4.0, 0.45), (0, 0, 0.0)))
    a = G + "BerthBollard"; P = [K.cyl("Body", "z", 0.18, 0.2, 0.45, (0, 0, 0.225), 0, 10), K.cyl("Cap", "z", 0.26, 0.22, 0.1, (0, 0, 0.5), 0, 10), K.box("PlatePost", (0.06, 0.06, 0.5), (0.35, 0, 0.25), 0), K.box("Plate", (0.4, 0.02, 0.16), (0.35, -0.04, 0.55), 1, bevel=False)]
    out.append(simple(a, P, [("cast iron", "2A2A30", 0.5, 0.8), ("name plate (12 decal variants)", "C8B48A", 0.5, 0.6)], [K.socket("Floor", (0, 0, 0)), K.socket("Rope", (0, 0, 0.35)), K.socket("Plate", (0.35, -0.05, 0.55))],
                      "0.6 m mooring bollard with swappable name plate", (0.75, 0.52, 0.63), (0.12, 0, 0.315)))
    for nm, L, hx, m, cab in (("TraderCog", 16, "6A4A2A", 1, True), ("FishingSmack", 12, "3A5A6A", 1, False), ("RiverBarge", 20, "4A4A3A", 0, True)):
        for st in ("Closed", "Open"):
            out.append(hull(G + "Ship_%s_Hatch%s" % (nm, st), L, hx, m, cab, st, "%s, hatch %s" % (nm, st.lower())))
    out.append(tick_board(G + "ArrivalTickBoard", 60, 5, "arrival ticks 0-60"))
    out.append(slate(G + "RailPostSlate", "Ossian's order slate"))
    for nm, hx in (("Calm", "6AB0E0"), ("Rush", "E0B030"), ("Spread", "6AC07A")):
        out.append(flag(G + "TideFlag_" + nm, hx, "tide profile " + nm.lower()))
    out.append(flag(G + "TideFlag_Storm", "C03030", "tide profile storm (ragged)", ragged=True))
    for nm, hx in (("Sweet", "40E070"), ("Fair", "FFB03A"), ("Jammed", "FF3A3A")):
        out.append(signal_lamp(G + "VerdictLamp_" + nm, hx, nm.lower()))
    for s in (0.5, 1.0, 2.0):
        out.append(crate(G + "Crate_%02dm" % int(s * 10), s))
    a = G + "GreaseTin"; P = [K.cyl("Tin", "z", 0.05, 0.05, 0.08, (0, 0, 0.04), 0, 12), K.cyl("Lid", "z", 0.052, 0.052, 0.012, (0, 0, 0.086), 1, 12), K.box("Bail", (0.1, 0.006, 0.006), (0, 0, 0.13), 1, bevel=False)]
    P += [K.box("BailSide%d" % s, (0.006, 0.006, 0.05), (s * 0.05, 0, 0.11), 1, bevel=False) for s in (-1, 1)]
    out.append(simple(a, P, [("tin", "6A6A60", 0.5, 0.8), ("lid / bail", "3A3A30", 0.6, 0.8)], [K.socket("Grip", (0, 0, 0.13)), K.socket("Base", (0, 0, 0))], "0.14 m grease tin (attach Grip to Ossian HandR)", (0.11, 0.11, 0.14), (0, 0, 0.07)))
    out.append(npc("Mob_GantrySweep_RailwrightOssian", "3A4A5A", "4A3A2A", [K.cyl("OTin", "z", 0.05, 0.05, 0.08, (-0.37, 0, 0.82), 4, 10)], [("grease tin", "6A6A60", 0.5, 0.8)], "Railwright Ossian (rig pending: idle, chalk, grumble)"))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--game", required=True); ap.add_argument("--kit", required=True); o = ap.parse_args()
    M_ = GAMES[o.game](); os.makedirs(os.path.dirname(os.path.abspath(o.kit)), exist_ok=True); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
