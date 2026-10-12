# SPDX-License-Identifier: MIT
"""Hephaestus Island, in-editor placement (safe to rerun). Run inside the editor on a granted turn only.
Built for a short (3 min) slot: almost every mesh is already shipped by the art queue to
/Game/Daedalus/Art/<Kind>/<Name>, so this only imports the few hero glbs still missing, then:
1. opens DaedalusWorld and creates/streams the sublevel /Game/Hephaestus/Maps/HephaestusIsland, makes it current
2. lays a 1024 m basalt ground disc at ARK_ORIGIN (6000000, 2000000, 0) cm
3. places data/islands/hephaestus/layout.json (hot-spring water as an engine plane), a forge-glow light, a hero camera
4. saves ONLY its own sublevel (and the few new assets). Prints PASS/FAIL and returns a dict.
Env: HEPH_GLB (glb folder), HEPH_LAYOUT (layout.json)."""
import json, math, os
import unreal

GLB = os.environ.get("HEPH_GLB", r"C:\Users\730ri\projects\bot-team\art\glb")
LAYOUT = os.environ.get("HEPH_LAYOUT", r"C:\Users\730ri\projects\Daedalus2\data\islands\hephaestus\layout.json")
ART = "/Game/Daedalus/Art"
SUB, PERSIST, SUBNAME = "/Game/Hephaestus/Maps/HephaestusIsland", "/Game/Daedalus/DaedalusWorld", "HephaestusIsland"
FOLDER = "Hephaestus"
KIND = {"Prop": "Prop", "Item": "Item", "Tool": "Tool", "Bld": "Bld", "Mob": "Mob", "Veh": "Veh", "Wpn": "Wpn"}
ENGINE = {"WaterPlane_HotSpring": ("/Engine/BasicShapes/Plane", 10.0)}  # asset -> (engine mesh, extra scale)
eal = unreal.EditorAssetLibrary


def log(m): unreal.log("[hephaestus-island] " + m)


def kind_of(name): return KIND.get(name.split("_", 1)[0], "Prop")


def mesh(name):
    if name in ENGINE: return unreal.load_asset(ENGINE[name][0])
    base = f"{ART}/{kind_of(name)}/{name}"
    for p in (f"{base}/{name}/StaticMeshes/{name}", f"{base}/{name}", f"{base}/StaticMeshes/{name}"):
        if eal.does_asset_exist(p):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    if eal.does_directory_exist(base):
        for p in eal.list_assets(base, recursive=True):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh): return a
    return None


def import_missing(names):
    tasks = []
    for n in names:
        f = os.path.join(GLB, n + ".glb")
        if n in ENGINE or mesh(n) is not None or not os.path.exists(f): continue
        t = unreal.AssetImportTask()
        for k, v in (("filename", f), ("destination_path", f"{ART}/{kind_of(n)}/{n}"), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t)
    if tasks: unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    log(f"imported {len(tasks)} new")
    return len(tasks)


def open_sublevel():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(PERSIST)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not eal.does_asset_exist(SUB):
        unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, move_selected_actors_into_new_level=False)
    else:
        try: unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingAlwaysLoaded)
        except Exception as e: log(f"add_level_to_world: {e}")
    les.set_current_level_by_name(SUBNAME)
    return les


def run():
    lay = json.load(open(LAYOUT))
    ox, oy, oz = lay["origin_cm"]
    imported = import_missing(sorted({p["asset"] for p in lay["placements"]}))
    les = open_sublevel()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actors.get_all_level_actors():  # rerun: clear only my own previous placements
        if str(a.get_folder_path()).startswith(FOLDER): actors.destroy_actor(a)
    # block-out ground: 1024 m disc, 20 m thick, top face at island z=0
    fx, fy = lay.get("footprint_m", [1024, 1024])
    g = actors.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cylinder"), unreal.Vector(ox, oy, oz - 1000))
    g.set_actor_scale3d(unreal.Vector(fx, fy, 20)); g.set_actor_label("Hephaestus Ground (blockout)"); g.set_folder_path(f"{FOLDER}/ground")
    placed, missing = 0, set()
    for p in lay["placements"]:
        if p.get("skip"): continue
        m = mesh(p["asset"])
        if m is None: missing.add(p["asset"]); continue
        s = p["scale"] * (ENGINE[p["asset"]][1] if p["asset"] in ENGINE else 1.0)
        a = actors.spawn_actor_from_object(m, unreal.Vector(ox + p["x"] * 100, oy + p["y"] * 100, oz + p["z"] * 100),
                                           unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]))
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_folder_path(f"{FOLDER}/{p['zone']}"); a.set_actor_label(p["asset"]); placed += 1
    # forge glow over the Great Forge so the caldera reads at dusk
    light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(ox, oy, oz + 600))
    light.set_actor_label("Hephaestus Forge Glow"); light.set_folder_path(FOLDER)
    try:
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_light_color(unreal.LinearColor(1.0, 0.42, 0.12, 1.0)); lc.set_intensity(50000.0); lc.set_attenuation_radius(6000.0)
    except Exception as e: log(f"light: {e}")
    # hero camera: high three-quarter view of caldera forge with drydock and springs behind
    c, t = lay.get("hero_cam_m", [140, -160, 90]), lay.get("hero_target_m", [0, 0, 5])
    cl = unreal.Vector(ox + c[0] * 100, oy + c[1] * 100, oz + c[2] * 100)
    dx, dy, dz = t[0] - c[0], t[1] - c[1], t[2] - c[2]
    rot = unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(dz, math.hypot(dx, dy))), yaw=math.degrees(math.atan2(dy, dx)))
    cam = actors.spawn_actor_from_class(unreal.CineCameraActor, cl, rot)
    cam.set_actor_label("Hephaestus Hero Cam"); cam.set_folder_path(FOLDER)
    les.save_current_level()
    want = sum(1 for p in lay["placements"] if not p.get("skip"))
    ok = placed >= int(0.9 * want)
    log(f"placed={placed}/{want} imported={imported} missing={sorted(missing)} {'PASS' if ok else 'FAIL'}")
    return {"ok": ok, "placed": placed, "want": want, "imported": imported, "missing": sorted(missing),
            "cam": [cl.x, cl.y, cl.z], "cam_rot": [rot.pitch, rot.yaw]}


if __name__ == "__main__":
    run()
