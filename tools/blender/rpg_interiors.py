# SPDX-License-Identifier: MIT
"""Building interiors for the two RPG realms, so every town door leads somewhere.

    python tools/blender/rpg_interiors.py OUT_ROOT [ROOT_FOR_DATA]

Builds on rpg_town.py (same palettes, tiles and villagers) and adds the interior pieces: void, pillar, throne,
fireplace (2 frames), wall torch (2 frames), banner, weapon rack, armour stand, stool, bookcase, exit mat, plus a
crowned ruler sprite. Five interiors per realm — Item Shop, Weapon Shop, Armour Shop (Portal) / Magic Shop
(Prismheart), Inn, Castle Hall — each a tile grid with its keeper and visitors.

Outputs OUT_ROOT/claude-battle-kit/<realm>/interiors/: Tile_<Name>.png (+_1x), NPC_Ruler.png, Interior_<Name>.png
(rendered x2) and sheet-interiors.png; data/rpg/interiors.json: per interior the grid, NPCs, spawn and exit tiles,
the town door that opens it (read from the demo town in data/rpg/town-tiles.json) and the shop stock (spells from
data/rpg/spells.json for the magic shop; original item, weapon and armour lists with prices and stats).
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402
import rpg_town as RT  # noqa: E402

T = RT.T
C, put, rect, fill, shade, canvas = RT.C, RT.put, RT.rect, RT.fill, RT.shade, RT.canvas


def t_void(r, f=0):
    a = canvas()
    fill(a, np.array([0.0, 0.0, 0.0]) if r == "portal" else np.array([0.06, 0.05, 0.09]))
    return a


def t_pillar(r, f=0):
    a = RT.t_stone(r)
    rect(a, 3, 0, 10, 2, C(r, "st2"))
    rect(a, 4, 2, 8, 12, C(r, "st1"))
    rect(a, 4, 2, 2, 12, shade(r, C(r, "st1"), 1.15) if r == "prism" else C(r, "pw1"))
    rect(a, 10, 2, 2, 12, C(r, "st2"))
    rect(a, 3, 14, 10, 2, C(r, "st2"))
    return a


def t_throne(r, f=0):
    a = RT.t_carpet(r)
    rect(a, 3, 0, 10, 10, C(r, "gold"))
    rect(a, 4, 1, 8, 8, C(r, "cp1"))
    rect(a, 2, 8, 12, 6, C(r, "gold"))
    rect(a, 3, 9, 10, 3, C(r, "cp1"))
    put(a, 7, 0, C(r, "c2"))
    put(a, 8, 0, C(r, "c2"))
    return a


def t_fireplace(r, f=0):
    a = RT.t_wall(r, kind="brick")
    rect(a, 2, 4, 12, 12, C(r, "st2"))
    rect(a, 4, 7, 8, 9, C(r, "out"))
    for k in range(8):
        h = 3 + ((k * 3 + f * 2) % 4)
        for y in range(h):
            put(a, 4 + k, 15 - y, C(r, "l2") if y < h - 2 else C(r, "l1"))
    rect(a, 1, 3, 14, 1, C(r, "wd2"))
    return a


def t_torch(r, f=0):
    a = RT.t_wall(r, kind="brick")
    rect(a, 7, 7, 2, 6, C(r, "wd2"))
    rect(a, 6, 6, 4, 1, C(r, "st2"))
    put(a, 7, 5 - f, C(r, "l2"))
    put(a, 8, 5, C(r, "l1"))
    put(a, 7, 4 - f, C(r, "l1"))
    put(a, 8, 3 + f, C(r, "l2"))
    return a


def t_banner(r, f=0):
    a = RT.t_wall(r, kind="brick")
    rect(a, 4, 1, 8, 1, C(r, "gold"))
    rect(a, 5, 2, 6, 11, C(r, "c1"))
    rect(a, 5, 13, 2, 1, C(r, "c1"))
    rect(a, 9, 13, 2, 1, C(r, "c1"))
    rect(a, 7, 5, 2, 5, C(r, "gold"))
    rect(a, 6, 6, 4, 1, C(r, "gold"))
    return a


def t_rack(r, f=0):
    a = RT.t_wall(r, kind="plaster")
    rect(a, 1, 3, 14, 1, C(r, "wd2"))
    rect(a, 1, 12, 14, 1, C(r, "wd2"))
    for i, x in enumerate((3, 7, 11)):
        rect(a, x, 2, 1, 11, C(r, "st1"))                                   # blades
        rect(a, x - 1, 10, 3, 1, C(r, "gold"))                              # guards
        rect(a, x, 11, 1, 3, C(r, "wd2"))                                   # grips
        if r == "prism":
            put(a, x, 2, np.array([1, 1, 1]))
    return a


def t_stand(r, f=0):
    a = RT.t_wood(r)
    rect(a, 7, 11, 2, 4, C(r, "wd2"))
    rect(a, 4, 14, 8, 1, C(r, "wd2"))
    rect(a, 4, 4, 8, 8, C(r, "c4"))                                         # chest plate
    rect(a, 3, 4, 10, 2, C(r, "c4"))
    rect(a, 6, 1, 4, 3, C(r, "c4"))                                         # helm
    rect(a, 7, 2, 2, 1, C(r, "out"))
    rect(a, 5, 6, 6, 1, C(r, "st2"))
    return a


def t_stool(r, f=0):
    a = RT.t_wood(r)
    for y in range(5, 10):
        rect(a, 5, y, 6, 1, C(r, "wd2") if y in (5, 9) else shade(r, C(r, "wd1"), 1.1))
    rect(a, 5, 10, 1, 4, C(r, "wd2"))
    rect(a, 10, 10, 1, 4, C(r, "wd2"))
    return a


def t_books(r, f=0):
    a = RT.t_wall(r, kind="plaster")
    rect(a, 1, 1, 14, 14, C(r, "wd2"))
    for row in (2, 7, 11):
        for i in range(12):
            c = ("c1", "c2", "c3", "c5", "gold", "c6")[(i * 7 + row) % 6]
            rect(a, 2 + i, row, 1, 3 if row != 11 else 3, C(r, c))
        rect(a, 2, row + 3, 12, 1, C(r, "wd1"))
    return a


def t_exit(r, f=0):
    a = RT.t_wood(r)
    rect(a, 2, 4, 12, 9, C(r, "cp1"))
    rect(a, 3, 5, 10, 7, C(r, "cp2"))
    for i in range(4):                                                      # arrow pointing out (down)
        rect(a, 8 - i, 7 + i, 2 * i if i else 1, 1, C(r, "cp1"))
    return a


ITILES = {
    "Void": (t_void, 1, False, None), "Pillar": (t_pillar, 1, False, None), "Throne": (t_throne, 1, False, "talk:ruler"),
    "Fireplace": (t_fireplace, 2, False, None), "Torch": (t_torch, 2, False, None), "Banner": (t_banner, 1, False, None),
    "WeaponRack": (t_rack, 1, False, None), "ArmorStand": (t_stand, 1, False, "search"), "Stool": (t_stool, 1, True, None),
    "Bookcase": (t_books, 1, False, "read"), "ExitMat": (t_exit, 1, True, "exit"),
}
ALL = dict(RT.TILES)
ALL.update(ITILES)


def tile(realm, name, f=0):
    return ALL[name][0](realm, f)


def ruler(realm, d, f):
    a = RT.npc(realm, "Elder", d, f)
    gold, red = C(realm, "gold"), C(realm, "c2")
    for x in range(4, 12):                                                  # crown
        put(a, x, 1, gold)
    for x in (4, 7, 8, 11):
        put(a, x, 0, gold)
    put(a, 7, 1, red)
    if d != "down":                                                         # cape
        rect(a, 5, 8, 6, 6, red)
    else:
        rect(a, 4, 8, 1, 6, red)
        rect(a, 11, 8, 1, 6, red)
    return a


# ---- stock (original names; prices in gold, stats for the battle system) ------------------------------------------
ITEMS = [("Herb Tonic", 8, "heal 30 HP"), ("Clear Draught", 30, "restore 20 MP"), ("Antidote Leaf", 6, "cure poison"),
         ("Wake Bell", 12, "cure sleep"), ("Feather of Waking", 150, "revive one ally at 1/4 HP"), ("Smoke Pouch", 20, "escape most battles"),
         ("Camp Tent", 120, "rest the party on the world map")]
WEAPONS = [("Copper Blade", 60, 6), ("Oak Staff", 40, 3), ("Hunter Bow", 120, 9), ("Iron Axe", 220, 14), ("Steel Saber", 480, 20),
           ("Silver Lance", 900, 27)]
ARMOR = [("Padded Vest", 45, 3), ("Ring Mail", 180, 8), ("Iron Helm", 120, 4), ("Kite Shield", 150, 5), ("Scale Coat", 520, 14),
         ("Tower Shield", 400, 9)]


def magic_stock(root, realm):
    try:
        sp = json.load(open(os.path.join(root, "data", "rpg", "spells.json"), encoding="utf-8"))["spells"]
    except OSError:
        return []
    return [{"name": s["name"], "price": s["mp"] * 25 * s["tier"], "spell": s["name"], "element": s["element"], "tier": s["tier"]}
            for s in sp if s["realm"] == realm and s["tier"] <= 2]


# ---- the interiors ----------------------------------------------------------------------------------------------

def room(w, h, floor="WoodFloor", wall="WallPlaster"):
    g = [["Void"] * w for _ in range(h)]
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            g[y][x] = floor
    for x in range(1, w - 1):
        g[1][x] = wall
        g[2][x] = wall
    ex = w // 2
    g[h - 2][ex] = "ExitMat"
    return g, (ex, h - 2)


def shop(kind, realm):
    if kind == "Inn":
        g, ex = room(14, 11, "WoodFloor", "WallPlaster")
        for x in range(1, 13):
            g[2][x] = "WallWindow" if x % 3 == 0 else "WallPlaster"
        g[2][2] = "Fireplace"
        for x in range(1, 6):
            g[5][x] = "Counter"
        for x in range(8, 13, 2):
            g[3][x] = "Bed"
            g[4][x] = "Bed"
        g[3][12] = "Stairs"
        for (x, y) in ((3, 7), (9, 7)):
            g[y][x] = "Table"
            g[y][x - 1] = "Stool"
            g[y][x + 1] = "Stool"
        g[8][1] = "Barrel"
        g[8][12] = "Pot"
        npcs = [("Innkeeper", 3, 4, "down"), ("Sailor", 9, 8, "up"), ("Farmer", 2, 8, "right")]
        return g, ex, npcs, {"rest_price": 10, "service": "inn"}
    if kind == "Castle":
        g, ex = room(15, 13, "StoneFloor", "WallBrick")
        for x in range(1, 14):
            g[2][x] = "Banner" if x in (3, 11) else ("Torch" if x in (5, 9) else "WallBrick")
        for y in range(3, ex[1]):                                          # runner stops at the exit mat
            g[y][7] = "Carpet"
        g[3][7] = "Throne"
        for y in (5, 8):
            for x in (3, 11):
                g[y][x] = "Pillar"
        g[3][6] = "Chest"
        g[3][8] = "Chest"
        npcs = [("Ruler", 7, 4, "down"), ("Guard", 5, 6, "right"), ("Guard", 9, 6, "left"), ("Guard", 6, 10, "up"), ("Guard", 8, 10, "up"),
                ("Mage", 10, 4, "down")]
        return g, ex, npcs, {"service": "audience"}
    g, ex = room(11, 9, "WoodFloor", "WallPlaster" if kind in ("Item", "Magic") else "WallBrick")
    back = {"Item": "Shelf", "Weapon": "WeaponRack", "Armor": "WeaponRack", "Magic": "Bookcase"}[kind]
    for x in range(1, 10):
        g[2][x] = back if x % 2 else g[2][x]
    for x in range(2, 9):
        g[4][x] = "Counter"
    if kind == "Armor":
        g[3][1] = g[3][9] = "ArmorStand"
    if kind == "Magic":
        g[3][1] = "Pot"
        g[3][9] = "Pot"
        for y in range(5, 8):
            g[y][5] = "Carpet"
    else:
        g[6][1] = "Barrel"
        g[6][9] = "Crate"
    keeper = {"Item": "Merchant", "Weapon": "Guard", "Armor": "Guard", "Magic": "Mage"}[kind]
    npcs = [(keeper, 5, 3, "down"), ("Child" if kind == "Item" else "Farmer", 3, 6, "up")]
    if kind == "Item":
        stock = [{"name": n, "price": p, "effect": e} for n, p, e in ITEMS]
    elif kind == "Weapon":
        stock = [{"name": n, "price": p, "attack": a} for n, p, a in WEAPONS]
    elif kind == "Armor":
        stock = [{"name": n, "price": p, "defence": d} for n, p, d in ARMOR]
    else:
        stock = None                                                        # filled from spells.json in build()
    return g, ex, npcs, {"service": "shop:" + kind.lower(), "stock": stock}


def render(realm, g, npcs):
    H, W = len(g), len(g[0])
    img = np.zeros((H * T, W * T, 4), np.float32)
    for y in range(H):
        for x in range(W):
            img[y * T:(y + 1) * T, x * T:(x + 1) * T] = tile(realm, g[y][x])
    for kind, x, y, d in npcs:
        s = ruler(realm, d, 0) if kind == "Ruler" else RT.npc(realm, kind, d, 0)
        img[y * T:(y + 1) * T, x * T:(x + 1) * T] = P.over(img[y * T:(y + 1) * T, x * T:(x + 1) * T], s)
    return img


def town_doors(realm):
    """(x, y, sign) of every door in the demo town that has a shop sign beside it."""
    _, grid, _ = RT.demo_town(realm)
    out = []
    for y, row in enumerate(grid):
        for x, n in enumerate(row):
            if n in ("WallDoor", "BrickDoor"):
                for dx in (-1, 1):
                    s = row[x + dx] if 0 <= x + dx < len(row) else ""
                    if s.startswith("Sign"):
                        out.append((x, y, s[4:]))
    return out


def build(out_root, data_root=None):
    rows, interiors = [], {}
    for realm in ("portal", "prism"):
        od = os.path.join(out_root, "claude-battle-kit", realm, "interiors")
        os.makedirs(od, exist_ok=True)
        for name, (fn, nf, walk, act) in ITILES.items():
            fr = [tile(realm, name, f) for f in range(nf)]
            strip = np.concatenate(fr, axis=1)
            P.save_png(P.upscale(strip, 4), os.path.join(od, "Tile_%s.png" % name))
            P.save_png(strip, os.path.join(od, "Tile_%s_1x.png" % name))
            rows.append({"realm": realm, "tile": name, "frames": nf, "walkable": walk, "interact": act})
        rs = np.concatenate([ruler(realm, d, f) for d in ("down", "up", "left", "right") for f in (0, 1)], axis=1)
        P.save_png(P.upscale(rs, 4), os.path.join(od, "NPC_Ruler.png"))
        P.save_png(rs, os.path.join(od, "NPC_Ruler_1x.png"))
        doors = {sign: (x, y) for x, y, sign in town_doors(realm)}
        kinds = ["Item", "Weapon", "Armor" if realm == "portal" else "Magic", "Inn", "Castle"]
        thumbs = []
        interiors[realm] = {}
        for k in kinds:
            g, ex, npcs, meta = shop(k, realm)
            if k == "Magic":
                meta["stock"] = magic_stock(data_root or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), realm)
            img = render(realm, g, npcs)
            P.save_png(P.upscale(img, 2), os.path.join(od, "Interior_%s.png" % k))
            thumbs.append(P.upscale(img, 1))
            door = doors.get(k)
            interiors[realm][k] = dict(meta, grid=g, npcs=[{"type": n, "x": x, "y": y, "facing": d} for n, x, y, d in npcs],
                                       spawn={"x": ex[0], "y": ex[1] - 1, "facing": "up"}, exit={"x": ex[0], "y": ex[1]},
                                       opened_by={"map": "demo_town", "door": {"x": door[0], "y": door[1]}} if door else
                                       ({"map": "overworld", "landmark": "Castle"} if k == "Castle" else None),
                                       render="engines/unreal/art/claude-battle-kit/%s/interiors/Interior_%s.png" % (realm, k))
        P.save_png(P.grid_sheet(thumbs, 3), os.path.join(od, "sheet-interiors.png"))
    if data_root:
        d = os.path.join(data_root, "data", "rpg")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "interiors.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.interiors/v1", "source": "tools/blender/rpg_interiors.py", "tile_size": T,
                       "tiles": rows, "note": "town tiles come from town-tiles.json; spawn is one tile inside the exit mat",
                       "interiors": interiors}, f, indent=1)
    return interiors


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    data = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, data)
    print("INTERIORS", {k: list(v) for k, v in r.items()})
