import unreal
ok=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
result=[ok,[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]]
