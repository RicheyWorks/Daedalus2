import unreal, json
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o={}
try: les.set_current_level_by_name("Island_AMF")
except Exception as e: o["err"]=str(e)
herb=0; herbtag=0; brew=[]; byl=[]
for a in eas.get_all_level_actors():
    l=a.get_actor_label(); t=[str(x) for x in a.tags]
    if l.startswith("Prop_Herb_AMF_"):
        herb+=1
        if "AMF_Herb" in t: herbtag+=1
    if "Brew_Trough" in t: brew.append(l)
    if l.startswith("Prop_Pet_AMF_Bowl_V") or l.startswith("Prop_Live_AMF_HayBale_V"): byl.append(l)
o.update(herb_actors=herb,herb_tagged=herbtag,brew_trough=brew,bowl_hay=sorted(set(byl)))
json.dump(o,open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_check2.json","w"),indent=1)
eal=unreal.EditorAssetLibrary
o["pup_meshes"]=[x.split(".")[-1] for x in eal.list_assets("/Game/Daedalus/Art/Mob/Mob_CorsoPup",True,False) if "/StaticMeshes/" in x]
o["kennel_meshes"]=[x.split(".")[-1] for x in eal.list_assets("/Game/Daedalus/Art/Prop/Prop_Kennel",True,False) if "/StaticMeshes/" in x]
json.dump(o,open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_check2.json","w"),indent=1)
