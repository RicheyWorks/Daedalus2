import unreal
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if les.is_in_play_in_editor(): les.editor_request_end_play()
w = ues.get_editor_world(); SUB = "/Game/Pythagoras/Maps/Island_Pythagoras"
names = [l.get_path_name() for l in unreal.EditorLevelUtils.get_levels(w)]
loaded = any("Island_Pythagoras" in n for n in names)
if not loaded and unreal.EditorAssetLibrary.does_asset_exist(SUB):
    unreal.EditorLevelUtils.add_level_to_world(w, SUB, unreal.LevelStreamingAlwaysLoaded); loaded = True
E = unreal.EditorLoadingAndSavingUtils
dirty_maps = [p.get_name() for p in E.get_dirty_map_packages()]
ok = E.save_dirty_packages(True, False)
result = {"world": w.get_name(), "island_loaded": loaded, "saved_maps": dirty_maps, "ok": ok, "still_dirty_maps": [p.get_name() for p in E.get_dirty_map_packages()]}
