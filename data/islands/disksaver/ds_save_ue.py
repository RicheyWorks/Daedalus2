# disk-saver: save dirty Island_DiskSaver + DaedalusWorld first thing in turn. No deletes, no Play changes.
import unreal
out = {}
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
out["pie"] = bool(les.is_in_play_in_editor())
out["levels_saved"] = bool(unreal.EditorLevelLibrary.save_all_dirty_levels())
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
try: out["world_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_map(w, "/Game/Daedalus/DaedalusWorld"))
except Exception as e: out["world_err"] = str(e)[:120]
result = out
