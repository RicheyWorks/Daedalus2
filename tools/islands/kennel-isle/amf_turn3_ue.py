# art-master-flex r3 turn: tag the herb actors missing AMF_Herb, delete leftover Mob_Starfall_Hopper_K3 meshes and
# duplicate CorsoPup/Kennel parts in the AMF + pet folders, then save ONLY Island_AMF and WildBiomes_AMF_Pets.
# DRY=True only reports (safe off-turn). Set DRY=False on the AMF editor turn.
import unreal, json
DRY = True
OUT=r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_turn3.json"
eal=unreal.EditorAssetLibrary; eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o={"dry":DRY,"err":[]}
try:
    if les.is_in_play_in_editor(): les.editor_request_end_play()
except Exception as e: o["err"].append("pie:"+str(e))
# 1 herb tags (Island_AMF)
tagged=[]
try:
    les.set_current_level_by_name("Island_AMF")
    for a in eas.get_all_level_actors():
        l=a.get_actor_label()
        if not l.startswith("Prop_Herb_AMF_"): continue
        t=[str(x) for x in a.tags]
        if "AMF_Herb" in t: continue
        tagged.append(l)
        if not DRY:
            a.modify(); a.tags=list(a.tags)+[unreal.Name("AMF_Herb")]
except Exception as e: o["err"].append("tag:"+str(e))
o["herb_tagged_now"]=len(tagged); o["herb_tagged_list"]=tagged
# 2 asset cleanup in AMF + pet folders
FOLDERS=["/Game/AMF","/Game/Daedalus/Art/Mob/Mob_CorsoPup","/Game/Daedalus/Art/Prop/Prop_Kennel"]
cands=[]; seen={}
for f in FOLDERS:
    if not eal.does_directory_exist(f): continue
    for p in eal.list_assets(f,True,False):
        pkg=p.split(".")[0]; n=pkg.split("/")[-1]
        if "Mob_Starfall_Hopper_K3" in n: cands.append([pkg,"hopper"]); continue
        if f!="/Game/AMF" and "/StaticMeshes/" in pkg:
            key=(f,n)
            if key in seen: cands.append([pkg,"dup_of:"+seen[key]])
            else: seen[key]=pkg
deleted=[]; kept=[]
for pkg,why in cands:
    refs=[str(r) for r in (eal.find_package_referencers_for_asset(pkg,False) or []) if not str(r).startswith(pkg)]
    # never delete a dup that a placed actor/level still uses; report it instead
    if refs: kept.append([pkg,why,refs[:5]]); continue
    if DRY: deleted.append([pkg,why,"would_delete",refs[:5]]); continue
    try: deleted.append([pkg,why,bool(eal.delete_asset(pkg)),refs[:5]])
    except Exception as e: o["err"].append("del:"+pkg+":"+str(e))
o["deleted"]=deleted; o["kept_referenced"]=kept
# 3 save only the two AMF levels
saved=[]
if not DRY:
    world=unreal.EditorLevelLibrary.get_editor_world()
    for lv in unreal.EditorLevelUtils.get_levels(world):
        p=lv.get_path_name()
        if "Island_AMF" in p or "WildBiomes_AMF_Pets" in p:
            try: saved.append([p,unreal.EditorLoadingAndSavingUtils.save_packages([lv.get_outermost()],True)])
            except Exception as e: saved.append([p,str(e)])
o["saved"]=saved
json.dump(o,open(OUT,"w"),indent=1)
unreal.log("AMF_TURN3 "+json.dumps(o)[:2000])


