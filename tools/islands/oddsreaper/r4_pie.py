import sys, time, json
sys.argv=["x","--skip-build"]
import oddsreaper_turn as T
# 1) undo the storm leak in DaedalusWorld + make our sublevel AlwaysLoaded, saved and file-verified (editor world)
T.say(f"world sky: {T.run_file(T.TOOL + chr(92) + 'restore_world_sky.py', 90)}")
CAM, TGT = T.hero_target_from_layout({})  # OddsReaper Island hero pose from layout.json (world cm)
T.call("play", timeout=60); T.say("Play"); time.sleep(6)
try: T.say(f"force: {T.force_storm_in_pie()}")
except Exception as e: T.say(f"force fail {e}")
time.sleep(4)
try:
    T.take_hero_shot(CAM, TGT, name="hero_unreal_play_r4.png"); T.say(f"rgb {T.hero_storm_rgb(T.SHOTS + chr(92) + 'hero_unreal_play_r4.png')}")
except Exception as e: T.say(f"shot fail {e}")
T.call("stop", timeout=60); T.say("stopped")
T.py("import unreal\nles=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)\nles.set_current_level_by_name('OddsReaperIsland')\nresult=les.save_current_level()",60); T.say("saved OddsReaperIsland")
