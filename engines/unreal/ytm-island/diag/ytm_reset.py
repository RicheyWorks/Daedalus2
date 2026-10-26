import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); print("persistent current", les.set_current_level_by_name("DaedalusWorld"), les.get_current_level().get_outer().get_name())
