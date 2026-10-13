import unreal, json, os
eal=unreal.EditorAssetLibrary; o={}
ar=unreal.AssetRegistryHelpers.get_asset_registry()
def find(name):
    return [str(d.package_name) for d in ar.get_assets_by_path("/Game",True) if str(d.asset_name)==name]
o["corso"]=find("Mob_CaneCorso"); o["pup"]=find("Mob_CorsoPup"); o["panda"]=find("Mob_RedPanda")
cls={}
amf=ar.get_assets_by_path("/Game/AMF",True)
o["amf_n"]=len(amf)
for d in amf:
    c=str(d.asset_class_path.asset_name); cls[c]=cls.get(c,0)+1
o["amf_cls"]=cls
o["rockcrate_mats"]=[str(d.package_name) for d in amf if "Material" in str(d.asset_class_path.asset_name) and ("Rock" in str(d.asset_name) or "Crate" in str(d.asset_name))][:20]
o["dirty"]=[str(x.get_name()) for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()][:40]
t=unreal.AssetImportTask(); t.filename=r"C:\Users\730ri\projects\bot-team\art\glb\Mob_RedPanda.glb"; t.destination_path="/Game/Daedalus/Art/Mob"; t.destination_name="Mob_RedPanda"; t.automated=True; t.save=True; t.replace_existing=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
o["panda_import"]=[str(x) for x in t.imported_object_paths]
json.dump(o,open(r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_probe.json","w"),indent=1)
