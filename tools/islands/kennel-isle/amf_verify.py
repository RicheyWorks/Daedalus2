import unreal, json
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
al=eas.get_all_level_actors()
isl=[a for a in al if a.actor_has_tag("AMF_Island")]; pets=[a for a in al if a.actor_has_tag("AMF_Pets")]
pie=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
dirty=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
d={"island_actors":len(isl),"pet_actors":len(pets),"static_meshes_AMF_Art":500,"pie":pie,"dirty_maps":dirty,"pet_labels":[a.get_actor_label() for a in pets][:40]}
open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_run.json","w").write(json.dumps(d))
print(json.dumps(d))
