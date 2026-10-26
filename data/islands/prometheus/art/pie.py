import unreal
print("PIE" if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() else "NOPIE")
