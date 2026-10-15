# SPDX-License-Identifier: MIT
"""Dungeons for the two RPG realms: themed tile sets + a seeded multi-floor dungeon generator. Pure numpy.

    python tools/blender/rpg_dungeon.py OUT_ROOT [ROOT_FOR_DATA]

Themes (tile palettes + a hazard): cave (bats' damp rock, water pools), castle (basement flagstones, spikes),
crypt (bone-dust tiles, open graves), tower (brick, broken floor), volcano (basalt, lava), crystal (amethyst
rock, crystal clusters), sea (wet stone, tide pools). Each theme has: Floor, FloorAlt, WallTop, WallFace,
WallTorch (2 frames), StairsDown, StairsUp, Chest, ChestOpen, Door, BossGate, Pillar, Rubble, Hazard (2 frames).

Generator: rooms scattered on a 40 x 28 grid, joined by L corridors (a spanning tree plus a few loops), walls
derived from the floor (a wall with floor below shows its face), stairs up in the first room and down in the
farthest one (breadth-first distance), chests in dead-end rooms with loot by depth, hazards in a few rooms, and on
a boss dungeon's last floor a sealed boss chamber behind a BossGate. Floors roll the realm's encounter zones
(data/rpg/<realm>-encounters.json; deeper floors use the *_deep zone when it exists).

Dungeons: Portal Realm - Old Mine (cave), Sunken Keep (castle), Hollow Crypt (crypt), Wizard's Spire (tower),
Ember Depths (volcano). Prismheart - the nine boss dungeons from data/rpg/prism-bosses.json (Cinder Forge,
Drowned Spire, Windcut Aerie, Rootdeep Hollow, Sunwell Sanctum, Umbral Vault, Gearwright's Folly, Fallen Keep,
The Shattered Heart), each ending at its boss.
Outputs OUT_ROOT/claude-battle-kit/<realm>/dungeons/: Tile_<Theme>_<Name>.png (+_1x), <Dungeon>_F<n>.png,
sheet-tiles.png, sheet-floors.png; data/rpg/dungeons.json: per floor the grid, stairs links, chests + loot,
hazards, encounter zone and step rate, boss.
"""
import json
import math
import os
import random
import sys
from collections import deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402

T = 16
THEMES = {   # floor, floor2, wall top, wall face, face dark, accent, hazard a, hazard b
    "cave":    ("#6c5c48", "#5a4c3a", "#2c241c", "#7a6a54", "#4e4232", "#9c8c70", "#2c5c9c", "#5c90d0"),
    "castle":  ("#7c7c84", "#6a6a72", "#2a2a30", "#8a8a94", "#5a5a62", "#b0b0b8", "#9a9aa4", "#d8d8e0"),
    "crypt":   ("#6c6458", "#5c5448", "#24201c", "#7c7466", "#504a40", "#d8d0b8", "#2c2824", "#4a4238"),
    "tower":   ("#8c6c50", "#7a5c42", "#2c2018", "#a05c3c", "#6c3c28", "#d8b088", "#141010", "#2c2420"),
    "volcano": ("#4c3c38", "#3c302c", "#1c1414", "#5c4844", "#3a2c28", "#e85820", "#e84818", "#ffc040"),
    "crystal": ("#5c5480", "#4c4470", "#1c1830", "#6c64a0", "#443c70", "#c890f8", "#8858d8", "#f0d8ff"),
    "sea":     ("#506c78", "#425a66", "#18242c", "#5c7c8a", "#3a525c", "#98d0d8", "#2c70b0", "#78c0f0"),
}
OUT = {"portal": "#000000", "prism": "#141018"}


def col(h):
    return np.array(P.hexc(h))


def canvas():
    return np.zeros((T, T, 4), np.float32)


def put(a, x, y, c):
    if 0 <= x < T and 0 <= y < T:
        a[y, x, :3] = c
        a[y, x, 3] = 1


def rect(a, x0, y0, w, h, c):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            put(a, x, y, c)


def h2(x, y, s):
    v = math.sin(x * 12.9898 + y * 78.233 + s * 37.7) * 43758.5453
    return v - math.floor(v)


def theme_tiles(theme, realm):
    f1, f2, wt, wf, wd, acc, ha, hb = [col(h) for h in THEMES[theme]]
    out = col(OUT[realm])
    pr = realm == "prism"
    s = list(THEMES).index(theme)

    def floor(alt=False):
        a = canvas()
        rect(a, 0, 0, T, T, f1)
        if theme in ("castle", "tower", "crypt"):                                 # laid stones / bricks
            for y in range(0, T, 8):
                rect(a, 0, y, T, 1, f2)
                rect(a, (y // 8) * 8 % T, y, 1, 8, f2)
        for y in range(T):
            for x in range(T):
                if h2(x, y, s) < (0.12 if alt else 0.06):
                    put(a, x, y, f2)
        if alt:                                                                    # a crack
            for i in range(6):
                put(a, 4 + i, 6 + (i % 3), out if not pr else wd)
        return a

    def wall_top():
        a = canvas()
        rect(a, 0, 0, T, T, wt)
        if pr:
            for y in range(T):
                for x in range(T):
                    if h2(x, y, s + 3) < 0.08:
                        put(a, x, y, np.minimum(1, wt * 1.6))
        return a

    def wall_face(torch=None):
        a = canvas()
        rect(a, 0, 0, T, T, wf)
        if theme in ("castle", "tower", "crypt"):
            for by in range(0, T, 5):
                rect(a, 0, by + 4, T, 1, wd)
                off = 4 if (by // 5) % 2 else 0
                for bx in range(off, T, 8):
                    rect(a, bx, by, 1, 4, wd)
        else:
            for y in range(T):
                for x in range(T):
                    if h2(x, y, s + 7) < 0.18:
                        put(a, x, y, wd)
        rect(a, 0, 0, T, 2, wt)                                                    # the lip of the wall top
        rect(a, 0, T - 1, T, 1, out if not pr else wd * 0.7)
        if theme == "crystal":
            for x0 in (3, 11):
                rect(a, x0, 6, 2, 6, acc)
                put(a, x0, 6, col("#ffffff"))
        if torch is not None:
            rect(a, 7, 8, 2, 5, col("#5a3a28"))
            put(a, 7, 7 - torch, hb)
            put(a, 8, 7, ha)
            put(a, 7, 6 - torch, ha)
            put(a, 8, 5 + torch, hb)
        return a

    def stairs(down):
        a = floor()
        for i in range(4):
            k = (1 - i * 0.18) if down else (0.6 + i * 0.13)
            rect(a, 2, 2 + i * 3, 12, 3, np.clip(f1 * k + (0.08 if not down else 0), 0, 1))
            rect(a, 2, 4 + i * 3, 12, 1, out if not pr else wd)
        if down:
            rect(a, 2, 14, 12, 1, out)
        return a

    def chest(opened):
        a = floor()
        rect(a, 2, 5, 12, 9, out)
        rect(a, 3, 6, 10, 7, col("#a86c30"))
        rect(a, 3, 9, 10, 1, col("#f0c040"))
        if opened:
            rect(a, 3, 6, 10, 3, out)
            rect(a, 2, 2, 12, 3, col("#7c4c20"))
        else:
            rect(a, 3, 6, 10, 2, col("#c88848"))
            put(a, 7, 9, out)
            put(a, 8, 9, out)
        return a

    def door(boss=False):
        a = wall_face()
        rect(a, 3, 3, 10, 13, out)
        rect(a, 4, 4, 8, 12, col("#7c4c20") if not boss else wd)
        if boss:
            rect(a, 4, 7, 8, 1, acc)
            rect(a, 7, 4, 2, 12, acc)
            rect(a, 6, 9, 4, 3, col("#f0c040"))
        else:
            for x in (6, 9):
                rect(a, x, 4, 1, 12, col("#5a3418"))
            put(a, 10, 10, col("#f0c040"))
        return a

    def pillar():
        a = floor()
        rect(a, 4, 1, 8, 14, wf)
        rect(a, 4, 1, 2, 14, np.minimum(1, wf * 1.25) if pr else acc)
        rect(a, 10, 1, 2, 14, wd)
        rect(a, 3, 0, 10, 2, wd)
        rect(a, 3, 14, 10, 2, wd)
        return a

    def rubble():
        a = floor()
        for (x, y, r) in ((4, 9, 2.5), (10, 6, 2), (11, 12, 1.6), (6, 4, 1.2)):
            for yy in range(T):
                for xx in range(T):
                    if (xx - x) ** 2 + (yy - y) ** 2 < r * r:
                        put(a, xx, yy, wf if xx + yy < x + y else wd)
        return a

    def hazard(fr):
        a = canvas()
        rect(a, 0, 0, T, T, ha)
        if theme in ("castle",):                                                   # spikes
            a = floor()
            for gx in range(1, T, 5):
                for gy in range(2, T, 5):
                    h = 3 if fr == 0 else 1
                    for k in range(h):
                        put(a, gx + 1, gy + 2 - k, hb)
                    put(a, gx, gy + 2, wd)
                    put(a, gx + 2, gy + 2, wd)
            return a
        if theme in ("tower", "crypt"):                                            # pit / open grave
            a = floor()
            rect(a, 2, 2, 12, 12, ha)
            rect(a, 2, 2, 12, 2, hb if theme == "tower" else wd)
            return a
        for y in range(T):
            for x in range(T):
                v = math.sin(x * 0.8 + y * 0.5 + fr * 1.7) + math.sin(y * 0.9 - x * 0.4)
                if v > 1.0:
                    put(a, x, y, hb)
        if theme == "crystal":
            for x0, h in ((4, 8), (9, 11), (12, 6)):
                rect(a, x0, T - h, 2, h, acc)
                put(a, x0, T - h, col("#ffffff"))
        return a

    return {
        "Floor": [floor()], "FloorAlt": [floor(True)], "WallTop": [wall_top()], "WallFace": [wall_face()],
        "WallTorch": [wall_face(0), wall_face(1)], "StairsDown": [stairs(True)], "StairsUp": [stairs(False)],
        "Chest": [chest(False)], "ChestOpen": [chest(True)], "Door": [door()], "BossGate": [door(True)],
        "Pillar": [pillar()], "Rubble": [rubble()], "Hazard": [hazard(0), hazard(1)],
    }


WALKABLE = {"Floor", "FloorAlt", "StairsDown", "StairsUp", "Door", "Rubble"}
INTERACT = {"StairsDown": "stairs_down", "StairsUp": "stairs_up", "Chest": "chest", "Door": "door", "BossGate": "boss_gate", "Hazard": "hazard"}
HAZARD_EFFECT = {"cave": "slow (deep water)", "castle": "spikes: 5% max HP", "crypt": "fall to the floor below", "tower": "fall to the floor below",
                 "volcano": "lava: 10% max HP per step", "crystal": "shards: 5% max HP", "sea": "tide pool: slow"}

# ---- generator ----------------------------------------------------------------------------------------------------
W, H = 40, 28


def gen_floor(seed, theme, n_rooms=8, boss=False):
    rng = random.Random(seed)
    grid = [["Void"] * W for _ in range(H)]
    rooms = []
    tries = 0
    while len(rooms) < n_rooms and tries < 400:
        tries += 1
        w, h = rng.randint(4, 8), rng.randint(3, 6)
        if boss and not rooms:
            w, h = 10, 6
        x, y = rng.randint(1, W - w - 2), rng.randint(3, H - h - 2)
        if any(x - 2 < rx + rw and rx - 2 < x + w and y - 3 < ry + rh and ry - 3 < y + h for rx, ry, rw, rh in rooms):
            continue
        rooms.append((x, y, w, h))
    if boss:                                                                       # boss chamber is room 0: move it last
        rooms = rooms[1:] + rooms[:1]
    for x, y, w, h in rooms:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = "FloorAlt" if rng.random() < 0.08 else "Floor"
    centers = [(x + w // 2, y + h // 2) for x, y, w, h in rooms]

    def carve(a, b):
        (x0, y0), (x1, y1) = a, b
        if rng.random() < 0.5:
            pts = [(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)] + [(x1, y) for y in range(min(y0, y1), max(y0, y1) + 1)]
        else:
            pts = [(x0, y) for y in range(min(y0, y1), max(y0, y1) + 1)] + [(x, y1) for x in range(min(x0, x1), max(x0, x1) + 1)]
        for x, y in pts:
            if grid[y][x] == "Void":
                grid[y][x] = "Floor"
    linked = [0]
    order = list(range(1, len(rooms) - (1 if boss else 0)))
    for i in order:                                                                # spanning tree: join each room to its nearest linked room
        j = min(linked, key=lambda k: abs(centers[k][0] - centers[i][0]) + abs(centers[k][1] - centers[i][1]))
        carve(centers[i], centers[j])
        linked.append(i)
    for _ in range(2):                                                             # a couple of loops
        a, b = rng.sample(order + [0], 2)
        carve(centers[a], centers[b])
    gate = None
    if boss:                                                                       # one corridor to a gate on the chamber's top wall... from below
        bx, by, bw, bh = rooms[-1]
        j = min(linked, key=lambda k: abs(centers[k][0] - centers[-1][0]) + abs(centers[k][1] - centers[-1][1]))
        gate = (bx + bw // 2, by + bh)
        if gate[1] >= H - 1:
            gate = (bx + bw // 2, by - 1)
        carve(centers[j], (gate[0], gate[1] + (1 if gate[1] > by else -1)))
    # walls from floor
    floorish = lambda t: t not in ("Void", "WallTop", "WallFace")                  # noqa: E731
    for y in range(H):
        for x in range(W):
            if grid[y][x] != "Void":
                continue
            near = any(0 <= y + dy < H and 0 <= x + dx < W and floorish(grid[y + dy][x + dx]) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            if near:
                grid[y][x] = "WallFace" if y + 1 < H and floorish(grid[y + 1][x]) else "WallTop"
    if gate:
        grid[gate[1]][gate[0]] = "BossGate"
    # torches on some faces
    for y in range(H):
        for x in range(W):
            if grid[y][x] == "WallFace" and (x * 7 + y * 3 + seed) % 9 == 0:
                grid[y][x] = "WallTorch"
    # stairs by BFS distance
    sx, sy = centers[0]
    dist = {(sx, sy): 0}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in dist and grid[ny][nx] in ("Floor", "FloorAlt"):
                dist[(nx, ny)] = dist[(x, y)] + 1
                q.append((nx, ny))
    grid[sy][sx] = "StairsUp"
    room_d = [dist.get(c, -1) for c in centers]
    cand = [i for i in range(1, len(rooms) - (1 if boss else 0)) if room_d[i] >= 0]
    far = max(cand, key=lambda i: room_d[i]) if cand else len(rooms) - 1
    down = centers[far]
    if not boss:
        grid[down[1]][down[0]] = "StairsDown"
    # chests in dead-end-ish rooms (fewest corridor openings), hazards, pillars, rubble
    chests, hazards = [], []
    for i, (x, y, w, h) in enumerate(rooms):
        if i in (0, far) or (boss and i == len(rooms) - 1):
            continue
        r = rng.random()
        if r < 0.45:
            cx, cy = x + rng.randint(0, w - 1), y
            if grid[cy][cx] in ("Floor", "FloorAlt"):
                grid[cy][cx] = "Chest"
                chests.append((cx, cy))
        elif r < 0.7:
            for _ in range(rng.randint(2, 5)):
                hx, hy = x + rng.randint(1, max(1, w - 2)), y + rng.randint(1, max(1, h - 2))
                if grid[hy][hx] in ("Floor", "FloorAlt"):
                    grid[hy][hx] = "Hazard"
                    hazards.append((hx, hy))
        elif r < 0.85 and w >= 6 and h >= 5:
            for px, py in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + h - 2), (x + w - 2, y + h - 2)):
                grid[py][px] = "Pillar"
        else:
            rx, ry = x + rng.randint(0, w - 1), y + rng.randint(0, h - 1)
            if grid[ry][rx] in ("Floor", "FloorAlt"):
                grid[ry][rx] = "Rubble"
    boss_spot = None
    if boss:
        bx, by, bw, bh = rooms[-1]
        boss_spot = (bx + bw // 2, by + bh // 2)
        for px, py in ((bx, by), (bx + bw - 1, by), (bx, by + bh - 1), (bx + bw - 1, by + bh - 1)):
            grid[py][px] = "Pillar"
    return {"grid": grid, "up": (sx, sy), "down": None if boss else down, "chests": chests, "hazards": hazards, "boss_spot": boss_spot, "gate": gate}


def render(realm, theme, g, tiles, boss_sprite=None, spot=None):
    img = np.zeros((H * T, W * T, 4), np.float32)
    void = col("#000000") if realm == "portal" else col("#0a0810")
    for y in range(H):
        for x in range(W):
            t = g[y][x]
            if t == "Void":
                img[y * T:(y + 1) * T, x * T:(x + 1) * T, :3] = void
                img[y * T:(y + 1) * T, x * T:(x + 1) * T, 3] = 1
            else:
                img[y * T:(y + 1) * T, x * T:(x + 1) * T] = tiles[t][0]
    if boss_sprite is not None and spot:
        s = boss_sprite
        sh, sw = s.shape[:2]
        x0 = max(0, spot[0] * T + T // 2 - sw // 2)
        y0 = max(0, spot[1] * T + T // 2 - sh // 2)
        h_, w_ = min(sh, img.shape[0] - y0), min(sw, img.shape[1] - x0)
        img[y0:y0 + h_, x0:x0 + w_] = P.over(img[y0:y0 + h_, x0:x0 + w_], s[:h_, :w_])
    return img


# ---- dungeons -----------------------------------------------------------------------------------------------------
PORTAL = [("Old Mine", "cave", "cave", 3), ("Sunken Keep", "castle", "castle", 3), ("Hollow Crypt", "crypt", "graveyard", 3),
          ("Wizard's Spire", "tower", "tower", 3), ("Ember Depths", "volcano", "volcano", 3)]
PRISM_THEME = {"Cinder Forge": ("volcano", "cave"), "Drowned Spire": ("sea", "sea_cave"), "Windcut Aerie": ("tower", "mountain"),
               "Rootdeep Hollow": ("cave", "cave"), "Sunwell Sanctum": ("castle", "ruins"), "Umbral Vault": ("crypt", "crypt"),
               "Gearwright's Folly": ("castle", "sewer"), "Fallen Keep": ("castle", "castle"), "The Shattered Heart": ("crystal", "crystal_cave")}


def load(root, name):
    try:
        return json.load(open(os.path.join(root, "data", "rpg", name), encoding="utf-8"))
    except OSError:
        return None


def loot_table(root, depth, rng):
    it = load(root, "interiors.json") or {}
    shop = (it.get("interiors") or {}).get("portal", {})
    items = [(s["name"], s["price"]) for k in ("Item", "Weapon", "Armor") for s in (shop.get(k, {}).get("stock") or [])]
    if not items or rng.random() < 0.35:
        return {"gold": int(rng.uniform(20, 60) * (1 + depth))}
    items.sort(key=lambda t: t[1])
    band = items[: max(2, int(len(items) * min(1.0, 0.35 + 0.25 * depth)))]
    n, p = rng.choice(band[-4:])
    return {"item": n, "value": p}


def boss_sprite(root, realm, boss):
    p = os.path.join(root, "claude-battle-sprites", realm, "Battle_Prism_Boss_%s_1x.png" % boss)
    if not os.path.exists(p):
        return None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rpg_battle_ui as UI
    s = UI.load_png_1x(p)
    if s is not None and s.shape[0] > 40:
        k = -(-s.shape[0] // 36)
        s = s[::k, ::k]
    return s


REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def build(out_root, data_root=None):
    root = data_root or REPO                                                       # bosses / encounters / shop stock live in the repo
    enc = {r: (load(root, "%s-encounters.json" % r) or {}).get("zones", {}) for r in ("portal", "prism")}
    bosses = (load(root, "prism-bosses.json") or {}).get("bosses", [])
    data = {}
    for realm in ("portal", "prism"):
        od = os.path.join(out_root, "claude-battle-kit", realm, "dungeons")
        os.makedirs(od, exist_ok=True)
        tilesets = {}
        sheet = []
        for theme in THEMES:
            ts = theme_tiles(theme, realm)
            tilesets[theme] = ts
            for name, fr in ts.items():
                strip = np.concatenate(fr, axis=1)
                P.save_png(P.upscale(strip, 4), os.path.join(od, "Tile_%s_%s.png" % (theme.title(), name)))
                P.save_png(strip, os.path.join(od, "Tile_%s_%s_1x.png" % (theme.title(), name)))
                sheet.append(P.upscale(fr[0], 2))
        P.save_png(P.grid_sheet(sheet, 14), os.path.join(od, "sheet-tiles.png"))
        if realm == "portal":
            plan = [(n, th, z, fl, None) for n, th, z, fl in PORTAL]
        else:
            plan = [(b["dungeon"], PRISM_THEME[b["dungeon"]][0], PRISM_THEME[b["dungeon"]][1], 3 if b["level"] < 30 else 4, b) for b in bosses]
        data[realm] = []
        thumbs = []
        for di, (dname, theme, zone, nfl, boss) in enumerate(plan):
            rng = random.Random(di * 977 + (0 if realm == "portal" else 50000))
            floors = []
            for fi in range(nfl):
                last = fi == nfl - 1
                fl = gen_floor(rng.randint(0, 10 ** 9), theme, n_rooms=7 + fi, boss=bool(boss) and last)
                zkey = zone if fi == 0 or (zone + "_deep") not in enc[realm] else zone + "_deep"
                if zkey not in enc[realm]:
                    zkey = next((k for k in (zone, "cave") if k in enc[realm]), None)
                z = enc[realm].get(zkey, {}) if zkey else {}
                bs = boss_sprite(out_root, realm, boss["name"]) if (boss and last) else None
                img = render(realm, theme, fl["grid"], tilesets[theme], bs, fl["boss_spot"])
                fn = "%s_F%d" % ("".join(ch for ch in dname.title() if ch.isalnum()), fi + 1)
                P.save_png(img, os.path.join(od, fn + ".png"))
                if fi == nfl - 1:
                    thumbs.append(img[::2, ::2])
                floors.append({
                    "floor": fi + 1, "png": "engines/unreal/art/claude-battle-kit/%s/dungeons/%s.png" % (realm, fn), "grid": fl["grid"],
                    "stairs_up": {"x": fl["up"][0], "y": fl["up"][1], "to": "floor %d" % fi if fi else "overworld"},
                    "stairs_down": {"x": fl["down"][0], "y": fl["down"][1], "to": "floor %d" % (fi + 2)} if fl["down"] else None,
                    "chests": [dict({"x": x, "y": y}, **loot_table(root, fi + (2 if boss else 0), rng)) for x, y in fl["chests"]],
                    "hazards": {"tiles": [{"x": x, "y": y} for x, y in fl["hazards"]], "effect": HAZARD_EFFECT[theme]},
                    "encounters": {"zone": zkey, "steps_mean": z.get("steps_mean"), "level_band": z.get("level_band")},
                    "boss": {"name": boss["name"], "x": fl["boss_spot"][0], "y": fl["boss_spot"][1], "gate": {"x": fl["gate"][0], "y": fl["gate"][1]},
                             "data": "data/rpg/prism-bosses.json"} if (boss and last) else None,
                })
            data[realm].append({"name": dname, "theme": theme, "floors": floors, "boss": boss["name"] if boss else None,
                                "shard": boss.get("shard") if boss else None, "level": boss.get("level") if boss else None})
        if thumbs:
            P.save_png(P.grid_sheet(thumbs, 3), os.path.join(od, "sheet-floors.png"))
    if data_root:
        d = os.path.join(data_root, "data", "rpg")
        with open(os.path.join(d, "dungeons.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.dungeons/v1", "source": "tools/blender/rpg_dungeon.py", "tile_size": T, "map": [W, H],
                       "walkable": sorted(WALKABLE), "interact": INTERACT, "dungeons": data}, f, indent=1)
    return data


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    dr = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, dr)
    print("DUNGEONS", {k: [(d["name"], len(d["floors"])) for d in v] for k, v in r.items()})
