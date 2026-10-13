import unreal, collections
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem); es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); W=ue.get_editor_world()
ar=unreal.AssetRegistryHelpers.get_asset_registry()
sw=[str(a.package_name) for a in ar.get_assets_by_path("/Game/Prometheus",recursive=True) if str(a.asset_class_path.asset_name) in ("SoundWave","SoundCue")]
acts=[a for a in es.get_all_level_actors() if a.get_actor_label().startswith("PI_")]
pref=collections.Counter(a.get_actor_label().split("_")[1] for a in acts)
print("world",W.get_name(),"sounds",len(sw),sw[:40]); print("prefixes",dict(pref.most_common(30)))
print("amb",[a.get_actor_label() for a in acts if isinstance(a,unreal.AmbientSound)][:30])
