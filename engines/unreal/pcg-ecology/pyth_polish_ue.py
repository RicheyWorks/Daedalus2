# SPDX-License-Identifier: MIT
"""island:pythagoras polish (editor turn): labels face the showcase camera, real ground + rock materials.
Touches only PYT_Island actors in our sublevel; saves our sublevel + /Game/Pythagoras packages only."""
import math, unreal
SUB = "Island_Pythagoras"; TAG = "PYT_Island"
ORIGIN = unreal.Vector(-60000, 60000, 2500); CAM = ORIGIN + unreal.Vector(-9000, -9000, 7000)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MEL = unreal.MaterialEditingLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary
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
grass = make_mat("M_PYT_IslandGrass_v2", (0.16, 0.32, 0.08), (0.30, 0.42, 0.12), 0.9, 0.004)
rock = make_mat("M_PYT_IslandRock_v2", (0.22, 0.19, 0.16), (0.40, 0.36, 0.30), 0.95, 0.002)
soil = make_mat("M_PYT_HerbSoil_v2", (0.18, 0.12, 0.07), (0.28, 0.2, 0.12), 1.0, 0.02)
les.set_current_level_by_name(SUB)
n = {"labels": 0, "ground": 0, "rock": 0, "beds": 0}
for a in eas.get_all_level_actors():
    if not a.actor_has_tag(TAG): continue
    lb = a.get_actor_label()
    if isinstance(a, unreal.TextRenderActor):
        L = a.get_actor_location(); yaw = math.degrees(math.atan2(CAM.y - L.y, CAM.x - L.x))
        a.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=yaw), False)
        a.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER); a.text_render.set_text_render_color(unreal.Color(255, 245, 210, 255)); n["labels"] += 1
    elif lb == "PYT_Island_Ground":
        a.static_mesh_component.set_material(0, grass); n["ground"] += 1
        g = a.get_actor_location(); a.set_actor_location(unreal.Vector(g.x, g.y, ORIGIN.z - 50), False, False)   # ground fit: cube top was 50 cm below the plants
    elif lb.startswith("PYT_Island_Rock"): a.static_mesh_component.set_material(0, rock); n["rock"] += 1
    elif lb.startswith("HerbBed_") or lb == "PYT_FoodTable": a.static_mesh_component.set_material(0, soil); n["beds"] += 1
# --- batch 2: import new glbs (skip existing) + Climax Seed adventure set
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
    if a.actor_has_tag("PYT_Adventure"): eas.destroy_actor(a)
R = random.Random(7); adv = 0
def put(nm, x, y, z=0, yaw=0, s=1.0, label=None):
    global adv
    m = mesh(nm)
    if not m: return None
    a = eas.spawn_actor_from_object(m, ORIGIN + unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw)); a.set_actor_scale3d(unreal.Vector(s, s, s))
    a.tags = [TAG, "PYT_Adventure"]; a.set_folder_path("Pythagoras/Island/Adventure"); a.set_actor_label(label or "ADV_%s_%d" % (nm, adv)); adv += 1
    a.static_mesh_component.set_collision_profile_name("NoCollision"); return a
put("Prop_Dress_PYT_OldStump_V4", 4600, -4600, label="ADV_OldStump")                      # Climax Seed altar
put("Item_Quest_PYT_ClimaxSeed_V2", 4600, -4600, 85, label="ADV_ClimaxSeed")
put("Prop_Tree_PYT_GreatOak_V3", 4200, -3700, label="ADV_GreatOak_Future", s=0.9)
for i, (x, y) in enumerate([(-3200, -1800), (-1800, -3200), (1800, -3200), (3200, 1800), (0, 1600), (4200, -4200)]):
    put("Prop_Sign_PYT_Chapter_V%d" % (1 + i % 5), x, y, yaw=R.uniform(0, 360), label="ADV_Chapter%d_Sign" % (i + 1))
for i in range(4): put("Prop_Dress_PYT_AshScar_V%d" % (i + 1), -3600 + i * 350, -4200 + R.uniform(-200, 200), yaw=R.uniform(0, 360))
for i in range(3): put("Prop_Dress_PYT_WindthrowLog_V%d" % (i + 1), -3000 + i * 500, 2600, yaw=R.uniform(0, 360))
for i in range(4): put("Prop_Live_PYT_Deer_V%d" % (i + 1), -3400 + R.uniform(-900, 900), 3400 + R.uniform(-900, 900), yaw=R.uniform(0, 360))
for i in range(5): put("Prop_Live_PYT_Frog_V%d" % (i + 1), 1500 + R.uniform(-500, 500), R.uniform(-400, 400), yaw=R.uniform(0, 360))
for i in range(3): put("Tool_PYT_FireweedTorch_V%d" % (i + 1), -1700 + i * 60, -900, 80, yaw=90)
for i, k in enumerate(["Pioneer", "Meadow", "Scrub", "Forest", "Riparian"]): put("Item_Seed_PYT_%sPouch_V1" % k, -1400 + i * 60, -900, 80)
n["adventure"] = adv; n["imported_new"] = len(tasks)
les.save_current_level()
E = unreal.EditorLoadingAndSavingUtils
mine = [p for p in E.get_dirty_content_packages() if p.get_name().startswith("/Game/Pythagoras/")]
if mine: E.save_packages(mine, True)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(CAM, unreal.Rotator(roll=0, pitch=-32, yaw=45))
result = n



