# SPDX-License-Identifier: MIT
"""Blender preview hero shot of OddsReaper Island from layout.json + glbs (headless).
blender -b --factory-startup -P render_hero.py -- <glb_dir> <layout.json> <out.png>"""
import bpy, json, math, os, sys
glb, lay_path, out = sys.argv[sys.argv.index("--") + 1:][:3]
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
lay = json.load(open(lay_path)); cache = {}
for p in lay["placements"]:
    if p.get("skip"): continue
    n = p["asset"]
    if n not in cache:
        bpy.ops.import_scene.gltf(filepath=os.path.join(glb, n + ".glb"))
        src = bpy.context.selected_objects[0]; cache[n] = src; o = src
    else:
        o = cache[n].copy(); bpy.context.collection.objects.link(o)
    o.location = (p["x"], p["y"], p["z"]); o.rotation_euler = (0, 0, math.radians(p["yaw"])); o.scale = (p["scale"],) * 3
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x, sc.render.resolution_y = 1600, 900
w = bpy.data.worlds.new("Storm"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.07, 0.16, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), 0, math.radians(-30))); bpy.context.active_object.data.energy = 2.5
bpy.context.active_object.data.color = (0.65, 0.62, 1.0)
bpy.ops.object.light_add(type="POINT", location=(0, 0, 60)); bpy.context.active_object.data.energy = 4e5; bpy.context.active_object.data.color = (0.5, 0.85, 1)
for x, y in ((0, -70), (-30, -60), (30, -60), (0, -10)):  # cyan odds-glow pools near the plaza
    bpy.ops.object.light_add(type="POINT", location=(x, y, 12)); bpy.context.active_object.data.energy = 6e4; bpy.context.active_object.data.color = (0.4, 0.9, 1)
c, t = lay.get("hero_cam_m", [-190, -320, 110]), lay.get("hero_target_m", [0, 0, 5])
bpy.ops.object.camera_add(location=c); cam = bpy.context.active_object; sc.camera = cam
d = (t[0] - c[0], t[1] - c[1], t[2] - c[2])
cam.rotation_euler = (math.atan2(math.hypot(d[0], d[1]), -d[2]), 0, math.atan2(d[1], d[0]) - math.pi / 2); cam.data.lens = 32
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print("HERO", out)
