"""capture/v1 Unreal runner (youtube-master). Run in your editor turn through the bridge:
    CAPTURE_JOB = r"...\\jobs\\ytm_island.json"; exec(open(r"...\\tools\\capture\\capture_ue.py").read())
or set env CAPTURE_JOB. Stills: one temp SceneCapture2D in the job's sublevel -> RGBA8 render target -> PNG,
synchronous (viewport high-res shots wrote no file in round 5; this is disk-saver's proven path, Daedalus2 4f45d840).
Fixed exposure (EV100 from the job) is set on the capture component, so no light/PPV actors are added.
The temp actor is destroyed afterwards; nothing is saved here (save your own sublevel after, per turn rules).
Clip (optional, only if free RAM >= clip.min_free_gb): MRQ PIE render of job.clip.sequence frames [start, start+frames).
Writes <out_dir>/<job>/manifest.json (capture/v1/manifest) for the registry's IN-GAME-DEMO link."""
import unreal, os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(globals().get("__file__", os.environ.get("CAPTURE_HERE", "."))))
sys.path.insert(0, HERE); import capture_job as cj
TMP = "CAPTURE_Temp"

def _commit():
    try: return subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception: return "unknown"

def _free_gb():
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"], capture_output=True, text=True).stdout
        return int(out.strip()) / 1048576
    except Exception: return 0.0

def stills(job):
    act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(): raise RuntimeError("PIE running: stop Play first")
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    out = os.path.join(job["out_dir"], job["name"]); os.makedirs(out, exist_ok=True)
    sl = unreal.GameplayStatics.get_streaming_level(w, job["sublevel"])
    if sl: unreal.EditorLevelUtils.make_level_current(sl)
    for a in act.get_all_level_actors():
        if a.actor_has_tag(TMP): act.destroy_actor(a)
    rt = unreal.RenderingLibrary.create_render_target2d(w, job["width"], job["height"], unreal.TextureRenderTargetFormat.RTF_RGBA8)
    pl = cj.plan(job); written, errs = [], []
    loc = lambda p: unreal.Vector(*p["eye"]); rot = lambda p: unreal.Rotator(roll=0, pitch=p["pitch"], yaw=p["yaw"])
    cap = act.spawn_actor_from_class(unreal.SceneCapture2D, loc(pl[0]), rot(pl[0])); cap.tags = [TMP]; cap.set_actor_label("CAPTURE_TEMP")
    try:
        cc = cap.capture_component2d
        cc.set_editor_property("texture_target", rt); cc.set_editor_property("fov_angle", job["fov"])
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        try:
            pps = cc.get_editor_property("post_process_settings")
            for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM), ("auto_exposure_min_brightness", job["ev100"]),
                         ("auto_exposure_max_brightness", job["ev100"])):
                pps.set_editor_property("override_" + k, True); pps.set_editor_property(k, v)
            cc.set_editor_property("post_process_settings", pps); cc.set_editor_property("post_process_blend_weight", 1.0)
        except Exception as e: errs.append("exposure: " + str(e)[:80])
        for p in pl:
            try:
                cap.set_actor_location_and_rotation(loc(p), rot(p), False, True); cc.capture_scene()
                unreal.RenderingLibrary.export_render_target(w, rt, out, p["file"]); written.append(p["file"])
            except Exception as e: errs.append("%s: %s" % (p["name"], str(e)[:80]))
        if job["basecolor"]:
            try:
                p = pl[0]; cap.set_actor_location_and_rotation(loc(p), rot(p), False, True)
                cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR); cc.capture_scene()
                f = p["file"].replace(".png", "_basecolor.png"); unreal.RenderingLibrary.export_render_target(w, rt, out, f); written.append(f)
            except Exception as e: errs.append("basecolor: " + str(e)[:80])
    finally:
        act.destroy_actor(cap)
    return out, written, errs

def clip(job):
    c = job.get("clip")
    if not c: return None
    free = _free_gb()
    if free < c["min_free_gb"]: return {"skipped": "RAM %.2f GB < %.1f" % (free, c["min_free_gb"])}
    eas = unreal.EditorAssetLibrary; path = "/Game/Capture/MRQ_Capture_Light"
    if not eas.does_directory_exist("/Game/Capture"): eas.make_directory("/Game/Capture")
    cfg = eas.load_asset(path) if eas.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "MRQ_Capture_Light", "/Game/Capture", unreal.MoviePipelinePrimaryConfig, unreal.MoviePipelinePrimaryConfigFactory())
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.output_resolution = unreal.IntPoint(1280, 720); o.use_custom_frame_rate = True; o.output_frame_rate = unreal.FrameRate(c["fps"], 1)
    o.use_custom_playback_range = True; o.custom_start_frame = c["start"]; o.custom_end_frame = c["start"] + c["frames"]
    clip_dir = os.path.join(job["out_dir"], job["name"], "clip")
    o.output_directory = unreal.DirectoryPath(clip_dir); o.file_name_format = "{frame_number}"; o.override_existing_output = True
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting); aa.spatial_sample_count = 1; aa.temporal_sample_count = 1
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase); cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    eas.save_loaded_asset(cfg)
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem); q = sub.get_queue()
    for jb in list(q.get_jobs()): q.delete_job(jb)
    jb = q.allocate_new_job(unreal.MoviePipelineExecutorJob); s = c["sequence"]
    jb.sequence = unreal.SoftObjectPath(s + "." + s.split("/")[-1])
    jb.map = unreal.SoftObjectPath("/Game/Daedalus/DaedalusWorld.DaedalusWorld"); jb.set_configuration(cfg)
    sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    return {"started": s, "frames": c["frames"], "dir": clip_dir, "free_gb": round(free, 2)}

def run(job_path):
    with open(job_path, encoding="utf-8-sig") as f: job = cj.load(f.read())
    out, written, errs = stills(job)
    c = clip(job) if os.environ.get("CAPTURE_CLIP", globals().get("CAPTURE_CLIP", "0")) == "1" else None
    m = cj.manifest(job, written, commit=_commit(), errors=errs, clip=c)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f: json.dump(m, f, indent=1)
    print("CAPTURE %s: %d files (%d views expected) complete=%s errors=%s clip=%s -> %s" % (job["name"], len(written), len(m["expected"]), m["complete"], errs, c, out))
    return m

_job = globals().get("CAPTURE_JOB") or os.environ.get("CAPTURE_JOB")
if _job: run(_job)
