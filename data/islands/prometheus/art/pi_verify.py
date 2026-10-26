import unreal, json
es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); L=[a.get_actor_label() for a in es.get_all_level_actors()]
c=lambda p: sum(1 for x in L if x.startswith(p))
print("VERIFY",json.dumps(dict(spring=c("PI_Water_SpringBasin"),stream=c("PI_Water_Stream_"),cistern=c("PI_Water_Cistern_"),pipe=c("PI_Water_Pipe_"),trough=c("PI_Water_Trough_"),rain=c("PI_Water_RainCatcher_"),still=c("PI_Water_Still_"),herbs=c("PI_Herb_"),livestock_parts=c("PI_Stock_"),calls=c("PI_Call_"),warm_lights=c("PI_Light_Warm_"),terrain=c("PI_Terrain"))))
