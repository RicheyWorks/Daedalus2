# SPDX-License-Identifier: MIT
"""Prismheart arcade batch d (blender-team, 2026-10-29, Richey "great lets keep it moving" via buffffff). Same conventions as batch b/c:
blender-kit/v1, origin bottom-centre (ceiling rigs: origin = ceiling hang plane, geometry hangs down -Z), front -Y, sockets as the Daedalus hook.
  Prop_Arcade_CeilingLightRig_A / _B / _C  truss light rigs (A straight 3 m, 4 cans; B cross 2.4 m, 4 cans; C ring 2.4 m, 6 cans):
                                            SOCKET_Hang_k (ceiling), SOCKET_Light_k (spot origin, aims -Z; tint/GlowPower via MI)
  Prop_Arcade_TicketCounter     redemption ticket counter: SOCKET_TicketIn, SOCKET_Display, SOCKET_ReceiptOut, SOCKET_Player1, SOCKET_Floor
  Prop_Arcade_PhotoBooth        booth: SOCKET_Seat, SOCKET_Camera, SOCKET_Screen, SOCKET_PhotoSlot, SOCKET_CurtainRail, SOCKET_Entry
  Prop_Arcade_HighScoreBoard    wall board with 10 entry rows: SOCKET_Entry_0..9 (text/widget anchor), SOCKET_Title, SOCKET_Wall
  Prop_Arcade_Cab_DancePad      dance cab: screen + speaker tower + 2-player stage, SOCKET_Pad_P1/P2_<Up|Down|Left|Right>, SOCKET_Player1/2, SOCKET_Screen
  Prop_Arcade_Cab_Pinball       pinball table: SOCKET_FlipperL/R, SOCKET_Plunger, SOCKET_Backglass, SOCKET_Ball, SOCKET_Player1, SOCKET_Floor
  Prop_Arcade_Plush_Pebblepup / _Lumenfish   2 more plush prizes (original critters), SOCKET_Shelf, SOCKET_Hand, SOCKET_Grab
  Decal_Arcade_Poster_StarRun / _PrismKnight / _CometCup / _ShardRacer   retro wall posters (decalkit), 60 x 90 cm
  Decal_Arcade_Carpet_Cosmic    arcade carpet decal, 200 x 200 cm, tiles seamlessly
Usage: python arcade_prism_props_d.py --kit data/contest/arcade_prism_d.kit.json --out <staging dir>"""
import argparse, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arcade_prism_props_b as AB
import arcade_prism_props_c as AC
K, DK, A = AB.K, AB.DK, AB.A
CAB, CHROME, PRISM, GOLD, BLACK, RED, BLUE, YEL = AB.CAB, AB.CHROME, AB.PRISM, AB.GOLD, AB.BLACK, AB.RED, AB.BLUE, AB.YEL
ball, GLASSC = AC.ball, AC.GLASSC
SEED = 2610264
SCREEN = "1A2A40"


def can(name, c, slot_body, slot_lens):
    x, y, z = c
    return [K.cyl(name + "Yoke", "z", 0.015, 0.015, 0.12, (x, y, z - 0.06), slot_body, 6), K.cyl(name, "z", 0.06, 0.08, 0.2, (x, y, z - 0.22), slot_body, 10),
            K.cyl(name + "Lens", "z", 0.072, 0.072, 0.01, (x, y, z - 0.325), slot_lens, 10)]


def light_rig(v):
    a = "Prop_Arcade_CeilingLightRig_" + v; P = []; S = []; zt = -0.6
    if v == "A":
        P.append(K.box("Truss", (3.0, 0.2, 0.2), (0, 0, zt), 0)); pts = [(-1.2 + 0.8 * i, 0) for i in range(4)]; hangs = [(-1.3, 0), (1.3, 0)]
        P += [K.box("Lace%d" % i, (0.02, 0.21, 0.21), (-1.4 + 0.2 * i, 0, zt), 0, rot=(45, 0, 0), bevel=False) for i in range(15)]
    elif v == "B":
        P += [K.box("TrussX", (2.4, 0.2, 0.2), (0, 0, zt), 0), K.box("TrussY", (0.2, 2.4, 0.2), (0, 0, zt), 0)]; pts = [(1.0, 0), (-1.0, 0), (0, 1.0), (0, -1.0)]; hangs = [(0.6, 0.0), (-0.6, 0.0), (0, 0.6), (0, -0.6)]
    else:
        P += [K.box("Arc%d" % i, (0.2, 1.3, 0.2), (1.2 * math.cos(i * math.pi / 3 + math.pi / 6) * 0.98, 1.2 * math.sin(i * math.pi / 3 + math.pi / 6) * 0.98, zt), 0, rot=(0, 0, math.degrees(i * math.pi / 3 + math.pi / 6))) for i in range(6)]
        pts = [(1.2 * math.cos(i * math.pi / 3), 1.2 * math.sin(i * math.pi / 3)) for i in range(6)]; hangs = pts[::2]
    for i, (x, y) in enumerate(hangs):
        P.append(K.cyl("Cable%d" % i, "z", 0.006, 0.006, -zt - 0.1, (x, y, zt / 2 + 0.05), 1, 4)); P.append(K.cyl("Plate%d" % i, "z", 0.06, 0.06, 0.02, (x, y, -0.01), 1, 8)); S.append(K.socket("Hang_%d" % i, (x, y, 0)))
    for i, (x, y) in enumerate(pts):
        P += can("Can%d" % i, (x, y, zt - 0.1), 1, 2 + i % 2); S.append(K.socket("Light_%d" % i, (x, y, zt - 0.33), forward=(0, 0, -1)))
    return A(a, P, [("truss (chrome)", CHROME, 0.35, 0.9), ("cans / cables (black)", BLACK, 0.5, 0.6), ("lens magenta (emissive)", "FF4AD0", 0.2, 0.0, True), ("lens cyan (emissive)", "6AE8FF", 0.2, 0.0, True)],
             S, [], "ceiling light rig %s; origin = ceiling plane, hangs %.1f m" % (v, 0.95))


def ticket_counter():
    a = "Prop_Arcade_TicketCounter"
    P = [K.box("Body", (0.6, 0.5, 1.2), (0, 0, 0.6), 0), K.box("Hood", (0.62, 0.3, 0.25), (0, 0.08, 1.32), 0), K.box("Display", (0.4, 0.02, 0.14), (0, -0.07, 1.33), 3, bevel=False),
         K.box("Feeder", (0.3, 0.12, 0.06), (0, -0.28, 0.95), 1), K.box("FeedSlot", (0.22, 0.02, 0.01), (0, -0.33, 0.985), 4, bevel=False), K.box("Printer", (0.12, 0.04, 0.05), (0.18, -0.27, 0.75), 1),
         K.box("Stripe", (0.61, 0.51, 0.08), (0, 0, 0.3), 2, bevel=False), K.box("Plinth", (0.64, 0.54, 0.06), (0, 0, 0.03), 4)]
    S = [K.socket("TicketIn", (0, -0.34, 0.99)), K.socket("Display", (0, -0.085, 1.33)), K.socket("ReceiptOut", (0.18, -0.3, 0.75)), K.socket("Player1", (0, -0.9, 0)), K.socket("Floor", (0, 0, 0))]
    return A(a, P, [("cabinet", CAB, 0.5), ("chrome trim", CHROME, 0.3, 0.9), ("prism stripe", PRISM, 0.4), ("ticket count display (emissive, MI digits)", "FF6A3A", 0.3, 0.0, True), ("black", BLACK, 0.5)],
             S, [K.ucx_box(a, 0, (0.64, 0.54, 1.45), (0, 0, 0.725))], "0.64 x 0.54 x 1.45 m ticket eater")


def photo_booth():
    a = "Prop_Arcade_PhotoBooth"; W, D, H = 1.4, 1.0, 2.1
    P = [K.box("Back", (W, 0.06, H), (0, D / 2 - 0.03, H / 2), 0), K.box("SideL", (0.06, D, H), (-W / 2 + 0.03, 0, H / 2), 0), K.box("Roof", (W + 0.06, D + 0.06, 0.08), (0, 0, H + 0.04), 0),
         K.box("Header", (W, 0.06, 0.35), (0, -D / 2 + 0.03, H - 0.175), 2), K.box("Seat", (0.5, 0.35, 0.06), (0.1, 0.2, 0.5), 3), K.cyl("SeatPost", "z", 0.04, 0.04, 0.47, (0.1, 0.2, 0.235), 1, 8),
         K.box("CamPanel", (0.06, 0.6, 0.7), (-W / 2 + 0.09, 0.0, 1.25), 1), K.cyl("Lens", "x", 0.04, 0.04, 0.03, (-W / 2 + 0.135, 0.0, 1.35), 4, 10), K.box("Screen", (0.01, 0.3, 0.2), (-W / 2 + 0.125, 0.0, 1.1), 4, bevel=False),
         K.box("SideR", (0.06, D, H), (W / 2 - 0.03, 0, H / 2), 0), K.box("Slot", (0.15, 0.01, 0.03), (W / 2 + 0.006, -0.3, 1.0), 1, bevel=False, rot=(0, 0, 90)), K.cyl("Rail", "x", 0.012, 0.012, W - 0.1, (0, -D / 2 + 0.06, H - 0.36), 1, 6)]
    for i in range(6): P.append(K.box("Curtain%d" % i, (0.13, 0.03, 1.5), (-0.55 + 0.14 * i, -D / 2 + 0.06, H - 0.38 - 0.75), 3, rot=(0, 0, (-1) ** i * 12)))
    S = [K.socket("Seat", (0.1, 0.2, 0.53)), K.socket("Camera", (-W / 2 + 0.15, 0.0, 1.35), forward=(1, 0, 0)), K.socket("Screen", (-W / 2 + 0.13, 0.0, 1.1)), K.socket("PhotoSlot", (W / 2 + 0.01, -0.3, 1.0)),
         K.socket("CurtainRail", (0, -D / 2 + 0.06, H - 0.36)), K.socket("Entry", (0, -D / 2 - 0.4, 0))]
    return A(a, P, [("booth shell", CAB, 0.5), ("chrome / black fittings", CHROME, 0.3, 0.9), ("header sign (neon decal target)", PRISM, 0.4, 0.0, True), ("curtain / seat velvet", "B02A5A", 0.95), ("lens / screen", SCREEN, 0.1)],
             S, [K.ucx_box(a, 0, (W, 0.06, H), (0, D / 2 - 0.03, H / 2)), K.ucx_box(a, 1, (0.06, D, H), (-W / 2 + 0.03, 0, H / 2)), K.ucx_box(a, 2, (0.06, D, H), (W / 2 - 0.03, 0, H / 2))], "1.4 x 1.0 x 2.15 m photo booth")


def high_score_board():
    a = "Prop_Arcade_HighScoreBoard"; W, H, z0 = 1.6, 2.0, 0.8
    P = [K.box("Panel", (W, 0.08, H), (0, 0, z0 + H / 2), 0), K.box("Bezel", (W + 0.08, 0.06, H + 0.08), (0, 0.02, z0 + H / 2), 1), K.box("Title", (W - 0.2, 0.02, 0.25), (0, -0.05, z0 + H - 0.2), 2, bevel=False)]
    S = [K.socket("Title", (0, -0.065, z0 + H - 0.2)), K.socket("Wall", (0, 0.05, z0 + H / 2))]
    for i in range(10):
        z = z0 + H - 0.45 - 0.145 * i; P.append(K.box("Row%d" % i, (W - 0.24, 0.015, 0.11), (0, -0.045, z), 3 if i % 2 == 0 else 4, bevel=False)); P.append(K.box("Rank%d" % i, (0.1, 0.02, 0.1), (-W / 2 + 0.2, -0.05, z), 2, bevel=False))
        S.append(K.socket("Entry_%d" % i, (0, -0.055, z)))
    return A(a, P, [("board back", BLACK, 0.5), ("chrome bezel", CHROME, 0.3, 0.9), ("title / rank chips (emissive)", "FFE04A", 0.3, 0.0, True), ("entry row A (emissive)", "3A2A70", 0.3, 0.0, True), ("entry row B (emissive)", "2A3A70", 0.3, 0.0, True)],
             S, [], "1.68 x 2.08 m wall board (hang at 0.8 m), 10 entry rows")


def dance_pad():
    a = "Prop_Arcade_Cab_DancePad"; P = []; S = []
    P += [K.box("Tower", (1.6, 0.6, 2.2), (0, 0.9, 1.1), 0), K.box("Screen", (1.0, 0.03, 0.62), (0, 0.585, 1.6), 3, bevel=False), K.box("Marquee", (1.6, 0.4, 0.35), (0, 0.8, 2.37), 2)]
    P += [K.cyl("Speaker%d" % s, "y", 0.16, 0.16, 0.04, (s * 0.62, 0.585, 1.6), 4, 12) for s in (-1, 1)]
    P += [K.box("Stage", (2.4, 1.2, 0.18), (0, -0.1, 0.09), 1), K.box("RailBack", (2.4, 0.05, 0.05), (0, 0.45, 1.0), 1)] + [K.cyl("RailPost%d" % s, "z", 0.025, 0.025, 0.82, (s * 1.15, 0.45, 0.59), 1, 8) for s in (-1, 1)]
    for p, px in (("P1", -0.6), ("P2", 0.6)):
        for nm, (dx, dy) in (("Up", (0, 0.32)), ("Down", (0, -0.32)), ("Left", (-0.32, 0)), ("Right", (0.32, 0))):
            c = (px + dx, -0.1 + dy, 0.185); P.append(K.box("Pad%s%s" % (p, nm), (0.28, 0.28, 0.012), c, 5, bevel=False))
            P.append(K.slab("Arrow%s%s" % (p, nm), [(0, 0.09), (0.07, 0), (0.03, 0), (0.03, -0.08), (-0.03, -0.08), (-0.03, 0), (-0.07, 0)], 0.004, (c[0], c[1], 0.192), 2,
                            rot=(0, 0, {"Up": 0, "Down": 180, "Left": 90, "Right": -90}[nm]))); S.append(K.socket("Pad_%s_%s" % (p, nm), (c[0], c[1], 0.196)))
        S.append(K.socket("Player%s" % p[1], (px, -0.1, 0.18)))
    S += [K.socket("Screen", (0, 0.57, 1.6)), K.socket("CoinSlot", (0.5, 0.59, 0.9))]
    return A(a, P, [("cab body", CAB, 0.5), ("stage / rails (chrome)", CHROME, 0.3, 0.9), ("arrows + marquee (emissive)", PRISM, 0.4, 0.0, True), ("screen", SCREEN, 0.1), ("speakers", BLACK, 0.5), ("pad panels (pressed = MI param)", "D0D8F0", 0.3)],
             S, [K.ucx_box(a, 0, (1.6, 0.6, 2.55), (0, 0.9, 1.27)), K.ucx_box(a, 1, (2.4, 1.2, 0.18), (0, -0.1, 0.09))], "2.4 x 1.8 x 2.55 m dance cab, 2 players, 8 arrow pads")


def pinball():
    a = "Prop_Arcade_Cab_Pinball"; L, W = 1.3, 0.7; tilt = 6.5
    zf, zb = 0.82, 0.82 + L * math.tan(math.radians(tilt))
    P = [K.box("Body", (W, L, 0.3), (0, 0, (zf + zb) / 2), 0, rot=(tilt, 0, 0)), K.box("Glass", (W - 0.06, L - 0.06, 0.01), (0, 0, (zf + zb) / 2 + 0.155), 4, rot=(tilt, 0, 0), bevel=False),
         K.box("Playfield", (W - 0.08, L - 0.08, 0.01), (0, 0, (zf + zb) / 2 + 0.1), 3, rot=(tilt, 0, 0), bevel=False),
         K.box("Backbox", (W, 0.25, 0.75), (0, L / 2 - 0.1, zb + 0.5), 0), K.box("Backglass", (W - 0.08, 0.01, 0.6), (0, L / 2 - 0.23, zb + 0.5), 2, bevel=False)]
    P += [K.box("Leg%d%d" % (s, e), (0.06, 0.06, (zf if e < 0 else zb) - 0.15), (s * (W / 2 - 0.05), e * (L / 2 - 0.05), ((zf if e < 0 else zb) - 0.15) / 2), 1) for s in (-1, 1) for e in (-1, 1)]
    zfl = zf + 0.04 + 0.1
    P += [K.box("Flipper%d" % s, (0.08, 0.025, 0.02), (s * 0.08, -L / 2 + 0.22, zfl), 1, rot=(tilt, 0, s * -25)) for s in (-1, 1)] + [K.cyl("Bumper%d" % i, "z", 0.04, 0.04, 0.05, (-0.15 + 0.15 * i, 0.2, zfl + 0.05 + 0.02 * i), 2, 10) for i in range(3)]
    P += [K.cyl("Plunger", "y", 0.012, 0.012, 0.12, (W / 2 - 0.05, -L / 2 - 0.04, zf + 0.05), 1, 6), K.box("Apron", (W - 0.1, 0.12, 0.04), (0, -L / 2 + 0.1, zfl - 0.01), 1)]
    S = [K.socket("FlipperL", (-0.08, -L / 2 + 0.22, zfl)), K.socket("FlipperR", (0.08, -L / 2 + 0.22, zfl)), K.socket("Plunger", (W / 2 - 0.05, -L / 2 - 0.1, zf + 0.05)), K.socket("Backglass", (0, L / 2 - 0.24, zb + 0.5)),
         K.socket("Ball", (W / 2 - 0.05, -L / 2 + 0.15, zfl)), K.socket("Player1", (0, -L / 2 - 0.5, 0)), K.socket("Floor", (0, 0, 0))]
    return A(a, P, [("cabinet", CAB, 0.5), ("chrome legs / trim", CHROME, 0.3, 0.9), ("backglass / bumpers (emissive)", PRISM, 0.4, 0.0, True), ("playfield art (MI)", "2A1A50", 0.4), ("glass", GLASSC, 0.1)],
             S, [K.ucx_box(a, 0, (W, L, zb + 0.15), (0, 0, (zb + 0.15) / 2)), K.ucx_box(a, 1, (W, 0.25, 0.75), (0, L / 2 - 0.1, zb + 0.5))], "0.7 x 1.3 x %.2f m pinball, playfield tilted %.1f deg" % (zb + 0.88, tilt))


def plush(kind):
    a = "Prop_Arcade_Plush_" + kind
    if kind == "Pebblepup":   # round stone-pup with floppy ears and a gem collar
        P = [ball("Body", (0, 0.02, 0.1), 0.1, 0), ball("Head", (0, -0.09, 0.18), 0.08, 0), ball("Snout", (0, -0.16, 0.16), 0.035, 1, 6), ball("Nose", (0, -0.19, 0.17), 0.012, 3, 6),
             ball("EyeL", (0.035, -0.155, 0.21), 0.014, 3, 6), ball("EyeR", (-0.035, -0.155, 0.21), 0.014, 3, 6), K.cyl("Collar", "z", 0.07, 0.07, 0.02, (0, -0.06, 0.13), 2, 10), ball("Gem", (0, -0.13, 0.12), 0.015, 2, 6)]
        P += [K.box("Ear%d" % s, (0.03, 0.05, 0.08), (s * 0.075, -0.08, 0.2), 1, rot=(0, s * 25, 0)) for s in (-1, 1)] + [ball("Paw%d" % i, (0.06 * (1 if i % 2 else -1), 0.07 * (1 if i > 1 else -1) - 0.02, 0.02), 0.028, 0, 6) for i in range(4)]
        P.append(K.cyl("Tail", "y", 0.02, 0.01, 0.06, (0, 0.13, 0.12), 1, 6, rot=(-30, 0, 0)))
        mats = [("plush pebble grey", "A8A0B8", 0.95), ("plush ears / snout", "D8C8E8", 0.95), ("prism gem collar", PRISM, 0.5), ("eyes / nose", BLACK, 0.4)]
    else:                       # Lumenfish: round glow fish with fins
        P = [ball("Body", (0, 0, 0.12), 0.11, 0), K.slab("Tail", [(0, 0), (0.08, 0.07), (0.1, 0.0), (0.08, -0.07)], 0.025, (0, 0.1, 0.12), 1, rot=(0, -90, 90)),
             K.slab("FinTop", [(0, 0), (0.05, 0.07), (0.09, 0)], 0.02, (0, -0.03, 0.21), 1, rot=(90, 0, 90)), ball("Lure", (0, -0.12, 0.27), 0.022, 2, 6), K.cyl("Stalk", "z", 0.005, 0.005, 0.07, (0, -0.1, 0.235), 1, 4, rot=(-25, 0, 0)),
             ball("EyeL", (0.05, -0.09, 0.15), 0.02, 3, 6), ball("EyeR", (-0.05, -0.09, 0.15), 0.02, 3, 6)]
        P += [K.slab("Side%d" % s, [(0, 0), (0.06, 0.03), (0.07, -0.02)], 0.015, (s * 0.1, 0, 0.1), 1, rot=(0, 0, 0 if s > 0 else 180)) for s in (-1, 1)]
        mats = [("plush teal", "4AC8C0", 0.95), ("fins coral", "F08A6A", 0.95), ("glow lure (emissive)", "FFF0A0", 0.4, 0.0, True), ("eyes", BLACK, 0.4)]
    return A(a, P, mats, [K.socket("Shelf", (0, 0, 0)), K.socket("Hand", (0, 0, 0.12)), K.socket("Grab", (0, 0, 0.22))], [], "~25 cm plush prize")


def assets():
    return [light_rig(v) for v in "ABC"] + [ticket_counter(), photo_booth(), high_score_board(), dance_pad(), pinball(), plush("Pebblepup"), plush("Lumenfish")]


POSTERS = {"StarRun": ("1A1040", "FF4AD0", "FFE04A", "star"), "PrismKnight": ("101830", "6AE8FF", "E6B3FF", "diamond"), "CometCup": ("301018", "FF8A3A", "FFE04A", "comet"), "ShardRacer": ("0A2A28", "4AF0A0", "6AE8FF", "chevron")}


def _hex(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def posters(out, wpx=400, hpx=600):
    res = []
    for k, (bg, c1, c2, shape) in POSTERS.items():
        a = "Decal_Arcade_Poster_" + k; y, x = np.mgrid[0:hpx, 0:wpx]; u, v = x / wpx, y / hpx
        col = _hex(bg)[None, None, :] * (0.6 + 0.4 * v[..., None])            # vertical gradient
        sun = np.hypot(u - 0.5, (v - 0.42) * 1.5) < 0.28
        for i in range(6): sun &= ~((v > 0.42 + 0.03 * i) & (v < 0.42 + 0.03 * i + 0.012))   # retro sun stripes
        col[sun] = col[sun] * 0.2 + _hex(c2) * 0.8
        X, Yc = (u - 0.5), (v - 0.42)
        if shape == "star":
            ang = np.arctan2(Yc, X); r = np.hypot(X, Yc); m = r < 0.09 + 0.07 * np.cos(5 * ang) ** 8
        elif shape == "diamond": m = (np.abs(X) / 0.14 + np.abs(Yc) / 0.22) < 1
        elif shape == "comet": m = (np.hypot(X - 0.08, Yc + 0.08) < 0.08) | ((np.abs((Yc + 0.08) + (X - 0.08) * 0.9) < 0.03) & (X < 0.08) & (X > -0.3))
        else: m = (np.abs(np.abs(X) * 1.2 + Yc * 0.0 - (Yc + 0.15) * 0.5) < 0.05) & (np.abs(Yc) < 0.18)
        col[m] = _hex(c1)
        for (y0, y1, w) in ((0.06, 0.13, 0.8), (0.76, 0.84, 0.7), (0.87, 0.91, 0.5)):              # title / tagline bars (text = MI or overlay)
            bar = (v > y0) & (v < y1) & (np.abs(u - 0.5) < w / 2); col[bar] = _hex(c1) if y0 < 0.5 else _hex(c2)
        border = (u < 0.03) | (u > 0.97) | (v < 0.02) | (v > 0.98); col[border] = _hex("F0E8D8")
        rng = np.random.default_rng(SEED + len(k)); col = np.clip(col * (0.92 + 0.08 * rng.random((hpx, wpx, 1))), 0, 255)   # print grain
        wear = np.clip(1 - np.maximum(0, np.hypot(u - 0.5, v - 0.5) - 0.55) * 3, 0.6, 1); col *= wear[..., None]
        mask = np.ones((hpx, wpx)); hgt = border * 0.2 + m * 0.1
        n = DK.normals(hgt, 1.0, 60.0, 90.0); dd = os.path.join(out, a); files, sha = DK.write_textures(dd, a, col, n, mask)
        man = DK.manifest(a, SEED, "tools/blender/arcade_prism_props_d.py", files, sha, wpx, hpx, [60.0, 90.0], 2.0, "M_Decal_ArcadePoster", 0.6,
                          "retro wall poster, 60 x 90 cm; any arcade wall", extra_params={"Fade": 0.0, "Tint": c1, "Title": "overlay text via MI/widget, no baked words"})
        DK.write_manifest(dd, man); res.append(a)
    return res


def carpet(out, px=512):
    a = "Decal_Arcade_Carpet_Cosmic"; y, x = np.mgrid[0:px, 0:px]; u, v = x / px, y / px; rng = np.random.default_rng(SEED)
    col = np.zeros((px, px, 3)) + _hex("140E2A")
    for (cx, cy, r, h) in [(rng.random(), rng.random(), 0.05 + 0.06 * rng.random(), ("FF4AD0", "6AE8FF", "FFE04A", "4AF0A0")[i % 4]) for i in range(14)]:
        dx = np.minimum(np.abs(u - cx), 1 - np.abs(u - cx)); dy = np.minimum(np.abs(v - cy), 1 - np.abs(v - cy)); d = np.hypot(dx, dy)   # wrap => seamless
        ring = np.abs(d - r) < 0.008; col[ring] = _hex(h)
        if i_ := int(r * 100) % 2: col[d < r * 0.35] = _hex(h)
    for i in range(10):    # zig-zag bolts, wrapped
        cx, cy = rng.random(), rng.random(); h = ("FF4AD0", "6AE8FF", "FFE04A")[i % 3]
        dx = (u - cx + 0.5) % 1 - 0.5; dy = (v - cy + 0.5) % 1 - 0.5
        bolt = (np.abs(dy - 0.02 * np.sign(np.sin(dx * 120))) < 0.006) & (np.abs(dx) < 0.07); col[bolt] = _hex(h)
    stars = rng.random((px, px)) > 0.996; col[stars] = 255
    col = np.clip(col * (0.9 + 0.1 * rng.random((px, px, 1))), 0, 255)   # pile noise
    mask = np.ones((px, px)); hgt = rng.random((px, px)) * 0.15
    n = DK.normals(hgt, 1.0, 200.0, 200.0); dd = os.path.join(out, a); files, sha = DK.write_textures(dd, a, col, n, mask)
    man = DK.manifest(a, SEED, "tools/blender/arcade_prism_props_d.py", files, sha, px, px, [200.0, 200.0], 1.0, "M_Decal_ArcadeCarpet", 0.95,
                      "arcade carpet, 200 x 200 cm, tiles seamlessly (wrap-around pattern); floor decal or tiling floor material",
                      extra_params={"Tiling": 1.0, "UVGlow": 0.0, "Seamless": True})
    DK.write_manifest(dd, man)
    return [a]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    M_ = assets(); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
    print("decals", posters(os.path.join(o.out, "decals")) + carpet(os.path.join(o.out, "decals")))
