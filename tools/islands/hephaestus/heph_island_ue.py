# SPDX-License-Identifier: MIT
"""Hephaestus Island, in-editor placement (safe to rerun). Run inside the editor on a granted turn only.
Built for a short (3 min) slot: almost every mesh is already shipped by the art queue to
/Game/Daedalus/Art/<Kind>/<Name>, so this only imports the few hero glbs still missing, then:
1. opens DaedalusWorld and creates/streams the sublevel /Game/Hephaestus/Maps/HephaestusIsland, makes it current
2. lays a 1024 m basalt ground disc at ARK_ORIGIN (6000000, 2000000, 0) cm
3. places data/islands/hephaestus/layout.json (hot-spring water as a tinted engine plane), a forge-glow light, a hero camera;
   multipart Mob_ livestock (head/body/legs as separate StaticMeshes) gets every part placed, not just the first
4. saves its sublevel, then DaedalusWorld (every dirty map package), and reports dirty maps left. Prints PASS/FAIL and returns a dict.
5. living check (Richey's rule: an island counts only with water, livestock and herbs in Unreal and the map saved):
   counts placed water / livestock / herb actors, fails the turn if any is zero, and posts the counts to the team link.
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
OUTBOX = r"C:\Users\730ri\projects\bot-team\link\outbox\hephaestus.jsonl"
SHOTS = r"C:\Users\730ri\projects\bot-team\shots\hephaestus"
HERO_PNG = "hero_r2.png"  # stable path for referee / round-2 living note
HOTSPRING_MI = "/Game/Hephaestus/Materials/MI_HotSpring"
BASALT_MI = "/Game/Hephaestus/Materials/MI_BasaltGround"
BASALT_COLOR = (0.045, 0.038, 0.035)  # dark basalt: the white 1024 m blockout disc washed out the round-5 hero


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


def mesh_parts(name):
    """Every StaticMesh of a multipart Mob_ (Prometheus found livestock ships as several meshes); else [mesh(name)]."""
    if kind_of(name) == "Mob" and name not in ENGINE:
        base = f"{ART}/Mob/{name}"
        if eal.does_directory_exist(base):
            parts = []
            for p in eal.list_assets(base, recursive=True):
                try: a = unreal.load_asset(p)
                except Exception: continue
                if isinstance(a, unreal.StaticMesh): parts.append(a)
            if parts: return parts
    m = mesh(name)
    return [m] if m is not None else []


def living_kind(name):
    if name.startswith("WaterPlane") or name.startswith("Prop_Water"): return "water"
    if name.startswith("Mob_"): return "livestock"
    if name.startswith("Item_Herb_"): return "herbs"
    return None


def hotspring_material():
    """Steam-blue instance of the engine basic-shape material so the springs read as water, not grey card."""
    try:
        if eal.does_asset_exist(HOTSPRING_MI): return unreal.load_asset(HOTSPRING_MI)
        parent = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_HotSpring", "/Game/Hephaestus/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(0.18, 0.62, 0.78, 1.0))
        eal.save_asset(HOTSPRING_MI)
        return mi
    except Exception as e:
        log(f"hotspring material: {e}"); return None


# Hero framing (round-5 lesson): the fixed hero_cam_m (140,-160,90) m sits ~230 m from the forge, so the lit round-5
# capture (luma 174) was a pale 1024 m disc with the caldera props as specks. Fit the camera to the hero zone instead:
# keep the layout's view direction, trim outliers, and back off just far enough that the core cluster fills the frame.
HERO_FRAME_ZONES = ("caldera_forge",)
HERO_FRAME_TRIM = 0.75   # radius quantile (drops a few far props so the core reads)
HERO_FRAME_MARGIN_M = 6.0
HERO_FRAME_FILL = 0.7    # cluster radius / half-frame at the target
HERO_FRAME_MIN_M = 30.0


def hero_pose_from_layout(lay, env=None):
    """Pure: (cam_m, target_m, fov, info). Fits the hero cam to HERO_FRAME_ZONES placements along the layout's view
    direction. HEPH_HERO_FIT=0, fewer than 3 points, or bad data -> the layout's fixed hero_cam_m / hero_target_m."""
    env = os.environ if env is None else env
    c0 = list(lay.get("hero_cam_m", [140, -160, 90])); t0 = list(lay.get("hero_target_m", [0, 0, 5]))
    fov = float(lay.get("hero_fov", 55))
    fixed = (c0, t0, fov, {"fit": False})
    if str(env.get("HEPH_HERO_FIT", "1")) == "0":
        fixed[3]["reason"] = "HEPH_HERO_FIT=0"; return fixed
    pts = [(float(p["x"]), float(p["y"]), float(p.get("z", 0))) for p in lay.get("placements") or []
           if p.get("zone") in HERO_FRAME_ZONES and not p.get("skip")]
    if len(pts) < 3:
        fixed[3]["reason"] = f"only {len(pts)} hero-zone points"; return fixed
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    ds = sorted(math.hypot(p[0] - cx, p[1] - cy) for p in pts)
    r = ds[min(len(ds) - 1, int(HERO_FRAME_TRIM * (len(ds) - 1) + 0.5))] + HERO_FRAME_MARGIN_M
    v = [c0[i] - t0[i] for i in range(3)]; n = math.sqrt(sum(x * x for x in v))
    if n < 1e-6:
        fixed[3]["reason"] = "hero_cam_m == hero_target_m"; return fixed
    d = max(HERO_FRAME_MIN_M, r / (HERO_FRAME_FILL * math.tan(math.radians(fov) / 2)))
    tz = t0[2]
    tgt = [round(cx, 2), round(cy, 2), tz]
    cam = [round(tgt[i] + v[i] / n * d, 2) for i in range(3)]
    return cam, tgt, fov, {"fit": True, "zones": list(HERO_FRAME_ZONES), "points": len(pts), "radius_m": round(r, 1),
                           "dist_m": round(d, 1), "fixed_dist_m": round(n, 1)}


def basalt_material():
    """Dark basalt instance of the engine basic-shape material for the blockout ground disc (was default white)."""
    try:
        if eal.does_asset_exist(BASALT_MI): return unreal.load_asset(BASALT_MI)
        parent = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_BasaltGround", "/Game/Hephaestus/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*BASALT_COLOR, 1.0))
        eal.save_asset(BASALT_MI)
        return mi
    except Exception as e:
        log(f"basalt material: {e}"); return None


def link_note(text):
    try:
        with open(OUTBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps({"from": "hephaestus", "to": "*", "type": "note", "body": {"text": text}}) + "\n")
    except OSError as e: log(f"link: {e}")


def resolve_glb(name):
    """Prefer blender-team _LOD1.glb when present (lower tris/RAM). HEPH_PREFER_LOD1=0 forces hi-res only."""
    prefer = os.environ.get("HEPH_PREFER_LOD1", "1") != "0"
    hi = os.path.join(GLB, name + ".glb")
    lod1 = os.path.join(GLB, name + "_LOD1.glb")
    if prefer and os.path.exists(lod1):
        return lod1, "lod1"
    if os.path.exists(hi):
        return hi, "hi"
    if os.path.exists(lod1):
        return lod1, "lod1"
    return None, None


def import_missing(names):
    # RAM guard (team rule 20:05, disk-saver pattern): heph_turn sets HEPH_NO_IMPORT=1 when free RAM < 1 GB, so the turn
    # only places meshes already in Content (preflight: all 72 present) and never risks an out-of-memory editor crash.
    if os.environ.get("HEPH_NO_IMPORT") == "1":
        log("RAM guard: imports skipped (HEPH_NO_IMPORT=1)"); return 0
    # HEPH_FORCE_LOD1=1 reimports even when the mesh already exists, swapping in blender-team LOD1 (landmarks).
    force_lod1 = os.environ.get("HEPH_FORCE_LOD1", "0") == "1"
    tasks, used = [], []
    for n in names:
        if n in ENGINE: continue
        already = mesh(n) is not None
        f, kind = resolve_glb(n)
        if f is None: continue
        if already and not (force_lod1 and kind == "lod1"): continue
        t = unreal.AssetImportTask()
        for k, v in (("filename", f), ("destination_path", f"{ART}/{kind_of(n)}/{n}"), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t); used.append(f"{n}:{kind}")
    if tasks: unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    log(f"imported {len(tasks)} new ({', '.join(used) if used else 'none'})")
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


def save_world():
    """Referee rule (6:22 PM): every turn ends with DaedalusWorld AND my sublevel saved. The sublevel is current, so
    save it, then save every dirty map package (DaedalusWorld carries the new streaming entry), and report what is left."""
    res = {"sublevel": False, "maps": False, "dirty_maps": None}
    try: res["sublevel"] = bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())
    except Exception as e: log(f"save sublevel: {e}")
    try: res["maps"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False))
    except Exception as e: log(f"save maps: {e}")
    try: res["dirty_maps"] = [str(k.get_name()) for k in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    except Exception as e: log(f"dirty map check: {e}")
    return res



# Exposure ladder for the SceneCapture hero (round-3 r2 PNG came out mean RGB ~0.1: a SceneCapture has no
# eye-adaptation history, so auto exposure starts dark at dusk). Each rung is (label, capture source, manual EV100
# or None for auto + bias). Manual exposure needs no adaptation; BASE_COLOR is the unlit last resort (never black).
EXPOSURE_LADDER = (
    ("auto+1", "SCS_FINAL_COLOR_LDR", None, 1.0),
    ("manual_ev8", "SCS_FINAL_COLOR_LDR", 8.0, 0.0),
    ("manual_ev5", "SCS_FINAL_COLOR_LDR", 5.0, 0.0),
    ("base_color", "SCS_BASE_COLOR", None, 0.0),
)
MIN_CAPTURE_LUM = 20.0  # same gate test_heph_nft_card uses for the card's primary hero


def mean_lum(colors):
    """Mean Rec.601 luma (0-255) of sampled pixels; each is an (r, g, b) 0-255 tuple or an object with .r/.g/.b."""
    tot, n = 0.0, 0
    for c in colors:
        r, g, b = (c.r, c.g, c.b) if hasattr(c, "r") else c[:3]
        tot += 0.299 * r + 0.587 * g + 0.114 * b; n += 1
    return tot / n if n else 0.0


def sample_grid(w, h, n=9):
    """n x n pixel coords inset 5% from the edges (cheap brightness probe, no PIL inside the editor)."""
    xs = [int(w * (0.05 + 0.9 * i / (n - 1))) for i in range(n)]
    ys = [int(h * (0.05 + 0.9 * j / (n - 1))) for j in range(n)]
    return [(x, y) for y in ys for x in xs]


# World-light probe (round 4, 23:45): every island's shot went near-black after the 22:59 editor restart because the
# persistent DaedalusWorld Sky Director was saved at sun 0 lux / skylight 0.017 (oddsreaper #26482). That is world-level,
# not island-level, so the hero now records the world light it saw and flags a lit re-shoot as owed instead of
# passing an unlit base_color frame off as the hero. Read-only: never spawns or edits a world sun (referee rule).
SUN_DARK_LUX = 1.0
SKY_DARK = 0.1


def world_light_verdict(suns, skies):
    """Pure check on DirectionalLight intensities (lux) and SkyLight intensities found in the loaded world."""
    sun = max((float(x) for x in (suns or []) if x is not None), default=None)
    sky = max((float(x) for x in (skies or []) if x is not None), default=None)
    dark = (sun is None or sun < SUN_DARK_LUX) and (sky is None or sky < SKY_DARK)
    return {"sun_lux": sun, "sky": sky, "suns": len(suns or []), "dark": dark}


def lit_owed(chosen, lum, gate=None):
    """A lit hero is still owed when the export fell back to unlit base color or never cleared the gate."""
    gate = MIN_CAPTURE_LUM if gate is None else gate
    return chosen is None or chosen == "base_color" or lum is None or lum < gate


# Sky gate (00:22 2026-10-13): oddsreaper #26626 found DaedalusWorld.umap on disk still holds the storm Sky Director
# (sun 0 lux, skylight 0.017); their 23:54 restore was in-memory only. So on my own granted turn, if the probe reads the
# world as dark, run oddsreaper's tools/islands/oddsreaper/restore_world_sky.py (young_meadow/Clear/9.4, explicit
# save_map + umap mtime check, NO new sun; its author cleared anyone holding a turn to run it), then re-probe before the
# exposure ladder. HEPH_RESTORE_SKY=0 disables it; at most one attempt per turn; result goes in hero_capture.json.
RESTORE_SKY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "oddsreaper", "restore_world_sky.py")


def sky_restore_plan(wl, env=None, attempted=False, script_exists=True):
    """Pure decision: should this turn run the shared sky restore before the hero capture? Returns (run, reason)."""
    env = os.environ if env is None else env
    if not wl or not wl.get("dark"): return False, "world lit"
    if env.get("HEPH_RESTORE_SKY", "1") == "0": return False, "disabled (HEPH_RESTORE_SKY=0)"
    if attempted: return False, "already attempted this turn"
    if not script_exists: return False, "restore_world_sky.py missing"
    return True, "world dark: run oddsreaper restore_world_sky (no new sun)"


def restore_sky():
    """Run oddsreaper's restore_world_sky.run() inside the editor. Returns its result dict (ok/saved/umap_written)."""
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("oddsreaper_restore_world_sky", RESTORE_SKY_SCRIPT)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.run()
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


# Temp island-only lights (disk-saver round-5 lit-capture pattern, 2026-10-13): when DaedalusWorld sky is
# storm-dark or SceneCapture has no eye-adaptation history, spawn a tagged HEPH_TEMP DirectionalLight
# (atmosphere_sun_light=False so it does NOT drive the world sky / time of day), a PointLight fill, and a
# bounded PostProcessVolume next to the island origin. Destroy every HEPH_TEMP_* before returning so the
# post-capture save_world cannot bake them into Content. HEPH_TEMP_LIGHTS=0 disables. Tuned values match
# disk-saver's good v5 shot (fill 5e5, EV100 9; commit 4f45d840).
TEMP_LIGHT_TAG = "HEPH_TempCapture"
TEMP_LIGHT_PREFIX = "HEPH_TEMP_"
TEMP_FILL_INTENSITY = 5.0e5
TEMP_SUN_INTENSITY = 8.0
TEMP_EV100 = 9.0


def temp_lights_plan(env=None):
    """Pure decision: should hero_capture spawn island-only temp lights? Returns (use, reason)."""
    env = os.environ if env is None else env
    if env.get("HEPH_TEMP_LIGHTS", "1") == "0":
        return False, "disabled (HEPH_TEMP_LIGHTS=0)"
    return True, "spawn island-only HEPH_TEMP sun/fill/PPV (no atmosphere sun; destroy before save)"


def is_temp_light_actor(label, tags=None):
    """True for actors this module spawned for a one-shot hero capture (label or tag)."""
    label = str(label or "")
    tags = [str(t) for t in (tags or [])]
    return label.startswith(TEMP_LIGHT_PREFIX) or TEMP_LIGHT_TAG in tags


def probe_world_light():

    suns, skies = [], []
    try:
        for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            for cls, comp, out in ((getattr(unreal, "DirectionalLight", None), "DirectionalLightComponent", suns),
                                   (getattr(unreal, "SkyLight", None), "SkyLightComponent", skies)):
                if cls is not None and isinstance(a, cls):
                    c = a.get_component_by_class(getattr(unreal, comp))
                    if c is not None: out.append(float(c.get_editor_property("intensity")))
    except Exception as e: log(f"world light probe: {e}")
    return world_light_verdict(suns, skies)


def hero_capture(cam_loc, target_loc, fov=55.0, origin=None):
    """SceneCapture2D hero shot with an exposure ladder and a brightness gate.
    Bypasses viewport_screenshot (bridge 9877 often times out). Tries each EXPOSURE_LADDER rung, probes a 9x9 pixel
    grid of the render target, and exports the first rung whose mean luma >= MIN_CAPTURE_LUM to SHOTS/hero_r2.png
    (the brightest rung if none pass). Writes the rung + luma to SHOTS/hero_capture.json. Returns path or None."""
    import time
    os.makedirs(SHOTS, exist_ok=True)
    out_path = os.path.join(SHOTS, HERO_PNG)
    try:
        ue_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = ue_sub.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        # clear prior capture / leftover temp-light actors from a partial run (never leave HEPH_TEMP in Content)
        for a in actors.get_all_level_actors():
            lab = str(a.get_actor_label())
            tags = [str(t) for t in (getattr(a, "tags", None) or [])]
            if lab.startswith("Hephaestus Hero Capture") or is_temp_light_actor(lab, tags):
                try: actors.destroy_actor(a)
                except Exception: pass
        rt = unreal.RenderingLibrary.create_render_target2d(
            world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        look = unreal.MathLibrary.find_look_at_rotation(cam_loc, target_loc)
        cap = actors.spawn_actor_from_class(unreal.SceneCapture2D, cam_loc, look)
        cap.set_actor_label("Hephaestus Hero Capture"); cap.set_folder_path(FOLDER)
        sc = cap.capture_component2d
        sc.set_editor_property("texture_target", rt)
        sc.set_editor_property("fov_angle", float(fov))
        grid = sample_grid(1920, 1080)
        wl = probe_world_light()
        log(f"world light: sun {wl['sun_lux']} lux, sky {wl['sky']}, dark={wl['dark']}")
        sky_fix = None
        go, why = sky_restore_plan(wl, script_exists=os.path.isfile(RESTORE_SKY_SCRIPT))
        if go:
            sky_fix = restore_sky()
            log(f"sky restore: {sky_fix}")
            wl = dict(probe_world_light(), before=wl)
            log(f"world light after restore: sun {wl['sun_lux']} lux, sky {wl['sky']}, dark={wl['dark']}")
        else:
            log(f"sky restore skipped: {why}")

        # Island-only temp lights (disk-saver pattern): lit hero even if world sky stays dark. Never saved.
        origin_v = origin if origin is not None else unreal.Vector(
            (cam_loc.x + target_loc.x) * 0.5, (cam_loc.y + target_loc.y) * 0.5, 0.0)
        use_tmp, tmp_why = temp_lights_plan()
        temp_info = {"used": False, "reason": tmp_why, "spawned": [], "removed": []}

        def _spawn_temp(cls, loc, rot, nm):
            a = actors.spawn_actor_from_class(cls, loc, rot)
            a.tags = [TEMP_LIGHT_TAG]
            a.set_actor_label(TEMP_LIGHT_PREFIX + nm)
            a.set_folder_path(f"{FOLDER}/TempCapture")
            temp_info["spawned"].append(a.get_actor_label())
            return a

        def _cleanup_temps():
            removed = []
            for a in list(actors.get_all_level_actors()):
                lab = str(a.get_actor_label())
                tags = [str(t) for t in (getattr(a, "tags", None) or [])]
                if is_temp_light_actor(lab, tags):
                    try:
                        actors.destroy_actor(a); removed.append(lab)
                    except Exception as e:
                        log(f"temp light cleanup {lab}: {e}")
            temp_info["removed"] = removed
            return removed

        if use_tmp:
            try:
                sun = _spawn_temp(unreal.DirectionalLight, origin_v + unreal.Vector(0, 0, 3000),
                                  unreal.Rotator(0, -40, 35), "Sun")
                sc_sun = sun.light_component
                sc_sun.set_editor_property("intensity", TEMP_SUN_INTENSITY)
                sc_sun.set_editor_property("light_color", unreal.Color(255, 244, 225, 255))
                try: sc_sun.set_editor_property("atmosphere_sun_light", False)
                except Exception: pass
                fill = _spawn_temp(unreal.PointLight, origin_v + unreal.Vector(0, 0, 6000),
                                   unreal.Rotator(0, 0, 0), "Fill")
                fc = fill.point_light_component
                fc.set_editor_property("intensity", TEMP_FILL_INTENSITY)
                fc.set_editor_property("attenuation_radius", 20000.0)
                fc.set_editor_property("cast_shadows", False)
                ppv = _spawn_temp(unreal.PostProcessVolume, origin_v, unreal.Rotator(0, 0, 0), "PPV")
                ppv.set_editor_property("unbound", False)
                ppv.set_actor_scale3d(unreal.Vector(200, 200, 100))
                s = ppv.settings
                for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
                             ("auto_exposure_min_brightness", TEMP_EV100),
                             ("auto_exposure_max_brightness", TEMP_EV100),
                             ("auto_exposure_bias", 0.5)):
                    try:
                        s.set_editor_property("override_" + k, True)
                        s.set_editor_property(k, v)
                    except Exception as e:
                        temp_info.setdefault("notes", []).append(f"{k}: {str(e)[:60]}")
                ppv.set_editor_property("settings", s)
                temp_info["used"] = True
                log(f"temp lights spawned: {temp_info['spawned']} (fill={TEMP_FILL_INTENSITY}, EV100={TEMP_EV100})")
            except Exception as e:
                temp_info["error"] = str(e)[:160]
                log(f"temp lights spawn failed: {e}")
                _cleanup_temps()
        else:
            log(f"temp lights skipped: {tmp_why}")

        def shoot(rung):
            label, src, ev100, bias = rung
            sc.set_editor_property("capture_source", getattr(unreal.SceneCaptureSource, src))
            pp = sc.get_editor_property("post_process_settings")
            sets = [("override_white_temp", True), ("white_temp", 5200.0),
                    ("override_bloom_intensity", True), ("bloom_intensity", 0.4),
                    ("override_auto_exposure_bias", True), ("auto_exposure_bias", float(bias)),
                    ("override_auto_exposure_method", ev100 is not None)]
            if ev100 is not None:
                sets += [("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                         ("override_auto_exposure_apply_physical_camera_exposure", True),
                         ("auto_exposure_apply_physical_camera_exposure", False),
                         ("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", float(ev100)),
                         ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", float(ev100))]
            for k, v in sets:
                try: pp.set_editor_property(k, v)
                except Exception: pass
            sc.set_editor_property("post_process_settings", pp)
            sc.set_editor_property("post_process_blend_weight", 1.0)
            sc.capture_scene()
            return mean_lum(unreal.RenderingLibrary.read_render_target_pixel(world, rt, x, y) for x, y in grid)

        tried, best = [], None
        for rung in EXPOSURE_LADDER:
            try: lum = shoot(rung)
            except Exception as e:
                log(f"hero capture rung {rung[0]}: {e}"); continue
            tried.append({"rung": rung[0], "lum": round(lum, 1)})
            log(f"hero capture rung {rung[0]}: mean luma {lum:.1f}")
            if best is None or lum > best[1]: best = (rung, lum)
            if lum >= MIN_CAPTURE_LUM: break
        if best and tried[-1]["rung"] != best[0][0]:  # none passed: re-shoot the brightest rung before export
            try: shoot(best[0])
            except Exception as e: log(f"hero capture re-shoot: {e}")
        unreal.RenderingLibrary.export_render_target(world, rt, SHOTS, HERO_PNG)
        try:
            with open(os.path.join(SHOTS, "hero_capture.json"), "w", encoding="utf-8") as f:
                chosen, blum = (best[0][0], best[1]) if best else (None, None)
                json.dump({"tried": tried, "chosen": chosen, "lum": round(blum, 1) if best else None,
                           "gate": MIN_CAPTURE_LUM, "world_light": wl, "sky_restore": sky_fix,
                           "temp_lights": temp_info, "lit_owed": lit_owed(chosen, blum)}, f, indent=1)
        except Exception as e: log(f"hero_capture.json: {e}")
        try: actors.destroy_actor(cap)
        except Exception: pass
        # ALWAYS strip HEPH_TEMP_* before any later save_world (run() re-saves after a successful shot).
        _cleanup_temps()
        log(f"temp lights removed: {temp_info.get('removed')}")
        # brief settle + existence check
        time.sleep(0.5)
        if best and lit_owed(best[0][0], best[1]):
            link_note(f"NEED island:hephaestus lit hero owed: export fell back to {best[0][0]} (lit rungs {tried[:-1]}); "
                      f"world light sun {wl['sun_lux']} lux / sky {wl['sky']}; temp_lights used={temp_info.get('used')} -> "
                      + ("world-level dark (DaedalusWorld sun/sky); temp island lights were used (not saved)"
                         if wl["dark"] else "world is lit, so re-aim hero cam / exposure next turn"))
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 1000 and best and best[1] >= MIN_CAPTURE_LUM:
            log(f"hero SceneCapture -> {out_path} ({os.path.getsize(out_path)} B, {best[0][0]} luma {best[1]:.1f})")
            return out_path
        log(f"hero SceneCapture too dark or missing ({tried}); trying HighResShot")
    except Exception as e:
        log(f"hero SceneCapture failed: {e}")
        try:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            for a in list(eas.get_all_level_actors()):
                lab = str(a.get_actor_label())
                tags = [str(t) for t in (getattr(a, "tags", None) or [])]
                if is_temp_light_actor(lab, tags) or lab.startswith("Hephaestus Hero Capture"):
                    try: eas.destroy_actor(a)
                    except Exception: pass
        except Exception as ce:
            log(f"temp light emergency cleanup: {ce}")
    # HighResShot fallback from the same hero pose (documented in ISLAND.md)
    try:
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
            cam_loc, unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(
                target_loc.z - cam_loc.z,
                math.hypot(target_loc.x - cam_loc.x, target_loc.y - cam_loc.y))),
                yaw=math.degrees(math.atan2(target_loc.y - cam_loc.y, target_loc.x - cam_loc.x))))
        time.sleep(2.0)  # longer settle than round-1
        unreal.SystemLibrary.execute_console_command(None, "HighResShot 1920x1080")
        unreal.SystemLibrary.execute_console_command(None, "Shot")
        time.sleep(4.0)
        saved = r"C:\Unreal\DaedalusRealm\Saved\Screenshots"
        cands = []
        for root, _, files in os.walk(saved):
            for fn in files:
                if fn.lower().endswith(".png"):
                    cands.append(os.path.join(root, fn))
        if cands:
            import shutil
            newest = max(cands, key=os.path.getmtime)
            shutil.copy2(newest, out_path)
            log(f"hero HighResShot fallback -> {out_path} from {newest}")
            return out_path
        log("hero HighResShot fallback: no png under Saved/Screenshots")
    except Exception as e:
        log(f"hero HighResShot fallback failed: {e}")
    return None


RESULT = r"C:\Users\730ri\projects\bot-team\shots\hephaestus\island_result.json"


def write_result(d):
    """Turn outcome on disk, so a bridge timeout on execute_python doesn't lose it (heph_turn / referee can read it)."""
    import datetime
    d = dict(d, ts=datetime.datetime.now().isoformat(timespec="seconds"))
    try:
        os.makedirs(os.path.dirname(RESULT), exist_ok=True)
        with open(RESULT, "w", encoding="utf-8") as f: json.dump(d, f, indent=1, default=str)
    except Exception as e: log(f"result file: {e}")


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
    basalt = basalt_material()
    if basalt is not None:
        try: g.static_mesh_component.set_material(0, basalt)
        except Exception as e: log(f"ground mat: {e}")
    placed, missing = 0, set()
    living = {"water": 0, "livestock": 0, "herbs": 0}
    spring_mi = hotspring_material()
    for p in lay["placements"]:
        if p.get("skip"): continue
        parts = mesh_parts(p["asset"])
        if not parts: missing.add(p["asset"]); continue
        s = p["scale"] * (ENGINE[p["asset"]][1] if p["asset"] in ENGINE else 1.0)
        for i, m in enumerate(parts):
            a = actors.spawn_actor_from_object(m, unreal.Vector(ox + p["x"] * 100, oy + p["y"] * 100, oz + p["z"] * 100),
                                               unreal.Rotator(roll=0, pitch=0, yaw=p["yaw"]))
            a.set_actor_scale3d(unreal.Vector(s, s, s))
            a.set_folder_path(f"{FOLDER}/{p['zone']}")
            a.set_actor_label(p["asset"] + (f"_part{i}" if len(parts) > 1 else "") + (f" ({p['animal']})" if p.get("animal") else ""))
            if p["asset"] in ENGINE and spring_mi is not None:
                try: a.static_mesh_component.set_material(0, spring_mi)
                except Exception as e: log(f"spring mat: {e}")
        placed += 1
        k = living_kind(p["asset"])
        if k: living[k] += 1
    # forge glow over the Great Forge so the caldera reads at dusk
    light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(ox, oy, oz + 600))
    light.set_actor_label("Hephaestus Forge Glow"); light.set_folder_path(FOLDER)
    try:
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_light_color(unreal.LinearColor(1.0, 0.42, 0.12, 1.0)); lc.set_intensity(50000.0); lc.set_attenuation_radius(6000.0)
    except Exception as e: log(f"light: {e}")
    # hero camera: high three-quarter view of caldera forge with drydock and springs behind
    c, t, hero_fov, hero_fit = hero_pose_from_layout(lay)
    log(f"hero pose: cam {c} m target {t} m fov {hero_fov} {hero_fit}")
    cl = unreal.Vector(ox + c[0] * 100, oy + c[1] * 100, oz + c[2] * 100)
    dx, dy, dz = t[0] - c[0], t[1] - c[1], t[2] - c[2]
    rot = unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(dz, math.hypot(dx, dy))), yaw=math.degrees(math.atan2(dy, dx)))
    cam = actors.spawn_actor_from_class(unreal.CineCameraActor, cl, rot)
    cam.set_actor_label("Hephaestus Hero Cam"); cam.set_folder_path(FOLDER)
    # Save BEFORE the hero capture: if the bridge times out mid-capture (blender-team's 20:31 make-up scored 0 that way),
    # the island is already saved to Content and the result is on disk for heph_turn to read.
    saved = save_world()
    want = sum(1 for p in lay["placements"] if not p.get("skip"))
    alive = all(living.values())
    ok = placed >= int(0.9 * want) and alive
    link_note(f"{'DONE' if alive else 'BLOCKED'} island:hephaestus living check in Unreal: water {living['water']}, "
              f"livestock {living['livestock']}, herbs {living['herbs']} placed; {placed}/{want} placements; "
              f"saved sublevel={saved['sublevel']} DaedalusWorld+maps={saved['maps']} dirty maps left={saved['dirty_maps']}")
    write_result({"stage": "saved", "ok": ok, "placed": placed, "want": want, "living": living, "saved": saved,
                  "hero_pose": {"cam_m": c, "target_m": t, "fov": hero_fov, **hero_fit}})
    # Warm SceneCapture hero PNG (bridge viewport_screenshot often times out on 9877).
    tl = unreal.Vector(ox + t[0] * 100, oy + t[1] * 100, oz + t[2] * 100)
    shot = hero_capture(cl, tl, fov=hero_fov, origin=unreal.Vector(ox, oy, oz))
    if shot:
        link_note(f"DONE island:hephaestus hero shot: {shot} (SceneCapture2D exposure ladder, see hero_capture.json)")
    else:
        link_note("NEED island:hephaestus: hero SceneCapture + HighResShot both failed; hero_r2.png still owed")
    if shot: saved = save_world()  # capture actor is transient; re-save only clears anything it dirtied
    log(f"placed={placed}/{want} imported={imported} missing={sorted(missing)} living={living} shot={shot} {'PASS' if ok else 'FAIL'}")
    try: cap = json.load(open(os.path.join(SHOTS, "hero_capture.json"), encoding="utf-8"))
    except Exception: cap = {}
    write_result({"stage": "done", "ok": ok, "placed": placed, "want": want, "living": living, "saved": saved, "shot": shot,
                  "hero_rung": cap.get("chosen"), "lit_owed": cap.get("lit_owed", True), "world_light": cap.get("world_light")})
    return {"ok": ok, "placed": placed, "want": want, "imported": imported, "missing": sorted(missing), "living": living,
            "saved": saved, "cam": [cl.x, cl.y, cl.z], "cam_rot": [rot.pitch, rot.yaw],
            "shot": shot, "hero_target": [tl.x, tl.y, tl.z]}


if __name__ == "__main__":
    run()
