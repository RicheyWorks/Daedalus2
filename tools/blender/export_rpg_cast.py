# SPDX-License-Identifier: MIT
"""Headless: the Portal Realm + Prismheart Realm casts (realm_rpg_cast.py) as rigged GLB + FBX + json, plus sheets.
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_rpg_cast.py -- OUT_ROOT [family ...] [--force] [--no-sheet]
Families: portal_enemy portal_friend portal_boss prism_hero prism_monster prism_summon prism_folk prism_mount.
Portal → OUT_ROOT/claude-portal-cast/, Prismheart → OUT_ROOT/claude-prism-cast/. Each json carries the realm row
(faction, type, individual, variant_seed, plan_id) so Codex can bind it to data/art/portal/population-plan.json.
"""
import json
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
root = os.path.abspath(argv[0])
want = [a for a in argv[1:] if not a.startswith("--")] or None
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_creatures as VC  # noqa: E402
import realm_rpg_cast as RC  # noqa: E402
import voxel_island as V  # noqa: E402


def out_dir(fam):
    return os.path.join(root, "claude-portal-cast" if fam.startswith("portal") else "claude-prism-cast")


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
t0, done = time.time(), 0
for realm_dir in ("claude-portal-cast", "claude-prism-cast"):
    os.makedirs(os.path.join(root, realm_dir), exist_ok=True)
man = RC.manifest()
for d in ("claude-portal-cast", "claude-prism-cast"):
    with open(os.path.join(root, d, "cast.manifest.json"), "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in man.items() if (k.startswith("Mob_Portal") == (d == "claude-portal-cast"))}, f, indent=1)
for key, (fam, fn, cm, name, meta) in RC.ROSTER.items():
    if want and fam not in want:
        continue
    od = out_dir(fam)
    if os.path.exists(os.path.join(od, name + ".glb")) and "--force" not in argv:
        continue
    VC.build(key, od, scale=float(cm))
    jp = os.path.join(od, name + ".json")
    with open(jp, encoding="utf-8") as f:
        j = json.load(f)
    j.update(meta)
    j["family"] = fam
    j["export_name"] = name
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(j, f, indent=1)
    done += 1
    if done % 50 == 0:
        print("CAST %d %.0fs" % (done, time.time() - t0), flush=True)
print("EXPORTED %d cast in %.0fs" % (done, time.time() - t0), flush=True)

if "--no-sheet" not in argv:
    fams = want or sorted({v[0] for v in RC.ROSTER.values()})
    for fam in fams:
        keys = [k for k, v in RC.ROSTER.items() if v[0] == fam]
        # one individual per type keeps the sheet readable (types, not clones); bosses/summons all
        seen, pick = set(), []
        for k in keys:
            t = RC.ROSTER[k][4].get("type") or RC.ROSTER[k][4].get("job")
            if t not in seen:
                seen.add(t)
                pick.append(k)
        cols = int(math.ceil(math.sqrt(len(pick) * 1.6)))
        obs, pitch = [], 2.4
        for i, k in enumerate(pick):
            parts = RC.plan(k)
            vox = [v for vs in parts.values() for v in vs]
            cm = RC.ROSTER[k][2]
            ob = V._mesh_from_voxels(k, vox, scale=cm, pal=RC.PAL)
            for v in ob.data.vertices:
                v.co /= 100.0
            ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
            obs.append(ob)
            pitch = max(pitch, 1.25 * max(ob.dimensions.x, ob.dimensions.y))
        for i, ob in enumerate(obs):
            zmin = min(v.co.z for v in ob.data.vertices)
            ob.location = ((i % cols) * pitch - (cols - 1) * pitch / 2, -(i // cols) * pitch, -zmin)
            ob.rotation_euler.z = math.radians(160)
        sc = bpy.context.scene
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = "STUDIO", "VERTEX", True, True
        sc.render.resolution_x, sc.render.resolution_y = 2000, 1250
        sc.world = bpy.data.worlds.new("Sky") if sc.world is None else sc.world
        sc.world.use_nodes = False
        sc.world.color = (.62, .72, .88)
        cam = bpy.data.objects.get("Cam") or bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        if cam.name not in sc.collection.objects:
            sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.lens, cam.data.clip_end = 35, 100000
        rows = int(math.ceil(len(obs) / cols))
        span = max(cols, rows) * pitch
        cam.location = (0, -(rows * pitch) / 2 - span * .9, span * .6)
        cam.rotation_euler = (math.radians(55), 0, 0)
        sc.render.filepath = os.path.join(out_dir(fam), "sheet-%s.png" % fam)
        bpy.ops.render.render(write_still=True)
        print("SHEET " + sc.render.filepath, flush=True)
        for ob in obs:
            bpy.data.objects.remove(ob, do_unlink=True)
        for me in list(bpy.data.meshes):
            if me.users == 0:
                bpy.data.meshes.remove(me)
