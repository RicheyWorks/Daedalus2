# SPDX-License-Identifier: MIT
"""Overworld tiles for the two RPG realms — 16 x 16 pixel tiles, shown x4 (64 px), in two looks:
Portal Realm (8-bit: 4-colour-per-tile palette, hard outlines) and Prismheart Realm (16-bit: richer palette,
highlights and shadows). Original pixel art: terrain is generated from small rules, landmarks are hand-pixeled
16 x 16 ASCII drawings below.

    python tools/blender/rpg_world_map.py OUT_ROOT [ROOT_FOR_DATA]

Outputs OUT_ROOT/claude-battle-kit/<realm>/worldmap/Tile_<Name>.png (x4; animated tiles are horizontal strips of 2
frames) + _1x.png, sheet-worldmap.png, map-demo.png (an island overworld assembled from the tiles with coasts, a
road and landmarks), and data/rpg/worldmap-tiles.json: per tile walkable / ship / airship, the encounter zone it rolls
on (the realm's data/rpg/<realm>-encounters.json keys) and, for landmarks, what entering it opens.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402

T = 16
PAL = {
    "portal": {"g1": "#00a800", "g2": "#58d854", "g3": "#005800", "k": "#000000", "s1": "#f0d088", "s2": "#c89848", "w1": "#3cbcfc",
               "w2": "#0078f8", "w3": "#0000bc", "m1": "#a8a8a8", "m2": "#787878", "m3": "#383838", "n1": "#fcfcfc", "n2": "#a4e4fc",
               "t1": "#00a844", "t2": "#005800", "b1": "#ac7c00", "b2": "#503000", "l1": "#f83800", "l2": "#fca044", "l3": "#881400",
               "sw1": "#587818", "sw2": "#304808", "sw3": "#6888fc", "r1": "#d82800", "r2": "#881400", "wl": "#fcfcfc", "wd": "#bcbcbc",
               "y": "#f8d878", "c1": "#f878f8", "c2": "#fcc4fc", "c3": "#9878f8", "f": "#f83800", "h": "#000000", "p": "#bcbcbc"},
    "prism": {"g1": "#5ca03c", "g2": "#8cc858", "g3": "#386c28", "k": "#202028", "s1": "#ecd8a0", "s2": "#c8a868", "w1": "#68b8f0",
              "w2": "#3880d0", "w3": "#205098", "m1": "#b8a890", "m2": "#887860", "m3": "#504438", "n1": "#f8f8ff", "n2": "#c0d8f0",
              "t1": "#3c8c3c", "t2": "#1c5428", "b1": "#a87848", "b2": "#604028", "l1": "#e85020", "l2": "#ffc048", "l3": "#801808",
              "sw1": "#5c7840", "sw2": "#384c28", "sw3": "#7090a8", "r1": "#c84838", "r2": "#7c2828", "wl": "#f0e8d8", "wd": "#b8a890",
              "y": "#ffe890", "c1": "#c890f8", "c2": "#f0d8ff", "c3": "#7058c8", "f": "#e84848", "h": "#181018", "p": "#d0c8c0"},
}

# Landmarks: '.' = the base tile shows through. Letters map to palette keys via GLYPH.
GLYPH = {"k": "k", "w": "wl", "W": "wd", "r": "r1", "R": "r2", "d": "b2", "g": "y", "f": "f", "s": "m1", "S": "m2", "x": "m3", "h": "h",
         "c": "c1", "C": "c2", "v": "c3", "l": "l1", "L": "l2", "b": "b1", "B": "b2", "p": "p", "n": "n1", "t": "t1", "T": "t2", "q": "w2"}
ICONS = {
    "Town": ("Grass", [
        "................",
        "...kk.......kk..",
        "..krrk.....krrk.",
        ".krrrRk...krrrRk",
        ".kwwwWk...kwwwWk",
        ".kwgdWk...kgwdWk",
        ".kkkkkk...kkkkkk",
        "......kkk.......",
        ".....krrrk......",
        "....krrrrRk.....",
        "...krrrrrrRk....",
        "...kwwwwwwWk....",
        "...kwgwddwWk....",
        "...kwwwddwWk....",
        "...kkkkkkkkk....",
        "................"]),
    "Village": ("Grass", [
        "................",
        "................",
        "....kk..........",
        "...kbbk.........",
        "..kbbbBk...kk...",
        "..kwwwWk..kbbk..",
        "..kwdgWk.kbbbBk.",
        "..kkkkkk.kwwwWk.",
        ".........kwgdWk.",
        "...tt....kkkkkk.",
        "..tttT..........",
        "..tttT...tt.....",
        "...dd...tttT....",
        "...dd...tttT....",
        ".........dd.....",
        "................"]),
    "Castle": ("Grass", [
        ".......f........",
        ".......ff.......",
        "..k.k..k...k.k..",
        "..kwk.kwk..kwk..",
        "..kwk.kWk..kwk..",
        "..kwkkkwkkkkwk..",
        "..kwwwwwwwwwWk..",
        "..kwgwwwwwgwWk..",
        "..kwwwwwwwwwWk..",
        "..kwwwkkkwwwWk..",
        "..kwwkhhhkwwWk..",
        "..kwwkhhhkwwWk..",
        "..kWWkhhhkWWWk..",
        "..kkkkkkkkkkkk..",
        "................",
        "................"]),
    "Cave": ("Mountain", [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "......kkkk......",
        ".....khhhhk.....",
        "....khhhhhhk....",
        "....khhhhhhk....",
        "...kSkhhhhkSk...",
        "...kSkhhhhkSk...",
        "..kSSkhhhhkSSk..",
        "..kkkkkkkkkkkk..",
        "................"]),
    "Tower": ("Grass", [
        "......kkkk......",
        ".....krrrRk.....",
        "....krrrrrRk....",
        "....kkkkkkkk....",
        ".....kwwwWk.....",
        ".....kwgwWk.....",
        ".....kwwwWk.....",
        ".....kwwwWk.....",
        ".....kwgwWk.....",
        ".....kwwwWk.....",
        ".....kwwwWk.....",
        "....kwwwwwWk....",
        "....kwwddwWk....",
        "....kwwddwWk....",
        "....kkkkkkkk....",
        "................"]),
    "Shrine": ("Grass", [
        "................",
        "................",
        "...kkkkkkkkkk...",
        "..krrrrrrrrrRk..",
        "...kkkkkkkkkk...",
        "....kw....wk....",
        "....kw.gg.wk....",
        "....kw.gg.wk....",
        "....kw.ss.wk....",
        "....kw.ss.wk....",
        "....kW.ss.Wk....",
        "...kkkkkkkkkk...",
        "..kssssssssssk..",
        "..kkkkkkkkkkkk..",
        "................",
        "................"]),
    "Dock": ("Water", [
        "................",
        "................",
        "....kkkkkkkkkk..",
        "....kbbbbbbbbk..",
        "....kBBBBBBBBk..",
        "....kbbbbbbbbk..",
        "....kBBBBBBBBk..",
        "....kkkkkkkkkk..",
        ".....kB....kB...",
        ".....kB....kB...",
        "..k.............",
        ".kbk........kk..",
        "kbbbk.....kbbbbk",
        ".kbbbbbbbbbbbbk.",
        "..kkkkkkkkkkkk..",
        "................"]),
    "Ruins": ("Grass", [
        "................",
        "................",
        "..kk.......kk...",
        ".kssk.....kssk..",
        ".ksSk.....ksSk..",
        ".ksSk..k..ksSk..",
        ".ksSk.ksk.ksSk..",
        ".ksSk.kSk.kkkk..",
        ".ksSk.kkk.......",
        ".kkkk......kk...",
        "......kk..kssk..",
        ".....kssk.kSSk..",
        "....kssSSk.kk...",
        "....kkkkkk......",
        "................",
        "................"]),
    "Graveyard": ("Grass", [
        "................",
        "...k......k.....",
        "..ksk....ksk....",
        ".kssSk..kssSk...",
        ".ksxsk..ksxsk...",
        ".kssSk..kssSk...",
        ".kkkkk..kkkkk...",
        "................",
        "......k......k..",
        ".....ksk....ksk.",
        "....kssSk..kssSk",
        "....ksxsk..ksxsk",
        "....kssSk..kssSk",
        "....kkkkk..kkkkk",
        "................",
        "................"]),
    "Volcano": ("Lava", [
        "......L..L......",
        ".....LlLLlL.....",
        "......kllk......",
        ".....kSllSk.....",
        "....kSSllSSk....",
        "....kSSSlSSk....",
        "...kSSSSlSSSk...",
        "...kSSSSSlSSk...",
        "..kSSSSSSSSSSk..",
        "..kSSSSSSSSSSk..",
        ".kSSSSSSSSSSSSk.",
        ".kSSSSSSSSSSSSk.",
        "kkkkkkkkkkkkkkkk",
        "................",
        "................",
        "................"]),
    "Lighthouse": ("Coast", [
        "......kkk.......",
        ".....kgggk......",
        ".....kgggk......",
        "....kkkkkkk.....",
        ".....kwrwk......",
        ".....kwrwk......",
        ".....krwrk......",
        "....kwwrwWk.....",
        "....kwrwrWk.....",
        "....krwwrrk.....",
        "....kwrwwWk.....",
        "...kwwwdwwWk....",
        "...kwwwdwwWk....",
        "...kkkkkkkkk....",
        "................",
        "................"]),
    "AirshipPad": ("Grass", [
        "................",
        "................",
        "....kkkkkkk.....",
        "..kkbbbbbbbkk...",
        ".kbbbBBBBBbbbk..",
        "..kkbbbbbbbkk...",
        "....kk.k.kk.....",
        "......kBk.......",
        "..kkkkkkkkkkkk..",
        ".kppppppppppppk.",
        ".kpggpppppggppk.",
        ".kppppppppppppk.",
        "..kkkkkkkkkkkk..",
        "................",
        "................",
        "................"]),
    "CrystalShrine": ("CrystalField", [
        ".......k........",
        "......kCk.......",
        "......kCvk......",
        ".....kCcvk......",
        ".....kCcvk......",
        "..k..kCcvk..k...",
        ".kCk.kCcvk.kCk..",
        ".kcv.kCcvk.kcv..",
        ".kcv.kCcvk.kcv..",
        ".kkkkkkkkkkkkk..",
        ".kssssssssssSk..",
        ".kSSSSSSSSSSSk..",
        ".kkkkkkkkkkkkk..",
        "................",
        "................",
        "................"]),
    "Inn": ("Grass", [
        "................",
        "....kkkkkkkk....",
        "...krrrrrrrRk...",
        "..krrrrrrrrrRk..",
        ".krrrrrrrrrrrRk.",
        ".kkkkkkkkkkkkkk.",
        "..kwwwwwwwwwWk..",
        "..kwgwkggkwgWk..",
        "..kwwwkggkwwWk..",
        "..kwwwwwwwwwWk..",
        "..kwwwwddwwwWk..",
        "..kwwwwddwwwWk..",
        "..kkkkkkkkkkkk..",
        "................",
        "................",
        "................"]),
}


def C(realm, key):
    return np.array(P.hexc(PAL[realm][key]))


def canvas():
    return np.zeros((T, T, 4), np.float32)


def put(a, x, y, col):
    if 0 <= x < T and 0 <= y < T:
        a[y, x, :3] = col
        a[y, x, 3] = 1


def fill(a, col):
    a[..., :3] = col
    a[..., 3] = 1


def hashf(x, y, s=0):
    v = math.sin(x * 12.9898 + y * 78.233 + s * 37.719) * 43758.5453
    return v - math.floor(v)


def t_grass(realm, f=0, flowers=False):
    a = canvas()
    fill(a, C(realm, "g1"))
    for y in range(T):
        for x in range(T):
            h = hashf(x, y, 1)
            if h < 0.08:
                put(a, x, y, C(realm, "g2"))
            elif h < 0.13 and realm == "prism":
                put(a, x, y, C(realm, "g3"))
    for (x, y) in ((3, 4), (11, 9), (6, 13)):
        put(a, x, y, C(realm, "g3"))
        put(a, x + 1, y - 1, C(realm, "g3"))
        put(a, x + 2, y, C(realm, "g3"))
    if flowers:
        for (x, y), c in zip(((2, 2), (9, 5), (13, 12), (5, 10)), ("y", "c1", "y", "f")):
            put(a, x, y, C(realm, c))
    return a


def t_forest(realm, f=0, pine=False):
    a = t_grass(realm)
    spots = ((4, 5), (12, 4), (8, 11), (1, 12), (14, 12)) if not pine else ((4, 6), (11, 5), (7, 13), (14, 13), (1, 13))
    for cx, cy in spots:
        if pine:
            for dy in range(-5, 2):
                w = (dy + 6) // 2
                for dx in range(-w, w + 1):
                    c = "t1" if dx < 0 or (dx == 0 and dy % 2) else "t2"
                    put(a, cx + dx, cy + dy, C(realm, c))
                put(a, cx - w - 1, cy + dy, C(realm, "k")) if realm == "portal" and dy == 1 else None
            put(a, cx, cy + 2, C(realm, "b2"))
        else:
            for dy in range(-4, 4):
                for dx in range(-4, 4):
                    d = math.hypot(dx + 0.5, dy + 0.5)
                    if d < 3.6:
                        c = "t1" if (dx + dy) < -1 else "t2"
                        if realm == "prism" and dx + dy < -4:
                            c = "g2"
                        put(a, cx + dx, cy + dy, C(realm, c))
                    elif d < 4.3 and dy >= 0:
                        put(a, cx + dx, cy + dy, C(realm, "k" if realm == "portal" else "t2"))
            put(a, cx, cy + 4, C(realm, "b2"))
    return a


def t_hills(realm, f=0):
    a = t_grass(realm)
    for cx, cy, r in ((5, 10, 5), (12, 6, 4)):
        for dx in range(-r, r + 1):
            hgt = int(round(math.sqrt(max(0, r * r - dx * dx)) * 0.7))
            for dy in range(hgt):
                put(a, cx + dx, cy - dy, C(realm, "g2" if dx < 0 else "g1"))
            put(a, cx + dx, cy - hgt, C(realm, "k" if realm == "portal" else "g3"))
    return a


def t_mountain(realm, f=0, snow=False):
    a = t_grass(realm)
    peak, base = 2, 14
    for y in range(peak, base + 1):
        w = (y - peak) * 7 // (base - peak)
        for x in range(8 - w, 8 + w + 1):
            c = "m1" if x < 8 else "m2"
            if snow and y < peak + 4:
                c = "n1" if x < 8 else "n2"
            if realm == "prism" and x == 8 - w + 1 and not (snow and y < peak + 4):
                c = "n2" if snow else "m1"
            put(a, x, y, C(realm, c))
        put(a, 8 - w - 1, y, C(realm, "k" if realm == "portal" else "m3"))
        put(a, 8 + w + 1, y, C(realm, "k" if realm == "portal" else "m3"))
    for x in range(0, T):
        if abs(x - 8) <= 8:
            put(a, x, base + 1, C(realm, "m3"))
    for y in range(peak + 5, base, 3):                                         # ridge line
        put(a, 8 + (y % 2), y, C(realm, "m3"))
    return a


def t_desert(realm, f=0):
    a = canvas()
    fill(a, C(realm, "s1"))
    for i, y in enumerate((3, 8, 13)):
        for x in range(T):
            yy = y + int(round(math.sin((x + i * 5) * 0.5)))
            put(a, x, yy, C(realm, "s2"))
    return a


def t_swamp(realm, f=0):
    a = canvas()
    fill(a, C(realm, "sw1"))
    for cx, cy, r in ((4, 5, 2.6), (11, 11, 3.1)):
        for y in range(T):
            for x in range(T):
                if ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.6)) ** 2 < 1:
                    put(a, x, y, C(realm, "sw3"))
    for x, y in ((9, 3), (2, 12), (14, 6)):
        for k in range(3):
            put(a, x, y - k, C(realm, "sw2"))
        put(a, x + 1, y - 2, C(realm, "sw2"))
    return a


def t_water(realm, f=0, deep=False):
    a = canvas()
    fill(a, C(realm, "w3" if deep else "w2"))
    for i, (x, y) in enumerate(((2, 3), (9, 6), (4, 11), (12, 13))):
        xx = (x + f * 2) % T
        put(a, xx, y, C(realm, "w1" if not deep else "w2"))
        put(a, (xx + 1) % T, y, C(realm, "w1" if not deep else "w2"))
        put(a, (xx + 2) % T, y - 1, C(realm, "w1" if not deep else "w2"))
    return a


def t_snow(realm, f=0):
    a = canvas()
    fill(a, C(realm, "n1"))
    for y in range(T):
        for x in range(T):
            if hashf(x, y, 5) < 0.09:
                put(a, x, y, C(realm, "n2"))
    return a


def t_lava(realm, f=0):
    a = canvas()
    fill(a, C(realm, "l3"))
    for y in range(T):
        for x in range(T):
            v = math.sin(x * 0.7 + y * 0.4 + f * 1.6) + math.sin(y * 0.9 - x * 0.3)
            if v > 1.1:
                put(a, x, y, C(realm, "l2"))
            elif v > 0.4:
                put(a, x, y, C(realm, "l1"))
    return a


def t_road(realm, f=0, vertical=False):
    a = t_grass(realm)
    for i in range(T):
        for j in range(6, 10):
            x, y = (j, i) if vertical else (i, j)
            put(a, x, y, C(realm, "s2" if j in (6, 9) else "s1"))
    return a


def t_bridge(realm, f=0, vertical=False):
    a = t_water(realm, f)
    for i in range(T):
        for j in range(4, 12):
            x, y = (j, i) if vertical else (i, j)
            c = "b2" if j in (4, 11) else ("b1" if i % 4 else "b2")
            put(a, x, y, C(realm, c))
    return a


def t_coast(realm, f=0, side="n"):
    a = t_water(realm, f)
    for x in range(T):
        depth = 5 + int(round(math.sin(x * 0.6 + f) * 1))
        for y in range(depth):
            c = "g1" if y < depth - 3 else ("s1" if y < depth - 1 else "w1")
            put(a, x, y, C(realm, c))
    k = {"n": 0, "e": 3, "s": 2, "w": 1}[side]
    return np.ascontiguousarray(np.rot90(a, k))


def t_crystal(realm, f=0):
    a = t_grass(realm)
    for cx, cy, h in ((4, 12, 5), (11, 9, 6), (8, 14, 3), (13, 14, 4)):
        for y in range(h):
            put(a, cx, cy - y, C(realm, "c2"))
            put(a, cx + 1, cy - y, C(realm, "c1" if y < h - 1 else "c2"))
        put(a, cx + 2, cy, C(realm, "c3"))
    return a


TERRAIN = {   # name: (fn, kwargs, frames)
    "Grass": (t_grass, {}, 1), "Flowers": (t_grass, {"flowers": True}, 1), "Forest": (t_forest, {}, 1), "PineForest": (t_forest, {"pine": True}, 1),
    "Hills": (t_hills, {}, 1), "Mountain": (t_mountain, {}, 1), "SnowPeak": (t_mountain, {"snow": True}, 1), "Desert": (t_desert, {}, 1),
    "Swamp": (t_swamp, {}, 1), "Water": (t_water, {}, 2), "DeepSea": (t_water, {"deep": True}, 2), "Snow": (t_snow, {}, 1),
    "Lava": (t_lava, {}, 2), "Road": (t_road, {}, 1), "RoadV": (t_road, {"vertical": True}, 1), "Bridge": (t_bridge, {}, 2),
    "BridgeV": (t_bridge, {"vertical": True}, 2), "CoastN": (t_coast, {"side": "n"}, 2), "CoastE": (t_coast, {"side": "e"}, 2),
    "CoastS": (t_coast, {"side": "s"}, 2), "CoastW": (t_coast, {"side": "w"}, 2), "CrystalField": (t_crystal, {}, 1),
    "Coast": (t_coast, {"side": "s"}, 2),
}
# what each tile means to the game; zones are the realm's encounter-table keys
RULES = {
    "Grass": ("meadow", "plains"), "Flowers": ("meadow", "plains"), "Forest": ("forest", "forest"), "PineForest": ("forest_deep", "forest_deep"),
    "Hills": ("hills", "plains_far"), "Mountain": (None, None), "SnowPeak": (None, None), "Desert": ("desert", "desert"), "Swamp": ("swamp", "swamp"),
    "Water": ("sea", "sea"), "DeepSea": ("sea_deep", "sea_deep"), "Snow": ("snow", "snow"), "Lava": ("volcano", None), "Road": (None, None),
    "RoadV": (None, None), "Bridge": (None, None), "BridgeV": (None, None), "CoastN": ("coast", "coast"), "CoastE": ("coast", "coast"),
    "CoastS": ("coast", "coast"), "CoastW": ("coast", "coast"), "Coast": ("coast", "coast"), "CrystalField": ("meadow_deep", "crystal_cave"),
}
ENTER = {"Town": "town", "Village": "town", "Castle": "castle", "Cave": "dungeon:cave", "Tower": "dungeon:tower", "Shrine": "shrine (save, heal)",
         "Dock": "harbour (board ship)", "Ruins": "dungeon:ruins", "Graveyard": "dungeon:graveyard/crypt", "Volcano": "dungeon:volcano",
         "Lighthouse": "town (coast)", "AirshipPad": "airship dock", "CrystalShrine": "Prism Shard dungeon", "Inn": "inn (rest)"}


def terrain(realm, name, f=0):
    fn, kw, _ = TERRAIN[name]
    return fn(realm, f, **kw)


def icon(realm, name, f=0):
    base, rows = ICONS[name]
    a = terrain(realm, base, f)
    for y, row in enumerate(rows):
        assert len(row) <= T, (name, y, len(row))
        for x, ch in enumerate(row.ljust(T, ".")):
            if ch != ".":
                put(a, x, y, C(realm, GLYPH[ch]))
    if realm == "prism":                                                       # 16-bit: a soft drop shadow under the icon
        mask = np.array([[ch != "." for ch in row.ljust(T, ".")] for row in rows])
        sh = np.zeros_like(mask)
        sh[1:, 1:] = mask[:-1, :-1]
        sh &= ~mask
        a[sh, :3] *= 0.72
    return a


def frames_of(name):
    if name in TERRAIN:
        return TERRAIN[name][2]
    return TERRAIN[ICONS[name][0]][2]


def tile(realm, name, f=0):
    return terrain(realm, name, f) if name in TERRAIN else icon(realm, name, f)


def demo_map(realm, W=32, H=20, seed=7):
    names = demo_layout(realm, W, H, seed)
    img = np.zeros((H * T, W * T, 4), np.float32)
    for y in range(H):
        for x in range(W):
            img[y * T:(y + 1) * T, x * T:(x + 1) * T] = tile(realm, names[y][x])
    return img


def demo_layout(realm, W=32, H=20, seed=7):
    """The demo island as a grid of tile names (rows of strings), shared by map-demo.png and the playable demo."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - W / 2) / (W * 0.42), (yy - H / 2) / (H * 0.42))
    n = np.zeros((H, W))
    for s, amp in ((4, 0.35), (8, 0.15)):
        g = rng.random((H // s + 2, W // s + 2))
        n += amp * g[yy // s, xx // s]
    h = 1 - d + n - 0.25
    names = np.empty((H, W), dtype=object)
    for y in range(H):
        for x in range(W):
            v = h[y, x]
            names[y, x] = "DeepSea" if v < -0.1 else "Water" if v < 0.05 else "Grass" if v < 0.3 else \
                ("Forest" if (x * 7 + y * 3) % 5 < 2 else "Grass" if (x + y) % 4 else "Flowers") if v < 0.5 else "Hills" if v < 0.62 else "Mountain" if v < 0.8 else "SnowPeak"
    if realm == "portal":
        names[(h > 0.05) & (h < 0.25) & (xx > W * 0.65) & (yy > H * 0.55)] = "Desert"
        names[(h > 0.05) & (h < 0.3) & (xx < W * 0.3) & (yy > H * 0.6)] = "Swamp"
    else:
        names[(h > 0.05) & (h < 0.25) & (xx > W * 0.65) & (yy < H * 0.4)] = "Snow"
        names[(h > 0.3) & (h < 0.45) & (xx < W * 0.35) & (yy < H * 0.45)] = "PineForest"
    land = lambda q: q not in ("Water", "DeepSea")                                     # noqa: E731
    for y in range(H):
        for x in range(W):
            if names[y, x] == "Water":
                for side, (dx, dy) in (("CoastN", (0, -1)), ("CoastS", (0, 1)), ("CoastW", (-1, 0)), ("CoastE", (1, 0))):   # strip faces the land
                    yy2, xx2 = y + dy, x + dx
                    if 0 <= yy2 < H and 0 <= xx2 < W and land(names[yy2, xx2]) and not names[yy2, xx2].startswith("Coast"):
                        names[y, x] = side
                        break
    cy = H // 2
    for x in range(W // 4, 3 * W // 4):                                        # a road across the island
        if names[cy, x] in ("Grass", "Flowers", "Forest", "Hills", "Desert", "Snow", "Swamp", "PineForest"):
            names[cy, x] = "Road"
    places = ["Castle", "Town", "Shrine", "Cave", "Tower", "Village", "Ruins"] + (["Graveyard"] if realm == "portal" else ["CrystalShrine", "AirshipPad"])
    spots = [(cy - 1, W // 4 + 1), (cy - 1, 3 * W // 4 - 2), (cy + 3, W // 2 - 1), (cy - 5, W // 2 + 3), (cy + 4, W // 4 + 3), (cy + 2, 3 * W // 4 - 4), (cy - 4, W // 3), (cy + 5, W // 2 + 5), (cy - 3, 2 * W // 3 + 1)]
    for p, (y, x) in zip(places, spots):
        if 0 <= y < H and 0 <= x < W and land(names[y, x]) and not names[y, x].startswith("Coast"):
            names[y, x] = p
    return [[str(names[y, x]) for x in range(W)] for y in range(H)]


def build(out_root, data_root=None):
    rows = []
    for realm in PAL:
        od = os.path.join(out_root, "claude-battle-kit", realm, "worldmap")
        os.makedirs(od, exist_ok=True)
        tiles = []
        for name in list(TERRAIN) + list(ICONS):
            if realm == "portal" and name in ("CrystalField", "CrystalShrine", "AirshipPad"):
                continue
            nf = frames_of(name)
            fr = [tile(realm, name, f) for f in range(nf)]
            strip = np.concatenate(fr, axis=1)
            P.save_png(P.upscale(strip, 4), os.path.join(od, "Tile_%s.png" % name))
            P.save_png(strip, os.path.join(od, "Tile_%s_1x.png" % name))
            tiles.append(P.upscale(fr[0], 4))
            zone = RULES.get(name, (None, None))[0 if realm == "portal" else 1] if name in TERRAIN else None
            rows.append({"realm": realm, "tile": name, "kind": "terrain" if name in TERRAIN else "landmark", "frames": nf,
                         "walkable": name not in ("Mountain", "SnowPeak", "Water", "DeepSea", "Lava") and not name.startswith("Coast"),
                         "ship": name in ("Water", "DeepSea", "Dock") or name.startswith("Coast"), "airship_lands": name in ("Grass", "Flowers", "Desert", "Snow", "AirshipPad", "Hills"),
                         "encounter_zone": zone, "enter": ENTER.get(name), "base": ICONS[name][0] if name in ICONS else None,
                         "png": "engines/unreal/art/claude-battle-kit/%s/worldmap/Tile_%s.png" % (realm, name), "tile_px": 64})
        P.save_png(P.grid_sheet(tiles, 8), os.path.join(od, "sheet-worldmap.png"))
        P.save_png(P.upscale(demo_map(realm), 2), os.path.join(od, "map-demo.png"))
    if data_root:
        d = os.path.join(data_root, "data", "rpg")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "worldmap-tiles.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.worldmap/v1", "source": "tools/blender/rpg_world_map.py", "tile_size": T, "scale": 4,
                       "demo_maps": {r: demo_layout(r) for r in PAL},
                       "note": "encounter_zone keys index data/rpg/<realm>-encounters.json; null = no random battles (roads, bridges, peaks)",
                       "tiles": rows}, f, indent=1)
    return rows


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    data = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, data)
    print("WORLDMAP %d tiles" % len(r))
