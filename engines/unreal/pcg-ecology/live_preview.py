# SPDX-License-Identifier: MIT
"""Fast visible preview: drop the ecology patch into the running editor's world (PIE if playing,
else the editor level) as one actor with an InstancedStaticMesh per species, snapped to the ground
by line traces. Sent through the Claude Unreal bridge (execute_python). Re-running replaces it."""
import sys, math, unreal, importlib
sys.path.insert(0, r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology")
import ecology_rules as eco; importlib.reload(eco)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_game_world() or ues.get_editor_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
if pawn:
    L = pawn.get_actor_location(); yaw = math.radians(pawn.get_actor_rotation().yaw)
else:
    L, rot = ues.get_level_viewport_camera_info(); yaw = math.radians(rot.yaw)
D = eco.DOMAIN * 100
ox = L.x + math.cos(yaw) * 2500 - D / 2 + math.cos(yaw) * D / 2
oy = L.y + math.sin(yaw) * 2500 - D / 2 + math.sin(yaw) * D / 2
# Python can't spawn actors into a PIE world, but it can add components to one that exists.
# Host = the level's Daedalus world actor (or any static actor with a root); our ISMs are tagged for cleanup.
pie = w is not ues.get_editor_world()
if pie:
    cands = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
             if a.root_component and a is not pawn and not isinstance(a, unreal.Pawn) and not isinstance(a, unreal.Controller)]
    host = next((a for a in cands if "Daedalus" in a.get_class().get_name()), cands[0])
else:
    host = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.Actor, unreal.Vector(ox, oy, L.z))
for c in host.get_components_by_class(unreal.InstancedStaticMeshComponent):
    if c.component_has_tag("PYTH_EcoPreview"):
        c.destroy_component(c)
SH = {"Sphere": "/Engine/BasicShapes/Sphere.Sphere", "Cone": "/Engine/BasicShapes/Cone.Cone", "Cylinder": "/Engine/BasicShapes/Cylinder.Cylinder"}
base = unreal.load_asset("/Engine/BasicShapeMaterial.BasicShapeMaterial") or unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")
placed, _ = eco.generate(7)
counts = {}; hits = 0
for sp in eco.SPECIES:
    c = host.add_component_by_class(unreal.InstancedStaticMeshComponent, False, unreal.Transform(), False)
    c.component_tags = ["PYTH_EcoPreview"]
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_static_mesh(unreal.load_asset(SH[sp["shape"]]))
    mid = unreal.MaterialInstanceDynamic.create(base, host) if base else None
    if mid:
        mid.set_vector_parameter_value("Color", unreal.LinearColor(*sp["tint"], 1.0)); c.set_material(0, mid)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    n = 0
    for p in placed:
        if p["species"] != sp["name"]: continue
        x, y = ox + p["x"] * 100, oy + p["y"] * 100
        hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, L.z + 20000), unreal.Vector(x, y, L.z - 40000),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn] if pawn else [], unreal.DrawDebugTrace.NONE, True)
        z = L.z - 100 + p["z"] * 100 * 0.3
        if hit:
            hits += 1; z = hit.to_tuple()[4].z
        s = p["scale"]; r, h = sp["r"], sp["h"]
        c.add_instance(unreal.Transform(unreal.Vector(x, y, z + h * 50 * s), unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]),
                                        unreal.Vector(2 * r * s / 1.0, 2 * r * s / 1.0, h * s)), True)  # world space
        n += 1
    counts[sp["name"]] = c.get_instance_count()
result = {"host": host.get_name(), "world": w.get_path_name(), "origin": [round(ox), round(oy), round(L.z)], "counts": counts, "ground_hits": hits}
