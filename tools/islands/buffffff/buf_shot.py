import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); W=ue.get_editor_world()
C=unreal.Vector(290000,148500,0); cam=C+unreal.Vector(-14000,-11000,7500); tgt=C+unreal.Vector(0,0,300)
rt=unreal.RenderingLibrary.create_render_target2d(W,1280,720,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",60.0); sc.capture_scene()
unreal.RenderingLibrary.export_render_target(W,rt,"C:/Users/730ri/projects/bot-team/art/buffffff/hero","Buffffff_Island_UE_day.png"); es.destroy_actor(c)
print("shot ok")
