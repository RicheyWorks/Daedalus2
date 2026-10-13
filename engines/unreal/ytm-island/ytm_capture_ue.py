r"""youtube-master island views via SceneCapture2D -> render target -> PNG (disk-saver's path, Daedalus2 4f45d840),
because viewport high-res screenshots never wrote a file in round 5 (log 'YTM_SHOTS done 8', no 'screenshot saved').
Synchronous: capture_scene() renders immediately, so all 8 views work in one call. One temp capture actor (tag
YTM_TempCapture) is spawned in YTM_Island and destroyed at the end; no lights added (world sun restored, #26770).
Output: bot-team\art\NOTES\youtube-master\shots\YTM_<view>.png (+ YTM_overview_basecolor.png, lighting-independent)."""
import unreal, math, os
OUT = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master\shots"; TMP = "YTM_TempCapture"
O = unreal.Vector(0, -2600000, 0); W_, H_ = 1600, 900
act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(): raise SystemExit("PIE running")
w = ues.get_editor_world(); os.makedirs(OUT, exist_ok=True)
V = lambda x, y, z: unreal.Vector(O.x + x, O.y + y, O.z + z)
def look(eye, tgt):
    d = tgt - eye
    return unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), yaw=math.degrees(math.atan2(d.y, d.x)))
VIEWS = [("overview", V(-9000, -9000, 7000), V(0, 0, 0)),
         ("spawn_shrine", V(400, -1800, 350), V(-900, 1000, 120)),
         ("spring_signs", V(0, -400, 300), V(1400, 0, 100)),
         ("garden", V(2200, -600, 500), V(4900, 200, 100)),
         ("farm", V(-2200, -600, 500), V(-4900, 0, 100)),
         ("kitchen", V(0, 1500, 400), V(300, 4000, 100)),
         ("ark_dock", V(0, -8500, 600), V(0, -11000, 100)),
         ("sign_readable", V(1100, -300, 180), V(1500, 400, 160))]
sl = unreal.GameplayStatics.get_streaming_level(w, "YTM_Island")
if sl: unreal.EditorLevelUtils.make_level_current(sl)
for a in act.get_all_level_actors():
    if a.actor_has_tag(TMP): act.destroy_actor(a)
rt = unreal.RenderingLibrary.create_render_target2d(w, W_, H_, unreal.TextureRenderTargetFormat.RTF_RGBA8)
cap = act.spawn_actor_from_class(unreal.SceneCapture2D, VIEWS[0][1], look(VIEWS[0][1], VIEWS[0][2]))
cap.tags = [TMP]; cap.set_actor_label("YTM_TEMP_Capture")
cc = cap.capture_component2d
cc.set_editor_property("texture_target", rt)
cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
cc.set_editor_property("fov_angle", 70.0)
done, errs = [], []
for name, eye, tgt in VIEWS:
    try:
        cap.set_actor_location_and_rotation(eye, look(eye, tgt), False, True)
        cc.capture_scene(); unreal.RenderingLibrary.export_render_target(w, rt, OUT, "YTM_%s.png" % name); done.append(name)
    except Exception as e: errs.append("%s: %s" % (name, str(e)[:80]))
try:  # lighting-independent check of the overview
    cap.set_actor_location_and_rotation(VIEWS[0][1], look(VIEWS[0][1], VIEWS[0][2]), False, True)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    cc.capture_scene(); unreal.RenderingLibrary.export_render_target(w, rt, OUT, "YTM_overview_basecolor.png"); done.append("overview_basecolor")
except Exception as e: errs.append("basecolor: " + str(e)[:80])
act.destroy_actor(cap)
print("YTM_CAPTURE wrote %d -> %s %s errors=%s" % (len(done), OUT, done, errs))
