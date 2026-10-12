"""Buffffff Island (Buffffff, Team Grok). Unreal Editor Python, run ONLY in a granted Grok editor turn:
  python ...\\pcg-ecology\\ue_send.py C:\\Users\\730ri\\projects\\bot-team\\art\\buffffff\\buffffff_island_ue.py 900
Imports the 560 BUF GLBs to /Game/Buffffff/Art (skips ones already imported), then places them from layout.json
into sublevel /Game/Buffffff/Maps/Buffffff_Island at OFFSET. Idempotent (removes its tagged actors first). No Play."""
import json, os, unreal
ROOT = r"C:\Users\730ri\projects\bot-team\art\buffffff"; DEST = "/Game/Buffffff/Art"; SUB = "/Game/Buffffff/Maps/Buffffff_Island"
TAG = "BUF_Island"; OFFSET = unreal.Vector(2600000, 2600000, 0)
eas = unreal.EditorAssetLibrary; act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lay = json.load(open(os.path.join(ROOT, "layout.json")))
tasks = []
for a in lay:
    n = a["asset"]
    if eas.does_asset_exist(f"{DEST}/{n}/{n}") or eas.does_asset_exist(f"{DEST}/{n}"): continue
    t = unreal.AssetImportTask(); t.filename = os.path.join(ROOT, "glb", n + ".glb"); t.destination_path = f"{DEST}/{n}"
    t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
if tasks: unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
world = unreal.EditorLevelLibrary.get_editor_world()
if not eas.does_asset_exist(SUB):
    unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
ls = unreal.GameplayStatics.get_streaming_level(world, SUB.split("/")[-1]) or unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
unreal.EditorLevelUtils.make_level_current(ls.get_loaded_level())
for x in act.get_all_level_actors():
    if x.actor_has_tag(TAG): act.destroy_actor(x)
base = act.spawn_actor_from_class(unreal.StaticMeshActor, OFFSET - unreal.Vector(0, 0, 800), unreal.Rotator(0, 0, 0))
base.static_mesh_component.set_static_mesh(eas.load_asset("/Engine/BasicShapes/Cylinder")); base.set_actor_scale3d(unreal.Vector(240, 240, 8))
base.tags = [TAG]; base.set_actor_label("BUF_Island_Ground"); base.set_folder_path("Buffffff_Island")
ok = 0; miss = []
for a in lay:
    n = a["asset"]; m = None
    for p in (f"{DEST}/{n}/{n}", f"{DEST}/{n}"):
        if eas.does_asset_exist(p): m = eas.load_asset(p); break
    if m is None:
        lst = eas.list_assets(f"{DEST}/{n}", recursive=True)
        sm = [p for p in lst if isinstance(eas.load_asset(p), unreal.StaticMesh)]
        m = eas.load_asset(sm[0]) if sm else None
    if not isinstance(m, unreal.StaticMesh): miss.append(n); continue
    s = act.spawn_actor_from_object(m, OFFSET + unreal.Vector(a["x"] * 100, a["y"] * 100, 0), unreal.Rotator(0, 0, 0))
    s.tags = [TAG, a["asset"].split("_")[2]]; s.set_folder_path("Buffffff_Island"); ok += 1
unreal.EditorLevelLibrary.save_all_dirty_levels()
print("BUF placed", ok, "missing", len(miss), miss[:10])
