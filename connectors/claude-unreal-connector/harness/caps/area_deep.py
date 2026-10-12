# SPDX-License-Identifier: MIT
# Deep probes: each builds something real with the setting the UI would normally ask for, then reads it back.
# Runs in the supervised sandbox (sandbox.py): progress(pid) before each probe, SKIP_EXTRA skips crashers.
# Probes that need a renderer (captures, screenshots) are in area_render.py and run in the open editor instead.
import json, time, traceback, warnings
import unreal
warnings.simplefilter("ignore")

D = "/Game/_ClaudeProbe/Deep"
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
CUBE = "/Engine/BasicShapes/Cube.Cube"
PROBES = []


def probe(fn):
    PROBES.append(fn)
    return fn


def make(name, cls, factory):
    a = AT.create_asset(name, D, cls, factory)
    if a is None:
        raise RuntimeError("create_asset %s returned None" % name)
    return a


@probe
def material_graph():
    m = make("M_Probe", unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    c.set_editor_property("constant", unreal.LinearColor(0.2, 0.6, 1.0, 1))
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 200)
    r.set_editor_property("parameter_name", "Rough")
    r.set_editor_property("default_value", 0.3)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    e = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 400)
    e.set_editor_property("parameter_name", "Glow")
    MEL.connect_material_property(e, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    n = MEL.get_num_material_expressions(m)
    names = [str(x) for x in MEL.get_scalar_parameter_names(m)]
    return {"ok": n == 3 and "Rough" in names, "expressions": n, "scalar_params": names}


@probe
def material_instance_params():
    m = EAL.load_asset(D + "/M_Probe")
    mi = make("MI_Probe", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, m)
    MEL.set_material_instance_scalar_parameter_value(mi, "Rough", 0.85)
    MEL.set_material_instance_vector_parameter_value(mi, "Glow", unreal.LinearColor(1, 0.5, 0, 1))
    v = MEL.get_material_instance_scalar_parameter_value(mi, "Rough")
    g = MEL.get_material_instance_vector_parameter_value(mi, "Glow")
    return {"ok": abs(v - 0.85) < 1e-4 and abs(g.g - 0.5) < 1e-4, "rough": v, "glow_g": g.g}


@probe
def material_translucent_two_sided():
    m = make("M_Glass", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("two_sided", True)
    MEL.recompile_material(m)
    return {"ok": m.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_TRANSLUCENT and m.get_editor_property("two_sided")}


@probe
def blueprint_with_components():
    f = unreal.BlueprintFactory()
    f.set_editor_property("parent_class", unreal.Actor)
    bp = make("BP_Probe", unreal.Blueprint, f)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    root = handles[0]
    added = []
    for cls in (unreal.StaticMeshComponent, unreal.PointLightComponent):
        p = unreal.AddNewSubobjectParams(parent_handle=root, new_class=cls, blueprint_context=bp)
        h, fail = sds.add_new_subobject(p)
        added.append(str(fail) if not fail.is_empty() else cls.__name__)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    after = len(sds.k2_gather_subobject_data_for_blueprint(bp))
    gen = unreal.BlueprintEditorLibrary.generated_class(bp)
    return {"ok": after >= len(handles) + 2 and gen is not None, "handles_before": len(handles), "after": after,
            "added": added, "generated": gen.get_name() if gen else None}


@probe
def blueprint_variable():
    bp = EAL.load_asset(D + "/BP_Probe")
    t = unreal.BlueprintEditorLibrary.get_basic_type_by_name("float")
    ok = unreal.BlueprintEditorLibrary.add_member_variable(bp, "Speed", t)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    gen = unreal.BlueprintEditorLibrary.generated_class(bp)
    cdo = unreal.get_default_object(gen)
    has = cdo.get_editor_property("Speed") is not None
    return {"ok": bool(ok) and has, "added": bool(ok), "on_cdo": has}


@probe
def struct_enum_datatable():
    s = make("S_Row", unreal.UserDefinedStruct, unreal.StructureFactory())
    e = make("E_Kind", unreal.UserDefinedEnum, unreal.EnumFactory())
    f = unreal.DataTableFactory()
    f.set_editor_property("struct", s)
    dt = make("DT_Probe", unreal.DataTable, f)
    csv = "Name,MemberVar_0\nrow_a,true\nrow_b,false\n"
    filled = unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(dt, csv)
    rows = [str(r) for r in unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)]
    return {"ok": dt is not None and len(rows) == 2, "filled": filled, "rows": rows, "struct": s.get_name(), "enum": e.get_name()}


@probe
def sequencer_keys():
    seq = make("LS_Probe", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(30, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(90)
    cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
    tr = cam.add_track(unreal.MovieScene3DTransformTrack)
    sec = tr.add_section()
    sec.set_range(0, 90)
    chans = sec.get_all_channels()
    chans[0].add_key(unreal.FrameNumber(0), 0.0)
    chans[0].add_key(unreal.FrameNumber(90), 1000.0)
    keys = len(chans[0].get_keys())
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
    cs = cut.add_section()
    cs.set_range(0, 90)
    return {"ok": keys == 2 and len(seq.get_bindings()) == 1, "keys": keys, "channels": len(chans),
            "bindings": len(seq.get_bindings()), "end": seq.get_playback_end()}


@probe
def pcg_graph_nodes():
    g = make("PCG_Probe", unreal.PCGGraph, unreal.PCGGraphFactory())
    n1 = g.add_node_of_type(unreal.PCGSurfaceSamplerSettings)
    n2 = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    first = n1[0] if isinstance(n1, tuple) else n1
    second = n2[0] if isinstance(n2, tuple) else n2
    g.add_edge(first, "Out", second, "In")
    nodes = len(g.get_editor_property("nodes"))
    return {"ok": nodes >= 2, "nodes": nodes}


@probe
def geometry_scripting():
    dm = unreal.DynamicMesh()
    opts = unreal.GeometryScriptPrimitiveOptions()
    unreal.GeometryScript_Primitives.append_box(dm, opts, unreal.Transform(), 100, 100, 100)
    unreal.GeometryScript_Primitives.append_sphere_lat_long(dm, opts, unreal.Transform(location=[80, 0, 0]), 60, 12, 12)
    tris = unreal.GeometryScript_MeshQueries.get_num_triangle_i_ds(dm)   # UE's Python spells IDs as i_ds
    sm_opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    sm, outcome = unreal.GeometryScript_AssetUtils.create_new_static_mesh_asset_from_mesh(dm, D + "/SM_Generated", sm_opts)
    sm_tris = sm.get_num_triangles(0) if sm else 0
    return {"ok": tris > 12 and sm is not None and sm_tris == tris, "dynamic_tris": tris, "asset_tris": sm_tris,
            "outcome": str(outcome)}


@probe
def static_mesh_lod_collision():
    src = EAL.load_asset(CUBE)
    dup = EAL.duplicate_asset(CUBE, D + "/SM_CubeCopy")
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if sub is None:
        return {"ok": False, "needs_editor": True, "why": "editor subsystems don't exist in a commandlet; run in the open editor"}
    lods = sub.get_lod_count(dup)
    sub.remove_collisions(dup)
    sub.add_simple_collisions(dup, unreal.ScriptCollisionShapeType.BOX)
    n = sub.get_simple_collision_count(dup)
    return {"ok": dup is not None and n >= 1, "lods": lods, "simple_collisions": n}


@probe
def paper2d_tilemap():
    ts = make("TS_Probe", unreal.PaperTileSet, unreal.PaperTileSetFactory())
    tm = make("TM_Probe", unreal.PaperTileMap, unreal.PaperTileMapFactory())
    tm.set_editor_property("map_width", 20)
    tm.set_editor_property("map_height", 18)
    return {"ok": tm.get_editor_property("map_width") == 20 and tm.get_editor_property("map_height") == 18,
            "map": [20, 18], "tileset": ts.get_name()}


@probe
def enhanced_input():
    ia = make("IA_Jump", unreal.InputAction, unreal.InputAction_Factory())
    ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    imc = make("IMC_Probe", unreal.InputMappingContext, unreal.InputMappingContext_Factory())
    key = unreal.Key()
    key.set_editor_property("key_name", "SpaceBar")
    imc.map_key(ia, key)
    n = len(imc.get_editor_property("default_key_mappings").get_editor_property("mappings")) \
        if hasattr(imc.get_editor_property("default_key_mappings"), "get_editor_property") else None
    return {"ok": ia.get_editor_property("value_type") == unreal.InputActionValueType.BOOLEAN, "mappings": n}


@probe
def physics_material():
    pm = make("PM_Probe", unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
    pm.set_editor_property("friction", 0.15)
    pm.set_editor_property("restitution", 0.9)
    return {"ok": abs(pm.get_editor_property("friction") - 0.15) < 1e-4 and abs(pm.get_editor_property("restitution") - 0.9) < 1e-4}


@probe
def niagara_system_asset():
    ns = make("NS_Probe", unreal.NiagaraSystem, unreal.NiagaraSystemFactoryNew())
    found = [str(a) for a in EAL.list_assets("/Niagara/DefaultAssets", recursive=True, include_folder=False)][:200]
    systems = [p for p in found if "System" in p or "NS_" in p]
    return {"ok": ns is not None, "engine_templates_seen": len(systems)}


@probe
def widget_and_metasound():
    w = make("WBP_Probe", unreal.WidgetBlueprint, unreal.WidgetBlueprintFactory())
    ms = make("MS_Probe", unreal.MetaSoundSource, unreal.MetaSoundSourceFactory())
    return {"ok": w is not None and ms is not None}


@probe
def asset_ops():
    src = D + "/PM_Probe"
    dup = EAL.duplicate_asset(src, D + "/PM_Dup")
    EAL.rename_asset(D + "/PM_Dup", D + "/PM_Renamed")
    EAL.set_metadata_tag(EAL.load_asset(D + "/PM_Renamed"), "claude", "probe")
    tag = EAL.get_metadata_tag(EAL.load_asset(D + "/PM_Renamed"), "claude")
    refs = EAL.find_package_referencers_for_asset(D + "/M_Probe", False)
    gone = EAL.delete_asset(D + "/PM_Renamed")
    return {"ok": dup is not None and tag == "probe" and gone and not EAL.does_asset_exist(D + "/PM_Renamed"),
            "metadata": tag, "referencers_of_M_Probe": len(refs)}


@probe
def gltf_export_reimport():
    import os, tempfile
    path = os.path.join(tempfile.gettempdir(), "claude_probe_cube.glb")
    opts = unreal.GLTFExportOptions()
    ok = unreal.GLTFExporter.export_to_gltf(EAL.load_asset(CUBE), path, opts, set())
    size = os.path.getsize(path) if os.path.exists(path) else 0
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", D + "/Reimport")
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    AT.import_asset_tasks([t])
    got = [str(p) for p in t.get_editor_property("imported_object_paths")]
    if os.path.exists(path):
        os.remove(path)
    return {"ok": size > 0 and any("StaticMesh" in p or "Cube" in p for p in got), "glb_bytes": size, "imported": got[:5]}


ONLY = globals().get("ONLY")
result = {"probes": {}}
t_all = time.time()
for fn in PROBES:
    if ONLY and fn.__name__ not in ONLY:
        continue
    if fn.__name__ in SKIP_EXTRA:
        result["probes"][fn.__name__] = {"ok": False, "crash": True}
        continue
    progress(fn.__name__)
    t0 = time.time()
    try:
        r = fn() or {}
    except Exception as e:
        r = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300]), "trace": traceback.format_exc()[-600:]}
    r["ms"] = int((time.time() - t0) * 1000)
    result["probes"][fn.__name__] = json.loads(json.dumps(r, default=repr))
result["passed"] = sum(1 for r in result["probes"].values() if r.get("ok"))
result["total"] = len(result["probes"])
result["secs"] = round(time.time() - t_all, 1)
