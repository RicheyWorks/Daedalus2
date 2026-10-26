# SPDX-License-Identifier: MIT
"""The Sims-like practical realm, built out in Blender (Richey 15:12: "we have a sims realm that needs its complete
build out"). The realm is docs/PRACTICAL-APPS.md: a real-world house where physical objects are interfaces to
Richey's existing desktop apps (PhotosToPDF scanner/printer, fax-trident fax machine, image-optimizer photo
workbench, synapse study desk). This module ships three things, all 10 cm voxels, bottom-centre pivots:

1. `Build_Sims_*`  - a modular house kit on a 1 m grid: floor tiles, walls (plain/window/door/corner), roof pieces,
   stairs, porch, driveway, garage door, pool edge, fence.
2. `Prop_Sims_*`   - the practical machines (scanner/printer, fax, computer desk, laptop, study desk + memory cards,
   photo workbench, phone, router, shredder, filing cabinet, whiteboard...) and household appliances (washer, dryer,
   dishwasher, microwave, coffee machine, toaster, vacuum, iron, treadmill, console, hot tub, grill, patio set,
   lawnmower, sprinkler head, letterbox).
3. `House_Sims_Starter` - one complete furnished starter house assembled from the kit and voxel_props furniture,
   exported as a single FBX (walls/floors/roof/furniture as separate meshes) so the realm has a lived-in exemplar.
"""
import os

import voxel_island as V
import voxel_props as VP

PAL = dict(VP.PAL)
PAL.update({"wall_w": (0.94, 0.92, 0.88), "wall_y": (0.95, 0.88, 0.70), "wall_b": (0.80, 0.86, 0.92), "siding": (0.85, 0.80, 0.70), "floor_w": (0.78, 0.62, 0.42),
            "floor_t": (0.85, 0.85, 0.82), "floor_c": (0.55, 0.50, 0.60), "roof_s": (0.45, 0.40, 0.42), "roof_t": (0.70, 0.30, 0.22), "concrete": (0.70, 0.70, 0.68),
            "asphalt": (0.30, 0.30, 0.32), "lawn": (0.40, 0.65, 0.30), "pool": (0.35, 0.75, 0.90), "plastic_k": (0.15, 0.15, 0.17), "plastic_w": (0.92, 0.92, 0.90),
            "led": (0.30, 0.95, 0.50), "paper_t": (0.98, 0.98, 0.96), "cardboard": (0.75, 0.60, 0.40), "steel": (0.75, 0.77, 0.80), "memory_card": (0.95, 0.85, 0.40)})
box = VP.box


def kit(n):
    o = []
    if n == "Floor_Wood":
        for x in range(0, 10):
            for y in range(0, 10):
                box(o, x, y, 0, 1, 1, 1, "floor_w" if (x // 2 + y) % 2 else "oak_d")
    elif n == "Floor_Tile":
        for x in range(0, 10):
            for y in range(0, 10):
                box(o, x, y, 0, 1, 1, 1, "floor_t" if (x // 5 + y // 5) % 2 else "porcelain")
    elif n == "Floor_Carpet":
        box(o, 0, 0, 0, 10, 10, 1, "floor_c")
    elif n == "Floor_Lawn":
        box(o, 0, 0, 0, 10, 10, 1, "lawn")
    elif n == "Floor_Concrete":
        box(o, 0, 0, 0, 10, 10, 1, "concrete")
    elif n == "Floor_Driveway":
        box(o, 0, 0, 0, 10, 10, 1, "asphalt")
    elif n == "Floor_Pool":
        box(o, 0, 0, 0, 10, 10, 1, "pool")
    elif n in ("Wall_Plain", "Wall_Window", "Wall_Door", "Wall_Corner", "Wall_Half", "Wall_Exterior", "Wall_Garage"):
        c = "siding" if n in ("Wall_Exterior", "Wall_Garage") else "wall_w"
        h = 14 if n != "Wall_Half" else 7
        box(o, 0, 0, 0, 10, 1, h, c)
        if n == "Wall_Window":
            box(o, 2, 0, 5, 6, 1, 6, "glass")
            box(o, 5, 0, 5, 1, 1, 6, "oak")
            box(o, 2, 0, 8, 6, 1, 1, "oak")
        elif n == "Wall_Door":
            box(o, 3, 0, 0, 4, 1, 10, "door")
            box(o, 6, 1, 5, 1, 1, 1, "brass")
        elif n == "Wall_Corner":
            box(o, 0, 0, 0, 1, 10, h, c)
        elif n == "Wall_Garage":
            for z in range(0, 12, 2):
                box(o, 1, 0, z, 8, 1, 1, "plastic_w")
                box(o, 1, 0, z + 1, 8, 1, 1, "steel")
    elif n in ("Roof_Flat", "Roof_Slope", "Roof_Ridge", "Roof_Gable_End", "Roof_Tile_Slope"):
        c = "roof_t" if n == "Roof_Tile_Slope" else "roof_s"
        if n == "Roof_Flat":
            box(o, 0, 0, 0, 10, 10, 1, c)
        elif n in ("Roof_Slope", "Roof_Tile_Slope"):
            for y in range(0, 10):
                box(o, 0, y, y // 2, 10, 1, 1, c)
        elif n == "Roof_Ridge":
            for y in range(0, 5):
                box(o, 0, y, y, 10, 1, 1, c)
                box(o, 0, 9 - y, y, 10, 1, 1, c)
        else:
            for z in range(0, 5):
                box(o, z, 0, z, 10 - 2 * z, 1, 1, "siding")
    elif n == "Stairs":
        for i in range(0, 7):
            box(o, 0, i, 0, 5, 1, i * 2 + 2, "oak")
        box(o, 5, 0, 0, 1, 7, 16, "oak_d")
    elif n == "Porch":
        box(o, 0, 0, 0, 10, 10, 2, "oak")
        for x in (0, 9):
            box(o, x, 0, 2, 1, 1, 12, "wall_w")
        box(o, 0, 0, 14, 10, 10, 1, "roof_s")
        for x in range(1, 9, 2):
            box(o, x, 0, 2, 1, 1, 4, "oak_d")
    elif n == "Fence_White":
        box(o, 0, 0, 2, 10, 1, 1, "plastic_w")
        box(o, 0, 0, 5, 10, 1, 1, "plastic_w")
        for x in range(0, 10, 2):
            box(o, x, 0, 0, 1, 1, 7, "plastic_w")
    elif n == "Pool_Edge":
        box(o, 0, 0, 0, 10, 2, 1, "floor_t")
        box(o, 0, 2, -1, 10, 8, 1, "pool")
    elif n == "Pool_Ladder":
        for x in (0, 2):
            box(o, x, 0, 0, 1, 1, 12, "chrome")
        for z in range(2, 12, 3):
            box(o, 0, 0, z, 3, 1, 1, "chrome")
    elif n == "Chimney":
        box(o, 0, 0, 0, 3, 3, 10, "stone")
        box(o, 1, 1, 10, 1, 1, 2, "smoke")
    elif n == "Mailbox_Street":
        box(o, 0, 0, 0, 1, 1, 10, "oak")
        box(o, -1, -1, 10, 3, 5, 3, "paint_b")
        box(o, 1, 1, 13, 1, 1, 2, "paint_r")
    return o


def machine(n):
    o = []
    if n == "Scanner_Printer":          # the PhotosToPDF machine: ADaedalusPhotoPdfMachine
        box(o, -4, -3, 0, 8, 6, 3, "plastic_w")
        box(o, -3, -2, 3, 6, 4, 1, "glass")
        box(o, -4, -3, 4, 8, 6, 1, "plastic_k")
        box(o, -3, 3, 1, 6, 1, 1, "paper_t")      # a PDF coming out
        box(o, 3, -3, 4, 1, 1, 1, "led")
    elif n == "Fax_Machine":
        box(o, -3, -3, 0, 6, 5, 3, "plastic_w")
        box(o, -2, -2, 3, 4, 2, 1, "screen")
        box(o, 2, -3, 3, 1, 3, 2, "plastic_k")    # handset
        box(o, -3, 2, 2, 6, 2, 1, "paper_t")
        box(o, -2, 2, 3, 4, 1, 1, "paper_t")
    elif n == "Computer_Desk":
        box(o, -6, -3, 7, 12, 6, 1, "oak")
        for (x, y) in ((-6, -3), (5, -3), (-6, 2), (5, 2)):
            box(o, x, y, 0, 1, 1, 7, "oak_d")
        box(o, -3, 0, 8, 6, 1, 4, "plastic_k")
        box(o, -2, 1, 9, 4, 1, 3, "screen")
        box(o, -2, -2, 8, 4, 1, 1, "plastic_w")   # keyboard
        box(o, 4, -2, 0, 2, 2, 6, "plastic_k")    # tower
        box(o, 5, -2, 4, 1, 1, 1, "led")
    elif n == "Laptop":
        box(o, -2, -1, 0, 4, 3, 1, "steel")
        box(o, -2, 2, 0, 4, 1, 3, "steel")
        box(o, -1, 2, 1, 2, 1, 2, "screen")
    elif n == "Study_Desk":                 # synapse memory cards
        box(o, -5, -3, 7, 10, 6, 1, "oak")
        for (x, y) in ((-5, -3), (4, -3), (-5, 2), (4, 2)):
            box(o, x, y, 0, 1, 1, 7, "oak_d")
        for i, x in enumerate(range(-4, 4, 2)):
            box(o, x, -1, 8, 1, 2, 1, "memory_card" if i % 2 else "paper_t")
        box(o, 3, 1, 8, 1, 1, 3, "candle_w")
        box(o, 3, 1, 11, 1, 1, 1, "flame")
        box(o, -3, 1, 8, 2, 1, 2, "book_b")
    elif n == "Photo_Workbench":            # image-optimizer
        box(o, -5, -3, 6, 10, 6, 1, "oak")
        for (x, y) in ((-5, -3), (4, -3), (-5, 2), (4, 2)):
            box(o, x, y, 0, 1, 1, 6, "oak_d")
        box(o, -4, 0, 7, 4, 1, 4, "plastic_k")
        box(o, -3, 1, 8, 2, 1, 2, "feather_b")
        for i, x in enumerate(range(0, 4)):
            box(o, x, -2, 7, 1, 1, 1, ("flower_r", "flower_y", "feather_b", "leaf")[i])   # prints
        box(o, 2, 1, 7, 2, 1, 3, "plastic_w")   # lamp
    elif n == "Phone_Desk":
        box(o, -2, -1, 0, 4, 2, 1, "plastic_k")
        box(o, -2, -1, 1, 1, 2, 1, "plastic_k")
        box(o, -1, 0, 1, 2, 1, 1, "paper_t")
    elif n == "Phone_Wall":
        box(o, -1, 0, 0, 2, 1, 4, "plastic_k")
        box(o, -2, 0, 1, 1, 1, 3, "plastic_k")
        box(o, -2, 0, 0, 1, 1, 1, "net")
    elif n == "Router":
        box(o, -2, -1, 0, 4, 2, 1, "plastic_k")
        box(o, -2, 0, 1, 1, 1, 2, "plastic_k")
        box(o, 1, 0, 1, 1, 1, 2, "plastic_k")
        box(o, 0, -1, 1, 1, 1, 1, "led")
    elif n == "Shredder":
        box(o, -2, -1, 0, 4, 3, 5, "plastic_k")
        box(o, -1, 0, 5, 2, 1, 1, "paper_t")
        box(o, -1, 0, 1, 2, 1, 3, "paper_t")
    elif n == "Filing_Cabinet":
        box(o, -2, -2, 0, 4, 4, 12, "steel")
        for z in (2, 6, 10):
            box(o, 0, 2, z, 1, 1, 1, "plastic_k")
    elif n == "Whiteboard":
        box(o, -6, 0, 6, 12, 1, 8, "plastic_w")
        box(o, -6, 0, 6, 12, 1, 1, "steel")
        box(o, -3, 1, 9, 3, 1, 1, "paint_b")
        box(o, 1, 1, 10, 2, 1, 1, "paint_r")
        box(o, -6, 0, 0, 1, 1, 6, "steel")
        box(o, 5, 0, 0, 1, 1, 6, "steel")
    elif n == "Bulletin_Board":
        box(o, -5, 0, 5, 10, 1, 7, "cardboard")
        for (x, z, c) in ((-3, 8, "paper_t"), (1, 9, "flower_y"), (3, 6, "paper_t"), (-1, 6, "feather_b")):
            box(o, x, 1, z, 2, 1, 2, c)
    elif n == "Server_Rack":               # LoadBalancerPro
        box(o, -3, -2, 0, 6, 4, 18, "plastic_k")
        for z in range(1, 18, 2):
            box(o, -2, 2, z, 4, 1, 1, "steel")
            box(o, 2, 2, z, 1, 1, 1, "led" if z % 4 == 1 else "flame")
    elif n == "Safe":
        box(o, -2, -2, 0, 4, 4, 5, "metal_k")
        box(o, 0, 2, 2, 1, 1, 1, "chrome")
    elif n == "Printer_3D":
        box(o, -3, -3, 0, 6, 6, 1, "plastic_k")
        for (x, y) in ((-3, -3), (2, -3), (-3, 2), (2, 2)):
            box(o, x, y, 1, 1, 1, 7, "steel")
        box(o, -3, -3, 8, 6, 6, 1, "plastic_k")
        box(o, -1, -1, 1, 2, 2, 2, "flower_b")   # the print
        box(o, -2, -2, 5, 4, 4, 1, "steel")
    elif n == "Camera_Tripod":
        box(o, 0, 0, 0, 1, 1, 10, "plastic_k")
        box(o, -1, -1, 10, 3, 2, 2, "plastic_k")
        box(o, 0, 1, 10, 1, 1, 1, "glass")
        for (dx, dy) in ((1, 1), (-1, 1), (0, -1)):
            box(o, dx, dy, 0, 1, 1, 1, "plastic_k")
    elif n == "Game_Console":
        box(o, -2, -1, 0, 4, 2, 1, "plastic_k")
        box(o, 1, 0, 1, 1, 1, 1, "led")
        box(o, -4, -1, 0, 1, 2, 1, "plastic_w")   # controller
    return o


def appliance(n):
    o = []
    if n in ("Washer", "Dryer", "Dishwasher"):
        box(o, -3, -3, 0, 6, 6, 8, "plastic_w")
        if n != "Dishwasher":
            for dx in range(-2, 2):
                for dz in range(2, 6):
                    if (dx + 0.5) ** 2 + (dz - 3.5) ** 2 <= 4:
                        box(o, dx, 3, dz, 1, 1, 1, "glass" if n == "Washer" else "screen")
        else:
            box(o, -2, 3, 1, 4, 1, 6, "steel")
        box(o, 2, 3, 7, 1, 1, 1, "led")
    elif n == "Microwave":
        box(o, -3, -2, 0, 6, 4, 3, "plastic_k")
        box(o, -2, 2, 1, 3, 1, 2, "glass")
        box(o, 2, 2, 1, 1, 1, 1, "led")
    elif n == "Coffee_Machine":
        box(o, -1, -1, 0, 3, 3, 1, "plastic_k")
        box(o, -1, -1, 3, 3, 3, 2, "plastic_k")
        box(o, -1, -1, 1, 1, 3, 2, "plastic_k")
        box(o, 0, 0, 1, 2, 2, 1, "porcelain")
        box(o, 0, 0, 2, 1, 1, 1, "choc")
    elif n == "Toaster":
        box(o, -2, -1, 0, 4, 2, 2, "chrome")
        box(o, -1, 0, 2, 1, 1, 1, "hay")
        box(o, 1, 0, 2, 1, 1, 1, "hay")
    elif n == "Vacuum":
        box(o, -1, -2, 0, 3, 4, 2, "paint_r")
        box(o, 0, 2, 0, 1, 1, 8, "steel")
        box(o, -1, 2, 8, 3, 1, 1, "plastic_k")
    elif n == "Iron_Board":
        box(o, -4, -1, 5, 8, 2, 1, "linen_w")
        box(o, -3, 0, 0, 1, 1, 5, "steel")
        box(o, 2, 0, 0, 1, 1, 5, "steel")
        box(o, 1, 0, 6, 2, 1, 1, "chrome")
    elif n == "Treadmill":
        box(o, -2, -6, 0, 4, 12, 1, "plastic_k")
        box(o, -2, 5, 1, 4, 1, 8, "steel")
        box(o, -2, 4, 9, 4, 2, 1, "screen")
    elif n == "Hot_Tub":
        for x in range(-4, 5):
            for y in range(-4, 5):
                if x * x + y * y <= 16:
                    box(o, x, y, 0, 1, 1, 3, "oak")
                    if x * x + y * y <= 9:
                        box(o, x, y, 3, 1, 1, 1, "pool")
        box(o, 0, 0, 4, 1, 1, 1, "cloud_w")
    elif n == "Grill":
        box(o, -3, -2, 4, 6, 4, 3, "plastic_k")
        box(o, -2, -1, 7, 4, 2, 1, "metal")
        box(o, -1, 0, 8, 1, 1, 1, "forge")
        for (x, y) in ((-2, -1), (1, 1)):
            box(o, x, y, 0, 1, 1, 4, "steel")
    elif n == "Patio_Set":
        box(o, -2, -2, 4, 5, 5, 1, "glass")
        box(o, 0, 0, 0, 1, 1, 4, "steel")
        for (x, y) in ((-4, 0), (4, 0), (0, -4), (0, 4)):
            box(o, x - 1, y - 1, 2, 2, 2, 1, "steel")
            box(o, x - 1, y - 1, 0, 1, 1, 2, "steel")
        box(o, 0, 0, 5, 1, 1, 8, "steel")
        box(o, -4, -4, 13, 9, 9, 1, "paint_g")       # umbrella
    elif n == "Lawnmower":
        box(o, -2, -2, 1, 4, 4, 2, "paint_g")
        box(o, 0, 0, 3, 1, 1, 2, "plastic_k")
        box(o, 0, -2, 2, 1, 1, 6, "steel")
        box(o, -1, -3, 8, 3, 1, 1, "steel")
        for (x, y) in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
            box(o, x, y, 0, 1, 1, 1, "tyre")
    elif n == "Sprinkler_Head":
        box(o, 0, 0, 0, 1, 1, 2, "plastic_k")
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            box(o, dx, dy, 2, 1, 1, 1, "water")
    elif n == "Trash_Can":
        box(o, -1, -1, 0, 3, 3, 4, "plastic_k")
        box(o, -1, -1, 4, 3, 3, 1, "steel")
    elif n == "Recycling_Bin":
        box(o, -1, -1, 0, 3, 3, 4, "paint_b")
        box(o, 0, 0, 4, 1, 1, 1, "paper_t")
    elif n == "Water_Cooler":
        box(o, -1, -1, 0, 3, 3, 8, "plastic_w")
        box(o, -1, -1, 8, 3, 3, 3, "glass")
        box(o, -1, -1, 9, 3, 3, 1, "water")
    elif n == "Air_Conditioner":
        box(o, -3, -1, 0, 6, 2, 3, "plastic_w")
        box(o, -2, 1, 1, 4, 1, 1, "steel")
    elif n == "Ceiling_Fan":
        box(o, 0, 0, 2, 1, 1, 2, "steel")
        for (dx, dy) in ((1, 0), (-4, 0), (0, 1), (0, -4)):
            box(o, dx, dy, 2, 4 if dy == 0 else 1, 1 if dy == 0 else 4, 1, "oak")
    elif n == "Aquarium":
        box(o, -4, -2, 0, 8, 4, 1, "plastic_k")
        box(o, -4, -2, 1, 8, 4, 5, "glass")
        box(o, -3, -1, 1, 6, 2, 4, "water")
        box(o, -2, 0, 2, 1, 1, 1, "fur_o")
        box(o, 1, 0, 3, 1, 1, 1, "feather_y")
    elif n == "Pet_Bed":
        box(o, -2, -2, 0, 5, 5, 1, "cushion_b")
        for x in range(-2, 3):
            for y in range(-2, 3):
                if abs(x) == 2 or abs(y) == 2:
                    box(o, x, y, 1, 1, 1, 1, "cushion_b")
    return o


MACHINES = ("Scanner_Printer", "Fax_Machine", "Computer_Desk", "Laptop", "Study_Desk", "Photo_Workbench", "Phone_Desk", "Phone_Wall", "Router", "Shredder",
            "Filing_Cabinet", "Whiteboard", "Bulletin_Board", "Server_Rack", "Safe", "Printer_3D", "Camera_Tripod", "Game_Console")
APPLIANCES = ("Washer", "Dryer", "Dishwasher", "Microwave", "Coffee_Machine", "Toaster", "Vacuum", "Iron_Board", "Treadmill", "Hot_Tub", "Grill", "Patio_Set",
              "Lawnmower", "Sprinkler_Head", "Trash_Can", "Recycling_Bin", "Water_Cooler", "Air_Conditioner", "Ceiling_Fan", "Aquarium", "Pet_Bed")
KIT = ("Floor_Wood", "Floor_Tile", "Floor_Carpet", "Floor_Lawn", "Floor_Concrete", "Floor_Driveway", "Floor_Pool", "Wall_Plain", "Wall_Window", "Wall_Door",
       "Wall_Corner", "Wall_Half", "Wall_Exterior", "Wall_Garage", "Roof_Flat", "Roof_Slope", "Roof_Ridge", "Roof_Gable_End", "Roof_Tile_Slope", "Stairs", "Porch",
       "Fence_White", "Pool_Edge", "Pool_Ladder", "Chimney", "Mailbox_Street")
CATALOG = {}
for k in KIT:
    CATALOG["Build_Sims_" + k] = ("kit", 10.0)
for m in MACHINES:
    CATALOG["Prop_Sims_" + m] = ("machine", 10.0)
for a in APPLIANCES:
    CATALOG["Prop_Sims_" + a] = ("appliance", 10.0)
CATALOG["House_Sims_Starter"] = ("house", 10.0)


def plan(name):
    fam, _ = CATALOG[name]
    if fam == "house":
        return starter_house()
    short = name.split("_", 2)[2]
    return {"kit": kit, "machine": machine, "appliance": appliance}[fam](short)


def _place(dst, voxels, dx, dy, dz=0, rot=0):
    for x, y, z, c in voxels:
        for _ in range(rot % 4):
            x, y = -y, x
        dst.append((x + dx, y + dy, z + dz, c))


def starter_house():
    """A 10 x 8 m one-storey house with a lounge, kitchen, bedroom, bathroom and office, furnished from
    voxel_props + the practical machines, on a lawn with a driveway and a mailbox. Returns {part: voxels}."""
    parts = {"floors": [], "walls": [], "roof": [], "furniture": [], "machines": [], "yard": []}
    W, D = 100, 80
    for x in range(-W // 2 - 30, W // 2 + 30):
        for y in range(-D // 2 - 30, D // 2 + 30):
            inside = -W // 2 <= x < W // 2 and -D // 2 <= y < D // 2
            if not inside:
                parts["yard"].append((x, y, -1, "lawn" if not (x >= W // 2 and -10 <= y < 20) else "asphalt"))
    for x in range(-W // 2, W // 2):
        for y in range(-D // 2, D // 2):
            room = "kitchen" if x < -10 and y >= 0 else ("bath" if x >= 25 and y >= 10 else ("office" if x >= 25 else "lounge"))
            c = {"kitchen": "floor_t", "bath": "porcelain", "office": "floor_c", "lounge": "floor_w"}[room]
            parts["floors"].append((x, y, 0, c))
    for x in range(-W // 2 - 1, W // 2 + 1):
        for z in range(1, 15):
            for y in (-D // 2 - 1, D // 2):
                win = (x % 25 in range(8, 16)) and 5 <= z <= 10 and y == D // 2
                door = y == -D // 2 - 1 and -3 <= x < 3 and z < 11
                parts["walls"].append((x, y, z, "glass" if win else ("door" if door else "siding")))
    for y in range(-D // 2 - 1, D // 2 + 1):
        for z in range(1, 15):
            for x in (-W // 2 - 1, W // 2):
                win = (y % 20 in range(6, 14)) and 5 <= z <= 10
                parts["walls"].append((x, y, z, "glass" if win else "siding"))
    for y in range(-D // 2, D // 2):                # inner wall between lounge and office, with a doorway
        for z in range(1, 15):
            if not (-12 <= y < -2 and z < 11):
                parts["walls"].append((24, y, z, "wall_w"))
    for x in range(-W // 2, -10):                    # kitchen half wall
        parts["walls"].append((x, 0, 1, "wall_y"))
        parts["walls"].append((x, 0, 2, "wall_y"))
    for z in range(0, 12):                           # ridge roof: 3 voxels of run per voxel of rise, solid slabs
        lo, hi = -D // 2 - 3 + z * 3, D // 2 + 3 - z * 3
        for x in range(-W // 2 - 3, W // 2 + 3):
            for y in range(lo, hi):
                if y < lo + 3 or y >= hi - 3 or z == 11:
                    parts["roof"].append((x, y, 15 + z, "roof_s"))
            if z == 0:                                # eaves underside / ceiling
                for y in range(-D // 2 - 1, D // 2 + 1):
                    parts["roof"].append((x, y, 15, "wall_w"))
    for z in range(15, 30):
        parts["roof"].append((30, 20, z, "stone"))
        parts["roof"].append((31, 20, z, "stone"))
    parts["roof"].append((30, 20, 30, "smoke"))
    place = [("Sofa", 0, 20, 1, 0), ("Coffee_Table", 0, 10, 1, 0), ("Television", 0, 32, 1, 2), ("Rug_Long", 0, 14, 1, 0), ("Bookshelf", -20, 36, 1, 0),
             ("Lamp_Floor", 18, 34, 1, 0), ("Fireplace", -22, 10, 1, 1), ("Plant_Pot", 20, -30, 1, 0),
             ("Bed", -35, 25, 1, 0), ("Nightstand", -44, 30, 1, 0), ("Wardrobe", -44, 10, 1, 1), ("Dresser", -30, 36, 1, 0),
             ("Kitchen_Counter", -40, -30, 1, 0), ("Fridge", -46, -20, 1, 0), ("Stove", -30, -30, 1, 0), ("Sink_Kitchen", -20, -30, 1, 0), ("Table", -30, -10, 1, 0),
             ("Chair", -36, -10, 1, 1), ("Chair", -24, -10, 1, 3), ("Dish_Rack", -14, -30, 1, 0),
             ("Bathtub", 42, 30, 1, 0), ("Toilet", 30, 34, 1, 2), ("Sink", 30, 24, 1, 0), ("Towel_Rack", 46, 18, 1, 1), ("Bath_Mat", 38, 20, 1, 0),
             ("Desk", 40, -20, 1, 0), ("Chair", 40, -28, 1, 2), ("Clock_Wall", 46, -5, 8, 1)]
    for name, x, y, z, rot in place:
        _place(parts["furniture"], VP.house(name), x, y, z, rot)
    for name, x, y, z, rot in (("Computer_Desk", 40, 0, 1, 0), ("Scanner_Printer", 46, -32, 1, 0), ("Fax_Machine", 30, -34, 1, 0), ("Router", 46, 8, 8, 0),
                               ("Washer", -46, -36, 1, 0), ("Microwave", -34, -30, 8, 0), ("Coffee_Machine", -24, -30, 8, 0), ("Trash_Can", -12, -36, 1, 0),
                               ("Study_Desk", 30, -10, 1, 1), ("Phone_Wall", 24, -20, 8, 1)):
        _place(parts["machines"], machine(name) if name in MACHINES else appliance(name), x, y, z, rot)
    for name, x, y, rot in (("Mailbox_Street", 60, -45, 0), ("Fence_White", -60, -45, 0), ("Fence_White", -50, -45, 0), ("Patio_Set", 0, 55, 0), ("Grill", 20, 55, 0),
                            ("Lawnmower", -40, 52, 0)):
        _place(parts["yard"], kit(name) if name in KIT else appliance(name), x, y, 0, rot)
    return parts


def build(name, out_dir):
    import bpy
    import json
    fam, cm = CATALOG[name]
    parts = plan(name)
    if isinstance(parts, list):
        parts = {"body": parts}
    allv = [v for vs in parts.values() for v in vs]
    zmin = min(z for _, _, z, _ in allv)
    obs = []
    for part, voxels in parts.items():
        if not voxels:
            continue
        ob = V._mesh_from_voxels(name + ("" if part == "body" else "_" + part), voxels, scale=cm, pal=PAL)
        for v in ob.data.vertices:
            v.co.z -= zmin * cm
        obs.append(ob)
    for o in bpy.data.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "family": fam, "voxel_cm": cm, "parts": {p: len(v) for p, v in parts.items()}, "pivot": "bottom-centre",
                   "app": {"Scanner_Printer": "PhotosToPDFPC", "Fax_Machine": "fax-trident", "Photo_Workbench": "image-optimizer", "Study_Desk": "synapse",
                           "Server_Rack": "LoadBalancerPro"}.get(name.split("_", 2)[-1])}, f, indent=1)
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
