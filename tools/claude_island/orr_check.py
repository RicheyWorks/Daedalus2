# SPDX-License-Identifier: MIT
"""Check every built Claude Island item against the art queue's rules (triangle budget, <= 3 materials, one
collection named after the asset, bottom on z = 0) and render a contact sheet of a sample.

    blender --background --factory-startup --python orr_check.py -- <art folder> <sheet.png> [names...]
"""
import json
import os
import sys

import bpy

BUDGET = {"Tool": 3000, "Item": 3000, "Wpn": 3000, "Prop": 3000, "Mob": 6000, "Veh": 12000, "Bld": 15000, "Sky": 15000}
argv = sys.argv[sys.argv.index("--") + 1:]
art, sheet, pick = argv[0], argv[1], argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orr_build  # noqa: E402

bad, stats = [], {}
for asset, kind, family, p in orr_build.catalogue():
    path = os.path.join(art, kind, asset + ".blend")
    if not os.path.exists(path):
        bad.append((asset, "missing"))
        continue
    bpy.ops.wm.open_mainfile(filepath=path)
    coll = bpy.data.collections.get(asset)
    obs = [o for o in (coll.objects if coll else []) if o.type == "MESH"]
    tris = sum(sum(len(f.vertices) - 2 for f in o.data.polygons) for o in obs)
    mats = max([len(o.data.materials) for o in obs] or [0])
    zmin = min([min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in obs] or [1])
    if not coll or not obs:
        bad.append((asset, "no collection/mesh"))
    elif tris > BUDGET[kind]:
        bad.append((asset, "tris %d" % tris))
    elif mats > 3:
        bad.append((asset, "materials %d" % mats))
    elif abs(zmin) > 0.001:
        bad.append((asset, "bottom %.3f" % zmin))
    stats[asset] = tris
print("ORR CHECK %d/%d ok; tris min %d max %d" % (len(stats) - len(bad), len(orr_build.catalogue()), min(stats.values()),
                                                 max(stats.values())))
for b in bad[:20]:
    print("BAD", b)

# contact sheet: each picked item appended into one scene on a grid, one render
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
cols = 6
for i, name in enumerate(pick):
    kind = name.split("_")[0]
    with bpy.data.libraries.load(os.path.join(art, kind, name + ".blend")) as (src, dst):
        dst.collections = [name]
    c = dst.collections[0]
    scene.collection.children.link(c)
    size = max(max(o.dimensions) for o in c.objects)
    for o in c.objects:
        o.scale = [1.6 / max(size, 0.01)] * 3
        o.location = ((i % cols) * 3.0, (i // cols) * 4.0, 0)
rows = (len(pick) + cols - 1) // cols
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = cols * 3.0 + 1
cam.location = ((cols - 1) * 1.5, (rows - 1) * 2.0 - 12, 9)
cam.rotation_euler = (1.0, 0, 0)
scene.camera = cam
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (0.6, 0.2, 0.8)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.13, 0.2, 1)
scene.world = world
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x, scene.render.resolution_y = 1500, 330 * rows + 100
scene.render.filepath = sheet
bpy.ops.render.render(write_still=True)
print("SHEET", sheet)
