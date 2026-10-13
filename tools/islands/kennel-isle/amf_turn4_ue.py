# art-master-flex r4 turn: (a) delete unused Mob_Starfall_Hopper_K3 materials in AMF/CorsoPup/Kennel folders;
# (b) repoint WildBiomes_AMF_Pets actors from OLD-folder CorsoPup/Kennel meshes to the NEW (re-sent, nested) copies,
# save ONLY Island_AMF + WildBiomes_AMF_Pets, then delete OLD copies only if nothing references them.
# Touches only AMF + pet assets. DRY=True only reports.
import unreal, json
DRY = True
OUT=r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_turn4.json"
eal=unreal.EditorAssetLibrary; eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o={"dry":DRY,"err":[]}
try:
    if les.is_in_play_in_editor(): les.editor_request_end_play()
except Exception as e: o["err"].append("pie:"+str(e))
PAIRS=[("/Game/Daedalus/Art/Mob/Mob_CorsoPup/StaticMeshes/","/Game/Daedalus/Art/Mob/Mob_CorsoPup/Mob_CorsoPup/StaticMeshes/"),
       ("/Game/Daedalus/Art/Prop/Prop_Kennel/StaticMeshes/","/Game/Daedalus/Art/Prop/Prop_Kennel/Prop_Kennel/StaticMeshes/")]
dups=[]
for old,new in PAIRS:
    if not eal.does_directory_exist(old.rstrip("/")): continue
    for p in eal.list_assets(old.rstrip("/"),False,False):
        pkg=p.split(".")[0]; n=pkg.split("/")[-1]
        if eal.does_asset_exist(new+n): dups.append([pkg,new+n])
o["dup_pairs"]=dups
dmap={a:b for a,b in dups}
# remap in pets level
remapped=[]
try:
    les.set_current_level_by_name("WildBiomes_AMF_Pets")
    for a in eas.get_all_level_actors():
        if "WildBiomes_AMF_Pets" not in a.get_outer().get_path_name(): continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm=c.static_mesh
            if not sm: continue
            sp=sm.get_path_name().split(".")[0]
            if sp in dmap:
                remapped.append([a.get_actor_label(),c.get_name(),sp,dmap[sp]])
                if not DRY:
                    a.modify(); c.modify(); c.set_static_mesh(eal.load_asset(dmap[sp]))
except Exception as e: o["err"].append("remap:"+str(e))
o["remapped"]=remapped
saved=[]
if not DRY:
    world=unreal.EditorLevelLibrary.get_editor_world()
    for lv in unreal.EditorLevelUtils.get_levels(world):
        p=lv.get_path_name()
        if "Island_AMF" in p or "WildBiomes_AMF_Pets" in p:
            try: saved.append([p,unreal.EditorLoadingAndSavingUtils.save_packages([lv.get_outermost()],True)])
            except Exception as e: saved.append([p,str(e)])
o["saved"]=saved
# candidates: hopper materials + old dup meshes
cands=[[a,"dup_of:"+b] for a,b in dups]
for f in ["/Game/AMF","/Game/Daedalus/Art/Mob/Mob_CorsoPup","/Game/Daedalus/Art/Prop/Prop_Kennel"]:
    if not eal.does_directory_exist(f): continue
    for p in eal.list_assets(f,True,False):
        pkg=p.split(".")[0]
        if "Mob_Starfall_Hopper_K3" in pkg.split("/")[-1]: cands.append([pkg,"hopper"])
deleted=[]; kept=[]
remap_pending=set(r[2] for r in remapped) if DRY else set()
for pkg,why in cands:
    refs=[str(r) for r in (eal.find_package_referencers_for_asset(pkg,False) or []) if not str(r).startswith(pkg)]
    if DRY and pkg in remap_pending: refs=[r for r in refs if "WildBiomes_AMF_Pets" not in r]
    if refs: kept.append([pkg,why,refs[:5]]); continue
    if DRY: deleted.append([pkg,why,"would_delete"]); continue
    try: deleted.append([pkg,why,bool(eal.delete_asset(pkg))])
    except Exception as e: o["err"].append("del:"+pkg+":"+str(e))
o["deleted"]=deleted; o["kept_referenced"]=kept
json.dump(o,open(OUT,"w"),indent=1)
unreal.log("AMF_TURN4 "+json.dumps(o)[:2000])
