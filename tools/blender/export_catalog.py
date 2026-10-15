# SPDX-License-Identifier: MIT
"""Headless: export one voxel catalogue (eggs | props | sims) as FBX + json, plus a contact sheet per family.
    blender -b --factory-startup --python-exit-code 1 --python tools/blender/export_catalog.py -- MODULE OUT_DIR [family ...] [--force] [--no-sheet]
MODULE: eggs (voxel_eggs, 196 Prop_Egg_*), aquatic (voxel_aquatic: pond | marsh | submerged | sea | realm, 258), props (voxel_props: house | grave | sport), sims (voxel_sims: kit | machine | appliance | house).
Same recipe as export_farm.py: build everything, free each object after export, then rebuild a family in a grid and render once with Workbench.
"""
import math
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
module, out_dir = argv[0], os.path.abspath(argv[1])
fams = [a for a in argv[2:] if not a.startswith("--")] or None
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import voxel_island as V  # noqa: E402

if module == "eggs":
    import voxel_eggs as M
    PITCH = {"egg": 1.2}

    def voxels_of(name):
        egg = name[len("Prop_Egg_"):].rsplit("_", 1)[0]
        st = name.rsplit("_", 1)[1]
        return M.plan(egg, "Intact" if st == "Shiny" else st, shiny=(st == "Shiny"))
elif module == "props":
    import voxel_props as M
    PITCH = {"house": 3.0, "grave": 2.5, "sport": 2.0}

    def voxels_of(name):
        p = M.plan(name)
        return p if isinstance(p, list) else [v for vs in p.values() for v in vs]
elif module == "prism":
    import realm_prism_props as M
    PITCH = {"structure": 14.0, "item": 2.4}

    def voxels_of(name):
        return M.plan(name)
elif module == "aquatic":
    import voxel_aquatic as M
    PITCH = {"pond": 2.4, "marsh": 2.4, "submerged": 2.0, "sea": 6.0, "realm": 2.2}

    def voxels_of(name):
        return M.plan(name)
elif module == "sims":
    import voxel_sims as M
    PITCH = {"kit": 3.5, "machine": 2.5, "appliance": 3.0, "house": 24.0}

    def voxels_of(name):
        p = M.plan(name)
        return p if isinstance(p, list) else [v for vs in p.values() for v in vs]
else:
    raise SystemExit("unknown module " + module)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
t0 = time.time()
force = "--force" in argv
if module == "eggs":
    done = M.build_all(out_dir, force=force)
else:
    done = M.build_all(out_dir, families=fams, force=force)
print("EXPORTED %d %s in %.0fs -> %s" % (len(done), module, time.time() - t0, out_dir), flush=True)

if "--no-sheet" not in argv:
    for fam in (fams or list(PITCH)):
        names = [n for n, (f, _) in M.CATALOG.items() if f == fam]
        if not names:
            continue
        cols = int(math.ceil(math.sqrt(len(names) * 1.6)))
        pitch = PITCH[fam]
        obs = []
        for i, n in enumerate(names):
            vox = voxels_of(n)
            cm = M.CATALOG[n][1]
            ob = V._mesh_from_voxels(n, vox, scale=cm, pal=M.PAL)
            zmin = min(z for _, _, z, _ in vox)
            ob.location = ((i % cols) * pitch - (cols - 1) * pitch / 2, -(i // cols) * pitch, -zmin * cm / 100.0)
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
