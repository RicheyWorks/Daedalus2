# SPDX-License-Identifier: MIT
"""Battle-screen enemy sprites for the random-encounter screens.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/render_battle_sprites.py -- OUT_ROOT [portal|prism ...] [--rigs] [--force]

Every enemy type — the 320 bestiary types (rpg_bestiary.py), the Portal population-plan enemies and bosses and the
Prismheart cast monsters and summons (realm_rpg_cast.py, individual 01) — is rendered with an orthographic camera and
a transparent background, then pixelated in numpy inside Blender (no PIL needed on the PC):
  Portal (8-bit):    384 px render -> 64 px grid, at most 6 colours + a black outline, shown ×4 = 256 px, facing you
  Prismheart (16-bit): 448 px render -> 112 px grid, at most 24 colours + a dark outline, ×4 = 448 px, 3/4 view facing
                     the party's side (right)
Outputs OUT_ROOT/claude-battle-sprites/<realm>/Battle_<Name>.png (+ _1x.png native size), sprites.json (name, file,
tier, stats ref) and sheet-<realm>.png. With --rigs it also exports the 320 bestiary bodies as rigged GLB/FBX/json to
OUT_ROOT/claude-bestiary/<realm>/ (same rig and clips as every creature).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
root = os.path.abspath(argv[0])
want = [a for a in argv[1:] if a in ("portal", "prism")] or ["portal", "prism"]
force = "--force" in argv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voxel_creatures as VC  # noqa: E402
import realm_rpg_cast as RC  # noqa: E402
import rpg_bestiary as BE  # noqa: E402
import voxel_island as V  # noqa: E402

STYLE = {"portal": {"res": 384, "grid": 64, "colors": 7, "outline": (0.02, 0.02, 0.03), "yaw": 28.0, "elev": 16.0},
         "prism": {"res": 448, "grid": 112, "colors": 24, "outline": None, "yaw": -35.0, "elev": 14.0}}


def roster(realm):
    """(sprite name, plan key, voxel cm, meta) for every enemy that can appear on that realm's battle screen."""
    out = []
    for k in BE.types(realm):
        r = BE.TYPES[k]
        out.append((r["export_name"].replace("Mob_", "Battle_"), k, r["voxel_cm"], {"source": "bestiary", "name": r["name"], "tier": r["tier"],
                    "level": r["level"], "line": r["line"], "key": k}))
    for k, (fam, fn, cm, name, meta) in RC.ROSTER.items():
        ok = (realm == "portal" and fam in ("portal_enemy", "portal_boss")) or (realm == "prism" and fam in ("prism_monster", "prism_summon"))
        if not ok or (meta.get("individual", 1) != 1):
            continue
        out.append((name.replace("Mob_", "Battle_").replace("_Voxel_01", "").replace("_01", ""), k, cm,
                    {"source": "population_plan" if realm == "portal" else "cast", "name": meta.get("type"), "faction": meta.get("faction"), "key": k}))
    return out


def plan_of(key):
    return BE.plan(key) if key in BE.TYPES else RC.plan(key)


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", False, True
    sh.cavity_type = "WORLD"
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    cam = bpy.data.objects.get("SpriteCam") or bpy.data.objects.new("SpriteCam", bpy.data.cameras.new("SpriteCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    sc.camera = cam
    return sc, cam


def pixelate(path_in, path_out, path_1x, st):
    img = bpy.data.images.load(path_in)
    img.colorspace_settings.name = "Non-Color"      # read the PNG's bytes as they are (sRGB-encoded), no linearising
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    g = st["grid"]
    b = w // g
    blk = px[:g * b, :g * b].reshape(g, b, g, b, 4)
    a = blk[..., 3]
    asum = a.sum(axis=(1, 3))
    rgb = (blk[..., :3] * a[..., None]).sum(axis=(1, 3)) / np.maximum(asum, 1e-6)[..., None]
    alpha = (asum / (b * b)) > .45
    lum = rgb.mean(-1, keepdims=True)
    rgb = np.clip(lum + (rgb - lum) * 1.25, 0, 1) ** .9          # punchier, like hand-picked console palettes
    # colour limit: quantise to a coarse lattice, keep the N most common, snap every pixel to its nearest
    lat = np.round(rgb * 7) / 7
    cols, counts = np.unique(lat[alpha].reshape(-1, 3), axis=0, return_counts=True) if alpha.any() else (np.zeros((1, 3)), np.ones(1))
    top = cols[np.argsort(-counts)[:st["colors"]]]
    d = ((rgb[:, :, None, :] - top[None, None, :, :]) ** 2).sum(-1)
    q = top[np.argmin(d, axis=-1)]
    # outline: pixels next to the sprite but outside it
    m = alpha
    dil = m.copy()
    dil[1:] |= m[:-1]
    dil[:-1] |= m[1:]
    dil[:, 1:] |= m[:, :-1]
    dil[:, :-1] |= m[:, 1:]
    edge = dil & ~m
    out = np.zeros((g, g, 4), dtype=np.float32)
    out[m, :3] = q[m]
    out[m, 3] = 1
    oc = st["outline"]
    if oc is None:      # 16-bit: a darker shade of the neighbouring colour
        nb = np.zeros_like(q)
        for sh_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.where(np.roll(m, sh_, axis=(0, 1))[..., None] & (nb.sum(-1, keepdims=True) == 0), np.roll(q, sh_, axis=(0, 1)), nb)
        out[edge, :3] = nb[edge] * .35
    else:
        out[edge, :3] = oc
    out[edge, 3] = 1
    for arr, path, k in ((out, path_1x, 1), (np.repeat(np.repeat(out, 4, axis=0), 4, axis=1), path_out, 4)):
        im = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
        im.pixels.foreach_set(arr.ravel())
        im.filepath_raw = path
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)
    return out


def sheet(sprites, path, cell):
    n = len(sprites)
    cols = int(math.ceil(math.sqrt(n * 1.6)))
    rows = int(math.ceil(n / cols))
    canvas = np.zeros((rows * cell, cols * cell, 4), dtype=np.float32)
    canvas[..., :3] = (.10, .10, .16)     # the black-blue battle backdrop
    canvas[..., 3] = 1
    for i, s in enumerate(sprites):
        r, c = rows - 1 - i // cols, i % cols
        hh, ww = s.shape[:2]
        y0, x0 = r * cell + (cell - hh) // 2, c * cell + (cell - ww) // 2
        a = s[..., 3:4]
        canvas[y0:y0 + hh, x0:x0 + ww, :3] = canvas[y0:y0 + hh, x0:x0 + ww, :3] * (1 - a) + s[..., :3] * a
    im = bpy.data.images.new("sheet", canvas.shape[1], canvas.shape[0], alpha=True)
    im.pixels.foreach_set(canvas.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc, cam = setup_scene()
t0 = time.time()
for realm in want:
    st = STYLE[realm]
    od = os.path.join(root, "claude-battle-sprites", realm)
    os.makedirs(od, exist_ok=True)
    tmp = os.path.join(od, "_render.png")
    sc.render.resolution_x = sc.render.resolution_y = st["res"]
    rows, small = [], []
    for name, key, cm, meta in roster(realm):
        out_png, out_1x = os.path.join(od, name + ".png"), os.path.join(od, name + "_1x.png")
        if os.path.exists(out_1x) and not force:
            im = bpy.data.images.load(out_1x)
            im.colorspace_settings.name = "Non-Color"
            small.append(np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4))
            bpy.data.images.remove(im)
            rows.append(dict(meta, sprite=name + ".png", sprite_1x=name + "_1x.png"))
            continue
        vox = [v for vs in plan_of(key).values() for v in vs]
        ob = V._mesh_from_voxels(name, vox, scale=cm, pal=RC.PAL)
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
        ob.rotation_euler.z = math.radians(st["yaw"])
        bpy.context.view_layer.update()
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
        hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
        ctr = (lo + hi) / 2
        size = max(hi.x - lo.x, hi.z - lo.z, (hi.y - lo.y) * .6)
        el = math.radians(st["elev"])
        dist = size * 4
        cam.location = (ctr.x, ctr.y + dist * math.cos(el), ctr.z + dist * math.sin(el))
        cam.rotation_euler = (Vector(ctr) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = size * 1.12
        cam.data.clip_end = dist * 4
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        small.append(pixelate(tmp, out_png, out_1x, st))
        rows.append(dict(meta, sprite=name + ".png", sprite_1x=name + "_1x.png"))
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        if len(rows) % 50 == 0:
            print("SPRITES %s %d %.0fs" % (realm, len(rows), time.time() - t0), flush=True)
    if os.path.exists(tmp):
        os.replace(tmp, os.path.join(od, "_last_render.png"))
    with open(os.path.join(od, "sprites.json"), "w", encoding="utf-8") as f:
        json.dump({"realm": BE.REALM_NAME[realm], "style": st, "count": len(rows), "bestiary": "data/rpg/%s-bestiary.json" % realm,
                   "encounters": "data/rpg/%s-encounters.json" % realm, "sprites": rows}, f, indent=1)
    sheet(small, os.path.join(od, "sheet-%s.png" % realm), st["grid"] + 8)
    print("SHEET %s %d sprites" % (realm, len(rows)), flush=True)

if "--rigs" in argv:
    n = 0
    for realm in want:
        od = os.path.join(root, "claude-bestiary", realm)
        for k in BE.types(realm):
            r = BE.TYPES[k]
            if os.path.exists(os.path.join(od, r["export_name"] + ".glb")) and not force:
                continue
            VC.build(k, od, scale=float(r["voxel_cm"]))
            jp = os.path.join(od, r["export_name"] + ".json")
            j = json.load(open(jp, encoding="utf-8"))
            j.update({kk: v for kk, v in r.items() if not kk.startswith("_")})
            json.dump(j, open(jp, "w", encoding="utf-8"), indent=1)
            n += 1
    print("RIGS %d %.0fs" % (n, time.time() - t0), flush=True)
print("DONE %.0fs" % (time.time() - t0), flush=True)
