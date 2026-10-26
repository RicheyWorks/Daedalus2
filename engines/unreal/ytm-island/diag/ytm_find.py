import unreal
r=unreal.AssetRegistryHelpers.get_asset_registry()
for n in ["Prop_YTM_Water_Spring_V1","Mob_YTM_Kelpig_Adult","Prop_YTM_Herb_Doleaf_S1"]:
    f=unreal.ARFilter(package_paths=["/Game"],recursive_paths=True)
    xs=[str(a.package_name) for a in r.get_assets_by_package_name if False] if False else []
print([p for p in unreal.EditorAssetLibrary.list_assets("/Game/Daedalus/Art/Prop",True,False) if "Water_Spring" in p][:3])
print([p for p in unreal.EditorAssetLibrary.list_assets("/Game",True,False) if "YTM_Water_Spring" in p][:3])
