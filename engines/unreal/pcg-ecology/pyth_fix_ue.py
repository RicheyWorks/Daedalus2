# SPDX-License-Identifier: MIT
"""island:pythagoras round-2 fixes (editor turn): per-actor downward-trace ground snapping, brighter grass,
delete broken v1 materials (ours only). Saves our sublevel + /Game/Pythagoras packages only."""
import unreal
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
SKIP = ("PYT_Island_", "PYT_Habitat_", "PYT_Label_", "HerbBed_", "PYT_FoodTable")
fixed = checked = 0; worst_before = 0.0
for a in acts:
    lb = a.get_actor_label()
    if lb == "PYT_Island_Ground": a.static_mesh_component.set_material(0, grass)
    if not isinstance(a, unreal.StaticMeshActor) or lb.startswith(SKIP) or "Mob_Bee" in lb: continue
    if a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name().startswith(("Item_", "Tool_")): continue   # table props
    L = a.get_actor_location()
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(L.x, L.y, L.z + 600), unreal.Vector(L.x, L.y, L.z - 3000),
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); checked += 1
    if not t[0]: continue
    d = L.z - t[4].z; worst_before = max(worst_before, abs(d))
    if abs(d) > 5: a.set_actor_location(unreal.Vector(L.x, L.y, t[4].z), False, False); fixed += 1
gone = []
for old in ("M_PYT_IslandGrass", "M_PYT_IslandRock", "M_PYT_HerbSoil", "M_PYT_IslandGrass_v2"):
    p = "/Game/Pythagoras/Materials/" + old
    if eal.does_asset_exist(p) and not unreal.EditorAssetLibrary.find_package_referencers_for_asset(p, False):
        if eal.delete_asset(p): gone.append(old)
les.save_current_level()
E = unreal.EditorLoadingAndSavingUtils
mine = [p for p in E.get_dirty_content_packages() if p.get_name().startswith("/Game/Pythagoras/")]
if mine: E.save_packages(mine, True)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(ORIGIN + unreal.Vector(-9000, -9000, 7000), unreal.Rotator(roll=0, pitch=-32, yaw=45))
result = {"checked": checked, "snapped": fixed, "worst_before_cm": round(worst_before, 1), "deleted": gone,
          "others_dirty": [p.get_name() for p in E.get_dirty_content_packages()] + [p.get_name() for p in E.get_dirty_map_packages()]}
