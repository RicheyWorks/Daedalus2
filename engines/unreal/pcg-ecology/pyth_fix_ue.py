# SPDX-License-Identifier: MIT
"""island:pythagoras round-2 fixes (editor turn): per-actor downward-trace ground snapping, brighter grass,
delete broken v1 materials (ours only). Saves our sublevel + /Game/Pythagoras packages only."""
import unreal
import sys; sys.path.insert(0, r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology")
SUB = "Island_Pythagoras"; TAG = "PYT_Island"; ORIGIN = unreal.Vector(-60000, 60000, 2500)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ew = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
MEL = unreal.MaterialEditingLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary
if les.is_in_play_in_editor(): les.editor_request_end_play()
les.set_current_level_by_name(SUB)
def make_mat(name, c1, c2, rough, scale):
    p = "/Game/Pythagoras/Materials/" + name
    if eal.does_asset_exist(p): return unreal.load_asset(p)
    m = AT.create_asset(name, "/Game/Pythagoras/Materials", unreal.Material, unreal.MaterialFactoryNew())
    a = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, -200); a.set_editor_property("constant", unreal.LinearColor(*c1, 1))
    b = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, 0); b.set_editor_property("constant", unreal.LinearColor(*c2, 1))
    wp = MEL.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, 200)
    nz = MEL.create_material_expression(m, unreal.MaterialExpressionNoise, -600, 200); nz.set_editor_property("scale", scale); nz.set_editor_property("levels", 3)
    MEL.connect_material_expressions(wp, "", nz, "Position")
    lp = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -300, 0)
    MEL.connect_material_expressions(a, "", lp, "A"); MEL.connect_material_expressions(b, "", lp, "B"); MEL.connect_material_expressions(nz, "", lp, "Alpha")
    MEL.connect_material_property(lp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200); r.set_editor_property("r", rough)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); eal.save_asset(p); return m
grass = make_mat("M_PYT_IslandGrass_v3", (0.32, 0.58, 0.14), (0.50, 0.70, 0.22), 0.85, 0.004)
acts = [a for a in eas.get_all_level_actors() if a.actor_has_tag(TAG)]
import importlib, pyth_groundfit as GF; importlib.reload(GF)
fixed = checked = 0; worst_before = 0.0
for a in acts:
    lb = a.get_actor_label()
    if lb == "PYT_Island_Ground": a.static_mesh_component.set_material(0, grass)
    if not isinstance(a, unreal.StaticMeshActor): continue
    sm = a.static_mesh_component.static_mesh
    if GF.excluded(lb, sm.get_name() if sm else ""): continue
    L = a.get_actor_location()
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(L.x, L.y, L.z + 600), unreal.Vector(L.x, L.y, L.z - 3000),
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); checked += 1
    if not t[0]: continue
    d = L.z - t[4].z; worst_before = max(worst_before, abs(d))
    if GF.classify(d, 5.0) != "ok": a.set_actor_location(unreal.Vector(L.x, L.y, t[4].z), False, False); fixed += 1
# old materials: swap every reference to the working replacement, then delete (consolidate does both, ours only)
gone = []; MAT = "/Game/Pythagoras/Materials/"
for old, new in (("M_PYT_IslandGrass", "M_PYT_IslandGrass_v3"), ("M_PYT_IslandGrass_v2", "M_PYT_IslandGrass_v3"),
                 ("M_PYT_IslandRock", "M_PYT_IslandRock_v2"), ("M_PYT_HerbSoil", "M_PYT_HerbSoil_v2")):
    if eal.does_asset_exist(MAT + old) and eal.does_asset_exist(MAT + new):
        if eal.consolidate_assets(unreal.load_asset(MAT + new), [unreal.load_asset(MAT + old)]): gone.append(old)
        if eal.does_asset_exist(MAT + old) and not eal.find_package_referencers_for_asset(MAT + old, False) and eal.delete_asset(MAT + old) and old not in gone: gone.append(old)
# --- batch 3: import new glbs (skip existing) + chapter set pieces
import os, glob, random
GLB = r"C:\Users\730ri\projects\bot-team\art\glb\pythagoras"
def dest(n): k, g = n.split("_")[0], n.split("_PYT_")[1].split("_")[0]; return "/Game/Pythagoras/Art/%s/%s" % (k, g)
tasks = []
for f in sorted(glob.glob(os.path.join(GLB, "*.glb"))):
    nm = os.path.splitext(os.path.basename(f))[0]
    if eal.does_asset_exist(dest(nm) + "/" + nm) or eal.list_assets(dest(nm) + "/" + nm, True, False): continue
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest(nm); t.destination_name = nm; t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
if tasks: AT.import_asset_tasks(tasks)
def mesh(nm):
    for p in eal.list_assets(dest(nm), True, False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name().startswith(nm): return a
les.set_current_level_by_name(SUB)
for a in eas.get_all_level_actors():
    if a.actor_has_tag("PYT_Chapter"): eas.destroy_actor(a)
R = random.Random(11); placed = 0
def gz(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, ORIGIN + unreal.Vector(x, y, 3000), ORIGIN + unreal.Vector(x, y, -3000), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); return (t[4].z - ORIGIN.z) if t[0] else 0.0
def put(nm, x, y, yaw=0, s=1.0):
    global placed
    m = mesh(nm)
    if not m: return
    a = eas.spawn_actor_from_object(m, ORIGIN + unreal.Vector(x, y, gz(x, y)), unreal.Rotator(roll=0, pitch=0, yaw=yaw)); a.set_actor_scale3d(unreal.Vector(s, s, s))
    a.tags = [TAG, "PYT_Chapter"]; a.set_folder_path("Pythagoras/Island/Chapters"); a.set_actor_label("CH_%s_%d" % (nm, placed)); a.static_mesh_component.set_collision_profile_name("NoCollision"); placed += 1
for i, (x, y) in enumerate([(-2700, -2700), (-2700, 2700), (2700, 2700), (2700, -2700), (0, 900), (4600, -4000)]): put("Prop_Quest_PYT_SeralStone_V%d" % (i + 1), x, y, R.uniform(0, 360))
for i in range(6): put("Prop_Tree_PYT_NursePine_V%d" % (1 + i), 2400 + R.uniform(-900, 900), 3600 + R.uniform(-900, 900), R.uniform(0, 360))
for i in range(5): put("Prop_Live_PYT_SaplingGuard_V%d" % (1 + i), -3600 + i * 350, 3800, R.uniform(0, 360))
put("Prop_Craft_PYT_DryingRack_V1", 900, -3600); put("Prop_Craft_PYT_DryingRack_V2", 1500, -3600)
put("Prop_Craft_PYT_TeaKettle_V1", 4400, -4300); put("Prop_Craft_PYT_SteepingPot_V1", 4800, -4300)
put("Prop_Veh_PYT_ArkSheepCrate_V1", -4400, -500, 90); put("Prop_Veh_PYT_ArkSheepCrate_V2", -4400, 300, 90)
for i in range(4): put("Prop_Dress_PYT_SeedRainBanner_V%d" % (1 + i), -5400 + i * 3600, 5400, 0)
put("Prop_Dress_PYT_StormShelter_V1", -1200, 4400, 30)
put("Prop_Water_PYT_BeaverDam_V1", 1100, 200, 90)
for i in range(3): put("Prop_Live_PYT_Beaver_V%d" % (1 + i), 1200 + R.uniform(-300, 300), 600 + R.uniform(-200, 200), R.uniform(0, 360))
put("Tool_PYT_StreamSpade_V1", -4700, 400); put("Tool_PYT_GrazingCrook_V1", -3700, -1200)
# chapter 7 "Seed Rain": jays at the old-growth oaks, Ark Raft + Islet Beacon on the east shore, Climax Seed by the oaks
for i in range(2): put("Prop_Live_PYT_JayFeeder_V%d" % (1 + i), -3900 + i * 1300, 2500, R.uniform(0, 360))
for i in range(3): put("Prop_Food_PYT_AcornCache_V%d" % (1 + i), -3500 + i * 500, 3900, R.uniform(0, 360))
put("Prop_Quest_PYT_ClimaxSeed_V1", -3200, 3200); put("Prop_Quest_PYT_SeedPod_V1", -2900, 3350); put("Prop_Quest_PYT_SeedPod_V2", -3450, 3000)
put("Prop_Veh_PYT_ArkRaft_V1", 5300, -1500, 90); put("Prop_Dress_PYT_IsletBeacon_V1", 5500, -400); put("Prop_Craft_PYT_SeedSorter_V1", 4600, -1500, 90)
put("Prop_Dress_PYT_ColonistCairn_V1", 5400, 600)
les.save_current_level()
E = unreal.EditorLoadingAndSavingUtils
mine = [p for p in E.get_dirty_content_packages() if p.get_name().startswith("/Game/Pythagoras/")]
if mine: E.save_packages(mine, True)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(ORIGIN + unreal.Vector(-9000, -9000, 7000), unreal.Rotator(roll=0, pitch=-32, yaw=45))
result = {"imported_new": len(tasks), "chapter_props": placed, "checked": checked, "snapped": fixed, "worst_before_cm": round(worst_before, 1), "deleted": gone,
          "others_dirty": [p.get_name() for p in E.get_dirty_content_packages()] + [p.get_name() for p in E.get_dirty_map_packages()]}

