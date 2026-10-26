import unreal
print(sorted(set(x.split(".")[-1] for x in unreal.EditorAssetLibrary.list_assets("/Game/Daedalus/Art/Mob",True,False) if x.split(".")[-1].startswith("Mob_")))[:80])
