# SPDX-License-Identifier: MIT
"""OddsReaper Island, editor turn script (safe to run again). Run inside the editor on a granted turn only.
1. imports the 524 OddsReaper glbs into /Game/OddsReaper/Art (skips assets that already exist)
2. creates/opens the sublevel /Game/OddsReaper/Maps/OddsReaperIsland under DaedalusWorld and makes it current
3. places layout.json, a storm Mood Volume over the island, and a hero camera
4. saves ONLY the sublevel. Prints PASS/FAIL.
Env: ODDSREAPER_GLB (glb folder), ODDSREAPER_LAYOUT (layout.json)."""
import json, os
import unreal

GLB = os.environ.get("ODDSREAPER_GLB", r"C:\Users\730ri\projects\bot-team\art\oddsreaper\glb")
LAYOUT = os.environ.get("ODDSREAPER_LAYOUT", r"C:\Users\730ri\projects\Daedalus2\data\islands\oddsreaper\layout.json")
ART, SUB, PERSIST = "/Game/OddsReaper/Art", "/Game/OddsReaper/Maps/OddsReaperIsland", "/Game/Daedalus/DaedalusWorld"
FOLDER = "OddsReaper"
eal = unreal.EditorAssetLibrary


def log(m): unreal.log("[oddsreaper-island] " + m)


def import_all():
    tasks = []
    for f in sorted(os.listdir(GLB)):
        if not f.endswith(".glb"): continue
        name = f[:-4]
        if eal.does_asset_exist(f"{ART}/{name}/{name}") or eal.does_asset_exist(f"{ART}/{name}"): continue
        t = unreal.AssetImportTask()
        for k, v in (("filename", os.path.join(GLB, f)), ("destination_path", f"{ART}/{name}"), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t)
    for i in range(0, len(tasks), 50):
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks[i:i + 50])
    log(f"imported {len(tasks)} new")


def mesh(name):
    for p in (f"{ART}/{name}/{name}", f"{ART}/{name}"):
        if eal.does_asset_exist(p):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    for p in eal.list_assets(f"{ART}/{name}", recursive=True):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh): return a
    return None


def open_sublevel():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(PERSIST)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not eal.does_asset_exist(SUB):
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, move_selected_actors_into_new_level=False)
    else:  # already made: make sure it's streamed into DaedalusWorld (harmless error if it already is)
        try: unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
        except Exception as e: log(f"add_level_to_world: {e}")
    les.set_current_level_by_name("OddsReaperIsland")
    return les


def run():
    import_all()
    les = open_sublevel()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    lay = json.load(open(LAYOUT))
    ox, oy, oz = lay["origin_cm"]
    for a in actors.get_all_level_actors():  # rerun: clear my own previous placements only
        if str(a.get_folder_path()).startswith(FOLDER): actors.destroy_actor(a)
    placed, missing = 0, set()
    for p in lay["placements"]:
        if p.get("skip"): continue
        m = mesh(p["asset"])
        if m is None: missing.add(p["asset"]); continue
        loc = unreal.Vector(ox + p["x"] * 100, oy + p["y"] * 100, oz + p["z"] * 100)
        a = actors.spawn_actor_from_object(m, loc, unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]))
        a.set_actor_scale3d(unreal.Vector(p["scale"], p["scale"], p["scale"]))
        a.set_folder_path(f"{FOLDER}/{p['zone']}"); a.set_actor_label(p["asset"]); placed += 1
    # signature mood: perpetual storm over the island via my Sky Director
    vol = actors.spawn_actor_from_class(unreal.DaedalusMoodVolume, unreal.Vector(ox, oy, oz + 3000))
    vol.set_actor_label("OddsReaper Storm Mood"); vol.set_folder_path(FOLDER)
    vol.set_actor_scale3d(unreal.Vector(1.4 * lay["scale"], 1.4 * lay["scale"], 1.5))
    vol.set_editor_property("mood", lay["mood"])
    for prop in ("set_weather", "b_set_weather"):  # UE python strips the b prefix; accept either
        try: vol.set_editor_property(prop, True); break
        except Exception: pass
    vol.set_editor_property("weather", getattr(unreal.DaedalusWeather, lay["weather"].upper()))
    import math
    c, t = lay["hero_cam_m"], lay["hero_target_m"]
    cl = unreal.Vector(ox + c[0] * 100, oy + c[1] * 100, oz + c[2] * 100)
    dx, dy, dz = (t[0] - c[0]), (t[1] - c[1]), (t[2] - c[2])
    rot = unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(dz, math.hypot(dx, dy))), yaw=math.degrees(math.atan2(dy, dx)))
    cam = actors.spawn_actor_from_class(unreal.CineCameraActor, cl, rot)
    cam.set_actor_label("OddsReaper Hero Cam"); cam.set_folder_path(FOLDER)
    les.save_current_level()
    unreal.EditorAssetLibrary.save_directory(ART, only_if_is_dirty=True, recursive=True)
    ok = placed >= 450 and not missing
    log(f"placed={placed} missing={sorted(missing)[:10]} {'PASS' if ok else 'FAIL'}")
    return {"ok": ok, "placed": placed, "missing": sorted(missing), "cam": [cl.x, cl.y, cl.z], "cam_rot": [rot.pitch, rot.yaw]}


if __name__ == "__main__":
    run()
