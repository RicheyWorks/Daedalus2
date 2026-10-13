# Island Audio core in-game demo: verify call/ambience AmbientSounds, label them, lit SceneCapture proof.
import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); W=ue.get_editor_world()
OUT="C:/Users/730ri/projects/_wt-prom-island/data/islands/prometheus"
acts=[a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")]
amb=[a for a in acts if isinstance(a,unreal.AmbientSound)]
rep=[]
for a in amb:
    c=a.get_component_by_class(unreal.AudioComponent); s=c.get_editor_property("sound")
    rep.append((a.get_actor_label(), s.get_name() if s else None, c.get_editor_property("auto_activate")))
bad=[r for r in rep if not r[1]]
print("ambient",len(rep),"unassigned",bad)
for a in [x for x in acts if x.get_actor_label().startswith("PI_AudioDemo_")]: es.destroy_actor(a)
calls=[a for a in amb if a.get_actor_label().startswith("PI_Call_")]
def label(txt,loc,n,sz=120.0,col=unreal.Color(255,214,150,255)):
    t=es.spawn_actor_from_class(unreal.TextRenderActor,loc,unreal.Rotator(0,0,36.4)); t.set_actor_label(n)
    tc=t.text_render; tc.set_editor_property("text",txt); tc.set_editor_property("world_size",sz); tc.set_editor_property("text_render_color",col); tc.set_editor_property("horizontal_alignment",unreal.HorizTextAligment.EHTA_CENTER); return t
for i,a in enumerate(calls):
    l=a.get_actor_label().split("_"); label("%s call: %s"%(l[2],"_".join(l[3:-1])),a.get_actor_location()+unreal.Vector(0,0,420),"PI_AudioDemo_Call_%02d"%i,70.0)
snd=[a for a in amb if a.get_actor_label().startswith("PI_Snd_")]
for i,a in enumerate(snd): label("biome ambience: "+a.get_actor_label()[7:],a.get_actor_location()+unreal.Vector(0,0,500),"PI_AudioDemo_Amb_%02d"%i,90.0,unreal.Color(150,210,255,255))
def ctr(L):
    v=unreal.Vector(0,0,0)
    for a in L: v+=a.get_actor_location()
    return v*(1.0/len(L))
done=[]
def snap(n,cam,tgt,fov=55.0):
    rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
    sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",fov); sc.capture_scene()
    unreal.RenderingLibrary.export_render_target(W,rt,OUT,n+".png"); es.destroy_actor(c); done.append(n)
cc=ctr(calls); snap("PI_audio_demo_calls",cc+unreal.Vector(-3800,-2800,2200),cc+unreal.Vector(0,0,300))
a0=calls[0].get_actor_location(); snap("PI_audio_demo_call_close",a0+unreal.Vector(-1200,-900,600),a0+unreal.Vector(0,0,250))
if snd: s0=snd[0].get_actor_location(); snap("PI_audio_demo_ambience",s0+unreal.Vector(-2400,-1800,1400),s0+unreal.Vector(0,0,300))
print("calls",len(calls),"amb",len(snd),"shots",done)


