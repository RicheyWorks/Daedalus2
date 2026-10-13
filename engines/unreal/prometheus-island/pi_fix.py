import unreal, json, math, os
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary
if ue.get_game_world(): raise RuntimeError("PIE")
W=ue.get_editor_world(); les.set_current_level_by_name("PrometheusIsland")
PI="C:/Users/730ri/projects/bot-team/art/prometheus_island/"; G="/Game/Prometheus"
I=json.load(open(PI+"island.json")); HM=json.load(open(PI+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
C=A["PI_Terrain"].get_actor_location()
def hz(lx,ly):
    j=min(N-1,max(0,int(round((lx/S+0.5)*(N-1))))); i=min(N-1,max(0,int(round((ly/S+0.5)*(N-1))))); return max(HM[i][j],0.0)*P
def path(t):
    i=N*(0.62-0.4*t); j=N*(0.40+0.32*t+0.06*math.sin(t*9)); return ((j/(N-1)-0.5)*S,(i/(N-1)-0.5)*S)
man=[]
for f in sorted(os.listdir(PI)):
    if f.startswith("manifest_"): man+=json.load(open(PI+f))
WATER=unreal.load_asset(G+"/Mat/M_PI_Water"); out={"stream_added":0,"herb_added":0}
segs=[m for m in man if m["cat"]=="water" and m["kind"]=="StreamSeg"]
for k,m in enumerate(segs):
    lab="PI_Water_Stream_%02d"%k
    if lab in A: continue
    t=(k+0.5)/len(segs); x,y=path(t); x2,y2=path(min(1,t+0.02))
    a=es.spawn_actor_from_class(unreal.StaticMeshActor,C+unreal.Vector(x,y,hz(x,y)-15),unreal.Rotator(0,0,math.degrees(math.atan2(y2-y,x2-x))))
    a.set_actor_label(lab); a.set_actor_scale3d(unreal.Vector(1.6,1.6,1.6)); a.static_mesh_component.set_static_mesh(unreal.load_asset(G+"/Items/water/"+m["name"]))
    a.static_mesh_component.set_material(0,WATER); a.tags=[unreal.Name("PI"),unreal.Name("water"),unreal.Name("stream")]; out["stream_added"]+=1
    if k%8==0 and ("PI_Snd_Stream_%02d"%k) not in A:
        s=es.spawn_actor_from_class(unreal.AmbientSound,C+unreal.Vector(x,y,hz(x,y)+80)); s.set_actor_label("PI_Snd_Stream_%02d"%k)
        ac=s.get_component_by_class(unreal.AudioComponent); ac.set_sound(unreal.load_asset(G+"/Audio/SW_PI_Stream")); ac.set_editor_property("volume_multiplier",0.45)
gx,gy=-2500.0,-4500.0
for m in [m for m in man if m["cat"]=="herb"]:
    q=int(m["name"].split("_V")[-1]); st=["Sprout","Bloom","Seed"].index(m["stage"]); qi=st*3+q
    lab="PI_Herb_%s_%02d"%(m["name"][5:],qi)
    if any(l.startswith("PI_Herb_"+m["name"][5:]) for l in A): continue
    pos=[(p*7)%12 for p in range(12)].index(m["pc"]); a_=pos*0.5236; x=gx+2000*math.cos(a_)+(qi%3)*70-70; y=gy+2000*math.sin(a_)+(qi//3)*70-70
    a=es.spawn_actor_from_class(unreal.StaticMeshActor,C+unreal.Vector(x,y,hz(x,y)),unreal.Rotator(0,0,0)); a.set_actor_label(lab); a.set_actor_scale3d(unreal.Vector(1.6,1.6,1.6))
    a.static_mesh_component.set_static_mesh(unreal.load_asset(G+"/Items/herb/"+m["name"])); hm=unreal.load_asset(G+"/Mat/M_PI_HerbPC%02d"%m["pc"])
    if hm: a.static_mesh_component.set_material(0,hm)
    a.tags=[unreal.Name("PI"),unreal.Name("herb"),unreal.Name("pc%d"%m["pc"])]; out["herb_added"]+=1
EAL.save_asset("/Game/Prometheus/Maps/PrometheusIsland",False); EAL.save_asset("/Game/Daedalus/DaedalusWorld",False)
L=[a.get_actor_label() for a in es.get_all_level_actors()]
out["stream"]=sum(x.startswith("PI_Water_Stream_") for x in L); out["herbs"]=sum(x.startswith("PI_Herb_") for x in L); out["pie"]=bool(ue.get_game_world()); print("FIX",json.dumps(out))
