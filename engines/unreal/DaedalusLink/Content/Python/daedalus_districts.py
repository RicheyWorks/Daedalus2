# SPDX-License-Identifier: MIT
"""District sublevels (ADR-063/065): the material a realm lays down is moved out of the persistent level into one
Dynamic streaming sublevel per district, so UDaedalusStreamer (ADR-064, islands.json) loads only the districts near
the player. This is what lets rings 7..49 (10,000 lands a realm) exist without the editor or RAM paying for all
of them at once.

    import daedalus_districts as D
    D.plan("GALLERY-CITY")        # {district: {"package": ..., "actors": n, "exists": bool}}
    D.apply("GALLERY-CITY")       # create missing sublevels, move the district's actors in, save, list in islands.json
    D.steps("GALLERY-CITY")       # the same as a generator for daedalus.steps (one district per editor tick)

What goes where: actors tagged Realm:<R> and District:<d> (the lands) go to /Game/Daedalus/Realms/<Realm>/D<dd>;
the hub, markers, kit, talkers and creatures (tagged Realm:<R> without District:) go to .../<Realm>_Hub. World
Zero's hub island stays in the persistent level; its plots stream like any realm's. Idempotent: an actor already
in its sublevel is skipped. The pure part (which actor belongs to which package) is testable headless.
"""
import os

ROOT = "/Game/Daedalus/Realms"


def realm_dir(realm):
    return realm.replace("-", "")


def package_for(realm, tags):
    """The sublevel package an actor with these tags belongs to, or None for an actor that stays where it is."""
    tags = [str(t) for t in tags]
    if ("Realm:%s" % realm) not in tags:
        return None
    for t in tags:
        if t.startswith("District:"):
            return "%s/%s/D%02d" % (ROOT, realm_dir(realm), int(t.split(":")[1]))
    if "Land" in tags:
        return None   # a land without a district number is malformed: leave it, report it
    return "%s/%s/%s_Hub" % (ROOT, realm_dir(realm), realm_dir(realm))


def group(realm, actors):
    """actors: iterable of (label, tags, current package). Returns {package: [labels to move]}, {skipped reason: n}."""
    moves, skipped = {}, {}
    for label, tags, current in actors:
        pkg = package_for(realm, tags)
        if pkg is None:
            skipped["not this realm or malformed"] = skipped.get("not this realm or malformed", 0) + 1
        elif pkg == current:
            skipped["already there"] = skipped.get("already there", 0) + 1
        else:
            moves.setdefault(pkg, []).append(label)
    return moves, skipped


# ---- editor side ----------------------------------------------------------------------------------------------

def _world():
    import unreal
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _streaming(world):
    try:
        return list(world.get_editor_property("streaming_levels") or [])
    except Exception:
        return list(world.get_streaming_levels())


def _sublevel(world, pkg, create=True):
    """The ULevelStreaming for pkg, created (Dynamic) when missing."""
    import unreal
    for sl in _streaming(world):
        if str(sl.get_world_asset_package_name()) == pkg:
            return sl
    if not create:
        return None
    sl = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, pkg, False, False)
    if sl is None:
        raise RuntimeError("could not create streaming level %s" % pkg)
    return sl


def _actors(realm):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    tag = "Realm:%s" % realm
    out = []
    for a in sub.get_all_level_actors():
        if any(str(t) == tag for t in a.tags):
            out.append(a)
    return out


def plan(realm):
    rows = [(a.get_actor_label(), a.tags, str(a.get_level().get_outermost().get_name())) for a in _actors(realm)]
    moves, skipped = group(realm, rows)
    world = _world()
    have = {str(sl.get_world_asset_package_name()) for sl in _streaming(world)}
    return {"realm": realm, "moves": {p: len(v) for p, v in sorted(moves.items())}, "skipped": skipped,
            "exists": {p: (p in have) for p in sorted(moves)}}


def steps(realm):
    """One district per editor tick: create the sublevel, move its actors, save the sublevel; finally save the
    persistent level and list the sublevels for the streamer. Yields a line per district."""
    import unreal
    import daedalus_plots
    import daedalus_islands
    world = _world()
    actors = {a.get_actor_label(): a for a in _actors(realm)}
    rows = [(l, a.tags, str(a.get_level().get_outermost().get_name())) for l, a in actors.items()]
    moves, skipped = group(realm, rows)
    moved_total = 0
    for pkg in sorted(moves):
        sl = _sublevel(world, pkg)
        batch = [actors[l] for l in moves[pkg]]
        # attached signs ride with their slab: move roots only, UE moves attachments
        roots = [a for a in batch if a.get_attach_parent_actor() is None]
        n = unreal.EditorLevelUtils.move_actors_to_level(roots, sl, False, False)
        moved_total += int(n)
        level = sl.get_loaded_level()
        if level is not None:
            daedalus_plots.save_packages_proven([level.get_outermost()])
        yield "%s: moved %d (roots %d) -> %s" % (realm, len(batch), int(n), pkg.split("/")[-1])
    daedalus_plots.save_world()
    daedalus_islands.write(prefixes=[ROOT + "/" + realm_dir(realm)])
    yield "islands.json updated"
    return {"realm": realm, "sublevels": len(moves), "moved": moved_total, "skipped": skipped}


def apply(realm):
    gen = steps(realm)
    lines = []
    try:
        while True:
            lines.append(next(gen))
    except StopIteration as stop:
        out = stop.value
    out["lines"] = lines
    return out
