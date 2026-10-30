# Prometheus one-shot Grok turn: Wild Biomes + livestock + shots. Saves ONLY Prometheus + WildBiomes packages. No PIE start/stop of others.
import unreal, json, math, random, os
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAL=unreal.EditorAssetLibrary
R={"steps":[]}
if ue.get_game_world(): raise RuntimeError("PIE running (someone is in Play); not touching it")
W=ue.get_editor_world()
MOB="/Game/Daedalus/Art/Mob/"
def parts(mob):
    base=MOB+"%s/%s/StaticMeshes/"%(mob,mob); ms=[]
    for p in EAL.list_assets(base,True,False):
        a=unreal.load_asset(p.split(".")[0])
        if isinstance(a,unreal.StaticMesh): ms.append(a)
    if not ms:
        for p in (MOB+"%s/%s"%(mob,mob),MOB+mob):
            a=unreal.load_asset(p)
            if isinstance(a,unreal.StaticMesh): ms=[a]; break
    ms.sort(key=lambda m:(0 if m.get_name() in (mob,mob+"_Body") else 1,m.get_name())); return ms
def spawn_mob(mob,loc,yaw,mat,label,tags):
    ms=parts(mob)
    if not ms: return 0
    root=None
    for m in ms:   # parts share one pivot (amf_pets_ue.py convention)
        a=es.spawn_actor_from_class(unreal.StaticMeshActor,loc,unreal.Rotator(0,0,yaw)); a.static_mesh_component.set_static_mesh(m)
        a.set_actor_label(label if root is None else label+"_"+m.get_name().split("_")[-1]); a.tags=[unreal.Name(t) for t in tags]
        if mat:
            for s in range(a.static_mesh_component.get_num_materials()): a.static_mesh_component.set_material(s,mat)
        if root is None: root=a
        else: a.attach_to_actor(root,"",unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    return len(ms)
def level_on(name,path):
    if not any(name in l.get_path_name() for l in unreal.EditorLevelUtils.get_levels(W)):
        if not EAL.does_asset_exist(path): return False
        unreal.EditorLevelUtils.add_level_to_world(W,path,unreal.LevelStreamingAlwaysLoaded)
    return bool(les.set_current_level_by_name(name))
# 1) Wild Biomes (Team Grok sublevel) with fixed multipart mob loading
WB="/Game/Pythagoras/Maps/WildBiomes_Pythagoras"
if level_on("WildBiomes_Pythagoras",WB):
    src=open("C:/Users/730ri/projects/bot-team/art/prometheus_ue/wild_biomes_place.py",encoding="utf-8-sig").read()
    src=src.replace('mesh=unreal.load_asset("/Game/Daedalus/Art/Mob/%s/%s"%(mob,mob)) or unreal.load_asset("/Game/Daedalus/Art/Mob/"+mob)','_ps=parts(mob); mesh=_ps[0] if _ps else None')
    src=src.replace("unreal.EditorLevelLibrary.save_current_level()","EAL.save_asset(WB_MAP)")
    src=src.replace("unreal.EditorLevelUtils.make_level_current(lv[0])","les.set_current_level_by_name(SUB)")
    g=dict(globals()); g["WB_MAP"]=WB
    try: exec(compile(src,"wild_biomes_place","exec"),g); R["steps"].append("wild_biomes ok")
    except Exception as e: R["steps"].append("wild_biomes ERR %s"%e)
else: R["steps"].append("wild_biomes SKIP: %s not on disk/loaded"%WB)
# 2) Prometheus livestock in the pens, Turing coats
PI="/Game/Prometheus/Maps/PrometheusIsland"
if not level_on("PrometheusIsland",PI): raise RuntimeError("PrometheusIsland sublevel missing")
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("PI_Stock_"): es.destroy_actor(a)
pens=[a.get_actor_location() for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_Pen_")]
cm=[unreal.load_asset(p.split(".")[0]) for p in EAL.list_assets("/Game/Prometheus/Coats",False,False) if p.split(".")[-1].startswith("M_Coat_")]
cm=[m for m in cm if m]
nm=0; nact=0
if pens:
    c=unreal.Vector(sum(p.x for p in pens)/len(pens),sum(p.y for p in pens)/len(pens),min(p.z for p in pens)); rnd=random.Random(15)
    herd=["Mob_Cow","Mob_Sheep","Mob_Goat","Mob_Pig","Mob_Donkey","Mob_Chicken"]*3
    for k,mob in enumerate(herd):
        x,y=c.x+rnd.uniform(-1100,1100),c.y+rnd.uniform(-1100,1100)
        h=unreal.SystemLibrary.line_trace_single(W,unreal.Vector(x,y,c.z+3000),unreal.Vector(x,y,c.z-3000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
        t=h.to_tuple() if h else None; z=t[4].z if (t and t[0]) else c.z
        m=cm[k%len(cm)] if cm else None
        n=spawn_mob(mob,unreal.Vector(x,y,z),rnd.uniform(0,360),m,"PI_Stock_%s_%s_%02d"%(mob[4:],m.get_name()[7:] if m else "plain",k),["PI","livestock"])
        if n: nm+=1; nact+=n
R["livestock"]=nm; R["livestock_actors"]=nact
EAL.save_asset(PI); EAL.save_directory("/Game/Prometheus",only_if_is_dirty=True,recursive=True)
# 3) shots by scene capture (Prometheus hero + details + Wild Biomes)
OUT="C:/Users/730ri/projects/bot-team/art/prometheus_island/shots"; shots=[]
def snap(n,cam,tgt,fov=60.0):
    rt=unreal.RenderingLibrary.create_render_target2d(W,1600,900,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c=es.spawn_actor_from_class(unreal.SceneCapture2D,cam,unreal.MathLibrary.find_look_at_rotation(cam,tgt)); sc=c.capture_component2d
    sc.set_editor_property("texture_target",rt); sc.set_editor_property("capture_source",unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR); sc.set_editor_property("fov_angle",fov)
    sc.capture_scene(); unreal.RenderingLibrary.export_render_target(W,rt,OUT,n+".png"); es.destroy_actor(c); shots.append(n)
L={a.get_actor_label():a for a in es.get_all_level_actors() if a.get_actor_label().startswith(("PI_","DA_WB_Amb_"))}
if "PI_Terrain" in L:
    C=L["PI_Terrain"].get_actor_location(); snap("PI_hero",C+unreal.Vector(-26000,-20000,16000),C+unreal.Vector(0,0,1500))
for k in ("PI_Jukebox","PI_Water_Cistern_0","PI_Label_Garden","PI_Water_SpringBasin"):
    if k in L: t=L[k].get_actor_location(); snap(k.replace("PI_","PI_shot_"),t+unreal.Vector(-2600,-1900,1300),t)
st=[a for k,a in L.items() if k.startswith("PI_Stock_")]
if st: t=st[0].get_actor_location(); snap("PI_shot_livestock",t+unreal.Vector(-1500,-1100,700),t)
for k,a in L.items():
    if k.startswith("DA_WB_Amb_"): snap("wb_"+k[10:],a.get_actor_location(),unreal.Vector(-1800,-1200,900))
R["shots"]=shots
# 4) tidy: close asset editors we may have opened; leave Play untouched (was not running)
try: unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_asset_editors()
except Exception as e: R["tidy"]=str(e)
R["pie"]=bool(ue.get_game_world())
print("PT",json.dumps(R))
