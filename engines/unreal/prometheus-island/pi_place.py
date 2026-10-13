# Prometheus Island: own sublevel only. Imports 500 Blender items + terrain + beds, places island, saves. Editor only, no PIE. Re-run safe.
import unreal, os, json, math, random
R0="C:/Users/730ri/projects/bot-team/art/"; PI=R0+"prometheus_island/"; CO=R0+"coats8/"
G="/Game/Prometheus"; ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL=unreal.EditorAssetLibrary; at=unreal.AssetToolsHelpers.get_asset_tools(); mel=unreal.MaterialEditingLibrary
if ue.get_game_world(): raise RuntimeError("PIE running")
W=ue.get_editor_world(); out={}
STAGE=globals().get("STAGE","all")
# 0) own sublevel
MAP=G+"/Maps/PrometheusIsland"
lv=[l for l in unreal.EditorLevelUtils.get_levels(W) if "PrometheusIsland" in l.get_path_name()]
if not lv:
    if EAL.does_asset_exist(MAP): unreal.EditorLevelUtils.add_level_to_world(W,MAP,unreal.LevelStreamingAlwaysLoaded)
    else: unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,MAP,False)
    lv=[l for l in unreal.EditorLevelUtils.get_levels(W) if "PrometheusIsland" in l.get_path_name()]
ok_=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name("PrometheusIsland")
if not ok_: raise RuntimeError("could not make PrometheusIsland current")
out["sublevel"]=lv[0].get_path_name()
# 1) imports (skip existing)
man=[]
for f in sorted(os.listdir(PI)):
    if f.startswith("manifest_"): man+=json.load(open(PI+f))
def task(fn,dst,name):
    t=unreal.AssetImportTask(); t.filename=fn; t.destination_path=dst; t.destination_name=name; t.automated=True; t.replace_existing=False; t.save=True; return t
ts=[]
for m in man:
    if not EAL.does_asset_exist(G+"/Items/%s/%s"%(m["cat"],m["name"])): ts.append(task(PI+"fbx/"+m["name"]+".fbx",G+"/Items/"+m["cat"],m["name"]))
if not EAL.does_asset_exist(G+"/Terrain/SM_PrometheusIsland_Terrain"): ts.append(task(PI+"fbx/SM_PrometheusIsland_Terrain.obj",G+"/Terrain","SM_PrometheusIsland_Terrain"))
for w in ("SW_PI_Stream","SW_PI_Song"):
    if not EAL.does_asset_exist(G+"/Audio/"+w): ts.append(task(PI+w+".wav",G+"/Audio",w))
coats=sorted(f[:-4] for f in os.listdir(CO) if f.endswith(".png"))
for c in coats:
    if not EAL.does_asset_exist(G+"/Coats/"+c): ts.append(task(CO+c+".png",G+"/Coats",c))
for i in range(0,len(ts),50): at.import_asset_tasks(ts[i:i+50])
out["imported_now"]=len(ts)
have=[m for m in man if EAL.does_asset_exist(G+"/Items/%s/%s"%(m["cat"],m["name"]))]; out["items_in_ue"]=len(have)
if STAGE=="import":
    EAL.save_directory(G,only_if_is_dirty=True,recursive=True); print("PI",json.dumps(out)); raise SystemExit
# 2) materials: dark, soft palette per category + water + coats
def cmat(n,rgb,rough=0.85,metal=0.0,op=None):
    p=G+"/Mat/"+n
    if EAL.does_asset_exist(p): return unreal.load_asset(p)
    m=at.create_asset(n,G+"/Mat",unreal.Material,unreal.MaterialFactoryNew())
    c=mel.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-400,0); c.set_editor_property("constant",unreal.LinearColor(*rgb,1)); mel.connect_material_property(c,"",unreal.MaterialProperty.MP_BASE_COLOR)
    r=mel.create_material_expression(m,unreal.MaterialExpressionConstant,-400,200); r.set_editor_property("r",rough); mel.connect_material_property(r,"",unreal.MaterialProperty.MP_ROUGHNESS)
    if metal: k=mel.create_material_expression(m,unreal.MaterialExpressionConstant,-400,300); k.set_editor_property("r",metal); mel.connect_material_property(k,"",unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m); EAL.save_loaded_asset(m); return m
PAL={"herb":(0.10,0.22,0.08),"water":(0.03,0.09,0.14),"stock":(0.22,0.15,0.08),"crop":(0.25,0.22,0.08),"tone":(0.08,0.08,0.10),
     "rock":(0.06,0.06,0.065),"tree":(0.04,0.10,0.05),"fungus":(0.20,0.12,0.06),"music":(0.03,0.03,0.035)}
MAT={k:cmat("M_PI_"+k,v,0.3 if k=="music" else 0.85,0.6 if k=="music" else 0) for k,v in PAL.items()}
WATER=cmat("M_PI_Water",(0.01,0.05,0.09),0.05); GROUND=cmat("M_PI_Ground",(0.07,0.09,0.05),0.95)
HERBC=[cmat("M_PI_HerbPC%02d"%i,tuple(0.06+0.16*x for x in (0.5+0.5*math.cos(i*0.5236),0.6,0.5+0.5*math.sin(i*0.5236)))) for i in range(12)]
CM=[]
for c in coats:
    p=G+"/Coats/M_"+c[2:]
    if EAL.does_asset_exist(p): CM.append(unreal.load_asset(p)); continue
    m=at.create_asset("M_"+c[2:],G+"/Coats",unreal.Material,unreal.MaterialFactoryNew())
    tc=mel.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate,-700,0); tc.set_editor_property("u_tiling",2.0); tc.set_editor_property("v_tiling",2.0)
    tx=mel.create_material_expression(m,unreal.MaterialExpressionTextureSample,-400,0); tx.texture=unreal.load_asset(G+"/Coats/"+c)
    mel.connect_material_expressions(tc,"",tx,"UVs"); mel.connect_material_property(tx,"RGB",unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(m); EAL.save_loaded_asset(m); CM.append(m)
# 3) pick an empty spot in the sky for a 480 m island
def hit(x,y):
    h=unreal.SystemLibrary.line_trace_single(W,unreal.Vector(x,y,60000),unreal.Vector(x,y,-60000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
    return bool(h and h.to_tuple()[0])
old=[a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")]
C=None
if old:
    t=[a for a in old if a.get_actor_label()=="PI_Terrain"]
    if t: C=t[0].get_actor_location()
for a in old: es.destroy_actor(a)
C=unreal.Vector(2000000,2000000,0)  # ARK_ORIGIN from BOARD island grid (msg 17138)
C=unreal.Vector(2000000,2000000,0)  # ARK_ORIGIN from BOARD island grid (msg 17138)
if C is None:
    for rr in (160000,220000,280000):
        for k in range(12):
            x,y=rr*math.cos(k*0.5236),rr*math.sin(k*0.5236)
            if not any(hit(x+dx,y+dy) for dx in (-30000,0,30000) for dy in (-30000,0,30000)): C=unreal.Vector(x,y,2000); break
        if C: break
out["center"]=[round(C.x),round(C.y),round(C.z)]
I=json.load(open(PI+"island.json")); HM=json.load(open(PI+"heights.json")); N=I["N"]; S=I["size_m"]*100.0; P=I["peak_m"]*100.0
def hz(lx,ly):
    j=(lx/S+0.5)*(N-1); i=(ly/S+0.5)*(N-1)
    if not (0<=i<N-1 and 0<=j<N-1): return None
    i0,j0=int(i),int(j); fi,fj=i-i0,j-j0
    h=(HM[i0][j0]*(1-fi)*(1-fj)+HM[i0][j0+1]*(1-fi)*fj+HM[i0+1][j0]*fi*(1-fj)+HM[i0+1][j0+1]*fi*fj)
    return None if h<=0.06 else h*P
def L(lx,ly,dz=0): 
    z=hz(lx,ly); return None if z is None else C+unreal.Vector(lx,ly,z+dz)
def mesh(m): return unreal.load_asset(G+"/Items/%s/%s"%(m["cat"],m["name"]))
n_placed=0
def put(lab,sm,loc,yaw=0,mat=None,sc=1.0,tags=()):
    global n_placed
    if loc is None or sm is None: return None
    a=es.spawn_actor_from_class(unreal.StaticMeshActor,loc,unreal.Rotator(0,0,yaw)); a.set_actor_label(lab); a.set_actor_scale3d(unreal.Vector(sc,sc,sc))
    a.static_mesh_component.set_static_mesh(sm); a.tags=[unreal.Name("PI")]+[unreal.Name(t) for t in tags]
    if mat:
        for s in range(a.static_mesh_component.get_num_materials()): a.static_mesh_component.set_material(s,mat)
    n_placed+=1; return a
def snd(lab,w,loc,vol,rad,tags=()):
    if loc is None: return
    s=es.spawn_actor_from_class(unreal.AmbientSound,loc); s.set_actor_label(lab); s.tags=[unreal.Name("PI")]+[unreal.Name(t) for t in tags]
    ac=s.get_component_by_class(unreal.AudioComponent); sw=unreal.load_asset(G+"/Audio/"+w)
    if sw: sw.set_editor_property("looping",True); EAL.save_loaded_asset(sw)
    ac.set_sound(sw); ac.set_editor_property("volume_multiplier",vol); ac.set_editor_property("override_attenuation",True)
    st=ac.get_editor_property("attenuation_overrides"); st.set_editor_property("spatialize",True); st.set_editor_property("falloff_distance",rad)
    st.set_editor_property("attenuate_with_lpf",True); st.set_editor_property("lpf_frequency_at_max",2500.0); ac.set_editor_property("attenuation_overrides",st)
def label(lab,txt,loc,size=60):
    if loc is None: return
    t=es.spawn_actor_from_class(unreal.TextRenderActor,loc); t.set_actor_label(lab); c=t.text_render; c.set_text(txt); c.set_world_size(size)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER); c.set_text_render_color(unreal.Color(200,190,160,255)); t.tags=[unreal.Name("PI")]
# terrain
tm=unreal.load_asset(G+"/Terrain/SM_PrometheusIsland_Terrain")
if tm:
    bs=tm.get_editor_property("body_setup")
    if bs: bs.set_editor_property("collision_trace_flag",unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE); EAL.save_loaded_asset(tm)
    put("PI_Terrain",tm,C,0,GROUND,100.0)
by={}
for m in have: by.setdefault(m["cat"],[]).append(m)
rnd=random.Random(15)
# 4) WATER SYSTEM: spring basin (top) -> stream -> cistern -> pipes -> troughs ; rain catchers -> cistern ; solar still at shore
def path(t):
    i=N*(0.62-0.4*t); j=N*(0.40+0.32*t+0.06*math.sin(t*9))
    return ((j/(N-1)-0.5)*S,(i/(N-1)-0.5)*S)
W_=lambda k:[m for m in by.get("water",[]) if m["kind"]==k]
sx,sy=path(0); put("PI_Water_SpringBasin",mesh(W_("SpringBasin")[0]),L(sx,sy,-20),0,WATER,1.0,["water","spring"])
for k,m in enumerate(W_("SpringBasin")[1:]): put("PI_Water_SpringBasin_%d"%k,mesh(m),L(sx+300*(k+1),sy+200,-20),k*40,MAT["rock"],0.6)
segs=W_("StreamSeg"); prev=None
for k,m in enumerate(segs):
    t=(k+0.5)/len(segs); x,y=path(t); x2,y2=path(min(1,t+0.02)); yaw=math.degrees(math.atan2(y2-y,x2-x))
    put("PI_Water_Stream_%02d"%k,mesh(m),L(x,y,-15),yaw,WATER,1.6,["water","stream"])
    if k%8==0: snd("PI_Snd_Stream_%02d"%k,"SW_PI_Stream",L(x,y,80),0.45,2200.0,["water"])
cx_,cy_=path(0.55); cx_+=1800
for k,m in enumerate(W_("Cistern")): put("PI_Water_Cistern_%d"%k,mesh(m),L(cx_+k*420,cy_,0),0,MAT["rock"],1.0,["water","cistern"])
for k,m in enumerate(W_("Pipe")):
    put("PI_Water_Pipe_%02d"%k,mesh(m),L(cx_+300+k*300,cy_+700,30),0,MAT["music"],1.0,["water","pipe"])
penx,peny=cx_+5200,cy_+600
for k,m in enumerate(W_("Trough")): put("PI_Water_Trough_%02d"%k,mesh(m),L(penx+(k%6)*500-1250,peny+(k//6)*2600-1300,0),90*(k//6),WATER,1.0,["water","trough"])
for k,m in enumerate(W_("RainCatcher")):
    a=k*0.5236; put("PI_Water_RainCatcher_%02d"%k,mesh(m),L(cx_-2600+2200*math.cos(a),cy_+2200*math.sin(a),0),0,MAT["music"],1.0,["water","raincatch"])
ex,ey=path(1.0)
for k,m in enumerate(W_("StillPart")): put("PI_Water_Still_%02d"%k,mesh(m),L(ex+(k%5)*260-520,ey-900+(k//5)*240,0),0,WATER,1.0,["water","still"])
label("PI_Label_Water","SPRING -> STREAM -> CISTERN -> PIPES -> TROUGHS\nrain catch -> cistern   |   solar still at shore",L(cx_,cy_,600),90)
# 5) HEART: jukebox + record presser + song
hx,hy=-2500.0,1500.0; heart=L(hx,hy,0)
jb=[a for a in es.get_all_level_actors() if a.get_actor_label()=="DA_JukeboxCabinet"]
if jb: put("PI_Jukebox",jb[0].static_mesh_component.static_mesh,heart,180,None,1.2,["jukebox"])
mus=by.get("music",[])
for k,m in enumerate([m for m in mus if m["kind"]=="PressPlate"]): put("PI_RecordPresser_%d"%k,mesh(m),L(hx+600+k*260,hy-500,0),0,MAT["music"],1.0,["presser"])
for k,m in enumerate([m for m in mus if m["kind"]=="Vinyl"]): put("PI_Vinyl_%02d"%k,mesh(m),L(hx+600+k*60,hy-250,95),0,MAT["music"],1.0,["vinyl"])
for k,m in enumerate([m for m in mus if m["kind"]=="Speaker"]): a=k*1.047; put("PI_Speaker_%d"%k,mesh(m),L(hx+900*math.cos(a),hy+900*math.sin(a),0),math.degrees(a)+90,MAT["music"],1.0)
for k,m in enumerate([m for m in mus if m["kind"]=="Lantern"]): a=k*1.571+0.78; put("PI_Lantern_%d"%k,mesh(m),L(hx+1300*math.cos(a),hy+1300*math.sin(a),0),0,MAT["music"])
snd("PI_Snd_IslandSong","SW_PI_Song",L(hx,hy,250),0.5,3500.0,["song"])
label("PI_Label_Heart","PROMETHEUS ISLAND\njukebox + record presser",L(hx,hy,700),110)
# 6) HARMONIC HERB GARDEN: 12 beds on the circle of fifths
gx,gy=-2500.0,-4500.0; herbs=by.get("herb",[]); NAMES={}
for m in herbs: NAMES[m["pc"]]=m["name"].split("_")[2]
PCN=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
for pos in range(12):
    pc=(pos*7)%12; a=pos*0.5236; bx,by_=gx+2000*math.cos(a),gy+2000*math.sin(a)
    for q,m in enumerate([m for m in herbs if m["pc"]==pc]):
        put("PI_Herb_%s_%02d"%(m["name"][5:],q),mesh(m),L(bx+(q%3)*70-70,by_+(q//3)*70-70,0),rnd.uniform(0,360),HERBC[pc],1.6,["herb","pc%d"%pc])
    label("PI_Label_Herb_%d"%pc,"%s  %s"%(PCN[pc],NAMES.get(pc,"")),L(bx,by_,140),40)
label("PI_Label_Garden","HARMONIC HERB GARDEN (circle of fifths)\ntriad=heal  fifth=shield  triplet=speed  tritone=poison",L(gx,gy,500),70)
for k,m in enumerate(by.get("tone",[])):
    a=k*0.1047; put("PI_ToneStone_%02d"%k,mesh(m),L(gx+3200*math.cos(a),gy+3200*math.sin(a),0),math.degrees(a),MAT["tone"],1.3,["tone"])
# 7) LIVESTOCK + FARM
st=by.get("stock",[])
for k,m in enumerate([m for m in st if m["kind"]=="PenFence"]):
    side=k//5; i=k%5; dx,dy=[(i*500-1000,-1500),(1500,i*600-1200),(i*500-1000,1500),(-1500,i*600-1200)][side]
    put("PI_Pen_%02d"%k,mesh(m),L(penx+dx,peny+dy,0),0 if side%2==0 else 90,MAT["stock"])
for k,m in enumerate([m for m in st if m["kind"]!="PenFence"]):
    put("PI_Farm_%s"%m["name"][6:],mesh(m),L(penx+2600+(k%8)*450,peny-1600+(k//8)*700,0),rnd.uniform(0,360),MAT["stock"])
mobs=[x for x in EAL.list_assets("/Game/Daedalus/Art/Mob",True,False)]
want=["Goat","Sheep","Cow","Pig","Chicken","Horse_Pony","Boar","Hare"]; picks=[]
for w in want:
    c=[x for x in mobs if x.split(".")[0].split("/")[-1]=="Mob_"+w]
    if c: picks.append(c[0])
nm=0
for k in range(16):
    if not picks or not CM: break
    sm=unreal.load_asset(picks[k%len(picks)])
    if not isinstance(sm,unreal.StaticMesh): continue
    cm=CM[k%len(CM)]; put("PI_Stock_%s_%s_%02d"%(picks[k%len(picks)].split(".")[-1][4:],cm.get_name()[7:],k),sm,L(penx+rnd.uniform(-1100,1100),peny+rnd.uniform(-1100,1100),0),rnd.uniform(0,360),cm,1.0,["livestock"]); nm+=1
out["livestock"]=nm; out["livestock_kinds"]=[p.split(".")[-1] for p in picks]
for k,m in enumerate(by.get("crop",[])):
    put("PI_Crop_%s"%m["name"][5:],mesh(m),L(penx-4200+(k%12)*300,peny-2600+(k//12)*350,0),0,MAT["crop"],1.5,["crop"])
label("PI_Label_Farm","PENS + FODDER: livestock drink at troughs, eat clover/lucerne/barley",L(penx,peny,500),70)
# 8) dressing: rocks, spruce, shelf fungus
def scatter(cat,mat,rmin,rmax,sc):
    for k,m in enumerate(by.get(cat,[])):
        for _ in range(20):
            a=rnd.uniform(0,6.283); r=rnd.uniform(rmin,rmax); p=L(r*math.cos(a),r*math.sin(a),0)
            if p: put("PI_%s_%02d"%(cat,k),mesh(m),p,rnd.uniform(0,360),mat,sc); break
scatter("rock",MAT["rock"],8000,21000,1.5); scatter("tree",MAT["tree"],7000,19000,1.0); scatter("fungus",MAT["fungus"],7000,18000,1.0)
# 9) light the heart softly, hero camera
pl=es.spawn_actor_from_class(unreal.PointLight,L(hx,hy,600)); pl.set_actor_label("PI_Light_Heart"); pc_=pl.point_light_component
pc_.set_editor_property("intensity",8000.0); pc_.set_editor_property("light_color",unreal.Color(255,190,120,255)); pc_.set_editor_property("attenuation_radius",4000.0)
hero=C+unreal.Vector(-26000,-20000,16000); cam=es.spawn_actor_from_class(unreal.CameraActor,hero,unreal.MathLibrary.find_look_at_rotation(hero,C+unreal.Vector(0,0,1500))); cam.set_actor_label("PI_HeroCam")
out["placed_meshes"]=n_placed
EAL.save_directory(G,only_if_is_dirty=True,recursive=True)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
print("PI",json.dumps(out))
