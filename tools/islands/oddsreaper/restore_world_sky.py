# SPDX-License-Identifier: MIT
"""Editor-turn fix (run ONLY on a granted turn). Undo the OddsReaper storm leak into DaedalusWorld and make the
OddsReaperIsland sublevel stream in Play. Root cause (2026-10-13): DaedalusWorld.umap on disk (saved 23:44) holds the
director at oddsreaper_storm/Storm/18.75/clock paused -> sun 0 lux, skylight 0.017 = near-black for every island.
The 23:53 restore was in-memory only (save_current_level saved the current sublevel, not the persistent map), so the
next level load brought the dark state back. This script saves the persistent map explicitly and verifies the file."""
import os
import unreal

MAP = "/Game/Daedalus/DaedalusWorld"
UMAP = r"C:\Unreal\DaedalusRealm\Content\Daedalus\DaedalusWorld.umap"
DEFAULTS = {"mood": "young_meadow", "hour": 9.4}


def _setp(o, name, val):
    for p in (name, "b_" + name):
        try: o.set_editor_property(p, val); return True
        except Exception: pass
    return False


def run():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    d = [a for a in actors if isinstance(a, unreal.DaedalusSkyDirector)]
    out = {"directors": len(d)}
    if d:
        x = d[0]
        out["before"] = {"mood": str(x.get_editor_property("mood")), "weather": str(x.get_editor_property("weather")),
                         "hour": x.get_editor_property("time_of_day")}
        x.set_editor_property("mood", DEFAULTS["mood"]); x.set_editor_property("weather", unreal.DaedalusWeather.CLEAR)
        _setp(x, "clock_running", True); x.set_editor_property("auto_weather_hours", 0.0)
        x.set_time_of_day(DEFAULTS["hour"]); x.apply_now()
        sun = x.get_editor_property("sun"); sky = x.get_editor_property("sky_light")
        out["sun_lux"] = sun.root_component.get_editor_property("intensity") if sun else None
        out["sky"] = sky.root_component.get_editor_property("intensity") if sky else None
    # Our sublevel was created as LevelStreamingDynamic, which never loads in PIE -> volumes=0, off-island Play shots.
    try:
        sl = unreal.GameplayStatics.get_streaming_level(world, "OddsReaperIsland")
        if sl and not isinstance(sl, unreal.LevelStreamingAlwaysLoaded):
            unreal.EditorLevelUtils.set_streaming_class_for_level(sl, unreal.LevelStreamingAlwaysLoaded)
        out["stream"] = "always_loaded"
    except Exception as e:
        out["stream"] = f"err: {e}"[:120]
    before = os.path.getmtime(UMAP)
    out["saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, MAP))
    out["umap_written"] = os.path.getmtime(UMAP) > before
    out["ok"] = bool(d) and out["saved"] and out["umap_written"] and (out.get("sun_lux") or 0) > 1
    return out


if __name__ == "__main__":
    print(run())
