# SPDX-License-Identifier: MIT
"""Prismheart Realm props (ADR-067) — original 16-bit crystal-era RPG kit, voxel, export_catalog-compatible.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_catalog.py -- prism OUT [structure|item]

Structures (25 cm voxels): the Prism Shrine, the Waystone (save point), the airship Skyfarer, castle gate, town house,
inn, item shop, arms shop, spell tower, chapel, harbour dock, crystal lamp post.
Items (10 cm voxels): chests (wood/iron/gilded, closed/open), one weapon per job (Bladeward sword, Runecaster staff,
Lightmender rod, Shadowstep daggers, Beastcaller bow, Gearwright wrench, Starlancer lance, Chronoseer hourglass staff),
potions (Mendwater, Mana Draught, Clearwater, Ember Plume), six Prism Shards (fire, tide, gale, stone, light, shade).
"""
import json
import math
import os

import voxel_creatures as VC

PAL = dict(VC.PAL)


def C(rgb):
    k = "p%02x%02x%02x" % tuple(int(max(0, min(1, c)) * 255) for c in rgb)
    PAL.setdefault(k, tuple(int(max(0, min(1, c)) * 255) / 255 for c in rgb))
    return k


def box(o, x0, y0, z0, w, d, h, c):
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + d):
            for z in range(z0, z0 + h):
                o.append((x, y, z, c))


def disc(o, cx, cy, z, r, c, h=1):
    for x in range(-r, r + 1):
        for y in range(-r, r + 1):
            if x * x + y * y <= r * r + r:
                box(o, cx + x, cy + y, z, 1, 1, h, c)


def gem(o, cx, cy, z0, r, h, c, c2=None):
    """Octahedral crystal: widest at a third of its height."""
    mid = z0 + h // 3
    for z in range(z0, z0 + h):
        k = (z - z0) / max(1, mid - z0) if z < mid else (z0 + h - z) / max(1, z0 + h - mid)
        rr = max(0, int(round(r * k)))
        for x in range(-rr, rr + 1):
            for y in range(-rr, rr + 1):
                if abs(x) + abs(y) <= rr:
                    o.append((cx + x, cy + y, z, c2 if (c2 and (x + y + z) % 4 == 0) else c))


STONE, STONE_D = C((.72, .70, .68)), C((.50, .48, .47))
WOOD, WOOD_D = C((.55, .38, .22)), C((.38, .25, .14))
ROOF_B, ROOF_R, ROOF_G = C((.25, .35, .65)), C((.70, .22, .20)), C((.30, .50, .30))
GOLD, IRON, CLOTH = C((.95, .78, .25)), C((.62, .62, .66)), C((.92, .88, .78))
PRISM = C((.65, .90, 1.0))
PRISM2 = C((.90, .70, 1.0))
GLOW = C((1.0, .90, .55))


def structure(n):
    o = []
    if n == "PrismShrine":
        disc(o, 0, 0, 0, 10, STONE_D, 1)
        disc(o, 0, 0, 1, 8, STONE, 1)
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            x, y = int(7 * math.cos(a)), int(7 * math.sin(a))
            box(o, x - 1, y - 1, 2, 2, 2, 12, STONE)
            box(o, x - 1, y - 1, 14, 2, 2, 1, GOLD)
        box(o, -2, -2, 2, 4, 4, 4, STONE_D)
        gem(o, 0, 0, 8, 3, 12, PRISM, PRISM2)
        for x in range(-7, 8):
            box(o, x, -7, 15, 1, 1, 1, STONE)
            box(o, x, 7, 15, 1, 1, 1, STONE)
    elif n == "Waystone":
        disc(o, 0, 0, 0, 3, STONE_D)
        gem(o, 0, 0, 2, 2, 9, C((.55, .95, .85)), GLOW)
    elif n == "Skyfarer":
        for y in range(-18, 19):                                        # hull: a boat, tapering
            w = int(6 * (1 - (abs(y) / 19) ** 2)) + 1
            for z in range(0, 5):
                ww = max(1, w - (4 - z) // 2)
                box(o, -ww, y, z, 2 * ww + 1, 1, 1, WOOD if z < 4 else WOOD_D)
        box(o, -5, -12, 5, 11, 24, 1, WOOD_D)                           # deck
        for x in (-5, 5):
            box(o, x, -12, 6, 1, 24, 1, GOLD)                           # rails
        box(o, -2, -16, 6, 5, 5, 4, WOOD)                               # cabin
        box(o, -2, -16, 10, 5, 5, 1, ROOF_R)
        box(o, 0, 14, 5, 1, 1, 3, GOLD)                                 # figurehead post
        gem(o, 0, 19, 4, 1, 4, PRISM)                                   # prism figurehead
        for y in (-8, 8):                                               # masts to the envelope
            box(o, 0, y, 6, 1, 1, 8, WOOD_D)
        for y in range(-16, 17):                                        # balloon envelope
            r = int(7 * (1 - (abs(y) / 17) ** 2) ** .5)
            for x in range(-r, r + 1):
                for z in range(-r, r + 1):
                    if x * x + z * z <= r * r and (x * x + z * z >= (r - 1) ** 2 or abs(y) > 14):
                        o.append((x, y, 21 + z, CLOTH if (y // 4) % 2 else C((.85, .30, .25))))
        for sx in (-8, 8):                                              # side propellers
            box(o, sx, -2, 4, 1, 1, 4, IRON)
            for k in range(-3, 4):
                o.append((sx + (1 if sx > 0 else -1), -2, 6 + k, WOOD_D))
                o.append((sx + (1 if sx > 0 else -1), -2 + k, 6, WOOD_D))
        box(o, -1, -20, 2, 3, 1, 4, WOOD_D)                             # rudder
    elif n == "CastleGate":
        for x0 in (-10, 6):
            box(o, x0, -3, 0, 5, 6, 18, STONE)
            for x in range(x0, x0 + 5, 2):
                box(o, x, -3, 18, 1, 6, 2, STONE)
            box(o, x0 + 1, -4, 16, 3, 1, 1, ROOF_B)                     # banners
            box(o, x0 + 2, -4, 9, 1, 1, 7, ROOF_B)
        box(o, -5, -3, 10, 11, 6, 4, STONE)
        for x in range(-5, 6, 2):
            box(o, x, -3, 14, 1, 6, 1, STONE)
        for x in range(-4, 5):
            for z in range(0, 10):
                if (x * x) / 25 + ((z - 3) ** 2) / 49 <= 1:
                    pass
        box(o, -4, -2, 0, 9, 1, 9, WOOD_D)                              # portcullis door
        for x in range(-4, 5, 2):
            box(o, x, -3, 0, 1, 1, 9, IRON)
    elif n in ("TownHouse", "Inn", "ItemShop", "ArmsShop", "Chapel"):
        W, D, H = {"TownHouse": (10, 8, 6), "Inn": (14, 10, 8), "ItemShop": (10, 9, 6), "ArmsShop": (10, 9, 6), "Chapel": (10, 16, 9)}[n]
        roof = {"TownHouse": ROOF_R, "Inn": ROOF_G, "ItemShop": ROOF_B, "ArmsShop": C((.35, .35, .38)), "Chapel": C((.45, .25, .55))}[n]
        box(o, -W // 2, -D // 2, 0, W, D, 1, STONE_D)
        box(o, -W // 2, -D // 2, 1, W, D, H, CLOTH if n != "ArmsShop" else STONE)
        for x in (-W // 2, W // 2 - 1):
            for y in (-D // 2, D // 2 - 1):
                box(o, x, y, 1, 1, 1, H, WOOD_D)                        # timber corners
        box(o, -W // 2, -D // 2, H, W, D, 1, WOOD_D)
        for z in range(W // 2 + 1):                                     # gable roof
            box(o, -W // 2 - 1 + z, -D // 2 - 1, H + 1 + z, max(1, W + 2 - 2 * z), D + 2, 1, roof)
        box(o, -1, -D // 2 - 1, 1, 2, 1, 3, WOOD)                       # door
        for x in (-W // 2 + 2, W // 2 - 3):
            box(o, x, -D // 2 - 1, 3, 2, 1, 2, GLOW)                    # lit windows
        sign = {"Inn": C((.85, .55, .20)), "ItemShop": C((.30, .65, .40)), "ArmsShop": IRON, "Chapel": GOLD, "TownHouse": None}[n]
        if sign:
            box(o, W // 2 - 2, -D // 2 - 2, H - 2, 3, 1, 2, sign)
            box(o, W // 2 - 1, -D // 2 - 2, H, 1, 1, 1, WOOD_D)
        if n == "Chapel":
            box(o, -1, D // 2 - 3, H + W // 2 + 1, 3, 3, 6, STONE)
            gem(o, 0, D // 2 - 2, H + W // 2 + 7, 1, 4, PRISM)
    elif n == "SpellTower":
        for z in range(0, 22):
            r = 4 if z < 18 else 5
            disc(o, 0, 0, z, r, STONE if z % 4 else STONE_D) if z in (0, 17, 18, 21) else None
            for a in range(0, 360, 12):
                x, y = int(round(r * math.cos(math.radians(a)))), int(round(r * math.sin(math.radians(a))))
                o.append((x, y, z, STONE if (z // 3) % 2 else C((.62, .60, .70))))
        for z in range(22, 30):
            disc(o, 0, 0, z, max(0, 6 - (z - 22)), C((.40, .25, .60)))
        gem(o, 0, 0, 30, 1, 4, PRISM2)
        box(o, -1, -5, 0, 2, 1, 3, WOOD)
        for z in (6, 12):
            box(o, 4, 0, z, 1, 1, 2, GLOW)
    elif n == "HarbourDock":
        box(o, -4, -14, 3, 9, 28, 1, WOOD)
        for y in range(-14, 15, 4):
            for x in (-4, 4):
                box(o, x, y, 0, 1, 1, 5, WOOD_D)
        box(o, 3, 10, 4, 1, 1, 2, IRON)
    elif n == "CrystalLampPost":
        box(o, 0, 0, 0, 1, 1, 10, IRON)
        box(o, -1, -1, 0, 3, 3, 1, IRON)
        gem(o, 0, 0, 10, 1, 4, GLOW)
    return o


def item(n):
    o = []
    if n.startswith("Chest"):
        wood = {"Wood": WOOD, "Iron": C((.40, .42, .48)), "Gilded": C((.55, .15, .20))}[n.split("_")[1]]
        trim = {"Wood": IRON, "Iron": IRON, "Gilded": GOLD}[n.split("_")[1]]
        box(o, -4, -3, 0, 9, 6, 4, wood)
        box(o, -4, -3, 3, 9, 6, 1, trim)
        if n.endswith("Open"):
            box(o, -4, -4, 4, 9, 1, 5, wood)                            # lid tipped back
            box(o, -3, -2, 4, 7, 4, 1, GOLD)                            # the loot glints
            box(o, -1, -1, 5, 2, 2, 1, GLOW)
        else:
            box(o, -4, -3, 4, 9, 6, 2, wood)
            box(o, -4, -3, 5, 9, 6, 1, trim)
            box(o, 0, 3, 2, 1, 1, 2, GOLD)
    elif n.startswith("Weapon"):
        k = n.split("_")[1]
        if k == "BladewardSword":
            box(o, 0, 0, 0, 1, 1, 4, WOOD_D); box(o, -2, 0, 4, 5, 1, 1, GOLD); box(o, 0, 0, 5, 1, 1, 14, C((.85, .88, .95))); box(o, 0, 0, 19, 1, 1, 1, PRISM)
        elif k == "RunecasterStaff":
            box(o, 0, 0, 0, 1, 1, 18, WOOD); gem(o, 0, 0, 18, 1, 5, C((.95, .40, .25))); box(o, -1, 0, 17, 3, 1, 1, GOLD)
        elif k == "LightmenderRod":
            box(o, 0, 0, 0, 1, 1, 14, CLOTH); disc(o, 0, 0, 14, 2, GOLD); gem(o, 0, 0, 15, 1, 3, GLOW)
        elif k == "ShadowstepDaggers":
            for x in (-2, 2):
                box(o, x, 0, 0, 1, 1, 2, WOOD_D); box(o, x, 0, 2, 1, 1, 6, C((.75, .78, .85)))
        elif k == "BeastcallerBow":
            for z in range(16):
                o.append((int(2 * math.sin(math.pi * z / 15)), 0, z, WOOD))
            box(o, 0, 0, 0, 1, 1, 16, CLOTH)
        elif k == "GearwrightWrench":
            box(o, 0, 0, 0, 1, 1, 10, IRON); box(o, -2, 0, 10, 5, 1, 2, IRON); box(o, -2, 0, 12, 1, 1, 2, IRON); box(o, 2, 0, 12, 1, 1, 2, IRON)
        elif k == "StarlancerLance":
            box(o, 0, 0, 0, 1, 1, 22, C((.70, .75, .85))); gem(o, 0, 0, 22, 1, 6, C((.85, .90, 1.0))); disc(o, 0, 0, 6, 2, GOLD)
        elif k == "ChronoseerStaff":
            box(o, 0, 0, 0, 1, 1, 16, WOOD_D); box(o, -2, -1, 16, 5, 3, 1, GOLD); box(o, -1, 0, 17, 3, 1, 2, C((.35, .80, .80)))
            box(o, -2, -1, 21, 5, 3, 1, GOLD); box(o, -1, 0, 19, 3, 1, 2, C((.90, .80, .45)))
    elif n.startswith("Potion"):
        c = {"Mendwater": C((.35, .85, .45)), "ManaDraught": C((.35, .55, .95)), "Clearwater": C((.75, .95, 1.0))}.get(n.split("_")[1])
        if c:
            disc(o, 0, 0, 0, 2, C((.85, .92, .95)))
            disc(o, 0, 0, 1, 2, c, 3)
            box(o, 0, 0, 4, 1, 1, 2, C((.85, .92, .95)))
            box(o, 0, 0, 6, 1, 1, 1, WOOD)
        else:   # EmberPlume: a revive feather
            for z in range(10):
                w = int(2 * math.sin(math.pi * z / 9))
                box(o, -w, 0, z, 2 * w + 1, 1, 1, C((1.0, .55, .20)) if z % 3 else C((1.0, .85, .35)))
            box(o, 0, 0, 0, 1, 1, 10, CLOTH)
    elif n.startswith("Shard"):
        c = {"Fire": (1.0, .40, .20), "Tide": (.25, .55, .95), "Gale": (.55, .95, .65), "Stone": (.80, .62, .35), "Light": (1.0, .95, .65), "Shade": (.45, .25, .65)}[n.split("_")[1]]
        gem(o, 0, 0, 0, 2, 9, C(c), C(tuple(min(1, x + .25) for x in c)))
    return o


STRUCTURES = ("PrismShrine", "Waystone", "Skyfarer", "CastleGate", "TownHouse", "Inn", "ItemShop", "ArmsShop", "SpellTower", "Chapel", "HarbourDock", "CrystalLampPost")
ITEMS = tuple("Chest_%s_%s" % (m, s) for m in ("Wood", "Iron", "Gilded") for s in ("Closed", "Open")) + \
    tuple("Weapon_" + w for w in ("BladewardSword", "RunecasterStaff", "LightmenderRod", "ShadowstepDaggers", "BeastcallerBow", "GearwrightWrench", "StarlancerLance", "ChronoseerStaff")) + \
    tuple("Potion_" + p for p in ("Mendwater", "ManaDraught", "Clearwater", "EmberPlume")) + tuple("Shard_" + s for s in ("Fire", "Tide", "Gale", "Stone", "Light", "Shade"))
CATALOG = {}
for s in STRUCTURES:
    CATALOG["Bld_Prism_" + s] = ("structure", 25.0)
for i in ITEMS:
    CATALOG["Prop_Prism_" + i] = ("item", 10.0)


def plan(name):
    fam, _ = CATALOG[name]
    short = name.split("_", 2)[2]
    return structure(short) if fam == "structure" else item(short)


def build(name, out_dir):
    import bpy
    import voxel_island as V
    fam, cm = CATALOG[name]
    vox = plan(name)
    ob = V._mesh_from_voxels(name, vox, scale=cm, pal=PAL)
    zmin = min(z for _, _, z, _ in vox)
    for v in ob.data.vertices:
        v.co.z -= zmin * cm
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")
    with open(out[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "realm": "Prismheart Realm", "family": fam, "voxel_cm": cm, "voxels": len(vox), "pivot": "bottom-centre"}, f, indent=1)
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


if __name__ == "__main__":
    miss = {c for n in CATALOG for *_, c in plan(n) if c not in PAL}
    empty = [n for n in CATALOG if not plan(n)]
    print(len(CATALOG), "props; empty", empty, "missing", miss)
