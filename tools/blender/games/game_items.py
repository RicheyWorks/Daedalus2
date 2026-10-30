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

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--game", required=True); ap.add_argument("--kit", required=True); o = ap.parse_args()
    M_ = GAMES[o.game](); os.makedirs(os.path.dirname(os.path.abspath(o.kit)), exist_ok=True); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
