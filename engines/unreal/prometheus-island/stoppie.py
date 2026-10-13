import unreal
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_game_world(): unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play(); print("STOPPED PIE")
else: print("NOPIE")
