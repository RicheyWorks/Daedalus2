# art-master-flex r2 turn: verify+save restored AMF rock/crate materials, import queue rows, place bowls/hay in Island_AMF.
import unreal, json, os
OUT=r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_turn2.json"
G=r"C:\Users\730ri\projects\bot-team\art\glb"
eal=unreal.EditorAssetLibrary; eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o={"err":[]}
try:
    if les.is_in_play_in_editor(): les.editor_request_end_play()
except Exception as e: o["err"].append("pie:"+str(e))
# 1 materials
mats=[]
for p in eal.list_assets("/Game/AMF",True,False):
    n=p.split("/")[-1].split(".")[0]
    if ("Rock" in p or "Crate" in p):
        d=eal.find_asset_data(p)
        if str(d.asset_class_path.asset_name) in ("Material","MaterialInstanceConstant"): mats.append(p)
dirty=[str(x.get_name()) for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
o["mat_total"]=len(mats); o["dirty_amf"]=[d for d in dirty if d.startswith("/Game/AMF")]
ok=0; bad=[]
for p in mats:
    a=unreal.load_asset(p)
    if a is None: bad.append(p); continue
    try:
        if eal.save_loaded_asset(a,False): ok+=1
        else: bad.append(p)
    except Exception as e: bad.append(p+":"+str(e))
o["mat_saved"]=ok; o["mat_bad"]=bad
# 2 imports
def info(path):
    ms=[x for x in eal.list_assets(path,True,False) if "/StaticMeshes/" in x] if eal.does_directory_exist(path) else []
    if not ms: return None
    m=unreal.load_asset(ms[0])
    if not m: return None
    r={"n_meshes":len(ms),"first":ms[0].split(".")[-1]}
    try:
        b=m.get_bounding_box(); s=b.max-b.min; r["size_cm"]=[round(s.x),round(s.y),round(s.z)]
    except Exception as e: r["bb_err"]=str(e)
    try: r["verts"]=unreal.EditorStaticMeshLibrary.get_number_verts(m,0)
    except Exception: pass
    return r
o["pup_before"]=info("/Game/Daedalus/Art/Mob/Mob_CorsoPup")
rows={"6296":"Prop_PetWaterBowl_V2","6297":"Prop_PetWaterBowl_V3","6298":"Prop_PetWaterBowl_V4",
      "6299":"Prop_HayBale_V2","6300":"Prop_HayBale_V3","6301":"Prop_HayBale_V4","1372":"Mob_CorsoPup",
      "1376":"Prop_Kennel","1377":"Prop_PetBed_Wicker","1378":"Prop_PetFeeder","1379":"Prop_PetWaterBowl"}
tasks=[]
for r,n in rows.items():
    f=os.path.join(G,n+".glb")
    if not os.path.exists(f): o["err"].append("nofile:"+n); continue
    t=unreal.AssetImportTask(); t.filename=f; t.destination_path="/Game/Daedalus/Art/"+n.split("_")[0]+"/"+n
    t.automated=True; t.save=True; t.replace_existing=True; tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
imp={}
for r,n in rows.items():
    path="/Game/Daedalus/Art/"+n.split("_")[0]+"/"+n
    imp[r]=info(path)
o["imported"]=imp; o["pup_after"]=imp.get("1372")
# 3 place bowls + hay into Island_AMF with the labels amf_loop_ue.py tags
O=unreal.Vector(4000000,2000000,2000); placed=[]
try:
    les.set_current_level_by_name("Island_AMF")
    byl={a.get_actor_label():a for a in eas.get_all_level_actors()}
    for i in (2,3,4):
        for src,lab,x,y in [("Prop_PetWaterBowl_V%d"%i,"Prop_Pet_AMF_Bowl_V%d"%i,1700,-700+(i-1)*600),
                            ("Prop_HayBale_V%d"%i,"Prop_Live_AMF_HayBale_V%d"%i,-2200+i*150,2450)]:
            if lab in byl: placed.append(lab+":exists"); continue
            sm=[x for x in eal.list_assets("/Game/Daedalus/Art/Prop/"+src,True,False) if "/StaticMeshes/" in x]; m=unreal.load_asset(sm[0]) if sm else None
            if not m: o["err"].append("noasset:"+src); continue
            a=eas.spawn_actor_from_object(m,O+unreal.Vector(x,y,0),unreal.Rotator(0,0,0))
            a.set_actor_label(lab); a.set_folder_path("AMF/KennelIsle/Food"); a.tags=["AMF_Island"]; placed.append(lab)
except Exception as e: o["err"].append("place:"+str(e))
o["placed"]=placed
json.dump(o,open(OUT,"w"),indent=1)
unreal.log("AMF_TURN2 "+json.dumps(o)[:2000])

