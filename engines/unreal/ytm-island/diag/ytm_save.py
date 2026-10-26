import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ok1=les.save_current_level()
unreal.EditorLevelUtils.make_level_current(w.get_editor_property("persistent_level")) if False else None
ok2=unreal.EditorLoadingAndSavingUtils.save_map(w, w.get_path_name().split(".")[0])
dirty=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
print("saved sublevel",ok1,"persistent",ok2,"dirty maps left",dirty,"play",les.is_in_play_in_editor(), "world", w.get_path_name())
