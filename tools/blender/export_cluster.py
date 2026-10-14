# SPDX-License-Identifier: MIT
"""Headless: build a four-island themed cluster, export FBX, and render two Workbench previews.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_cluster.py -- 7 out_dir WORLD-ZERO spring
"""
import importlib.util
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
seed = int(argv[0]) if argv else 7
here = os.path.dirname(os.path.abspath(__file__))
out_dir = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(here)), "engines", "unreal", "art", "claude-islands")
realm = argv[2] if len(argv) > 2 else "WORLD-ZERO"
theme = argv[3] if len(argv) > 3 else "spring"
sys.path.insert(0, here)
import island_cluster as X  # noqa: E402

t = time.time()
out = os.path.join(out_dir, "Cluster_%s_%d.fbx" % (theme, seed))
r = X.build(seed, out, theme=theme, keep=True)
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
cam_data = bpy.data.cameras.new("ClusterCam")
cam = bpy.data.objects.new("ClusterCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 40
cam_data.clip_end = 200000
for i, (dist, yaw_deg, pitch_deg, name) in enumerate(((52000, 40, 30, "a"), (60000, 220, 26, "b"))):
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    cam.location = (dist * math.cos(yaw) * math.cos(pitch), dist * math.sin(yaw) * math.cos(pitch), dist * math.sin(pitch) - 3000)
    cam.rotation_euler = (math.radians(90 - pitch_deg), 0.0, yaw + math.radians(90))
    scene.render.filepath = out[:-4] + "_%s.png" % name
    bpy.ops.render.render(write_still=True)
    print("RENDERED " + scene.render.filepath, flush=True)
print("DONE %.1fs" % (time.time() - t), flush=True)
