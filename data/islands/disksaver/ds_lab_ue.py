import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
m=[a for a in eas.get_all_level_actors() if "DS_Island" in [str(t) for t in a.tags]]
result=sorted(set(a.get_actor_label()[:40] for a in m))[:200]
