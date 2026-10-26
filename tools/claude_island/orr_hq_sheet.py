# SPDX-License-Identifier: MIT
"""Before/after contact sheet for orr_hq.py: each item twice, side by side: the plain orr_build version on the left,
the upgrade on the right.

    python3 orr_hq_sheet.py sheet.png Name1,Name2,...
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orr_hq  # noqa: E402  (patches orr_build)
import bpy  # noqa: E402
import orr_build  # noqa: E402


def main(sheet, names):
    cat = {a: (k, f, p) for a, k, f, p in orr_build.catalogue()}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for row, level in enumerate((0, 2)):
        orr_hq.LEVEL["value"] = level
        for i, name in enumerate(names):
            k, f, p = cat[name]
            before = set(bpy.data.objects)
            # build() names its collection after the asset; give each row its own copy
            orr_build.build(name, k, f, p)
            obs = [o for o in bpy.data.objects if o not in before]
            coll = obs[0].users_collection[0]
            coll.name = "%s_%d" % (name, row)
            size = max(max(o.dimensions) for o in obs)
            for o in obs:
                o.data.name = "%s_%d" % (name, row)
                o.scale = [1.6 / max(size, 0.01)] * 3
                o.location = (i * 4.0 + row * 1.8, 0, 0)
    cols = len(names)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = cols * 4.0
    cam.location = ((cols - 1) * 2.0 + 0.9, -10, 4.2)
    cam.rotation_euler = (1.3, 0, 0)
    scene.camera = cam
    for rot, e in (((0.7, 0.2, 0.8), 3.5), ((1.2, 0, -2.4), 1.2)):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = e
        sun.rotation_euler = rot
        scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.38, 0.5, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 400 * cols, 520
    scene.render.filepath = sheet
    bpy.ops.render.render(write_still=True)
    print("SHEET", sheet, scene.render.engine)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","))
