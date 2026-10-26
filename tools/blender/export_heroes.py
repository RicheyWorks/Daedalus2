# SPDX-License-Identifier: MIT
"""Headless batch of hero-grade islands (Richey 14:15 "build more islands in blender"): seeds cycle through the
six kinds, each with its own chemistry roll; FBX + chemistry manifest + one Workbench preview per island.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_heroes.py -- 1000 1050 OUT_DIR [REALM]
"""
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
start, stop = int(argv[0]), int(argv[1])
out_dir = argv[2]
realm = argv[3] if len(argv) > 3 else "WORLD-ZERO"
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import hero_island as H  # noqa: E402

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
scene.render.resolution_x, scene.render.resolution_y = 1280, 800
scene.world = bpy.data.worlds.new("Sky") if scene.world is None else scene.world
scene.world.use_nodes = False
scene.world.color = (0.62, 0.72, 0.88)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens, cam.data.clip_end = 40, 200000
dist, yaw, pitch = 22000, math.radians(35), math.radians(32)
cam.location = (dist * math.cos(yaw) * math.cos(pitch), dist * math.sin(yaw) * math.cos(pitch), dist * math.sin(pitch) - 1500)
cam.rotation_euler = (math.radians(90 - 32), 0.0, yaw + math.radians(90))

t0 = time.time()
done = 0
for seed in range(start, stop):
    kind = H.KIND_NAMES[seed % len(H.KIND_NAMES)]
    out = os.path.join(out_dir, "Island_H%d_%s.fbx" % (seed, kind))
    if os.path.exists(out):
        continue
    t = time.time()
    H.build(seed, out, keep=True, realm=realm, kind=kind)
    for ob in bpy.data.objects:
        if ob.name.startswith("UCX_"):
            ob.hide_render = True
        elif ob.type == "MESH" and "Col" in ob.data.color_attributes:
            ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
    scene.render.filepath = out[:-4] + ".png"
    bpy.ops.render.render(write_still=True)
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Island_H") or ob.name.startswith("UCX_Island_H"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    done += 1
    print("ISLAND %d %s %.1fs" % (seed, kind, time.time() - t), flush=True)
print("EXPORTED %d heroes in %.0fs -> %s" % (done, time.time() - t0, out_dir), flush=True)
