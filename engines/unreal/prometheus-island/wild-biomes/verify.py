import unreal, json
es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
L=[a.get_actor_label() for a in es.get_all_level_actors()]
want={"audio":["DA_JukeboxCabinet","DA_JukeboxEmitter_e00015","DA_BiomeAmbience_Rain"],"tod":["DA_Amb_Day","DA_Amb_Night","DA_Amb_Weather_Storm"]}
r={k:[x for x in v if x not in L] for k,v in want.items()}
r["coats"]=sum(1 for x in L if x.startswith("DA_Coat_")); r["craft"]=sum(1 for x in L if x.startswith("DA_Craft_")); r["wb"]=sum(1 for x in L if x.startswith("DA_WB_"))
r["pie"]=bool(ue.get_game_world()); r["map"]=ue.get_editor_world().get_path_name()
print("VERIFY",json.dumps(r))
