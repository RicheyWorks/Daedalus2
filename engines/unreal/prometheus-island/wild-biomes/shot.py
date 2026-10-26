import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
jb=[a for a in es.get_all_level_actors() if a.get_actor_label()=="DA_JukeboxCabinet"][0].get_actor_location()
cam=jb+unreal.Vector(-1600,-900,900)
rot=unreal.MathLibrary.find_look_at_rotation(cam,jb+unreal.Vector(400,0,0))
ue.set_level_viewport_camera_info(cam,rot)
unreal.SystemLibrary.execute_console_command(ue.get_editor_world(),"HighResShot 1920x1080 filename=C:/Users/730ri/projects/bot-team/art/prometheus_ue/shot_jukebox_yard.png")
print("shot requested", cam)
