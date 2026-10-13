# disk-saver capture A: temporary lights for OUR island only, then request the screenshot.
# Nothing is saved here; ds_capture_cleanup_ue.py removes the DS_TempCapture actors after the shot.
import unreal, os
SHOT = os.environ.get("DS_SHOT", r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\diskSaver_island_v5.png")
O = unreal.Vector(4000000, 4000000, 2000); TMP = "DS_TempCapture"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(): raise SystemExit("PIE running")
w = ues.get_editor_world()
sl = unreal.GameplayStatics.get_streaming_level(w, "Island_DiskSaver")
if sl: unreal.EditorLevelUtils.make_level_current(sl)
out = {"spawned": []}
def tmp(cls, loc, rot=unreal.Rotator(0, 0, 0), nm="X"):
    a = eas.spawn_actor_from_class(cls, loc, rot); a.tags = [TMP]; a.set_actor_label("DS_TEMP_" + nm); out["spawned"].append(a.get_actor_label()); return a
sun = tmp(unreal.DirectionalLight, O + unreal.Vector(0, 0, 3000), unreal.Rotator(0, -40, 35), "Sun")
c = sun.light_component
c.set_editor_property("intensity", 8.0); c.set_editor_property("light_color", unreal.Color(255, 244, 225, 255))
try: c.set_editor_property("atmosphere_sun_light", False)   # don't drive the world sky / time of day
except Exception: pass
fill = tmp(unreal.PointLight, O + unreal.Vector(0, 0, 6000), nm="Fill")
fc = fill.point_light_component
fc.set_editor_property("intensity", 5.0e5); fc.set_editor_property("attenuation_radius", 20000.0); fc.set_editor_property("cast_shadows", False)
ppv = tmp(unreal.PostProcessVolume, O, nm="PPV")
ppv.set_editor_property("unbound", False); ppv.set_actor_scale3d(unreal.Vector(200, 200, 100))   # bounded to our cell only
s = ppv.settings
for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM), ("auto_exposure_min_brightness", 9.0),
             ("auto_exposure_max_brightness", 9.0), ("auto_exposure_bias", 0.5)):   # fixed EV100 ~3 for a 10-lux sun
    try: s.set_editor_property("override_" + k, True); s.set_editor_property(k, v)
    except Exception as e: out.setdefault("notes", []).append(k + ": " + str(e)[:60])
ppv.set_editor_property("settings", s)
ues.set_level_viewport_camera_info(O + unreal.Vector(-3800, -3800, 2600), unreal.Rotator(0, -28, 45))
unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, SHOT)
out["shot"] = SHOT
# fallback (bridge viewport shots have timed out for other bots): SceneCapture2D -> render target -> PNG
try:
    rt = unreal.RenderingLibrary.create_render_target2d(w, 1600, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cap = tmp(unreal.SceneCapture2D, O + unreal.Vector(-3800, -3800, 2600), unreal.Rotator(0, -28, 45), "Capture")
    cc = cap.capture_component2d
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.capture_scene()
    d, f = os.path.split(SHOT)
    unreal.RenderingLibrary.export_render_target(w, rt, d, f.replace(".png", "_capture.png"))
    out["capture"] = os.path.join(d, f.replace(".png", "_capture.png"))
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)   # lighting-independent colours
    cc.capture_scene(); unreal.RenderingLibrary.export_render_target(w, rt, d, f.replace(".png", "_basecolor.png"))
    out["basecolor"] = os.path.join(d, f.replace(".png", "_basecolor.png"))
except Exception as e: out["capture_err"] = str(e)[:120]
result = out
