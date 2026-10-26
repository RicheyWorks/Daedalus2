# SPDX-License-Identifier: MIT
"""Bring a team island to life: herds of DaedalusCritter (ADR-055) placed by the island's own zones.

Richey (2026-10-13): "groks team built a bunch of islands they should be populated with animals eco system etc".

An island built of static meshes already names its zones in its outliner folders (pen_cattle, meadow, pond, ...).
A plan maps each zone folder to the animals that belong there; every herd is placed on real ground inside that
zone (traced from above), and leashed so pen stock stays near its pen while wild animals roam.

    import daedalus_populate as P
    P.plan(P.GROK_ARKISLE)     # dry run: zones found, ground hits, where each animal goes
    P.apply(P.GROK_ARKISLE)    # spawn into the island's level, folder <root>/Life, tag unreal-team; save that level
    P.remove(P.GROK_ARKISLE)   # take back exactly what apply placed (by tag + folder)

Placement math (zones, spreading, leash) is pure and tested by test_daedalus_populate.py.
"""
import math
import random

TAG = "unreal-team-life"

# (zone folder suffix, [(species, count)], leash cm). Pens: stock stays home; wild: roams the island.
GROK_ARKISLE = {
    "level": "ArkDock_2hot2trot",
    "root": "Grok/ArkIsle",
    "seed": 2026,
    "zones": [
        ("pen_cattle", [("Mob_Cow", 5)], 1500.0),
        ("pen_pigs", [("Mob_Pig", 5)], 1500.0),
        ("pen_stable", [("Mob_Horse", 4)], 1800.0),
        ("pen_sheep_goats", [("Mob_Sheep", 4), ("Mob_Goat", 3)], 1500.0),
        ("pen_poultry", [("Mob_Chicken", 6), ("Mob_Duck", 2)], 1200.0),
        ("meadow", [("Mob_Hare", 4), ("Mob_Marmot", 3), ("Mob_Fox", 1)], 5000.0),
        ("grove", [("Mob_Squirrel", 4), ("Mob_Fox", 1)], 4000.0),
        ("pond", [("Mob_Duck", 4)], 2500.0),
        ("shoreline", [("Mob_Crab", 4), ("Mob_Lizard", 2)], 3000.0),
    ],
}


def spread(center, extent, count, rng, margin=0.15):
    """count points inside the zone box (centre, half-extent), kept off its edges by margin, on a jittered ring
    so a herd stands together without stacking."""
    cx, cy = center
    ex, ey = extent
    rx, ry = max(ex * (1 - margin), 50.0), max(ey * (1 - margin), 50.0)
    out = []
    for i in range(count):
        a = 2 * math.pi * i / max(1, count) + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.25, 0.85)
        out.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    return out


def zone_box(points):
    """points: [(x, y, ex, ey)] of a zone's actors -> ((cx, cy), (half x, half y))."""
    x0 = min(p[0] - p[2] for p in points)
    x1 = max(p[0] + p[2] for p in points)
    y0 = min(p[1] - p[3] for p in points)
    y1 = max(p[1] + p[3] for p in points)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0), ((x1 - x0) / 2.0, (y1 - y0) / 2.0)


# ---- editor side ----------------------------------------------------------------------------------------------

def _zones(spec):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    zones = {}
    for a in sub.get_all_level_actors():
        if a.get_level().get_outer().get_name() != spec["level"]:
            continue
        f = str(a.get_folder_path())
        if not f.startswith(spec["root"] + "/"):
            continue
        z = f[len(spec["root"]) + 1:].split("/")[0]
        o, e = a.get_actor_bounds(False)
        if e.x > 20000 or e.y > 20000:
            continue
        zones.setdefault(z, []).append((o.x, o.y, max(e.x, 50.0), max(e.y, 50.0), o.z + e.z))
    return zones


def _ground(x, y, top):
    """The walkable surface under (x, y): first world-static hit going down. None over water or the void."""
    import unreal
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, top + 2000.0), unreal.Vector(x, y, top - 20000.0),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()
    blocking, loc, normal, actor = t[0], t[4], t[6], t[9]
    if not blocking or normal.z < 0.7:
        return None
    name = actor.get_actor_label().lower() if actor else ""
    if "sea" in name or "water" in name or "pond_water" in name:
        return None
    return loc.z


def plan(spec):
    rng = random.Random(spec["seed"])
    zones = _zones(spec)
    rows, missing = [], []
    for zone, herd, leash in spec["zones"]:
        pts = zones.get(zone)
        if not pts:
            missing.append(zone)
            continue
        (cx, cy), (ex, ey) = zone_box([p[:4] for p in pts])
        top = max(p[4] for p in pts)
        for species, count in herd:
            for (x, y) in spread((cx, cy), (ex, ey), count, rng):
                z = _ground(x, y, top)
                rows.append({"zone": zone, "species": species, "x": round(x), "y": round(y),
                             "z": None if z is None else round(z), "leash": leash})
    return {"zones_found": sorted(zones), "missing": missing, "animals": rows,
            "placeable": sum(1 for r in rows if r["z"] is not None)}


def apply(spec):
    import unreal
    p = plan(spec)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.set_current_level_by_name(spec["level"])
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    placed = 0
    try:
        for i, r in enumerate(p["animals"]):
            if r["z"] is None:
                continue
            c = eas.spawn_actor_from_class(unreal.DaedalusCritter, unreal.Vector(r["x"], r["y"], r["z"] + 60.0),
                                           unreal.Rotator(0, 0, (i * 47) % 360))
            if not c:
                continue
            c.tags = [TAG]
            c.set_folder_path(spec["root"] + "/Life/" + r["zone"])
            c.set_actor_label("Life_%s_%s_%02d" % (r["zone"], r["species"].replace("Mob_", ""), i))
            c.set_editor_property("species", r["species"])
            c.set_editor_property("seed", spec["seed"] + i)
            c.set_editor_property("range", r["leash"])
            placed += 1
    finally:
        les.set_current_level_by_name("DaedalusWorld")
    _save(spec["level"])
    return {"placed": placed, "skipped": len(p["animals"]) - placed, "missing_zones": p["missing"]}


def remove(spec):
    import unreal
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gone = 0
    for a in eas.get_all_level_actors():
        if (a.get_level().get_outer().get_name() == spec["level"] and TAG in [str(t) for t in a.tags]
                and str(a.get_folder_path()).startswith(spec["root"] + "/Life")):
            eas.destroy_actor(a)
            gone += 1
    _save(spec["level"])
    return {"removed": gone}


def _save(level):
    import unreal
    pk = [x for x in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() if x.get_name().endswith("/" + level)]
    if pk:
        unreal.EditorLoadingAndSavingUtils.save_packages(pk, True)
