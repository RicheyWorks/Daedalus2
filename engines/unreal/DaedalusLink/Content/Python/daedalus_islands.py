# SPDX-License-Identifier: MIT
"""Write Saved/Daedalus/islands.json for UDaedalusStreamer (ADR-062): one row per island sublevel, with its centre and
radius taken from its own actors' bounds. That is Minecraft's chunk list, with islands as the chunks.

    import daedalus_islands; daedalus_islands.write()            # or write(["/Game/Claude/", "/Game/Buffffff/"])

By default it lists only the levels whose package starts with one of OWNED. Each bot opts its own island in, so
nobody's level starts streaming without its owner agreeing. A level must be Dynamic (not AlwaysLoaded) to unload;
the report says which ones are not.
"""
import json
import os

import unreal

OWNED = ["/Game/Claude/"]   # unreal-team's own; other bots add their prefix when they opt in
MARGIN = 2000.0             # cm added to each radius


def _rows(prefixes):
    world = unreal.EditorLevelLibrary.get_editor_world()
    rows, notes = [], []
    for sl in world.get_streaming_levels():
        pkg = str(sl.get_world_asset_package_name())
        if not any(pkg.startswith(p) for p in prefixes):
            continue
        level = sl.get_loaded_level()
        if level is None:
            notes.append(pkg + ": not loaded in the editor, skipped")
            continue
        actors = [a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_level() == level]
        if not actors:
            notes.append(pkg + ": no actors")
            continue
        centre, extent = unreal.GameplayStatics.get_actor_array_bounds(actors, False)
        radius = (extent.x ** 2 + extent.y ** 2 + extent.z ** 2) ** 0.5 + MARGIN
        if isinstance(sl, unreal.LevelStreamingAlwaysLoaded):
            notes.append(pkg + ": AlwaysLoaded, so the streamer cannot unload it (make it Dynamic to stream)")
        rows.append({"package": pkg, "x": round(centre.x), "y": round(centre.y), "z": round(centre.z),
                     "radius": round(radius), "always": False, "actors": len(actors)})
    return rows, notes


def write(prefixes=None):
    rows, notes = _rows(prefixes or OWNED)
    out = os.path.join(unreal.Paths.project_saved_dir(), "Daedalus", "islands.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # keep other bots' rows already in the file
    old = []
    if os.path.exists(out):
        try:
            with open(out, encoding="utf-8") as f:
                old = [r for r in json.load(f) if r.get("package") not in {x["package"] for x in rows}]
        except (OSError, ValueError):
            old = []
    with open(out, "w", encoding="utf-8") as f:
        json.dump(old + rows, f, indent=1)
    return {"path": out, "rows": rows, "kept": len(old), "notes": notes}
