# SPDX-License-Identifier: MIT
"""Blender Boss Island: in-editor import + placement (safe to rerun). Run INSIDE the editor on a granted turn only; do not run otherwise.
1. imports Prop_Island_BlenderBoss_Base (terrain, underside, pier, water chain) and any Prop_BBIsle_* / catalog glb not yet in
   /Game/Daedalus/Art/<Kind>/<Name> from art\\glb (replace_existing, saved)
2. opens DaedalusWorld, creates/streams the sublevel /Game/BlenderBoss/Maps/BlenderBossIsland and makes it current
3. places data/islands/blenderboss/layout.json (1003+ placements) at ORIGIN, plus a hero camera
4. saves ONLY its own sublevel. Prints PASS/FAIL and returns a dict. Panels are closed after by bb_turn.ps1 (tidy.ps1).
Env: BB_GLB (glb folder), BB_LAYOUT (layout.json)."""
import json, math, os, time
import unreal

GLB = os.environ.get("BB_GLB", r"C:\Users\730ri\projects\bot-team\art\glb")
LAYOUT = os.environ.get("BB_LAYOUT", r"C:\Users\730ri\projects\Daedalus2\data\islands\blenderboss\layout.json")
ART = "/Game/Daedalus/Art"
SUB, PERSIST, SUBNAME = "/Game/BlenderBoss/Maps/BlenderBossIsland", "/Game/Daedalus/DaedalusWorld", "BlenderBossIsland"
FOLDER = "BlenderBoss"
IMPORT_BUDGET_S = float(os.environ.get("BB_IMPORT_S", "200"))
_MODEF = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Daedalus", "jobs", "bb_mode.txt")   # code runs inside the editor process,
_MODE = os.environ.get("BB_MODE") or (open(_MODEF).read().strip() if os.path.exists(_MODEF) else "")   # so the sender's env never reaches it
BASEONLY = _MODE == "base"   # re-import + re-place ONLY the island base (terrain colour fix)
MAKEUP = _MODE == "makeup" or BASEONLY   # keep existing placements; re-place base + place only assets with no actor yet
BASE_MIN_CM = 10000.0   # the island is 240 m across; a base mesh smaller than 100 m means the wrong asset was found
SHOT = os.environ.get("BB_SHOT", r"C:\Users\730ri\projects\bot-team\shots\blenderboss\ue_island.png")
eal = unreal.EditorAssetLibrary


def log(m): unreal.log("[blenderboss-island] " + m)


def kind_of(name): return name.split("_", 1)[0] if name.split("_", 1)[0] in ("Prop", "Item", "Tool", "Bld", "Mob", "Veh", "Wpn") else "Prop"


_MC = {}
def mesh(name):
    if name in _MC: return _MC[name]
    _MC[name] = _mesh(name); return _MC[name]


def _mesh(name, exact=False):
    base = f"{ART}/{kind_of(name)}/{name}"
    for p in (f"{base}/{name}/StaticMeshes/{name}", f"{base}/{name}", f"{base}/StaticMeshes/{name}"):
        if eal.does_asset_exist(p):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    if eal.does_directory_exist(base) and not exact:
        for p in eal.list_assets(base, recursive=True):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    return None


def import_missing(names, force=()):
    tasks = []
    for n in names:
        f = os.path.join(GLB, n + ".glb")
        if not os.path.exists(f) or (n not in force and mesh(n) is not None): continue
        t = unreal.AssetImportTask()
        for k, v in (("filename", f), ("destination_path", f"{ART}/{kind_of(n)}/{n}"), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t)
    t0, done = time.time(), 0
    for i in range(0, len(tasks), 20):                 # chunks; stop importing when the time box is used up
        if time.time() - t0 > IMPORT_BUDGET_S: break
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i+20]); done += len(tasks[i:i+20])
    for t in tasks[:done]: _MC.pop(os.path.splitext(os.path.basename(t.get_editor_property("filename")))[0], None)
    log(f"imported {done}/{len(tasks)} in {time.time()-t0:.0f}s")
    return done


def _streamed(world):
    try: return any(str(l.get_world_asset_package_name()) == SUB for l in world.get_streaming_levels())
    except Exception as e: log(f"streamed check: {e}"); return True   # unsure -> do NOT re-add (re-add can pop a modal)


def open_sublevel():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(PERSIST)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not eal.does_asset_exist(SUB):
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, move_selected_actors_into_new_level=False)
    elif not _streamed(world):
        # only add when not already streamed: re-adding an existing sublevel opened a modal "Add Level" dialog (22:2x make-up)
        try: unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
        except Exception as e: log(f"add_level_to_world: {e}")
    les.set_current_level_by_name(SUBNAME)
    return les


def spawn(actors, m, loc, yaw, s, folder, label):
    a = actors.spawn_actor_from_object(m, loc, unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.set_folder_path(folder); a.set_actor_label(label)
    return a


def run():
    les0 = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les0.is_in_play_in_editor(): les0.editor_request_end_play(); log("ended Play")
    except Exception as e: log(f"play check: {e}")
    lay = json.load(open(LAYOUT))
    ox, oy, oz = lay["origin_cm"]; base = lay["base_asset"]
    names = sorted({p["asset"] for p in lay["placements"]})
    imported = import_missing([base] + ([] if BASEONLY else names), force=(base,))   # base always re-imported (water chain lives there)
    les = open_sublevel()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    present = set()
    for a in actors.get_all_level_actors():   # rerun: clear only our own previous placements (make-up: only base + cam)
        fp = str(a.get_folder_path())
        if not fp.startswith(FOLDER): continue
        if MAKEUP and fp != f"{FOLDER}/base" and fp != FOLDER: present.add(a.get_actor_label()); continue
        actors.destroy_actor(a)
    bm = _mesh(base, exact=True)   # never fall back to a random part of the base folder
    base_cm = 0.0
    if bm:
        ext = bm.get_bounds().box_extent; base_cm = 2 * max(ext.x, ext.y)
        if base_cm < BASE_MIN_CM: log(f"base mesh only {base_cm:.0f} cm across: wrong asset, not placing"); bm = None
    if bm: spawn(actors, bm, unreal.Vector(ox, oy, oz), 0, 1.0, f"{FOLDER}/base", "BlenderBoss Island Base")
    placed, missing = 0, set()
    for p in ([] if BASEONLY else lay["placements"]):
        if MAKEUP and p["asset"] in present: continue
        m = mesh(p["asset"])
        if m is None: missing.add(p["asset"]); continue
        # Blender is right-handed Z-up metres; Unreal is left-handed cm: flip Y and yaw
        spawn(actors, m, unreal.Vector(ox + p["x"] * 100, oy - p["y"] * 100, oz + p["z"] * 100), -p["yaw"], p["scale"],
              f"{FOLDER}/{p['zone']}", p["asset"]); placed += 1
    c, t = lay["hero_cam_m"], lay["hero_target_m"]
    cl = unreal.Vector(ox + c[0] * 100, oy - c[1] * 100, oz + c[2] * 100)
    dx, dy, dz = t[0] - c[0], -(t[1] - c[1]), t[2] - c[2]
    rot = unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(dz, math.hypot(dx, dy))), yaw=math.degrees(math.atan2(dy, dx)))
    cam = actors.spawn_actor_from_class(unreal.CineCameraActor, cl, rot); cam.set_actor_label("BlenderBoss Hero Cam"); cam.set_folder_path(FOLDER)
    les.save_current_level()
    try: unreal.EditorLevelLibrary.save_all_dirty_levels()      # DaedalusWorld (streaming ref) + our sublevel
    except Exception as e: log(f"save_all_dirty_levels: {e}")
    shot = None
    try:
        os.makedirs(os.path.dirname(SHOT), exist_ok=True)
        unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, SHOT, camera=cam); shot = SHOT
    except Exception as e: log(f"screenshot: {e}")
    want = len(lay["placements"]); kept = sum(1 for p in lay["placements"] if p["asset"] in present); total = placed + kept
    ok = bool(bm) and (BASEONLY or total >= int(0.9 * want))
    log(f"base={'ok' if bm else 'MISSING'} placed={placed}/{want} imported={imported} missing={len(missing)} {'PASS' if ok else 'FAIL'}")
    return {"ok": ok, "base": bool(bm), "placed": total, "new": placed, "kept": kept, "base_cm": round(base_cm), "want": want, "imported": imported, "missing_n": len(missing), "missing": sorted(missing)[:20], "shot": shot}


RESULT = run()
print(json.dumps(RESULT))
