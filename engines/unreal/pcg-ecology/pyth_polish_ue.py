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
    a = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, -200); a.constant = unreal.LinearColor(*c1, 1)
    b = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, 0); b.constant = unreal.LinearColor(*c2, 1)
    wp = MEL.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, 200)
    nz = MEL.create_material_expression(m, unreal.MaterialExpressionNoise, -600, 200); nz.scale = scale; nz.levels = 3
    MEL.connect_material_expressions(wp, "", nz, "Position")
    lp = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -300, 0)
    MEL.connect_material_expressions(a, "", lp, "A"); MEL.connect_material_expressions(b, "", lp, "B"); MEL.connect_material_expressions(nz, "", lp, "Alpha")
    MEL.connect_material_property(lp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200); r.r = rough
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); eal.save_asset(p); return m
grass = make_mat("M_PYT_IslandGrass", (0.16, 0.32, 0.08), (0.30, 0.42, 0.12), 0.9, 0.004)
rock = make_mat("M_PYT_IslandRock", (0.22, 0.19, 0.16), (0.40, 0.36, 0.30), 0.95, 0.002)
soil = make_mat("M_PYT_HerbSoil", (0.18, 0.12, 0.07), (0.28, 0.2, 0.12), 1.0, 0.02)
les.set_current_level_by_name(SUB)
n = {"labels": 0, "ground": 0, "rock": 0, "beds": 0}
for a in eas.get_all_level_actors():
    if not a.actor_has_tag(TAG): continue
    lb = a.get_actor_label()
    if isinstance(a, unreal.TextRenderActor):
        L = a.get_actor_location(); yaw = math.degrees(math.atan2(CAM.y - L.y, CAM.x - L.x))
        a.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=yaw), False)
        a.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER); a.text_render.set_text_render_color(unreal.Color(255, 245, 210, 255)); n["labels"] += 1
    elif lb == "PYT_Island_Ground": a.static_mesh_component.set_material(0, grass); n["ground"] += 1
    elif lb.startswith("PYT_Island_Rock"): a.static_mesh_component.set_material(0, rock); n["rock"] += 1
    elif lb.startswith("HerbBed_") or lb == "PYT_FoodTable": a.static_mesh_component.set_material(0, soil); n["beds"] += 1
les.save_current_level()
E = unreal.EditorLoadingAndSavingUtils
mine = [p for p in E.get_dirty_content_packages() if p.get_name().startswith("/Game/Pythagoras/")]
if mine: E.save_packages(mine, True)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(CAM, unreal.Rotator(roll=0, pitch=-32, yaw=45))
result = n
