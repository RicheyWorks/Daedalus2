# SPDX-License-Identifier: MIT
"""Read the contest islands (Richey 09:20: "make the island look good like in our build-an-island contest") as data:
for each team folder (AMF, DiskSaver, Pythagoras, ...) the actors it placed, grouped by mesh family, with the
island's footprint, so the detail pass can copy their density and mix instead of guessing.

    import daedalus_island_recipe as R
    R.recipes()          -> {team: {"actors": n, "radius_m": r, "families": {family: count}, "per_1000m2": {...}}}
    R.write()            -> Saved/Daedalus/island-recipes.json
"""
import collections
import json
import math
import os
import re

TEAMS = ("AMF", "BlenderBoss", "Buffffff", "Claude", "Codex", "DiskSaver", "Grok", "Hephaestus", "OddsReaper", "Prometheus", "Pythagoras", "YTM")
FAMILY = [  # (regex on the mesh/actor name, family)
    (r"Tree", "tree"), (r"Bush|Shrub", "bush"), (r"Grass|Sedge|Hay|Moss", "grass"), (r"Fern", "fern"),
    (r"Flower|Bloom", "flower"), (r"Mushroom", "mushroom"), (r"Crystal", "crystal"), (r"Rock|Boulder|Stone", "rock"),
    (r"Fence|Wall|Gate", "fence"), (r"House|Hut|Cabin|Bld_|Tower|Camp|Kennel|Shed|Barn", "building"),
    (r"Path|Road|Tile|Floor|Plank|Bridge", "path"), (r"Water|Pond|Lake|Sea", "water"), (r"Lamp|Light|Lantern|Torch", "light"),
    (r"Island|Ground|Terrain|Disc|Base", "ground"),
]


def family_of(name):
    for pat, fam in FAMILY:
        if re.search(pat, name, re.I):
            return fam
    return "other"


def recipes():
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_team = collections.defaultdict(list)
    for a in sub.get_all_level_actors():
        folder = str(a.get_folder_path())
        team = folder.split("/")[0] if folder else ""
        if team not in TEAMS:
            continue
        mesh = ""
        try:
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            if c and c.static_mesh:
                mesh = c.static_mesh.get_name()
        except Exception:
            pass
        loc = a.get_actor_location()
        by_team[team].append((mesh or a.get_actor_label(), loc.x, loc.y, loc.z, a.get_class().get_name()))
    out = {}
    for team, rows in by_team.items():
        xs = [r[1] for r in rows]
        ys = [r[2] for r in rows]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        rad = sorted(math.hypot(x - cx, y - cy) for x, y in zip(xs, ys))
        radius_m = rad[int(len(rad) * 0.95)] / 100.0 if rad else 0.0
        fams = collections.Counter(family_of(r[0]) for r in rows)
        meshes = collections.Counter(r[0] for r in rows)
        area = max(math.pi * radius_m * radius_m, 1.0)
        out[team] = {"actors": len(rows), "centre_cm": [round(cx), round(cy)], "radius_m": round(radius_m, 1),
                     "families": dict(fams), "per_1000m2": {f: round(1000.0 * n / area, 2) for f, n in fams.items()},
                     "top_meshes": meshes.most_common(15), "z_span_m": round((max(r[3] for r in rows) - min(r[3] for r in rows)) / 100.0, 1)}
    return out


def write():
    import unreal
    data = recipes()
    path = os.path.join(unreal.Paths.project_saved_dir(), "Daedalus", "island-recipes.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return path
