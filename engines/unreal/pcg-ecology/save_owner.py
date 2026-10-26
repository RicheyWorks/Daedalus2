import unreal
want=["/Game/DaedalusAudio/SW_Jukebox_e00015","/Game/DaedalusAudio/SW_Bed_Rain"]
dc=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
dm=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
other=[p for p in dc+dm if p not in want]
saved=[]
if not other:
    for p in want:
        if p in dc: saved.append((p, unreal.EditorAssetLibrary.save_asset(p, True)))
after=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]+[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
result={"other_dirty":other,"saved":saved,"dirty_after":after}
