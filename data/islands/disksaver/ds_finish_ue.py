# DiskSaver FINISH pass (hooks re-run for guard-skipped actors, 0.5 GB guard, v4 shot); from FIX pass (disk-saver, Team Grok). Granted editor turn only.
#   python ds_ue_send.py ds_island_fix_ue.py 420
# Our sublevel only (/Game/DiskSaver/Maps/Island_DiskSaver), assets only under /Game/DiskSaver. No deletes:
# replaced looks are overwrite-reimports, swapped meshes or hidden-in-game originals. ~6 min guard, then save.
import unreal, os, time, math
T0 = time.time(); LIMIT = 330
LIGHT = True   # True in ds_island_fix_light_ue.py: no imports (RAM < 1 GB), only swap to already-imported meshes + materials + hooks
SUB = "/Game/DiskSaver/Maps/Island_DiskSaver"; TAG = "DS_Island"; MAP = "/Game/Daedalus/DaedalusWorld"
GLB = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\glb"
SHOT = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\diskSaver_island_v4.png"
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
    if free_gb() < 0.5:
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
# ---------- 1. meshes: actors are identified by their mesh ASSET FOLDER (labels are often just "Cube").
ART_ROOTS = ("/Game/DiskSaver/Art/", "/Game/Daedalus/Art/")
def asset_of(a):
    c = smc(a)
    if not c or not c.static_mesh: return None
    p = c.static_mesh.get_path_name()
    for r in ART_ROOTS:
        if p.startswith(r):
            parts = p.split("/")
            return parts[5] if len(parts) > 5 else None
    return None
names = {}
for a in mine:
    n = asset_of(a)
    if n and "_DS_" in n: names.setdefault(n, []).append(a)
out["distinct_assets"] = len(names)
def own_mesh(n):
    p = "/Game/DiskSaver/Art/%s/%s/%s" % (n.split("_")[0], n, n)
    if eal.does_asset_exist(p): return unreal.load_asset(p)
    d = "/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n)
    if eal.does_directory_exist(d):
        for q in eal.list_assets(d, True, False):
            if q.split("/")[-1].split(".")[0] == n:
                x = unreal.load_asset(q)
                if isinstance(x, unreal.StaticMesh): return x
    return None
tasks = []
for n in names:
    f = os.path.join(GLB, n + ".glb")
    if not os.path.exists(f): out["missing"].append(n); continue
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = "/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n)
    t.destination_name = n; t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
if LIGHT: out["notes"].append("LIGHT: %d reimports skipped" % len(tasks)); tasks = []
for i in range(0, len(tasks), 10):
    if late(): out["notes"].append("reimport cut early"); break
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i+10]); out["reimported"] += len(tasks[i:i+10])
for n, acts in names.items():
    if late(): break
    m = own_mesh(n)
    if m is None: out["notes"].append("no single mesh " + n) if len(out["notes"]) < 30 else None; continue
    for a in acts:
        if smc(a).static_mesh != m: smc(a).set_static_mesh(m); out["swapped"] += 1
        if lab(a).startswith("Cube") or lab(a) == "": a.set_actor_label(n)
# ---------- 2. materials: own tint parents (Color vector param) + instances under /Game/DiskSaver/Materials
mel = unreal.MaterialEditingLibrary; at = unreal.AssetToolsHelpers.get_asset_tools(); MD = "/Game/DiskSaver/Materials"
def tint_parent(name, translucent):
    p = MD + "/" + name
    if eal.does_asset_exist(p): return unreal.load_asset(p)
    m = at.create_asset(name, MD, unreal.Material, unreal.MaterialFactoryNew())
    v = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0)
    v.set_editor_property("parameter_name", "Color"); v.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mel.connect_material_property(v, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 200)
    r.set_editor_property("parameter_name", "Roughness"); r.set_editor_property("default_value", 0.8)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if translucent:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        o = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 350)
        o.set_editor_property("parameter_name", "Opacity"); o.set_editor_property("default_value", 0.6)
        mel.connect_material_property(o, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(m); eal.save_asset(p); return m
def mic(name, parent, rgb, rough=0.8, opacity=None):
    path = MD + "/" + name
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else at.create_asset(name, MD, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)   # existing round-2 instances are re-parented, not deleted
    mel.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
    if opacity is not None: mel.set_material_instance_scalar_parameter_value(mi, "Opacity", opacity)
    eal.save_asset(path); out["materials"] += 1; return mi
P_OP = tint_parent("M_DS_Tint", False); P_TR = tint_parent("M_DS_TintWater", True)
grass = mic("MI_DS_Grass", P_OP, (0.13, 0.42, 0.10)); stone = mic("MI_DS_Stone", P_OP, (0.35, 0.34, 0.33), 0.9)
water = mic("MI_DS_Water", P_TR, (0.05, 0.25, 0.75), 0.1, 0.6); leaf = mic("MI_DS_Leaf", P_OP, (0.16, 0.50, 0.14))
for a in mine:
    L = lab(a); c = smc(a)
    if not c: continue
    if L == "DS_Ground": c.set_material(0, grass); hook("grass")
    elif L == "DS_RockSkirt": c.set_material(0, stone); hook("stone")
    elif L.startswith("W3_Stream"): c.set_material(0, water); hook("water_plane")
    elif L.startswith("W4_Pond") or L.startswith("W8_Cistern"):
        for i, mt in enumerate(c.get_materials()):
            if mt and "water" in mt.get_name().lower(): c.set_material(i, water); hook("water_slot")
    n = asset_of(a)
    if n and "_DS_Tree_" in n:
        for i, mt in enumerate(c.get_materials()):
            if mt and "leaf" in mt.get_name().lower(): c.set_material(i, leaf); hook("leaf_slot")
# ---------- 3. gameplay hooks by asset name (DaedalusLink classes; skipped cleanly if not compiled)
have = set(lab(x) for x in eas.get_all_level_actors())
def spawn(cls, loc, label, tags):
    if label in have: return None
    x = eas.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0)); have.add(label)
    x.tags = [TAG] + tags; x.set_folder_path("DiskSaver/Gameplay"); x.set_actor_label(label); return x
DRINK = ("W1_Spring", "W2_Well", "W6_Bucket", "W6_Canteen")
RAW = ("W3_Stream", "W4_Pond", "W8_Cistern", "W7_Gutter", "W9_Trough")
PROD = {"ByteHen": ("Egg", 4.0), "MossGoat": ("GoatMilk", 8.0), "TidePig": ("Manure", 6.0), "CacheCow": ("Milk", 10.0), "DriftDuck": ("Egg", 5.0)}
k = 0
for a in mine:
    if late(): break
    k += 1
    L = lab(a); loc = a.get_actor_location(); tags = [str(t) for t in a.tags]; n = asset_of(a) or ""
    if (L.startswith(DRINK) or L.startswith(RAW)) and "DS_Water" not in tags:
        q = "Drinkable" if L.startswith(DRINK) else "RawWater"; a.tags = tags + ["DS_Water", q]; hook("water_tag_" + q)
        if hasattr(unreal, "DaedalusWaterSource") and not (L.startswith("W3_Stream_") and L != "W3_Stream_0"):
            ws = spawn(unreal.DaedalusWaterSource, loc, "DS_WaterSource_" + L, ["DS_WaterLogic"])
            if ws:
                try: ws.set_editor_property("quality", "clean" if q == "Drinkable" else "raw")
                except Exception as e: out["notes"].append("WaterSource prop: " + str(e)[:80])
                hook("WaterSource")
    if L.startswith("W5_FilterBarrel") and hasattr(unreal, "DaedalusWaterFilter"):
        if spawn(unreal.DaedalusWaterFilter, loc + unreal.Vector(0, -120, 0), "DS_Filter_" + L, ["DS_WaterTreat", "Filter"]): hook("WaterFilter")
    if ("_DS_Cauldron" in n or "_DS_Campfire" in n) and hasattr(unreal, "DaedalusKettle"):
        if spawn(unreal.DaedalusKettle, loc + unreal.Vector(0, 150, 0), "DS_BoilKettle_%d" % k, ["DS_WaterTreat", "Boil"]): hook("Kettle_boil")
    if ("_DS_HerbCompressor" in n or "_DS_DryingRack" in n) and hasattr(unreal, "DaedalusKettle"):
        if spawn(unreal.DaedalusKettle, loc + unreal.Vector(150, 0, 0), "DS_Brew_" + ("Compressor" if "Compressor" in n else "TeaRack_%d" % k), ["DS_Brew"]): hook("Kettle_brew")
    if "_DS_Herb_" in n and "_S3" in n and "DS_Herb" not in tags:
        sp = n.split("_DS_Herb_")[1].split("_")[0]
        a.tags = tags + ["DS_Herb", "Harvestable", sp]; hook("herb_tag")
        if hasattr(unreal, "DaedalusStarbloom"):
            b = spawn(unreal.DaedalusStarbloom, loc, "DS_Herb_%s_%d" % (sp, k), ["DS_Herb", "Harvestable", sp])
            if b:
                try:
                    b.set_editor_property("species", sp)
                    b.get_editor_property("body").set_static_mesh(smc(a).static_mesh)
                    a.set_actor_hidden_in_game(True)   # pickable Starbloom carries the same mesh; original kept, not deleted
                except Exception as e: out["notes"].append("Starbloom: " + str(e)[:80])
                hook("Starbloom")
    if n.startswith("Mob_DS_") and "DS_Livestock" not in tags:
        sp = n.split("Mob_DS_")[1].split("_")[0]
        a.tags = tags + ["DS_Livestock", sp, "Pen_West", "Feeds_W9_Trough"]; hook("livestock_tag")
        if hasattr(unreal, "DaedalusLivestock"):
            l = spawn(unreal.DaedalusLivestock, loc, "DS_Livestock_%s_%d" % (sp, k), ["DS_LivestockLogic"])
            if l:
                for kk, v in (("species", sp), ("product", PROD.get(sp, ("", 5.0))[0]), ("produce_every_min", PROD.get(sp, ("", 5.0))[1])):
                    try: l.set_editor_property(kk, v)
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
