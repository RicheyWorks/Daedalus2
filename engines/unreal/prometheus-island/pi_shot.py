# Hidden hero shot via SceneCapture2D (no viewport). Removes temp actor.
import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); W=ue.get_editor_world()
OUT="C:/Users/730ri/projects/bot-team/art/prometheus_island/shots"
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
C=A["PI_Terrain"].get_actor_location(); done=[]
def snap(n,cam,tgt,fov=60.0):
    rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
    sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",fov); sc.capture_scene()
    unreal.RenderingLibrary.export_render_target(W,rt,OUT,n+".png"); es.destroy_actor(c); done.append(n)
snap("PI_hero",C+unreal.Vector(-26000,-20000,16000),C+unreal.Vector(0,0,1500))
for k in ("PI_Jukebox","PI_Water_Cistern_0","PI_Label_Garden","PI_Water_SpringBasin"):
    if k in A: t=A[k].get_actor_location(); snap(k.replace("PI_","PI_shot_"),t+unreal.Vector(-2600,-1900,1300),t)
print("shots",done)
