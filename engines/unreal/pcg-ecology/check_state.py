import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ew = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = eas.get_all_level_actors()
result = {"world": ew.get_name() if ew else None, "plants": sum(a.actor_has_tag("PYTH_EcoPlant") for a in acts),
  "flora": sum(a.actor_has_tag("PYTH_Flora") for a in acts),
  "graphs": [p for p in ("/Game/Pythagoras/PCGEcology/PCG_Ecology", "/Game/Pythagoras/PCGEcology/PCG_EcologyNative") if unreal.EditorAssetLibrary.does_asset_exist(p)]}
