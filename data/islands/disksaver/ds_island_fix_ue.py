# DiskSaver Island FIX pass (disk-saver, Team Grok). Granted editor turn only.
#   python ds_ue_send.py ds_island_fix_ue.py 420
# Our sublevel only (/Game/DiskSaver/Maps/Island_DiskSaver), assets only under /Game/DiskSaver. No deletes:
# replaced looks are overwrite-reimports, swapped meshes or hidden-in-game originals. ~6 min guard, then save.
import unreal, os, time, math
T0 = time.time(); LIMIT = 330
SUB = "/Game/DiskSaver/Maps/Island_DiskSaver"; TAG = "DS_Island"; MAP = "/Game/Daedalus/DaedalusWorld"
GLB = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
SHOT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\diskSaver_island_v2.png"
eal = unreal.EditorAssetLibrary; eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
out = {"reimported": 0, "swapped": 0, "materials": 0, "hooks": {}, "missing": [], "notes": []}
def hook(k): out["hooks"][k] = out["hooks"].get(k, 0) + 1
import ctypes
class _MS(ctypes.Structure):
    _fields_=[("l",ctypes.c_ulong),("m",ctypes.c_ulong),("t",ctypes.c_ulonglong),("a",ctypes.c_ulonglong),("x1",ctypes.c_ulonglong),("x2",ctypes.c_ulonglong),("x3",ctypes.c_ulonglong),("x4",ctypes.c_ulonglong),("x5",ctypes.c_ulonglong)]
def free_gb():
    try:
        s=_MS(); s.l=ctypes.sizeof(_MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)); return s.a/2**30
    except Exception: return 99.0
def late():
    if free_gb() < 1.0:
        if "LOW RAM: stopped early" not in out["notes"]: out["notes"].append("LOW RAM: stopped early")
        return True
    return time.time() - T0 > LIMIT
try:
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise SystemExit("PIE running: refusing (not stopping someone else's Play)")
except AttributeError: pass
w = ues.get_editor_world()
if w is None or "DaedalusWorld" not in w.get_path_name(): raise SystemExit("DaedalusWorld not open")
sl = unreal.GameplayStatics.get_streaming_level(w, "Island_DiskSaver")
if sl is None: raise SystemExit("Island_DiskSaver sublevel not in world")
unreal.EditorLevelUtils.make_level_current(sl)
mine = [a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
out["actors_before"] = len(mine)
def lab(a): return a.get_actor_label()
def smc(a):
    try: return a.static_mesh_component
    except Exception: return None
# ---------- 1. meshes: overwrite-reimport our glbs (offsets now baked into vertices) and point actors at them
def first_mesh(folder):
    if eal.does_directory_exist(folder):
        for p in eal.list_assets(folder, True, False):
            x = unreal.load_asset(p)
            if isinstance(x, unreal.StaticMesh): return x
    return None
names = {}
for a in mine:
    c = smc(a)
    if c and c.static_mesh and "_DS_" in c.static_mesh.get_name() and ("Tree" in c.static_mesh.get_name() or not c.static_mesh.get_path_name().startswith("/Game/DiskSaver/")):
        names.setdefault(c.static_mesh.get_name(), []).append(a)
tasks = []
for n in names:
    f = os.path.join(GLB, n + ".glb")
    if not os.path.exists(f): out["missing"].append(n); continue
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = "/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n)
    t.destination_name = n; t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
for i in range(0, len(tasks), 10):
    if late(): out["notes"].append("reimport cut by time"); break
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i+10]); out["reimported"] += len(tasks[i:i+10])
for n, acts in names.items():
    if late(): break
    m = first_mesh("/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n))
    if m is None: continue
    for a in acts:
        if smc(a).static_mesh != m: smc(a).set_static_mesh(m); out["swapped"] += 1
# ---------- 2. materials: grass ground, stone skirt, visible water (instances under /Game/DiskSaver/Materials)
mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools()
def mic(name, parent_path, rgb, opacity=None):
    path = "/Game/DiskSaver/Materials/" + name
    if eal.does_asset_exist(path): return unreal.load_asset(path)
    parent = unreal.load_asset(parent_path)
    if parent is None: out["notes"].append("no parent " + parent_path); return None
    mi = at.create_asset(name, "/Game/DiskSaver/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    vn = [str(x) for x in mel.get_vector_parameter_names(parent)]
    pick = [x for x in vn if "color" in x.lower() or "base" in x.lower() or "tint" in x.lower()] or vn
    if pick: mel.set_material_instance_vector_parameter_value(mi, pick[0], unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    else: out["notes"].append(name + ": parent has no vector params")
    if opacity is not None:
        for s in [str(x) for x in mel.get_scalar_parameter_names(parent)]:
            if "opac" in s.lower(): mel.set_material_instance_scalar_parameter_value(mi, s, opacity)
    eal.save_asset(path); out["materials"] += 1; return mi
grass = mic("MI_DS_Grass", "/Game/Daedalus/Materials/M_DaedalusOpaque", (0.20, 0.55, 0.16))
stone = unreal.load_asset("/Game/Daedalus/Materials/M_Stone") or mic("MI_DS_Stone", "/Game/Daedalus/Materials/M_DaedalusOpaque", (0.42, 0.42, 0.45))
water = mic("MI_DS_Water", "/Game/Daedalus/Materials/M_DaedalusTranslucent", (0.12, 0.38, 0.85), 0.65)
for a in mine:
    L = lab(a); c = smc(a)
    if not c: continue
    if L == "DS_Ground" and grass: c.set_material(0, grass); hook("grass")
    elif L == "DS_RockSkirt" and stone: c.set_material(0, stone); hook("stone")
    elif L.startswith("W3_Stream") and water: c.set_material(0, water); hook("water_plane")
# ---------- 3. gameplay hooks (DaedalusLink classes; skipped cleanly if a class is not compiled)
def spawn(cls, loc, label, tags):
    x = eas.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0))
    x.tags = [TAG] + tags; x.set_folder_path("DiskSaver/Gameplay"); x.set_actor_label(label); return x
DRINK = ("W1_Spring", "W2_Well", "W6_Bucket", "W6_Canteen")
RAW = ("W3_Stream", "W4_Pond", "W8_Cistern", "W7_Gutter", "W9_Trough")
for a in mine:
    if late(): break
    L = lab(a); loc = a.get_actor_location(); tags = [str(t) for t in a.tags]
    if L.startswith(DRINK) or L.startswith(RAW):
        q = "Drinkable" if L.startswith(DRINK) else "RawWater"
        if q not in tags: a.tags = tags + ["DS_Water", q]; hook("water_tag_" + q)
        if hasattr(unreal, "DaedalusWaterSource") and not L.startswith("W3_Stream_") or (L == "W3_Stream_0" and hasattr(unreal, "DaedalusWaterSource")):
            ws = spawn(unreal.DaedalusWaterSource, loc, "DS_WaterSource_" + L, ["DS_WaterLogic"])
            try: ws.set_editor_property("quality", "clean" if q == "Drinkable" else "raw")
            except Exception as e: out["notes"].append("WaterSource prop: " + str(e)[:80])
            hook("WaterSource")
    if L.startswith("W5_FilterBarrel") and hasattr(unreal, "DaedalusWaterFilter"):
        spawn(unreal.DaedalusWaterFilter, loc + unreal.Vector(0, -120, 0), "DS_Filter_" + L, ["DS_WaterTreat", "Filter"]); hook("WaterFilter")
    if L.startswith(("Prop_DS_Cauldron", "Prop_DS_Campfire")) and hasattr(unreal, "DaedalusKettle"):
        spawn(unreal.DaedalusKettle, loc + unreal.Vector(0, 150, 0), "DS_BoilKettle_" + L, ["DS_WaterTreat", "Boil"]); hook("Kettle_boil")
    if L.startswith(("Prop_DS_HerbCompressor", "Prop_DS_DryingRack")) and hasattr(unreal, "DaedalusKettle"):
        k = spawn(unreal.DaedalusKettle, loc + unreal.Vector(150, 0, 0), "DS_Brew_" + ("Compressor" if "Compressor" in L else "TeaRack"), ["DS_Brew"])
        hook("Kettle_brew")
    if "_DS_Herb_" in L and L.endswith("_S3") or ("_DS_Herb_" in L and "_S3" in L):
        if hasattr(unreal, "DaedalusStarbloom"):
            sp = L.split("_DS_Herb_")[1].split("_")[0]
            b = spawn(unreal.DaedalusStarbloom, loc, "DS_Herb_" + sp + "_%d" % out["hooks"].get("Starbloom", 0), ["DS_Herb", "Harvestable", sp])
            try:
                b.set_editor_property("species", sp)
                if smc(a) and smc(a).static_mesh: b.get_editor_property("body").set_static_mesh(smc(a).static_mesh)
                a.set_actor_hidden_in_game(True)   # the Starbloom carries the same mesh and is pickable; original kept, not deleted
            except Exception as e: out["notes"].append("Starbloom: " + str(e)[:80])
            hook("Starbloom")
        else:
            a.tags = tags + ["DS_Herb", "Harvestable"]; hook("herb_tag")
    if L.startswith("Mob_DS_"):
        sp = L.split("Mob_DS_")[1].split("_")[0]
        a.tags = tags + ["DS_Livestock", sp, "Pen_West", "Feeds_W9_Trough"]; hook("livestock_tag")
        if hasattr(unreal, "DaedalusLivestock"):
            PROD = {"ByteHen": ("Egg", 4.0), "MossGoat": ("GoatMilk", 8.0), "TidePig": ("Manure", 6.0), "CacheCow": ("Milk", 10.0), "DriftDuck": ("Egg", 5.0)}
            l = spawn(unreal.DaedalusLivestock, loc, "DS_Livestock_" + sp + "_%d" % out["hooks"].get("Livestock", 0), ["DS_LivestockLogic"])
            for k, v in (("species", sp), ("product", PROD.get(sp, ("", 5.0))[0]), ("produce_every_min", PROD.get(sp, ("", 5.0))[1])):
                try: l.set_editor_property(k, v)
                except Exception: pass
            a.attach_to_actor(l, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
            hook("Livestock")
for cls in ("DaedalusWaterSource", "DaedalusLivestock", "DaedalusWaterFilter", "DaedalusKettle", "DaedalusStarbloom"):
    if not hasattr(unreal, cls): out["notes"].append(cls + " not compiled: skipped")
# ---------- 4. save our sublevel + DaedalusWorld, screenshot
out["levels_saved"] = bool(unreal.EditorLevelLibrary.save_all_dirty_levels())
try: out["world_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_map(ues.get_editor_world(), MAP))
except Exception as e: out["world_save_err"] = str(e)[:120]
out["actors_after"] = len([a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]])
try:
    ues.set_level_viewport_camera_info(unreal.Vector(4000000, 4000000, 2000) + unreal.Vector(-3800, -3800, 2600), unreal.Rotator(0, -28, 45))
    unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, SHOT); out["screenshot"] = SHOT
except Exception as e: out["screenshot_err"] = str(e)[:120]
out["seconds"] = round(time.time() - T0, 1)
print("DS_FIX_DONE", out)
result = out
