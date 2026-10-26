# SPDX-License-Identifier: MIT
"""Headless: every voxel prop (trees x stages, plants, shrubs, clouds) as FBX + json, plus a contact sheet per family.
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_flora.py -- OUT_DIR [tree|plant|shrub|cloud ...] [--force]
"""
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
out_dir = argv[0]
fams = [a for a in argv[1:] if not a.startswith("--")] or None
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_flora as F  # noqa: E402
import voxel_island as V  # noqa: E402

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
t0 = time.time()
done = F.build_all(out_dir, families=fams, force="--force" in argv)
print("EXPORTED %d props in %.0fs -> %s" % (len(done), time.time() - t0, out_dir), flush=True)
# contact sheet: rebuild the family's props in a grid and render once
for fam in (fams or ("tree", "plant", "shrub", "cloud")):
    names = [n for n, (f, _) in F.CATALOG.items() if f == fam]
    cols = int(math.ceil(math.sqrt(len(names) * 1.6)))
    pitch = {"tree": 14.0, "plant": 1.6, "shrub": 1.6, "cloud": 40.0}[fam]
    obs = []
    for i, n in enumerate(names):
        vox = F.plan(n)
        ob = V._mesh_from_voxels(n, vox, scale=F.CATALOG[n][1], pal=F.PAL)
        zmin = min(z for _, _, z, _ in vox)
        ob.location = ((i % cols) * pitch - cols * pitch / 2, -(i // cols) * pitch, -zmin * F.CATALOG[n][1] / 100.0)
        for v in ob.data.vertices:
            v.co /= 100.0
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
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
    scene.render.filepath = os.path.join(out_dir, "sheet-%s.png" % fam)
    bpy.ops.render.render(write_still=True)
    print("SHEET " + scene.render.filepath, flush=True)
    for ob in obs:
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
