# SPDX-License-Identifier: MIT
"""Static voxel props for the world dresser (Richey 14:58: "more blender items: plants, trees, shrubs, cloud types of
different colours"). Names follow ADR-054's library lookup (`Prop_Tree_<Species>_<Stage>`, `Prop_Plant_*`,
`Prop_Shrub_*`, `Prop_Cloud_*`) so every export joins the world on the next `Dress()` with no code change; pivots
are bottom-centre per docs/BLENDER-TEAM-BRIEF.md; 1 voxel = 10 cm for plants/shrubs, 50 cm for trees, 1 m for clouds.

    import voxel_flora as F
    F.plan("Prop_Tree_Oak_Mature")      -> voxels (pure Python)
    F.CATALOG                           -> every prop name with its family and voxel size
    F.build_all(out_dir)                -> one FBX per prop + json (Blender)
"""
import math
import os
import random

import hero_island as H
import voxel_island as V

import island_cluster as IC
import voxel_creatures as VCR
PAL = dict(H.PAL)
PAL.update(IC.PAL)          # pumpkin, hay, fog, lantern...
PAL.update(VCR.PAL)         # fur_*, stem, shell...
PAL.update({
    "bark_w": (0.88, 0.86, 0.80), "bark_k": (0.20, 0.16, 0.12), "bark_r": (0.55, 0.30, 0.18), "leaf_a": (0.85, 0.42, 0.12), "leaf_y": (0.92, 0.75, 0.20),
    "leaf_d": (0.12, 0.35, 0.18), "leaf_l": (0.55, 0.78, 0.35), "needle": (0.18, 0.40, 0.28), "needle2": (0.25, 0.50, 0.32), "berry": (0.80, 0.15, 0.25),
    "berry_b": (0.30, 0.25, 0.60), "lavender": (0.65, 0.50, 0.85), "rose": (0.90, 0.20, 0.35), "holly": (0.10, 0.35, 0.15), "reed": (0.55, 0.65, 0.30),
    "cattail": (0.45, 0.28, 0.15), "moss_l": (0.45, 0.65, 0.30), "vine": (0.25, 0.50, 0.22), "fern": (0.30, 0.60, 0.28), "bamboo": (0.60, 0.75, 0.35),
    "cloud_w": (0.97, 0.97, 0.99), "cloud_g": (0.70, 0.72, 0.78), "cloud_k": (0.35, 0.36, 0.42), "cloud_p": (0.98, 0.78, 0.85), "cloud_o": (0.98, 0.72, 0.45),
    "cloud_v": (0.70, 0.60, 0.90), "cloud_b": (0.78, 0.88, 0.98), "cloud_y": (0.98, 0.92, 0.70), "cloud_r": (0.95, 0.55, 0.55), "bolt": (1.00, 0.95, 0.60),
    "aurora_g": (0.40, 0.95, 0.70), "aurora_v": (0.60, 0.45, 0.95), "ash": (0.45, 0.42, 0.42), "snowc": (0.92, 0.95, 1.00), "rainbow_r": (0.95, 0.25, 0.25),
    "rainbow_o": (0.98, 0.60, 0.20), "rainbow_y": (0.98, 0.92, 0.30), "rainbow_g": (0.35, 0.80, 0.40), "rainbow_b": (0.30, 0.50, 0.95), "rainbow_v": (0.60, 0.35, 0.85),
})
TREE_SPECIES = {   # species: (bark, leaves, shape)   shapes: round, pine, column, willow, palm, dead, umbrella, bamboo, cactus
    "Oak": ("trunk", ("leaf", "leaf2", "leaf3"), "round"), "Birch": ("bark_w", ("leaf_l", "leaf2"), "column"), "Pine": ("bark_r", ("needle", "needle2"), "pine"),
    "Spruce": ("bark_k", ("needle", "leaf_d"), "pine"), "Willow": ("trunk", ("leaf_l", "leaf"), "willow"), "Maple": ("trunk", ("leaf_a", "leaf_y", "rose"), "round"),
    "Cherry": ("bark_k", ("blossom", "blossom2"), "round"), "Apple": ("trunk", ("leaf", "leaf2", "fruit_apple"), "round"), "Palm": ("trunk", ("leaf_l", "leaf"), "palm"),
    "Baobab": ("bark_r", ("leaf_l",), "umbrella"), "Dead": ("bark_k", (), "dead"), "Mangrove": ("trunk", ("leaf_d", "leaf"), "round"),
    "Redwood": ("bark_r", ("needle2", "needle"), "pine"), "Bamboo": ("bamboo", ("leaf_l",), "bamboo"), "Saguaro": ("stridefern", (), "cactus"),
    "Joshua": ("bark_k", ("needle",), "umbrella"), "Larch": ("bark_r", ("leaf_y", "needle2"), "pine"), "Autumn_Oak": ("trunk", ("leaf_a", "leaf_y", "berry"), "round"),
    "Snow_Pine": ("bark_k", ("needle", "snowc"), "pine"), "Crystal_Tree": ("crystal2", ("crystal", "clearbell"), "round"), "Ember_Tree": ("bark_k", ("forge", "coal"), "dead"),
}
STAGES = {"Sapling": 0.35, "Young": 0.65, "Mature": 1.0, "Ancient": 1.4}
PLANTS = ("Fern", "Grass_Tuft", "Tall_Grass", "Reed", "Cattail", "Lily_Pad", "Moss_Clump", "Vine", "Mushroom_Red", "Mushroom_Brown", "Mushroom_Glow",
          "Clover", "Wildflower_Mix", "Tulip_Row", "Sunflower", "Wheat", "Carrot", "Pumpkin", "Corn", "Cabbage", "Beet", "Edelweiss", "Desert_Rose",
          "Tumbleweed", "Sedge", "Fireweed", "Yarrow", "Dawnleaf", "Rillprism", "Cinderbud", "Stillmoss", "Stridefern", "Clearbell")
SHRUBS = ("Bramble", "Berry_Bush", "Blueberry_Bush", "Hedge", "Lavender", "Rose_Bush", "Holly", "Juniper", "Sagebrush", "Azalea", "Boxwood_Ball", "Fern_Clump")
CLOUDS = ("Cumulus_White", "Cumulus_Big", "Stratus_Grey", "Wisp", "Storm_Dark", "Thunder_Bolt", "Sunset_Pink", "Sunset_Orange", "Dawn_Violet",
          "Sky_Blue", "Gold_Evening", "Blood_Red", "Fog_Bank", "Snow_Cloud", "Ash_Cloud", "Aurora_Ribbon", "Rainbow_Arc", "Rain_Cloud")


def _rng(name):
    return random.Random(sum(ord(c) * (i + 1) for i, c in enumerate(name)))


def _sphere(out, cx, cy, cz, r, pick, rng, holes=0.0):
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dy * dy + dz * dz <= r * r + 1 and rng.random() >= holes:
                    out.append((cx + dx, cy + dy, cz + dz, pick()))


def tree(species, stage):
    bark, leaves, shape = TREE_SPECIES[species]
    k = STAGES[stage]
    rng = _rng(species + stage)
    pick = (lambda: leaves[int(rng.random() * len(leaves))]) if leaves else (lambda: bark)
    out = []
    hgt = max(3, int(12 * k))
    tw = 1 if k < 0.6 else 2
    for z in range(0, hgt):
        for dx in range(0, tw):
            for dy in range(0, tw):
                out.append((dx, dy, z, bark))
    if shape == "round":
        r = max(2, int(5 * k))
        _sphere(out, 0, 0, hgt + r - 1, r, pick, rng, 0.08)
        for _ in range(2 + int(2 * k)):
            _sphere(out, rng.randint(-r, r), rng.randint(-r, r), hgt + rng.randint(r - 3, r + 1), max(1, r - 2), pick, rng, 0.1)
    elif shape == "column":
        r = max(1, int(3 * k))
        for z in range(hgt - 2, hgt + int(8 * k)):
            rr = r if z < hgt + int(5 * k) else max(1, r - 1)
            _sphere(out, 0, 0, z, rr, pick, rng, 0.3)
    elif shape == "pine":
        base_r = max(2, int(5 * k))
        for i in range(int(10 * k) + 1):
            rr = max(0, base_r - (i * base_r) // (int(10 * k) + 1))
            z = hgt - int(6 * k) + i
            for dx in range(-rr, rr + 1):
                for dy in range(-rr, rr + 1):
                    if abs(dx) + abs(dy) <= rr:
                        out.append((dx, dy, z, pick()))
        out.append((0, 0, hgt + int(4 * k) + 1, pick()))
    elif shape == "willow":
        r = max(2, int(5 * k))
        _sphere(out, 0, 0, hgt + 1, r, pick, rng, 0.2)
        for _ in range(int(14 * k)):
            a = rng.uniform(0, 6.28)
            x, y = int(round((r + 1) * math.cos(a))), int(round((r + 1) * math.sin(a)))
            for z in range(hgt + 1, max(1, hgt - int(8 * k)), -1):
                out.append((x, y, z, pick()))
    elif shape == "palm":
        for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            for i in range(1, int(7 * k) + 2):
                out.append((ddx * i, ddy * i, hgt + (2 if i < 3 else 1) - i // 3, pick()))
        out.append((0, 0, hgt + 2, "fruit_orange" if "fruit_orange" in PAL else "beak"))
    elif shape == "umbrella":
        r = max(3, int(7 * k))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    out.append((dx, dy, hgt, pick()))
                    if dx * dx + dy * dy <= (r - 2) ** 2:
                        out.append((dx, dy, hgt + 1, pick()))
        for z in range(0, hgt):
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    out.append((dx, dy, z, bark))
    elif shape == "dead":
        for ddx, ddy in ((1, 0), (-1, 1), (0, -1), (1, 1), (-1, -1)):
            for i in range(1, int(5 * k) + 1):
                out.append((ddx * i, ddy * i, hgt - 3 + i, bark))
                if leaves and i == int(5 * k):
                    out.append((ddx * i, ddy * i, hgt - 2 + i, pick()))
    elif shape == "bamboo":
        out = []
        for (bx, by) in ((0, 0), (2, 1), (-1, 2), (1, -2), (-2, -1)):
            for z in range(0, hgt + int(6 * k)):
                out.append((bx, by, z, "bamboo" if z % 4 else "leaf_d"))
                if z % 5 == 3:
                    out.append((bx + 1, by, z, "leaf_l"))
    elif shape == "cactus":
        out = []
        for z in range(0, hgt):
            out.append((0, 0, z, bark))
            out.append((1, 0, z, bark))
        for sx in (-2, 3):
            for z in range(hgt // 3, hgt // 3 + 2):
                out.append((sx, 0, z, bark))
            for z in range(hgt // 3 + 2, hgt - 2):
                out.append((sx, 0, z, bark))
        out.append((0, 0, hgt, "flower_p"))
    return out


def plant(name):
    rng = _rng(name)
    out = []
    n = name
    if n in ("Fern", "Fern_Clump"):
        for i, (dx, dy) in enumerate(((3, 0), (-3, 1), (0, 3), (1, -3), (-2, -2), (2, 2))):
            for t in range(1, 5):
                out.append((int(round(dx * t / 4)), int(round(dy * t / 4)), min(t, 3), "fern"))
    elif n in ("Grass_Tuft", "Tall_Grass", "Sedge", "Reed"):
        h = {"Grass_Tuft": 3, "Tall_Grass": 6, "Sedge": 5, "Reed": 9}[n]
        c = "reed" if n == "Reed" else ("sedge" if "sedge" in PAL else "grass2")
        for (x, y) in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)):
            for z in range(0, h - abs(x) - abs(y)):
                out.append((x, y, z, c if z < h - 2 else "leaf_l"))
    elif n == "Cattail":
        for z in range(0, 8):
            out.append((0, 0, z, "reed" if z < 5 else "cattail"))
        for z in range(0, 6):
            out.append((2, 1, z, "reed"))
    elif n == "Lily_Pad":
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5 and not (dx > 0 and dy == 0):
                    out.append((dx, dy, 0, "stridefern"))
        out.append((0, 0, 1, "flower_p"))
    elif n == "Moss_Clump":
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    out.append((dx, dy, 0, "moss_l" if rng.random() < 0.7 else "moss"))
    elif n == "Vine":
        for z in range(0, 12):
            out.append((0 if z % 4 < 2 else 1, 0, z, "vine"))
            if z % 3 == 0:
                out.append((-1 if z % 2 else 2, 0, z, "leaf_l"))
    elif n.startswith("Mushroom"):
        c = {"Mushroom_Red": "shroom", "Mushroom_Brown": "fur_b", "Mushroom_Glow": "lantern"}[n]
        for z in range(0, 3):
            out.append((0, 0, z, "trunk" if n != "Mushroom_Glow" else "clearbell"))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.append((dx, dy, 3, "shroom_dot" if (dx, dy) == (0, 0) and n == "Mushroom_Red" else c))
    elif n == "Clover":
        for (x, y) in ((0, 0), (1, 0), (0, 1), (1, 1)):
            out.append((x, y, 0, "leaf_l"))
    elif n in ("Wildflower_Mix", "Tulip_Row", "Sunflower", "Edelweiss", "Desert_Rose", "Fireweed", "Yarrow"):
        cols = {"Wildflower_Mix": ("flower_r", "flower_y", "flower_w", "flower_p", "flower_b"), "Tulip_Row": ("flower_r", "flower_y", "flower_p"),
                "Sunflower": ("flower_y",), "Edelweiss": ("flower_w",), "Desert_Rose": ("flower_p",), "Fireweed": ("flower_p", "rose"), "Yarrow": ("flower_w", "flower_y")}[n]
        cnt = {"Wildflower_Mix": 7, "Tulip_Row": 5, "Sunflower": 1, "Edelweiss": 3, "Desert_Rose": 2, "Fireweed": 4, "Yarrow": 4}[n]
        h = 8 if n == "Sunflower" else 3
        for i in range(cnt):
            x, y = (i * 2 - cnt, 0) if n == "Tulip_Row" else (rng.randint(-2, 2), rng.randint(-2, 2))
            for z in range(0, h):
                out.append((x, y, z, "stem"))
            out.append((x, y, h, cols[i % len(cols)]))
            if n == "Sunflower":
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        out.append((x + dx, y + dy, h, "flower_y" if (dx, dy) != (0, 0) else "fur_b"))
    elif n in ("Wheat", "Corn", "Carrot", "Cabbage", "Beet", "Pumpkin"):
        if n == "Wheat":
            for x in range(-2, 3):
                for z in range(0, 5):
                    out.append((x, 0, z, "wheat" if z > 2 else "stem"))
        elif n == "Corn":
            for z in range(0, 10):
                out.append((0, 0, z, "stem" if z % 3 else "leaf_l"))
            out.append((1, 0, 6, "wheat"))
        elif n == "Carrot":
            for x in (-2, 0, 2):
                for z in range(0, 3):
                    out.append((x, 0, z, "stridefern"))
                out.append((x, 0, -1, "carrot"))
        elif n == "Cabbage":
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    out.append((dx, dy, 0, "leaf_l"))
            out.append((0, 0, 1, "leaf_l"))
        elif n == "Beet":
            out.append((0, 0, 0, "flower_p"))
            for z in (1, 2):
                out.append((0, 0, z, "leaf_d"))
        else:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for z in (0, 1):
                        out.append((dx, dy, z, "pumpkin"))
            out.append((0, 0, 2, "stem"))
    elif n == "Tumbleweed":
        _sphere(out, 0, 0, 2, 2, lambda: "hay", rng, 0.45)
    elif n in ("Dawnleaf", "Rillprism", "Cinderbud", "Stillmoss", "Stridefern", "Clearbell"):
        key = n.lower()
        for z in range(0, 3):
            out.append((0, 0, z, "stem"))
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            out.append((dx, dy, 2, key))
        out.append((0, 0, 3, key))
    return out


def shrub(name):
    rng = _rng(name)
    out = []
    base = {"Bramble": ("vine", "berry"), "Berry_Bush": ("leaf_d", "berry"), "Blueberry_Bush": ("leaf_d", "berry_b"), "Hedge": ("holly", None),
            "Lavender": ("leaf_l", "lavender"), "Rose_Bush": ("leaf_d", "rose"), "Holly": ("holly", "berry"), "Juniper": ("needle", "berry_b"),
            "Sagebrush": ("fur_g", None), "Azalea": ("leaf", "flower_p"), "Boxwood_Ball": ("leaf_d", None), "Fern_Clump": ("fern", None)}[name]
    if name == "Hedge":
        for x in range(-4, 5):
            for y in range(-1, 2):
                for z in range(0, 4):
                    out.append((x, y, z, base[0]))
    elif name == "Lavender":
        for x in range(-3, 4):
            for z in range(0, 3):
                out.append((x, (x * 3) % 2, z, base[0] if z < 2 else base[1]))
                out.append((x, (x * 3) % 2, 3, base[1]))
    else:
        _sphere(out, 0, 0, 2, 3, lambda: base[0], rng, 0.25)
        if base[1]:
            for _ in range(10):
                out.append((rng.randint(-3, 3), rng.randint(-3, 3), rng.randint(1, 5), base[1]))
    return out


def cloud(name):
    rng = _rng(name)
    out = []
    col = {"Cumulus_White": "cloud_w", "Cumulus_Big": "cloud_w", "Stratus_Grey": "cloud_g", "Wisp": "cloud_w", "Storm_Dark": "cloud_k", "Thunder_Bolt": "cloud_k",
           "Sunset_Pink": "cloud_p", "Sunset_Orange": "cloud_o", "Dawn_Violet": "cloud_v", "Sky_Blue": "cloud_b", "Gold_Evening": "cloud_y", "Blood_Red": "cloud_r",
           "Fog_Bank": "fog", "Snow_Cloud": "snowc", "Ash_Cloud": "ash", "Aurora_Ribbon": "aurora_g", "Rainbow_Arc": "rainbow_r", "Rain_Cloud": "cloud_g"}[name]
    if name == "Rainbow_Arc":
        bands = ("rainbow_r", "rainbow_o", "rainbow_y", "rainbow_g", "rainbow_b", "rainbow_v")
        for i, c in enumerate(bands):
            r = 20 - i
            for a in range(0, 181, 2):
                x, z = int(round(r * math.cos(math.radians(a)))), int(round(r * math.sin(math.radians(a))))
                out.append((x, 0, z, c))
        return out
    if name == "Aurora_Ribbon":
        for x in range(-16, 17):
            for z in range(0, 5):
                out.append((x, int(round(3 * math.sin(x / 4.0))), z + int(round(2 * math.sin(x / 3.0))), "aurora_g" if (x + z) % 3 else "aurora_v"))
        return out
    sx, sy, sz = {"Cumulus_Big": (12, 7, 5), "Stratus_Grey": (16, 6, 2), "Wisp": (14, 2, 1), "Fog_Bank": (18, 10, 2)}.get(name, (8, 5, 3))
    for dx in range(-sx, sx + 1):
        for dy in range(-sy, sy + 1):
            for dz in range(0, sz + 1):
                if dx * dx / float(sx * sx) + dy * dy / float(sy * sy) + (dz - sz / 2.0) ** 2 / (sz * sz / 2.5) <= 1.0 + rng.uniform(-0.2, 0.2):
                    c = col
                    if name == "Sunset_Pink" and dz == sz:
                        c = "cloud_o"
                    if name in ("Storm_Dark", "Thunder_Bolt", "Rain_Cloud") and dz == sz:
                        c = "cloud_g"
                    out.append((dx, dy, dz, c))
    if name == "Cumulus_White" or name == "Cumulus_Big":
        for _ in range(3):
            _sphere(out, rng.randint(-sx // 2, sx // 2), rng.randint(-sy // 2, sy // 2), sz + 1, 3, lambda: col, rng, 0.1)
    if name == "Thunder_Bolt":
        x, y = 0, 0
        for z in range(0, -9, -1):
            x += rng.choice((-1, 0, 1))
            out.append((x, y, z - 1, "bolt"))
    if name == "Rain_Cloud":
        for _ in range(30):
            out.append((rng.randint(-sx, sx), rng.randint(-sy, sy), rng.randint(-6, -1), "water"))
    if name == "Snow_Cloud":
        for _ in range(30):
            out.append((rng.randint(-sx, sx), rng.randint(-sy, sy), rng.randint(-6, -1), "cloud_w"))
    return out


CATALOG = {}
for sp in TREE_SPECIES:
    for st in STAGES:
        CATALOG["Prop_Tree_%s_%s" % (sp, st)] = ("tree", 50.0)
for p in PLANTS:
    CATALOG["Prop_Plant_%s" % p] = ("plant", 10.0)
for s_ in SHRUBS:
    CATALOG["Prop_Shrub_%s" % s_] = ("shrub", 10.0)
for c in CLOUDS:
    CATALOG["Prop_Cloud_%s" % c] = ("cloud", 100.0)


def plan(name):
    fam, _ = CATALOG[name]
    if fam == "tree":
        _, sp, st = name.split("_", 2)[0], name[len("Prop_Tree_"):].rsplit("_", 1)[0], name.rsplit("_", 1)[1]
        return tree(sp, st)
    if fam == "plant":
        return plant(name[len("Prop_Plant_"):])
    if fam == "shrub":
        return shrub(name[len("Prop_Shrub_"):])
    return cloud(name[len("Prop_Cloud_"):])


def build(name, out_dir):
    import bpy
    voxels = plan(name)
    fam, cm = CATALOG[name]
    for ob in list(bpy.data.objects):
        if ob.name == name:
            bpy.data.objects.remove(ob, do_unlink=True)
    ob = V._mesh_from_voxels(name, voxels, scale=cm, pal=PAL)
    # bottom-centre pivot: the brief wants the origin on the ground under the prop's centre
    zmin = min(z for _, _, z, _ in voxels)
    for v in ob.data.vertices:
        v.co.z -= zmin * cm
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    import json
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "family": fam, "voxel_cm": cm, "voxels": len(voxels), "pivot": "bottom-centre", "collides": fam in ("tree",)}, f, indent=1)
    bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return out


def build_all(out_dir, families=None, force=False):
    done = []
    for name, (fam, _) in CATALOG.items():
        if families and fam not in families:
            continue
        if not force and os.path.exists(os.path.join(out_dir, name + ".fbx")):
            continue
        done.append(build(name, out_dir))
    return done
