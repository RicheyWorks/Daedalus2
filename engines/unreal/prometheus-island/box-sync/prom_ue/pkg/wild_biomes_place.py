# Prometheus: Wild Biomes ambience + Turing-coat herds. Re-run safe (replaces DA_WB_* actors). Editor only, no PIE.
import unreal, os, json, math, random
A="C:/Users/730ri/projects/bot-team/art/"; CO=A+"coats8/"; AU=A+"audio/biomes/"
DST="/Game/DaedalusAudio"; CDST=DST+"/Coats"
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if ue.get_game_world(): raise RuntimeError("PIE running")
W=ue.get_editor_world(); at=unreal.AssetToolsHelpers.get_asset_tools(); mel=unreal.MaterialEditingLibrary; EAL=unreal.EditorAssetLibrary
BIOMES={"meadow":["meadow"],"bramble":["bramble","scrub"],"pine":["pine"],"oak":["oak"],"willow":["willow","riverbank","river"]}
HERDS={"meadow":["Mob_Hare","Mob_Rabbit","Mob_Deer_Red","Mob_Horse_Pony"],"bramble":["Mob_Fox","Mob_Badger","Mob_Boar_Wild"],
 "pine":["Mob_Lynx","Mob_Wolf","Mob_Owl"],"oak":["Mob_Deer","Mob_Stag_Star","Mob_Boar_Wild"],"willow":["Mob_Frog","Mob_Frog_Bull","Mob_Horse"]}
# 1) import audio + coats
ts=[]
for b in BIOMES:
    t=unreal.AssetImportTask(); t.filename=AU+"SW_Biome_%s.wav"%b; t.destination_path=DST; t.destination_name="SW_Biome_"+b; t.automated=True; t.replace_existing=True; t.save=True; ts.append(t)
coats=sorted(f[:-4] for f in os.listdir(CO) if f.endswith(".png"))
for c in coats:
    t=unreal.AssetImportTask(); t.filename=CO+c+".png"; t.destination_path=CDST; t.destination_name=c; t.automated=True; t.replace_existing=True; t.save=True; ts.append(t)
at.import_asset_tasks(ts)
mats=[]
for c in coats:
    mp=CDST+"/M_"+c[2:]
    if EAL.does_asset_exist(mp): m=unreal.load_asset(mp)
    else:
        m=at.create_asset("M_"+c[2:],CDST,unreal.Material,unreal.MaterialFactoryNew())
        tc=mel.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate,-700,0); tc.set_editor_property("u_tiling",2.0); tc.set_editor_property("v_tiling",2.0)
        ts_=mel.create_material_expression(m,unreal.MaterialExpressionTextureSample,-400,0); ts_.texture=unreal.load_asset(CDST+"/"+c)
        mel.connect_material_expressions(tc,"",ts_,"UVs"); mel.connect_material_property(ts_,"RGB",unreal.MaterialProperty.MP_BASE_COLOR)
        r=mel.create_material_expression(m,unreal.MaterialExpressionConstant,-400,200); r.set_editor_property("r",0.8); mel.connect_material_property(r,"",unreal.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(m); EAL.save_loaded_asset(m)
    mats.append(m)
# 2) find biome centers: layout json > tagged/labelled actors > fallback ring
def center(keys):
    p=A+"prometheus_ue/wild_biomes_layout.json"
    if os.path.exists(p):
        L=json.load(open(p))
        for k in keys:
            if k in L: return unreal.Vector(*L[k]),"layout"
    pts=[a.get_actor_location() for a in es.get_all_level_actors()
         if any(k in (a.get_actor_label()+" "+" ".join(str(t) for t in a.tags)).lower() for k in keys) and not a.get_actor_label().startswith("DA_")]
    if pts:
        s=unreal.Vector(0,0,0)
        for q in pts: s=s+q
        return s*(1.0/len(pts)),"actors(%d)"%len(pts)
    return None,"none"
jb=[a for a in es.get_all_level_actors() if a.get_actor_label()=="DA_JukeboxCabinet"]
base=jb[0].get_actor_location() if jb else ue.get_level_viewport_camera_info()[0]
def ground(v):
    h=unreal.SystemLibrary.line_trace_single(W,v+unreal.Vector(0,0,3000),v-unreal.Vector(0,0,20000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
    if h: 
        t=h.to_tuple(); return t[4] if t[0] else v
    return v
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("DA_WB_"): es.destroy_actor(a)
rnd=random.Random(20261012); out=[]; ci=0
for i,(b,keys) in enumerate(BIOMES.items()):
    c,src=center(keys)
    if c is None: ang=2*math.pi*i/5; c=base+unreal.Vector(2500+3500*math.cos(ang),3500*math.sin(ang),0); src="fallback"
    c=ground(c)
    s=es.spawn_actor_from_class(unreal.AmbientSound,c+unreal.Vector(0,0,200)); s.set_actor_label("DA_WB_Amb_"+b); s.tags=[unreal.Name("DA_Ambient"),unreal.Name("WB_"+b)]
    ac=s.get_component_by_class(unreal.AudioComponent); ac.set_sound(unreal.load_asset(DST+"/SW_Biome_"+b)); ac.set_editor_property("volume_multiplier",0.7)
    ac.set_editor_property("override_attenuation",True); st=ac.get_editor_property("attenuation_overrides")
    st.set_editor_property("spatialize",True); st.set_editor_property("attenuation_shape",unreal.AttenuationShape.SPHERE)
    st.set_editor_property("attenuation_shape_extents",unreal.Vector(2500,0,0)); st.set_editor_property("falloff_distance",2000.0)
    st.set_editor_property("non_spatialized_radius_start",2000.0); st.set_editor_property("non_spatialized_radius_end",2500.0)
    ac.set_editor_property("attenuation_overrides",st)
    n=0
    for mob in HERDS[b]:
        mesh=unreal.load_asset("/Game/Daedalus/Art/Mob/%s/%s"%(mob,mob)) or unreal.load_asset("/Game/Daedalus/Art/Mob/"+mob)
        if not isinstance(mesh,unreal.StaticMesh): out.append((b,mob,"mesh missing")); continue
        for k in range(2):
            ang=rnd.uniform(0,2*math.pi); r=rnd.uniform(300,1400); p=ground(c+unreal.Vector(r*math.cos(ang),r*math.sin(ang),0))
            a=es.spawn_actor_from_class(unreal.StaticMeshActor,p,unreal.Rotator(0,0,rnd.uniform(0,360)))
            m=mats[ci%len(mats)]; ci+=1
            a.set_actor_label("DA_WB_%s_%s_%s"%(b,mob[4:],m.get_name()[7:])); a.tags=[unreal.Name("DA_Coat"),unreal.Name("WB_"+b)]
            sm=a.static_mesh_component; sm.set_static_mesh(mesh)
            for sl in range(sm.get_num_materials()): sm.set_material(sl,m)
            n+=1
    out.append((b,src,[round(c.x),round(c.y),round(c.z)],n))
EAL.save_directory(DST,only_if_is_dirty=True,recursive=True)
unreal.EditorLevelLibrary.save_current_level()
print("WB",json.dumps(out))
