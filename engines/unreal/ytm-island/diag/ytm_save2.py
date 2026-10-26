import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ok=unreal.EditorLoadingAndSavingUtils.save_map(w,"/Game/Daedalus/DaedalusWorld")
sub=[p for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() if "YTM" in p.get_name()]
ok2=unreal.EditorLoadingAndSavingUtils.save_packages(sub,True) if sub else "clean"
seqs=[p for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() if "/Game/YTM" in p.get_name()]
ok3=unreal.EditorLoadingAndSavingUtils.save_packages(seqs,True) if seqs else "clean"
print("world",ok,"ytm sublevel",ok2,"ytm seq",ok3,"play",les.is_in_play_in_editor(),"current",les.get_current_level().get_outer().get_name())
