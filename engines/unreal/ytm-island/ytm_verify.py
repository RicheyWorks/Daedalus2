import unreal
act=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
A=[a for a in act.get_all_level_actors() if a.actor_has_tag("YTM_Island")]
sp=[a for a in A if a.actor_has_tag("YTM_Spawn")]
d=[a for a in A if a.actor_has_tag("Drinkable")]
near=[a for a in d if sp and (a.get_actor_location()-sp[0].get_actor_location()).length()<=4000]
lvls=set(a.get_level().get_outer().get_name() for a in A[:50])
miss=0
print("YTM actors",len(A),"spawn",len(sp),"drinkable",len(d),"WATER", "OK" if near else "FAIL", len(near),"within 40m; levels",lvls)
print("herbs",len([a for a in A if a.actor_has_tag("YTM_Herb")]),"livestock",len([a for a in A if a.actor_has_tag("YTM_Livestock")]),"hooks",hasattr(unreal,"DaedalusWaterSource"))
print("play", les.is_in_play_in_editor())
