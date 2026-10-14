# SPDX-License-Identifier: MIT
"""Team Claude's hero island for the Blender contest (Richey 13:25: "make the very best single best island you can ...
don't forget new oceans, rivers, streams and ponds that magically flow through the air through our islands and clouds").

Skyfall: a big terraced main island with a hilltop lake, a meandering stream that runs across the island under a plank
bridge and pours off the rim as a wide waterfall; above and behind it a small source islet whose spring feeds a SKY
RIVER - a ribbon of water that arcs through open air (through a cloud) into the lake; below, a floating ocean basin
that catches the waterfall and spills a thin fall of its own. Big round-canopy trees in groves, blossom trees, a stone
cottage with a chimney and smoke, lanterns on the path, a dock with a boat on the lake, a fenced garden, mushrooms,
crystals under both rocks, clouds. 1 voxel = 1 m; pivot = main plateau top centre (z=0).

    import hero_island as H
    H.plan(seed)                 -> {layer: [(x, y, z, colour)]}  (pure Python; the planner tests run without Blender)
    H.build(seed, out_fbx)       -> FBX with body / water / clouds meshes + UCX boxes (Blender)
"""
import math
import os
import random

import island_chemistry as CH
import voxel_island as V

PAL = dict(V.PAL)
PAL.update({
    "stone": (0.58, 0.58, 0.62), "stone2": (0.50, 0.50, 0.55), "smoke": (0.75, 0.75, 0.78), "smoke2": (0.85, 0.85, 0.88),
    "deepwater": (0.20, 0.42, 0.80), "sea": (0.22, 0.55, 0.85), "sea2": (0.30, 0.65, 0.90), "moss": (0.30, 0.50, 0.25),
    "bridge": (0.55, 0.40, 0.25), "leaf3": (0.20, 0.48, 0.20), "flower_p": (0.85, 0.45, 0.80), "flower_b": (0.35, 0.45, 0.95),
    # ADR-050 lands: ores by depth, the Heartstone core, starmetal under a meteor crater
    "coal": (0.12, 0.12, 0.13), "copper": (0.78, 0.45, 0.25), "iron": (0.70, 0.62, 0.55), "gold": (0.95, 0.80, 0.25),
    "starmetal": (0.55, 0.85, 1.00), "heartstone": (1.00, 0.35, 0.45), "heartstone2": (1.00, 0.60, 0.65),
    "deepstone": (0.22, 0.22, 0.26), "crater": (0.30, 0.26, 0.24), "cave": (0.08, 0.08, 0.10),
    # town + farm + chemistry (ADR-054 starter town, RingInfusion herbs, Kennel tonic trough)
    "thatch": (0.80, 0.68, 0.35), "board": (0.45, 0.32, 0.20), "paper": (0.96, 0.94, 0.88), "awning": (0.85, 0.25, 0.25),
    "awning2": (0.95, 0.95, 0.95), "anvil": (0.25, 0.25, 0.28), "forge": (1.00, 0.55, 0.15), "wheat": (0.90, 0.78, 0.35),
    "carrot": (0.95, 0.50, 0.15), "soil": (0.35, 0.24, 0.15), "wool": (0.95, 0.95, 0.92), "hen": (0.90, 0.85, 0.75),
    "comb": (0.90, 0.20, 0.20), "rail": (0.50, 0.50, 0.55), "cart": (0.40, 0.30, 0.22), "wheel": (0.60, 0.45, 0.28),
    "sailcloth": (0.92, 0.90, 0.82), "hull": (0.42, 0.28, 0.16), "trough": (0.50, 0.38, 0.24), "brew": (0.55, 0.85, 0.45),
    "dawnleaf": (0.95, 0.80, 0.40), "rillprism": (0.55, 0.80, 0.95), "cinderbud": (0.95, 0.40, 0.20),
    "stillmoss": (0.30, 0.55, 0.35), "stridefern": (0.45, 0.75, 0.30), "clearbell": (0.85, 0.90, 1.00),
})
HERBS = ("dawnleaf", "rillprism", "cinderbud", "stillmoss", "stridefern", "clearbell")   # docs/mechanics/RingInfusion.md
LAYERS = ("island", "water", "trees", "cottage", "props", "flowers", "crystals", "clouds")
GROUPS = {"body": ("island", "trees", "cottage", "props", "flowers", "crystals"), "water": ("water",), "clouds": ("clouds",)}


def _harm(rng, n=3, lo=0.04, hi=0.10):
    return [(rng.uniform(lo, hi), rng.randint(2, 5), rng.uniform(0, 6.28)) for _ in range(n)]


def _radius(size, harm):
    def r(ang):
        return size * (1.0 + sum(a * math.sin(k * ang + p) for a, k, p in harm))
    return r


def _disc(size, harm, cx=0, cy=0):
    rad = _radius(size, harm)
    top = {}
    for x in range(cx - size - 8, cx + size + 9):
        for y in range(cy - size - 8, cy + size + 9):
            ang = math.atan2(y - cy + 0.5, x - cx + 0.5)
            d = math.hypot(x - cx + 0.5, y - cy + 0.5)
            if d <= rad(ang):
                top[(x, y)] = (d, rad(ang) - d)     # distance from centre, distance to the edge
    return top


def _patch(x, y, z, salt, p=0.7, b=4):
    h = ((x // b) * 73856093 ^ (y // b) * 19349663 ^ (z // b) * 83492791 ^ salt) & 0xFFFF
    return h < p * 0xFFFF


def _body(vox, top, ztop_of, thick, salt, cx=0, cy=0, sand_w=2.0, terrace=None):
    """Rock mass under a plateau: sand rim, grass top, dirt band, rock to a jagged keel; `terrace` = (edge_dist,
    drop) carves a lower ring `drop` m below the plateau within edge_dist of the rim."""
    for (x, y), (d, edge) in top.items():
        zt = ztop_of(x, y)
        rim = edge < sand_w
        if terrace and edge < terrace[0]:
            zt -= terrace[1]
        if rim:
            zt -= 1
        colour = "sand" if rim else ("grass" if _patch(x, y, zt, salt) else "grass2")
        vox["island"].append((x, y, zt, colour))
        for z in range(zt - 1, zt - 5, -1):
            vox["island"].append((x, y, z, "dirt" if _patch(x, y, z, salt) else "dirt2"))
        frac = d / max(d + edge, 1.0)
        jag = (((x // 3) * 2654435761 ^ (y // 3) * 40503 ^ salt) & 7) // 2 - 1
        depth = int(thick * (1.0 - frac ** 3.2) ** 0.7 + jag)      # a fat keel like the reference, thin only at the rim
        for z in range(zt - 5, zt - 5 - max(depth, 2), -1):
            vox["island"].append((x, y, z, "rock" if _patch(x, y, z, salt, 0.6) else "rock2"))


def _sphere(vox, layer, cx, cy, cz, rad, pick):
    for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                if dx * dx + dy * dy + dz * dz <= rad * rad + 1:
                    vox[layer].append((cx + dx, cy + dy, cz + dz, pick()))


# ---- island types (Richey 13:25 "five more islands of different types") -------------------------------------
# each type is a palette remap + a few structural switches read inside plan()
KINDS = {
    "meadow": {},
    "volcano": {"pal": {"grass": (0.26, 0.22, 0.22), "grass2": (0.33, 0.27, 0.25), "dirt": (0.18, 0.13, 0.12), "dirt2": (0.26, 0.17, 0.14),
                        "rock": (0.16, 0.14, 0.16), "rock2": (0.24, 0.20, 0.22), "sand": (0.32, 0.28, 0.26), "water": (1.00, 0.45, 0.10),
                        "sea": (1.00, 0.40, 0.08), "sea2": (1.00, 0.62, 0.18), "deepwater": (0.85, 0.25, 0.05), "foam": (1.00, 0.85, 0.35),
                        "leaf": (0.30, 0.28, 0.22), "leaf2": (0.42, 0.36, 0.24), "leaf3": (0.22, 0.20, 0.18), "blossom": (0.95, 0.35, 0.10),
                        "blossom2": (1.00, 0.60, 0.15), "cloud": (0.45, 0.42, 0.45), "roof": (0.28, 0.24, 0.26), "wall": (0.40, 0.36, 0.36)},
                "tree": "dead", "lake": "lava", "extra": "obsidian_spires"},
    "frost": {"pal": {"grass": (0.93, 0.95, 0.98), "grass2": (0.86, 0.90, 0.95), "dirt": (0.55, 0.58, 0.65), "dirt2": (0.62, 0.66, 0.72),
                      "sand": (0.82, 0.86, 0.92), "water": (0.72, 0.88, 0.98), "sea": (0.60, 0.80, 0.95), "sea2": (0.80, 0.92, 1.00),
                      "leaf": (0.18, 0.40, 0.30), "leaf2": (0.80, 0.88, 0.92), "leaf3": (0.14, 0.33, 0.26), "blossom": (0.90, 0.92, 0.96),
                      "blossom2": (0.72, 0.82, 0.92), "roof": (0.30, 0.36, 0.52), "thatch": (0.90, 0.92, 0.96)},
              "tree": "pine", "lake": "ice", "extra": "hot_spring"},
    "mesa": {"pal": {"grass": (0.80, 0.62, 0.35), "grass2": (0.86, 0.70, 0.40), "dirt": (0.72, 0.40, 0.22), "dirt2": (0.80, 0.48, 0.26),
                     "rock": (0.62, 0.32, 0.20), "rock2": (0.70, 0.40, 0.24), "sand": (0.92, 0.82, 0.58), "leaf": (0.30, 0.55, 0.25),
                     "leaf2": (0.40, 0.62, 0.28), "leaf3": (0.25, 0.48, 0.22), "blossom": (0.95, 0.45, 0.55), "blossom2": (0.98, 0.65, 0.30),
                     "roof": (0.75, 0.55, 0.35), "wall": (0.90, 0.80, 0.60)},
             "tree": "palm", "lake": "oasis", "extra": "cacti"},
    "mire": {"pal": {"grass": (0.25, 0.38, 0.18), "grass2": (0.32, 0.45, 0.20), "dirt": (0.25, 0.20, 0.12), "dirt2": (0.32, 0.26, 0.14),
                     "water": (0.25, 0.42, 0.32), "sea": (0.22, 0.40, 0.30), "sea2": (0.30, 0.50, 0.36), "deepwater": (0.15, 0.30, 0.22),
                     "leaf": (0.18, 0.42, 0.16), "leaf2": (0.26, 0.52, 0.18), "leaf3": (0.14, 0.34, 0.14), "cloud": (0.78, 0.80, 0.76),
                     "sand": (0.45, 0.42, 0.28), "roof": (0.35, 0.40, 0.25), "wall": (0.50, 0.45, 0.32)},
             "tree": "mangrove", "lake": "bog", "extra": "lilies"},
    "crystal": {"pal": {"grass": (0.55, 0.45, 0.75), "grass2": (0.62, 0.52, 0.82), "dirt": (0.30, 0.22, 0.40), "dirt2": (0.38, 0.28, 0.48),
                        "rock": (0.28, 0.24, 0.40), "rock2": (0.36, 0.30, 0.50), "sand": (0.80, 0.75, 0.92), "water": (0.55, 0.85, 1.00),
                        "sea": (0.45, 0.80, 1.00), "sea2": (0.70, 0.92, 1.00), "leaf": (0.70, 0.55, 0.95), "leaf2": (0.85, 0.70, 1.00),
                        "leaf3": (0.55, 0.40, 0.85), "blossom": (0.55, 0.95, 0.95), "blossom2": (0.80, 1.00, 1.00), "cloud": (0.90, 0.88, 1.00),
                        "roof": (0.45, 0.30, 0.70), "wall": (0.85, 0.82, 0.95)},
                "tree": "round", "lake": "glow", "extra": "spires"},
}
KIND_NAMES = tuple(KINDS)


def palette_for(kind):
    pal = dict(PAL)
    pal.update(KINDS.get(kind, {}).get("pal", {}))
    return pal


FRUIT = {"apple": (0.90, 0.20, 0.20), "cherry": (0.75, 0.10, 0.25), "plum": (0.45, 0.20, 0.55), "orange": (1.00, 0.60, 0.15),
         "pear": (0.75, 0.85, 0.35), "lemon": (0.98, 0.92, 0.30)}
PAL.update({"fruit_" + k: v for k, v in FRUIT.items()})


def plan(seed=1, realm="WORLD-ZERO", kind="meadow"):
    K = KINDS.get(kind, KINDS["meadow"])
    tree_shape = K.get("tree", "round")
    rng = random.Random(seed * 7919 + 11)
    salt = rng.randint(0, 1 << 20)
    vox = {k: [] for k in LAYERS}
    chem = CH.profile(seed, realm)          # the seed's chemistry decides herbs, fruit, ores, grade
    herbs_here = chem["flora"]["herbs"]
    orchard = list(chem["flora"]["orchard"])
    legendary = chem["geology"]["starmetal_crater"]

    # ---- main island: size 60, a hill with the lake on top -----------------------------------------------
    size, thick = 60, 38
    harm = _harm(rng)
    top = _disc(size, harm)
    hx, hy = -8, 6                       # hill centre; the lake sits in the hill
    hr = 34.0

    def hill(x, y):
        d = math.hypot(x - hx, y - hy)
        return int(round(7.0 * max(0.0, 1.0 - (d / hr) ** 2))) if d < hr else 0

    lake = {(x, y) for (x, y) in top if math.hypot(x - hx, y - hy) <= 11.5}
    lake_z = hill(hx, hy) - 2            # water surface two below the hill crest
    # stream: from the lake rim toward the far rim with a gentle meander, 2 wide
    sang = rng.uniform(0, 6.28)
    stream = []
    sx, sy = hx + 11.5 * math.cos(sang), hy + 11.5 * math.sin(sang)
    dirx, diry = math.cos(sang), math.sin(sang)
    i = 0
    while (int(sx), int(sy)) in top and i < 200:
        wob = math.sin(i / 6.0) * 0.9
        px, py = sx + (-diry) * wob, sy + dirx * wob
        stream.append((int(round(px)), int(round(py))))
        sx += dirx
        sy += diry
        i += 1
    stream_cells = set()
    for (x, y) in stream:
        for dx in (0, 1):
            for dy in (0, 1):
                stream_cells.add((x + dx, y + dy))
    fall_x, fall_y = stream[-1] if stream else (size, 0)

    def ztop_main(x, y):
        h = hill(x, y)
        if (x, y) in lake:
            return lake_z - 1
        if (x, y) in stream_cells:
            return h - 1
        return h
    _body(vox, top, ztop_main, thick, salt, terrace=(7.0, 2))
    # dirt under the lake and stream beds
    for (x, y) in lake:
        vox["island"].append((x, y, lake_z - 1, "dirt2"))
    # water: lake, stream, waterfall sheet off the rim
    for (x, y) in lake:
        vox["water"].append((x, y, lake_z, "water" if _patch(x, y, 0, salt, 0.85, 3) else "sea2"))
    for (x, y) in stream_cells:
        if (x, y) in top and (x, y) not in lake:
            vox["water"].append((x, y, hill(x, y), "water"))
    fall_dir = (dirx, diry)
    for k in range(-2, 3):               # a 5-wide sheet one cell past the rim, pouring 46 m
        fx = int(round(fall_x + dirx * 2 - diry * k))
        fy = int(round(fall_y + diry * 2 + dirx * k))
        for z in range(hill(fall_x, fall_y), -46, -1):
            vox["water"].append((fx, fy, z, "foam" if (z + k) % 4 == 0 else "water"))

    # ---- ocean basin: a floating ring island 50 m below, catching the fall -------------------------------
    ox, oy = int(fall_x + dirx * 22), int(fall_y + diry * 22)
    oz = -50
    otop = _disc(30, _harm(rng, 2, 0.03, 0.07), ox, oy)
    sea = {(x, y) for (x, y), (d, e) in otop.items() if e > 5.0}

    def ztop_ocean(x, y):
        return oz - 3 if (x, y) in sea else oz
    _body(vox, otop, ztop_ocean, 20, salt ^ 0x5555, sand_w=3.0)
    for (x, y) in sea:
        vox["water"].append((x, y, oz - 2, "sea" if _patch(x, y, 1, salt, 0.8, 3) else "sea2"))
        vox["water"].append((x, y, oz - 3, "deepwater"))
    # the basin's own thin overflow fall on the far side
    bx, by = int(ox + dirx * 29), int(oy + diry * 29)
    for z in range(oz - 2, oz - 30, -1):
        vox["water"].append((bx, by, z, "water" if z % 3 else "foam"))
        vox["water"].append((bx - int(round(diry)), by + int(round(dirx)), z, "water"))

    # ---- source islet: small, 34 m above and behind, with the spring -------------------------------------
    ix, iy = int(hx - dirx * 52), int(hy - diry * 52)
    iz = 34
    itop = _disc(14, _harm(rng, 2, 0.04, 0.08), ix, iy)
    spring = {(x, y) for (x, y), (d, e) in itop.items() if d <= 4.5}

    def ztop_islet(x, y):
        return iz - 2 if (x, y) in spring else iz
    _body(vox, itop, ztop_islet, 16, salt ^ 0xAAAA, sand_w=1.5)
    for (x, y) in spring:
        vox["water"].append((x, y, iz - 1, "water"))
    # ---- the SKY RIVER: a 3-wide ribbon arcing through open air from the spring to the lake ---------------
    ax, ay, az = ix + dirx * 5, iy + diry * 5, iz - 1
    ex, ey, ez = hx - dirx * 9, hy - diry * 9, lake_z + 1
    n = int(math.hypot(ex - ax, ey - ay))
    for i in range(n + 1):
        t = i / float(n)
        px = ax + (ex - ax) * t
        py = ay + (ey - ay) * t
        pz = az + (ez - az) * t + 14.0 * math.sin(math.pi * t)       # rises then dives: a magical arc
        side = math.sin(t * 9.0) * 1.2                                   # a lazy weave in the air
        for k in (-1, 0, 1):
            vx = int(round(px - diry * (k + side)))
            vy = int(round(py + dirx * (k + side)))
            vz = int(round(pz))
            vox["water"].append((vx, vy, vz, "foam" if (i + k) % 5 == 0 else ("water" if k else "sea2")))
            if k == 0 and i % 7 == 0:
                vox["water"].append((vx, vy, vz - 1, "water"))         # droplets under the ribbon
    # a cloud the river passes through, half way up the arc
    mx, my, mz = int((ax + ex) / 2), int((ay + ey) / 2), int((az + ez) / 2 + 13)
    for dx in range(-7, 8):
        for dy in range(-4, 5):
            for dz in range(-2, 3):
                if dx * dx / 49.0 + dy * dy / 16.0 + dz * dz / 4.0 <= 1.0 + rng.uniform(-0.15, 0.15):
                    vox["clouds"].append((mx + dx, my + dy, mz + dz, "cloud"))

    # ---- cottage: stone walls, red roof, chimney and smoke, on the hill's shoulder ------------------------
    cang = sang + math.pi * 0.75
    cx, cy = int(hx + 20 * math.cos(cang)), int(hy + 20 * math.sin(cang))
    hz = hill(cx, cy)
    w, d, h = 9, 7, 5
    for x in range(cx - w // 2, cx + w // 2 + 1):
        for y in range(cy - d // 2, cy + d // 2 + 1):
            for z in range(hz + 1, hz + h + 1):
                shell = x in (cx - w // 2, cx + w // 2) or y in (cy - d // 2, cy + d // 2)
                if not shell:
                    continue
                c = "stone" if _patch(x, y, z, salt, 0.6, 2) else "stone2"
                if z - hz in (2, 3) and ((x - cx) % 3 == 0) and y in (cy - d // 2, cy + d // 2) and x not in (cx - w // 2, cx + w // 2):
                    c = "window"
                if z - hz in (1, 2) and x == cx and y == cy + d // 2:
                    c = "door"
                vox["cottage"].append((x, y, z, c))
    for k in range(5):
        for x in range(cx - w // 2 - 1 + k, cx + w // 2 + 2 - k):
            for y in range(cy - d // 2 - 1, cy + d // 2 + 2):
                vox["cottage"].append((x, y, hz + h + 1 + k, "roof"))
    chx, chy = cx + 2, cy
    for z in range(hz + h + 2, hz + h + 8):
        vox["cottage"].append((chx, chy, z, "stone2"))
    for i, (dx, dy, r) in enumerate(((0, 0, 1), (1, 0, 1), (2, 1, 2), (3, 1, 2), (5, 2, 2))):
        _sphere(vox, "props", chx + dx, chy + dy, hz + h + 9 + i * 2, r, lambda: "smoke" if rng.random() < 0.6 else "smoke2")
    # path from the door down to the lake dock, lanterns beside it
    dock_ang = cang + 0.3
    dx0, dy0 = int(hx + 12 * math.cos(dock_ang)), int(hy + 12 * math.sin(dock_ang))
    steps_n = max(int(math.hypot(dx0 - cx, dy0 - cy)), 1)
    for i in range(d // 2 + 1, steps_n):
        px, py = int(round(cx + (dx0 - cx) * i / steps_n)), int(round(cy + (dy0 - cy) * i / steps_n))
        for (qx, qy) in ((px, py), (px + 1, py)):
            if (qx, qy) in top and (qx, qy) not in lake and (qx, qy) not in stream_cells:
                vox["island"].append((qx, qy, hill(qx, qy), "path"))
        if i % 6 == 0:
            lx, ly = px - 1, py - 1
            if (lx, ly) in top and (lx, ly) not in lake:
                b = hill(lx, ly)
                for z in range(b + 1, b + 4):
                    vox["props"].append((lx, ly, z, "trunk"))
                vox["props"].append((lx, ly, b + 4, "lantern"))
    # dock + boat on the lake
    for i in range(0, 7):
        px, py = int(round(dx0 + math.cos(dock_ang + math.pi) * -i)), int(round(dy0 + math.sin(dock_ang + math.pi) * -i))
        for s in (-1, 0, 1):
            qx, qy = px - int(round(math.sin(dock_ang) * s)), py + int(round(math.cos(dock_ang) * s))
            vox["props"].append((qx, qy, lake_z + 1, "plank"))
            if i % 3 == 0 and s:
                for z in range(lake_z - 2, lake_z + 1):
                    vox["props"].append((qx, qy, z, "fence"))
    bx2, by2 = int(round(hx + 5 * math.cos(dock_ang + 0.6))), int(round(hy + 5 * math.sin(dock_ang + 0.6)))
    for dx in range(-3, 4):
        for dy in range(-1, 2):
            vox["props"].append((bx2 + dx, by2 + dy, lake_z, "boat"))
            if abs(dx) < 3:
                vox["props"].append((bx2 + dx, by2 + dy, lake_z + 1, "boat" if dy else "plank"))
    for z in range(lake_z + 2, lake_z + 8):
        vox["props"].append((bx2, by2, z, "trunk"))
        if z < lake_z + 7:
            for dx in range(1, lake_z + 8 - z):
                vox["props"].append((bx2 + dx, by2, z, "sail"))
    # plank bridge over the stream, a third of the way down
    if len(stream) > 30:
        bxs, bys = stream[len(stream) // 3]
        for s in range(-2, 4):
            for t in (-1, 0, 1, 2):
                qx, qy = bxs + int(round(-diry * s)) + int(round(dirx * t)), bys + int(round(dirx * s)) + int(round(diry * t))
                vox["props"].append((qx, qy, hill(bxs, bys) + 1, "bridge"))
            if s in (-2, 3):
                for t in (-1, 2):
                    qx, qy = bxs + int(round(-diry * s)) + int(round(dirx * t)), bys + int(round(dirx * s)) + int(round(diry * t))
                    vox["props"].append((qx, qy, hill(bxs, bys) + 2, "fence"))

    # ---- trees: big groves of round canopies, blossom trees, a few on the islet --------------------------
    def free(tp, x, y, m=3):
        if (x, y) not in tp or tp[(x, y)][1] < 4:
            return False
        if (x, y) in lake or (x, y) in stream_cells:
            return False
        return abs(x - cx) > w // 2 + m or abs(y - cy) > d // 2 + m

    def big_tree(x, y, base, kind="leaf", fruit=None):
        hgt = rng.randint(6, 9)
        for z in range(base + 1, base + hgt + 1):
            for (tx, ty) in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                vox["trees"].append((tx, ty, z, "trunk"))
        picks = ("leaf", "leaf2", "leaf3") if kind == "leaf" else ("blossom", "blossom2", "blossom")
        pick = lambda: picks[int(rng.random() * 3)]
        r = rng.randint(3, 4)
        shape = "round" if kind == "blossom" else tree_shape
        if shape == "round":
            _sphere(vox, "trees", x, y, base + hgt + 1, r, pick)
            _sphere(vox, "trees", x + rng.randint(-2, 2), y + rng.randint(-2, 2), base + hgt + rng.randint(0, 2), r - 1, pick)
            _sphere(vox, "trees", x + rng.randint(-2, 2), y + rng.randint(-2, 2), base + hgt + 3, r - 1, pick)
        elif shape == "pine":
            for i, rr in enumerate((5, 4, 4, 3, 3, 2, 2, 1, 1, 0)):
                z = base + hgt - 5 + i
                for dx in range(-rr, rr + 1):
                    for dy in range(-rr, rr + 1):
                        if abs(dx) + abs(dy) <= rr:
                            vox["trees"].append((x + dx, y + dy, z, pick()))
        elif shape == "palm":
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                for i in range(1, 8):
                    vox["trees"].append((x + ddx * i, y + ddy * i, base + hgt + (2 if i < 3 else 1) - (i // 3), pick()))
                    if i > 2:
                        vox["trees"].append((x + ddx * i, y + ddy * i, base + hgt + 1 - (i // 3), pick()))
        elif shape == "mangrove":
            for ddx, ddy in ((2, 0), (-2, 1), (1, -2), (-1, -1), (0, 2)):      # stilt roots
                for z in range(base + 1, base + 4):
                    vox["trees"].append((x + ddx * (base + 4 - z) // 2, y + ddy * (base + 4 - z) // 2, z, "trunk"))
            _sphere(vox, "trees", x, y, base + hgt + 1, r + 1, pick)
            _sphere(vox, "trees", x + 3, y - 2, base + hgt - 1, r - 1, pick)
        else:   # dead: bare forked branches, a few embers
            for ddx, ddy in ((1, 0), (-1, 1), (0, -1), (1, 1)):
                for i in range(1, 5):
                    vox["trees"].append((x + ddx * i, y + ddy * i, base + hgt - 3 + i, "trunk"))
                vox["trees"].append((x + ddx * 4, y + ddy * 4, base + hgt + 2, "blossom"))
        if fruit:                              # fruit hangs on the canopy's underside and sides
            for _ in range(10):
                fx_, fy_, fz_ = x + rng.randint(-r, r), y + rng.randint(-r, r), base + hgt + rng.randint(-1, 2)
                vox["trees"].append((fx_, fy_, fz_, "fruit_" + fruit))
    for _ in range(5):
        for _try in range(60):
            gx, gy = rng.randint(-size, size), rng.randint(-size, size)
            if free(top, gx, gy, 6):
                break
        for _ in range(rng.randint(3, 5)):
            tx, ty = gx + rng.randint(-7, 7), gy + rng.randint(-7, 7)
            if free(top, tx, ty, 5):
                big_tree(tx, ty, hill(tx, ty))
    for _ in range(4):
        for _try in range(60):
            tx, ty = rng.randint(-size, size), rng.randint(-size, size)
            if free(top, tx, ty, 5):
                big_tree(tx, ty, hill(tx, ty), "blossom")
                break
    for _ in range(3):
        for _try in range(40):
            tx, ty = ix + rng.randint(-10, 10), iy + rng.randint(-10, 10)
            if (tx, ty) in itop and itop[(tx, ty)][1] > 3 and (tx, ty) not in spring:
                big_tree(tx, ty, iz, "blossom" if rng.random() < 0.4 else "leaf")
                break
    # orchard: a grove of this island's fruit species beside the fields (island_chemistry: what the fruit is for)
    oang = cang + 1.4
    ogx, ogy = int(hx + 30 * math.cos(oang)), int(hy + 30 * math.sin(oang))
    for i, species in enumerate(orchard * 3):
        tx, ty = ogx + (i % 3) * 7 - 7, ogy + (i // 3) * 7 - 7
        if free(top, tx, ty, 3):
            big_tree(tx, ty, hill(tx, ty), "leaf", fruit=CH.ORCHARD[species][0])
    # ---- flowers, garden, mushrooms, rocks ----------------------------------------------------------------
    for _ in range(260):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if free(top, x, y, 1):
            vox["flowers"].append((x, y, hill(x, y) + 1, rng.choice(("flower_r", "flower_y", "flower_w", "flower_p", "flower_b"))))
    gx, gy = cx - w // 2 - 11, cy - d // 2 - 1
    for x in range(gx, gx + 10):
        for y in range(gy, gy + 8):
            if (x, y) not in top or (x, y) in lake:
                continue
            b = hill(x, y)
            if x in (gx, gx + 9) or y in (gy, gy + 7):
                if (x + y) % 2 == 0 or x in (gx, gx + 9):
                    vox["props"].append((x, y, b + 1, "fence"))
            elif (x + y) % 2 == 0:
                vox["flowers"].append((x, y, b + 1, rng.choice(("flower_r", "flower_y", "flower_p"))))
    for _ in range(14):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if free(top, x, y, 1):
            b = hill(x, y)
            vox["props"].append((x, y, b + 1, "trunk"))
            for ddx in (-1, 0, 1):
                for ddy in (-1, 0, 1):
                    vox["props"].append((x + ddx, y + ddy, b + 2, "shroom_dot" if (ddx, ddy) == (0, 0) else "shroom"))
    for _ in range(10):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if free(top, x, y, 2):
            b = hill(x, y)
            for ddx in range(0, rng.randint(2, 4)):
                for ddy in range(0, rng.randint(1, 3)):
                    for ddz in range(1, rng.randint(2, 4)):
                        vox["props"].append((x + ddx, y + ddy, b + ddz, "stone" if rng.random() < 0.5 else "moss"))
    # ---- type extras ----------------------------------------------------------------------------------------
    extra = K.get("extra")
    if K.get("lake") == "ice":
        vox["water"] = [(x, y, z, ("clearbell" if c in ("water", "sea2") else c)) for x, y, z, c in vox["water"]]
    for _ in range({"obsidian_spires": 7, "cacti": 16, "lilies": 40, "spires": 10, "hot_spring": 1}.get(extra, 0)):
        x, y = rng.randint(-size, size), rng.randint(-size, size)
        if extra == "lilies":
            lx_, ly_ = hx + rng.randint(-10, 10), hy + rng.randint(-10, 10)
            if (lx_, ly_) in lake:
                vox["props"].append((lx_, ly_, lake_z + 1, "stridefern"))
                if rng.random() < 0.3:
                    vox["props"].append((lx_, ly_, lake_z + 2, "flower_p"))
            continue
        if not free(top, x, y, 2):
            continue
        b = hill(x, y)
        if extra == "obsidian_spires":
            hgt_ = rng.randint(5, 11)
            for z in range(b + 1, b + hgt_):
                rr = 2 if z < b + 3 else (1 if z < b + hgt_ - 2 else 0)
                for dx in range(-rr, rr + 1):
                    for dy in range(-rr, rr + 1):
                        vox["props"].append((x + dx, y + dy, z, "coal" if (dx + dy + z) % 3 else "forge"))
        elif extra == "cacti":
            hgt_ = rng.randint(3, 6)
            for z in range(b + 1, b + hgt_ + 1):
                vox["props"].append((x, y, z, "stridefern"))
            for ddx in (-1, 1):
                for z in range(b + 2, b + 4):
                    vox["props"].append((x + ddx, y, z, "stridefern"))
                vox["props"].append((x + ddx, y, b + 4, "stridefern"))
            vox["props"].append((x, y, b + hgt_ + 1, "flower_p"))
        elif extra == "spires":
            hgt_ = rng.randint(8, 16)
            c = rng.choice(("crystal", "crystal2", "starmetal"))
            for z in range(b + 1, b + hgt_):
                rr = 2 if z < b + hgt_ // 2 else 1
                for dx in range(-rr, rr + 1):
                    for dy in range(-rr, rr + 1):
                        if abs(dx) + abs(dy) <= rr:
                            vox["crystals"].append((x + dx, y + dy, z, c))
        elif extra == "hot_spring":
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx * dx + dy * dy <= 9:
                        vox["island"].append((x + dx, y + dy, b, "stone"))
                        vox["water"].append((x + dx, y + dy, b, "sea2"))
            for i in range(1, 7):
                _sphere(vox, "props", x + rng.randint(-1, 1), y + rng.randint(-1, 1), b + 2 + i * 2, 1, lambda: "smoke2")
    # ---- ADR-050: the Heartstone core, ore veins on the cliff and in a cave, a meteor crater (LEGENDARY land) --
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            for dz in range(-3, 4):
                if dx * dx + dy * dy + dz * dz * 1.6 <= 17:
                    vox["island"].append((dx, dy, -thick - 1 + dz, "heartstone" if (dx + dy + dz) % 2 else "heartstone2"))
    ores = (("coal", -2, -22, 0.10), ("copper", -6, -28, 0.07), ("iron", -14, -38, 0.06), ("gold", -26, -46, 0.04))
    rock_cells = [(x, y, z) for x, y, z, c in vox["island"] if c in ("rock", "rock2")]
    for (ore, zhi, zlo, p) in ores:
        for (x, y, z) in rock_cells:
            if zlo <= z <= zhi and _patch(x, y, z, salt ^ hash(ore) & 0xFFFF, p, 2):
                vox["island"].append((x, y, z, ore))
    # cave mouth into the hill on the side away from the cottage, with a lit tunnel and a geode at the end
    mang = cang + math.pi
    mx0, my0 = int(hx + 30 * math.cos(mang)), int(hy + 30 * math.sin(mang))
    for i in range(0, 14):
        px, py = int(round(mx0 - i * math.cos(mang))), int(round(my0 - i * math.sin(mang)))
        for s_ in (-1, 0, 1):
            for dz in (0, 1, 2):
                qx, qy = px - int(round(math.sin(mang) * s_)), py + int(round(math.cos(mang) * s_))
                vox["island"].append((qx, qy, hill(px, py) + dz - 2 - i // 4, "cave"))
    gx_, gy_ = int(round(mx0 - 13 * math.cos(mang))), int(round(my0 - 13 * math.sin(mang)))
    for dx in (-1, 0, 1):
        vox["crystals"].append((gx_ + dx, gy_, hill(gx_, gy_) - 5, "crystal2"))
    # mine rails from the cave mouth to the smithy, with a cart
    rail_n = 12
    for i in range(0, rail_n):
        px, py = int(round(mx0 + i * math.cos(mang))), int(round(my0 + i * math.sin(mang)))
        if (px, py) in top:
            vox["props"].append((px, py, hill(px, py) + 1, "rail" if i % 2 else "board"))
    cx2, cy2 = int(round(mx0 + 5 * math.cos(mang))), int(round(my0 + 5 * math.sin(mang)))
    for dx in (-1, 0, 1):
        vox["props"].append((cx2 + dx, cy2, hill(cx2, cy2) + 2, "cart"))
        vox["props"].append((cx2 + dx, cy2, hill(cx2, cy2) + 3, "coal" if dx else "gold"))
    # meteor crater with a starmetal mass, on the terrace near the rim opposite the waterfall
    crx, cry = int(-dirx * (size - 14)), int(-diry * (size - 14))
    for (x, y), (d, e) in (top.items() if legendary else ()):
        dd = math.hypot(x - crx, y - cry)
        if dd <= 7.5:
            zt = hill(x, y) - int(round(3.0 * (1.0 - dd / 7.5)))
            for z in range(hill(x, y), zt - 1, -1):
                vox["island"].append((x, y, z, "crater" if dd > 2.5 else "starmetal"))
            if dd > 7.0:
                vox["island"].append((x, y, hill(x, y) + 1, "deepstone"))
    for z in (range(hill(crx, cry) - 4, hill(crx, cry) - 14, -1) if legendary else ()):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    vox["island"].append((crx + dx, cry + dy, z, "starmetal" if _patch(dx, dy, z, salt, 0.5, 1) else "deepstone"))

    # ---- ADR-054 starter town beside the cottage: well, news board, shop, inn, smithy ---------------------
    tang = cang - 0.45
    tx0, ty0 = int(hx + 27 * math.cos(tang)), int(hy + 27 * math.sin(tang))

    def box(layer, x0, y0, z0, w_, d_, h_, wall, roofc, roof_h=2, door=True):
        for x in range(x0, x0 + w_):
            for y in range(y0, y0 + d_):
                for z in range(z0 + 1, z0 + h_ + 1):
                    if x in (x0, x0 + w_ - 1) or y in (y0, y0 + d_ - 1):
                        c = wall
                        if z - z0 == 2 and (x - x0) % 2 == 1 and y == y0:
                            c = "window"
                        if door and z - z0 in (1, 2) and x == x0 + w_ // 2 and y == y0 + d_ - 1:
                            c = "door"
                        vox[layer].append((x, y, z, c))
        for k in range(roof_h):
            for x in range(x0 - 1 + k, x0 + w_ + 1 - k):
                for y in range(y0 - 1, y0 + d_ + 1):
                    vox[layer].append((x, y, z0 + h_ + 1 + k, roofc))
    tb = hill(tx0, ty0)
    # the well: stone ring, two posts, a little roof, a bucket on a rope
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if abs(dx) + abs(dy) > 0:
                vox["props"].append((tx0 + dx, ty0 + dy, tb + 1, "stone"))
    for dx in (-1, 1):
        for z in range(tb + 2, tb + 5):
            vox["props"].append((tx0 + dx, ty0, z, "trunk"))
    for dx in range(-2, 3):
        vox["props"].append((tx0 + dx, ty0, tb + 5, "thatch"))
        vox["props"].append((tx0 + dx, ty0 + 1, tb + 5, "thatch"))
        vox["props"].append((tx0 + dx, ty0 - 1, tb + 5, "thatch"))
    vox["props"].append((tx0, ty0, tb + 2, "cart"))
    # news board
    nbx, nby = tx0 + 4, ty0 - 4
    for z in range(tb + 1, tb + 4):
        vox["props"].append((nbx, nby, z, "trunk"))
        vox["props"].append((nbx + 3, nby, z, "trunk"))
    for dx in range(0, 4):
        for z in (tb + 2, tb + 3):
            vox["props"].append((nbx + dx, nby + 1, z, "paper" if (dx + z) % 2 else "board"))
    # shop with a striped awning, inn (bigger, two windows rows), smithy with anvil and forge glow
    box("cottage", tx0 - 12, ty0 - 2, hill(tx0 - 12, ty0 - 2), 6, 5, 3, "wall", "thatch", 2)
    for dx in range(-1, 7):
        vox["props"].append((tx0 - 12 + dx, ty0 + 3, hill(tx0 - 12, ty0 - 2) + 3, "awning" if dx % 2 else "awning2"))
    box("cottage", tx0 + 6, ty0 + 3, hill(tx0 + 6, ty0 + 3), 8, 7, 6, "stone", "roof", 3)
    sb = hill(tx0 - 4, ty0 + 8)
    box("cottage", tx0 - 6, ty0 + 7, sb, 6, 5, 3, "stone2", "board", 1, door=False)
    vox["props"].append((tx0 - 4, ty0 + 13, sb + 1, "anvil"))
    vox["props"].append((tx0 - 2, ty0 + 13, sb + 1, "stone"))
    vox["props"].append((tx0 - 2, ty0 + 13, sb + 2, "forge"))
    for z in range(sb + 4, sb + 8):
        vox["cottage"].append((tx0 - 2, ty0 + 9, z, "stone2"))
    _sphere(vox, "props", tx0 - 2, ty0 + 9, sb + 9, 1, lambda: "smoke")
    # windmill on the hill shoulder: the island's power (tower, sails of cloth)
    wmx, wmy = int(hx + 16 * math.cos(cang - 1.2)), int(hy + 16 * math.sin(cang - 1.2))
    wb = hill(wmx, wmy)
    for z in range(wb + 1, wb + 10):
        r_ = 2 if z < wb + 4 else 1
        for dx in range(-r_, r_ + 1):
            for dy in range(-r_, r_ + 1):
                if abs(dx) + abs(dy) <= r_:
                    vox["cottage"].append((wmx + dx, wmy + dy, z, "stone" if (dx + dy + z) % 2 else "stone2"))
    for k in range(-5, 6):
        vox["props"].append((wmx + k, wmy - 2, wb + 8, "sailcloth" if abs(k) > 1 else "trunk"))
        vox["props"].append((wmx, wmy - 2, wb + 8 + k, "sailcloth" if abs(k) > 1 else "trunk"))
        if abs(k) > 1:
            vox["props"].append((wmx + k, wmy - 2, wb + 9 if k > 0 else wb + 7, "sailcloth"))
    # ---- farm: crop rows, a livestock pen with sheep and hens, the herb garden and the brew trough ----------
    fang = cang + 0.9
    fx0, fy0 = int(hx + 34 * math.cos(fang)), int(hy + 34 * math.sin(fang))
    for row in range(0, 5):
        for i in range(0, 12):
            x, y = fx0 + i, fy0 + row * 2
            if (x, y) in top and (x, y) not in lake and (x, y) not in stream_cells:
                b = hill(x, y)
                vox["island"].append((x, y, b, "soil"))
                vox["props"].append((x, y, b + 1, "wheat" if row < 3 else "carrot"))
                if row < 3 and i % 2 == 0:
                    vox["props"].append((x, y, b + 2, "wheat"))
    px0, py0 = fx0 - 12, fy0
    for x in range(px0, px0 + 10):
        for y in range(py0, py0 + 9):
            if (x, y) not in top:
                continue
            b = hill(x, y)
            if (x in (px0, px0 + 9) or y in (py0, py0 + 8)) and (x + y) % 2 == 0:
                vox["props"].append((x, y, b + 1, "fence"))
    for (sx_, sy_) in ((px0 + 3, py0 + 3), (px0 + 6, py0 + 5), (px0 + 4, py0 + 6)):
        b = hill(sx_, sy_)
        for dx in (0, 1):
            for dy in (0, 1):
                vox["props"].append((sx_ + dx, sy_ + dy, b + 1, "trunk"))
                vox["props"].append((sx_ + dx, sy_ + dy, b + 2, "wool"))
        vox["props"].append((sx_ + 2, sy_, b + 2, "coal"))
    for (hx_, hy_) in ((px0 + 2, py0 + 7), (px0 + 7, py0 + 2)):
        b = hill(hx_, hy_)
        vox["props"].append((hx_, hy_, b + 1, "hen"))
        vox["props"].append((hx_, hy_, b + 2, "comb"))
    # herb garden: six herbs in a ring (RingInfusion), the brew trough and the clean-water barrel in the middle
    hgx, hgy = int(hx + 20 * math.cos(cang + 2.2)), int(hy + 20 * math.sin(cang + 2.2))
    for k, herb in enumerate(HERBS):
        if herb not in herbs_here:            # the ring has six beds; only this island's herbs grow in them
            continue
        a = k * math.pi / 3.0
        x, y = int(round(hgx + 4 * math.cos(a))), int(round(hgy + 4 * math.sin(a)))
        if (x, y) in top:
            b = hill(x, y)
            vox["island"].append((x, y, b, "soil"))
            vox["props"].append((x, y, b + 1, herb))
            vox["props"].append((x, y, b + 2, herb))
            vox["props"].append((x + (1 if k % 2 else -1), y, b + 1, herb))
    tbz = hill(hgx, hgy)
    for dx in (-1, 0, 1):
        vox["props"].append((hgx + dx, hgy, tbz + 1, "trough"))
        vox["props"].append((hgx + dx, hgy, tbz + 2, "brew" if dx else "trough"))
    vox["props"].append((hgx, hgy + 2, tbz + 1, "cart"))
    vox["props"].append((hgx, hgy + 2, tbz + 2, "water"))
    # waterworks: a filter hut on the stream bank with a water wheel in the stream (the keeper's well water, filtered)
    if len(stream) > 24:
        wsx, wsy = stream[2 * len(stream) // 3]
        wbz = hill(wsx, wsy)
        bank_x, bank_y = wsx + int(round(-diry * 4)), wsy + int(round(dirx * 4))
        box("cottage", bank_x - 2, bank_y - 2, hill(bank_x, bank_y), 5, 5, 3, "board", "thatch", 2)
        for k in range(-3, 4):
            for j in range(-3, 4):
                if 6 <= k * k + j * j <= 10:
                    vox["props"].append((wsx + int(round(dirx * k)), wsy + int(round(diry * k)), wbz + 2 + j, "wheel"))
        for z in range(wbz + 1, wbz + 3):
            vox["props"].append((wsx + int(round(-diry * 2)), wsy + int(round(dirx * 2)), z, "trunk"))
    # ark moored at the dock (ADR-050: a plank dock where an ark moors) and a fishing pier on the ocean basin
    akx, aky = int(round(hx + 16 * math.cos(dock_ang))), int(round(hy + 16 * math.sin(dock_ang)))
    for i in range(-6, 7):
        for j in range(-2, 3):
            if abs(i) + abs(j) * 2 <= 8:
                vox["props"].append((akx + i, aky + j, lake_z + 1, "hull"))
                if abs(i) < 5 and abs(j) < 2:
                    vox["props"].append((akx + i, aky + j, lake_z + 2, "hull"))
    for z in range(lake_z + 3, lake_z + 12):
        vox["props"].append((akx, aky, z, "trunk"))
        if z < lake_z + 11 and z > lake_z + 4:
            for dx in range(1, min(6, lake_z + 12 - z)):
                vox["props"].append((akx + dx, aky, z, "sailcloth"))
    for i in range(0, 8):
        px, py = int(round(ox - dirx * (29 - i))), int(round(oy - diry * (29 - i)))
        vox["props"].append((px, py, oz + 1, "plank"))
        vox["props"].append((px + 1, py, oz + 1, "plank"))
    # ---- crystals under both rocks, clouds around ---------------------------------------------------------
    for (ccx, ccy, cz, n_) in ((0, 0, -thick - 6, 9), (ox, oy, oz - 24, 4), (ix, iy, iz - 18, 3)):
        for _ in range(n_):
            x, y = ccx + rng.randint(-size // 3, size // 3), ccy + rng.randint(-size // 3, size // 3)
            ln = rng.randint(5, 12)
            c = rng.choice(("crystal", "crystal2"))
            for z in range(cz, cz - ln, -1):
                vox["crystals"].append((x, y, z, c))
                if ln > 8 and z > cz - 4:
                    vox["crystals"].append((x + 1, y, z, c))
                    vox["crystals"].append((x, y + 1, z, c))
    for _ in range(5):
        ang = rng.uniform(0, 6.28)
        cx0, cy0, cz0 = int((size + 24) * math.cos(ang)), int((size + 24) * math.sin(ang)), rng.randint(4, 26)
        for dx in range(-8, 9):
            for dy in range(-4, 5):
                for dz in range(0, 4):
                    if dx * dx / 64.0 + dy * dy / 16.0 + (dz - 1.5) ** 2 / 2.5 <= 1.0 + rng.uniform(-0.2, 0.2):
                        vox["clouds"].append((cx0 + dx, cy0 + dy, cz0 + dz, "cloud"))
    return vox


def build(seed, out, keep=False, realm="WORLD-ZERO", kind="meadow"):
    """Blender: mesh and export the hero island as FBX (body + water + clouds + UCX boxes) + chemistry manifest."""
    import bpy
    vox = plan(seed, realm, kind)
    pal = palette_for(kind)
    with open(out[:-4] + ".chemistry.json", "w", encoding="utf-8") as f:
        f.write(CH.manifest(seed, realm))
    name = "Island_H%d" % seed if kind == "meadow" else "Island_H%d_%s" % (seed, kind)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(name) or ob.name.startswith("UCX_" + name):
            bpy.data.objects.remove(ob, do_unlink=True)
    objs = []
    for layer, members in GROUPS.items():
        voxels = [v for m in members for v in vox.get(m, [])]
        if voxels:
            objs.append(V._mesh_from_voxels("%s_%s" % (name, layer), voxels, pal=pal))
    hulls = V._ucx_boxes(name, vox["island"], depth=6)
    for ob in bpy.data.objects:
        ob.select_set(ob in objs or ob in hulls)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    if not keep:
        for ob in objs + hulls:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {"seed": seed, "out": out, "voxels": V.stats(vox)}
