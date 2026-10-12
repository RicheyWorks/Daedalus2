# SPDX-License-Identifier: MIT
"""Live pass in the open editor (via the Claude Unreal bridge): build /Game/Pythagoras/PCGEcology/PCG_Ecology
from ecology_rules and drop ONE PCGVolume (tag PYTH_Eco) ~25 m ahead of the player/camera in the editor level,
snapped to ground with line traces, then Generate. Python can't add actors to a PIE world, so this lands in the
editor world (visible in the viewport, and after Play stops). Re-running replaces the volume. Does not save the level."""
import sys, math, json, unreal, importlib
HERE = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
sys.path.insert(0, HERE)
import ecology_rules as eco; importlib.reload(eco)
ROOT = "/Game/Pythagoras/PCGEcology"
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ew = ues.get_editor_world(); gw = ues.get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(gw, 0) if gw else None
if pawn:
    L = pawn.get_actor_location(); yaw = pawn.get_actor_rotation().yaw
else:
    # anchor on the PlayerStart (the camera moves every run when we frame the view, which made the patch drift)
    starts = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == "PlayerStart"]
    if starts: L = starts[0].get_actor_location(); yaw = starts[0].get_actor_rotation().yaw
    else: L, rot = ues.get_level_viewport_camera_info(); yaw = rot.yaw
# Fit fix (2026-10-12): the Daedalus world is floating voxel islands; a fixed 100 m patch ahead of the camera
# hung 77% off the edge. Search centres around the camera and patch scales, keep the one with the most ground.
def _probe(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, L.z + 30000), unreal.Vector(x, y, L.z - 60000),
            unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    return h.to_tuple()[4].z if h else None
best = None
for S in (1.0, 0.7, 0.5, 0.35):
    D = eco.DOMAIN * 100 * S
    for r in (0.0, 0.25, 0.5, 0.8):
        for k in range(8 if r else 1):
            a = math.radians(yaw + 45 * k)
            cx, cy = L.x + math.cos(a) * r * D, L.y + math.sin(a) * r * D
            zs = [_probe(cx - D / 2 + D * (i + 0.5) / 8, cy - D / 2 + D * (j + 0.5) / 8) for i in range(8) for j in range(8)]
            cov = sum(z is not None for z in zs) / 64.0
            if best is None or cov > best[0] + 1e-6 or (abs(cov - best[0]) < 1e-6 and S > best[1]):
                best = (cov, S, cx, cy)
    if best[0] >= 0.9 and best[1] == S: break
COVER, S, cx, cy = best
D = eco.DOMAIN * 100 * S
ox, oy = cx - D / 2, cy - D / 2
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYTH_Eco") or a.actor_has_tag("PYTH_EcoPlant"): eas.destroy_actor(a)
placed, rejected = eco.generate(7)
SH = {"Sphere": "/Engine/BasicShapes/Sphere.Sphere", "Cone": "/Engine/BasicShapes/Cone.Cone", "Cylinder": "/Engine/BasicShapes/Cylinder.Cylinder"}
def ground(x, y):
    if ew is None: return (L.z - 90, False)
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, L.z + 30000), unreal.Vector(x, y, L.z - 60000),
            unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    return (h.to_tuple()[4].z, True) if h else (L.z - 100, False)
at = unreal.EditorAssetLibrary
gp = ROOT + "/PCG_Ecology"
g = unreal.load_asset(gp)  # reuse (in-memory or on disk) so re-runs never collide
if g:
    for n in list(g.get_editor_property("nodes")): g.remove_node(n)
else: g = unreal.AssetToolsHelpers.get_asset_tools().create_asset("PCG_Ecology", ROOT, unreal.PCGGraph, unreal.PCGGraphFactory())
out_node = g.get_output_node(); made = {}; hits = 0; spawn_list = []
for sp in eco.SPECIES:
    arr = []
    for p in placed:
        if p["species"] != sp["name"]: continue
        x, y = ox + p["x"] * 100 * S, oy + p["y"] * 100 * S
        z, ok = ground(x, y); hits += ok
        if not ok: continue          # no ground under it: skip rather than float
        s = p["scale"] * S   # shrink plants with the patch so crown spacing (competition) keeps its geometry
        pt = unreal.PCGPoint()
        pt.set_editor_property("transform", unreal.Transform(unreal.Vector(x, y, z + sp["h"] * 50 * s),
            unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]), unreal.Vector(2 * sp["r"] * s, 2 * sp["r"] * s, sp["h"] * s)))
        pt.set_editor_property("seed", len(arr) + 1); arr.append(pt); spawn_list.append((sp, pt.get_editor_property("transform")))
    cnode, cset = g.add_node_of_type(unreal.PCGCreatePointsSettings)
    cset.set_editor_property("points_to_create", arr)
    try: cset.set_editor_property("coordinate_space", unreal.PCGCoordinateSpace.WORLD)
    except Exception as e: unreal.log_warning("coord space: %s" % e)
    snode, sset = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    sel = sset.get_editor_property("mesh_selector_parameters")
    e = unreal.PCGMeshSelectorWeightedEntry()
    d = e.get_editor_property("descriptor"); d.set_editor_property("static_mesh", unreal.load_asset(SH[sp["shape"]])); e.set_editor_property("descriptor", d)
    e.set_editor_property("weight", 1)
    sel.set_editor_property("mesh_entries", [e])  # instanced UObject: edit in place
    g.add_edge(cnode, "Out", snode, "In"); g.add_edge(snode, "Out", out_node, "Out")  # the output node's input pin is labelled "Out"
    made[sp["name"]] = len(arr)
at.save_loaded_asset(g)
vol = eas.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(cx, cy, L.z))
vol.set_actor_scale3d(unreal.Vector(D / 200 + 2, D / 200 + 2, 300)); vol.set_actor_label("PYTH_PCG_Ecology"); vol.tags = ["PYTH_Eco"]
comp = vol.get_component_by_class(unreal.PCGComponent)
comp.set_graph(g)
comp.generate(True)
unreal.EditorAssetLibrary.save_loaded_asset(g)
# ground fit: re-trace every point and compare spawned base to ground
float_n = sunk = 0
for p in placed:
    x, y = ox + p["x"] * 100 * S, oy + p["y"] * 100 * S
    z, ok = ground(x, y)
    if not ok: float_n += 1
ues.set_level_viewport_camera_info(unreal.Vector(cx - D * 0.55, cy - D * 0.55, L.z + D * 0.45), unreal.Rotator(roll=0, pitch=-30, yaw=45))
gf = {"traced_on_ground": hits, "no_ground_under": float_n}
result = {"ground_fit": gf, "graph": gp, "points": made, "ground_hits": hits, "patch": {"scale": S, "ground_cover_probe": COVER}, "centre": [round(cx), round(cy), round(L.z)], "pie": bool(gw), "editor_world": ew.get_path_name()}

# Fallback (2026-10-12): in this editor the PCG component accepts generate() but never runs (no LogPCG lines,
# generated stays False; the PCG plugin isn't enabled in DaedalusRealm.uproject, only its classes are loaded).
# So the same points are also placed as tagged StaticMeshActors with per-species colour material instances
# (assets under /Game/Pythagoras/PCGEcology). When PCG does generate, these are skipped.
fallback = 0
if not comp.get_editor_property("generated"):
    at2 = unreal.AssetToolsHelpers.get_asset_tools()
    parent = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")
    mis = {}
    for sp in eco.SPECIES:
        mp = ROOT + "/MI_Eco_" + sp["name"]
        mi = unreal.load_asset(mp) or at2.create_asset("MI_Eco_" + sp["name"], ROOT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*sp["tint"], 1.0))
        unreal.EditorAssetLibrary.save_loaded_asset(mi); mis[sp["name"]] = mi
    with unreal.ScopedSlowTask(len(spawn_list), "Pythagoras: placing ecology") as task:
        for sp, tr in spawn_list:
            a = eas.spawn_actor_from_object(unreal.load_asset(SH[sp["shape"]]), tr.translation, tr.rotation.rotator())
            a.set_actor_scale3d(tr.scale3d); a.tags = ["PYTH_EcoPlant"]
            a.set_actor_label("Eco_%s_%d" % (sp["name"], fallback)); a.set_folder_path("Pythagoras/PCGEcology")
            smc = a.static_mesh_component; smc.set_material(0, mis[sp["name"]]); smc.set_collision_profile_name("NoCollision")  # persists through save/reload (set_collision_enabled did not)
            fallback += 1
result["fallback_actors"] = fallback