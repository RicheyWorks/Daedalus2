# SPDX-License-Identifier: MIT
"""Place and configure the Daedalus Sky Director (day/night + weather + biome mood) in a level. Board #11.

Editor-only, idempotent: run it again and it updates rather than duplicates.
    py daedalus_sky_director.py                       # DaedalusWorld, mood young_meadow, 9:00, Clear
    env DAEDALUS_SKY_MAP / _MOOD / _HOUR / _WEATHER / _DAYMIN override.
Reuses import_world_package.ensure_sky for sun/sky/skylight/haze; adds a VolumetricCloud if missing.
Moods come from data/wild_biomes_moods.csv (shipped next to this script as wild_biomes_moods.csv).
"""
import os
import unreal

MAP = os.environ.get("DAEDALUS_SKY_MAP", "/Game/Daedalus/DaedalusWorld")
MOOD = os.environ.get("DAEDALUS_SKY_MOOD", "young_meadow")
HOUR = float(os.environ.get("DAEDALUS_SKY_HOUR", "9"))
WEATHER = os.environ.get("DAEDALUS_SKY_WEATHER", "CLEAR").upper()
DAYMIN = float(os.environ.get("DAEDALUS_SKY_DAYMIN", "20"))
TABLE_DIR, TABLE_NAME = "/Game/Daedalus/Sky", "DT_WildBiomeMoods"
LABEL, FOLDER = "Daedalus Sky Director", "Daedalus/Sky"
HERE = os.path.dirname(os.path.abspath(__file__))


def log(msg):
    unreal.log("[sky-director] " + msg)


def mood_table():
    path = f"{TABLE_DIR}/{TABLE_NAME}"
    csv = os.path.join(HERE, "wild_biomes_moods.csv")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", csv)
    task.set_editor_property("destination_path", TABLE_DIR)
    task.set_editor_property("destination_name", TABLE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    factory = unreal.CSVImportFactory()
    settings = unreal.CSVImportSettings()
    settings.set_editor_property("import_row_struct", unreal.DaedalusLightMood.static_struct())
    settings.set_editor_property("import_type", unreal.CSVImportType.ECSV_DATA_TABLE)
    factory.set_editor_property("automated_import_settings", settings)
    task.set_editor_property("factory", factory)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return unreal.load_asset(path)


def run():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not les.load_level(MAP):
        raise RuntimeError("cannot open " + MAP)
    try:
        from import_world_package import ensure_sky
        added = ensure_sky(actors)
    except Exception as e:  # keep working if the importer moved
        added, _ = [], log(f"ensure_sky unavailable: {e}")
    all_actors = actors.get_all_level_actors()
    if not any(isinstance(a, unreal.VolumetricCloud) for a in all_actors):
        c = actors.spawn_actor_from_class(unreal.VolumetricCloud, unreal.Vector(0, 0, 0))
        c.set_actor_label("Daedalus Clouds"); c.set_folder_path(FOLDER); added.append("Daedalus Clouds")
    for a in actors.get_all_level_actors():  # the director rotates the sun, so it must be movable
        if isinstance(a, (unreal.DirectionalLight, unreal.SkyLight)):
            a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)

    director = next((a for a in actors.get_all_level_actors() if isinstance(a, unreal.DaedalusSkyDirector)), None)
    if director is None:
        director = actors.spawn_actor_from_class(unreal.DaedalusSkyDirector, unreal.Vector(0, 0, 500))
        director.set_actor_label(LABEL); director.set_folder_path(FOLDER)
    director.set_editor_property("mood_table", mood_table())
    director.set_editor_property("mood", MOOD)
    director.set_editor_property("time_of_day", HOUR)
    director.set_editor_property("day_length_minutes", DAYMIN)
    director.set_editor_property("weather", getattr(unreal.DaedalusWeather, WEATHER))
    found = director.find_sky_actors()
    director.apply_now()
    les.save_current_level()

    ok = all(director.get_editor_property(p) for p in ("sun", "sky_light", "height_fog", "clouds"))
    log(f"added={added} linked={found} mood={MOOD} hour={HOUR} weather={WEATHER} {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    run()
