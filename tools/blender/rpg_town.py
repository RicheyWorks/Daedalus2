# SPDX-License-Identifier: MIT
"""Walkable towns for the two RPG realms — town tiles, walking villagers and a sample town per realm.

    python tools/blender/rpg_town.py OUT_ROOT [ROOT_FOR_DATA]

Same two looks as the overworld (rpg_world_map.py): Portal Realm 8-bit (flat colours, black outlines) and
Prismheart Realm 16-bit (highlights, soft shadows). Pure numpy, original pixel art.

Tiles (16 x 16, shown x4): cobble, path, plaza, wood and stone floors, carpet, brick / plaster / timber walls,
wall with window, wall with door, red and blue roofs (body + ridge + eave), shop signs (weapon, armour, item,
inn, magic), counter, shelf, bed, table, barrel, crate, pot, fountain (2 frames), well, tree, flowers, fence,
stairs, chest (closed / open), lamp post.
Villagers (16 x 16): 8 types (farmer, merchant, guard, elder, child, innkeeper, mage, sailor) x 4 directions x
2 walk frames, as one strip each; Prismheart adds a soft drop shadow.
Outputs OUT_ROOT/claude-battle-kit/<realm>/town/: Tile_<Name>.png (+_1x), NPC_<Type>.png (8 frames: down, up,
left, right x 2), sheet-town.png, npcs.gif-ready sheet-npcs.png, town-demo.png; data/rpg/town-tiles.json
(walkable, interact: shop/inn/chest/sign/talk, shop kind) and the demo town layout as a grid of tile names.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402
import rpg_world_map as WM  # noqa: E402

T = 16
EXTRA = {
    "portal": {"cob1": "#a4a4a4", "cob2": "#747474", "pl1": "#fcd8a8", "pl2": "#d8a060", "wd1": "#c88848", "wd2": "#8c5018", "st1": "#bcbcbc",
               "st2": "#7c7c7c", "cp1": "#d82800", "cp2": "#f8b800", "br1": "#a83010", "br2": "#6c1c08", "pw1": "#fcfcfc", "pw2": "#bcbcbc",
               "rf1": "#d82800", "rf2": "#881400", "rb1": "#0058f8", "rb2": "#0000bc", "gl": "#3cbcfc", "gold": "#f8b800", "skin": "#fca044",
               "hair1": "#503000", "hair2": "#fcfcfc", "c1": "#0058f8", "c2": "#d82800", "c3": "#00a800", "c4": "#a4a4a4", "c5": "#6844fc",
               "c6": "#f878f8", "boot": "#503000", "out": "#000000"},
    "prism": {"cob1": "#b0a898", "cob2": "#807868", "pl1": "#e8d0a0", "pl2": "#c0a070", "wd1": "#b88850", "wd2": "#7c5430", "st1": "#c0c0c8",
              "st2": "#888898", "cp1": "#a83848", "cp2": "#e8c058", "br1": "#b05838", "br2": "#783020", "pw1": "#f0e8d8", "pw2": "#c8b8a0",
              "rf1": "#c84838", "rf2": "#802828", "rb1": "#4870c0", "rb2": "#284888", "gl": "#a0d8f8", "gold": "#f0c040", "skin": "#f0c098",
              "hair1": "#6a4028", "hair2": "#e8e8f0", "c1": "#4870c0", "c2": "#c04848", "c3": "#58a048", "c4": "#9098a8", "c5": "#8058c8",
              "c6": "#e888b8", "boot": "#5a3a28", "out": "#202028"},
}


def C(realm, key):
    if key in EXTRA[realm]:
        return np.array(P.hexc(EXTRA[realm][key]))
    return WM.C(realm, key)


def canvas():
    return np.zeros((T, T, 4), np.float32)


def put(a, x, y, col):
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
        a[y, x, :3] = col
        a[y, x, 3] = 1


def rect(a, x0, y0, w, h, col):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            put(a, x, y, col)


def fill(a, col):
    a[..., :3] = col
    a[..., 3] = 1


def shade(realm, col, k):
    return np.clip(col * k, 0, 1) if realm == "prism" else col


# ---- tiles ------------------------------------------------------------------------------------------------------

def t_cobble(r, f=0):
    a = canvas()
    fill(a, C(r, "cob2"))
    for by in range(0, T, 4):
        off = 2 if (by // 4) % 2 else 0
        for bx in range(-2, T, 4):
            rect(a, bx + off, by, 3, 3, C(r, "cob1"))
            if r == "prism":
                put(a, bx + off, by, np.minimum(1, C(r, "cob1") * 1.15))
    return a


def t_path(r, f=0):
    a = canvas()
    fill(a, C(r, "pl1"))
    for y in range(T):
        for x in range(T):
            if WM.hashf(x, y, 9) < 0.1:
                put(a, x, y, C(r, "pl2"))
    return a


def t_plaza(r, f=0):
    a = canvas()
    fill(a, C(r, "st1"))
    for i in range(T):
        put(a, i, 0, C(r, "st2"))
        put(a, 0, i, C(r, "st2"))
        put(a, i, 8, C(r, "st2"))
        put(a, 8, i, C(r, "st2"))
    return a


def t_wood(r, f=0):
    a = canvas()
    fill(a, C(r, "wd1"))
    for y in range(0, T, 4):
        rect(a, 0, y + 3, T, 1, C(r, "wd2"))
        put(a, (y * 5) % T, y + 1, C(r, "wd2"))
    return a


def t_stone(r, f=0):
    a = t_plaza(r)
    for y in range(T):
        for x in range(T):
            if WM.hashf(x, y, 4) < 0.06:
                put(a, x, y, C(r, "st2"))
    return a


def t_carpet(r, f=0):
    a = canvas()
    fill(a, C(r, "cp1"))
    rect(a, 1, 1, 14, 1, C(r, "cp2"))
    rect(a, 1, 14, 14, 1, C(r, "cp2"))
    rect(a, 1, 1, 1, 14, C(r, "cp2"))
    rect(a, 14, 1, 1, 14, C(r, "cp2"))
    put(a, 7, 7, C(r, "cp2"))
    put(a, 8, 8, C(r, "cp2"))
    return a


def t_wall(r, f=0, kind="brick", feature=None):
    a = canvas()
    if kind == "brick":
        fill(a, C(r, "br2"))
        for by in range(0, T, 4):
            off = 4 if (by // 4) % 2 else 0
            for bx in range(-4, T, 8):
                rect(a, bx + off, by, 7, 3, C(r, "br1"))
    elif kind == "plaster":
        fill(a, C(r, "pw1"))
        rect(a, 0, 14, T, 2, C(r, "pw2"))
    else:                                                                   # timber frame
        fill(a, C(r, "pw1"))
        rect(a, 0, 0, T, 2, C(r, "wd2"))
        rect(a, 0, 14, T, 2, C(r, "wd2"))
        rect(a, 0, 0, 2, T, C(r, "wd2"))
        rect(a, 14, 0, 2, T, C(r, "wd2"))
        for i in range(2, 14):                                              # X brace
            put(a, i, i, C(r, "wd2"))
            put(a, 15 - i, i, C(r, "wd2"))
    if feature == "window":
        rect(a, 4, 3, 8, 7, C(r, "wd2"))
        rect(a, 5, 4, 6, 5, C(r, "gl"))
        rect(a, 7, 4, 1, 5, C(r, "wd2"))
        if r == "prism":
            put(a, 5, 4, np.array([1, 1, 1]))
    elif feature == "door":
        rect(a, 4, 3, 8, 13, C(r, "wd2"))
        rect(a, 5, 4, 6, 12, C(r, "wd1"))
        rect(a, 5, 4, 6, 1, shade(r, C(r, "wd1"), 1.2))
        put(a, 9, 10, C(r, "gold"))
    return a


def t_roof(r, f=0, colour="red", part="body"):
    a = canvas()
    c1, c2 = (C(r, "rf1"), C(r, "rf2")) if colour == "red" else (C(r, "rb1"), C(r, "rb2"))
    fill(a, c1)
    for y in range(1, T, 4):
        rect(a, 0, y + 2, T, 1, c2)
        for x in range((y // 4) % 2 * 2, T, 4):
            put(a, x, y, c2)
            put(a, x, y + 1, c2)
    if part == "ridge":
        rect(a, 0, 0, T, 3, c2)
        rect(a, 0, 1, T, 1, shade(r, c1, 1.25) if r == "prism" else c1)
    elif part == "eave":
        rect(a, 0, 13, T, 3, C(r, "out") if r == "portal" else shade(r, c2, 0.7))
    return a


SIGN_ICON = {   # 8 x 8 glyph on the sign board
    "weapon": ["......#.", ".....#..", "....#...", "...#....", "#.#.....", ".#......", "#.#.....", "........"],
    "armor": ["#..##..#", "########", ".######.", ".######.", ".######.", "..####..", "...##...", "........"],
    "item": ["...##...", "..#..#..", "..####..", ".######.", ".######.", ".######.", "..####..", "........"],
    "inn": ["........", "#.......", "#.####..", "#######.", "#.....#.", "#.....#.", "........", "........"],
    "magic": ["...#....", "..###...", ".#####..", "...#....", "...#..#.", "...#.###", "......#.", "........"],
}


def t_sign(r, f=0, kind="item"):
    a = t_wall(r, kind="plaster")
    rect(a, 2, 2, 12, 11, C(r, "out"))
    rect(a, 3, 3, 10, 9, C(r, "wd1"))
    col = {"weapon": C(r, "st1"), "armor": C(r, "c4"), "item": C(r, "c3"), "inn": C(r, "cp1"), "magic": C(r, "c5")}[kind]
    for y, row in enumerate(SIGN_ICON[kind]):
        for x, ch in enumerate(row):
            if ch == "#":
                put(a, 4 + x, 3 + y, col)
    return a


def t_counter(r, f=0):
    a = t_wood(r)
    rect(a, 0, 5, T, 8, C(r, "wd2"))
    rect(a, 0, 5, T, 2, shade(r, C(r, "wd1"), 1.1))
    rect(a, 0, 12, T, 1, C(r, "out"))
    return a


def t_shelf(r, f=0):
    a = t_wall(r, kind="plaster")
    for y in (3, 9):
        rect(a, 1, y + 4, 14, 1, C(r, "wd2"))
        for i, c in enumerate(("c2", "c3", "c1", "gold", "c5")):
            rect(a, 2 + i * 3, y, 2, 4, C(r, c))
    return a


def t_bed(r, f=0):
    a = t_wood(r)
    rect(a, 2, 1, 12, 14, C(r, "wd2"))
    rect(a, 3, 2, 10, 4, C(r, "pw1"))
    rect(a, 3, 6, 10, 8, C(r, "c1"))
    rect(a, 3, 6, 10, 1, shade(r, C(r, "c1"), 1.3))
    return a


def t_table(r, f=0):
    a = t_wood(r)
    rect(a, 2, 3, 12, 8, C(r, "wd2"))
    rect(a, 3, 4, 10, 6, shade(r, C(r, "wd1"), 1.15))
    rect(a, 3, 11, 2, 3, C(r, "wd2"))
    rect(a, 11, 11, 2, 3, C(r, "wd2"))
    put(a, 7, 6, C(r, "pw1"))
    put(a, 8, 6, C(r, "pw1"))
    return a


def prop_on(base, r, draw):
    a = base(r)
    draw(a, r)
    return a


def d_barrel(a, r):
    for y in range(2, 15):
        w = 5 if y in (2, 14) else 6
        rect(a, 8 - w, y, w * 2, 1, C(r, "wd1"))
    for y in (4, 12):
        rect(a, 2, y, 12, 1, C(r, "out"))
    rect(a, 3, 2, 10, 1, C(r, "wd2"))


def d_crate(a, r):
    rect(a, 2, 3, 12, 11, C(r, "wd2"))
    rect(a, 3, 4, 10, 9, C(r, "wd1"))
    for i in range(9):
        put(a, 3 + i, 4 + i, C(r, "wd2"))


def d_pot(a, r):
    for y in range(4, 14):
        w = [3, 4, 5, 6, 6, 6, 6, 5, 4, 3][y - 4]
        rect(a, 8 - w, y, w * 2, 1, C(r, "br1"))
    rect(a, 5, 3, 6, 1, C(r, "br2"))
    if r == "prism":
        rect(a, 4, 6, 1, 4, np.minimum(1, C(r, "br1") * 1.3))


def d_tree(a, r):
    rect(a, 7, 10, 2, 5, C(r, "b2"))
    for y in range(T):
        for x in range(T):
            d = math.hypot(x - 7.5, y - 6)
            if d < 6:
                put(a, x, y, C(r, "t1") if (x + y) < 13 or d < 3 else C(r, "t2"))


def d_flowers(a, r):
    for (x, y), c in zip(((3, 3), (10, 4), (6, 9), (13, 11), (2, 12), (9, 13)), ("c2", "gold", "c6", "c2", "gold", "c6")):
        put(a, x, y, C(r, c))
        put(a, x, y + 1, C(r, "t2"))


def d_fence(a, r):
    rect(a, 0, 6, T, 2, C(r, "wd1"))
    rect(a, 0, 11, T, 2, C(r, "wd1"))
    for x in (1, 7, 13):
        rect(a, x, 3, 2, 12, C(r, "wd2"))


def d_stairs(a, r):
    for i in range(4):
        rect(a, 0, i * 4, T, 3, shade(r, C(r, "st1"), 1 - i * 0.08))
        rect(a, 0, i * 4 + 3, T, 1, C(r, "st2"))


def d_chest(a, r, opened=False):
    rect(a, 2, 5, 12, 9, C(r, "out"))
    rect(a, 3, 6, 10, 7, C(r, "wd1"))
    rect(a, 3, 9, 10, 1, C(r, "gold"))
    put(a, 7, 9, C(r, "out"))
    put(a, 8, 9, C(r, "out"))
    if opened:
        rect(a, 3, 6, 10, 3, C(r, "out"))
        rect(a, 2, 2, 12, 3, C(r, "wd2"))
    else:
        rect(a, 3, 6, 10, 2, shade(r, C(r, "wd1"), 1.2))


def d_lamp(a, r):
    rect(a, 7, 5, 2, 10, C(r, "out"))
    rect(a, 5, 1, 6, 5, C(r, "out"))
    rect(a, 6, 2, 4, 3, C(r, "gold"))


def d_well(a, r):
    for y in range(4, 15):
        for x in range(T):
            d = math.hypot(x - 7.5, (y - 9.5) * 1.3)
            if d < 7:
                put(a, x, y, C(r, "st1") if d > 4.5 else C(r, "w3"))
    rect(a, 2, 1, 1, 6, C(r, "wd2"))
    rect(a, 13, 1, 1, 6, C(r, "wd2"))
    rect(a, 2, 1, 12, 1, C(r, "wd2"))


def t_fountain(r, f=0):
    a = t_plaza(r)
    for y in range(T):
        for x in range(T):
            d = math.hypot(x - 7.5, y - 7.5)
            if d < 7.5:
                put(a, x, y, C(r, "st2") if d > 6.2 else C(r, "w2"))
    rect(a, 7, 5, 2, 6, C(r, "st1"))
    for k, (x, y) in enumerate(((5, 3), (10, 3), (4, 6), (11, 6))):
        put(a, x + (f if k % 2 else -f), y + f, C(r, "w1"))
    put(a, 7, 2 + f, C(r, "w1"))
    put(a, 8, 3 - f, C(r, "w1"))
    return a


TILES = {   # name: (builder, frames, walkable, interact)
    "Cobble": (t_cobble, 1, True, None), "Path": (t_path, 1, True, None), "Plaza": (t_plaza, 1, True, None), "Grass": (lambda r, f=0: WM.t_grass(r), 1, True, None),
    "WoodFloor": (t_wood, 1, True, None), "StoneFloor": (t_stone, 1, True, None), "Carpet": (t_carpet, 1, True, None),
    "WallBrick": (lambda r, f=0: t_wall(r, kind="brick"), 1, False, None), "WallPlaster": (lambda r, f=0: t_wall(r, kind="plaster"), 1, False, None),
    "WallTimber": (lambda r, f=0: t_wall(r, kind="timber"), 1, False, None), "WallWindow": (lambda r, f=0: t_wall(r, kind="plaster", feature="window"), 1, False, None),
    "WallDoor": (lambda r, f=0: t_wall(r, kind="plaster", feature="door"), 1, True, "door"), "BrickDoor": (lambda r, f=0: t_wall(r, kind="brick", feature="door"), 1, True, "door"),
    "BrickWindow": (lambda r, f=0: t_wall(r, kind="brick", feature="window"), 1, False, None),
    "RoofRed": (lambda r, f=0: t_roof(r), 1, False, None), "RoofRedRidge": (lambda r, f=0: t_roof(r, part="ridge"), 1, False, None),
    "RoofRedEave": (lambda r, f=0: t_roof(r, part="eave"), 1, False, None), "RoofBlue": (lambda r, f=0: t_roof(r, colour="blue"), 1, False, None),
    "RoofBlueRidge": (lambda r, f=0: t_roof(r, colour="blue", part="ridge"), 1, False, None),
    "RoofBlueEave": (lambda r, f=0: t_roof(r, colour="blue", part="eave"), 1, False, None),
    "SignWeapon": (lambda r, f=0: t_sign(r, kind="weapon"), 1, False, "shop:weapon"), "SignArmor": (lambda r, f=0: t_sign(r, kind="armor"), 1, False, "shop:armor"),
    "SignItem": (lambda r, f=0: t_sign(r, kind="item"), 1, False, "shop:item"), "SignInn": (lambda r, f=0: t_sign(r, kind="inn"), 1, False, "inn"),
    "SignMagic": (lambda r, f=0: t_sign(r, kind="magic"), 1, False, "shop:magic"),
    "Counter": (t_counter, 1, False, "talk_across"), "Shelf": (t_shelf, 1, False, None), "Bed": (t_bed, 1, False, "rest"), "Table": (t_table, 1, False, None),
    "Barrel": (lambda r, f=0: prop_on(t_wood, r, d_barrel), 1, False, "search"), "Crate": (lambda r, f=0: prop_on(t_wood, r, d_crate), 1, False, "search"),
    "Pot": (lambda r, f=0: prop_on(t_stone, r, d_pot), 1, False, "search"), "Fountain": (t_fountain, 2, False, "save"),
    "Well": (lambda r, f=0: prop_on(t_cobble, r, d_well), 1, False, "search"), "Tree": (lambda r, f=0: prop_on(lambda q: WM.t_grass(q), r, d_tree), 1, False, None),
    "Flowers": (lambda r, f=0: prop_on(lambda q: WM.t_grass(q), r, d_flowers), 1, True, None),
    "Fence": (lambda r, f=0: prop_on(lambda q: WM.t_grass(q), r, d_fence), 1, False, None), "Stairs": (lambda r, f=0: prop_on(canvas_stone, r, d_stairs), 1, True, "stairs"),
    "Chest": (lambda r, f=0: prop_on(t_stone, r, d_chest), 1, False, "chest"),
    "ChestOpen": (lambda r, f=0: prop_on(t_stone, r, lambda a, q: d_chest(a, q, True)), 1, False, None),
    "Lamp": (lambda r, f=0: prop_on(t_plaza, r, d_lamp), 1, False, None),
    "Water": (lambda r, f=0: WM.t_water(r, f), 2, False, None),
}


def canvas_stone(r):
    return t_stone(r)


def tile(realm, name, f=0):
    return TILES[name][0](realm, f)


# ---- villagers ---------------------------------------------------------------------------------------------------
NPCS = {   # type: (hair, cloth, cloth2, extras)
    "Farmer": ("hair1", "c3", "wd2", "hat"), "Merchant": ("hair1", "c5", "gold", "cap"), "Guard": ("hair1", "c4", "c1", "helmet"),
    "Elder": ("hair2", "c4", "pw2", "beard"), "Child": ("hair1", "c2", "c1", "child"), "Innkeeper": ("hair1", "pw1", "c2", "apron"),
    "Mage": ("hair2", "c5", "c1", "hood"), "Sailor": ("hair1", "c1", "pw1", "stripes"),
}


def npc(realm, kind, d, f):
    hair, cl, cl2, extra = NPCS[kind]
    a = np.zeros((T, T, 4), np.float32)
    oy = 2 if extra == "child" else 0
    H, S, K, K2, B = C(realm, hair), C(realm, "skin"), C(realm, cl), C(realm, cl2), C(realm, "boot")
    side = d in ("left", "right")
    # head
    for y in range(1 + oy, 8):
        for x in range(4, 12):
            if (y == 1 + oy and x in (4, 11)) or (y == 7 and x in (4, 11)):
                continue
            put(a, x, y, S)
    for y in range(1 + oy, 4 + oy):                                         # hair cap
        rect(a, 4, y, 8, 1, H)
    if d == "up":
        rect(a, 4, 1 + oy, 8, 6 - oy, H)
    elif side:
        rect(a, 4 if d == "right" else 8, 1 + oy, 4, 6 - oy, H)
    else:
        put(a, 4, 4 + oy, H)
        put(a, 11, 4 + oy, H)
    ey = 5 + oy // 2
    eye = C(realm, "out")
    if d == "down":
        put(a, 6, ey, eye)
        put(a, 9, ey, eye)
    elif d == "right":
        put(a, 10, ey, eye)
    elif d == "left":
        put(a, 5, ey, eye)
    if extra == "beard" and d != "up":
        rect(a, 5 if not side else (7 if d == "right" else 5), 6, 6 if not side else 4, 2, C(realm, "hair2"))
    if extra == "helmet":
        rect(a, 4, oy, 8, 3, C(realm, "c4"))
        put(a, 7, oy - 1 if oy else 0, C(realm, "c2"))
    if extra == "hat":
        rect(a, 3, 1, 10, 1, C(realm, "pl1"))
        rect(a, 5, 0, 6, 1, C(realm, "pl1"))
    if extra == "cap":
        rect(a, 4, 1, 8, 2, C(realm, "c2"))
    if extra == "hood":
        rect(a, 3, 1, 10, 3, K)
        rect(a, 3, 1, 1, 7, K)
        rect(a, 12, 1, 1, 7, K)
    # body
    by = 8
    bh = 4 if extra != "child" else 3
    bx0, bw = (5, 6) if not side else (6, 4)
    rect(a, bx0, by, bw, bh, K)
    if extra == "apron" and d != "up":
        rect(a, bx0 + 1, by + 1, bw - 2, bh, C(realm, "pw2") if realm == "portal" else C(realm, "pw1"))
        rect(a, bx0, by, bw, 1, K2)
    if extra == "stripes":
        for yy in range(by, by + bh, 2):
            rect(a, bx0, yy, bw, 1, K2)
    if extra == "hood":
        rect(a, bx0 - 1, by, bw + 2, bh + 2, K)                            # long robe
    rect(a, bx0, by + bh - 1, bw, 1, K2)                                   # belt / hem
    # arms swing with the walk
    sw = 1 if f else 0
    if not side:
        rect(a, 4, by, 1, 3, K)
        rect(a, 11, by, 1, 3, K)
        put(a, 4, by + 3 - sw, S)
        put(a, 11, by + 2 + sw, S)
    else:
        ax = 8 if d == "right" else 7
        rect(a, ax + (sw if d == "right" else -sw), by + 1, 1, 3, K)
        put(a, ax + (sw if d == "right" else -sw), by + 4, S)
    # legs
    ly = by + bh
    if not side:
        if f == 0:
            rect(a, 6, ly, 2, T - 1 - ly, K2 if extra != "hood" else B)
            rect(a, 8, ly, 2, T - 1 - ly, K2 if extra != "hood" else B)
            rect(a, 6, T - 1, 2, 1, B)
            rect(a, 8, T - 1, 2, 1, B)
        else:
            rect(a, 6, ly, 2, T - 2 - ly, K2)
            rect(a, 8, ly, 2, T - 1 - ly, K2)
            rect(a, 6, T - 2, 2, 1, B)
            rect(a, 8, T - 1, 2, 1, B)
    else:
        if f == 0:
            rect(a, 7, ly, 2, T - 1 - ly, K2)
            rect(a, 7, T - 1, 3 if d == "right" else 2, 1, B)
            if d == "left":
                put(a, 6, T - 1, B)
        else:
            rect(a, 6, ly, 2, T - 1 - ly, K2)
            rect(a, 9, ly, 2, T - 2 - ly, K2)
            rect(a, 6, T - 1, 2, 1, B)
            rect(a, 9, T - 2, 2, 1, B)
    # outline
    m = a[..., 3] > 0
    dil = m.copy()
    dil[1:] |= m[:-1]
    dil[:-1] |= m[1:]
    dil[:, 1:] |= m[:, :-1]
    dil[:, :-1] |= m[:, 1:]
    edge = dil & ~m
    a[edge, :3] = C(realm, "out")
    a[edge, 3] = 1
    if realm == "prism":                                                    # soft highlight on the top-left of the head
        put(a, 5, 2 + oy, np.minimum(1, (H if d != "down" else H) * 1.3))
    return a


def npc_strip(realm, kind):
    return np.concatenate([npc(realm, kind, d, f) for d in ("down", "up", "left", "right") for f in (0, 1)], axis=1)


# ---- a sample town ------------------------------------------------------------------------------------------------

def house(grid, x, y, w, roof="Red", wall="WallPlaster", door_at=None, sign=None):
    for i in range(w):
        grid[y][x + i] = "Roof%sRidge" % roof
        grid[y + 1][x + i] = "Roof%s" % roof
        grid[y + 2][x + i] = "Roof%sEave" % roof
        grid[y + 3][x + i] = ("WallWindow" if wall == "WallPlaster" else "BrickWindow") if i % 2 else wall
    dx = x + (door_at if door_at is not None else w // 2)
    grid[y + 3][dx] = "WallDoor" if wall == "WallPlaster" else "BrickDoor"
    if sign:
        grid[y + 3][dx - 1 if dx - 1 >= x else dx + 1] = "Sign" + sign


def demo_town(realm):
    W, H = 24, 18
    g = [["Grass"] * W for _ in range(H)]
    for x in range(W):
        g[0][x] = g[H - 1][x] = "Fence"
    for y in range(H):
        g[y][0] = g[y][W - 1] = "Fence"
    for x in range(1, W - 1):
        g[9][x] = "Cobble"
        g[10][x] = "Cobble"
    for y in range(1, H - 1):
        g[y][11] = "Cobble"
        g[y][12] = "Cobble"
    g[H - 1][11] = g[H - 1][12] = "Path"
    for y in range(7, 13):
        for x in range(9, 15):
            g[y][x] = "Plaza"
    g[9][11] = "Fountain"
    house(g, 2, 2, 5, "Red", "WallPlaster", sign="Item")
    house(g, 15, 2, 6, "Blue", "WallBrick", sign="Weapon")
    house(g, 2, 12, 6, "Blue", "WallPlaster", sign="Inn")
    house(g, 16, 12, 5, "Red", "WallBrick", sign="Armor" if realm == "portal" else "Magic")
    for (y, x), n in zip(((7, 3), (7, 5), (7, 17), (7, 20), (16, 9), (16, 15), (2, 9), (2, 13), (5, 9)),
                         ("Tree", "Flowers", "Barrel", "Crate", "Tree", "Tree", "Tree", "Tree", "Well")):
        g[y][x] = n
    for (y, x) in ((8, 9), (8, 14), (11, 9), (11, 14)):
        g[y][x] = "Lamp"
    for x in range(2, 7):
        g[6][x] = "Path"
    for x in range(15, 21):
        g[6][x] = "Path"
    g[1][20] = "Chest"
    npcs = [("Guard", 13, 16, "down"), ("Guard", 10, 16, "down"), ("Merchant", 4, 7, "down"), ("Child", 14, 10, "left"),
            ("Elder", 8, 9, "right"), ("Farmer", 5, 11, "up"), ("Innkeeper", 5, 16, "down"), ("Sailor", 17, 7, "down"), ("Mage", 18, 11, "left")]
    img = np.zeros((H * T, W * T, 4), np.float32)
    for y in range(H):
        for x in range(W):
            img[y * T:(y + 1) * T, x * T:(x + 1) * T] = tile(realm, g[y][x])
    for kind, x, y, d in npcs:
        s = npc(realm, kind, d, 0)
        if realm == "prism":                                                # soft shadow under the feet
            sh = np.zeros_like(s)
            for yy in range(13, 16):
                for xx in range(4, 12):
                    if abs(xx - 7.5) < 4 - (yy - 13):
                        sh[yy, xx] = [0, 0, 0, 0.35]
            img[y * T:(y + 1) * T, x * T:(x + 1) * T] = P.over(img[y * T:(y + 1) * T, x * T:(x + 1) * T], sh)
        img[y * T:(y + 1) * T, x * T:(x + 1) * T] = P.over(img[y * T:(y + 1) * T, x * T:(x + 1) * T], s)
    return img, g, npcs


def build(out_root, data_root=None):
    rows, towns = [], {}
    for realm in ("portal", "prism"):
        od = os.path.join(out_root, "claude-battle-kit", realm, "town")
        os.makedirs(od, exist_ok=True)
        tiles = []
        for name, (fn, nf, walk, act) in TILES.items():
            fr = [tile(realm, name, f) for f in range(nf)]
            strip = np.concatenate(fr, axis=1)
            P.save_png(P.upscale(strip, 4), os.path.join(od, "Tile_%s.png" % name))
            P.save_png(strip, os.path.join(od, "Tile_%s_1x.png" % name))
            tiles.append(P.upscale(fr[0], 4))
            rows.append({"realm": realm, "tile": name, "frames": nf, "walkable": walk, "interact": act,
                         "png": "engines/unreal/art/claude-battle-kit/%s/town/Tile_%s.png" % (realm, name)})
        P.save_png(P.grid_sheet(tiles, 10), os.path.join(od, "sheet-town.png"))
        strips = []
        for kind in NPCS:
            s = npc_strip(realm, kind)
            P.save_png(P.upscale(s, 4), os.path.join(od, "NPC_%s.png" % kind))
            P.save_png(s, os.path.join(od, "NPC_%s_1x.png" % kind))
            strips.append(P.upscale(s, 4))
        P.save_png(P.grid_sheet(strips, 1), os.path.join(od, "sheet-npcs.png"))
        img, g, npcs = demo_town(realm)
        P.save_png(P.upscale(img, 2), os.path.join(od, "town-demo.png"))
        towns[realm] = {"grid": g, "npcs": [{"type": k, "x": x, "y": y, "facing": d} for k, x, y, d in npcs]}
    if data_root:
        d = os.path.join(data_root, "data", "rpg")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "town-tiles.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.town/v1", "source": "tools/blender/rpg_town.py", "tile_size": T, "scale": 4,
                       "npc_strip": "8 frames of 16 px: down0 down1 up0 up1 left0 left1 right0 right1",
                       "npc_types": list(NPCS), "tiles": rows, "demo_towns": towns}, f, indent=1)
    return rows


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    data = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    print("TOWN %d tiles" % len(build(out, data)))
