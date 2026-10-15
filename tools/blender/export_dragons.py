# SPDX-License-Identifier: MIT
"""Headless: all 504 flying dragons as rigged GLB + FBX + json, plus one contact sheet per element (42 dragons each).
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_dragons.py -- OUT_DIR [element ...] [--force] [--no-sheet]
"""
import json
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
out_dir = os.path.abspath(argv[0])
want = [a for a in argv[1:] if not a.startswith("--")] or None
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_creatures as VC  # noqa: E402
import voxel_dragons as D  # noqa: E402
import voxel_island as V  # noqa: E402

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "dragons.manifest.json"), "w", encoding="utf-8") as f:
    json.dump(D.manifest(), f, indent=1)
t0 = time.time()
done = 0
for n in D.NAMES:
    el = n.split("_")[1]
    if want and el not in want:
        continue
    name = "Creature_" + "".join(w.capitalize() for w in n.split("_"))
    if os.path.exists(os.path.join(out_dir, name + ".glb")) and "--force" not in argv:
        continue
    VC.build(n, out_dir)
    done += 1
    if done % 50 == 0:
        print("DRAGONS %d %.0fs" % (done, time.time() - t0), flush=True)
print("EXPORTED %d dragons in %.0fs -> %s" % (done, time.time() - t0, out_dir), flush=True)

if "--no-sheet" not in argv:
    for el in (want or list(D.ELEMENTS)):
        names = [n for n in D.NAMES if n.split("_")[1] == el]
        cols = int(math.ceil(math.sqrt(len(names) * 1.6)))
        pitch = 6.5
        obs = []
        for i, n in enumerate(names):
            vox = [v for vs in D.plan(n).values() for v in vs]
            ob = V._mesh_from_voxels(n, vox, scale=10.0, pal=D.PAL)
            ob.location = ((i % cols) * pitch - (cols - 1) * pitch / 2, -(i // cols) * pitch, 0)
            for v in ob.data.vertices:
                v.co /= 100.0
            ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
            ob.rotation_euler.z = 3.14159 * (0.85 if "owl" in "export_dragons.py" else 1.0) if True else 0   # face the camera
            obs.append(ob)
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
        scene.render.resolution_x, scene.render.resolution_y = 2000, 1250
        scene.world = bpy.data.worlds.new("Sky") if scene.world is None else scene.world
        scene.world.use_nodes = False
        scene.world.color = (0.62, 0.72, 0.88)
        cam = bpy.data.objects.get("Cam") or bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        if cam.name not in scene.collection.objects:
            scene.collection.objects.link(cam)
        scene.camera = cam
        cam.data.lens, cam.data.clip_end = 35, 100000
        rows = int(math.ceil(len(names) / cols))
        span = max(cols, rows) * pitch
        cam.location = (0, -(rows * pitch) / 2 - span * 0.9, span * 0.7)
        cam.rotation_euler = (math.radians(50), 0, 0)
        scene.render.filepath = os.path.join(out_dir, "sheet-%s.png" % el)
        bpy.ops.render.render(write_still=True)
        print("SHEET " + scene.render.filepath, flush=True)
        for ob in obs:
            bpy.data.objects.remove(ob, do_unlink=True)
        for me in list(bpy.data.meshes):
            if me.users == 0:
                bpy.data.meshes.remove(me)
