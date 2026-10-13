# SPDX-License-Identifier: MIT
"""island:pythagoras (Team Grok) - Wild Biomes ecology island. Editor turn only.
  python ue_send.py pyth_island_ue.py 900
1) imports art\glb\pythagoras\*.glb (512 Blender items) -> /Game/Pythagoras/Art/<Kind>/<Group>/ (skips existing)
2) own sublevel /Game/Pythagoras/Maps/Island_Pythagoras (actors tagged PYT_Island, idempotent)
3) 120 m island (double size): 5 Wild Biomes from the ecology model, drinkable water chain
   (spring -> stream -> pond -> reed filter -> well/cistern -> troughs, rain barrels), livestock pens
   (sheep/hens/bees + shipped Mob meshes), succession herb garden, pet habitat TriggerBoxes.
4) saves only our sublevel; persistent map only if it was clean before we started."""
import sys, os, glob, math, random, unreal
D = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
if D not in sys.path: sys.path.insert(0, D)
import importlib, ecology_rules, wild_biomes
for m in (ecology_rules, wild_biomes): importlib.reload(m)
GLB = r"C:\Users\730ri\projects\bot-team\art\glb\pythagoras"
SUB = "/Game/Pythagoras/Maps/Island_Pythagoras"; TAG = "PYT_Island"
ORIGIN = unreal.Vector(-60000, 60000, 2500)
HALF = 6000.0   # cm: 120 m square island
eal = unreal.EditorAssetLibrary; eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ELS = unreal.EditorLoadingAndSavingUtils
pre_dirty = [p.get_name() for p in ELS.get_dirty_map_packages()] + [p.get_name() for p in ELS.get_dirty_content_packages()]
def dest(n): k, g = n.split("_")[0], n.split("_PYT_")[1].split("_")[0]; return "/Game/Pythagoras/Art/%s/%s" % (k, g)
# 1 import
tasks = []
for f in sorted(glob.glob(os.path.join(GLB, "*.glb"))):
    n = os.path.splitext(os.path.basename(f))[0]
    if eal.does_asset_exist(dest(n) + "/" + n) or eal.list_assets(dest(n) + "/" + n, True, False): continue   # glTF import nests assets in <dest>/<name>/StaticMeshes
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest(n); t.destination_name = n
    t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
for i in range(0, len(tasks), 50): unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i + 50])
_mc = {}
def mesh(n):
    if n in _mc: return _mc[n]
    m = None
    if n.startswith("/"): m = unreal.load_asset(n)
    else:
        for p in eal.list_assets(dest(n), True, False):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh) and a.get_name().startswith(n): m = a; break
    _mc[n] = m; return m
def mob(n):
    for p in eal.list_assets("/Game/Daedalus/Art/Mob/" + n, True, False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh): return a
    return None
# 2 sublevel
w = ues.get_editor_world(); lvl = None
for s in unreal.EditorLevelUtils.get_levels(w):
    if SUB.split("/")[-1] in s.get_path_name(): lvl = s
if lvl is None:
    if eal.does_asset_exist(SUB): unreal.EditorLevelUtils.add_level_to_world(w, SUB, unreal.LevelStreamingAlwaysLoaded)
    else: unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, SUB, False)
    w = ues.get_editor_world(); lvl = [l for l in unreal.EditorLevelUtils.get_levels(w) if SUB.split("/")[-1] in l.get_path_name()][0]
les.set_current_level_by_name(SUB.split("/")[-1])
for a in eas.get_all_level_actors():
    if a.actor_has_tag(TAG): eas.destroy_actor(a)
N = {"n": 0}
def put(sm, x, y, z=0.0, yaw=0.0, s=1.0, label=None, folder="Island", tags=()):
    if isinstance(sm, str): sm = mesh(sm)
    if sm is None: return None
    a = eas.spawn_actor_from_object(sm, ORIGIN + unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.tags = [TAG] + list(tags)
    a.set_folder_path("Pythagoras/Island/" + folder); a.set_actor_label(label or "PYT_%s_%d" % (sm.get_name(), N["n"])); N["n"] += 1
    return a
def nocol(a):
    if a: a.static_mesh_component.set_collision_profile_name("NoCollision")
    return a
R = random.Random(2026)
CUBE, CYL, PLANE = "/Engine/BasicShapes/Cube.Cube", "/Engine/BasicShapes/Cylinder.Cylinder", "/Engine/BasicShapes/Plane.Plane"
# 3a island body: grass top (walkable), soil + rock skirt tapering down
g = put(CUBE, 0, 0, -100, label="PYT_Island_Ground"); g.set_actor_scale3d(unreal.Vector(HALF / 50, HALF / 50, 1))
for k, (sc, dz) in enumerate([(0.92, 900), (0.75, 2600), (0.5, 4800), (0.25, 7000)]):
    r = put(CUBE, 0, 0, -dz, yaw=k * 11, label="PYT_Island_Rock_%d" % k); r.set_actor_scale3d(unreal.Vector(HALF / 50 * sc, HALF / 50 * sc, 16))
# 3b biomes: five 30 m patches around the centre; stream runs through the riverbank patch
SPEC = {"Oak": "Prop_Tree_PYT_Oak_V", "Pine": "Prop_Tree_PYT_Pine_V", "Willow": "Prop_Tree_PYT_Willow_V", "Bramble": "Prop_Shrub_PYT_Bramble_V",
        "Sedge": "Prop_Ground_PYT_Sedge_V", "Grass": "Prop_Ground_PYT_MeadowGrass_V", "Fern": "Prop_Ground_PYT_Fern_V"}
NV = {"Oak": 15, "Pine": 15, "Willow": 15, "Bramble": 10, "Sedge": 10, "Grass": 10, "Fern": 10}
W = 3000.0; WM = 30.0
CENT = {"YoungMeadow": (-3200, -3200), "BrambleScrub": (3200, -3200), "PineStand": (3200, 3200), "OldGrowthOak": (-3200, 3200), "WillowRiverbank": (0, 0)}
counts = {}
for name, pts in wild_biomes.all_biomes(WM).items():
    cx, cy = CENT[name]; n = 0
    for p in pts:
        sp = p["species"]; v = 1 + int(p["scale"] * 97 + p["x"] * 13) % NV[sp]
        a = nocol(put("%s%02d" % (SPEC[sp], v), cx + (p["x"] / WM - .5) * W, cy + (p["y"] / WM - .5) * W, 0, p["yaw"], 0.8 + 0.4 * p["scale"] * 0.5,
                     folder="Biomes/" + name, tags=("PYT_Biome_" + name,)))
        n += a is not None
    counts[name] = n
    hb = put(CUBE, cx, cy, 300, label="PYT_Habitat_" + name, folder="Habitat", tags=("DAEDALUS_Habitat", "Habitat_" + name))
    if hb: hb.set_actor_scale3d(unreal.Vector(W / 100, W / 100, 6)); hb.set_actor_hidden_in_game(True); hb.static_mesh_component.set_visibility(False); nocol(hb)
    lab = eas.spawn_actor_from_class(unreal.TextRenderActor, ORIGIN + unreal.Vector(cx, cy, 2200), unreal.Rotator())
    lab.text_render.set_text(name); lab.text_render.set_world_size(260); lab.tags = [TAG]; lab.set_actor_label("PYT_Label_" + name); lab.set_folder_path("Pythagoras/Island/Labels")
# 3c drinkable water chain (W1..W7)
put("Prop_Water_PYT_Spring_V3", -5000, 0, label="W1_Spring", folder="Water", tags=("Water_Drinkable",))
for i in range(12):   # W2 stream: spring -> pond, gentle meander through the riverbank biome
    x = -4600 + i * 400; y = 350 * math.sin(i / 2.0)
    put("Prop_Water_PYT_StreamSegment_V%d" % (1 + i % 8), x, y, 2, math.degrees(math.atan2(350 * math.cos(i / 2.0) / 2.0, 400)), 1.4, label="W2_Stream_%02d" % i, folder="Water", tags=("Water_Drinkable",))
put("Prop_Water_PYT_PondBasin_V6", 1800, 0, label="W3_Pond", folder="Water", s=1.6, tags=("Water_Drinkable",))
put("Prop_Water_PYT_ReedFilter_V2", 2900, 300, label="W4_ReedFilter", folder="Water")
put("Prop_Water_PYT_Well_V4", 3300, 900, label="W5_Well", folder="Water", tags=("Water_Drinkable",))
put("Prop_Water_PYT_Cistern_V2", 3500, -200, label="W6_Cistern", folder="Water", tags=("Water_Drinkable",))
for i in range(4): put("Prop_Water_PYT_RainBarrel_V%d" % (i + 1), -1000 + i * 500, 1500, label="W7_RainBarrel_%d" % i, folder="Water")
# 3d livestock + food loop: sheep graze the meadow, hens scratch the scrub edge, bees work wildflowers
PEN = (-3200, -400)
for i in range(16):
    a = i / 16 * 2 * math.pi
    put("Prop_Live_PYT_Fence_V%02d" % (1 + i % 10), PEN[0] + 1300 * math.cos(a), PEN[1] + 900 * math.sin(a), 0, math.degrees(a) + 90, label="Pen_Fence_%02d" % i, folder="Livestock")
put("Prop_Live_PYT_SheepShelter_V01", PEN[0] - 700, PEN[1], folder="Livestock"); put("Prop_Live_PYT_HayRack_V01", PEN[0] + 300, PEN[1] + 500, folder="Livestock")
for i in range(3): put("Prop_Water_PYT_Trough_V%d" % (i + 1), PEN[0] + 500, PEN[1] - 500 + i * 300, yaw=90, label="W8_Trough_%d" % i, folder="Water", tags=("Water_Drinkable",))
animals = {}
for nm, cnt, (ax, ay) in (("Mob_Sheep", 5, PEN), ("Mob_Goat", 2, PEN), ("Mob_Chicken", 6, (2400, -2200)), ("Mob_Cow", 1, (PEN[0] + 200, PEN[1] + 200)), ("Mob_Bee", 4, (-2400, -4200))):
    m = mob(nm); animals[nm] = 0
    for i in range(cnt if m else 0):
        put(m, ax + R.uniform(-700, 700), ay + R.uniform(-500, 500), 0 if nm != "Mob_Bee" else 120, R.uniform(0, 360), folder="Livestock", tags=("PYT_Livestock",)); animals[nm] += 1
for i in range(3): put("Prop_Live_PYT_HenCoop_V%02d" % (i + 1), 2000 + i * 400, -2700, folder="Livestock"); put("Prop_Live_PYT_Feeder_V%02d" % (i + 1), 2100 + i * 400, -1900, folder="Livestock")
for i in range(5): put("Prop_Live_PYT_Beehive_V%02d" % (i + 1), -3000 + i * 300, -4800, folder="Livestock")
for i, f in enumerate(["HoneyJar", "EggBasket", "Wool", "MilkPail", "BerryBasket", "HerbBread", "Cheese", "NutSack"]):
    put("Item_Food_PYT_%s_V1" % f, -1900 + i * 60, -900, 80, folder="Food"); 
put(CUBE, -1700, -900, 0, label="PYT_FoodTable", folder="Food").set_actor_scale3d(unreal.Vector(5.5, 1.2, 0.8))
# 3e succession herb garden: 4 beds (one per seral stage), 3 herbs each
HERBS = [["Fireweed", "Yarrow", "Plantain"], ["Selfheal", "Meadowsweet", "Comfrey"], ["Nettle", "Mullein", "Valerian"], ["Woodsorrel", "Ramsons", "Wintergreen"]]
for st, row in enumerate(HERBS):
    bed = put(CUBE, 400 + st * 450, -2600, -40, label="HerbBed_Stage%d" % st, folder="Herbs"); bed.set_actor_scale3d(unreal.Vector(3.6, 6, 0.5))
    for k, h in enumerate(row):
        for r in range(4): nocol(put("Prop_Herb_PYT_%s_V%d" % (h, 1 + r % 5), 300 + st * 450 + k * 100, -2850 + r * 160, 0, R.uniform(0, 360), 1.6, folder="Herbs", tags=("PYT_Herb", "Herb_" + h)))
for i in range(12): put("Item_Tea_PYT_Succession_T%02d" % (i + 1), 350 + i * 130, -3300, 60, folder="Herbs")
# 3f dressing ring
for i in range(36):
    a = i / 36 * 2 * math.pi; r = HALF - 400 - R.uniform(0, 500)
    k = ["Prop_Dress_PYT_Rock_V%02d", "Prop_Dress_PYT_Log_V%02d", "Prop_Dress_PYT_Stump_V%02d", "Prop_Dress_PYT_Mushroom_V%02d"][i % 4] % (1 + i % 10)
    nocol(put(k, r * math.cos(a), r * math.sin(a), 0, R.uniform(0, 360), folder="Dressing"))
for i, k in enumerate(["Birch", "Alder", "Hazel", "Elder", "Gorse"]):
    for j2 in range(6):
        nm = ("Prop_Tree_PYT_%s_V%02d" if k in ("Birch", "Alder") else "Prop_Shrub_PYT_%s_V%02d") % (k, 1 + j2)
        a = (i * 6 + j2) / 30 * 2 * math.pi; nocol(put(nm, (HALF - 1300) * math.cos(a), (HALF - 1300) * math.sin(a), 0, R.uniform(0, 360), folder="Edge"))
# 4 save
les.set_current_level_by_name(SUB.split("/")[-1]); les.save_current_level()
persist_saved = False
if not pre_dirty: persist_saved = ELS.save_dirty_packages(True, False)
dirty = [p.get_name() for p in ELS.get_dirty_map_packages()] + [p.get_name() for p in ELS.get_dirty_content_packages()]
ues.set_level_viewport_camera_info(ORIGIN + unreal.Vector(-9000, -9000, 7000), unreal.Rotator(roll=0, pitch=-32, yaw=45))
result = {"imported": len(tasks), "actors": N["n"], "biomes": counts, "animals": animals, "pre_dirty": pre_dirty,
          "persistent_saved": persist_saved, "dirty_after": dirty, "missing_mesh": [k for k, v in _mc.items() if v is None][:15]}


