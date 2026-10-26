# Prometheus r3: in-editor HighResShot of the hero framing (editor viewport camera), no saves.
import unreal, json
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
T=[a for a in es.get_all_level_actors() if a.get_actor_label()=="PI_Terrain"][0]; C=T.get_actor_location()
cam=C+unreal.Vector(-26000,-20000,16000); rot=unreal.MathLibrary.find_look_at_rotation(cam,C+unreal.Vector(0,0,1500))
ue.set_level_viewport_camera_info(cam,rot)
unreal.SystemLibrary.execute_console_command(ue.get_editor_world(),"HighResShot 1920x1080 filename=PI_hero_hrs")
print("HRS", json.dumps({"cam":[cam.x,cam.y,cam.z],"dir":unreal.Paths.screen_shot_dir()}))
