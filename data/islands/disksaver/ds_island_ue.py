# DiskSaver Island (disk-saver, Team Grok). Editor turn only (granted Grok slot).
#   python ds_ue_send.py ds_island_ue.py 600
# Builds our own sublevel /Game/DiskSaver/Maps/Island_DiskSaver (actors tagged DS_Island), saves only it.
# Never destroys actors: if DS_Island actors already exist it stops (re-runs need a human decision).
import unreal, math, random
MAP = "/Game/Daedalus/DaedalusWorld"; SUB = "/Game/DiskSaver/Maps/Island_DiskSaver"; TAG = "DS_Island"
ORIGIN = unreal.Vector(4000000, 4000000, 2000)
SHOT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\diskSaver_island.png"
eal = unreal.EditorAssetLibrary; eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
out = {"placed": 0, "missing": []}
_cache = {}
import os
GLB = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
SHIPPED = set(l.split("|")[2].strip() for l in open(r"C:\Users\730ri\projects\bot-team\art\QUEUE.md", encoding="utf-8") if "_DS_" in l and "| SHIPPED" in l)
def _first_mesh(folder):
    if eal.does_directory_exist(folder):
        for p in eal.list_assets(folder, True, False):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    return None
def mesh(n):
    if n in _cache: return _cache[n]
    k = n.split("_")[0]; m = None
    if n in SHIPPED: m = _first_mesh("/Game/Daedalus/Art/%s/%s" % (k, n))   # judged by the watcher
    if m is None:   # not drained yet: import our own glb into our own folder
        own = "/Game/DiskSaver/Art/%s/%s" % (k, n); m = _first_mesh(own)
        f = os.path.join(GLB, n + ".glb")
        if m is None and os.path.exists(f):
            t = unreal.AssetImportTask(); t.filename = f; t.destination_path = own; t.destination_name = n
            t.automated = True; t.save = True; t.replace_existing = True
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]); out["imported"] = out.get("imported", 0) + 1
            m = _first_mesh(own)
    if m is None: out["missing"].append(n)
    _cache[n] = m; return m
try:
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise SystemExit("PIE running: refusing to touch the level (not stopping someone else's Play)")
except AttributeError: pass
w = ues.get_editor_world()
if w is None or "DaedalusWorld" not in w.get_path_name():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP); w = ues.get_editor_world()
if any(TAG in [str(t) for t in a.tags] for a in eas.get_all_level_actors()):
    raise SystemExit("DS_Island actors already present; not rebuilding (no deletes)")
lvl = None
for sl in unreal.EditorLevelUtils.get_levels(w):
    if SUB in sl.get_path_name(): lvl = sl
if lvl is None:
    if eal.does_asset_exist(SUB): unreal.EditorLevelUtils.add_level_to_world(w, SUB, unreal.LevelStreamingDynamic)
    else: unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, False)
    w = ues.get_editor_world()
    lvl = [l for l in unreal.EditorLevelUtils.get_levels(w) if SUB in l.get_path_name()][0]
_sl = unreal.GameplayStatics.get_streaming_level(w, "Island_DiskSaver")
if _sl is None: raise SystemExit("could not find streaming level for " + SUB)
unreal.EditorLevelUtils.make_level_current(_sl)
R = random.Random(4004)
import time
T0 = time.time()
def put(sm, x, y, z=0, yaw=0, s=1.0, label=None, folder="DiskSaver"):
    if time.time() - T0 > 240: out["timed_out"] = True; return None
    if isinstance(sm, str): sm = unreal.load_asset(sm) if sm.startswith("/") else mesh(sm)
    if sm is None: return None
    a = eas.spawn_actor_from_object(sm, ORIGIN + unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.tags = [TAG]
    a.set_folder_path("DiskSaver/" + folder); a.set_actor_label(label or sm.get_name()); out["placed"] += 1; return a
CUBE = "/Engine/BasicShapes/Cube.Cube"; PLANE = "/Engine/BasicShapes/Plane.Plane"
g = put(CUBE, 0, 0, -100, label="DS_Ground", folder="Terrain"); g.set_actor_scale3d(unreal.Vector(90, 90, 1))
r = put(CUBE, 0, 0, -1600, label="DS_RockSkirt", folder="Terrain"); r.set_actor_scale3d(unreal.Vector(80, 80, 15))
# rocky centre: spring + well + rocks
put("Prop_DS_Water_SpringRocks_V0", 0, 0, label="W1_Spring", folder="Water")
put("Prop_DS_Water_Well_V0", 600, 200, label="W2_Well", folder="Water")
for i in range(16):
    a = i * 2 * math.pi / 16; rr = 500 + (i % 3) * 150
    put("Prop_DS_Rock_%02d" % (6 + (i % 4) * 8), math.cos(a) * rr, math.sin(a) * rr, yaw=R.uniform(0, 360), folder="RockyCentre")
for i in range(6):
    p = put(PLANE, 300 + i * 300, -300 - i * 300, 5, label="W3_Stream_%d" % i, folder="Water")
    if p: p.set_actor_scale3d(unreal.Vector(3, 1.2, 1))
put("Prop_DS_Water_PondEdge_V0", 2200, -2200, label="W4_Pond", folder="Water")
put("Prop_DS_Water_FilterBarrel_V0", 1700, -1500, label="W5_FilterBarrel", folder="Water")
put("Prop_DS_Water_FilterBarrel_V1", 1850, -1500, label="W5_FilterBarrel_2", folder="Water")
put("Prop_DS_Water_Bucket_V0", 650, 350, label="W6_Bucket", folder="Water")
put("Prop_DS_Water_Canteen_V0", 700, 360, 0, label="W6_Canteen", folder="Water")
# farm (east): crops plots
crops = ["Clover", "Groat", "Kelpweed", "Bitroot", "Spudlet"]
for ci, c in enumerate(crops):
    for j in range(6):
        put("Prop_DS_Crop_%s_S%d_V0" % (c, 3 if j % 2 else 2), 2000 + j * 110, 400 + ci * 220, folder="Farm")
put("Prop_DS_Water_Gutter_V0", 1900, 300, label="W7_Gutter", folder="Water")
put("Prop_DS_Water_CisternBarrel_V0", 1850, 250, label="W8_Cistern", folder="Water")
put("Prop_DS_CompostBin_V0", 2800, 300, folder="Farm"); put("Prop_DS_HerbCompressor", 1500, 900, folder="Farm")
put("Prop_DS_DryingRack", 1500, 1200, folder="Farm"); put("Prop_DS_Campfire_V0", 1200, 700, folder="Farm")
put("Prop_DS_Cauldron_V0", 1250, 800, folder="Farm")
# coop + pens (west)
put("Bld_DS_Coop", -2200, 1500, folder="Livestock")
for i in range(10): put("Prop_DS_Fence_Seg_00", -3200 + i * 220, 2600, folder="Livestock")
for i in range(6): put("Prop_DS_Fence_Seg_00", -3300, 2500 - i * 220, yaw=90, folder="Livestock")
put("Prop_DS_Fence_Gate_12", -1000, 2600, folder="Livestock")
put("Prop_DS_Trough", -1800, 2200, label="W9_Trough", folder="Water"); put("Prop_DS_FencePen", -2600, 600, folder="Livestock")
for i in range(3): put("Prop_DS_Haystack_V0", -3000 + i * 150, 2300, folder="Livestock")
put("Prop_DS_FeedSack_V0", -2000, 1200, folder="Livestock")
animals = [("Mob_DS_ByteHen", -2000, 1700), ("Mob_DS_ByteHen", -2100, 1850), ("Mob_DS_DriftDuck", -1800, 1600),
           ("Mob_DS_MossGoat", -2600, 2200), ("Mob_DS_MossGoat", -2450, 2300), ("Mob_DS_TidePig", -2800, 1900),
           ("Mob_DS_CacheCow", -3000, 2100), ("Mob_DS_CacheCow", -2900, 2350), ("Mob_DS_DriftDuck", 2150, -2050)]
for n, x, y in animals: put(n, x, y, yaw=R.uniform(0, 360), folder="Livestock")
# herb garden (north)
herbs = ["CacheLeaf","BufferBloom","OverclockThorn","DefragMoss","SwapRoot","ParityPetal","ChecksumClover","LatencyLily","ZipVine","ArchiveSage"]
for i, h in enumerate(herbs):
    for st in (1, 2, 3):
        put("Prop_DS_Herb_%s_S%d" % (h, st), -1200 + i * 250, -1800 - st * 150, yaw=R.uniform(0, 360), folder="Herbs")
# trees ring + wild herbs
for i in range(28):
    a = i * 2 * math.pi / 28; rr = 3600 + R.uniform(-200, 300)
    put("Prop_DS_Tree_%02d" % (8 + (i % 6) * 5), math.cos(a) * rr, math.sin(a) * rr, yaw=R.uniform(0, 360), folder="Trees")
for i in range(12):
    a = R.uniform(0, 2 * math.pi); rr = R.uniform(2800, 3300)
    put("Prop_DS_Herb_%s_S3" % herbs[i % 10], math.cos(a) * rr, math.sin(a) * rr, folder="Herbs")
out["levels_saved"] = bool(unreal.EditorLevelLibrary.save_all_dirty_levels())
try:
    out["world_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_map(ues.get_editor_world(), MAP))
except Exception as e:
    out["world_save_err"] = str(e)
try:
    ues.set_level_viewport_camera_info(ORIGIN + unreal.Vector(-5200, -5200, 4200), unreal.Rotator(0, -32, 45))
    unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, SHOT)
    out["screenshot"] = SHOT
except Exception as e:
    out["screenshot_err"] = str(e)
unreal.log("DS_ISLAND_DONE %s" % out)
print("DS_ISLAND_DONE", out)
result = out
