import unreal
A=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
h=[a.get_actor_label() for a in A if a.actor_has_tag("YTM_Hero")]
print("HERO",len(h),sorted(h))
print("PIE", unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor())
