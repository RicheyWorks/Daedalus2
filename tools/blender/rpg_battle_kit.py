# SPDX-License-Identifier: MIT
"""Battle-screen kit for the Portal Realm (8-bit) and the Prismheart Realm (16-bit).

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/rpg_battle_kit.py -- OUT_ROOT [backdrops] [party] [bosses] [icons] [--force]

* backdrops — one per encounter zone per realm: a small voxel diorama (sky gradient, terrain strip, the zone's trees /
  rocks / walls / water from voxel_flora and simple kit pieces) rendered wide and pixelated
  (Portal 256×144 grid ×4, ≤ 16 colours; Prismheart 320×180 grid ×4, ≤ 40 colours) → Backdrop_<Realm>_<zone>.png
* party — Prismheart job heroes (3/4 view facing left, toward the enemies) and the Portal party (hero, sage, scout)
  → Party_<Realm>_<Job>.png
* bosses — the nine Prismheart bosses (rpg_bosses.py): battle sprites + rigged GLB/FBX/json → claude-bestiary/prism-bosses/
* icons — 32-px menu icons for every Prismheart item (realm_prism_props items) → Icon_Prism_<Item>.png
All to OUT_ROOT/claude-battle-kit/<realm>/ (bosses' sprites also to claude-battle-sprites/prism/), plus sheets.
"""
import json
import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
root = os.path.abspath(argv[0])
parts = [a for a in argv[1:] if not a.startswith("--")] or ["backdrops", "party", "bosses", "icons"]
force = "--force" in argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voxel_island as V  # noqa: E402
import voxel_flora as F  # noqa: E402
import voxel_creatures as VC  # noqa: E402
import realm_rpg_cast as RC  # noqa: E402
import realm_prism_props as PP  # noqa: E402
import rpg_bosses as RB  # noqa: E402
import pixel_art as PX  # noqa: E402

KIT = os.path.join(root, "claude-battle-kit")
TMP = os.path.join(KIT, "_render.png")

# zone -> sky top, sky bottom, ground, ground2, props [(flora name, count)], feature
ZONES = {
    "meadow":      ((.35, .60, .95), (.75, .88, 1.0), (.35, .62, .28), (.45, .72, .32), [("Prop_Tree_Oak_Mature", 3), ("Prop_Shrub_Berry_Bush", 4), ("Prop_Cloud_Cumulus_White", 2)], None),
    "plains":      ((.40, .62, .95), (.80, .90, 1.0), (.50, .68, .30), (.62, .75, .36), [("Prop_Tree_Apple_Mature", 2), ("Prop_Cloud_Cumulus_Big", 2)], None),
    "plains_far":  ((.55, .55, .80), (.95, .80, .70), (.55, .58, .30), (.66, .62, .34), [("Prop_Tree_Baobab_Mature", 2), ("Prop_Cloud_Gold_Evening", 2)], None),
    "forest":      ((.25, .45, .55), (.55, .70, .65), (.22, .42, .20), (.30, .50, .22), [("Prop_Tree_Pine_Ancient", 5), ("Prop_Tree_Oak_Ancient", 3), ("Prop_Shrub_Bramble", 4)], None),
    "hills":       ((.40, .62, .92), (.80, .90, 1.0), (.40, .58, .30), (.55, .52, .38), [("Prop_Tree_Larch_Mature", 3), ("Prop_Cloud_Stratus_Grey", 1)], "hills"),
    "swamp":       ((.30, .38, .32), (.55, .62, .50), (.28, .35, .22), (.22, .32, .28), [("Prop_Tree_Mangrove_Mature", 3), ("Prop_Tree_Willow_Mature", 2), ("Prop_Cloud_Fog_Bank", 2)], "water_low"),
    "desert":      ((.45, .65, .95), (.98, .88, .70), (.88, .74, .45), (.80, .62, .38), [("Prop_Tree_Saguaro_Mature", 4), ("Prop_Tree_Joshua_Mature", 1)], "dunes"),
    "snow":        ((.55, .65, .85), (.88, .92, 1.0), (.92, .95, 1.0), (.80, .86, .95), [("Prop_Tree_Snow_Pine_Mature", 5), ("Prop_Cloud_Snow_Cloud", 2)], None),
    "mountain":    ((.35, .50, .85), (.75, .85, 1.0), (.50, .48, .46), (.62, .60, .58), [("Prop_Tree_Spruce_Mature", 2), ("Prop_Cloud_Stratus_Grey", 2)], "peaks"),
    "coast":       ((.40, .65, .95), (.82, .92, 1.0), (.90, .82, .58), (.85, .76, .50), [("Prop_Tree_Palm_Mature", 3), ("Prop_Cloud_Cumulus_White", 2)], "sea_back"),
    "sea":         ((.40, .62, .95), (.80, .90, 1.0), (.15, .40, .65), (.25, .55, .80), [("Prop_Cloud_Cumulus_Big", 3)], "sea_full"),
    "cave":        ((.06, .05, .07), (.12, .10, .12), (.30, .26, .24), (.22, .20, .19), [], "cave"),
    "crystal_cave": ((.08, .06, .14), (.18, .12, .26), (.30, .28, .40), (.24, .20, .34), [("Prop_Tree_Crystal_Tree_Mature", 3)], "cave_crystal"),
    "sea_cave":    ((.05, .08, .12), (.10, .18, .24), (.25, .30, .32), (.15, .35, .45), [], "cave_water"),
    "castle":      ((.10, .08, .12), (.20, .16, .20), (.45, .40, .38), (.55, .20, .22), [], "castle"),
    "tower":       ((.12, .10, .20), (.26, .20, .36), (.45, .42, .50), (.35, .30, .45), [], "tower"),
    "crypt":       ((.05, .05, .08), (.14, .12, .18), (.30, .30, .34), (.22, .22, .26), [], "crypt"),
    "graveyard":   ((.18, .16, .30), (.42, .36, .55), (.25, .32, .22), (.30, .30, .28), [("Prop_Tree_Dead_Ancient", 3), ("Prop_Cloud_Storm_Dark", 2)], "graves"),
    "town_ruins":  ((.45, .45, .60), (.80, .72, .65), (.45, .42, .35), (.55, .50, .42), [("Prop_Tree_Dead_Mature", 1)], "ruins"),
    "ruins":       ((.45, .55, .80), (.85, .82, .75), (.45, .52, .32), (.60, .58, .50), [("Prop_Tree_Oak_Ancient", 1)], "ruins"),
    "sewer":       ((.08, .10, .08), (.16, .20, .16), (.30, .32, .28), (.20, .32, .22), [], "sewer"),
    "volcano":     ((.35, .10, .08), (.85, .35, .15), (.18, .14, .13), (.30, .12, .08), [("Prop_Tree_Ember_Tree_Mature", 2), ("Prop_Cloud_Ash_Cloud", 3)], "lava"),
    "airship":     ((.30, .55, .95), (.80, .90, 1.0), (.55, .38, .22), (.45, .30, .18), [("Prop_Cloud_Cumulus_Big", 4)], "deck"),
}
STYLE = {"portal": {"gw": 256, "gh": 144, "colors": 16, "res": (1024, 576), "sprite_grid": 64, "sprite_colors": 7, "outline": (.02, .02, .03)},
         "prism": {"gw": 320, "gh": 180, "colors": 40, "res": (1280, 720), "sprite_grid": 112, "sprite_colors": 24, "outline": None}}


def zones_for(realm):
    p = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rpg", "%s-encounters.json" % realm)
    with open(p, encoding="utf-8") as f:
        return sorted({z.replace("_deep", "") for z in json.load(f)["zones"]})


def clear():
    bpy.data.batch_remove([o for o in bpy.data.objects if o.name != "KitCam"])
    bpy.data.batch_remove([m for m in bpy.data.meshes if m.users == 0])


def cam_get():
    sc = bpy.context.scene
    cam = bpy.data.objects.get("KitCam") or bpy.data.objects.new("KitCam", bpy.data.cameras.new("KitCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def workbench(transparent):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
    sc.display.shadow_focus = .6
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "Standard"     # AgX (4.x default) desaturates the palette
    sc.view_settings.look = "None"
    sc.render.image_settings.color_mode = "RGBA"
    sc.world = bpy.data.worlds.new("Sky") if sc.world is None else sc.world
    sc.world.use_nodes = False
    sc.world.color = (0, 0, 0)


def vox_obj(name, vox, cm, loc=(0, 0, 0), rot_z=0.0, pal=None):
    ob = V._mesh_from_voxels(name, vox, scale=cm, pal=pal or RC.PAL)
    for v in ob.data.vertices:
        v.co /= 100.0
    ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return ob


def sky(top, bot, w=120, h=50, y=40):
    me = bpy.data.meshes.new("Sky")
    verts = [(-w / 2, y, -5), (w / 2, y, -5), (w / 2, y, h), (-w / 2, y, h)]
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    ca = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    cols = [bot, bot, top, top]
    for i, li in enumerate(me.polygons[0].loop_indices):
        ca.data[li].color = (*[c ** (1 / 2.2) for c in cols[i]], 1)
    me.color_attributes.active_color = ca
    ob = bpy.data.objects.new("Sky", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ground_strip(name, c1, c2, rng, feature):
    """A 60 m × 30 m voxel strip at 50 cm — ground in front of the camera, height noise by feature."""
    vox = []
    a, b = RC.col(c1), RC.col(c2)
    for x in range(-60, 60):
        for y in range(-10, 50):
            hgt = 1
            if feature == "hills" and y > 20:
                hgt += int(6 * (1 + math.sin(x / 9 + y / 13)) * (y - 20) / 30)
            elif feature == "dunes":
                hgt += int(2 * (1 + math.sin(x / 7 + y / 5)))
            elif feature == "peaks" and y > 15:
                hgt += int(max(0, 22 - abs(((x + 60) % 40) - 20) * 1.1) * (y - 15) / 35)
            elif feature in ("water_low",) and 5 < y < 20 and abs(x) > 8:
                hgt = 0
            c = a if (rng.random() < .7) else b
            for z in range(hgt):
                vox.append((x, y, z, c if z == hgt - 1 else b))
    if feature in ("sea_back", "sea_full", "water_low", "cave_water"):
        w = RC.col((.20, .45, .70) if feature != "cave_water" else (.12, .30, .38))
        w2 = RC.col((.40, .65, .85) if feature != "cave_water" else (.18, .42, .50))
        y0 = -10 if feature == "sea_full" else (24 if feature == "sea_back" else 6)
        y1 = 50 if feature != "water_low" else 20
        for x in range(-60, 60):
            for y in range(y0, y1):
                vox.append((x, y, 1 if feature != "water_low" else 0, w2 if (x + y * 3) % 11 == 0 else w))
    if feature == "lava":
        lv = RC.col((1.0, .45, .08))
        for x in range(-60, 60):
            for y in range(15, 30):
                if math.sin(x / 5) + math.cos(y / 3) > .6:
                    vox.append((x, y, 1, lv))
    return vox_obj(name, vox, 50)


def walls(kind, c1, c2, rng):
    """Interior zones: a back wall of blocks with arches, pillars, torches, crystals, graves, crates, pipes."""
    vox = []
    a, b = RC.col(c1), RC.col(c2)
    glow = RC.col((1.0, .75, .30))
    for x in range(-60, 60):
        for z in range(0, 40):
            c = a if ((x // 4 + z // 2) % 2 or kind in ("cave", "cave_crystal", "cave_water")) else b
            depth = 0
            if kind.startswith("cave"):
                depth = int(3 * (1 + math.sin(x / 4 + z / 6) * math.cos(z / 5)))
            for dy in range(depth + 1):
                vox.append((x, 34 - dy, z, c))
    if kind in ("castle", "tower", "crypt", "sewer"):
        for x in range(-50, 51, 20):
            for z in range(0, 34):
                for dx in range(3):
                    vox.append((x + dx, 28, z, b))
            for z in range(14, 17):
                vox.append((x + 1, 27, z, glow))
        if kind == "castle":
            ban = RC.col((.65, .12, .18))
            for x in range(-40, 41, 20):
                for z in range(16, 30):
                    for dx in range(4):
                        vox.append((x + 8 + dx, 33, z, ban))
        if kind == "sewer":
            wt = RC.col((.25, .40, .28))
            for x in range(-60, 60):
                for y in range(10, 20):
                    vox.append((x, y, 1, wt))
    if kind == "cave_crystal":
        cr = RC.col((.70, .55, 1.0))
        cr2 = RC.col((.45, .85, 1.0))
        for i in range(14):
            x, y = rng.randint(-50, 50), rng.randint(20, 32)
            for z in range(rng.randint(4, 12)):
                vox.append((x, y, z, cr if i % 2 else cr2))
                if z < 4:
                    vox.append((x + 1, y, z, cr if i % 2 else cr2))
    return vox_obj("Walls", vox, 50)


def kit_props(feature, rng):
    obs = []
    stone = RC.col((.55, .55, .58))
    if feature == "graves":
        for i in range(8):
            vox = [(x, 0, z, stone) for x in range(3) for z in range(5)] + [(1, 0, 5, stone)]
            obs.append(vox_obj("Grave%d" % i, vox, 50, (rng.uniform(-22, 22), rng.uniform(4, 16), .5)))
    elif feature == "ruins":
        for i in range(6):
            h = rng.randint(4, 14)
            vox = [(x, y, z, stone) for x in range(3) for y in range(3) for z in range(h)]
            obs.append(vox_obj("Pillar%d" % i, vox, 50, (rng.uniform(-24, 24), rng.uniform(8, 20), .5)))
    elif feature == "deck":
        wood, rail = RC.col((.55, .38, .22)), RC.col((.95, .78, .25))
        vox = [(x, 0, z, rail) for x in range(-60, 60) for z in (0, 3)] + [(x, 0, z, wood) for x in range(-60, 60, 6) for z in range(4)]
        obs.append(vox_obj("Rail", vox, 50, (0, 12, .5)))
    return obs


def render_backdrops():
    workbench(False)
    sc, cam = cam_get()
    cam.data.type = "PERSP"
    cam.data.lens = 28
    cam.location, cam.rotation_euler = (0, -6, 3.2), (math.radians(84), 0, 0)
    out = {}
    for realm in ("portal", "prism"):
        st = STYLE[realm]
        od = os.path.join(KIT, realm)
        os.makedirs(od, exist_ok=True)
        sc.render.resolution_x, sc.render.resolution_y = st["res"]
        tiles = []
        for z in zones_for(realm):
            name = "Backdrop_%s_%s" % ("Portal" if realm == "portal" else "Prism", z)
            path = os.path.join(od, name + ".png")
            if os.path.exists(path) and not force:
                tiles.append(PX.load(path)[::4, ::4])
                continue
            clear()
            top, bot, g1, g2, props, feat = ZONES[z]
            rng = random.Random(len(z) * 131 + (7 if realm == "prism" else 0))
            sky(top, bot)
            ground_strip("Ground", g1, g2, rng, feat)
            if feat in ("cave", "cave_crystal", "cave_water", "castle", "tower", "crypt", "sewer"):
                walls(feat, g1, g2, rng)
            kit_props(feat, rng)
            for pname, n in props:
                if pname not in F.CATALOG:
                    continue
                fam, cm = F.CATALOG[pname]
                vox = F.plan(pname)
                for i in range(n):
                    if fam == "cloud":
                        loc = (rng.uniform(-22, 22), rng.uniform(26, 36), rng.uniform(10, 18))
                    else:
                        side = -1 if i % 2 == 0 else 1
                        loc = (side * rng.uniform(6, 20), rng.uniform(10, 26), .5)
                    vox_obj("%s_%d" % (pname, i), vox, cm, loc, rng.uniform(0, 6.3), pal=F.PAL)
            sc.render.filepath = TMP
            bpy.ops.render.render(write_still=True)
            arr = PX.backdrop(PX.load(TMP), st["gw"], st["gh"], st["colors"])
            PX.save(PX.upscale(arr, 4), path)
            PX.save(arr, os.path.join(od, name + "_1x.png"))
            tiles.append(arr)
            out.setdefault(realm, []).append(name)
            print("BACKDROP %s" % name, flush=True)
        PX.sheet(tiles, os.path.join(od, "sheet-backdrops-%s.png" % realm), st["gw"] + 8, st["gh"] + 8)
    return out


def sprite_of(parts, cm, st, yaw, elev, path):
    """Shared sprite render: ortho, transparent, pixelate with the realm's style."""
    workbench(True)
    sc, cam = cam_get()
    sc.render.resolution_x = sc.render.resolution_y = st["sprite_grid"] * (6 if st["sprite_grid"] == 64 else 4)
    clear()
    vox = [v for vs in parts.values() for v in vs] if isinstance(parts, dict) else parts
    ob = vox_obj("Subject", vox, cm, rot_z=math.radians(yaw))
    bpy.context.view_layer.update()
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
    hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
    ctr, size = (lo + hi) / 2, max(hi.x - lo.x, hi.z - lo.z, (hi.y - lo.y) * .6)
    el, dist = math.radians(elev), size * 4
    cam.data.type = "ORTHO"
    cam.location = (ctr.x, ctr.y + dist * math.cos(el), ctr.z + dist * math.sin(el))
    cam.rotation_euler = (Vector(ctr) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale, cam.data.clip_end = size * 1.12, dist * 4
    sc.render.filepath = TMP
    bpy.ops.render.render(write_still=True)
    arr = PX.sprite(PX.load(TMP), st["sprite_grid"], st["sprite_colors"], st["outline"])
    PX.save(PX.upscale(arr, 4), path)
    PX.save(arr, path[:-4] + "_1x.png")
    return arr


def render_party():
    rows = []
    for realm in ("prism", "portal"):
        st = STYLE[realm]
        od = os.path.join(KIT, realm)
        os.makedirs(od, exist_ok=True)
        tiles = []
        if realm == "prism":
            subjects = [("Party_Prism_%s" % job, RC.plan("prism_hero_%s_01" % job.lower())) for job in RC.PRISM_JOBS]
            yaw, elev = 35.0, 12.0          # 3/4, facing left toward the enemies
        else:
            rng = random.Random(3)
            subjects = [("Party_Portal_Hero", RC.humanoid(RC.SKINS[0], RC.col((.25, .35, .70)), trim=RC.col((.95, .78, .25)), hair=RC.col((.35, .2, .1)),
                                                          tool=RC.col((.8, .82, .88)), tool_kind="sword", shield=RC.col((.70, .15, .20)), cape=RC.col((.70, .15, .20)))),
                        ("Party_Portal_Sage", RC.humanoid(RC.SKINS[1], RC.col((.30, .55, .40)), trim=RC.col((.95, .95, .9)), hat=RC.col((.30, .55, .40)), hat_style="point",
                                                          tool=RC.col((.55, .35, .2)), tool_kind="staff", beard=RC.col((.9, .9, .9)))),
                        ("Party_Portal_Scout", RC.humanoid(RC.SKINS[2], RC.col((.55, .40, .25)), trim=RC.col((.35, .25, .15)), hat=RC.col((.40, .45, .30)), hat_style="hood",
                                                           tool=RC.col((.55, .40, .2)), tool_kind="bow"))]
            yaw, elev = 28.0, 16.0
        for name, parts in subjects:
            path = os.path.join(od, name + ".png")
            if os.path.exists(path) and not force:
                tiles.append(PX.load(path[:-4] + "_1x.png"))
                continue
            tiles.append(sprite_of(parts, 10, st, yaw, elev, path))
            rows.append(name)
            print("PARTY %s" % name, flush=True)
        PX.sheet(tiles, os.path.join(od, "sheet-party-%s.png" % realm), st["sprite_grid"] + 8)
    return rows


def render_bosses():
    st = STYLE["prism"]
    od = os.path.join(root, "claude-battle-sprites", "prism")
    rd = os.path.join(root, "claude-bestiary", "prism-bosses")
    os.makedirs(od, exist_ok=True)
    tiles = []
    for k in RB.KEYS:
        name = "Battle_Prism_Boss_%s" % RB.KEYS[k][0]
        path = os.path.join(od, name + ".png")
        if not os.path.exists(path) or force:
            tiles.append(sprite_of(RB.plan(k), 10, st, -35.0, 14.0, path))
            print("BOSS %s" % name, flush=True)
        else:
            tiles.append(PX.load(path[:-4] + "_1x.png"))
        if not os.path.exists(os.path.join(rd, VC.NAMES[k] + ".glb")) or force:
            clear()
            VC.build(k, rd, scale=10.0)
    PX.sheet(tiles, os.path.join(od, "sheet-prism-bosses.png"), st["sprite_grid"] + 8)


def render_icons():
    st = {"sprite_grid": 32, "sprite_colors": 10, "outline": (.05, .04, .06)}
    od = os.path.join(KIT, "prism", "icons")
    os.makedirs(od, exist_ok=True)
    tiles = []
    for n, (fam, cm) in PP.CATALOG.items():
        if fam != "item":
            continue
        name = n.replace("Prop_Prism_", "Icon_Prism_")
        path = os.path.join(od, name + ".png")
        if os.path.exists(path) and not force:
            tiles.append(PX.load(path[:-4] + "_1x.png"))
            continue
        sty = dict(st)
        workbench(True)
        sc, _ = cam_get()
        sc.render.resolution_x = sc.render.resolution_y = 256
        # sprite_of wants grid*6 or *4; icons: 32 grid from 256 = ×8 blocks
        tiles.append(_icon(PP.plan(n), cm, sty, path))
        print("ICON %s" % name, flush=True)
    PX.sheet(tiles, os.path.join(od, "sheet-icons-prism.png"), 40)


def _icon(vox, cm, st, path):
    sc, cam = cam_get()
    clear()
    ob = vox_obj("Icon", [(x, y, z, c) for x, y, z, c in vox], cm, rot_z=math.radians(30), pal=PP.PAL)
    bpy.context.view_layer.update()
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
    hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
    ctr, size = (lo + hi) / 2, max(hi.x - lo.x, hi.z - lo.z, hi.y - lo.y)
    el, dist = math.radians(25), size * 4
    cam.data.type = "ORTHO"
    cam.location = (ctr.x, ctr.y + dist * math.cos(el), ctr.z + dist * math.sin(el))
    cam.rotation_euler = (Vector(ctr) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale, cam.data.clip_end = size * 1.15, dist * 4
    sc.render.filepath = TMP
    bpy.ops.render.render(write_still=True)
    arr = PX.sprite(PX.load(TMP), 32, st["sprite_colors"], st["outline"])
    PX.save(PX.upscale(arr, 4), path)
    PX.save(arr, path[:-4] + "_1x.png")
    return arr


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
os.makedirs(KIT, exist_ok=True)
t0 = time.time()
if "backdrops" in parts:
    render_backdrops()
if "party" in parts:
    render_party()
if "bosses" in parts:
    render_bosses()
if "icons" in parts:
    render_icons()
if os.path.exists(TMP):
    os.replace(TMP, os.path.join(KIT, "_last_render.png"))
print("KIT DONE %.0fs" % (time.time() - t0), flush=True)
