# SPDX-License-Identifier: MIT
"""Prismheart Arcade Hall modular kit (blender-team, 2026-10-29, Richey via buffffff 57464). blender-kit/v1, same conventions as the
arcade prop batches: origin bottom-centre on the 2 m grid line, interior face -Y (walls), sockets as the Daedalus hook.
  Prop_ArcadeHall_Wall_2m       2 x 0.2 x 4 m wall bay, prism stripe + crown: SOCKET_Edge_L/R (grid joints), SOCKET_Edge_Top, SOCKET_Floor,
                                SOCKET_Poster (interior, 1.7 m), SOCKET_Sconce
  Prop_ArcadeHall_Corner        0.3 m corner post that hides the joint where two walls meet: SOCKET_Edge_X, SOCKET_Edge_Y, SOCKET_Edge_Top, SOCKET_Floor
  Prop_ArcadeHall_Doorway_2m    wall bay with a 1.4 x 2.6 m opening, chrome frame, neon PRISMHEART sign header outside (+Y):
                                SOCKET_Edge_L/R/Top, SOCKET_Door (portal plane, forward = outside), SOCKET_Entry_Outside, SOCKET_Entry_Inside, SOCKET_Sign
  Prop_ArcadeHall_Window_2m     wall bay with a 1.2 x 1.2 m window (sill 1.2 m), glass + mullions: SOCKET_Edge_L/R/Top, SOCKET_Window, SOCKET_Poster
  Prop_ArcadeHall_CeilingBay_2m 2 x 2 m coffered ceiling bay; origin = ceiling plane (sits on wall tops at z 4 m): SOCKET_Edge_N/E/S/W, SOCKET_Hang
  Prop_ArcadeHall_Foundation_2m 2 x 2 x 0.4 m plinth; origin = TOP centre (hall floor level) so it sinks into island terrain: SOCKET_Edge_N/E/S/W, SOCKET_Floor
Signage pack (2026-10-29): wall neons Prop_ArcadeHall_Sign_Prismheart / _Prizes / _PlayArrow and Prop_ArcadeHall_Sign_DoorInside (EXIT, over the
doorway inside); pixel-font neon letters, origin = back centre on the wall (face -Y): SOCKET_Wall, SOCKET_Light, SOCKET_Hang_L/R.
Exterior dressing (2026-10-29): Prop_ArcadeHall_EntranceSteps (island grade -0.4 m up to the floor, 3 steps), Prop_ArcadeHall_Awning
(neon awning over the doorway, outside), Prop_ArcadeHall_PathTile (1.6 m island path slab with glow inlay, origin = top).
Usage: python arcade_hall_kit.py --kit data/contest/arcade_hall.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arcade_prism_props_b as AB
K = AB.K
CHROME, PRISM, BLACK = AB.CHROME, AB.PRISM, AB.BLACK
WALL, WALL_D, NEON_M, NEON_C, GLASS = "3A2350", "24163A", "FF4AD0", "6AE8FF", "8FD8FF"
G, H, T = 2.0, 4.0, 0.2     # grid, wall height, wall thickness


def A(a, P, mats, S, ucx, size):
    return AB.A(a, P, mats, S, ucx, size)


def edges(S):
    return S + [K.socket("Edge_L", (-G / 2, 0, 0), forward=(-1, 0, 0)), K.socket("Edge_R", (G / 2, 0, 0), forward=(1, 0, 0)), K.socket("Edge_Top", (0, 0, H), forward=(0, 0, 1)),
                K.socket("Floor", (0, 0, 0))]


def trims(P, x0=-G / 2, x1=G / 2, tag=""):
    w = x1 - x0; cx = (x0 + x1) / 2
    P += [K.box("Base" + tag, (w, T + 0.04, 0.15), (cx, 0, 0.075), 1), K.box("Crown" + tag, (w, T + 0.04, 0.12), (cx, 0, H - 0.06), 1),
          K.box("Stripe" + tag, (w, T + 0.01, 0.08), (cx, 0, 1.0), 3, bevel=False)]


MATS = [("wall plaster (deep violet)", WALL, 0.85), ("trim (black)", BLACK, 0.5, 0.3), ("chrome", CHROME, 0.3, 0.9), ("prism stripe (emissive, MI hue)", PRISM, 0.4, 0.0, True)]


def wall():
    a = "Prop_ArcadeHall_Wall_2m"
    P = [K.box("Panel", (G, T, H), (0, 0, H / 2), 0), K.box("Wainscot", (G - 0.1, 0.02, 0.8), (0, -T / 2 - 0.01, 0.55), 1, bevel=False)]
    trims(P)
    S = edges([K.socket("Poster", (0, -T / 2 - 0.005, 1.7)), K.socket("Sconce", (0, -T / 2 - 0.02, 3.2))])
    return A(a, P, MATS, S, [K.ucx_box(a, 0, (G, T, H), (0, 0, H / 2))], "2 x 0.2 x 4 m wall bay")


def corner():
    a = "Prop_ArcadeHall_Corner"
    P = [K.box("Post", (0.3, 0.3, H), (0, 0, H / 2), 1), K.box("Cap", (0.36, 0.36, 0.1), (0, 0, H + 0.05), 2), K.box("Foot", (0.36, 0.36, 0.15), (0, 0, 0.075), 2),
         K.box("Stripe", (0.31, 0.31, 0.08), (0, 0, 1.0), 3, bevel=False)]
    S = [K.socket("Edge_X", (0, 0, 0), forward=(1, 0, 0)), K.socket("Edge_Y", (0, 0, 0), forward=(0, 1, 0)), K.socket("Edge_Top", (0, 0, H + 0.1), forward=(0, 0, 1)), K.socket("Floor", (0, 0, 0))]
    return A(a, P, MATS, S, [K.ucx_box(a, 0, (0.36, 0.36, H + 0.1), (0, 0, (H + 0.1) / 2))], "0.36 x 0.36 x 4.1 m corner post")


def doorway():
    a = "Prop_ArcadeHall_Doorway_2m"; w, h = 1.4, 2.6; j = (G - w) / 2
    P = [K.box("JambL", (j, T, H), (-(w + j) / 2, 0, H / 2), 0), K.box("JambR", (j, T, H), ((w + j) / 2, 0, H / 2), 0), K.box("Lintel", (w, T, H - h), (0, 0, h + (H - h) / 2), 0),
         K.box("FrameL", (0.08, T + 0.06, h), (-w / 2 + 0.04, 0, h / 2), 2), K.box("FrameR", (0.08, T + 0.06, h), (w / 2 - 0.04, 0, h / 2), 2),
         K.box("FrameTop", (w, T + 0.06, 0.08), (0, 0, h - 0.04), 2), K.box("Threshold", (w, T + 0.2, 0.03), (0, 0, 0.015), 2, bevel=False),
         K.box("SignBack", (1.5, 0.06, 0.5), (0, T / 2 + 0.03, 3.25), 1), K.box("SignNeon", (1.3, 0.02, 0.06), (0, T / 2 + 0.07, 3.38), 4, bevel=False),
         K.box("SignNeon2", (1.3, 0.02, 0.06), (0, T / 2 + 0.07, 3.12), 5, bevel=False)]
    for i in range(10):     # letter blocks of the sign, alternating neon
        P.append(K.box("Glyph%d" % i, (0.08, 0.02, 0.14), (-0.54 + 0.12 * i, T / 2 + 0.07, 3.25), 4 + i % 2, bevel=False))
    trims(P, -G / 2, -w / 2, "L"); trims(P, w / 2, G / 2, "R")
    S = edges([K.socket("Door", (0, 0, 0), forward=(0, 1, 0)), K.socket("Entry_Outside", (0, 1.2, 0), forward=(0, -1, 0)), K.socket("Entry_Inside", (0, -1.2, 0)),
               K.socket("Sign", (0, T / 2 + 0.09, 3.25), forward=(0, 1, 0))])
    return A(a, P, MATS + [("neon magenta (emissive)", NEON_M, 0.2, 0.0, True), ("neon cyan (emissive)", NEON_C, 0.2, 0.0, True)], S,
             [K.ucx_box(a, 0, (j, T, H), (-(w + j) / 2, 0, H / 2)), K.ucx_box(a, 1, (j, T, H), ((w + j) / 2, 0, H / 2)), K.ucx_box(a, 2, (w, T, H - h), (0, 0, h + (H - h) / 2))],
             "2 x 0.2 x 4 m doorway bay, 1.4 x 2.6 m opening")


def window():
    a = "Prop_ArcadeHall_Window_2m"; w, s, top = 1.2, 1.2, 2.4; side = (G - w) / 2
    P = [K.box("Below", (G, T, s), (0, 0, s / 2), 0), K.box("Above", (G, T, H - top), (0, 0, top + (H - top) / 2), 0),
         K.box("SideL", (side, T, top - s), (-(w + side) / 2, 0, (s + top) / 2), 0), K.box("SideR", (side, T, top - s), ((w + side) / 2, 0, (s + top) / 2), 0),
         K.box("Glass", (w, 0.03, top - s), (0, 0, (s + top) / 2), 4, bevel=False), K.box("MullionV", (0.05, T + 0.02, top - s), (0, 0, (s + top) / 2), 2),
         K.box("MullionH", (w, T + 0.02, 0.05), (0, 0, (s + top) / 2), 2), K.box("Sill", (w + 0.1, T + 0.14, 0.05), (0, 0, s - 0.025), 2),
         K.box("Head", (w + 0.1, T + 0.06, 0.06), (0, 0, top + 0.03), 2)]
    trims(P)
    S = edges([K.socket("Window", (0, 0, (s + top) / 2), forward=(0, 1, 0)), K.socket("Poster", (0.0, -T / 2 - 0.005, 3.2))])
    return A(a, P, MATS + [("window glass (translucent)", GLASS, 0.05, 0.0)], S, [K.ucx_box(a, 0, (G, T, H), (0, 0, H / 2))], "2 x 0.2 x 4 m window bay, 1.2 x 1.2 m glass")


def ceiling():
    a = "Prop_ArcadeHall_CeilingBay_2m"
    P = [K.box("Slab", (G, G, 0.15), (0, 0, 0.075), 0), K.box("Panel", (1.3, 1.3, 0.02), (0, 0, -0.01), 3, bevel=False)]
    for i, (sx, sy, x, y) in enumerate(((G, 0.12, 0, G / 2 - 0.06), (G, 0.12, 0, -G / 2 + 0.06), (0.12, G, G / 2 - 0.06, 0), (0.12, G, -G / 2 + 0.06, 0))):
        P.append(K.box("Beam%d" % i, (sx, sy, 0.14), (x, y, -0.07), 1))
    S = [K.socket("Edge_N", (0, G / 2, 0), forward=(0, 1, 0)), K.socket("Edge_S", (0, -G / 2, 0), forward=(0, -1, 0)), K.socket("Edge_E", (G / 2, 0, 0), forward=(1, 0, 0)),
         K.socket("Edge_W", (-G / 2, 0, 0), forward=(-1, 0, 0)), K.socket("Hang", (0, 0, -0.02), forward=(0, 0, -1))]
    return A(a, P, [("ceiling (dark violet)", WALL_D, 0.9), ("beams (black)", BLACK, 0.5, 0.3), ("chrome", CHROME, 0.3, 0.9), ("glow panel (emissive)", "C8B8FF", 0.4, 0.0, True)],
             S, [K.ucx_box(a, 0, (G, G, 0.15), (0, 0, 0.075))], "2 x 2 m ceiling bay; origin = ceiling plane")


def foundation():
    a = "Prop_ArcadeHall_Foundation_2m"
    P = [K.box("Plinth", (G, G, 0.4), (0, 0, -0.2), 0), K.box("Lip", (G, 0.06, 0.06), (0, -G / 2 + 0.03, -0.03), 1)]
    S = [K.socket("Edge_N", (0, G / 2, 0), forward=(0, 1, 0)), K.socket("Edge_S", (0, -G / 2, 0), forward=(0, -1, 0)), K.socket("Edge_E", (G / 2, 0, 0), forward=(1, 0, 0)),
         K.socket("Edge_W", (-G / 2, 0, 0), forward=(-1, 0, 0)), K.socket("Floor", (0, 0, 0), forward=(0, 0, 1))]
    return A(a, P, [("foundation stone", "5A5868", 0.9), ("chrome lip", CHROME, 0.3, 0.9)], S, [K.ucx_box(a, 0, (G, G, 0.4), (0, 0, -0.2))], "2 x 2 x 0.4 m plinth; origin = top")


FONT = {"P": ["111", "101", "111", "100", "100"], "R": ["110", "101", "110", "101", "101"], "I": ["111", "010", "010", "010", "111"],
        "S": ["111", "100", "111", "001", "111"], "M": ["101", "111", "111", "101", "101"], "H": ["101", "101", "111", "101", "101"],
        "E": ["111", "100", "110", "100", "111"], "A": ["010", "101", "111", "101", "101"], "T": ["111", "010", "010", "010", "010"],
        "Z": ["111", "001", "010", "100", "111"], "X": ["101", "101", "010", "101", "101"], "L": ["100", "100", "100", "100", "111"],
        "Y": ["101", "101", "010", "010", "010"], "C": ["111", "100", "100", "100", "111"], "D": ["110", "101", "101", "101", "110"]}


def word(P, text, cx, cz, px, y, slot, tag="L"):
    """Pixel-font neon letters (3 x 5 cells of px metres), centred at (cx, cz), standing in the XZ plane at depth y."""
    w = len(text) * 4 * px - px; x0 = cx - w / 2
    for i, ch in enumerate(text):
        for r, row in enumerate(FONT[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    P.append(K.box("%s%d_%d_%d" % (tag, i, r, c), (px * 0.9, 0.02, px * 0.9), (x0 + (4 * i + c) * px + px / 2, y, cz + (2 - r) * px), slot, bevel=False))


SIGN_MATS = [("sign back (black)", BLACK, 0.5, 0.3), ("chrome frame", CHROME, 0.3, 0.9), ("neon magenta (emissive)", NEON_M, 0.2, 0.0, True),
             ("neon cyan (emissive)", NEON_C, 0.2, 0.0, True), ("neon gold (emissive)", "FFE04A", 0.2, 0.0, True)]


def neon_sign(a, text, w, h, border_slot, text_slot, px, extra=None, size=""):
    """Wall-mounted neon sign; origin = back centre on the wall surface, face -Y, so the assembler sets z = mount height."""
    d = 0.08; P = [K.box("Back", (w, d, h), (0, -d / 2, 0), 0), K.box("FrameTop", (w + 0.04, d + 0.02, 0.03), (0, -d / 2, h / 2), 1),
                   K.box("FrameBot", (w + 0.04, d + 0.02, 0.03), (0, -d / 2, -h / 2), 1)]
    tz = 0.0 if not extra else 0.06
    for k, (sx, sz, x, z) in enumerate(((w - 0.08, 0.025, 0, h / 2 - 0.06), (w - 0.08, 0.025, 0, -h / 2 + 0.06), (0.025, h - 0.12, -w / 2 + 0.04, 0), (0.025, h - 0.12, w / 2 - 0.04, 0))):
        P.append(K.box("Tube%d" % k, (sx, 0.025, sz), (x, -d - 0.015, z), border_slot, bevel=False))
    word(P, text, 0, tz, px, -d - 0.012, text_slot)
    if extra: extra(P, d)
    S = [K.socket("Wall", (0, 0, 0), forward=(0, 1, 0)), K.socket("Light", (0, -d - 0.3, 0), forward=(0, -1, 0)), K.socket("Hang_L", (-w / 2 + 0.1, -d / 2, h / 2)),
         K.socket("Hang_R", (w / 2 - 0.1, -d / 2, h / 2))]
    return A(a, P, SIGN_MATS, S, [K.ucx_box(a, 0, (w, d, h), (0, -d / 2, 0))], size)


def sign_prismheart():
    return neon_sign("Prop_ArcadeHall_Sign_Prismheart", "PRISMHEART", 2.3, 0.6, 2, 3, 0.045, None, "2.3 x 0.6 m wall neon")


def sign_prizes():
    def star(P, d):
        P.append(K.slab("Star", [(0.09 * math.cos(math.radians(90 + 36 * k)) * (1 if k % 2 == 0 else 0.45), 0.09 * math.sin(math.radians(90 + 36 * k)) * (1 if k % 2 == 0 else 0.45)) for k in range(10)],
                        0.02, (0, -d - 0.012, -0.14), 4, rot=(90, 0, 0)))
    return neon_sign("Prop_ArcadeHall_Sign_Prizes", "PRIZES", 1.3, 0.5, 4, 2, 0.04, star, "1.3 x 0.5 m prize neon")


def sign_play():
    a = "Prop_ArcadeHall_Sign_PlayArrow"; m = neon_sign(a, "PLAY", 1.1, 0.45, 3, 4, 0.04, lambda P, d: P.append(
        K.slab("Arrow", [(-0.2, 0.03), (0.08, 0.03), (0.08, 0.08), (0.2, 0.0), (0.08, -0.08), (0.08, -0.03), (-0.2, -0.03)], 0.02, (0, -0.092, -0.14), 2, rot=(90, 0, 0))), "1.1 x 0.45 m arrow neon")
    return m


def sign_door_inside():
    """Over the doorway, inside face: EXIT neon on a bar that sits on the lintel (origin = back centre on the wall)."""
    return neon_sign("Prop_ArcadeHall_Sign_DoorInside", "EXIT", 0.9, 0.3, 3, 2, 0.03, None, "0.9 x 0.3 m inside-door EXIT neon")


def sign_assets():
    return [sign_prismheart(), sign_prizes(), sign_play(), sign_door_inside()]


def entrance_steps():
    """3 steps from island grade (z = -0.4, the Foundation_2m depth) up to the hall floor (z = 0). Origin = top centre at the wall's
    outer face; the flight runs out along -Y (local), so the assembler turns it to face away from the doorway."""
    a = "Prop_ArcadeHall_EntranceSteps"; w, rise, run = 2.0, 0.4 / 3, 0.3; P = []
    for i in range(3):
        top = -i * rise; d = run * (i + 1)
        P.append(K.box("Step%d" % i, (w, run, 0.4 + top), (0, -run * i - run / 2, -0.4 + (0.4 + top) / 2), 0))
        P.append(K.box("Nosing%d" % i, (w - 0.04, 0.03, 0.02), (0, -run * i - run + 0.015, top - 0.01), 3, bevel=False))
    for s in (-1, 1):
        P.append(K.box("Cheek%d" % (s > 0), (0.1, 0.9, 0.5), (s * (w / 2 + 0.05), -0.45, -0.15), 1))
        P.append(K.box("RailPost%d" % (s > 0), (0.05, 0.05, 0.9), (s * (w / 2 + 0.05), -0.85, 0.35), 2))
        P.append(K.box("Rail%d" % (s > 0), (0.05, 0.9, 0.05), (s * (w / 2 + 0.05), -0.45, 0.8), 2))
    S = [K.socket("Top", (0, 0, 0), forward=(0, 1, 0)), K.socket("Bottom", (0, -0.9, -0.4), forward=(0, -1, 0)), K.socket("Edge_L", (-w / 2, -0.45, -0.4)),
         K.socket("Edge_R", (w / 2, -0.45, -0.4))]
    return A(a, P, [("step stone", "5A5868", 0.85), ("cheek walls (black)", BLACK, 0.5, 0.3), ("chrome rails", CHROME, 0.3, 0.9), ("nosing glow (emissive)", NEON_C, 0.2, 0.0, True)],
             S, [K.ucx_box(a, i, (w, run, 0.4 - i * rise), (0, -run * i - run / 2, -0.4 + (0.4 - i * rise) / 2)) for i in range(3)], "2.2 x 0.9 x 0.4 m entrance steps, 3 x 13 cm rise")


def awning():
    """Neon awning over the doorway, outside; origin = back centre on the outer wall face, sticks out along -Y (local)."""
    a = "Prop_ArcadeHall_Awning"; w, d = 2.2, 1.0; P = []
    P.append(K.slab("Canopy", [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, -d), (-w / 2, -d)], 0.04, (0, 0, 0.12), 0, rot=None))
    for i in range(6):     # alternating stripes on top
        P.append(K.box("Stripe%d" % i, (w / 6 - 0.01, d - 0.04, 0.012), (-w / 2 + w / 12 + i * w / 6, -d / 2, 0.146), 1 + i % 2, bevel=False))
    P.append(K.box("Valance", (w, 0.03, 0.18), (0, -d + 0.015, 0.05), 0))
    P.append(K.box("NeonEdge", (w - 0.06, 0.02, 0.03), (0, -d - 0.015, 0.05), 3, bevel=False))
    for s in (-1, 1):
        P.append(K.cyl("Brace%d" % (s > 0), "y", 0.012, 0.012, 0.99, (s * (w / 2 - 0.1), -0.46, -0.125), 4, 6, rot=(-27, 0, 0)))
    S = [K.socket("Wall", (0, 0, 0), forward=(0, 1, 0)), K.socket("Light", (0, -d / 2, 0.08), forward=(0, 0, -1)), K.socket("Sign", (0, -d - 0.03, 0.05), forward=(0, -1, 0))]
    return A(a, P, [("canopy (black)", BLACK, 0.5, 0.3), ("stripe magenta", NEON_M, 0.5), ("stripe cyan", NEON_C, 0.5), ("neon edge (emissive)", "FFE04A", 0.2, 0.0, True), ("chrome", CHROME, 0.3, 0.9)],
             S, [K.ucx_box(a, 0, (w, d, 0.2), (0, -d / 2, 0.08))], "2.2 x 1.0 m neon awning")


def path_tile():
    """1.6 x 1.6 m island path slab; origin = top centre (island grade). Glow inlay strip along the walking direction (Y)."""
    a = "Prop_ArcadeHall_PathTile"; s = 1.6
    P = [K.box("Slab", (s, s, 0.08), (0, 0, -0.04), 0), K.box("Inlay", (0.12, s - 0.1, 0.012), (0, 0, 0.0), 2, bevel=False)]
    for k in (-1, 1): P.append(K.box("Kerb%d" % (k > 0), (0.08, s, 0.1), (k * (s / 2 - 0.04), 0, -0.03), 1))
    S = [K.socket("Next", (0, -s / 2, 0), forward=(0, -1, 0)), K.socket("Prev", (0, s / 2, 0), forward=(0, 1, 0)), K.socket("Floor", (0, 0, 0), forward=(0, 0, 1))]
    return A(a, P, [("path stone", "6A6878", 0.9), ("kerb (dark)", "3A3848", 0.9), ("path glow inlay (emissive)", PRISM, 0.4, 0.0, True)],
             S, [K.ucx_box(a, 0, (s, s, 0.08), (0, 0, -0.04))], "1.6 x 1.6 m path slab")


def exterior_assets():
    return [entrance_steps(), awning(), path_tile()]


def assets():
    return [wall(), corner(), doorway(), window(), ceiling(), foundation()] + sign_assets() + exterior_assets()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); o = ap.parse_args()
    M_ = assets(); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
