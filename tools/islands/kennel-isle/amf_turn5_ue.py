# art-master-flex r5: tag brew trough + herb actors with tonics.json data (tags only) + 1 sign. AMF levels only.
import unreal, json
OUT=r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_turn5.json"
H={"Barkbalm": ["Tonic_Herb_Barkbalm", "Tonic_Role_base", "Tonic_Family_Heal", "Tonic_Shape_burst", "Tonic_Mod_hearts_add_1.0"], "Guardthistle": ["Tonic_Herb_Guardthistle", "Tonic_Role_base", "Tonic_Family_Shield", "Tonic_Shape_sustained", "Tonic_Mod_blunt_add_0.15"], "Wagwort": ["Tonic_Herb_Wagwort", "Tonic_Role_base", "Tonic_Family_Speed", "Tonic_Shape_burst", "Tonic_Mod_speed_mul_1.1"], "Howlroot": ["Tonic_Herb_Howlroot", "Tonic_Role_base", "Tonic_Family_Fury", "Tonic_Shape_burst", "Tonic_Mod_damage_add_0.5"], "Dozeleaf": ["Tonic_Herb_Dozeleaf", "Tonic_Role_base", "Tonic_Family_Calm", "Tonic_Shape_sustained", "Tonic_Mod_loyalty_add_5"], "Pawmint": ["Tonic_Herb_Pawmint", "Tonic_Role_heart", "Tonic_Stat_Stamina", "Tonic_Mod_cooldownPct_add_-0.05"], "Ironfang": ["Tonic_Herb_Ironfang", "Tonic_Role_heart", "Tonic_Stat_Defense", "Tonic_Mod_blunt_add_0.05"], "Snoutsage": ["Tonic_Herb_Snoutsage", "Tonic_Role_heart", "Tonic_Stat_Perception", "Tonic_Mod_hazardResist_add_0.1"], "Starkibble": ["Tonic_Herb_Starkibble", "Tonic_Role_heart", "Tonic_Stat_Luck", "Tonic_Mod_expPct_add_0.05"], "Furfern": ["Tonic_Herb_Furfern", "Tonic_Role_finish", "Tonic_Finish_Long", "Tonic_DurSec_240"], "Dewclaw": ["Tonic_Herb_Dewclaw", "Tonic_Role_finish", "Tonic_Finish_Swim", "Tonic_DurSec_120"], "Coppercap": ["Tonic_Herb_Coppercap", "Tonic_Role_finish", "Tonic_Finish_Instant", "Tonic_DurSec_0"]}
TR=["Tonic_Data_tonics_json_v1","Tonic_MaxHerbs_3","Tonic_Slot1_base","Tonic_Slot2_heart","Tonic_Slot3_finish","Tonic_Decay_3drinks_10min","Tonic_Recipes_100","Tonic_CorsoDrinker_1.0","Tonic_Pack_0.5"]
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o={"err":[],"herbs":0,"trough":0,"sign":0,"tags_added":0,"saved":[]}
def addtags(a,ts):
    cur=[str(x) for x in a.tags]; new=[t for t in ts if t not in cur]
    if new:
        a.modify(); a.tags=list(a.tags)+[unreal.Name(t) for t in new]; o["tags_added"]+=len(new)
try:
    if les.is_in_play_in_editor(): les.editor_request_end_play()
except Exception as e: o["err"].append("pie:"+str(e))
try:
    les.set_current_level_by_name("Island_AMF")
    trough=None
    for a in eas.get_all_level_actors():
        if "Island_AMF" not in a.get_outer().get_path_name(): continue
        tg=[str(x) for x in a.tags]
        if "Brew_Trough" in tg:
            addtags(a,TR); o["trough"]+=1; trough=a
        if "Herb_Source" in tg:
            nm=None
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                if c.static_mesh:
                    n=c.static_mesh.get_name()
                    for k in H:
                        if "_"+k+"_" in n or n.endswith("_"+k): nm=k
            if not nm:
                for k in H:
                    if k in a.get_actor_label(): nm=k
            if nm: addtags(a,H[nm]); o["herbs"]+=1
            else: o["err"].append("noherb:"+a.get_actor_label())
        if "AMF_TonicSign" in tg: o["sign"]=-1
    if trough and o["sign"]==0:
        loc=trough.get_actor_location()+unreal.Vector(0,0,160)
        s=eas.spawn_actor_from_class(unreal.TextRenderActor,loc)
        s.set_actor_label("AMF_TonicSign"); s.tags=[unreal.Name("AMF_TonicSign"),unreal.Name("AMF_Loop")]
        t=s.text_render; t.set_text("BREW TROUGH: base + heart + finish (max 3)"); t.set_world_size(24); t.set_text_render_color(unreal.Color(80,220,90,255)); t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        o["sign"]=1
except Exception as e: o["err"].append("tag:"+str(e))
for L in ["Island_AMF","WildBiomes_AMF_Pets"]:
    try:
        for lv in unreal.EditorLevelUtils.get_levels(unreal.EditorLevelLibrary.get_editor_world()):
            if L in lv.get_path_name(): o["saved"].append([L,unreal.EditorLoadingAndSavingUtils.save_packages([lv.get_outermost()],True)])
    except Exception as e: o["err"].append("save:"+L+":"+str(e))
json.dump(o,open(OUT,"w"),indent=1)
