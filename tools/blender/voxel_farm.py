# SPDX-License-Identifier: MIT
"""Farm machines, buildings, tools and crops (Richey 15:04: "machines, tractors and everything we need for farming,
and all the farm plants and stuff associated with farms"). Static voxel props in the dresser naming scheme
(`Prop_Machine_*`, `Prop_Farm_*`, `Prop_Crop_*`), 25 cm voxels for machines/buildings, 10 cm for crops/tools,
bottom-centre pivot. Vehicles keep their wheels as a separate `_Wheels` mesh so Unreal can spin them.

    import voxel_farm as FM
    FM.CATALOG; FM.plan(name) -> {part: voxels}; FM.build_all(out_dir)
"""
import math
import os
import random

import voxel_flora as F
import voxel_island as V

PAL = dict(F.PAL)
PAL.update({"paint_r": (0.80, 0.15, 0.15), "paint_g": (0.20, 0.55, 0.25), "paint_b": (0.20, 0.40, 0.80), "paint_y": (0.95, 0.75, 0.15),
            "tyre": (0.10, 0.10, 0.11), "rim": (0.85, 0.85, 0.80), "glass": (0.70, 0.85, 0.95), "metal": (0.55, 0.58, 0.62), "metal_k": (0.25, 0.26, 0.30),
            "rust": (0.60, 0.35, 0.20), "wood_l": (0.80, 0.65, 0.42), "tomato": (0.90, 0.20, 0.15), "potato": (0.75, 0.62, 0.40), "lettuce": (0.55, 0.80, 0.35),
            "strawberry": (0.90, 0.15, 0.25), "grape": (0.45, 0.25, 0.55), "melon": (0.30, 0.55, 0.25), "onion": (0.85, 0.75, 0.60), "pepper": (0.90, 0.50, 0.10),
            "cotton": (0.97, 0.97, 0.95), "rice": (0.70, 0.78, 0.40), "cane": (0.55, 0.70, 0.30), "hop": (0.60, 0.80, 0.35), "bean": (0.40, 0.65, 0.30),
            "silo": (0.80, 0.80, 0.78), "barn_r": (0.70, 0.18, 0.15), "barn_w": (0.95, 0.95, 0.92), "tin": (0.70, 0.72, 0.75), "honeycomb": (0.95, 0.75, 0.25)})


def box(out, part, x0, y0, z0, w, d, h, c):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + d):
            for z in range(z0, z0 + h):
                out.setdefault(part, []).append((x, y, z, c))


def wheel(out, part, cx, cy, cz, r, w=2):
    for x in range(cx, cx + w):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dy * dy + dz * dz <= r * r:
                    out.setdefault(part, []).append((x, cy + dy, cz + dz, "tyre" if dy * dy + dz * dz > (r - 1) ** 2 else "rim"))


def machine(name):
    out = {}
    n = name
    if n in ("Tractor_Red", "Tractor_Green", "Tractor_Blue", "Tractor_Old"):
        paint = {"Tractor_Red": "paint_r", "Tractor_Green": "paint_g", "Tractor_Blue": "paint_b", "Tractor_Old": "rust"}[n]
        box(out, "body", -3, -6, 3, 7, 12, 4, paint)              # engine + chassis
        box(out, "body", -3, 2, 7, 7, 4, 1, paint)
        box(out, "body", -2, -5, 7, 5, 4, 4, "glass")             # cab
        box(out, "body", -3, -5, 11, 7, 5, 1, paint)
        box(out, "body", 2, 5, 7, 1, 1, 4, "metal_k")             # exhaust stack
        box(out, "body", -1, -1, 7, 2, 1, 1, "metal_k")           # steering wheel
        for sx in (-4, 4):
            wheel(out, "wheels", sx if sx < 0 else sx - 1, -4, 3, 3, 1)      # big rear
            wheel(out, "wheels", sx if sx < 0 else sx - 1, 5, 2, 2, 1)       # small front
    elif n in ("Plough", "Seeder", "Harrow", "Harvester", "Hay_Baler", "Sprayer", "Mower"):
        box(out, "body", -4, -2, 2, 9, 4, 2, "metal")
        box(out, "body", -1, 2, 2, 3, 4, 1, "metal_k")             # hitch
        if n == "Plough":
            for x in range(-4, 5, 2):
                box(out, "body", x, -3, 0, 1, 2, 2, "metal_k")
        elif n == "Seeder":
            box(out, "body", -4, -2, 4, 9, 3, 3, "paint_y")
            for x in range(-4, 5, 2):
                box(out, "body", x, -3, 0, 1, 1, 2, "metal_k")
        elif n == "Harrow":
            for x in range(-4, 5):
                for y in (-3, -1):
                    box(out, "body", x, y, 0, 1, 1, 2, "metal_k")
        elif n == "Harvester":
            box(out, "body", -4, -6, 3, 9, 10, 5, "paint_r")
            box(out, "body", -3, -2, 8, 7, 4, 3, "glass")
            box(out, "body", -6, 4, 1, 13, 2, 3, "metal")           # header
            for x in range(-6, 7, 2):
                box(out, "body", x, 6, 1, 1, 1, 2, "metal_k")
            box(out, "body", 4, -4, 8, 1, 1, 6, "tin")              # auger
            for sx in (-5, 4):
                wheel(out, "wheels", sx, -3, 2, 2, 1)
        elif n == "Hay_Baler":
            box(out, "body", -3, -5, 2, 7, 7, 6, "paint_r")
            box(out, "body", -2, -7, 3, 5, 2, 4, "hay")
            for sx in (-4, 3):
                wheel(out, "wheels", sx, -2, 2, 2, 1)
        elif n == "Sprayer":
            box(out, "body", -2, -2, 4, 5, 4, 4, "glass")
            box(out, "body", -10, -3, 3, 21, 1, 1, "metal")
            for x in range(-10, 11, 3):
                box(out, "body", x, -3, 2, 1, 1, 1, "water")
        else:
            box(out, "body", -5, -3, 1, 11, 3, 1, "paint_r")
        if n not in ("Harvester", "Hay_Baler"):
            for sx in (-5, 4):
                wheel(out, "wheels", sx, 0, 1, 1, 1)
    elif n in ("Wagon", "Hay_Wagon", "Wheelbarrow", "Cart_Milk", "Horse_Cart"):
        if n == "Wheelbarrow":
            box(out, "body", -2, -3, 1, 4, 5, 3, "metal")
            box(out, "body", -1, -2, 2, 2, 3, 2, "soil")
            box(out, "body", -2, -5, 2, 1, 3, 1, "trunk")
            box(out, "body", 1, -5, 2, 1, 3, 1, "trunk")
            wheel(out, "wheels", 0, 3, 1, 1, 1)
        else:
            box(out, "body", -3, -5, 3, 7, 11, 1, "wood_l")
            box(out, "body", -3, -5, 4, 1, 11, 2, "wood_l")
            box(out, "body", 3, -5, 4, 1, 11, 2, "wood_l")
            if n == "Hay_Wagon":
                box(out, "body", -2, -4, 4, 5, 9, 3, "hay")
            if n == "Cart_Milk":
                for y in (-3, 0, 3):
                    box(out, "body", -1, y, 4, 2, 2, 3, "tin")
            if n == "Horse_Cart":
                box(out, "body", -1, 6, 3, 1, 5, 1, "trunk")
                box(out, "body", 1, 6, 3, 1, 5, 1, "trunk")
            for sx in (-4, 3):
                wheel(out, "wheels", sx, -2, 2, 2, 1)
                if n != "Wheelbarrow":
                    wheel(out, "wheels", sx, 3, 2, 2, 1)
    elif n in ("Water_Pump", "Sprinkler", "Irrigation_Pipe", "Windpump", "Water_Tank"):
        if n == "Water_Pump":
            box(out, "body", -1, -1, 0, 2, 2, 4, "metal_k")
            box(out, "body", -1, 1, 3, 2, 2, 1, "metal_k")
            box(out, "body", -2, -1, 4, 1, 1, 3, "paint_r")
            box(out, "body", 0, 2, 2, 1, 1, 1, "water")
        elif n == "Sprinkler":
            box(out, "body", 0, 0, 0, 1, 1, 5, "metal")
            for (dx, dy) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                box(out, "body", dx, dy, 5, 1, 1, 1, "water")
                box(out, "body", dx * 2, dy * 2, 4, 1, 1, 1, "water")
        elif n == "Irrigation_Pipe":
            box(out, "body", -8, 0, 1, 17, 1, 1, "metal")
            for x in range(-8, 9, 4):
                box(out, "body", x, 0, 0, 1, 1, 1, "metal_k")
                box(out, "body", x, -1, 2, 1, 1, 1, "water")
        elif n == "Windpump":
            for z in range(0, 14):
                r = 2 if z < 2 else 1
                box(out, "body", -r, -r, z, 2 * r, 2 * r, 1, "metal_k" if z % 3 else "metal")
            for k in range(-4, 5):
                box(out, "wheels", -1, k, 14 + 0, 1, 1, 1, "tin")
                box(out, "wheels", -1, 0, 14 + k, 1, 1, 1, "tin")
                box(out, "wheels", -1, k, 14 + (4 if k > 0 else -4), 1, 1, 1, "tin")
        else:
            for z in range(0, 6):
                for x in range(-3, 4):
                    for y in range(-3, 4):
                        if abs(x) == 3 or abs(y) == 3:
                            box(out, "body", x, y, z + 1, 1, 1, 1, "tin")
            box(out, "body", -3, -3, 7, 7, 7, 1, "tin")
            box(out, "body", -3, -3, 0, 7, 7, 1, "stone")
    return out


def building(name):
    out = {}
    n = name
    if n in ("Barn_Red", "Barn_White", "Stable", "Cow_Shed"):
        wall = {"Barn_Red": "barn_r", "Barn_White": "barn_w", "Stable": "wood_l", "Cow_Shed": "trunk"}[n]
        W, D, H = 14, 20, 8
        for x in range(-W // 2, W // 2):
            for y in range(-D // 2, D // 2):
                for z in range(0, H):
                    if x in (-W // 2, W // 2 - 1) or y in (-D // 2, D // 2 - 1):
                        c = wall
                        if y == D // 2 - 1 and -2 <= x < 2 and z < 5:
                            c = "door"
                        if z == 4 and x % 4 == 0 and y in (-D // 2, D // 2 - 1) and abs(x) > 2:
                            c = "window"
                        box(out, "body", x, y, z, 1, 1, 1, c)
        for k in range(5):                                        # gambrel roof
            box(out, "body", -W // 2 - 1 + k, -D // 2 - 1, H + k, W + 2 - 2 * k, D + 2, 1, "tin" if n != "Barn_White" else "barn_r")
        box(out, "body", -1, -1, H + 5, 3, 3, 2, "tin")             # cupola
        box(out, "body", 0, 0, H + 7, 1, 1, 2, "metal_k")
        box(out, "body", -1, 0, H + 8, 1, 2, 1, "paint_r")          # weathervane rooster
    elif n in ("Silo", "Silo_Tall"):
        h = 16 if n == "Silo" else 24
        for z in range(0, h):
            for x in range(-3, 4):
                for y in range(-3, 4):
                    if x * x + y * y <= 10 and x * x + y * y > 4:
                        box(out, "body", x, y, z, 1, 1, 1, "silo" if z % 4 else "metal")
        for z in range(0, 3):
            r = 3 - z
            for x in range(-r, r + 1):
                for y in range(-r, r + 1):
                    if x * x + y * y <= r * r + 1:
                        box(out, "body", x, y, h + z, 1, 1, 1, "tin")
    elif n in ("Chicken_Coop", "Beehive", "Beehive_Log", "Greenhouse", "Pig_Pen", "Dovecote", "Tool_Shed", "Root_Cellar", "Smokehouse", "Dairy"):
        if n == "Chicken_Coop":
            box(out, "body", -3, -3, 2, 6, 6, 4, "wood_l")
            box(out, "body", -4, -4, 6, 8, 8, 1, "tin")
            for sx in (-3, 2):
                box(out, "body", sx, -3, 0, 1, 1, 2, "trunk")
                box(out, "body", sx, 2, 0, 1, 1, 2, "trunk")
            box(out, "body", -1, 3, 2, 2, 1, 2, "door")
            box(out, "body", -1, 3, 0, 2, 3, 1, "plank")              # ramp
        elif n == "Beehive":
            box(out, "body", -2, -2, 1, 4, 4, 1, "trunk")
            for z in range(2, 7):
                box(out, "body", -2, -2, z, 4, 4, 1, "barn_w" if z % 2 else "wood_l")
            box(out, "body", -3, -3, 7, 6, 6, 1, "tin")
            box(out, "body", -1, 2, 2, 2, 1, 1, "bee_k")
        elif n == "Beehive_Log":
            for z in range(0, 6):
                box(out, "body", -2, -2, z, 4, 4, 1, "trunk")
            box(out, "body", -1, -1, 6, 2, 2, 1, "honeycomb")
        elif n == "Greenhouse":
            for x in range(-4, 5):
                for y in range(-6, 7):
                    for z in range(0, 6):
                        edge = x in (-4, 4) or y in (-6, 6)
                        if edge or z == 5:
                            box(out, "body", x, y, z, 1, 1, 1, "glass" if (x + y + z) % 4 else "metal")
            for x in range(-3, 4, 2):
                for y in range(-5, 6, 2):
                    box(out, "body", x, y, 0, 1, 1, 1, "soil")
                    box(out, "body", x, y, 1, 1, 1, 1, "tomato" if (x + y) % 4 else "lettuce")
        elif n == "Pig_Pen":
            for x in range(-5, 6):
                for y in range(-5, 6):
                    if (x in (-5, 5) or y in (-5, 5)) and (x + y) % 2 == 0:
                        box(out, "body", x, y, 0, 1, 1, 2, "fence")
            box(out, "body", -3, -3, 0, 6, 6, 1, "dirt2")
            box(out, "body", -1, -1, 0, 3, 3, 1, "water")
        elif n == "Dovecote":
            box(out, "body", 0, 0, 0, 1, 1, 8, "trunk")
            box(out, "body", -2, -2, 8, 5, 5, 3, "barn_w")
            box(out, "body", -3, -3, 11, 7, 7, 1, "tin")
            for (dx, dy) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                box(out, "body", dx, dy, 9, 1, 1, 1, "door")
        elif n == "Tool_Shed":
            box(out, "body", -3, -3, 0, 6, 6, 5, "wood_l")
            box(out, "body", -4, -4, 5, 8, 8, 1, "tin")
            box(out, "body", -1, 3, 0, 2, 1, 3, "door")
            box(out, "body", 3, -2, 0, 1, 1, 4, "iron")               # a rake leaning
        elif n == "Root_Cellar":
            box(out, "body", -3, -3, 0, 6, 5, 2, "soil")
            box(out, "body", -3, -3, 2, 6, 5, 1, "grass")
            box(out, "body", -2, 2, 0, 4, 1, 2, "door")
            box(out, "body", -3, 2, 0, 1, 1, 3, "stone")
            box(out, "body", 2, 2, 0, 1, 1, 3, "stone")
        elif n == "Smokehouse":
            box(out, "body", -2, -2, 0, 4, 4, 6, "stone")
            box(out, "body", -3, -3, 6, 6, 6, 1, "tin")
            box(out, "body", 0, 0, 7, 1, 1, 3, "stone2")
            box(out, "body", 0, 0, 10, 1, 1, 1, "smoke")
        else:
            box(out, "body", -4, -4, 0, 8, 8, 5, "barn_w")
            box(out, "body", -5, -5, 5, 10, 10, 1, "tin")
            box(out, "body", -1, 4, 0, 2, 1, 3, "door")
            for y in (-3, 0, 3):
                box(out, "body", -5, y, 0, 1, 1, 3, "tin")              # milk churns outside
    return out


def tool(name):
    out = {}
    n = name
    if n in ("Fence_Post", "Fence_Rail", "Fence_Gate", "Stone_Wall", "Hedge_Gate"):
        if n == "Fence_Post":
            box(out, "body", 0, 0, 0, 1, 1, 6, "fence")
        elif n == "Fence_Rail":
            box(out, "body", 0, 0, 0, 1, 1, 6, "fence")
            box(out, "body", 9, 0, 0, 1, 1, 6, "fence")
            for z in (2, 4):
                box(out, "body", 0, 0, z, 10, 1, 1, "plank")
        elif n == "Fence_Gate":
            box(out, "body", 0, 0, 0, 1, 1, 7, "trunk")
            box(out, "body", 7, 0, 0, 1, 1, 7, "trunk")
            for z in (1, 3, 5):
                box(out, "body", 1, 0, z, 6, 1, 1, "plank")
            for i in range(0, 6):
                box(out, "body", 1 + i, 0, 1 + i // 2, 1, 1, 1, "plank")
        elif n == "Stone_Wall":
            for x in range(0, 10):
                for z in range(0, 4):
                    box(out, "body", x, 0, z, 1, 2, 1, "stone" if (x + z) % 2 else "stone2")
        else:
            box(out, "body", -5, 0, 0, 4, 2, 5, "holly")
            box(out, "body", 2, 0, 0, 4, 2, 5, "holly")
            box(out, "body", -1, 0, 0, 3, 1, 4, "plank")
    elif n in ("Hay_Bale", "Hay_Bale_Round", "Hay_Stack", "Compost_Bin", "Trough_Water", "Trough_Feed", "Rain_Barrel", "Milk_Churn", "Scarecrow",
               "Crate_Apples", "Sack_Grain", "Basket_Eggs", "Cider_Press", "Loom", "Butter_Churn", "Spinning_Wheel", "Anvil", "Grindstone", "Well_Farm", "Mailbox", "Market_Stall", "Bird_Feeder"):
        if n == "Hay_Bale":
            box(out, "body", -3, -2, 0, 6, 4, 3, "hay")
        elif n == "Hay_Bale_Round":
            wheel(out, "body", -2, 0, 3, 3, 4)
            for v in list(out["body"]):
                out["body"].remove(v)
                out["body"].append((v[0], v[1], v[2], "hay"))
        elif n == "Hay_Stack":
            for z in range(0, 6):
                r = 4 - z // 2
                for x in range(-r, r + 1):
                    for y in range(-r, r + 1):
                        if x * x + y * y <= r * r + 1:
                            box(out, "body", x, y, z, 1, 1, 1, "hay")
            box(out, "body", 0, 0, 6, 1, 1, 2, "trunk")
        elif n == "Compost_Bin":
            for x in range(-2, 3):
                for y in range(-2, 3):
                    if abs(x) == 2 or abs(y) == 2:
                        box(out, "body", x, y, 0, 1, 1, 3, "plank")
            box(out, "body", -1, -1, 0, 3, 3, 2, "dirt2")
            box(out, "body", 0, 0, 2, 1, 1, 1, "leaf_a")
        elif n in ("Trough_Water", "Trough_Feed"):
            box(out, "body", -3, -1, 0, 6, 2, 2, "trough")
            box(out, "body", -2, -1, 1, 4, 2, 1, "water" if n == "Trough_Water" else "wheat")
        elif n == "Rain_Barrel":
            for z in range(0, 4):
                box(out, "body", -1, -1, z, 3, 3, 1, "trunk" if z % 2 else "metal_k")
            box(out, "body", -1, -1, 4, 3, 3, 1, "water")
        elif n == "Milk_Churn":
            box(out, "body", 0, 0, 0, 2, 2, 3, "tin")
            box(out, "body", 0, 0, 3, 2, 2, 1, "metal")
        elif n == "Scarecrow":
            box(out, "body", 0, 0, 0, 1, 1, 7, "trunk")
            box(out, "body", -3, 0, 5, 7, 1, 1, "trunk")
            box(out, "body", -1, 0, 3, 3, 1, 3, "cloth" if "cloth" in PAL else "fur_b")
            box(out, "body", -1, 0, 7, 3, 2, 3, "hay")
            box(out, "body", -2, -1, 10, 5, 4, 1, "hay")
            box(out, "body", 0, 2, 8, 1, 1, 1, "eye")
        elif n == "Crate_Apples":
            box(out, "body", -2, -2, 0, 4, 4, 2, "wood_l")
            for (dx, dy) in ((-1, -1), (0, 0), (1, -1), (-1, 1), (1, 1)):
                box(out, "body", dx, dy, 2, 1, 1, 1, "fruit_apple")
        elif n == "Sack_Grain":
            box(out, "body", -1, -1, 0, 3, 3, 3, "hay")
            box(out, "body", 0, 0, 3, 1, 1, 1, "wheat")
        elif n == "Basket_Eggs":
            box(out, "body", -1, -1, 0, 3, 3, 1, "wood_l")
            for (dx, dy) in ((0, 0), (1, 0), (0, 1), (-1, 0)):
                box(out, "body", dx, dy, 1, 1, 1, 1, "egg_y" if "egg_y" in PAL else "paper")
            box(out, "body", -1, 0, 2, 3, 1, 1, "trunk")
        elif n == "Cider_Press":
            box(out, "body", -2, -2, 0, 4, 4, 2, "trunk")
            box(out, "body", -1, -1, 2, 3, 3, 3, "wood_l")
            box(out, "body", 0, 0, 5, 1, 1, 3, "metal_k")
            box(out, "body", -1, 0, 7, 3, 1, 1, "metal_k")
            box(out, "body", 0, 0, 1, 1, 1, 1, "fruit_apple")
        elif n == "Loom":
            box(out, "body", -3, 0, 0, 1, 1, 6, "trunk")
            box(out, "body", 3, 0, 0, 1, 1, 6, "trunk")
            box(out, "body", -3, 0, 5, 7, 1, 1, "trunk")
            for x in range(-2, 3):
                box(out, "body", x, 0, 1, 1, 1, 4, "wool" if x % 2 else "flower_b")
        elif n == "Butter_Churn":
            box(out, "body", 0, 0, 0, 2, 2, 4, "trunk")
            box(out, "body", 0, 0, 4, 1, 1, 3, "plank")
        elif n == "Spinning_Wheel":
            wheel(out, "body", 0, 0, 3, 3, 1)
            box(out, "body", -3, -1, 0, 7, 3, 1, "trunk")
            box(out, "body", -3, 0, 1, 1, 1, 3, "trunk")
        elif n == "Anvil":
            box(out, "body", -2, -1, 0, 4, 2, 1, "anvil")
            box(out, "body", -1, -1, 1, 2, 2, 1, "anvil")
            box(out, "body", -3, -1, 2, 6, 2, 1, "anvil")
        elif n == "Grindstone":
            wheel(out, "body", 0, 0, 2, 2, 1)
            box(out, "body", -2, -1, 0, 5, 3, 1, "trunk")
        elif n == "Well_Farm":
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if (dx, dy) != (0, 0):
                        box(out, "body", dx, dy, 0, 1, 1, 2, "stone")
            box(out, "body", -1, 0, 2, 1, 1, 4, "trunk")
            box(out, "body", 1, 0, 2, 1, 1, 4, "trunk")
            box(out, "body", -2, -1, 6, 5, 3, 1, "thatch")
            box(out, "body", 0, 0, 1, 1, 1, 1, "water")
        elif n == "Mailbox":
            box(out, "body", 0, 0, 0, 1, 1, 4, "trunk")
            box(out, "body", -1, -1, 4, 3, 2, 2, "paint_b")
            box(out, "body", 1, 0, 6, 1, 1, 1, "paint_r")
        elif n == "Market_Stall":
            for sx in (-3, 3):
                for sy in (-2, 2):
                    box(out, "body", sx, sy, 0, 1, 1, 6, "trunk")
            box(out, "body", -3, -2, 2, 7, 5, 1, "plank")
            for x in range(-4, 4):
                box(out, "body", x, -3, 6, 1, 7, 1, "awning" if x % 2 else "awning2")
            for (dx, c) in ((-2, "fruit_apple"), (0, "carrot"), (2, "wheat")):
                box(out, "body", dx, 0, 3, 1, 1, 1, c)
        else:
            box(out, "body", 0, 0, 0, 1, 1, 5, "trunk")
            box(out, "body", -1, -1, 5, 3, 3, 1, "plank")
            box(out, "body", -2, -2, 7, 5, 5, 1, "thatch")
            box(out, "body", 0, 0, 6, 1, 1, 1, "wheat")
    return out


def crop(name):
    out = []
    n = name
    rng = random.Random(len(n))
    if n in ("Tomato", "Pepper", "Bean_Trellis", "Grape_Vine", "Hops", "Cucumber"):
        fruit = {"Tomato": "tomato", "Pepper": "pepper", "Bean_Trellis": "bean", "Grape_Vine": "grape", "Hops": "hop", "Cucumber": "melon"}[n]
        for x in (-2, 2):
            for z in range(0, 8):
                out.append((x, 0, z, "trunk"))
        for z in (3, 6):
            for x in range(-2, 3):
                out.append((x, 0, z, "plank"))
        for i in range(10):
            x, z = rng.randint(-2, 2), rng.randint(1, 7)
            out.append((x, 1 if i % 2 else -1, z, "vine"))
            if i % 3 == 0:
                out.append((x, 1, z, fruit))
    elif n in ("Potato", "Onion", "Garlic", "Turnip", "Radish"):
        c = {"Potato": "potato", "Onion": "onion", "Garlic": "cotton", "Turnip": "flower_p", "Radish": "flower_r"}[n]
        for x in (-2, 0, 2):
            out.append((x, 0, -1, c))
            for z in range(0, 3):
                out.append((x, 0, z, "leaf_l"))
            out.append((x, 1, 1, "leaf_l"))
    elif n in ("Lettuce", "Spinach", "Kale", "Broccoli", "Cauliflower"):
        c = {"Lettuce": "lettuce", "Spinach": "leaf_d", "Kale": "leaf_d", "Broccoli": "leaf_d", "Cauliflower": "cotton"}[n]
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                out.append((dx, dy, 0, "leaf_l"))
        out.append((0, 0, 1, c))
        if n in ("Broccoli", "Cauliflower"):
            out.append((0, 0, 2, c))
    elif n in ("Strawberry", "Melon", "Squash", "Watermelon"):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    out.append((dx, dy, 0, "leaf_l" if (dx + dy) % 2 else "vine"))
        if n == "Strawberry":
            for (dx, dy) in ((1, 1), (-1, 1), (0, -2), (2, -1)):
                out.append((dx, dy, 1, "strawberry"))
        else:
            c = {"Melon": "melon", "Squash": "pumpkin", "Watermelon": "melon"}[n]
            for (dx, dy) in ((1, 1), (-2, 0)):
                out.append((dx, dy, 1, c))
                out.append((dx + 1, dy, 1, c))
                out.append((dx, dy, 2, c))
    elif n in ("Rice_Paddy", "Sugarcane", "Cotton", "Hay_Field", "Flax", "Hemp_Row", "Barley", "Oats", "Rye"):
        c = {"Rice_Paddy": "rice", "Sugarcane": "cane", "Cotton": "cotton", "Hay_Field": "hay", "Flax": "flower_b", "Hemp_Row": "leaf_l", "Barley": "wheat", "Oats": "wheat", "Rye": "wheat"}[n]
        h = {"Sugarcane": 10, "Hemp_Row": 9}.get(n, 5)
        for x in range(-3, 4):
            for y in (-1, 1):
                for z in range(0, h - abs(x) % 2):
                    out.append((x, y, z, "stem" if z < h - 2 else c))
        if n == "Rice_Paddy":
            for x in range(-4, 5):
                for y in range(-2, 3):
                    out.append((x, y, -1, "water"))
    elif n in ("Apple_Row", "Pear_Row", "Peach_Row", "Lemon_Row", "Olive_Row", "Fig_Row"):
        f = {"Apple_Row": "fruit_apple", "Pear_Row": "fruit_pear", "Peach_Row": "fruit_orange", "Lemon_Row": "fruit_lemon", "Olive_Row": "leaf_d", "Fig_Row": "grape"}[n]
        for x in (-6, 0, 6):
            for z in range(0, 5):
                out.append((x, 0, z, "trunk"))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    for dz in range(4, 8):
                        if dx * dx + dy * dy + (dz - 6) ** 2 <= 5:
                            out.append((x + dx, dy, dz, "leaf" if (dx + dy + dz) % 5 else f))
    return out


MACHINES = ("Tractor_Red", "Tractor_Green", "Tractor_Blue", "Tractor_Old", "Plough", "Seeder", "Harrow", "Harvester", "Hay_Baler", "Sprayer", "Mower",
            "Wagon", "Hay_Wagon", "Wheelbarrow", "Cart_Milk", "Horse_Cart", "Water_Pump", "Sprinkler", "Irrigation_Pipe", "Windpump", "Water_Tank")
BUILDINGS = ("Barn_Red", "Barn_White", "Stable", "Cow_Shed", "Silo", "Silo_Tall", "Chicken_Coop", "Beehive", "Beehive_Log", "Greenhouse", "Pig_Pen",
             "Dovecote", "Tool_Shed", "Root_Cellar", "Smokehouse", "Dairy")
TOOLS = ("Fence_Post", "Fence_Rail", "Fence_Gate", "Stone_Wall", "Hedge_Gate", "Hay_Bale", "Hay_Bale_Round", "Hay_Stack", "Compost_Bin", "Trough_Water",
         "Trough_Feed", "Rain_Barrel", "Milk_Churn", "Scarecrow", "Crate_Apples", "Sack_Grain", "Basket_Eggs", "Cider_Press", "Loom", "Butter_Churn",
         "Spinning_Wheel", "Anvil", "Grindstone", "Well_Farm", "Mailbox", "Market_Stall", "Bird_Feeder")
CROPS = ("Tomato", "Pepper", "Bean_Trellis", "Grape_Vine", "Hops", "Cucumber", "Potato", "Onion", "Garlic", "Turnip", "Radish", "Lettuce", "Spinach", "Kale",
         "Broccoli", "Cauliflower", "Strawberry", "Melon", "Squash", "Watermelon", "Rice_Paddy", "Sugarcane", "Cotton", "Hay_Field", "Flax", "Hemp_Row",
         "Barley", "Oats", "Rye", "Apple_Row", "Pear_Row", "Peach_Row", "Lemon_Row", "Olive_Row", "Fig_Row")
CATALOG = {}
for m in MACHINES:
    CATALOG["Prop_Machine_" + m] = ("machine", 25.0)
for b in BUILDINGS:
    CATALOG["Prop_Farm_" + b] = ("building", 25.0)
for t in TOOLS:
    CATALOG["Prop_Farm_" + t] = ("tool", 10.0)
for c in CROPS:
    CATALOG["Prop_Crop_" + c] = ("crop", 10.0)


def plan(name):
    fam, _ = CATALOG[name]
    short = name.split("_", 2)[2]
    if fam == "machine":
        return machine(short)
    if fam == "building":
        return building(short)
    if fam == "tool":
        return tool(short)
    return {"body": crop(short)}


def build(name, out_dir):
    import bpy
    parts = plan(name)
    fam, cm = CATALOG[name]
    allv = [v for vs in parts.values() for v in vs]
    zmin = min(z for _, _, z, _ in allv)
    obs = []
    for part, voxels in parts.items():
        ob = V._mesh_from_voxels(name + ("" if part == "body" else "_" + part.capitalize()), voxels, scale=cm, pal=PAL)
        for v in ob.data.vertices:
            v.co.z -= zmin * cm
        obs.append(ob)
    for o in bpy.data.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    import json
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "family": fam, "voxel_cm": cm, "parts": {p: len(v) for p, v in parts.items()}, "pivot": "bottom-centre",
                   "wheels_spin": "wheels" in parts}, f, indent=1)
    for ob in obs:
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
