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
Usage: python arcade_hall_kit.py --kit data/contest/arcade_hall.kit.json"""
import argparse, os, sys
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


def assets():
    return [wall(), corner(), doorway(), window(), ceiling(), foundation()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); o = ap.parse_args()
    M_ = assets(); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
