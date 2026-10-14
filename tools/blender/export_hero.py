# SPDX-License-Identifier: MIT
"""Headless: build the hero island, export FBX + chemistry manifest, and render two Workbench previews.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_hero.py -- 39 [out_dir] [REALM]
"""
import importlib.util
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
seed = int(argv[0]) if argv else 39
here = os.path.dirname(os.path.abspath(__file__))
out_dir = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(here)), "engines", "unreal", "art", "claude-islands")
realm = argv[2] if len(argv) > 2 else "WORLD-ZERO"
sys.path.insert(0, here)
import hero_island as H  # noqa: E402

t = time.time()
out = os.path.join(out_dir, "Island_H%d.fbx" % seed)
r = H.build(seed, out, keep=True, realm=realm)
print("BUILT %s in %.1fs voxels=%s" % (out, time.time() - t, r["voxels"]), flush=True)

# --- preview renders: Workbench, flat vertex colours, two aerial cameras ------------------------------------------
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "VERTEX"
sh.show_shadows = True
sh.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("Sky") if scene.world is None else scene.world
scene.world.use_nodes = False
scene.world.color = (0.62, 0.72, 0.88)
for ob in bpy.data.objects:
    if ob.name.startswith("UCX_"):
        ob.hide_render = True
    elif ob.type == "MESH" and "Col" in ob.data.color_attributes:
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]      # Workbench VERTEX reads the active one
        ob.data.color_attributes.render_color_index = ob.data.color_attributes.find("Col")
cam_data = bpy.data.cameras.new("HeroCam")
cam = bpy.data.objects.new("HeroCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 40
cam_data.clip_end = 200000
for i, (dist, yaw_deg, pitch_deg, name) in enumerate(((22000, 35, 32, "a"), (26000, 215, 24, "b"))):
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    cam.location = (dist * math.cos(yaw) * math.cos(pitch), dist * math.sin(yaw) * math.cos(pitch), dist * math.sin(pitch) - 1500)
    cam.rotation_euler = (math.radians(90 - pitch_deg), 0.0, yaw + math.radians(90))
    scene.render.filepath = os.path.join(out_dir, "Island_H%d_%s.png" % (seed, name))
    bpy.ops.render.render(write_still=True)
    print("RENDERED " + scene.render.filepath, flush=True)
print("DONE %.1fs" % (time.time() - t), flush=True)
