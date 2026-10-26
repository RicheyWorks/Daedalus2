# SPDX-License-Identifier: MIT
"""Visual check (blender -b --python bip_render_check.py -- <manifest> <packet dir> <source.glb> <out dir>): renders the source island and the
reassembled packets (terrain chunks + props placed from the manifest) from the same top-down camera and prints the pixel difference."""
import bpy, json, os, sys, mathutils
man, pdir, src, out = sys.argv[sys.argv.index("--") + 1:][:4]
m = json.load(open(man, encoding="utf-8"))
C = mathutils.Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1))); Ci = C.inverted()


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup(tag):
    sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x = sc.render.resolution_y = 1000; sc.render.image_settings.file_format = "PNG"
    lo, hi = m["totals"]["world_min"], m["totals"]["world_max"]; cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.type = "ORTHO"; cam.data.ortho_scale = max(hi[0] - lo[0], hi[2] - lo[2]) * 1.05
    cam.location = (cx, -cz, 400); cam.rotation_euler = (0, 0, 0); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.filepath = os.path.join(out, tag + ".png"); bpy.ops.render.render(write_still=True)


os.makedirs(out, exist_ok=True)
clear(); bpy.ops.import_scene.gltf(filepath=src); setup("source")
clear()
for p in m["packets"]:
    if p["kind"] == "terrain":
        bpy.ops.import_scene.gltf(filepath=os.path.join(pdir, p["file"]))
imported = {}
for p in m["packets"]:
    if p["kind"] != "props":
        continue
    before = set(bpy.data.objects.keys()); bpy.ops.import_scene.gltf(filepath=os.path.join(pdir, p["file"]))
    for n in set(bpy.data.objects.keys()) - before:
        o = bpy.data.objects[n]; imported[(p["id"], o.name)] = o
        o.hide_render = True
n = 0
for pl in m["placements"]:
    src_o = imported.get((pl["packet"], pl["prop"]))
    if src_o is None or src_o.type != "MESH":
        continue
    d = bpy.data.objects.new("pl", src_o.data); q = pl["rotation"]
    M = mathutils.Matrix.Translation(pl["translation"]) @ mathutils.Quaternion((q[3], q[0], q[1], q[2])).to_matrix().to_4x4()
    S = mathutils.Matrix.Diagonal((*pl["scale"], 1)); d.matrix_world = C @ (M @ S) @ Ci
    bpy.context.scene.collection.objects.link(d); n += 1
print("PLACED", n, "of", len(m["placements"]))
setup("packets")
import numpy as np
a = bpy.data.images.load(os.path.join(out, "source.png")); b = bpy.data.images.load(os.path.join(out, "packets.png"))
A = np.array(a.pixels[:]).reshape(-1, 4)[:, :3]; B = np.array(b.pixels[:]).reshape(-1, 4)[:, :3]
diff = np.abs(A - B).max(axis=1)
print("PIXELS", len(diff), "differ>0.05:", float((diff > 0.05).mean()), "mean abs:", float(np.abs(A - B).mean()))
