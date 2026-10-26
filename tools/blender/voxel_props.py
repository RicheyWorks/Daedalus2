# SPDX-License-Identifier: MIT
"""Household equipment, graveyard pieces and sports gear (Richey 15:10-15:11: "tombstones, bathtubs and all house
equipment ... all sports equipment: islanders play baseball, catch, basketball, football, dodgeball").

Static voxel props, 10 cm voxels, bottom-centre pivot, dresser names `Prop_House_*`, `Prop_Grave_*`, `Prop_Sport_*`.
Balls are separate single props so the games can throw them (the ledger's minigames: catch, dodgeball, baseball...).

    import voxel_props as P
    P.CATALOG; P.plan(name) -> voxels; P.build_all(out_dir)
"""
import math
import os

import voxel_farm as FM
import voxel_island as V

import voxel_eggs as EG
import voxel_flora as FL
PAL = dict(FM.PAL)
PAL.update(FL.PAL)
PAL.update(EG.PAL)
PAL.update({"pot": (0.35, 0.35, 0.38), "linen": (0.90, 0.85, 0.72), "leather": (0.50, 0.32, 0.18), "glow": (0.70, 1.00, 0.80)})
PAL.update({"porcelain": (0.96, 0.96, 0.95), "chrome": (0.80, 0.84, 0.88), "oak": (0.70, 0.52, 0.32), "oak_d": (0.50, 0.35, 0.20), "cushion_r": (0.75, 0.20, 0.25),
            "cushion_b": (0.25, 0.40, 0.70), "cushion_g": (0.30, 0.60, 0.35), "linen_w": (0.95, 0.94, 0.90), "blanket": (0.40, 0.55, 0.75), "pillow": (0.98, 0.98, 0.96),
            "screen": (0.10, 0.12, 0.15), "brass": (0.80, 0.65, 0.30), "candle_w": (0.97, 0.95, 0.85), "flame": (1.00, 0.75, 0.30), "rug_r": (0.70, 0.25, 0.25),
            "rug_y": (0.90, 0.80, 0.45), "book_r": (0.70, 0.20, 0.20), "book_b": (0.20, 0.35, 0.70), "book_g": (0.25, 0.55, 0.30), "mirror": (0.80, 0.90, 0.95),
            "granite": (0.45, 0.45, 0.48), "granite2": (0.38, 0.38, 0.42), "marble_g": (0.85, 0.85, 0.83), "moss_g": (0.40, 0.55, 0.30), "ivy": (0.25, 0.45, 0.22),
            "iron_g": (0.20, 0.20, 0.24), "skull": (0.92, 0.90, 0.82), "soil_g": (0.30, 0.22, 0.14), "ghost": (0.85, 0.90, 0.95),
            "baseball": (0.97, 0.96, 0.92), "stitch": (0.85, 0.20, 0.20), "basketball": (0.90, 0.45, 0.15), "football": (0.50, 0.30, 0.18), "soccer_w": (0.97, 0.97, 0.97),
            "soccer_k": (0.10, 0.10, 0.12), "dodge_r": (0.85, 0.20, 0.25), "dodge_b": (0.25, 0.45, 0.85), "dodge_y": (0.95, 0.80, 0.20), "volley": (0.95, 0.95, 0.90),
            "tennis": (0.80, 0.95, 0.25), "golf_w": (0.98, 0.98, 0.98), "puck": (0.08, 0.08, 0.08), "net": (0.90, 0.90, 0.90), "court": (0.85, 0.60, 0.35),
            "leather_g": (0.60, 0.40, 0.22), "glove": (0.55, 0.35, 0.20), "bat": (0.78, 0.62, 0.38), "pole": (0.75, 0.75, 0.78), "flag_r": (0.85, 0.15, 0.15),
            "board": (0.55, 0.35, 0.20) if "board" not in PAL else PAL["board"], "trophy": (0.95, 0.80, 0.25), "mat": (0.25, 0.40, 0.75), "bowl_pin": (0.97, 0.97, 0.95),
            "bowl_ball": (0.15, 0.10, 0.30), "surf": (0.95, 0.60, 0.30), "kayak": (0.90, 0.30, 0.20), "frisbee": (0.95, 0.35, 0.60)})


def box(out, x0, y0, z0, w, d, h, c):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + d):
            for z in range(z0, z0 + h):
                out.append((x, y, z, c))


def ball(out, cx, cy, cz, r, c, c2=None, seam="none"):
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dy * dy + dz * dz <= r * r + 1:
                    col = c
                    if c2 and seam == "stitch" and abs(dx) == abs(dz) and dy in (-r, r):
                        col = c2
                    if c2 and seam == "lines" and (dx == 0 or dz == 0) and dx * dx + dy * dy + dz * dz >= (r - 1) ** 2:
                        col = c2
                    if c2 and seam == "patches" and (dx + dy + dz) % 3 == 0 and dx * dx + dy * dy + dz * dz >= (r - 1) ** 2:
                        col = c2
                    out.append((cx + dx, cy + dy, cz + dz, col))


def house(n):
    o = []
    if n == "Bed":
        box(o, -4, -7, 0, 8, 14, 1, "oak_d")
        box(o, -4, -7, 1, 8, 14, 2, "linen_w")
        box(o, -4, -7, 3, 8, 11, 1, "blanket")
        box(o, -3, 4, 3, 3, 3, 1, "pillow")
        box(o, 1, 4, 3, 3, 3, 1, "pillow")
        box(o, -4, 7, 0, 8, 1, 7, "oak")
    elif n == "Bed_Bunk":
        for z in (0, 6):
            box(o, -3, -6, z, 6, 12, 1, "oak_d")
            box(o, -3, -6, z + 1, 6, 12, 1, "blanket")
        for (x, y) in ((-3, -6), (2, -6), (-3, 5), (2, 5)):
            box(o, x, y, 0, 1, 1, 10, "oak")
    elif n == "Crib":
        box(o, -3, -4, 2, 6, 8, 1, "linen_w")
        for x in range(-3, 3):
            box(o, x, -4, 0, 1, 1, 6, "oak" if x % 2 else "oak_d")
            box(o, x, 3, 0, 1, 1, 6, "oak" if x % 2 else "oak_d")
    elif n in ("Table", "Table_Round", "Desk", "Nightstand", "Coffee_Table"):
        w, d, h = {"Table": (8, 5, 5), "Table_Round": (6, 6, 5), "Desk": (8, 4, 5), "Nightstand": (3, 3, 4), "Coffee_Table": (6, 4, 3)}[n]
        box(o, -w // 2, -d // 2, h - 1, w, d, 1, "oak")
        for (x, y) in ((-w // 2, -d // 2), (w // 2 - 1, -d // 2), (-w // 2, d // 2 - 1), (w // 2 - 1, d // 2 - 1)):
            box(o, x, y, 0, 1, 1, h - 1, "oak_d")
        if n == "Desk":
            box(o, 1, -1, h, 2, 2, 1, "book_b")
            box(o, -3, 0, h, 1, 1, 2, "candle_w")
        if n == "Nightstand":
            box(o, -1, -1, h, 1, 1, 2, "brass")
            box(o, -2, -2, h + 2, 3, 3, 1, "linen_w")
    elif n in ("Chair", "Stool", "Armchair", "Sofa", "Bench_Indoor", "Rocking_Chair"):
        if n == "Stool":
            box(o, -1, -1, 3, 3, 3, 1, "oak")
            for (x, y) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                box(o, x, y, 0, 1, 1, 3, "oak_d")
        elif n == "Chair" or n == "Rocking_Chair":
            box(o, -2, -2, 3, 4, 4, 1, "oak")
            for (x, y) in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
                box(o, x, y, 0, 1, 1, 3, "oak_d")
            box(o, -2, -2, 4, 4, 1, 4, "oak")
            if n == "Rocking_Chair":
                box(o, -3, -3, 0, 1, 6, 1, "oak_d")
                box(o, 2, -3, 0, 1, 6, 1, "oak_d")
        else:
            w = 4 if n == "Armchair" else 10
            box(o, -w // 2, -2, 1, w, 5, 2, "cushion_r" if n != "Bench_Indoor" else "oak")
            box(o, -w // 2, -3, 1, w, 1, 5, "cushion_r" if n != "Bench_Indoor" else "oak")
            box(o, -w // 2 - 1, -3, 1, 1, 6, 4, "cushion_r" if n != "Bench_Indoor" else "oak_d")
            box(o, w // 2, -3, 1, 1, 6, 4, "cushion_r" if n != "Bench_Indoor" else "oak_d")
            box(o, -w // 2, -2, 0, w, 5, 1, "oak_d")
    elif n in ("Bathtub", "Bathtub_Clawfoot", "Shower", "Toilet", "Sink", "Sink_Kitchen", "Washbasin", "Towel_Rack", "Bath_Mat"):
        if n.startswith("Bathtub"):
            box(o, -3, -7, 1 if n == "Bathtub_Clawfoot" else 0, 6, 14, 4, "porcelain")
            box(o, -2, -6, 3, 4, 12, 1, "water")
            box(o, -2, -6, 4, 4, 12, 1, "water" if n == "Bathtub" else "cloud_w")
            box(o, -1, 6, 4, 1, 1, 2, "chrome")
            box(o, 0, 6, 5, 1, 1, 1, "chrome")
            if n == "Bathtub_Clawfoot":
                for (x, y) in ((-3, -7), (2, -7), (-3, 6), (2, 6)):
                    box(o, x, y, 0, 1, 1, 1, "brass")
        elif n == "Shower":
            box(o, -3, -3, 0, 6, 6, 1, "porcelain")
            box(o, -3, -3, 1, 1, 6, 12, "glass")
            box(o, -3, 2, 1, 6, 1, 12, "glass")
            box(o, 0, 2, 11, 1, 1, 1, "chrome")
            box(o, 0, 0, 11, 1, 2, 1, "chrome")
            for z in range(4, 11, 2):
                box(o, 0, 0, z, 1, 1, 1, "water")
        elif n == "Toilet":
            box(o, -2, -2, 0, 4, 5, 4, "porcelain")
            box(o, -1, -1, 4, 2, 3, 1, "water")
            box(o, -2, -3, 4, 4, 1, 5, "porcelain")
            box(o, -2, -2, 4, 4, 5, 1, "porcelain")
            box(o, -1, -3, 9, 1, 1, 1, "chrome")
        elif n in ("Sink", "Washbasin", "Sink_Kitchen"):
            h = 8 if n != "Washbasin" else 7
            box(o, -3, -2, 0, 6, 4, h, "porcelain" if n != "Sink_Kitchen" else "oak")
            box(o, -2, -1, h - 1, 4, 2, 1, "chrome" if n == "Sink_Kitchen" else "water")
            box(o, 0, 1, h, 1, 1, 2, "chrome")
            box(o, 0, 0, h + 1, 1, 1, 1, "chrome")
        elif n == "Towel_Rack":
            box(o, -3, 0, 0, 7, 1, 1, "chrome")
            box(o, -2, 0, 0, 2, 1, 4, "linen_w")
            box(o, 1, 0, 0, 2, 1, 4, "blanket")
        else:
            box(o, -3, -2, 0, 6, 4, 1, "mat")
    elif n in ("Stove", "Fridge", "Oven_Brick", "Kitchen_Counter", "Cupboard", "Kettle", "Pot", "Pan", "Cutting_Board", "Dish_Rack", "Bread_Oven"):
        if n == "Stove":
            box(o, -3, -3, 0, 6, 6, 8, "chrome")
            for (x, y) in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
                box(o, x, y, 8, 2, 2, 1, "metal_k")
            box(o, -2, -3, 2, 4, 1, 4, "screen")
        elif n == "Fridge":
            box(o, -3, -3, 0, 6, 6, 16, "porcelain")
            box(o, 2, -3, 4, 1, 1, 8, "chrome")
        elif n in ("Oven_Brick", "Bread_Oven"):
            for z in range(0, 7):
                r = 3 if z < 4 else 3 - (z - 4)
                box(o, -r, -3, z, 2 * r + 1, 6, 1, "stone" if z % 2 else "stone2")
            box(o, -1, 3, 1, 3, 1, 3, "forge")
        elif n == "Kitchen_Counter":
            box(o, -6, -2, 0, 12, 4, 7, "oak")
            box(o, -6, -2, 7, 12, 4, 1, "marble_g")
            box(o, -5, -1, 8, 2, 2, 2, "pot")
        elif n == "Cupboard":
            box(o, -3, -1, 0, 6, 2, 10, "oak")
            box(o, -1, 1, 4, 1, 1, 1, "brass")
        elif n == "Kettle":
            box(o, -1, -1, 0, 3, 3, 3, "chrome")
            box(o, 2, 0, 1, 1, 1, 2, "chrome")
            box(o, 0, 0, 3, 1, 1, 1, "metal_k")
        elif n == "Pot":
            box(o, -2, -2, 0, 4, 4, 3, "metal_k")
            box(o, -1, -1, 3, 2, 2, 1, "metal")
        elif n == "Pan":
            box(o, -2, -2, 0, 4, 4, 1, "metal_k")
            box(o, 2, 0, 0, 4, 1, 1, "oak_d")
        elif n == "Cutting_Board":
            box(o, -3, -2, 0, 6, 4, 1, "oak")
            box(o, -1, 0, 1, 2, 1, 1, "carrot")
        else:
            box(o, -3, -1, 0, 6, 2, 1, "chrome")
            for x in range(-2, 3, 2):
                box(o, x, 0, 1, 1, 1, 3, "porcelain")
    elif n in ("Bookshelf", "Wardrobe", "Dresser", "Chest", "Barrel", "Mirror_Standing", "Coat_Rack", "Clock_Grandfather", "Clock_Wall", "Lamp_Floor", "Lamp_Table",
               "Chandelier", "Candle_Stick", "Rug_Round", "Rug_Long", "Fireplace", "Piano", "Harp", "Easel", "Globe", "Vase", "Plant_Pot", "Bathroom_Cabinet",
               "Trunk_Travel", "Hat_Stand", "Cradle", "Television", "Radio", "Sewing_Machine", "Washboard", "Broom", "Bucket_House", "Ladder", "Window_Frame", "Door_Frame"):
        if n == "Bookshelf":
            box(o, -3, -1, 0, 6, 2, 12, "oak")
            for z in (1, 4, 7, 10):
                for x in range(-2, 3):
                    box(o, x, 0, z, 1, 1, 2, ("book_r", "book_b", "book_g", "paper")[(x + z) % 4])
        elif n in ("Wardrobe", "Dresser", "Bathroom_Cabinet"):
            h = {"Wardrobe": 16, "Dresser": 8, "Bathroom_Cabinet": 6}[n]
            box(o, -3, -2, 0, 6, 4, h, "oak")
            for z in range(2, h, 3):
                box(o, -1, 2, z, 1, 1, 1, "brass")
                box(o, 1, 2, z, 1, 1, 1, "brass")
        elif n in ("Chest", "Trunk_Travel"):
            box(o, -3, -2, 0, 6, 4, 4, "oak_d" if n == "Chest" else "leather")
            box(o, -3, -2, 4, 6, 4, 1, "oak" if n == "Chest" else "brass")
            box(o, 0, 2, 2, 1, 1, 1, "brass")
        elif n == "Barrel":
            for z in range(0, 6):
                box(o, -2, -2, z, 4, 4, 1, "trunk" if z % 2 else "metal_k")
        elif n == "Mirror_Standing":
            box(o, -2, 0, 0, 5, 1, 1, "oak")
            box(o, -2, 0, 1, 5, 1, 9, "oak")
            box(o, -1, 0, 2, 3, 1, 7, "mirror")
        elif n in ("Coat_Rack", "Hat_Stand"):
            box(o, 0, 0, 0, 1, 1, 12, "oak")
            box(o, -2, -2, 0, 5, 5, 1, "oak_d")
            for (dx, dy) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                box(o, dx, dy, 10, 1, 1, 1, "brass")
            box(o, -1, -1, 12, 3, 3, 1, "fur_k" if n == "Hat_Stand" else "blanket")
        elif n == "Clock_Grandfather":
            box(o, -2, -1, 0, 4, 2, 16, "oak_d")
            box(o, -1, 1, 12, 2, 1, 2, "paper")
            box(o, 0, 1, 5, 1, 1, 6, "brass")
        elif n == "Clock_Wall":
            box(o, -2, 0, 0, 5, 1, 5, "oak")
            box(o, -1, 1, 1, 3, 1, 3, "paper")
            box(o, 0, 1, 2, 1, 1, 2, "metal_k")
        elif n in ("Lamp_Floor", "Lamp_Table"):
            h = 12 if n == "Lamp_Floor" else 5
            box(o, 0, 0, 0, 1, 1, h, "brass")
            box(o, -2, -2, h, 5, 5, 3, "linen")
            box(o, -1, -1, h + 1, 3, 3, 1, "flame")
        elif n == "Chandelier":
            box(o, 0, 0, 10, 1, 1, 4, "brass")
            box(o, -4, -4, 8, 9, 9, 1, "brass")
            for (dx, dy) in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                box(o, dx, dy, 9, 1, 1, 1, "candle_w")
                box(o, dx, dy, 10, 1, 1, 1, "flame")
        elif n == "Candle_Stick":
            box(o, -1, -1, 0, 3, 3, 1, "brass")
            box(o, 0, 0, 1, 1, 1, 3, "candle_w")
            box(o, 0, 0, 4, 1, 1, 1, "flame")
        elif n in ("Rug_Round", "Rug_Long"):
            if n == "Rug_Round":
                for x in range(-5, 6):
                    for y in range(-5, 6):
                        if x * x + y * y <= 25:
                            box(o, x, y, 0, 1, 1, 1, "rug_r" if x * x + y * y > 9 else "rug_y")
            else:
                box(o, -8, -3, 0, 16, 6, 1, "rug_r")
                box(o, -7, -2, 0, 14, 4, 1, "rug_y")
        elif n == "Fireplace":
            box(o, -5, -2, 0, 10, 3, 10, "stone")
            box(o, -3, -1, 0, 6, 3, 5, "cave")
            box(o, -2, 0, 0, 4, 1, 2, "forge")
            box(o, -1, 0, 2, 2, 1, 1, "flame")
            box(o, -5, -2, 10, 10, 4, 1, "oak")
        elif n == "Piano":
            box(o, -7, -3, 0, 14, 6, 8, "fur_k")
            box(o, -6, 3, 6, 12, 1, 1, "porcelain")
            for x in range(-6, 6, 2):
                box(o, x, 3, 7, 1, 1, 1, "fur_k")
            box(o, -2, 6, 0, 4, 2, 5, "fur_k")
        elif n == "Harp":
            box(o, 0, -3, 0, 1, 7, 1, "brass")
            box(o, 0, -3, 0, 1, 1, 14, "brass")
            for y in range(-2, 4):
                box(o, 0, y, 1, 1, 1, 12 - y * 2, "pole")
        elif n == "Easel":
            box(o, -2, 0, 0, 1, 1, 12, "oak")
            box(o, 2, 0, 0, 1, 1, 12, "oak")
            box(o, 0, 1, 0, 1, 1, 10, "oak")
            box(o, -3, 0, 4, 7, 1, 7, "paper")
            box(o, -1, -1, 6, 3, 1, 3, "flower_b")
        elif n == "Globe":
            box(o, -1, -1, 0, 3, 3, 1, "oak_d")
            ball(o, 0, 0, 4, 2, "sea_e" if "sea_e" in PAL else "feather_b", "leaf", "patches")
        elif n in ("Vase", "Plant_Pot"):
            box(o, -1, -1, 0, 3, 3, 4 if n == "Vase" else 3, "pitcher_r" if n == "Vase" else "copper_e" if "copper_e" in PAL else "rust")
            if n == "Vase":
                box(o, 0, 0, 4, 1, 1, 3, "stem")
                box(o, 0, 0, 7, 1, 1, 1, "flower_r")
            else:
                box(o, -1, -1, 3, 3, 3, 2, "leaf_l")
        elif n == "Cradle":
            box(o, -2, -3, 1, 4, 6, 1, "linen_w")
            box(o, -2, -3, 2, 1, 6, 2, "oak")
            box(o, 1, -3, 2, 1, 6, 2, "oak")
            box(o, -3, -1, 0, 6, 1, 1, "oak_d")
        elif n == "Television":
            box(o, -4, 0, 2, 8, 1, 5, "metal_k")
            box(o, -3, 1, 3, 6, 1, 3, "screen")
            box(o, -1, 0, 0, 2, 1, 2, "metal_k")
        elif n == "Radio":
            box(o, -2, -1, 0, 4, 2, 3, "oak")
            box(o, -1, 1, 1, 2, 1, 1, "net")
            box(o, 1, 0, 3, 1, 1, 3, "chrome")
        elif n == "Sewing_Machine":
            box(o, -3, -1, 0, 6, 2, 1, "oak")
            box(o, -2, 0, 1, 1, 1, 4, "metal_k")
            box(o, -2, 0, 4, 5, 1, 1, "metal_k")
            box(o, 2, 0, 1, 1, 1, 3, "metal_k")
        elif n == "Washboard":
            box(o, -2, 0, 0, 4, 1, 8, "oak")
            for z in range(1, 7, 2):
                box(o, -1, 1, z, 2, 1, 1, "chrome")
        elif n == "Broom":
            box(o, 0, 0, 3, 1, 1, 10, "oak")
            box(o, -1, -1, 0, 3, 3, 3, "hay")
        elif n == "Bucket_House":
            box(o, -1, -1, 0, 3, 3, 3, "tin")
            box(o, -1, 0, 3, 3, 1, 1, "metal_k")
        elif n == "Ladder":
            box(o, -1, 0, 0, 1, 1, 14, "oak")
            box(o, 2, 0, 0, 1, 1, 14, "oak")
            for z in range(1, 14, 2):
                box(o, 0, 0, z, 2, 1, 1, "oak_d")
        elif n == "Window_Frame":
            box(o, -3, 0, 0, 7, 1, 1, "oak")
            box(o, -3, 0, 7, 7, 1, 1, "oak")
            box(o, -3, 0, 1, 1, 1, 6, "oak")
            box(o, 3, 0, 1, 1, 1, 6, "oak")
            box(o, -2, 0, 1, 5, 1, 6, "glass")
            box(o, 0, 0, 1, 1, 1, 6, "oak")
        else:
            box(o, -3, 0, 0, 1, 1, 12, "oak")
            box(o, 3, 0, 0, 1, 1, 12, "oak")
            box(o, -3, 0, 12, 7, 1, 1, "oak")
            box(o, -2, 0, 0, 5, 1, 12, "door")
            box(o, 1, 1, 5, 1, 1, 1, "brass")
    return o


def grave(n):
    o = []
    if n in ("Tombstone_Round", "Tombstone_Cross", "Tombstone_Slab", "Tombstone_Obelisk", "Tombstone_Angel", "Tombstone_Broken", "Tombstone_Mossy", "Tombstone_Ornate", "Tombstone_Skull", "Tombstone_Tilted"):
        g = "granite"
        if n == "Tombstone_Round":
            box(o, -2, 0, 0, 5, 2, 5, g)
            for x in range(-1, 2):
                box(o, x, 0, 5, 1, 2, 1, g)
            box(o, 0, 0, 6, 1, 2, 1, g)
            box(o, -1, 2, 2, 3, 1, 2, "granite2")
        elif n == "Tombstone_Cross":
            box(o, -1, 0, 0, 3, 2, 2, g)
            box(o, 0, 0, 2, 1, 2, 7, g)
            box(o, -2, 0, 6, 5, 2, 1, g)
        elif n == "Tombstone_Slab":
            box(o, -3, -4, 0, 6, 8, 1, g)
            box(o, -2, 3, 1, 4, 1, 3, g)
        elif n == "Tombstone_Obelisk":
            box(o, -2, -2, 0, 4, 4, 1, g)
            for z in range(1, 12):
                r = 1 if z < 10 else 0
                box(o, -r, -r, z, 2 * r + 1 if r else 1, 2 * r + 1 if r else 1, 1, g if z % 3 else "granite2")
        elif n == "Tombstone_Angel":
            box(o, -2, -2, 0, 4, 4, 3, g)
            box(o, -1, -1, 3, 2, 2, 5, "marble_g")
            box(o, -1, -1, 8, 2, 2, 2, "marble_g")
            box(o, -4, 0, 5, 3, 1, 3, "marble_g")
            box(o, 1, 0, 5, 3, 1, 3, "marble_g")
        elif n == "Tombstone_Broken":
            box(o, -2, 0, 0, 5, 2, 3, g)
            box(o, -2, 0, 3, 2, 2, 2, g)
            box(o, 1, 2, 0, 3, 2, 1, "granite2")
        elif n == "Tombstone_Mossy":
            box(o, -2, 0, 0, 5, 2, 5, g)
            box(o, -2, 0, 5, 5, 2, 1, "moss_g")
            box(o, -2, 2, 0, 2, 1, 3, "moss_g")
            box(o, 1, 2, 3, 2, 1, 2, "ivy")
        elif n == "Tombstone_Ornate":
            box(o, -3, 0, 0, 7, 2, 1, "marble_g")
            box(o, -2, 0, 1, 5, 2, 6, "marble_g")
            box(o, -3, 0, 7, 7, 2, 1, "marble_g")
            box(o, 0, 0, 8, 1, 2, 2, "gold_e" if "gold_e" in PAL else "brass")
            box(o, -1, 2, 2, 3, 1, 3, "granite2")
        elif n == "Tombstone_Skull":
            box(o, -2, 0, 0, 5, 2, 5, "granite2")
            box(o, -1, 2, 2, 3, 1, 2, "skull")
            box(o, -1, 3, 3, 1, 1, 1, "cave")
            box(o, 1, 3, 3, 1, 1, 1, "cave")
        else:
            for z in range(0, 5):
                box(o, -2 + z // 2, 0, z, 5, 2, 1, g)
    elif n in ("Grave_Mound", "Grave_Open", "Coffin", "Coffin_Open", "Mausoleum", "Crypt_Door", "Urn", "Iron_Fence", "Iron_Gate", "Lantern_Grave", "Skull_Pile", "Bone_Pile", "Dead_Flowers", "Raven_Perch", "Ghost_Wisp", "Gravedigger_Shovel", "Cauldron", "Hanging_Lantern", "Witch_Hat_Stone"):
        if n == "Grave_Mound":
            for x in range(-2, 3):
                box(o, x, -4, 0, 1, 8, 2 - abs(x) // 2, "soil_g")
            box(o, -1, 3, 2, 3, 1, 3, "granite")
        elif n == "Grave_Open":
            box(o, -3, -5, -3, 6, 10, 1, "soil_g")
            for x in (-3, 2):
                box(o, x, -5, -3, 1, 10, 3, "soil_g")
            box(o, -3, -5, -3, 6, 1, 3, "soil_g")
            box(o, -3, 4, -3, 6, 1, 3, "soil_g")
            box(o, 3, -3, 0, 3, 6, 2, "soil_g")
        elif n.startswith("Coffin"):
            box(o, -3, -7, 0, 6, 14, 3, "oak_d")
            box(o, -4, -3, 0, 8, 6, 3, "oak_d")
            if n == "Coffin_Open":
                box(o, -2, -6, 1, 4, 12, 1, "velvet" if "velvet" in PAL else "cushion_r")
                box(o, 3, -7, 0, 1, 14, 6, "oak_d")
            else:
                box(o, -4, -3, 3, 8, 6, 1, "oak")
                box(o, -3, -7, 3, 6, 14, 1, "oak")
        elif n == "Mausoleum":
            box(o, -6, -6, 0, 12, 12, 9, "marble_g")
            box(o, -2, 6, 0, 4, 1, 6, "iron_g")
            for x in (-5, -2, 1, 4):
                box(o, x, -7, 0, 1, 1, 9, "granite")
            box(o, -7, -7, 9, 14, 14, 1, "granite")
            box(o, -1, -1, 10, 2, 2, 2, "granite2")
        elif n == "Crypt_Door":
            box(o, -3, 0, 0, 7, 1, 1, "granite")
            box(o, -3, 0, 1, 1, 1, 8, "granite")
            box(o, 3, 0, 1, 1, 1, 8, "granite")
            box(o, -3, 0, 9, 7, 1, 1, "granite")
            box(o, -2, 0, 1, 5, 1, 8, "iron_g")
        elif n == "Urn":
            box(o, -1, -1, 0, 3, 3, 1, "granite")
            for z in range(1, 6):
                r = 2 if 2 <= z <= 4 else 1
                box(o, -r, -r, z, 2 * r + 1, 2 * r + 1, 1, "marble_g")
        elif n == "Iron_Fence":
            box(o, -5, 0, 0, 11, 1, 1, "iron_g")
            box(o, -5, 0, 4, 11, 1, 1, "iron_g")
            for x in range(-5, 6, 2):
                box(o, x, 0, 0, 1, 1, 6, "iron_g")
        elif n == "Iron_Gate":
            for x in (-4, 4):
                box(o, x, 0, 0, 1, 1, 9, "granite")
            box(o, -4, 0, 9, 9, 1, 1, "iron_g")
            for x in range(-3, 4):
                box(o, x, 0, 0, 1, 1, 7 - abs(x) // 2, "iron_g")
        elif n in ("Lantern_Grave", "Hanging_Lantern"):
            if n == "Hanging_Lantern":
                box(o, 0, 0, 0, 1, 1, 9, "iron_g")
                box(o, 0, 0, 9, 4, 1, 1, "iron_g")
                box(o, 2, -1, 5, 3, 3, 4, "iron_g")
                box(o, 3, 0, 6, 1, 1, 2, "flame")
            else:
                box(o, -1, -1, 0, 3, 3, 1, "granite")
                box(o, -1, -1, 1, 3, 3, 4, "iron_g")
                box(o, 0, 0, 2, 1, 1, 2, "flame")
        elif n in ("Skull_Pile", "Bone_Pile"):
            for (dx, dy, dz) in ((0, 0, 0), (2, 0, 0), (-2, 1, 0), (1, -2, 0), (1, 0, 2), (-1, -1, 2)):
                if n == "Skull_Pile":
                    box(o, dx - 1, dy - 1, dz, 2, 2, 2, "skull")
                    box(o, dx - 1, dy, dz + 1, 1, 1, 1, "cave")
                else:
                    box(o, dx - 2, dy, dz, 5, 1, 1, "bone_e" if "bone_e" in PAL else "skull")
        elif n == "Dead_Flowers":
            for (dx, dy) in ((0, 0), (1, 1), (-1, 0)):
                box(o, dx, dy, 0, 1, 1, 3, "bark_e" if "bark_e" in PAL else "trunk")
                box(o, dx, dy, 3, 1, 1, 1, "granite2")
        elif n == "Raven_Perch":
            box(o, 0, 0, 0, 1, 1, 10, "bark_k" if "bark_k" in PAL else "trunk")
            box(o, -2, 0, 7, 5, 1, 1, "trunk")
            box(o, 1, 0, 8, 2, 1, 2, "feather_k")
            box(o, 3, 0, 9, 1, 1, 1, "beak")
        elif n == "Ghost_Wisp":
            for z in range(0, 6):
                r = 1 if z < 4 else 2
                box(o, -r, -r, z, 2 * r + 1, 2 * r + 1, 1, "ghost")
            box(o, -1, 2, 4, 1, 1, 1, "cave")
            box(o, 1, 2, 4, 1, 1, 1, "cave")
        elif n == "Gravedigger_Shovel":
            box(o, 0, 0, 2, 1, 1, 9, "oak")
            box(o, -1, 0, 0, 3, 1, 3, "metal")
            box(o, -2, -2, -1, 5, 4, 1, "soil_g")
        elif n == "Cauldron":
            box(o, -2, -2, 1, 4, 4, 4, "metal_k")
            box(o, -1, -1, 4, 2, 2, 1, "glow")
            for (dx, dy) in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
                box(o, dx, dy, 0, 1, 1, 1, "metal_k")
            box(o, 0, 0, 5, 1, 1, 2, "smoke2")
        else:
            box(o, -2, 0, 0, 5, 2, 4, "granite2")
            for z in range(4, 9):
                r = 2 - (z - 4) // 2
                box(o, -r, 0, z, 2 * r + 1, 2, 1, "fur_k")
            box(o, -3, 0, 4, 7, 2, 1, "fur_k")
    return o


def sport(n):
    o = []
    if n == "Baseball":
        ball(o, 0, 0, 1, 1, "baseball", "stitch", "stitch")
    elif n == "Baseball_Bat":
        for y in range(0, 10):
            box(o, 0, y, 0, 1, 1, 1, "bat" if y > 2 else "oak_d")
            if y > 5:
                box(o, 0, y, 1, 1, 1, 1, "bat")
    elif n == "Baseball_Glove":
        box(o, -2, -1, 0, 4, 2, 3, "glove")
        for x in range(-2, 2):
            box(o, x, 0, 3, 1, 1, 2, "glove")
        box(o, 2, 0, 1, 1, 1, 2, "glove")
    elif n in ("Base_Plate", "Home_Plate", "Pitchers_Mound"):
        if n == "Pitchers_Mound":
            for x in range(-4, 5):
                for y in range(-4, 5):
                    if x * x + y * y <= 16:
                        box(o, x, y, 0, 1, 1, 1 if x * x + y * y > 4 else 2, "dirt2")
            box(o, -1, 0, 2, 2, 1, 1, "porcelain")
        else:
            box(o, -1, -1, 0, 3 if n == "Base_Plate" else 4, 3, 1, "porcelain")
    elif n == "Backstop":
        for x in range(-6, 7, 2):
            box(o, x, 0, 0, 1, 1, 12, "metal_k")
        for z in range(1, 12, 2):
            box(o, -6, 0, z, 13, 1, 1, "net")
    elif n == "Batting_Helmet":
        ball(o, 0, 0, 2, 2, "paint_b")
        box(o, -2, 2, 1, 5, 2, 1, "paint_b")
    elif n == "Basketball":
        ball(o, 0, 0, 1, 1, "basketball", "fur_k", "lines")
    elif n == "Basketball_Hoop":
        box(o, 0, 0, 0, 1, 1, 24, "pole")
        box(o, -6, 0, 20, 13, 1, 8, "glass" if "glass" in PAL else "porcelain")
        box(o, -2, 0, 21, 5, 1, 3, "paint_r")
        for a in range(0, 360, 30):
            x, y = int(round(3 * math.cos(math.radians(a)))), int(round(3 * math.sin(math.radians(a))))
            box(o, x, y + 4, 21, 1, 1, 1, "basketball")
            box(o, x, y + 4, 17, 1, 1, 4, "net")
    elif n == "Football":
        for y in range(-3, 4):
            r = 2 - abs(y) // 2
            box(o, -r, y, 0, 2 * r + 1, 1, 2 * r + 1, "football")
        for y in range(-2, 3):
            box(o, 0, y, 4 if abs(y) < 1 else 3, 1, 1, 1, "soccer_w")
    elif n == "Goalpost":
        box(o, 0, 0, 0, 1, 1, 10, "paint_y")
        box(o, -8, 0, 10, 17, 1, 1, "paint_y")
        box(o, -8, 0, 10, 1, 1, 16, "paint_y")
        box(o, 8, 0, 10, 1, 1, 16, "paint_y")
    elif n in ("Soccer_Ball", "Volleyball", "Dodgeball_Red", "Dodgeball_Blue", "Dodgeball_Yellow", "Tennis_Ball", "Golf_Ball", "Bowling_Ball", "Beach_Ball", "Rugby_Ball", "Softball"):
        c = {"Soccer_Ball": ("soccer_w", "soccer_k", "patches", 2), "Volleyball": ("volley", "paint_b", "lines", 2), "Dodgeball_Red": ("dodge_r", "dodge_r", "none", 2),
             "Dodgeball_Blue": ("dodge_b", "dodge_b", "none", 2), "Dodgeball_Yellow": ("dodge_y", "dodge_y", "none", 2), "Tennis_Ball": ("tennis", "soccer_w", "lines", 1),
             "Golf_Ball": ("golf_w", "golf_w", "none", 1), "Bowling_Ball": ("bowl_ball", "bowl_ball", "none", 2), "Beach_Ball": ("soccer_w", "dodge_r", "patches", 3),
             "Rugby_Ball": ("football", "soccer_w", "stitch", 2), "Softball": ("tennis", "stitch", "stitch", 1)}[n]
        ball(o, 0, 0, c[3], c[3], c[0], c[1], c[2])
    elif n == "Soccer_Goal":
        for x in (-10, 10):
            box(o, x, 0, 0, 1, 1, 7, "pole")
        box(o, -10, 0, 7, 21, 1, 1, "pole")
        for x in range(-10, 11, 2):
            box(o, x, -3, 0, 1, 4, 1, "net")
            box(o, x, -3, 0, 1, 1, 7, "net")
    elif n == "Volleyball_Net":
        for x in (-12, 12):
            box(o, x, 0, 0, 1, 1, 24, "pole")
        for z in range(14, 24, 2):
            box(o, -12, 0, z, 25, 1, 1, "net")
        box(o, -12, 0, 23, 25, 1, 1, "soccer_w")
    elif n == "Tennis_Racket":
        box(o, 0, 0, 0, 1, 1, 6, "oak_d")
        for a in range(0, 360, 20):
            x, z = int(round(3 * math.cos(math.radians(a)))), 9 + int(round(4 * math.sin(math.radians(a))))
            box(o, x, 0, z, 1, 1, 1, "chrome")
        for z in range(6, 13, 2):
            box(o, -2, 0, z, 5, 1, 1, "net")
    elif n == "Tennis_Net":
        for x in (-10, 10):
            box(o, x, 0, 0, 1, 1, 10, "pole")
        for z in range(1, 10, 2):
            box(o, -10, 0, z, 21, 1, 1, "net")
        box(o, -10, 0, 10, 21, 1, 1, "soccer_w")
    elif n == "Golf_Club":
        box(o, 0, 0, 1, 1, 1, 10, "chrome")
        box(o, 0, 0, 0, 3, 1, 1, "chrome")
    elif n == "Golf_Flag":
        box(o, 0, 0, 0, 1, 1, 14, "pole")
        box(o, 1, 0, 11, 4, 1, 3, "flag_r")
        for x in range(-2, 3):
            for y in range(-2, 3):
                if x * x + y * y <= 4:
                    box(o, x, y, -1, 1, 1, 1, "cave")
    elif n == "Hockey_Stick":
        box(o, 0, 0, 0, 1, 1, 12, "oak")
        box(o, 0, 0, 0, 4, 1, 1, "oak_d")
    elif n == "Hockey_Puck":
        ball(o, 0, 0, 0, 1, "puck")
    elif n == "Hockey_Goal":
        for x in (-6, 6):
            box(o, x, 0, 0, 1, 1, 5, "paint_r")
        box(o, -6, 0, 5, 13, 1, 1, "paint_r")
        for x in range(-6, 7, 2):
            box(o, x, -3, 0, 1, 4, 1, "net")
    elif n == "Frisbee":
        for x in range(-2, 3):
            for y in range(-2, 3):
                if x * x + y * y <= 5:
                    box(o, x, y, 0, 1, 1, 1, "frisbee")
    elif n == "Skateboard":
        box(o, -4, -1, 1, 9, 3, 1, "oak")
        for x in (-3, 2):
            for y in (-1, 1):
                box(o, x, y, 0, 1, 1, 1, "tyre")
    elif n == "Bowling_Pin":
        for z in range(0, 6):
            r = 1 if z < 3 or z == 5 else 0
            box(o, -r, -r, z, 2 * r + 1, 2 * r + 1, 1, "bowl_pin" if z != 3 else "paint_r")
    elif n == "Boxing_Glove":
        ball(o, 0, 0, 2, 2, "dodge_r")
        box(o, -1, -3, 0, 3, 2, 3, "dodge_r")
    elif n == "Archery_Target":
        for r in range(0, 5):
            for x in range(-4, 5):
                for z in range(-4, 5):
                    if x * x + z * z <= (5 - r) ** 2 - 1:
                        box(o, x, 0, 5 + z, 1, 1, 1, ("soccer_w", "paint_r", "paint_b", "soccer_w", "paint_y")[r])
        box(o, -3, 1, 0, 1, 1, 6, "oak")
        box(o, 3, 1, 0, 1, 1, 6, "oak")
    elif n == "Bow":
        for z in range(0, 10):
            box(o, 2 - abs(z - 5) // 2, 0, z, 1, 1, 1, "oak")
        box(o, 0, 0, 0, 1, 1, 10, "net")
    elif n == "Bicycle":
        for cx in (-4, 4):
            for a in range(0, 360, 15):
                box(o, cx + int(round(3 * math.cos(math.radians(a)))), 0, 3 + int(round(3 * math.sin(math.radians(a)))), 1, 1, 1, "tyre")
        box(o, -4, 0, 3, 9, 1, 1, "paint_r")
        box(o, -1, 0, 3, 1, 1, 4, "paint_r")
        box(o, -2, -1, 7, 3, 3, 1, "fur_k")
        box(o, 3, -1, 6, 1, 3, 1, "chrome")
    elif n == "Ping_Pong_Table":
        box(o, -7, -4, 4, 14, 8, 1, "paint_g")
        box(o, -7, 0, 5, 14, 1, 1, "net")
        for (x, y) in ((-6, -3), (5, -3), (-6, 2), (5, 2)):
            box(o, x, y, 0, 1, 1, 4, "metal_k")
    elif n == "Surfboard":
        for y in range(-8, 9):
            r = 1 if abs(y) < 6 else 0
            box(o, -r, y, 0, 2 * r + 1, 1, 1, "surf" if y % 4 else "soccer_w")
    elif n == "Kayak":
        for y in range(-10, 11):
            r = 2 if abs(y) < 7 else 1
            box(o, -r, y, 0, 2 * r + 1, 1, 2, "kayak")
        box(o, -1, -3, 1, 3, 6, 1, "cave")
    elif n == "Paddle":
        box(o, 0, 0, 0, 1, 1, 10, "oak")
        box(o, -1, 0, 10, 3, 1, 4, "oak_d")
    elif n == "Fishing_Rod":
        box(o, 0, 0, 0, 1, 1, 16, "oak")
        box(o, 1, 0, 14, 1, 1, 1, "net")
        box(o, 1, 0, 8, 1, 1, 6, "net")
        box(o, 1, 0, 7, 1, 1, 1, "dodge_r")
    elif n == "Trophy":
        box(o, -1, -1, 0, 3, 3, 1, "oak_d")
        box(o, 0, 0, 1, 1, 1, 2, "trophy")
        box(o, -2, -2, 3, 5, 5, 3, "trophy")
        box(o, -3, 0, 4, 1, 1, 2, "trophy")
        box(o, 3, 0, 4, 1, 1, 2, "trophy")
    elif n == "Scoreboard":
        box(o, -6, 0, 10, 13, 1, 6, "metal_k")
        box(o, -5, 1, 11, 5, 1, 4, "screen")
        box(o, 1, 1, 11, 5, 1, 4, "screen")
        box(o, -4, 1, 12, 1, 1, 2, "paint_y")
        box(o, 2, 1, 12, 1, 1, 2, "paint_y")
        box(o, -1, 0, 0, 3, 1, 10, "pole")
    elif n == "Bleachers":
        for i in range(4):
            box(o, -8, -i * 2 - 2, i * 2, 17, 2, 2, "oak" if i % 2 else "oak_d")
    elif n == "Court_Cone":
        for z in range(0, 4):
            r = 2 - z // 2
            box(o, -r, -r, z, 2 * r + 1, 2 * r + 1, 1, "basketball" if z != 2 else "soccer_w")
    elif n == "Jump_Rope":
        for a in range(0, 180, 10):
            x, z = int(round(5 * math.cos(math.radians(a)))), int(round(4 * math.sin(math.radians(a))))
            box(o, x, 0, z, 1, 1, 1, "dodge_r")
        box(o, -5, 0, 0, 1, 1, 2, "oak")
        box(o, 5, 0, 0, 1, 1, 2, "oak")
    elif n == "Swing_Set":
        for x in (-6, 6):
            box(o, x, -2, 0, 1, 1, 14, "oak")
            box(o, x, 2, 0, 1, 1, 14, "oak")
        box(o, -6, 0, 14, 13, 1, 1, "oak_d")
        for x in (-3, 2):
            box(o, x, 0, 4, 1, 1, 10, "net")
            box(o, x - 1, 0, 3, 3, 1, 1, "oak")
    elif n == "Seesaw":
        box(o, -1, -1, 0, 3, 3, 2, "oak_d")
        for x in range(-7, 8):
            box(o, x, 0, 2 + x // 4, 1, 1, 1, "paint_y")
    elif n == "Sandbox":
        for x in range(-4, 5):
            for y in range(-4, 5):
                box(o, x, y, 0, 1, 1, 1, "sand_e" if "sand_e" in PAL else "sand")
                if abs(x) == 4 or abs(y) == 4:
                    box(o, x, y, 1, 1, 1, 1, "oak")
        box(o, 1, 1, 1, 1, 1, 1, "tin")
    return o


HOUSE = ("Bed", "Bed_Bunk", "Crib", "Table", "Table_Round", "Desk", "Nightstand", "Coffee_Table", "Chair", "Stool", "Armchair", "Sofa", "Bench_Indoor", "Rocking_Chair",
         "Bathtub", "Bathtub_Clawfoot", "Shower", "Toilet", "Sink", "Sink_Kitchen", "Washbasin", "Towel_Rack", "Bath_Mat", "Stove", "Fridge", "Oven_Brick", "Kitchen_Counter",
         "Cupboard", "Kettle", "Pot", "Pan", "Cutting_Board", "Dish_Rack", "Bread_Oven", "Bookshelf", "Wardrobe", "Dresser", "Chest", "Barrel", "Mirror_Standing", "Coat_Rack",
         "Clock_Grandfather", "Clock_Wall", "Lamp_Floor", "Lamp_Table", "Chandelier", "Candle_Stick", "Rug_Round", "Rug_Long", "Fireplace", "Piano", "Harp", "Easel", "Globe",
         "Vase", "Plant_Pot", "Bathroom_Cabinet", "Trunk_Travel", "Hat_Stand", "Cradle", "Television", "Radio", "Sewing_Machine", "Washboard", "Broom", "Bucket_House", "Ladder",
         "Window_Frame", "Door_Frame")
GRAVE = ("Tombstone_Round", "Tombstone_Cross", "Tombstone_Slab", "Tombstone_Obelisk", "Tombstone_Angel", "Tombstone_Broken", "Tombstone_Mossy", "Tombstone_Ornate",
         "Tombstone_Skull", "Tombstone_Tilted", "Grave_Mound", "Grave_Open", "Coffin", "Coffin_Open", "Mausoleum", "Crypt_Door", "Urn", "Iron_Fence", "Iron_Gate",
         "Lantern_Grave", "Skull_Pile", "Bone_Pile", "Dead_Flowers", "Raven_Perch", "Ghost_Wisp", "Gravedigger_Shovel", "Cauldron", "Hanging_Lantern", "Witch_Hat_Stone")
SPORT = ("Baseball", "Baseball_Bat", "Baseball_Glove", "Base_Plate", "Home_Plate", "Pitchers_Mound", "Backstop", "Batting_Helmet", "Basketball", "Basketball_Hoop",
         "Football", "Goalpost", "Soccer_Ball", "Soccer_Goal", "Volleyball", "Volleyball_Net", "Dodgeball_Red", "Dodgeball_Blue", "Dodgeball_Yellow", "Tennis_Ball",
         "Tennis_Racket", "Tennis_Net", "Golf_Ball", "Golf_Club", "Golf_Flag", "Hockey_Stick", "Hockey_Puck", "Hockey_Goal", "Frisbee", "Skateboard", "Bowling_Ball",
         "Bowling_Pin", "Boxing_Glove", "Archery_Target", "Bow", "Bicycle", "Ping_Pong_Table", "Surfboard", "Kayak", "Paddle", "Fishing_Rod", "Trophy", "Scoreboard",
         "Bleachers", "Court_Cone", "Jump_Rope", "Swing_Set", "Seesaw", "Sandbox", "Beach_Ball", "Rugby_Ball", "Softball")
CATALOG = {}
for h in HOUSE:
    CATALOG["Prop_House_" + h] = ("house", 10.0)
for g in GRAVE:
    CATALOG["Prop_Grave_" + g] = ("grave", 10.0)
for s_ in SPORT:
    CATALOG["Prop_Sport_" + s_] = ("sport", 10.0)


def plan(name):
    fam, _ = CATALOG[name]
    short = name.split("_", 2)[2]
    return {"house": house, "grave": grave, "sport": sport}[fam](short)


def build(name, out_dir):
    import bpy
    import json
    voxels = plan(name)
    fam, cm = CATALOG[name]
    ob = V._mesh_from_voxels(name, voxels, scale=cm, pal=PAL)
    zmin = min(z for _, _, z, _ in voxels)
    for v in ob.data.vertices:
        v.co.z -= zmin * cm
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "family": fam, "voxel_cm": cm, "voxels": len(voxels), "pivot": "bottom-centre",
                   "throwable": fam == "sport" and ("Ball" in name or name.endswith(("Baseball", "Football", "Frisbee", "Puck", "Softball")))}, f, indent=1)
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
