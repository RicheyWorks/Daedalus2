# SPDX-License-Identifier: MIT
"""Build the PCG ecology test level in Unreal (hidden, run by run-pcg-ecology.ps1).

  UnrealEditor-Cmd <uproject> -run=pythonscript -script=build_pcg_ecology.py -EnablePlugins=PCG ...

Writes ONLY under /Game/Pythagoras/PCGEcology:
  T_Terrain (static mesh from ecology_rules.height), PCG_Ecology (PCG graph: one Create Points ->
  Static Mesh Spawner branch per species), L_PCGEcology (level with terrain + PCGVolume/Component).
The ecology lives in ecology_rules.py (engine-free, tested); PCG does the spawning. Results JSON
and a screenshot go next to this script under out/.
"""
import os, sys, json, math, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unreal
import ecology_rules as eco

ROOT = "/Game/Pythagoras/PCGEcology"
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
R = {"steps": [], "errors": []}
def step(name, fn):
    try:
        v = fn(); R["steps"].append([name, "ok"]); unreal.log("PCGECO ok " + name); return v
    except Exception as e:
        R["steps"].append([name, "FAIL"]); R["errors"].append(name + ": " + traceback.format_exc()); unreal.log_error("PCGECO FAIL " + name + " " + str(e)); return None

at = unreal.EditorAssetLibrary
SHAPES = {"Sphere": "/Engine/BasicShapes/Sphere.Sphere", "Cone": "/Engine/BasicShapes/Cone.Cone", "Cylinder": "/Engine/BasicShapes/Cylinder.Cylinder"}

# 1. ecology (pure python)
placed, rejected = eco.generate(7)
checks, st = eco.checks(placed)
R["ecology"] = {"checks": [[l, ok] for l, ok, _ in checks], "stats": st, "rejected": rejected}

# 2. terrain mesh via OBJ import
def terrain():
    n, D = 60, eco.DOMAIN
    p = os.path.join(OUT, "T_Terrain.obj")
    with open(p, "w") as f:
        for j in range(n + 1):
            for i in range(n + 1):
                x, y = D * i / n, D * j / n
                f.write("v %.3f %.3f %.3f\n" % (x * 100, y * 100, eco.height(x, y) * 100))  # OBJ->UE axis handled by importer; we verify bounds after
        for j in range(n):
            for i in range(n):
                a = j * (n + 1) + i + 1
                f.write("f %d %d %d\nf %d %d %d\n" % (a, a + 1, a + n + 2, a, a + n + 2, a + n + 1))
    t = unreal.AssetImportTask(); t.filename = p; t.destination_path = ROOT; t.automated = True; t.replace_existing = True; t.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.imported_object_paths)
R["terrain_assets"] = step("terrain import", terrain)

# 3. PCG graph
def graph():
    path = ROOT + "/PCG_Ecology"
    if at.does_asset_exist(path): at.delete_asset(path)
    g = unreal.AssetToolsHelpers.get_asset_tools().create_asset("PCG_Ecology", ROOT, unreal.PCGGraph, unreal.PCGGraphFactory())
    out_node = g.get_output_node()
    made = {}
    for sp in eco.SPECIES:
        pts = [p for p in placed if p["species"] == sp["name"]]
        cnode, cset = g.add_node_of_type(unreal.PCGCreatePointsSettings)
        arr = []
        for p in pts:
            pt = unreal.PCGPoint()
            s = p["scale"]; rad = sp["r"]; h = sp["h"]
            # basic shapes are 100 cm: scale to crown diameter x height
            tr = unreal.Transform(unreal.Vector(p["x"] * 100, p["y"] * 100, p["z"] * 100 + h * 50 * s),
                                  unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]), unreal.Vector(2 * rad * s, 2 * rad * s, h * s))
            pt.set_editor_property("transform", tr)
            pt.set_editor_property("seed", len(arr) + 1)
            arr.append(pt)
        cset.set_editor_property("points_to_create", arr)
        try: cset.set_editor_property("coordinate_space", unreal.PCGCoordinateSpace.WORLD)
        except Exception: pass
        snode, sset = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        sel = sset.get_editor_property("mesh_selector_parameters")
        e = unreal.PCGMeshSelectorWeightedEntry()
        d = e.get_editor_property("descriptor"); d.set_editor_property("static_mesh", unreal.load_asset(SHAPES[sp["shape"]])); e.set_editor_property("descriptor", d)
        e.set_editor_property("weight", 1)
        sel.set_editor_property("mesh_entries", [e]); sset.set_editor_property("mesh_selector_parameters", sel)
        g.add_edge(cnode, "Out", snode, "In")
        g.add_edge(snode, "Out", out_node, "In")
        made[sp["name"]] = len(arr)
    at.save_loaded_asset(g)
    return made
R["graph_points"] = step("pcg graph", graph)

# 4. level + PCG volume, generate, count
def level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    lp = ROOT + "/L_PCGEcology"
    if at.does_asset_exist(lp): at.delete_asset(lp)
    les.new_level(lp)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if R["terrain_assets"]:
        m = unreal.load_asset(R["terrain_assets"][0].split(".")[0])
        ta = eas.spawn_actor_from_object(m, unreal.Vector(0, 0, 0)); ta.set_actor_label("Terrain")
        R["terrain_bounds"] = [str(v) for v in ta.get_actor_bounds(False)]
    sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(roll=0, pitch=-40, yaw=-45))
    eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 3000))
    vol = eas.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(5000, 5000, 500))
    vol.set_actor_scale3d(unreal.Vector(52, 52, 20)); vol.set_actor_label("PCG_Ecology_Volume")
    comp = vol.get_component_by_class(unreal.PCGComponent)
    comp.set_graph(unreal.load_asset(ROOT + "/PCG_Ecology"))
    comp.generate_local(True) if hasattr(comp, "generate_local") else comp.generate(True)
    # count spawned instances per mesh
    counts = {}
    for a in [vol] + list(eas.get_all_level_actors()):
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            k = sm.get_name() if sm else "?"; counts[k] = counts.get(k, 0) + c.get_instance_count()
    R["spawned_instances_by_mesh"] = counts
    les.save_current_level()
    return lp
R["level"] = step("level + generate", level)

# 5. offscreen screenshot via SceneCapture2D
def shot():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rt = unreal.RenderingLibrary.create_render_target2d(unreal.EditorLevelLibrary.get_editor_world(), 1600, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(-3500, -3500, 5500), unreal.Rotator(roll=0, pitch=-35, yaw=45))
    c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
    c.set_editor_property("texture_target", rt); c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property("fov_angle", 60.0)
    c.capture_scene()
    unreal.RenderingLibrary.export_render_target(unreal.EditorLevelLibrary.get_editor_world(), rt, OUT, "pcg_ecology.png")
    eas.destroy_actor(cap)
    return os.path.join(OUT, "pcg_ecology.png")
if "-nullrhi" not in unreal.SystemLibrary.get_command_line().lower():
    R["screenshot"] = step("screenshot", shot)

json.dump(R, open(os.path.join(OUT, "result.json"), "w"), indent=1, default=str)
unreal.log("PCGECO done")
