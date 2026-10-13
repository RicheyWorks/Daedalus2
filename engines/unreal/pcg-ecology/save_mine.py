import unreal
E = unreal.EditorLoadingAndSavingUtils
mine = [p for p in E.get_dirty_content_packages() if p.get_name().startswith("/Game/Pythagoras/")]
ok = E.save_packages(mine, True) if mine else True
rest = [p.get_name() for p in E.get_dirty_content_packages()] + [p.get_name() for p in E.get_dirty_map_packages()]
result = {"saved_mine": len(mine), "ok": ok, "still_dirty": rest}
