# SPDX-License-Identifier: MIT
"""Editor-turn fix (run ONLY on a granted turn). Undo the OddsReaper storm leak into DaedalusWorld and make the
OddsReaperIsland sublevel stream in Play. Root cause (2026-10-13): DaedalusWorld.umap on disk (saved 23:44) holds the
director at oddsreaper_storm/Storm/18.75/clock paused -> sun 0 lux, skylight 0.017 = near-black for every island.
The 23:53 restore was in-memory only (save_current_level saved the current sublevel, not the persistent map), so the
next level load brought the dark state back. This script saves the persistent map explicitly, verifies the umap mtime,
re-reads the director after save, and refuses to spawn a second sun."""
import json
import os
import time
import unreal

MAP = "/Game/Daedalus/DaedalusWorld"
UMAP = r"C:\Unreal\DaedalusRealm\Content\Daedalus\DaedalusWorld.umap"
RESULT = r"C:\Users\730ri\projects\bot-team\shots\oddsreaper\restore_world_sky.json"
DEFAULTS = {"mood": "young_meadow", "hour": 9.4}
MIN_SUN = 1.0
MIN_SKY = 0.5


def _setp(o, name, val):
    for p in (name, "b_" + name):
        try:
            o.set_editor_property(p, val)
            return True
        except Exception:
            pass
    return False


def _snap(x):
    sun = x.get_editor_property("sun")
    sky = x.get_editor_property("sky_light")
    return {
        "mood": str(x.get_editor_property("mood")),
        "weather": str(x.get_editor_property("weather")),
        "hour": float(x.get_editor_property("time_of_day")),
        "sun_lux": float(sun.root_component.get_editor_property("intensity")) if sun else None,
        "sky": float(sky.root_component.get_editor_property("intensity")) if sky else None,
    }


def _count_suns(actors):
    n = 0
    for a in actors:
        try:
            if a.get_class().get_name() == "DirectionalLight":
                n += 1
        except Exception:
            pass
    return n


def _save_verified(world):
    """Persist DaedalusWorld and confirm the umap file actually advanced."""
    before = os.path.getmtime(UMAP) if os.path.exists(UMAP) else 0.0
    saved = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, MAP))
    time.sleep(0.15)
    after = os.path.getmtime(UMAP) if os.path.exists(UMAP) else 0.0
    written = after > before
    if saved and not written:
        time.sleep(0.25)
        saved = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, MAP))
        time.sleep(0.15)
        after = os.path.getmtime(UMAP) if os.path.exists(UMAP) else 0.0
        written = after > before
    return {
        "saved": saved,
        "umap_written": written,
        "umap_mtime_before": before,
        "umap_mtime_after": after,
    }


def run():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    suns_before = _count_suns(actors)
    d = [a for a in actors if isinstance(a, unreal.DaedalusSkyDirector)]
    out = {"directors": len(d), "suns_before": suns_before, "new_sun": False}

    if d:
        x = d[0]
        out["before"] = _snap(x)
        x.set_editor_property("mood", DEFAULTS["mood"])
        x.set_editor_property("weather", unreal.DaedalusWeather.CLEAR)
        _setp(x, "clock_running", True)
        x.set_editor_property("auto_weather_hours", 0.0)
        x.set_time_of_day(DEFAULTS["hour"])
        x.apply_now()
        out["after_apply"] = _snap(x)

    # Our sublevel was LevelStreamingDynamic (never loads in PIE) -> volumes=0, off-island Play shots.
    try:
        sl = unreal.GameplayStatics.get_streaming_level(world, "OddsReaperIsland")
        if sl and not isinstance(sl, unreal.LevelStreamingAlwaysLoaded):
            unreal.EditorLevelUtils.set_streaming_class_for_level(sl, unreal.LevelStreamingAlwaysLoaded)
        out["stream"] = "always_loaded"
    except Exception as e:
        out["stream"] = f"err: {e}"[:120]

    save_info = _save_verified(world)
    out.update(save_info)

    # Post-save disk check: re-read director (save must not have reverted Clear).
    actors2 = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    out["suns_after"] = _count_suns(actors2)
    out["new_sun"] = out["suns_after"] > suns_before
    d2 = [a for a in actors2 if isinstance(a, unreal.DaedalusSkyDirector)]
    if d2:
        out["after_save"] = _snap(d2[0])

    snap = out.get("after_save") or out.get("after_apply") or {}
    sun_ok = snap.get("sun_lux") or 0
    sky_ok = snap.get("sky") or 0
    mood_ok = "young_meadow" in str(snap.get("mood", ""))
    weather_ok = "CLEAR" in str(snap.get("weather", "")).upper()
    out["ok"] = (
        bool(d)
        and out["saved"]
        and out["umap_written"]
        and sun_ok >= MIN_SUN
        and sky_ok >= MIN_SKY
        and mood_ok
        and weather_ok
        and not out["new_sun"]
    )
    try:
        os.makedirs(os.path.dirname(RESULT), exist_ok=True)
        with open(RESULT, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        out["result_json"] = RESULT
    except Exception as e:
        out["result_json_err"] = str(e)[:120]
    return out


if __name__ == "__main__":
    print(run())
