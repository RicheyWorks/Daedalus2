# SPDX-License-Identifier: MIT
"""Headless: rigged wildlife catalogues (wolves | rabbits) as GLB + FBX + json, plus contact sheets.
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_wildlife.py -- MODULE OUT_DIR [group ...] [--force] [--no-sheet] [--sheet-only]
MODULE wolves -> voxel_wolves (504, group = kind, 5 cm voxels); rabbits -> voxel_rabbits (504, group = breed, 2.5 cm).
Sheets: sheet-<group>.png (that group's 42) and sheet-all.png (one of every group x coat, variant 01).
"""
import json
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
module, out_dir = argv[0], os.path.abspath(argv[1])
want = [a for a in argv[2:] if not a.startswith("--")] or None
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_creatures as VC  # noqa: E402
import voxel_island as V  # noqa: E402

if module == "wolves":
    import voxel_wolves as M
    GROUP, GROUPS, YAW = "kind", list(M.KINDS), 150
elif module == "rabbits":
    import voxel_rabbits as M
    GROUP, GROUPS, YAW = "breed", list(M.BREEDS), 150
else:
    raise SystemExit("unknown module " + module)
CM = M.VOXEL_CM

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, module + ".manifest.json"), "w", encoding="utf-8") as f:
    json.dump(M.manifest(), f, indent=1)
t0 = time.time()
done = 0
if "--sheet-only" not in argv:
    for n in M.NAMES:
        if want and M.spec(n)[GROUP] not in want:
            continue
        name = "Creature_" + "".join(w.capitalize() for w in n.split("_"))
        if os.path.exists(os.path.join(out_dir, name + ".glb")) and "--force" not in argv:
            continue
        VC.build(n, out_dir, scale=CM)
        jp = os.path.join(out_dir, name + ".json")
        j = json.load(open(jp, encoding="utf-8"))
        j.update({"catalogue": module, "spec": {k: v for k, v in M.spec(n).items() if k != "seed"}, "ecology": "see %s.manifest.json" % module})
        json.dump(j, open(jp, "w", encoding="utf-8"), indent=1)
        done += 1
        if done % 50 == 0:
            print("WILDLIFE %s %d %.0fs" % (module, done, time.time() - t0), flush=True)
print("EXPORTED %d %s in %.0fs -> %s" % (done, module, time.time() - t0, out_dir), flush=True)


def sheet(names, path):
    vox_all = {n: [v for vs in M.plan(n).values() for v in vs] for n in names}
    ext = max(max(max(abs(x), abs(y)) for x, y, _, _ in vs) for vs in vox_all.values()) * CM / 100.0
    pitch = max(0.6, ext * 2.4)
    cols = int(math.ceil(math.sqrt(len(names) * 1.6)))
    obs = []
    for i, n in enumerate(names):
        ob = V._mesh_from_voxels(n, vox_all[n], scale=CM, pal=M.PAL)
        ob.location = ((i % cols) * pitch - (cols - 1) * pitch / 2, -(i // cols) * pitch, 0)
        for v in ob.data.vertices:
            v.co /= 100.0
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
        ob.rotation_euler.z = math.radians(YAW)
        obs.append(ob)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
    scene.view_settings.view_transform = "Standard"
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
    cam.location = (0, -(rows * pitch) / 2 - span * 0.9, span * 0.6)
    cam.rotation_euler = (math.radians(55), 0, 0)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("SHEET " + path, flush=True)
    for ob in obs:
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


if "--no-sheet" not in argv:
    for g in (want or GROUPS):
        sheet([n for n in M.NAMES if M.spec(n)[GROUP] == g], os.path.join(out_dir, "sheet-%s.png" % g))
    if not want:
        sheet([n for n in M.NAMES if n.endswith("_01")], os.path.join(out_dir, "sheet-all.png"))
