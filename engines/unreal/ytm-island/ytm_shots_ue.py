r"""youtube-master visual check (next editor turn): moves the EDITOR VIEWPORT camera (no actors spawned, nothing dirtied,
nothing saved) to 8 island views and takes 1280x720 high-res screenshots into Saved/Screenshots/YTM_check.
Run: ue_send.py ytm_shots_ue.py 240. Afterwards copy Saved\Screenshots\WindowsEditor\YTM_check_* to the Grok box."""
import unreal, math
O = unreal.Vector(0, -2600000, 0)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
def look(eye, tgt):
    d = tgt - eye; yaw = math.degrees(math.atan2(d.y, d.x)); pit = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    return unreal.Rotator(roll=0, pitch=pit, yaw=yaw)
V = lambda x, y, z: unreal.Vector(O.x + x, O.y + y, O.z + z)
SHOTS = [("overview", V(-9000, -9000, 7000), V(0, 0, 0)),
         ("spawn_shrine", V(400, -1800, 350), V(-900, 1000, 120)),
         ("spring_signs", V(0, -400, 300), V(1400, 0, 100)),
         ("garden", V(2200, -600, 500), V(4900, 200, 100)),
         ("farm", V(-2200, -600, 500), V(-4900, 0, 100)),
         ("kitchen", V(0, 1500, 400), V(300, 4000, 100)),
         ("ark_dock", V(0, -8500, 600), V(0, -11000, 100)),
         ("sign_readable", V(1500, 150, 170), V(1500, 400, 160))]
before = len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
for name, eye, tgt in SHOTS:
    ues.set_level_viewport_camera_info(eye, look(eye, tgt))
    unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, "YTM_check_%s.png" % name)
after = len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
print("YTM_SHOTS queued %d, dirty maps before/after %d/%d" % (len(SHOTS), before, after))
