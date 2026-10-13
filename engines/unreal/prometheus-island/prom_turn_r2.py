# Prometheus round-2 turn: terrain flip fix, genome livestock calls, warm hero re-shot, optional Wild Biomes. Saves ONLY own packages.
import unreal, json, math, os, re, ctypes
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary; at=unreal.AssetToolsHelpers.get_asset_tools()
R={}
def free_gb():
    class M(ctypes.Structure): _fields_=[("l",ctypes.c_ulong),("ml",ctypes.c_ulong),("tp",ctypes.c_ulonglong),("ap",ctypes.c_ulonglong),("tf",ctypes.c_ulonglong),("af",ctypes.c_ulonglong),("tv",ctypes.c_ulonglong),("av",ctypes.c_ulonglong),("x",ctypes.c_ulonglong)]
    m=M(); m.l=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return m.ap/2**30
if ue.get_game_world(): les.editor_request_end_play(); R["pie_stopped_at_start"]=True
W=ue.get_editor_world(); G="/Game/Prometheus"; PIMAP=G+"/Maps/PrometheusIsland"
SRC="C:/Users/730ri/projects/bot-team/art/prometheus_island/"
if not les.set_current_level_by_name("PrometheusIsland"): raise RuntimeError("PrometheusIsland not loaded")
A={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")}
T=A["PI_Terrain"]; C=T.get_actor_location(); sm=T.static_mesh_component
I=json.load(open(SRC+"island.json")); HM=json.load(open(SRC+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
def hz(lx,ly):
    j=min(N-1,max(0,int(round((lx/S+0.5)*(N-1))))); i=min(N-1,max(0,int(round((ly/S+0.5)*(N-1)))))
    h=HM[i][j]; return h*P if h>0.05 else None
# 1) terrain: try orientations, keep the one whose top surface matches the heightmap
bs=sm.static_mesh.get_editor_property("body_setup")
if bs: bs.set_editor_property("collision_trace_flag",unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
samples=[(x,y) for x in (-12000,-6000,0,6000,12000) for y in (-12000,-6000,0,6000,12000) if hz(x,y) is not None]
def score():
    err=0.0; n=0
    for x,y in samples:
        st=C+unreal.Vector(x,y,20000); en=C+unreal.Vector(x,y,-20000)
        r=sm.line_trace_component(st,en,True,False,False)
        hit=r[0] if isinstance(r,tuple) else r
        if isinstance(r,tuple) and r[0]:
            z=r[1].z-C.z; err+=abs(z-hz(x,y)); n+=1
        else: err+=5000
    return err/max(1,len(samples)),n
cands=[]
for rot in [(0,0,0),(90,0,0),(-90,0,0),(180,0,0),(0,90,0),(0,-90,0)]:
    for sy in (1,-1):
        for yaw in (0,90,180,270):
            cands.append((rot,sy,yaw))
best=None
for (roll,pitch,_),sy,yaw in cands:
    T.set_actor_rotation(unreal.Rotator(roll,pitch,yaw),False); T.set_actor_scale3d(unreal.Vector(100,100*sy,100))
    e,n=score()
    if best is None or e<best[0]: best=(e,n,roll,pitch,yaw,sy)
e,n,roll,pitch,yaw,sy=best
T.set_actor_rotation(unreal.Rotator(roll,pitch,yaw),False); T.set_actor_scale3d(unreal.Vector(100,100*sy,100))
R["terrain"]=dict(mean_err_cm=round(e),hits=n,of=len(samples),roll=roll,pitch=pitch,yaw=yaw,mirror_y=sy<0)
# 3) warm local lights (island only, no global sun)
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("PI_Light_Warm_"): es.destroy_actor(a)
for k,(x,y) in enumerate([(0,0),(-9000,-6000),(9000,-6000),(-9000,7000),(9000,7000)]):
    l=es.spawn_actor_from_class(unreal.PointLight,C+unreal.Vector(x,y,9000)); l.set_actor_label("PI_Light_Warm_%d"%k); pc=l.point_light_component
    pc.set_editor_property("intensity",400000.0); pc.set_editor_property("light_color",unreal.Color(255,196,140,255)); pc.set_editor_property("attenuation_radius",22000.0); pc.set_editor_property("cast_shadows",False)
EAL.save_asset(PIMAP,False); EAL.save_directory(G,only_if_is_dirty=True,recursive=True)
# 4) optional Wild Biomes (only with WB_TARGET set, agreed with pythagoras)
WBT=globals().get("WB_TARGET","")
if WBT and free_gb()>=1.0:
    nm=WBT.split("/")[-1]
    if EAL.does_asset_exist(WBT) and les.set_current_level_by_name(nm):
        src=open("C:/Users/730ri/projects/bot-team/art/prometheus_ue/wild_biomes_place.py",encoding="utf-8-sig").read()
        src=src.replace('SUB="WildBiomes_Pythagoras"','SUB="%s"'%nm).replace("unreal.EditorLevelUtils.make_level_current(lv[0])","les.set_current_level_by_name(SUB)")
        src=src.replace("unreal.EditorLevelLibrary.save_current_level()","EAL.save_asset(WBT,False)")
        exec(compile(open(SRC+"mobparts.py").read(),"mobparts","exec"),globals())
        src=src.replace('mesh=unreal.load_asset("/Game/Daedalus/Art/Mob/%s/%s"%(mob,mob)) or unreal.load_asset("/Game/Daedalus/Art/Mob/"+mob)','_ps=parts(mob); mesh=_ps[0] if _ps else None')
        try: exec(compile(src,"wb","exec"),dict(globals())); R["wild_biomes"]="ok -> "+nm
        except Exception as ex: R["wild_biomes"]="ERR %s"%ex
        les.set_current_level_by_name("PrometheusIsland")
    else: R["wild_biomes"]="skip: %s missing"%WBT
# 5) shots: warm post-process on the capture only
OUT=SRC+"shots"; shots=[]
def snap(n,cam,tgt,fov=55.0):
    rt=unreal.RenderingLibrary.create_render_target2d(W,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
    sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",fov)
    pp=sc.get_editor_property("post_process_settings")
    for k,v in (("override_auto_exposure_bias",True),("auto_exposure_bias",1.0),("override_white_temp",True),("white_temp",5200.0),("override_bloom_intensity",True),("bloom_intensity",0.4)):
        try: pp.set_editor_property(k,v)
        except Exception: pass
    sc.set_editor_property("post_process_settings",pp); sc.set_editor_property("post_process_blend_weight",1.0)
    sc.capture_scene(); unreal.RenderingLibrary.export_render_target(W,rt,OUT,n+".png"); es.destroy_actor(c); shots.append(n)
snap("PI_hero_v2",C+unreal.Vector(-30000,-22000,14000),C+unreal.Vector(0,0,1500))
for k in ("PI_Jukebox","PI_Water_Cistern_0","PI_Label_Garden","PI_Water_SpringBasin"):
    if k in A: t=A[k].get_actor_location(); snap(k.replace("PI_","PI_v2_"),t+unreal.Vector(-2600,-1900,1300),t)
stk=[a for l,a in A.items() if re.match(r"PI_Stock_.+_\d\d$",l)]
if stk: t=stk[0].get_actor_location(); snap("PI_v2_livestock",t+unreal.Vector(-1600,-1200,700),t)
for l,a in [(l,a) for l,a in {x.get_actor_label():x for x in es.get_all_level_actors()}.items() if l.startswith("DA_WB_Amb_")]:
    t=a.get_actor_location(); snap("wb_"+l[10:],t+unreal.Vector(-1800,-1200,900),t)
R["shots"]=shots
# 2) genome calls LAST, only with >=1 GB free (imports are the crash risk)
R["ram_before_calls_gb"]=round(free_gb(),2)
if R["ram_before_calls_gb"]>=1.0:
    ts=[]
    for f in sorted(os.listdir(SRC+"calls")):
        if f.endswith(".wav") and not EAL.does_asset_exist(G+"/Audio/Calls/"+f[:-4]):
            t=unreal.AssetImportTask(); t.filename=SRC+"calls/"+f; t.destination_path=G+"/Audio/Calls"; t.destination_name=f[:-4]; t.automated=True; t.save=True; ts.append(t)
    if ts: at.import_asset_tasks(ts)
    for a in es.get_all_level_actors():
        if a.get_actor_label().startswith("PI_Call_"): es.destroy_actor(a)
    nc=0
    for lab,a in list(A.items()):
        m=re.match(r"PI_Stock_([A-Za-z]+)_(.+)_(\d\d)$",lab)
        if not m: continue
        sw=unreal.load_asset(G+"/Audio/Calls/SW_Call_PI_"+m.group(2))
        if not sw: continue
        sw.set_editor_property("looping",True); EAL.save_loaded_asset(sw)
        s=es.spawn_actor_from_class(unreal.AmbientSound,a.get_actor_location()+unreal.Vector(0,0,120)); s.set_actor_label("PI_Call_"+lab[9:]); s.tags=[unreal.Name("PI"),unreal.Name("livestock_call")]
        ac=s.get_component_by_class(unreal.AudioComponent); ac.set_sound(sw); ac.set_editor_property("volume_multiplier",0.3); ac.set_editor_property("override_attenuation",True)
        st=ac.get_editor_property("attenuation_overrides"); st.set_editor_property("spatialize",True); st.set_editor_property("falloff_distance",1200.0)
        st.set_editor_property("attenuate_with_lpf",True); st.set_editor_property("lpf_frequency_at_max",1500.0); ac.set_editor_property("attenuation_overrides",st)
        s.attach_to_actor(a,"",unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False); nc+=1
    R["calls"]=nc
    EAL.save_asset(PIMAP,False); EAL.save_directory(G,only_if_is_dirty=True,recursive=True)
else: R["calls"]="SKIPPED: RAM %.2f GB < 1 GB"%R["ram_before_calls_gb"]
try: unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_asset_editors()
except Exception: pass
R["pie"]=bool(ue.get_game_world()); print("R2",json.dumps(R))
