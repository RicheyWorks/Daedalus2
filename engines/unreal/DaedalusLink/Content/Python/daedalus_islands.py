# SPDX-License-Identifier: MIT
"""Write Saved/Daedalus/islands.json for UDaedalusStreamer (ADR-064): one row per island sublevel, with its centre and
radius taken from its own actors' bounds. That is Minecraft's chunk list, with islands as the chunks.

    import daedalus_islands; daedalus_islands.write()            # or write(["/Game/Claude/", "/Game/Buffffff/"])

By default it lists only the levels whose package starts with one of OWNED. Each bot opts its own island in, so
nobody's level starts streaming without its owner agreeing. A level must be Dynamic (not AlwaysLoaded) to unload;
the report says which ones are not.

Each row also gets `disk_kib` (the level and every /Game package it depends on, from the asset registry) and
`ram_kib` (estimated from disk; see daedalus_dsb), and the same islands go to Saved/Daedalus/islands.dsb as a DSB 1
manifest, so the streamer's RAM budget (daedalus.StreamRamBudgetMiB) and disk-saver's Java planner (ADR-063) use
one set of numbers.
"""
import json
import os

import unreal

import daedalus_dsb

OWNED = ["/Game/Claude/"]   # unreal-team's own; other bots add their prefix when they opt in
MARGIN = 2000.0             # cm added to each radius


def _cost_fns():
    """deps(pkg) and size(pkg) for daedalus_dsb.package_cost, from the asset registry and the Content folder."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=False, include_hard_package_references=True, include_searchable_names=False,
        include_soft_management_references=False, include_hard_management_references=False)
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())

    def deps(pkg):
        return [str(x) for x in (ar.get_dependencies(pkg, opts) or [])]

    def size(pkg):
        if not pkg.startswith(daedalus_dsb.GAME):
            return 0
        base = os.path.join(content, *pkg[len(daedalus_dsb.GAME):].split("/"))
        return sum(os.path.getsize(base + ext) for ext in (".umap", ".uasset", ".uexp", ".ubulk") if os.path.exists(base + ext))

    return deps, size


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
        row = {"package": pkg, "x": round(centre.x), "y": round(centre.y), "z": round(centre.z),
               "radius": round(radius), "always": False, "actors": len(actors)}
        try:
            deps, size = _cost_fns()
            nbytes, packages = daedalus_dsb.package_cost(pkg, deps, size)
            row.update(disk_kib=daedalus_dsb.kib(nbytes), packages=packages)
            row["ram_kib"] = daedalus_dsb.ram_kib(row["disk_kib"])
        except Exception as e:  # a cost we can't read leaves the row unbudgeted (ram 0 = free), never breaks the list
            notes.append(pkg + ": cost unknown (%s)" % e)
        rows.append(row)
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
    dsb = os.path.join(os.path.dirname(out), "islands.dsb")
    with open(dsb, "w", encoding="utf-8", newline="\n") as f:
        f.write(daedalus_dsb.write_dsb([r for r in old + rows if "x" in r and "y" in r]))
    return {"path": out, "dsb": dsb, "rows": rows, "kept": len(old), "notes": notes}
