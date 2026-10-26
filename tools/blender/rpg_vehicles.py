# SPDX-License-Identifier: MIT
"""Prismheart world-map vehicles: the Prism Skiff airship, as a pixel sprite in the realm's 16-bit style.

    python rpg_vehicles.py OUT_ROOT [--force]          (bpy module)  |  blender -b --python rpg_vehicles.py -- OUT_ROOT

Writes OUT_ROOT/claude-battle-kit/prism/vehicles/Vehicle_Prism_Airship.png (x4) and _1x.png: a 32-px sprite seen from
the world map's high three-quarter view, bow to the right (the demo mirrors it to fly left), plus two frames in one
strip (propellers turning). Original design: a timber skiff under a striped teal-and-violet gas envelope, a prism
crystal at the bow, a stern propeller on each side. Voxels at 10 cm, rendered with Workbench vertex colour and
pixelated with tools/blender/pixel_art.py, the same path as the realm's party and boss sprites.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_art as PX  # noqa: E402
import realm_rpg_cast as RC  # noqa: E402
import voxel_island as V  # noqa: E402

GRID, COLORS = 32, 24               # sprite grid (px) and colour limit: the realm's prism style, at world-map size
ELEV, YAW = 28.0, 0.0                # low three-quarter view (the envelope reads over the hull), bow to screen right

WOOD, WOOD_D, DECK = RC.col((.55, .34, .18)), RC.col((.36, .22, .12)), RC.col((.72, .55, .34))
TEAL, VIOLET, TRIM = RC.col((.20, .70, .72)), RC.col((.50, .32, .78)), RC.col((.95, .85, .45))
CRYSTAL, ROPE, IRON = RC.col((.70, .95, 1.0)), RC.col((.82, .78, .62)), RC.col((.40, .42, .48))


def plan(prop_phase=0):
    """Voxels (x, y, z, colour): x along the ship (bow at +x), y across, z up."""
    vox = set()
    L, half = 22, 4
    for x in range(L):                                       # hull: a boat section that narrows to bow and stern
        t = x / (L - 1)
        w = max(1, int(round(half * math.sin(math.pi * (0.12 + 0.8 * t)))))
        depth = 3 if 3 < x < L - 4 else 2
        for y in range(-w, w + 1):
            for z in range(depth):
                if z == 0 and abs(y) == w:
                    continue                                 # rounded keel
                vox.add((x, y, z, WOOD_D if z < depth - 1 else WOOD))
            vox.add((x, y, depth, DECK))
        for y in (-w - 0, w):                                # gunwale trim
            vox.add((x, y, depth + 1, WOOD_D))
    for x in range(8, 13):                                   # cabin amidships
        for y in range(-2, 3):
            for z in range(4, 7):
                vox.add((x, y, z, WOOD if z < 6 else TRIM))
    for x, y in ((6, -2), (6, 2), (15, -2), (15, 2)):        # ropes up to the envelope
        for z in range(4, 10):
            vox.add((x, y, z, ROPE))
    cx, cz, rx, ry, rz = 10.5, 14.0, 10.5, 4.8, 4.6          # the gas envelope, striped lengthwise
    for x in range(0, 22):
        for y in range(-5, 6):
            for z in range(9, 20):
                if ((x - cx) / rx) ** 2 + (y / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1.0:
                    vox.add((x, y, z, TEAL if (x // 3) % 2 == 0 else VIOLET))
    for x in range(1, 21):                                   # trim band round the envelope's belly
        if ((x - cx) / rx) ** 2 <= .92:
            vox.add((x, 0, 9, TRIM))
    for z in range(2, 6):                                    # prism crystal at the bow
        for d in range(0, 3 - abs(z - 3)):
            for y in range(-d, d + 1):
                vox.add((L + d - 1, y, z, CRYSTAL))
    for side in (-1, 1):                                     # stern propellers on outriggers, two phases
        for y in range(1, 4):
            vox.add((1, side * (half + y - 1), 3, IRON))
        hub = (0, side * (half + 3), 3)
        blades = [(0, 0, 1), (0, 0, 2), (0, 0, -1), (0, 0, -2)] if prop_phase == 0 else [(0, 1, 0), (0, 2, 0), (0, -1, 0), (0, -2, 0)]
        vox.add((*hub, IRON))
        for dx, dy, dz in blades:
            vox.add((hub[0] + dx, hub[1] + dy, hub[2] + dz, ROPE))
    best = {}
    for x, y, z, c in vox:                                   # one colour per cell (later writes are details)
        best[(x, y, z)] = c
    return [(x, y, z, c) for (x, y, z), c in sorted(best.items())]


def render(out_root, force=False):
    od = os.path.join(out_root, "claude-battle-kit", "prism", "vehicles")
    os.makedirs(od, exist_ok=True)
    path = os.path.join(od, "Vehicle_Prism_Airship.png")
    if os.path.exists(path) and not force:
        return path
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
    sc.render.film_transparent = True
    sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_x = sc.render.resolution_y = GRID * 6
    cam = bpy.data.objects.new("VehCam", bpy.data.cameras.new("VehCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    frames, tmp = [], os.path.join(od, "_render.png")
    for phase in (0, 1):
        for o in [o for o in bpy.data.objects if o.name != "VehCam"]:
            bpy.data.objects.remove(o, do_unlink=True)
        ob = V._mesh_from_voxels("Airship", plan(phase), scale=10.0, pal=RC.PAL)
        for v in ob.data.vertices:
            v.co /= 100.0
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
        ob.rotation_euler.z = math.radians(YAW)
        bpy.context.view_layer.update()
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
        hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
        ctr, size = (lo + hi) / 2, max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
        el, dist = math.radians(ELEV), size * 4
        cam.data.type, cam.data.ortho_scale, cam.data.clip_end = "ORTHO", size * 1.1, dist * 4
        cam.location = (ctr.x, ctr.y - dist * math.cos(el), ctr.z + dist * math.sin(el))
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        frames.append(PX.sprite(PX.load(tmp), GRID, COLORS, (.06, .05, .09)))   # dark outline: it must read over any tile
    os.remove(tmp)
    import numpy as np
    strip = np.concatenate(frames, axis=1)                   # frame 0 | frame 1
    PX.save(PX.upscale(strip, 4), path)
    PX.save(strip, path[:-4] + "_1x.png")
    print("VEHICLE %s %dx%d" % (path[:-4] + "_1x.png", strip.shape[1], strip.shape[0]), flush=True)
    return path


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    render(os.path.abspath(a[0]), "--force" in a)
