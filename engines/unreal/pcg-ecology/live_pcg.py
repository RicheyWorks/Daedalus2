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
    L, rot = ues.get_level_viewport_camera_info(); yaw = rot.yaw
D = eco.DOMAIN * 100; f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
cx, cy = L.x + f[0] * (2500 + D / 2), L.y + f[1] * (2500 + D / 2)
ox, oy = cx - D / 2, cy - D / 2
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYTH_Eco"): eas.destroy_actor(a)
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
out_node = g.get_output_node(); made = {}; hits = 0
for sp in eco.SPECIES:
    arr = []
    for p in placed:
        if p["species"] != sp["name"]: continue
        x, y = ox + p["x"] * 100, oy + p["y"] * 100
        z, ok = ground(x, y); hits += ok
        s = p["scale"]
        pt = unreal.PCGPoint()
        pt.set_editor_property("transform", unreal.Transform(unreal.Vector(x, y, z + sp["h"] * 50 * s),
            unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]), unreal.Vector(2 * sp["r"] * s, 2 * sp["r"] * s, sp["h"] * s)))
        pt.set_editor_property("seed", len(arr) + 1); arr.append(pt)
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
    g.add_edge(cnode, "Out", snode, "In"); g.add_edge(snode, "Out", out_node, "In")
    made[sp["name"]] = len(arr)
at.save_loaded_asset(g)
vol = eas.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(cx, cy, L.z))
vol.set_actor_scale3d(unreal.Vector(D / 200 + 2, D / 200 + 2, 300)); vol.set_actor_label("PYTH_PCG_Ecology"); vol.tags = ["PYTH_Eco"]
comp = vol.get_component_by_class(unreal.PCGComponent)
comp.set_graph(g)
comp.generate(True)
result = {"graph": gp, "points": made, "ground_hits": hits, "centre": [round(cx), round(cy), round(L.z)], "pie": bool(gw), "editor_world": ew.get_path_name()}
