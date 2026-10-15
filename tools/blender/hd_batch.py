# SPDX-License-Identifier: MIT
"""Mass-produce HD islands (hd_island.py) — the 10,000-island run.

    blender -b --factory-startup --python-exit-code 1 --python tools/blender/hd_batch.py -- OUT_ROOT START COUNT [--workers W --worker I] [--no-thumb]

Seeds START .. START+COUNT-1; worker I of W takes every W-th seed (start + I, start + I + W, …), so W Blender processes
split one range with no overlap. Kind = KINDS[seed % 6]. Each island is built, exported (GLB + FBX + json with its
chemistry and gameplay hooks), thumbnailed (480x300 Workbench hero), indexed (one json line in
index-worker<I>.jsonl), then the scene is purged — every object, mesh and material — so island 500 is as fast
as island 1. Resume-safe: an island whose json already exists is skipped. A failure is logged and the worker moves on.
Output: OUT_ROOT/<thousands>/HDIsland_<Kind>_<seed>.{glb,fbx,json,thumb.png}.
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hd_island as H  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
root = os.path.abspath(argv[0])
start, count = int(argv[1]), int(argv[2])
W = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 1
I = int(argv[argv.index("--worker") + 1]) if "--worker" in argv else 0
thumb = "--no-thumb" not in argv
KIND_ORDER = list(H.KINDS)


def purge():
    bpy.data.batch_remove(list(bpy.data.objects))
    bpy.data.batch_remove(list(bpy.data.meshes))
    bpy.data.batch_remove([m for m in bpy.data.materials])
    bpy.data.batch_remove(list(bpy.data.curves))
    H.MATS.clear()
    H.GROUP = []


def setup_thumb():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "MATERIAL", True, True
    sc.render.resolution_x, sc.render.resolution_y = 480, 300
    sc.world = bpy.data.worlds.new("Sky") if sc.world is None else sc.world
    sc.world.use_nodes = False
    sc.world.color = (.62, .74, .90)


def render_thumb(path):
    sc = bpy.context.scene
    cam = bpy.data.objects.new("ThumbCam", bpy.data.cameras.new("ThumbCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens, cam.data.clip_end = 32, 100000
    cam.location = (330, -290, 140)
    cam.rotation_euler = (Vector((0, 0, -5)) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    for o in bpy.data.objects:
        if o.name.startswith("UCX_") or "_LOD" in o.name or o.location.z < -400:
            o.hide_render = True
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


purge()
setup_thumb()
os.makedirs(root, exist_ok=True)
idx_path = os.path.join(root, "index-worker%d.jsonl" % I)
seeds = [start + I + k * W for k in range((count - I + W - 1) // W)]
t_all, done, failed = time.time(), 0, 0
for seed in seeds:
    kind = KIND_ORDER[seed % len(KIND_ORDER)]
    shard = os.path.join(root, "%05d-%05d" % (seed // 1000 * 1000, seed // 1000 * 1000 + 999))
    name = "HDIsland_%s_%d" % (kind.title(), seed)
    if os.path.exists(os.path.join(shard, name + ".json")):
        continue
    t0 = time.time()
    try:
        man = H.build(seed, kind, shard)
        if thumb:
            render_thumb(os.path.join(shard, name + ".thumb.png"))
        row = {"seed": seed, "kind": kind, "name": name, "shard": os.path.basename(shard), "tris": man["triangles"], "objects": man["objects"],
               "grade": man["chemistry"].get("geology", {}).get("grade"), "surplus": man["chemistry"].get("economy", {}).get("surplus"),
               "need": man["chemistry"].get("economy", {}).get("need"), "hooks": len(man.get("gameplay", [])), "secs": round(time.time() - t0, 1)}
        with open(idx_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        done += 1
        print("ISLAND %d %s %.1fs tris=%d objs=%d" % (seed, kind, time.time() - t0, man["triangles"], man["objects"]), flush=True)
    except Exception:
        failed += 1
        print("FAILED %d %s\n%s" % (seed, kind, traceback.format_exc()), flush=True)
        with open(os.path.join(root, "failed-worker%d.log" % I), "a", encoding="utf-8") as f:
            f.write("%d %s\n%s\n" % (seed, kind, traceback.format_exc()))
    purge()
    setup_thumb()
print("BATCH worker %d/%d done=%d failed=%d %.0fs" % (I, W, done, failed, time.time() - t_all), flush=True)
