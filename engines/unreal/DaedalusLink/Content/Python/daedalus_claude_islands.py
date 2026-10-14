# SPDX-License-Identifier: MIT
"""Team Claude's contest islands into the world (2026-10-14 09:36: "team codex vs team claude ... whoever produces
the best and most islands wins"). tools/blender/voxel_island.py exports Island_C<seed>.glb (one mesh per layer,
vertex-coloured, 100 units per voxel); this module imports a GLB, gives every layer the vertex-colour material,
clears the deed's old instances (fragment, ground, detail) and places the island on the deed at 1 voxel = 1 m.

    import daedalus_claude_islands as C
    C.place_batch([240, 241, ...], realm="WORLD-ZERO")   -> [{seed, deed, assets, cleared}]
    C.count()                                            -> contest tally (islands placed, per realm)
"""
import json
import math
import os

import unreal

GLB_DIR = r"C:\Users\730ri\projects\D2-build\engines\unreal\art\claude-islands"
LEDGER = r"C:\Users\730ri\projects\D2-build\docs\production\lands"
ROOT = "/Game/Daedalus/Art/Islands/ClaudeIslands"
MAT = ROOT + "/M_VoxelVertexColour"
LAYERS = ("body", "clouds")   # voxel_island.GROUPS; the first 36 islands came as 8 layers (see OLD_LAYERS)
OLD_LAYERS = ("island", "water", "trees", "cottage", "flowers", "rocks", "crystals", "clouds")
SCALE = 0.01          # GLB comes in at 100 units/voxel x the importer's 100: scale back to 1 voxel = 1 m
CLEAR_R = 4200.0      # cm: the deed cell's own instances (fragment/ground/detail), not the neighbours'


def material():
    if not unreal.EditorAssetLibrary.does_asset_exist(MAT):
        mel = unreal.MaterialEditingLibrary
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_VoxelVertexColour", ROOT, unreal.Material, unreal.MaterialFactoryNew())
        vc = mel.create_material_expression(m, unreal.MaterialExpressionVertexColor, -400, 0)
        mel.connect_material_property(vc, "", unreal.MaterialProperty.MP_BASE_COLOR)
        r = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 200)
        r.r = 0.9
        mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(m)
        unreal.EditorAssetLibrary.save_asset(MAT)
    return unreal.EditorAssetLibrary.load_asset(MAT)


def import_island(seed, force=False, save=False):
    """Import Island_C<seed>.glb under ROOT/Island_C<seed>; returns {layer: mesh path}."""
    name = "Island_C%d" % seed
    dest = "%s/%s" % (ROOT, name)
    # the interchange importer makes <destination_path>/<destination_name>/StaticMeshes/...
    paths = {}
    for layers, d in ((LAYERS, dest), (OLD_LAYERS, dest), (OLD_LAYERS, dest + "/" + name)):
        cand = {l: "%s/StaticMeshes/%s_%s.%s_%s" % (d, name, l, name, l) for l in layers}
        if unreal.EditorAssetLibrary.does_asset_exist(cand[layers[0]]):
            paths = cand
            break
    if force or not paths:
        t = unreal.AssetImportTask()
        t.filename = os.path.join(GLB_DIR, name + ".glb")
        t.destination_path = ROOT
        t.destination_name = name
        t.automated = True
        t.replace_existing = True
        t.save = False
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        made = [str(p) for p in t.imported_object_paths]
        paths = {}
        for p in made:                      # the GLB decides the layer set (2 for v2, 8 for the first batches)
            tail = p.rsplit(".", 1)[-1]
            if tail.startswith(name + "_"):
                paths[tail[len(name) + 1:]] = p
    m = material()
    out = {}
    for l, p in paths.items():
        if not unreal.EditorAssetLibrary.does_asset_exist(p):
            continue
        sm = unreal.EditorAssetLibrary.load_asset(p)
        for i in range(sm.get_num_sections(0)):
            sm.set_material(i, m)
        if l in ("island", "body"):
            bs = sm.get_editor_property("body_setup")
            if bs is not None:
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if save:
            unreal.EditorAssetLibrary.save_loaded_asset(sm)
        out[l] = p
    return out


def clear_cell(cx, cy, r=CLEAR_R, district=None):
    """Remove every ISM instance of the old deed (fragment, ground plate, detail props) within r of the centre.
    With `district`, only that district's actors (Lands_/Detail_/Decor_ *_D<dd>*) are scanned: walking every
    instance of all 500 districts cost ~10 s per deed."""
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    tag = "_D%02d" % district if district is not None else None
    n = 0
    for a in sub.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("ClaudeIsland_"):
            continue
        if tag and not (tag in lab and ("_" + tag.strip("_") + "_") in lab + "_"):
            continue
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            rm = []
            for i in range(c.get_instance_count()):
                l = c.get_instance_transform(i, True).translation
                if math.hypot(l.x - cx, l.y - cy) < r and -4000 < l.z < 6000:
                    rm.append(i)
            if rm:
                c.remove_instances(rm)
                a.modify()
                n += len(rm)
    return n


def place(seed, cx, cy, top, assets=None, district=None):
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assets = assets or import_island(seed)
    for a in sub.get_all_level_actors():
        if a.get_actor_label().startswith("ClaudeIsland_%d_" % seed):
            sub.destroy_actor(a)
    cleared = clear_cell(cx, cy, district=district)
    loc = unreal.Vector(cx, cy, top)
    for l, p in assets.items():
        a = sub.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0.0, 0.0, 0.0))
        a.set_actor_label("ClaudeIsland_%d_%s" % (seed, l))
        a.static_mesh_component.set_static_mesh(unreal.EditorAssetLibrary.load_asset(p))
        a.set_actor_scale3d(unreal.Vector(SCALE, SCALE, SCALE))
        a.set_folder_path("Claude/Islands")
        a.tags = [unreal.Name("District"), unreal.Name("ClaudeIsland")]
        if l in ("clouds", "crystals", "flowers"):
            a.static_mesh_component.set_cast_shadow(l != "clouds")
    return {"seed": seed, "assets": len(assets), "cleared": cleared}


def deeds(realm="WORLD-ZERO"):
    with open(os.path.join(LEDGER, realm.lower() + ".json"), encoding="utf-8") as f:
        return {row["deed"]: row for row in json.load(f)["lands"]}


def save_assets():
    """One save of every dirty island asset (per-mesh saves made an import cost 18 s)."""
    return unreal.EditorAssetLibrary.save_directory(ROOT, only_if_is_dirty=True, recursive=True)


def place_batch(seeds, realm="WORLD-ZERO", save=True):
    """Seed n goes on deed n of the realm (one island per deed; the seed is the deed so re-runs are idempotent)."""
    rows = deeds(realm)
    out = []
    for seed in seeds:
        row = rows.get(seed)
        if row is None:
            out.append({"seed": seed, "error": "no deed"})
            continue
        if not os.path.exists(os.path.join(GLB_DIR, "Island_C%d.glb" % seed)):
            out.append({"seed": seed, "error": "no glb"})
            continue
        r = place(seed, row["x_cm"], row["y_cm"], row["top_cm"], district=row.get("district"))
        r["deed"] = seed
        out.append(r)
    if save:
        save_assets()
    return out


def count():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    seeds = set()
    for a in sub.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("ClaudeIsland_") and (lab.endswith("_island") or lab.endswith("_body")):
            seeds.add(int(lab.split("_")[1]))
    return {"islands": len(seeds), "seeds": sorted(seeds)}
