import unreal, os
D = "C:/Users/730ri/projects/bot-team/art/coats/"
DST = "/Game/DaedalusAudio/Coats"
at = unreal.AssetToolsHelpers.get_asset_tools(); mel = unreal.MaterialEditingLibrary
es = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ue = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_game_world(): raise RuntimeError("PIE running")
files = sorted(f for f in os.listdir(D) if f.endswith(".png"))
tasks = []
for f in files:
    t = unreal.AssetImportTask(); t.filename = D + f; t.destination_path = DST; t.destination_name = "T_" + f[:-4]
    t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
at.import_asset_tasks(tasks)
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("DA_Coat_"): es.destroy_actor(a)
jb = [a for a in es.get_all_level_actors() if a.get_actor_label() == "DA_JukeboxCabinet"]
base = jb[0].get_actor_location() if jb else ue.get_level_viewport_camera_info()[0]
meshes = ["/Engine/BasicShapes/Sphere", "/Engine/BasicShapes/Cylinder", "/Engine/BasicShapes/Cone"]
import math
out = []
for i, f in enumerate(files):
    n = f[:-4]; tex = unreal.load_asset(DST + "/T_" + n)
    mp = DST + "/M_" + n
    if unreal.EditorAssetLibrary.does_asset_exist(mp): unreal.EditorAssetLibrary.delete_asset(mp)
    m = at.create_asset("M_" + n, DST, unreal.Material, unreal.MaterialFactoryNew())
    ts = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -400, 0)
    ts.texture = tex
    mel.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(m); unreal.EditorAssetLibrary.save_loaded_asset(m)
    ang = 2 * math.pi * i / len(files)
    loc = base + unreal.Vector(400 * math.cos(ang), 400 * math.sin(ang), 60)
    a = es.spawn_actor_from_class(unreal.StaticMeshActor, loc); a.set_actor_label("DA_Coat_" + n[5:])
    c = a.static_mesh_component; c.set_static_mesh(unreal.load_asset(meshes[i % 3])); c.set_material(0, m)
    a.set_actor_scale3d(unreal.Vector(1.2, 1.2, 1.2)); out.append((a.get_actor_label(), str(loc)))
unreal.EditorAssetLibrary.save_directory(DST, only_if_is_dirty=False, recursive=True)
unreal.EditorLevelLibrary.save_current_level()
print("coats", out)
