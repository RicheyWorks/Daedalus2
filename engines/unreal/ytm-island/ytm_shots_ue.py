r"""youtube-master visual check: ONE screenshot per editor tick (slate post-tick state machine). Moves only the
editor viewport camera (no actors, nothing saved). 8 views, 1280x720 -> Saved\Screenshots\WindowsEditor\YTM_check_*.png.
Per view: tick 0 move camera, ticks 1-5 settle (streaming/exposure), tick 6 request screenshot, tick 9 next view.
Returns immediately; the shots finish ~2-4 s later. Prints YTM_SHOTS done when finished."""
import unreal, math
O = unreal.Vector(0, -2600000, 0)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
V = lambda x, y, z: unreal.Vector(O.x + x, O.y + y, O.z + z)
def look(eye, tgt):
    d = tgt - eye
    return unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), yaw=math.degrees(math.atan2(d.y, d.x)))
SHOTS = [("overview", V(-9000, -9000, 7000), V(0, 0, 0)),
         ("spawn_shrine", V(400, -1800, 350), V(-900, 1000, 120)),
         ("spring_signs", V(0, -400, 300), V(1400, 0, 100)),
         ("garden", V(2200, -600, 500), V(4900, 200, 100)),
         ("farm", V(-2200, -600, 500), V(-4900, 0, 100)),
         ("kitchen", V(0, 1500, 400), V(300, 4000, 100)),
         ("ark_dock", V(0, -8500, 600), V(0, -11000, 100)),
         ("sign_readable", V(1100, -300, 180), V(1500, 400, 160))]  # in front of the spring sign's text face
state = {"i": 0, "t": 0, "h": None}
def tick(dt):
    i, t = state["i"], state["t"]
    if i >= len(SHOTS):
        unreal.unregister_slate_post_tick_callback(state["h"]); print("YTM_SHOTS done", len(SHOTS)); return
    name, eye, tgt = SHOTS[i]
    if t == 0: ues.set_level_viewport_camera_info(eye, look(eye, tgt))
    elif t == 6: unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, "YTM_check_%s.png" % name)
    state["t"] = t + 1
    if state["t"] >= 10: state["i"] += 1; state["t"] = 0
state["h"] = unreal.register_slate_post_tick_callback(tick)
print("YTM_SHOTS scheduled", len(SHOTS))
