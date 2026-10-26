# SPDX-License-Identifier: MIT
"""Ark Mortar herb-combo station for Ark Dock Isle (2hot2trot). Reusable + idempotent.
Run via: python ue_send.py ark_mortar_ue.py 300 [DO_BUILD=1]
- Always reports: playing, existing mortar actors (tag GROK_ArkMortar or label *ark_mortar*), bench location.
- DO_BUILD=1 and no existing GROK_ArkMortar station and Play off: builds a mortar from basic shapes near the
  crafting bench, a TextRender "Ark Mortar", and one sign per recipe in herb_combos.json, all tagged
  GROK_ArkMortar, clamped inside the island bounds; saves ONLY the ArkDock sublevel; aims the camera at it.
"""
import unreal, json, os
SUB = "ArkDock_2hot2trot"; TAG = "GROK_ArkMortar"; FOLDER = "ArkDock_2hot2trot/Crafting/ArkMortar"
CX, CY = 150000.0, 148500.0; BX = (123000.0, 177000.0); BY = (121500.0, 175500.0)
DO_BUILD = globals().get("DO_BUILD", 0.0) > 0
RECIPES = globals().get("RECIPES", "ark_tonic,storm_salve,seafarer_tea,moon_draught,herd_lick")
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
out = {"playing": bool(ues.get_game_world())}
mine = [a for a in eas.get_all_level_actors() if SUB in a.get_level().get_path_name()]
out["sub_actors"] = len(mine)
tagged = [a for a in mine if a.actor_has_tag(TAG)]
legacy = [a.get_actor_label() for a in mine if "ark_mortar" in a.get_actor_label().lower() or "Sign_Mortar" in a.get_actor_label()]
out["existing_tagged"] = len(tagged); out["legacy_mortar"] = legacy[:10]
bench = next((a for a in mine if "CraftingBench" in a.get_actor_label() or "workbench" in a.get_actor_label().lower()), None)
if bench:
    l = bench.get_actor_location(); out["bench"] = [bench.get_actor_label(), round(l.x), round(l.y), round(l.z)]
    bx, by, bz = l.x, l.y, l.z
else:
    bx, by, bz = CX, CY, 0.0
clamp = lambda v, r: max(r[0] + 500, min(r[1] - 500, v))
def put(shape, x, y, z, sx, sy, sz, label, color=None):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator())
    a.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/%s.%s" % (shape, shape)))
    a.set_actor_scale3d(unreal.Vector(sx / 100.0, sy / 100.0, sz / 100.0))
    a.set_actor_label(label); a.set_folder_path(FOLDER); a.tags = [TAG, "GROK_ArkIsle", "Station_ark_mortar"]
    return a
def text(x, y, z, s, label, size=40, yaw=0.0):
    t = eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    t.text_render.set_text(s); t.text_render.set_world_size(size)
    t.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    t.set_actor_label(label); t.set_folder_path(FOLDER); t.tags = [TAG, "GROK_ArkIsle"]
    return t
if DO_BUILD and not tagged and not out["playing"]:
    les.set_current_level_by_name(SUB)
    mx, my = clamp(bx + 400, BX), clamp(by + 300, BY); gz = bz if bench else 0.0
    added = []
    added.append(put("Cylinder", mx, my, gz + 40, 120, 120, 80, "ArkMortar_Plinth"))
    added.append(put("Cylinder", mx, my, gz + 110, 90, 90, 60, "ArkMortar_Bowl"))
    added.append(put("Cylinder", mx, my, gz + 142, 70, 70, 6, "ArkMortar_BowlInner"))
    p = put("Cylinder", mx + 15, my, gz + 185, 14, 14, 110, "ArkMortar_Pestle"); p.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=0) if False else unreal.Rotator(roll=20, pitch=0, yaw=0), False); added.append(p)
    added.append(text(mx, my, gz + 300, "Ark Mortar", "ArkMortar_Label", 60))
    names = [r.strip() for r in str(RECIPES).split(",") if r.strip()]
    for i, r in enumerate(names):
        sx, sy = clamp(mx - 400 + i * 200, BX), clamp(my + 250, BY)
        added.append(put("Cube", sx, sy, gz + 60, 10, 10, 120, "ArkMortar_SignPost_%s" % r))
        added.append(put("Cube", sx, sy, gz + 140, 90, 8, 50, "ArkMortar_SignBoard_%s" % r))
        added.append(text(sx, sy - 10, gz + 140, r.replace("_", " "), "ArkMortar_Recipe_%s" % r, 16, -90.0))
    out["added"] = len(added); out["station_at"] = [round(mx), round(my), round(gz)]
    out["in_bounds"] = all(BX[0] <= a.get_actor_location().x <= BX[1] and BY[0] <= a.get_actor_location().y <= BY[1] for a in added)
    les.set_current_level_by_name(SUB); out["saved"] = les.save_current_level()
    ues.set_level_viewport_camera_info(unreal.Vector(mx - 900, my - 900, gz + 700), unreal.Rotator(roll=0, pitch=-28, yaw=45))
elif tagged:
    l = tagged[0].get_actor_location(); out["station_at"] = [round(l.x), round(l.y), round(l.z)]
    if globals().get("AIM", 0.0) > 0:
        ues.set_level_viewport_camera_info(unreal.Vector(l.x - 900, l.y - 900, l.z + 700), unreal.Rotator(roll=0, pitch=-28, yaw=45))
print(json.dumps(out)); result = out
