# Hidden screenshot: SceneCapture2D -> render target -> PNG (no viewport needed). Removes its temp actor.
import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); W=ue.get_editor_world()
OUT="C:/Users/730ri/projects/bot-team/art/prometheus_ue/shots"
L={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("DA_")}
def snap(name,target,off):
    cam=target+off; rot=unreal.MathLibrary.find_look_at_rotation(cam,target)
    rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,rot); sc=c.capture_component2d
    sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    sc.set_editor_property("fov_angle",70.0); sc.capture_scene()
    unreal.RenderingLibrary.export_render_target(W,rt,OUT,name+".png"); es.destroy_actor(c); return name
done=[]
if "DA_JukeboxCabinet" in L:
    j=L["DA_JukeboxCabinet"].get_actor_location()
    done.append(snap("jukebox_yard",j+unreal.Vector(450,0,0),unreal.Vector(-1700,-1300,800)))
for k,a in L.items():
    if k.startswith("DA_WB_Amb_"): done.append(snap("wb_"+k[10:],a.get_actor_location(),unreal.Vector(-1800,-1200,900)))
print("shots",done)
