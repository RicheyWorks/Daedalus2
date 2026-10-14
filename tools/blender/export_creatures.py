# SPDX-License-Identifier: MIT
"""Headless: every voxel creature (animals, birds, bees, carnivorous plants) as rigged GLB + FBX + json, plus one
contact-sheet preview.   blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_creatures.py -- OUT_DIR [family|species ...]
"""
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
out_dir = argv[0]
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_creatures as VC  # noqa: E402

for o in list(bpy.data.objects):          # factory startup ships a cube, a light and a camera
    bpy.data.objects.remove(o, do_unlink=True)
wanted = argv[1:] or VC.all_species()
species = [s for w in wanted for s in (VC.SPECIES[w] if w in VC.SPECIES else (w,))]
t0 = time.time()
done = []
for sp in species:
    t = time.time()
    name = "Creature_" + "".join(w.capitalize() for w in sp.split("_"))
    if os.path.exists(os.path.join(out_dir, name + ".glb")) and "--force" not in argv:
        continue
    r = VC.build(sp, out_dir)
    print("CREATURE %s %.2f m %.1fs" % (sp, r["height_m"], time.time() - t), flush=True)
    done.append(sp)
# contact sheet: line every creature up on a grid and render once (Workbench, vertex colours)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
scene.render.resolution_x, scene.render.resolution_y = 2000, 1250
scene.world = bpy.data.worlds.new("Sky") if scene.world is None else scene.world
scene.world.use_nodes = False
scene.world.color = (0.62, 0.72, 0.88)
rigs = sorted([o for o in bpy.data.objects if o.type == "ARMATURE"], key=lambda o: o.name)
cols = max(1, int(math.ceil(math.sqrt(len(rigs) * 1.6))))
rows = int(math.ceil(len(rigs) / cols))
for i, rig in enumerate(rigs):
    rig.location = ((i % cols) * 2.2 - cols * 1.1, -(i // cols) * 2.2 + rows * 1.1, 0)
for o in bpy.data.objects:
    if o.type == "MESH" and "Col" in o.data.color_attributes:
        o.data.color_attributes.active_color = o.data.color_attributes["Col"]
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 35
span = max(cols, rows) * 2.2
cam.location = (0, -span * 0.9, span * 0.75)
cam.rotation_euler = (math.radians(50), 0, 0)
scene.render.filepath = os.path.join(out_dir, "creatures-contact-sheet.png")
bpy.ops.render.render(write_still=True)
print("EXPORTED %d creatures in %.0fs -> %s" % (len(done), time.time() - t0, out_dir), flush=True)
