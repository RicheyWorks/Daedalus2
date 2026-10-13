# Kennel Isle (art-master-flex, Team Grok). Editor turn only, after buffffff grants the Grok slot.
#   python ue_send.py C:\Users\730ri\projects\bot-team\art\NOTES\amf\amf_island_ue.py 900
# 1) imports art\glb\amf\*.glb -> /Game/AMF/Art/<Kind>/  (skips already-imported)
# 2) builds/refreshes our own sublevel /Game/AMF/Maps/Island_AMF (actors tagged AMF_Island, idempotent)
# 3) saves only our sublevel. Never touches other sublevels.
import unreal, os, glob, math, random
GLB = r"C:\Users\730ri\projects\bot-team\art\glb\amf"
MAP = "/Game/Daedalus/DaedalusWorld"; SUB = "/Game/AMF/Maps/Island_AMF"; TAG = "AMF_Island"
ORIGIN = unreal.Vector(4000000, 2000000, 2000)   # cm; change if it collides with another island
eal = unreal.EditorAssetLibrary; eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
def dest(n): return "/Game/AMF/Art/" + n.split("_")[0] + "/" + n.split("_AMF_")[1].split("_")[0]
# --- 1 import
tasks = []
for f in sorted(glob.glob(os.path.join(GLB, "*.glb"))):
    n = os.path.splitext(os.path.basename(f))[0]
    if eal.does_asset_exist(dest(n) + "/" + n): continue
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest(n); t.destination_name = n
    t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
for i in range(0, len(tasks), 50):
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i+50])
unreal.log("AMF imported %d" % len(tasks))
def mesh(n):
    for p in eal.list_assets(dest(n), True, False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name().startswith(n.split("_V")[0][:20]): return a
    return None
# --- 2 sublevel
w = ues.get_editor_world()
if w is None or "DaedalusWorld" not in w.get_path_name():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP); w = ues.get_editor_world()
lvl = None
for sl in unreal.EditorLevelUtils.get_levels(w):
    if SUB in sl.get_path_name(): lvl = sl
if lvl is None:
    if eal.does_asset_exist(SUB): unreal.EditorLevelUtils.add_level_to_world(w, SUB, unreal.LevelStreamingDynamic)
    else: unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, False)
    w = ues.get_editor_world()
    lvl = [l for l in unreal.EditorLevelUtils.get_levels(w) if SUB in l.get_path_name()][0]
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(SUB.split("/")[-1])
for a in eas.get_all_level_actors():
    if TAG in [str(t) for t in a.tags]: eas.destroy_actor(a)
def put(sm, x, y, z=0, yaw=0, s=1.0, label=None):
    if isinstance(sm, str): sm = unreal.load_asset(sm) if sm.startswith("/") else mesh(sm)
    if sm is None: return None
    a = eas.spawn_actor_from_object(sm, ORIGIN + unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.tags = [TAG]
    a.set_folder_path("AMF/KennelIsle"); a.set_actor_label(label or sm.get_name()); return a
R = random.Random(1789)
# platform: grass top + rock skirt (engine cube = 100cm)
CUBE = "/Engine/BasicShapes/Cube.Cube"; PLANE = "/Engine/BasicShapes/Plane.Plane"
top = put(CUBE, 0, 0, -100, s=1); top.set_actor_scale3d(unreal.Vector(60, 60, 1)); top.set_actor_label("KennelIsle_Ground")
sk = put(CUBE, 0, 0, -1400, s=1); sk.set_actor_scale3d(unreal.Vector(52, 52, 13)); sk.set_actor_label("KennelIsle_Rock")
# WATER SYSTEM: spring -> stream -> filter -> cistern -> pipes -> troughs; rain catchers + still top up the cistern
put("Prop_Water_AMF_SpringBasin_V1", -2000, -2000, label="W1_Spring")
pond = put(PLANE, -2000, -2000, 30); pond.set_actor_scale3d(unreal.Vector(4, 4, 1)); pond.set_actor_label("W1_SpringPool")
for i in range(6):   # stream channel of shallow water planes from spring to filter
    s = put(PLANE, -1600 + i * 250, -1600 + i * 250, 5); s.set_actor_scale3d(unreal.Vector(2.5, 1.2, 1)); s.set_actor_label("W2_Stream_%d" % i)
for i, (x, y) in enumerate([(-600, 600), (-200, 900), (200, 900)]): put("Prop_Water_AMF_RainCatcher_V%d" % (i + 1), x, y, label="W3_RainCatch_%d" % i)
put("Prop_Water_AMF_Filter_V1", 0, 0, label="W4_SandCharcoalFilter")
put("Prop_Water_AMF_Cistern_V1", 300, 0, label="W5_Cistern")
put("Prop_Water_AMF_SolarStill_V1", 300, -400, label="W6_SolarStill_Backup")
put("Prop_Water_AMF_Well_V1", -900, 300, label="W7_Well_Backup")
for i in range(8): put("Prop_Water_AMF_PipeStraight_V1", 450 + i * 100, 0, 30, label="W8_Pipe_%d" % i)
put("Prop_Water_AMF_PipeTee_V1", 1250, 0, 30, label="W8_PipeTee")
for i in range(4): put("Prop_Water_AMF_Trough_V%d" % (i + 1), 1500, -900 + i * 600, yaw=90, label="W9_Trough_%d" % i)
# pet camp + livestock pen
for i in range(4): put("Prop_Pet_AMF_Kennel_V%d" % (i + 1), 2200, -900 + i * 600, yaw=-90)
for i in range(4): put("Prop_Pet_AMF_Bed_V%d" % (i + 1), 1900, -800 + i * 600); put("Prop_Pet_AMF_Bowl_V%d" % (i + 1), 1700, -700 + i * 600)
for i in range(12): put("Prop_Live_AMF_Fence_V%d" % (i % 20 + 1), -2600 + i * 100, 1800, label="Pen_Fence_%d" % i)
put("Prop_Live_AMF_Gate_V1", -1300, 1800); put("Prop_Live_AMF_GoatShelter_V1", -2200, 2300)
for i in range(4): put("Prop_Live_AMF_HayBale_V%d" % (i + 1), -1800 + i * 120, 2400)
put("Prop_Water_AMF_Trough_V5", -1600, 2100, label="W9_Trough_Pen")
# herb garden (trough-brew tonics): 12 species x 3 rows near the trough line
HERBS = ["Barkbalm","Pawmint","Howlroot","Snoutsage","Furfern","Wagwort","Ironfang","Dewclaw","Starkibble","Coppercap","Guardthistle","Dozeleaf"]
for i, h in enumerate(HERBS):
    for r in range(3): put("Prop_Herb_AMF_%s_V%d" % (h, r + 1), 600 + (i % 6) * 150, 1400 + (i // 6) * 450 + r * 120, yaw=R.uniform(0, 360))
# dressing
for i in range(24):
    a = i * 15 * math.pi / 180; put(("Prop_Dress_AMF_Rock_V%d" if i % 2 else "Prop_Dress_AMF_Bush_V%d") % (i + 1), math.cos(a) * 2800, math.sin(a) * 2800, yaw=R.uniform(0, 360))
for i in range(6): put("Prop_Dress_AMF_Lantern_V%d" % (i + 1), 1500 + (i % 2) * 900, -1200 + (i // 2) * 1000)
# animals: the world Corso (Mob_CaneCorso, Richey's decision) + pets + livestock
MOB = "/Game/Daedalus/Art/Mob/"
def mob(n, x, y, yaw=0):
    for p in eal.list_assets(MOB + n, True, False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name() in (n, n + "_Body"): return put(a, x, y, yaw=yaw, label=n)
mob("Mob_CaneCorso", 1700, 0, 180)
for i, (n, x, y) in enumerate([("Mob_CorsoPup", 1900, 300), ("Mob_RedPanda", 900, 1600), ("Mob_MossTurtle", -1900, -1700), ("Mob_Capybara", -1500, -1500),
                               ("Mob_PygmyGoat", -2100, 2000), ("Mob_PygmyGoat", -1900, 2150), ("Mob_PygmyGoat", -1700, 2000), ("Mob_Capybara", -1600, 2200)]):
    mob(n, x, y, R.uniform(0, 360))
# --- 3 save our sublevel only, stop PIE if any
try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
except Exception: pass
unreal.EditorLoadingAndSavingUtils.save_map(lvl.get_outer() if hasattr(lvl, "get_outer") else lvl, SUB)
unreal.log("AMF_ISLAND_DONE actors=%d" % len([a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]]))

