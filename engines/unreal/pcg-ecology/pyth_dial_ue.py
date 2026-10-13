# SPDX-License-Identifier: MIT
"""Playable editor prototype (our turn only): Fire Keeper dial on the live island.
Set DIAL (0..1) below or in pyth_dial.json; the script simulates 100 years at that burn rate on the 12x12 grid (live beaver
dams -> wetland cells that never burn) and shows the result as a coloured tile overlay 30 cm above Island_Pythagoras
(folder Pythagoras/Island/SimOverlay, tag PYT_SimOverlay, no collision), plus a text readout of rate, H and the forester's line.
Re-running replaces the overlay; DIAL < 0 clears it."""
import unreal
import sys; sys.path.insert(0, r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology")
import json, os, random, importlib, quest_hook, rate_dial, fire_keeper
for m in (quest_hook, fire_keeper, rate_dial): importlib.reload(m)
HERE = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
cfg = json.load(open(os.path.join(HERE, "pyth_dial.json"), encoding="utf-8-sig")) if os.path.exists(os.path.join(HERE, "pyth_dial.json")) else {}
DIAL = float(cfg.get("dial", 0.1))
ORIGIN = unreal.Vector(-60000, 60000, 2500); TAG = "PYT_Island"; N = 12; CELL = 1000.0
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); eal = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools(); MEL = unreal.MaterialEditingLibrary
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name("Island_Pythagoras")
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYT_SimOverlay"): eas.destroy_actor(a)
def flat(name, rgb):
    p = "/Game/Pythagoras/Materials/" + name
    if eal.does_asset_exist(p): return unreal.load_asset(p)
    m = AT.create_asset(name, "/Game/Pythagoras/Materials", unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0); c.set_editor_property("constant", unreal.LinearColor(*rgb, 1))
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR); MEL.recompile_material(m); eal.save_asset(p); return m
result = {"cleared": True}
if DIAL >= 0:
    st = rate_dial.dial_state(DIAL)
    dams = [quest_hook.cell(a.get_actor_location().x - ORIGIN.x, a.get_actor_location().y - ORIGIN.y) for a in eas.get_all_level_actors()
            if isinstance(a, unreal.StaticMeshActor) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name().startswith("Prop_Water_PYT_BeaverDam")]
    import keystone_beaver; importlib.reload(keystone_beaver)
    from succession_sim import Island
    wet = set(keystone_beaver.flood(Island(N, 0), dams).water) if dams else set()
    G = rate_dial.simulate_grid(st["rate"], wet, N)
    mats = [flat("M_PYT_Stage%d" % k, c) for k, c in enumerate([(0.75, 0.68, 0.35), (0.40, 0.70, 0.25), (0.15, 0.45, 0.20), (0.05, 0.25, 0.10)])] + [flat("M_PYT_Wetland", (0.15, 0.40, 0.80))]
    plane = unreal.load_asset("/Engine/BasicShapes/Plane.Plane"); counts = [0] * 5
    for j in range(N):
        for i in range(N):
            k = G[j][i]; counts[k] += 1
            x, y = (i + 0.5) * CELL - N * CELL / 2, (j + 0.5) * CELL - N * CELL / 2
            a = eas.spawn_actor_from_object(plane, ORIGIN + unreal.Vector(x, y, 30), unreal.Rotator())
            a.set_actor_scale3d(unreal.Vector(CELL / 100 * 0.96, CELL / 100 * 0.96, 1)); a.static_mesh_component.set_material(0, mats[k])
            a.static_mesh_component.set_collision_profile_name("NoCollision"); a.tags = [TAG, "PYT_SimOverlay"]
            a.set_folder_path("Pythagoras/Island/SimOverlay"); a.set_actor_label("PYT_SimTile_%02d_%02d" % (i, j))
    lab = eas.spawn_actor_from_class(unreal.TextRenderActor, ORIGIN + unreal.Vector(0, -N * CELL / 2 - 600, 1500), unreal.Rotator(yaw=90))
    lab.text_render.set_text("FIRE DIAL %.2f  burn %.3f/yr  H %.2f  %s\n%s" % (DIAL, st["rate"], st["H"], "PASS" if st["pass"] else "TRY AGAIN", st["line"]))
    lab.text_render.set_world_size(220); lab.tags = [TAG, "PYT_SimOverlay"]; lab.set_folder_path("Pythagoras/Island/SimOverlay"); lab.set_actor_label("PYT_SimReadout")
    result = {"dial": DIAL, "rate": st["rate"], "H": st["H"], "pass": st["pass"], "tiles": dict(zip(["bare", "meadow", "scrub_pine", "oak", "wetland"], counts)), "dams": dams}

