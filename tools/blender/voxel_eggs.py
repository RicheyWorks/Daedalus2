# SPDX-License-Identifier: MIT
"""Eggs (Richey 15:10: "all sorts of egg types - hatching animals is one of our minigames, like Adopt Me ... gemstone
eggs to diamond to gold to silver to silk to whatever you can come up with").

Every egg type is a material + pattern + rarity, rendered in three stages that follow PORT06 (land egg growth
stages: intact / cracked / hatching) so the same mesh family tells the hatch story. `HATCH[type]` says which creature
families (voxel_creatures) the egg can hatch and at what odds, and `RARITY` carries the mint tiers (common / rare /
legendary / ultra-rare; any egg can also roll SHINY = sparkle voxels + boosted stats, per the mint design).

    import voxel_eggs as E
    E.plan("Diamond", "Cracked")          -> voxels (10 cm; egg ~0.5 m tall; pivot bottom-centre)
    E.CATALOG                             -> {"Prop_Egg_<Type>_<Stage>": ("egg", 10.0)}
    E.manifest()                          -> hatch tables + rarity for the game/ledger
    E.build_all(out_dir)                  -> one FBX + json per egg stage (Blender)
"""
import json
import math
import os
import random

import voxel_creatures as VC
import voxel_island as V

PAL = dict(VC.PAL)
PAL.update({
    "ruby": (0.85, 0.10, 0.20), "ruby2": (1.00, 0.35, 0.45), "sapphire": (0.15, 0.30, 0.85), "sapphire2": (0.40, 0.55, 1.00),
    "emerald": (0.10, 0.65, 0.35), "emerald2": (0.40, 0.90, 0.60), "amethyst": (0.55, 0.30, 0.80), "amethyst2": (0.75, 0.55, 0.95),
    "topaz": (0.95, 0.70, 0.20), "topaz2": (1.00, 0.85, 0.45), "opal": (0.90, 0.92, 0.95), "opal2": (0.75, 0.90, 0.95), "opal3": (0.95, 0.80, 0.90),
    "diamond": (0.92, 0.96, 1.00), "diamond2": (0.75, 0.85, 1.00), "pearl": (0.96, 0.94, 0.90), "pearl2": (0.90, 0.88, 0.95),
    "gold_e": (0.95, 0.78, 0.25), "gold_e2": (1.00, 0.90, 0.50), "silver_e": (0.80, 0.82, 0.86), "silver_e2": (0.95, 0.96, 0.98),
    "copper_e": (0.78, 0.45, 0.25), "bronze": (0.65, 0.45, 0.22), "platinum": (0.85, 0.88, 0.90), "iron_e": (0.45, 0.45, 0.48),
    "silk": (0.95, 0.85, 0.90), "silk2": (0.98, 0.95, 0.98), "velvet": (0.45, 0.10, 0.25), "velvet2": (0.60, 0.20, 0.35), "wool_e": (0.95, 0.95, 0.92),
    "linen": (0.90, 0.85, 0.72), "leather": (0.50, 0.32, 0.18), "speckle_base": (0.90, 0.85, 0.70), "speckle": (0.45, 0.35, 0.25),
    "robin": (0.55, 0.80, 0.85), "marble_w": (0.92, 0.92, 0.90), "marble_v": (0.55, 0.55, 0.58), "moss_e": (0.35, 0.55, 0.25), "bark_e": (0.40, 0.28, 0.16),
    "lava_k": (0.15, 0.10, 0.10), "lava_o": (1.00, 0.45, 0.10), "ice_e": (0.80, 0.92, 1.00), "ice_e2": (0.95, 0.98, 1.00), "cloud_e": (0.96, 0.96, 0.99),
    "galaxy": (0.08, 0.05, 0.20), "galaxy2": (0.35, 0.15, 0.55), "star_e": (1.00, 0.98, 0.80), "dragon_r": (0.65, 0.12, 0.10), "dragon_g": (0.15, 0.45, 0.20),
    "dino_e": (0.60, 0.70, 0.40), "dino_spot": (0.30, 0.40, 0.20), "zombie_e": (0.45, 0.55, 0.35), "zombie_e2": (0.30, 0.35, 0.25), "coral_e": (0.95, 0.50, 0.45),
    "honey_e": (0.95, 0.75, 0.25), "candy_p": (0.98, 0.60, 0.80), "candy_w": (1.00, 1.00, 1.00), "choc": (0.35, 0.20, 0.10), "choc2": (0.50, 0.30, 0.15),
    "pumpkin_e": (0.95, 0.52, 0.12), "bauble_r": (0.80, 0.12, 0.15), "bauble_g": (0.15, 0.55, 0.25), "glow": (0.70, 1.00, 0.80), "obsidian": (0.10, 0.08, 0.12),
    "rainbow1": (0.95, 0.25, 0.25), "rainbow2": (0.98, 0.60, 0.20), "rainbow3": (0.98, 0.92, 0.30), "rainbow4": (0.35, 0.80, 0.40), "rainbow5": (0.30, 0.50, 0.95), "rainbow6": (0.60, 0.35, 0.85),
    "sand_e": (0.85, 0.75, 0.50), "sea_e": (0.25, 0.60, 0.80), "sea_e2": (0.45, 0.80, 0.90), "crystal_e": (0.70, 0.55, 0.95), "crystal_e2": (0.85, 0.75, 1.00),
    "starmetal_e": (0.55, 0.85, 1.00), "heart_e": (1.00, 0.35, 0.45), "heart_e2": (1.00, 0.60, 0.65), "shadow": (0.15, 0.12, 0.20), "bone_e": (0.92, 0.90, 0.80),
    "sparkle": (1.00, 1.00, 1.00), "crack": (0.08, 0.06, 0.06), "yolk": (1.00, 0.85, 0.30),
})
# type: (pattern, colours, rarity, hatch pool {family: weight}) - patterns: solid, speckle, stripe, spiral, dots, marble, zigzag, bands, facet
EGGS = {
    # gemstones
    "Ruby": ("facet", ("ruby", "ruby2"), "rare", {"animal": 3, "bird": 2, "dino": 1}),
    "Sapphire": ("facet", ("sapphire", "sapphire2"), "rare", {"sea": 3, "fish": 2, "bird": 1}),
    "Emerald": ("facet", ("emerald", "emerald2"), "rare", {"animal": 2, "plant": 2, "insect": 2}),
    "Amethyst": ("facet", ("amethyst", "amethyst2"), "rare", {"bee": 2, "insect": 2, "bird": 2}),
    "Topaz": ("facet", ("topaz", "topaz2"), "rare", {"animal": 3, "bird": 3}),
    "Opal": ("marble", ("opal", "opal2", "opal3"), "legendary", {"bird": 2, "sea": 2, "dino": 1, "animal": 1}),
    "Diamond": ("facet", ("diamond", "diamond2"), "legendary", {"dino": 2, "animal": 2, "sea": 1}),
    "Pearl": ("solid", ("pearl", "pearl2"), "rare", {"sea": 4, "fish": 2}),
    "Crystal": ("facet", ("crystal_e", "crystal_e2"), "rare", {"insect": 2, "bee": 2, "plant": 1}),
    "Starmetal": ("facet", ("starmetal_e", "silver_e2"), "ultra", {"dino": 3, "sea": 1, "animal": 1}),
    "Heartstone": ("marble", ("heart_e", "heart_e2"), "ultra", {"animal": 2, "bird": 2, "dino": 2}),
    "Obsidian": ("solid", ("obsidian", "lava_k"), "rare", {"zombie": 2, "dino": 2, "animal": 1}),
    # metals
    "Gold": ("solid", ("gold_e", "gold_e2"), "legendary", {"animal": 3, "bird": 2, "dino": 1}),
    "Silver": ("solid", ("silver_e", "silver_e2"), "rare", {"animal": 3, "bird": 3}),
    "Copper": ("bands", ("copper_e", "bronze"), "common", {"animal": 3, "insect": 2}),
    "Bronze": ("bands", ("bronze", "copper_e"), "common", {"animal": 3, "bird": 1}),
    "Platinum": ("solid", ("platinum", "silver_e2"), "legendary", {"bird": 3, "animal": 2}),
    "Iron": ("solid", ("iron_e", "iron_e"), "common", {"animal": 2, "insect": 2, "zombie": 1}),
    # fabrics
    "Silk": ("spiral", ("silk", "silk2"), "rare", {"bird": 3, "insect": 3}),
    "Velvet": ("solid", ("velvet", "velvet2"), "rare", {"animal": 3, "bee": 1}),
    "Wool": ("dots", ("wool_e", "silver_e"), "common", {"animal": 4}),
    "Linen": ("stripe", ("linen", "wool_e"), "common", {"bird": 3, "animal": 2}),
    "Leather": ("solid", ("leather", "bark_e"), "common", {"animal": 3, "dino": 1}),
    # natural
    "Speckled": ("speckle", ("speckle_base", "speckle"), "common", {"bird": 5}),
    "Robin": ("speckle", ("robin", "speckle"), "common", {"bird": 5}),
    "Marble": ("marble", ("marble_w", "marble_v"), "common", {"animal": 2, "sea": 2}),
    "Moss": ("speckle", ("moss_e", "leaf"), "common", {"plant": 3, "insect": 2, "animal": 1}),
    "Bark": ("stripe", ("bark_e", "trunk"), "common", {"animal": 2, "bird": 2, "insect": 2}),
    "Stone": ("speckle", ("stone", "stone2"), "common", {"animal": 2, "zombie": 1}),
    "Sand": ("dots", ("sand_e", "linen"), "common", {"sea": 2, "animal": 2}),
    "Lava": ("marble", ("lava_k", "lava_o"), "legendary", {"dino": 3, "zombie": 1}),
    "Ice": ("facet", ("ice_e", "ice_e2"), "rare", {"animal": 2, "bird": 2, "sea": 1}),
    "Cloud": ("solid", ("cloud_e", "ice_e2"), "rare", {"bird": 4, "bee": 1}),
    "Rainbow": ("bands", ("rainbow1", "rainbow2", "rainbow3", "rainbow4", "rainbow5", "rainbow6"), "ultra", {"animal": 2, "bird": 2, "sea": 1, "dino": 1, "insect": 1}),
    "Galaxy": ("speckle", ("galaxy", "galaxy2"), "ultra", {"dino": 2, "sea": 2, "bird": 1}),
    "Sea": ("marble", ("sea_e", "sea_e2"), "common", {"sea": 4, "fish": 3}),
    "Coral": ("dots", ("coral_e", "pearl"), "rare", {"sea": 4, "fish": 1}),
    "Honeycomb": ("dots", ("honey_e", "topaz"), "common", {"bee": 5, "insect": 1}),
    "Glow": ("speckle", ("glow", "emerald2"), "rare", {"insect": 3, "plant": 2}),
    "Shadow": ("spiral", ("shadow", "galaxy2"), "rare", {"zombie": 3, "insect": 1}),
    "Bone": ("zigzag", ("bone_e", "linen"), "rare", {"dino": 3, "zombie": 2}),
    # creature-typed
    "Dragon": ("facet", ("dragon_r", "dragon_g"), "legendary", {"dino": 4}),
    "Dino": ("speckle", ("dino_e", "dino_spot"), "rare", {"dino": 5}),
    "Zombie": ("marble", ("zombie_e", "zombie_e2"), "rare", {"zombie": 5}),
    # holidays (clusters)
    "Candy": ("spiral", ("candy_p", "candy_w"), "common", {"animal": 3, "bird": 2}),
    "Chocolate": ("solid", ("choc", "choc2"), "common", {"animal": 4}),
    "Pumpkin": ("stripe", ("pumpkin_e", "topaz"), "rare", {"zombie": 2, "animal": 2, "insect": 1}),
    "Bauble": ("bands", ("bauble_r", "bauble_g", "gold_e"), "rare", {"animal": 3, "bird": 2}),
    "Easter_Painted": ("zigzag", ("flower_p", "flower_y", "feather_b", "egg_g" if "egg_g" in PAL else "emerald2"), "common", {"animal": 3, "bird": 3}),
}
STAGES = ("Intact", "Cracked", "Hatching")
RARITY = {"common": 0.70, "rare": 0.22, "legendary": 0.07, "ultra": 0.01}
SHINY_ODDS = 0.02


def _shell(rx=3, ry=3, rz=4):
    """Egg body: an ellipsoid, fatter at the bottom (z 0..2rz)."""
    cells = []
    for x in range(-rx - 1, rx + 2):
        for y in range(-ry - 1, ry + 2):
            for z in range(0, 2 * rz + 1):
                t = (z - rz) / float(rz)
                w = 1.0 - 0.15 * t - 0.1 * t * t      # narrower at the top
                if (x / (rx * w)) ** 2 + (y / (ry * w)) ** 2 + t * t <= 1.0:
                    cells.append((x, y, z))
    return cells


def _colour(pattern, cols, x, y, z, rng):
    if pattern == "solid":
        return cols[0] if rng.random() < 0.85 else cols[1 % len(cols)]
    if pattern == "speckle":
        return cols[1] if rng.random() < 0.18 else cols[0]
    if pattern == "dots":
        return cols[1] if (x % 3 == 0 and y % 3 == 0 and z % 3 == 1) else cols[0]
    if pattern == "stripe":
        return cols[(z // 2) % len(cols)]
    if pattern == "bands":
        return cols[(z // 2) % len(cols)]
    if pattern == "spiral":
        a = math.atan2(y, x)
        return cols[int((a / math.pi * 3 + z) // 2) % len(cols)]
    if pattern == "zigzag":
        return cols[(abs(x + y) + z // 2) % len(cols)]
    if pattern == "marble":
        v = math.sin(x * 0.9 + z * 0.7) + math.cos(y * 1.1 - z * 0.5)
        return cols[1] if v > 0.9 else (cols[2 % len(cols)] if v < -1.2 else cols[0])
    if pattern == "facet":
        return cols[1] if (abs(x) + abs(y)) % 3 == 0 or z % 4 == 0 else cols[0]
    return cols[0]


def plan(egg, stage="Intact", shiny=False):
    pattern, cols, rarity, _ = EGGS[egg]
    rng = random.Random(sum(ord(c) for c in egg) * 31 + STAGES.index(stage))
    out = []
    shell = _shell()
    top = max(z for _, _, z in shell)
    for (x, y, z) in shell:
        c = _colour(pattern, cols, x, y, z, rng)
        if stage == "Cracked":
            # a jagged crack line running down one side
            if abs(x - int(round(2 * math.sin(z * 0.9)))) <= 0 and y > 0 and 2 <= z <= top - 1:
                c = "crack"
        elif stage == "Hatching":
            if z >= top - 2:                           # the top is broken off
                continue
            if z == top - 3 and (x + y) % 2:          # jagged rim
                continue
        out.append((x, y, z, c))
    if stage == "Hatching":                            # yolk-light inside and a nose peeking out
        out.append((0, 0, top - 3, "yolk"))
        out.append((0, 1, top - 2, "eye"))
        out.append((0, -1, top - 2, "eye"))
        out.append((0, 0, top - 2, "nose"))
    if shiny:
        for _ in range(8):
            x, y, z = rng.choice(shell)
            out.append((x, y, z + (1 if z > top // 2 else 0), "sparkle"))
    # a little nest under every egg so it sits on the ground with a reason
    for x in range(-4, 5):
        for y in range(-4, 5):
            if 9 <= x * x + y * y <= 20:
                out.append((x, y, -1, "hay" if (x + y) % 2 else "trunk"))
    return out


CATALOG = {}
for e in EGGS:
    for st in STAGES:
        CATALOG["Prop_Egg_%s_%s" % (e, st)] = ("egg", 10.0)
    CATALOG["Prop_Egg_%s_Shiny" % e] = ("egg", 10.0)


def manifest():
    return {"stages": list(STAGES), "rarity_odds": RARITY, "shiny_odds": SHINY_ODDS,
            "eggs": {e: {"pattern": p, "rarity": r, "hatch": h} for e, (p, c, r, h) in EGGS.items()},
            "note": "hatch pools name voxel_creatures families; the game rolls a species from the family by the realm's ecology (PORT06 egg stages)"}


def build(name, out_dir):
    import bpy
    egg = name[len("Prop_Egg_"):].rsplit("_", 1)[0]
    stage = name.rsplit("_", 1)[1]
    voxels = plan(egg, "Intact" if stage == "Shiny" else stage, shiny=(stage == "Shiny"))
    ob = V._mesh_from_voxels(name, voxels, scale=10.0, pal=PAL)
    for v in ob.data.vertices:
        v.co.z += 10.0           # the nest sits at z=-1: lift so the ground is z=0
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "egg": egg, "stage": stage, "rarity": EGGS[egg][2], "hatch": EGGS[egg][3], "voxel_cm": 10.0, "pivot": "bottom-centre"}, f, indent=1)
    bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return out


def build_all(out_dir, force=False):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "eggs.manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest(), f, indent=1)
    done = []
    for name in CATALOG:
        if not force and os.path.exists(os.path.join(out_dir, name + ".fbx")):
            continue
        done.append(build(name, out_dir))
    return done
