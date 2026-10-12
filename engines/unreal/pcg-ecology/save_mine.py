# Save ONLY Pythagoras assets and the current map; never touch other teams' dirty packages (reported, not saved).
import unreal
L=unreal.EditorLoadingAndSavingUtils; EA=unreal.EditorAssetLibrary
for dbg in ("/Game/Pythagoras/PCGEcology/PCG_EcoDebug_grid","/Game/Pythagoras/PCGEcology/PCG_EcoDebug_grid_proj"):
    if EA.does_asset_exist(dbg) or unreal.load_asset(dbg): EA.delete_asset(dbg)
dc=[p.get_name() for p in L.get_dirty_content_packages()]; dm=[p.get_name() for p in L.get_dirty_map_packages()]
mine=[p for p in dc if p.startswith("/Game/Pythagoras/")]
saved=[(p, EA.save_asset(p, True)) for p in mine]
if "/Game/Daedalus/DaedalusWorld" in dm: saved.append(("map", unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()))
after=[p.get_name() for p in L.get_dirty_content_packages()]+[p.get_name() for p in L.get_dirty_map_packages()]
result={"saved":saved,"others_left_dirty":len([p for p in after if not p.startswith("/Game/Pythagoras/")]),"mine_left":[p for p in after if p.startswith("/Game/Pythagoras/") or p=="/Game/Daedalus/DaedalusWorld"]}
