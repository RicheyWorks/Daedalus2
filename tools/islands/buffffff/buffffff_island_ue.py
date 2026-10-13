"""Buffffff Island (Buffffff, Team Grok). Unreal Editor Python, run ONLY in a granted Grok editor turn:
  python ...\\pcg-ecology\\ue_send.py C:\\Users\\730ri\\projects\\bot-team\\art\\buffffff\\buffffff_island_ue.py 900
Imports the 560 BUF GLBs to /Game/Buffffff/Art (skips ones already imported), then places them from layout.json
into sublevel /Game/Buffffff/Maps/Buffffff_Island at OFFSET. Idempotent (removes its tagged actors first). No Play."""
import json, os, unreal
ROOT = r"C:\Users\730ri\projects\bot-team\art\buffffff"; DEST = "/Game/Buffffff/Art"; SUB = "/Game/Buffffff/Maps/Buffffff_Island"
TAG = "BUF_Island"; OFFSET = unreal.Vector(290000, 148500, 0)  # compact cluster (Richey 23:14): 1 km east of 2hot2trot Ark Dock, no overlap
HALF = int(globals().get("BUF_HALF", 0))  # 1 or 2: import half of the layout; 0 = all; 3 = place+shot only
eas = unreal.EditorAssetLibrary; act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lay = json.load(open(os.path.join(ROOT, "layout.json")))
CHAIN = ["Prop_BUF_Water_Spring_V2","Prop_BUF_Pipe_Straight","Prop_BUF_Water_SandFilter_V1","Prop_BUF_Pipe_Elbow","Prop_BUF_Water_CharcoalFilter_V1","Prop_BUF_Pipe_Valve","Prop_BUF_Water_Cistern_V2","Prop_BUF_Pipe_Tee","Prop_BUF_Trough_Long","Prop_BUF_Pipe_Spigot","Prop_BUF_Trough_Round","Prop_BUF_Lore_ShardSpring"]
for i,c in enumerate(CHAIN): lay.append({"asset":c,"x":-60.0+i*6.0,"y":-45.0,"yaw":0,"s":1,"chain":i})
CORE = bool(int(globals().get("BUF_CORE", 0)))  # core mode: ~100 key meshes, resumable, ~6 min import budget
if CORE:
    import math
    CS = json.load(open(os.path.join(ROOT, "core.json"), encoding="utf-8-sig"))
    seen = {a["asset"] for a in lay}
    extra = [n for n in CS if n not in seen]
    for i, n in enumerate(extra):  # core meshes with no layout spot: ring near the village
        ang = 2 * math.pi * i / max(1, len(extra)); lay.append({"asset": n, "x": 35 * math.cos(ang), "y": 35 * math.sin(ang), "yaw": 0, "s": 1})
    keep = set(CS) | {x.split("/")[4] for x in eas.list_assets(DEST, recursive=True) if x.count("/") >= 5}
    if int(globals().get("BUF_CORE_ONLY", 0)): keep = set(CS)
    lay = [a for a in lay if a["asset"] in keep]
    HALF = 0
uniq = sorted({a["asset"] for a in lay}); mid = len(uniq)//2
imp = uniq[:mid] if HALF == 1 else uniq[mid:] if HALF == 2 else [] if HALF == 3 else uniq
tasks = []
for n in imp:
    k = n.split("_")[0]
    if eas.does_directory_exist(f"{DEST}/{n}") and eas.list_assets(f"{DEST}/{n}", recursive=True): continue
    if any(eas.does_asset_exist(p) for p in (f"{DEST}/{n}/{n}", f"{DEST}/{n}", f"/Game/Daedalus/Art/{k}/{n}/{n}", f"/Game/Daedalus/Art/{k}/{n}")): continue
    t = unreal.AssetImportTask(); t.filename = os.path.join(ROOT, "glb", n + ".glb"); t.destination_path = f"{DEST}/{n}"
    t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
import time as _t; _t0 = _t.time(); BUDGET = float(globals().get("BUF_BUDGET", 330)); _left = len(tasks)
_B = 5 if CORE else 20
for _i in range(0, len(tasks), _B):
    if CORE and _t.time() - _t0 > BUDGET: print("BUF import budget hit, remaining", _left, "(resume next turn)"); break
    _left -= len(tasks[_i:_i+_B])
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[_i:_i+_B]); print("BUF batch", _i, len(tasks))
def _place():
  return None
if HALF == 1:
    print("BUF half1 imported", len(tasks)); _stop = True
else: _stop = False
if not _stop:
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not eas.does_asset_exist(SUB):
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    ls = unreal.GameplayStatics.get_streaming_level(world, SUB.split("/")[-1]) or unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
    unreal.EditorLevelUtils.make_level_current(ls)
    for x in act.get_all_level_actors():
        if x.actor_has_tag(TAG): act.destroy_actor(x)
    base = act.spawn_actor_from_class(unreal.StaticMeshActor, OFFSET - unreal.Vector(0, 0, 800), unreal.Rotator(0, 0, 0))
    base.static_mesh_component.set_static_mesh(eas.load_asset("/Engine/BasicShapes/Cylinder")); base.set_actor_scale3d(unreal.Vector(240, 240, 8))
    base.tags = [TAG]; base.set_actor_label("BUF_Island_Ground"); base.set_folder_path("Buffffff_Island")
    ok = 0; miss = []
    for a in lay:
        n = a["asset"]; m = None
        k = n.split("_")[0]
        for p in (f"/Game/Daedalus/Art/{k}/{n}/{n}", f"/Game/Daedalus/Art/{k}/{n}", f"{DEST}/{n}/{n}", f"{DEST}/{n}"):
            if eas.does_asset_exist(p): m = eas.load_asset(p); break
        if m is None:
            lst = eas.list_assets(f"{DEST}/{n}", recursive=True)
            sm = [p for p in lst if isinstance(eas.load_asset(p), unreal.StaticMesh)]
            m = eas.load_asset(sm[0]) if sm else None
        if not isinstance(m, unreal.StaticMesh): miss.append(n); continue
        s = act.spawn_actor_from_object(m, OFFSET + unreal.Vector(a["x"] * 100, a["y"] * 100, 0), unreal.Rotator(0, 0, a.get("yaw", 0)))
        s.set_actor_scale3d(unreal.Vector(a.get("s", 1), a.get("s", 1), a.get("s", 1)))
        grp = a["asset"].split("_")[2]; WATER = grp in ("Water","Trough","Pipe") or "chain" in a; s.tags = [TAG, grp] + (["Drinkable","WaterChain"] if WATER else []) + (["Livestock"] if a["asset"].startswith("Mob_BUF_") and "Pest" not in a["asset"] else []) + (["HerbBed"] if grp in ("Herb","HerbPlot") else []); s.set_folder_path("Buffffff_Island"); ok += 1
    unreal.EditorLevelLibrary.save_current_level()  # own sublevel only; never the persistent DaedalusWorld
    if HALF in (2, 3):  # hero shot from an aerial camera
        cam = act.spawn_actor_from_class(unreal.CameraActor, OFFSET + unreal.Vector(9500, -9500, 5500), unreal.Rotator(0, -28, 135))
        cam.tags = [TAG]; cam.set_actor_label("BUF_HeroCam"); cam.set_folder_path("Buffffff_Island")
        unreal.EditorLevelLibrary.pilot_level_actor(cam)
        unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, r"C:\Users\730ri\projects\bot-team\art\buffffff\hero\Buffffff_Island_UE_hero.png", cam)
        unreal.EditorLevelLibrary.eject_pilot_level_actor()
        unreal.EditorLevelLibrary.save_current_level()  # own sublevel only; never the persistent DaedalusWorld
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les.is_in_play_in_editor(): les.editor_request_end_play()
    except Exception as e: print("pie", e)
    try: unreal.EditorLoadingAndSavingUtils.save_map(world, world.get_path_name().split(".")[0])
    except Exception as e: print("savemap", e)
    tagc = lambda t: sum(1 for x in act.get_all_level_actors() if x.actor_has_tag(t))
    print("BUF counts total", tagc(TAG), "livestock", tagc("Livestock"), "drinkable", tagc("Drinkable"), "herbbed", tagc("HerbBed"), "world", world.get_path_name())
    print("BUF placed", ok, "missing", len(miss), miss[:10])








