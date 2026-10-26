import unreal, math
O = unreal.Vector(0, -2600000, 0); eye = O + unreal.Vector(400, -1800, 350); tgt = O + unreal.Vector(-900, 1000, 120); d = tgt - eye
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(eye, unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), yaw=math.degrees(math.atan2(d.y, d.x))))
unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, "YTM_check_spawn_shrine.png")
print("YTM_ONE requested")
