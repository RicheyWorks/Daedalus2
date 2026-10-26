# SPDX-License-Identifier: MIT
"""Four-island clusters (Richey 13:27: "make your very best multiple island of 4, then five of those that are
different - seasons of the year and holidays, Easter, Halloween, Christmas...").

A cluster = four Skyfall-planner islands of different kinds around a shared sky, at different heights, linked by
SKY RIVERS (water ribbons through the air from each lake to the next lower lake), rope bridges between the two
closest rims, and one big ocean basin underneath that catches all the waterfalls. A theme restyles the whole
cluster: palette, tree dressing and holiday props.

    import island_cluster as X
    X.plan(seed, theme="spring")   -> {layer: voxels}      (pure Python)
    X.build(seed, out_fbx, theme)  -> FBX (body / water / clouds + UCX)  (Blender)

Themes (each realm keeps its own folklore: Halloween belongs to the Labyrinth - Mechanics sheet LAB09):
    spring/easter  - pastel blossom, painted eggs hidden in the grass, a bunny-ear topiary, tulip rows
    summer/festival- lantern strings between trees, paper boats on the lake, fireworks mortars on the pier
    harvest        - autumn palettes, pumpkin patch, hay bales, corn rows, scarecrow
    halloween      - purple-grey grass, dead trees, jack-o-lanterns, candles on the path, fog clouds low (LABYRINTH)
    christmas      - snow, decorated pines (lights), candy-cane posts, gift boxes, a star on the tallest pine
"""
import math
import os
import random

import hero_island as H
import voxel_island as V

THEMES = {
    "spring": {"kinds": ("meadow", "meadow", "mesa", "crystal"), "realm": "WORLD-ZERO",
               "pal": {"grass": (0.45, 0.72, 0.38), "grass2": (0.55, 0.78, 0.42), "blossom": (0.98, 0.72, 0.85), "blossom2": (0.85, 0.80, 0.98)},
               "props": "eggs"},
    "summer": {"kinds": ("meadow", "mesa", "mire", "meadow"), "realm": "WORLD-ZERO",
               "pal": {"grass": (0.32, 0.66, 0.28), "water": (0.25, 0.70, 0.90), "sea": (0.20, 0.62, 0.88)},
               "props": "lanterns"},
    "harvest": {"kinds": ("meadow", "meadow", "mesa", "frost"), "realm": "PARCELS",
                "pal": {"grass": (0.68, 0.58, 0.25), "grass2": (0.76, 0.64, 0.28), "leaf": (0.85, 0.42, 0.12), "leaf2": (0.92, 0.62, 0.16),
                        "leaf3": (0.72, 0.30, 0.10), "blossom": (0.80, 0.20, 0.12), "blossom2": (0.95, 0.50, 0.15)},
                "props": "pumpkins"},
    "halloween": {"kinds": ("volcano", "mire", "crystal", "volcano"), "realm": "LABYRINTH",
                  "pal": {"grass": (0.30, 0.28, 0.38), "grass2": (0.36, 0.32, 0.44), "cloud": (0.55, 0.50, 0.62), "leaf": (0.25, 0.22, 0.28),
                          "leaf2": (0.32, 0.28, 0.34), "blossom": (0.95, 0.50, 0.10), "blossom2": (0.60, 0.20, 0.70), "roof": (0.25, 0.15, 0.30)},
                  "props": "jack"},
    "christmas": {"kinds": ("frost", "frost", "meadow", "crystal"), "realm": "WORLD-ZERO",
                  "pal": {"grass": (0.93, 0.95, 0.98), "grass2": (0.86, 0.90, 0.95), "leaf": (0.12, 0.40, 0.22), "leaf2": (0.18, 0.50, 0.28),
                          "leaf3": (0.10, 0.34, 0.18), "roof": (0.75, 0.15, 0.15), "blossom": (0.90, 0.92, 0.96), "blossom2": (0.75, 0.85, 0.92)},
                  "props": "lights"},
}
THEME_NAMES = tuple(THEMES)
PAL = dict(H.PAL)
PAL.update({"egg_p": (0.95, 0.70, 0.85), "egg_b": (0.65, 0.80, 0.98), "egg_y": (0.98, 0.92, 0.55), "egg_g": (0.70, 0.92, 0.70),
            "lantern_r": (1.00, 0.35, 0.30), "lantern_y": (1.00, 0.85, 0.40), "string": (0.30, 0.25, 0.20), "pumpkin": (0.95, 0.52, 0.12),
            "pumpkin2": (0.85, 0.40, 0.10), "jack": (1.00, 0.80, 0.20), "hay": (0.88, 0.75, 0.40), "scare": (0.60, 0.45, 0.30),
            "candle": (1.00, 0.95, 0.70), "light_r": (1.00, 0.20, 0.20), "light_g": (0.20, 1.00, 0.30), "light_b": (0.30, 0.50, 1.00),
            "cane_r": (0.95, 0.15, 0.15), "cane_w": (1.00, 1.00, 1.00), "gift": (0.85, 0.20, 0.25), "gift2": (0.20, 0.55, 0.85),
            "ribbon": (1.00, 0.90, 0.30), "star": (1.00, 0.95, 0.50), "fog": (0.70, 0.68, 0.76), "rope": (0.55, 0.42, 0.25)})
ISLAND_LAYOUT = ((0, 0, 0), (165, 40, 22), (60, 170, -18), (-120, 130, 38))   # (dx, dy, dz) in voxels, the hero at the origin


def _shift(vox, dx, dy, dz):
    return {k: [(x + dx, y + dy, z + dz, c) for x, y, z, c in v] for k, v in vox.items()}


def _lake_of(vox):
    """(x, y, z) of the island's lake centre: the mean of its 'water' voxels at the most common water height."""
    import collections
    zs = collections.Counter(z for x, y, z, c in vox["water"] if c in ("water", "sea2", "clearbell"))
    if not zs:
        return None
    z = zs.most_common(1)[0][0]
    pts = [(x, y) for x, y, zz, c in vox["water"] if zz == z]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), z)


def _sky_river(out, a, b, rng):
    """A 3-wide ribbon of water arcing through the air from lake a to lake b (b lower)."""
    (ax, ay, az), (bx, by, bz) = a, b
    n = max(int(math.hypot(bx - ax, by - ay)), 2)
    dirx, diry = (bx - ax) / n, (by - ay) / n
    for i in range(n + 1):
        t = i / float(n)
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        pz = az + (bz - az) * t + 18.0 * math.sin(math.pi * t) + 2
        side = math.sin(t * 7.0) * 1.5
        for k in (-1, 0, 1):
            out["water"].append((int(round(px - diry * (k + side))), int(round(py + dirx * (k + side))), int(round(pz)),
                                 "foam" if (i + k) % 6 == 0 else ("water" if k else "sea2")))
        if i % 9 == 0:
            out["water"].append((int(round(px)), int(round(py)), int(round(pz)) - 1, "water"))


def _rope_bridge(out, a, b):
    (ax, ay, az), (bx, by, bz) = a, b
    n = max(int(math.hypot(bx - ax, by - ay)), 2)
    dirx, diry = (bx - ax) / n, (by - ay) / n
    for i in range(n + 1):
        t = i / float(n)
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        pz = az + (bz - az) * t - 4.0 * math.sin(math.pi * t)       # sags in the middle
        for k in (-1, 0, 1):
            out["props"].append((int(round(px - diry * k)), int(round(py + dirx * k)), int(round(pz)), "plank" if i % 2 else "bridge"))
        if i % 5 == 0:
            for z in range(int(round(pz)) + 1, int(round(pz)) + 3):
                out["props"].append((int(round(px - diry * 2)), int(round(py + dirx * 2)), z, "rope"))
                out["props"].append((int(round(px + diry * 2)), int(round(py - dirx * 2)), z, "rope"))


def _theme_props(out, kind_props, islands, rng):
    tops = [(x, y, z) for x, y, z, c in out["island"] if c in ("grass", "grass2")]
    rng.shuffle(tops)
    if kind_props == "eggs":
        for (x, y, z) in tops[:220]:
            out["props"].append((x, y, z + 1, rng.choice(("egg_p", "egg_b", "egg_y", "egg_g"))))
        for (x, y, z) in tops[220:232]:        # tulip rows
            for i in range(6):
                out["props"].append((x + i, y, z + 1, "stridefern"))
                out["props"].append((x + i, y, z + 2, rng.choice(("flower_r", "flower_y", "flower_p"))))
    elif kind_props == "lanterns":
        trunks = [(x, y, z) for x, y, z, c in out["trees"] if c == "trunk"]
        rng.shuffle(trunks)
        for i in range(0, min(len(trunks) - 1, 60), 2):
            (ax, ay, az), (bx, by, bz) = trunks[i], trunks[i + 1]
            n = int(math.hypot(bx - ax, by - ay))
            if 6 < n < 30:
                for j in range(n + 1):
                    t = j / float(n)
                    px, py, pz = ax + (bx - ax) * t, ay + (by - ay) * t, max(az, bz) + 4 - 2.5 * math.sin(math.pi * t)
                    out["props"].append((int(round(px)), int(round(py)), int(round(pz)), "lantern_r" if j % 4 == 0 else ("lantern_y" if j % 4 == 2 else "string")))
    elif kind_props == "pumpkins":
        for (x, y, z) in tops[:90]:
            out["props"].append((x, y, z + 1, "pumpkin" if rng.random() < 0.7 else "pumpkin2"))
            if rng.random() < 0.5:
                out["props"].append((x + 1, y, z + 1, "pumpkin2"))
        for (x, y, z) in tops[90:110]:
            for dx in range(0, 3):
                for dy in range(0, 2):
                    for dz in range(1, 3):
                        out["props"].append((x + dx, y + dy, z + dz, "hay"))
        for (x, y, z) in tops[110:116]:        # scarecrows
            for dz in range(1, 6):
                out["props"].append((x, y, z + dz, "scare"))
            for dx in (-2, -1, 1, 2):
                out["props"].append((x + dx, y, z + 4, "scare"))
            out["props"].append((x, y, z + 6, "jack"))
    elif kind_props == "jack":
        for (x, y, z) in tops[:120]:
            out["props"].append((x, y, z + 1, "pumpkin"))
            out["props"].append((x, y, z + 2, "jack"))
        for (x, y, z) in tops[120:260]:
            out["props"].append((x, y, z + 1, "candle"))
        for (x, y, z) in tops[260:300]:        # fog banks lying low on the grass
            for dx in range(-4, 5):
                for dy in range(-2, 3):
                    if dx * dx / 16.0 + dy * dy / 4.0 <= 1.0:
                        out["clouds"].append((x + dx, y + dy, z + 2, "fog"))
    elif kind_props == "lights":
        leaves = [(x, y, z) for x, y, z, c in out["trees"] if c in ("leaf", "leaf2", "leaf3")]
        rng.shuffle(leaves)
        for (x, y, z) in leaves[:900]:
            out["props"].append((x, y, z + 1, rng.choice(("light_r", "light_g", "light_b", "light_r"))))
        for (x, y, z) in tops[:60]:
            for dz in range(1, 5):
                out["props"].append((x, y, z + dz, "cane_r" if dz % 2 else "cane_w"))
        for (x, y, z) in tops[60:110]:
            for dx in (0, 1):
                for dy in (0, 1):
                    out["props"].append((x + dx, y + dy, z + 1, "gift" if (x + y) % 2 else "gift2"))
            out["props"].append((x, y, z + 2, "ribbon"))
        if leaves:
            tx, ty, tz = max(leaves, key=lambda p: p[2])
            for dz in range(1, 4):
                out["props"].append((tx, ty, tz + dz, "star"))
            out["props"].append((tx + 1, ty, tz + 2, "star"))
            out["props"].append((tx - 1, ty, tz + 2, "star"))


def plan(seed, theme="spring"):
    T = THEMES[theme]
    rng = random.Random(seed * 31337 + 5)
    out = {k: [] for k in H.LAYERS}
    islands = []
    for i, (kind, (dx, dy, dz)) in enumerate(zip(T["kinds"], ISLAND_LAYOUT)):
        vox = H.plan(seed * 10 + i, T["realm"], kind)
        kp = H.KINDS[kind].get("pal", {})
        if kp:                       # keep each kind's own colours inside the shared cluster palette
            vox = {k: [(x, y, z, (c + "@" + kind) if c in kp else c) for x, y, z, c in v] for k, v in vox.items()}
        vox = _shift(vox, dx, dy, dz)
        islands.append((kind, (dx, dy, dz), _lake_of(vox)))
        for k in out:
            out[k].extend(vox.get(k, []))
    # sky rivers: from each lake to the next lower one (sorted by height), through the open air
    lakes = sorted([l for _, _, l in islands if l], key=lambda p: -p[2])
    for a, b in zip(lakes, lakes[1:]):
        _sky_river(out, a, b, rng)
    # rope bridges between the two closest rims (islands 0-1 and 0-3 by the layout)
    for i, j in ((0, 1), (0, 3), (1, 2)):
        (ax, ay, az), (bx, by, bz) = ISLAND_LAYOUT[i], ISLAND_LAYOUT[j]
        n = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / n, (by - ay) / n
        _rope_bridge(out, (ax + ux * 58, ay + uy * 58, az + 1), (bx - ux * 58, by - uy * 58, bz + 1))
    _theme_props(out, T["props"], islands, rng)
    return out


def palette_for(theme):
    pal = dict(PAL)
    for kind, K in H.KINDS.items():
        for c, rgb in K.get("pal", {}).items():
            pal[c + "@" + kind] = rgb
    pal.update(THEMES[theme].get("pal", {}))
    return pal


def build(seed, out, theme="spring", keep=False):
    import bpy
    vox = plan(seed, theme)
    pal = palette_for(theme)
    name = "Cluster_%s_%d" % (theme, seed)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(name) or ob.name.startswith("UCX_" + name):
            bpy.data.objects.remove(ob, do_unlink=True)
    objs = []
    for layer, members in H.GROUPS.items():
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
    return {"seed": seed, "theme": theme, "out": out, "voxels": V.stats(vox)}
