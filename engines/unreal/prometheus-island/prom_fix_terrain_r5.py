# Prometheus r5: terrain transform fix + ground snap. OBJ is Z-up meters, (x,y,z)=(lx,ly,h) matching heights.json / pi_place hz().
# Diagnosis: r2 auto-fit kept scale 100 regardless of import units; derive scale from mesh bounds, then search 24 rotations x mirror by traces.
import unreal, json, math
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary
if ue.get_game_world(): les.editor_request_end_play()
R={}; G="/Game/Prometheus"; PIMAP=G+"/Maps/PrometheusIsland"; SRC="C:/Users/730ri/projects/_wt-prom-island/data/islands/prometheus/"
if not les.set_current_level_by_name("PrometheusIsland"): raise RuntimeError("PrometheusIsland not loaded")
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
T=A["PI_Terrain"]; C=T.get_actor_location(); sm=T.static_mesh_component; mesh=sm.static_mesh
I=json.load(open(SRC+"island.json")); HM=json.load(open(SRC+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
def hz(lx,ly):
    j=(lx/S+0.5)*(N-1); i=(ly/S+0.5)*(N-1)
    if not (0<=i<N-1 and 0<=j<N-1): return None
    i0,j0=int(i),int(j); fi,fj=i-i0,j-j0
    h=HM[i0][j0]*(1-fi)*(1-fj)+HM[i0][j0+1]*(1-fi)*fj+HM[i0+1][j0]*fi*(1-fj)+HM[i0+1][j0+1]*fi*fj
    return None if h<=0.06 else h*P
bb=mesh.get_bounding_box(); ext=[bb.max.x-bb.min.x,bb.max.y-bb.min.y,bb.max.z-bb.min.z]
R["before"]=dict(rot=[T.get_actor_rotation().roll,T.get_actor_rotation().pitch,T.get_actor_rotation().yaw],scale=[T.get_actor_scale3d().x,T.get_actor_scale3d().y,T.get_actor_scale3d().z],local_extent=[round(e,2) for e in ext])
k=S/max(ext)  # uniform scale so the 480 m footprint is exact
R["scale"]=round(k,4)
bs=mesh.get_editor_property("body_setup")
if bs: bs.set_editor_property("collision_trace_flag",unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
samples=[(x,y) for x in range(-18000,18001,4500) for y in range(-18000,18001,4500) if hz(x,y) is not None]
def score():
    err=0.0; n=0
    for x,y in samples:
        r=sm.line_trace_component(C+unreal.Vector(x,y,30000),C+unreal.Vector(x,y,-30000),True,False,False)
        if isinstance(r,tuple) and r[0]: err+=abs((r[1].z-C.z)-hz(x,y)); n+=1
        else: err+=5000
    return err/max(1,len(samples)),n
best=None
for roll in (0,90,180,270):
    for pitch in (0,90,270):
        for yaw in (0,90,180,270):
            for sy in (1,-1):
                T.set_actor_rotation(unreal.Rotator(roll,pitch,yaw),False); T.set_actor_scale3d(unreal.Vector(k,k*sy,k))
                e,n=score()
                if best is None or e<best[0]: best=(e,n,roll,pitch,yaw,sy)
e,n,roll,pitch,yaw,sy=best
T.set_actor_rotation(unreal.Rotator(roll,pitch,yaw),False); T.set_actor_scale3d(unreal.Vector(k,k*sy,k))
R["after"]=dict(mean_err_cm=round(e),hits=n,of=len(samples),roll=roll,pitch=pitch,yaw=yaw,mirror_y=sy<0)
OK=e<300
if not OK:
    b0=R["before"]; T.set_actor_rotation(unreal.Rotator(*b0["rot"]),False); T.set_actor_scale3d(unreal.Vector(*b0["scale"]))
# ground snap: keep each item's designed offset above the heightmap, then trace the real surface
snapped=0
if OK:
    for lab,a in A.items():
        if lab=="PI_Terrain" or lab.startswith(("PI_HeroCam","PI_Light")): continue
        l=a.get_actor_location(); lx,ly=l.x-C.x,l.y-C.y; h=hz(lx,ly)
        if h is None: continue
        dz=(l.z-C.z)-h
        r=sm.line_trace_component(unreal.Vector(l.x,l.y,C.z+30000),unreal.Vector(l.x,l.y,C.z-30000),True,False,False)
        if isinstance(r,tuple) and r[0]:
            nz=r[1].z+dz
            if abs(nz-l.z)>1: a.set_actor_location(unreal.Vector(l.x,l.y,nz),False,False); snapped+=1
    EAL.save_asset(PIMAP,False); EAL.save_directory(G,only_if_is_dirty=True,recursive=True)
R["snapped"]=snapped; R["saved"]=OK
# re-capture (hidden SceneCapture, temp actor)
W=ue.get_editor_world(); OUT="C:/Users/730ri/projects/bot-team/art/prometheus_island/shots"
cam=C+unreal.Vector(-26000,-20000,16000); tgt=C+unreal.Vector(0,0,1500)
rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); scc=c.capture_component2d
scc.set_editor_property("texture_target",rt); scc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); scc.set_editor_property("fov_angle",55.0)
scc.capture_scene(); unreal.RenderingLibrary.export_render_target(W,rt,OUT,"PI_hero_ue_r5.png"); es.destroy_actor(c)
R["pie"]=bool(ue.get_game_world()); print("R5",json.dumps(R))
