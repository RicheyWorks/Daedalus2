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
    """UE 5.8 Python exposes neither World.streaming_levels nor get_streaming_levels(); the loaded ULevels come
    from EditorLevelUtils.get_levels and a ULevelStreaming by package from GameplayStatics.get_streaming_level."""
    import unreal
    out = []
    for lv in unreal.EditorLevelUtils.get_levels(world):
        pkg = str(lv.get_outermost().get_name())
        sl = unreal.GameplayStatics.get_streaming_level(world, pkg)
        if sl is not None:
            out.append(sl)
    return out


def _sublevel(world, pkg, create=True):
    """The ULevelStreaming for pkg, created (Dynamic) when missing."""
    import unreal
    sl = unreal.GameplayStatics.get_streaming_level(world, pkg)
    if sl is not None:
        return sl
    if not create:
        return None
    sl = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, pkg, False)
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


def district_cells(d):
    """The 100 cell numbers of district d (0..99), in spiral order."""
    import daedalus_land_grid as G
    return sorted(G.number(x, y) for x in range(10 * (d % 10), 10 * (d % 10) + 10) for y in range(10 * (d // 10), 10 * (d // 10) + 10))


GROUND_M = 2560.0      # one district: 10 cells x 256 m
GROUND_THICK_M = 4.0


def ground_label(realm, d):
    return "Ground_%s_D%02d" % (realm.replace("-", ""), d)


def lay_ground(realm, d, sub=None, cube=None, labels=None):
    """One ground slab under a whole district (Richey 23:53: "fix all the falling through the floor stuff. add
    ground"): 2.56 km square, 4 m thick, its top 1 m under the plots' tops, so the 164 m gaps between 92 m plots
    are floor, not sky. Idempotent by label. Returns the actor or None when it exists."""
    import unreal
    import daedalus_land_grid as G
    import daedalus_plots as P
    import daedalus_realm_ground as R
    sub = sub or unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube = cube or unreal.load_asset(P.CUBE)
    label = ground_label(realm, d)
    if label in (labels if labels is not None else P._labels_cache(sub)):
        return None
    origin = R.ORIGINS[realm]
    # the district's centre: cells 10*(d%10)..+9 east, 10*(d//10)..+9 north, cell centres at (x-HUB)*pitch
    cx = (10 * (d % 10) + 4.5 - G.HUB) * G.PITCH_M * 100.0 + origin[0]
    cy = (10 * (d // 10) + 4.5 - G.HUB) * G.PITCH_M * 100.0 + origin[1]
    top = R.GROUND_Z - 100.0            # plots sit at GROUND_Z with a 2 m slab whose top is GROUND_Z
    z = top - GROUND_THICK_M * 50.0
    a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cx, cy, z))
    a.static_mesh_component.set_static_mesh(cube)
    a.set_actor_scale3d(unreal.Vector(GROUND_M, GROUND_M, GROUND_THICK_M))
    a.set_actor_label(label)
    a.set_folder_path("Realms/%s/Ground" % realm if realm != "WORLD-ZERO" else "Daedalus/Ground")
    a.tags = [unreal.Name("Ground"), unreal.Name("Realm:%s" % realm), unreal.Name("District:%d" % d)]
    return a


def lay_ground_steps(realm, districts):
    """Ground under existing districts (the hub rings laid before ground existed): one per tick, into the
    district's sublevel when it exists, else the persistent level."""
    import unreal
    import daedalus_plots as P
    world = _world()
    made = 0
    for d in districts:
        a = lay_ground(realm, d)
        if a is not None:
            sl = _sublevel(world, "%s/%s/D%02d" % (ROOT, realm_dir(realm), d), create=False)
            if sl is not None:
                unreal.EditorLevelUtils.move_actors_to_level([a], sl, False, False)
                lv = sl.get_loaded_level()
                if lv is not None:
                    P.save_packages_proven([lv.get_outermost()])
            made += 1
        yield "%s D%02d ground: %s" % (realm, d, "laid" if a is not None else "exists")
    P.save_world()
    return {"realm": realm, "ground": made}


def lay_district_steps(realm, districts, taken=frozenset(), save_every=10, sublevels=False):
    """Lay EVERY free cell of each district as ONE instanced-mesh actor (Lands_<Realm>_D<dd>: 100 plot instances
    of the cube, tagged District:<d>, instance i = district_cells(d)[i]) plus the district's ground slab, straight
    into the district's streamed sublevel; sublevels are saved every `save_every` districts. 23:56 Richey: "I need
    you to be fast": 100 plot actors + 100 signs + a save per district was 6.5 s each; one actor per district is
    ~0.3 s. Rings 1..6 keep their labelled Land_ actors (the registry sync reconciles those by label).
    `taken`: cell numbers to skip. Idempotent by label. Yields a line per district."""
    import unreal
    import daedalus_land_grid as G
    import daedalus_plots as P
    import daedalus_realm_ground as R
    world = _world()
    origin = R.ORIGINS[realm]
    ground = R.GROUND_Z
    have = P._labels_cache()
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube = unreal.load_asset(P.CUBE)
    pre = P._prefix(realm)
    total = 0
    pending = []
    labels = P._labels_cache(sub)   # scanned ONCE (00:05: a scan per district plus a sublevel create + move per
    for d in districts:             # district made each step ~60 s; one instanced actor in the persistent level is ~0.1 s)
        made = []
        g = lay_ground(realm, d, sub=sub, cube=cube, labels=labels)
        if g is not None:
            made.append(g)
        label = "Lands_%s_D%02d" % (realm.replace("-", ""), d)
        n_inst = 0
        if label not in labels:
            cells = [n for n in district_cells(d) if n not in taken and ("%s%d" % (pre, n)) not in have]
            if cells:
                a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(origin[0], origin[1], ground))
                a.static_mesh_component.set_visibility(False)   # the root is an empty anchor; the plots are instances
                # AddComponentByClass registers and attaches (UE Python has no register_component); the instances
                # are world-space transforms, so the anchor's own location does not matter.
                ism = a.add_component_by_class(unreal.InstancedStaticMeshComponent, False, unreal.Transform(), False)
                ism.set_static_mesh(cube)
                ism.set_mobility(unreal.ComponentMobility.STATIC)
                a.finish_adding_component(ism)
                ts = []
                for n in cells:
                    x, y = G.cell(n)
                    ts.append(unreal.Transform(unreal.Vector(origin[0] + (x - G.HUB) * G.PITCH_M * 100.0, origin[1] + (y - G.HUB) * G.PITCH_M * 100.0, ground - P.SLAB_M * 50.0),
                                               unreal.Rotator(0.0, 0.0, 0.0), unreal.Vector(P.LAND_M, P.LAND_M, P.SLAB_M)))
                ism.add_instances(ts, False, True)
                a.set_actor_label(label)
                a.set_folder_path("Realms/%s/Lands" % realm)
                a.tags = [unreal.Name("Lands"), unreal.Name("Realm:%s" % realm), unreal.Name("District:%d" % d), unreal.Name("Cells:%s" % ",".join(str(c) for c in cells))]
                made.append(a)
                n_inst = len(cells)
        if made and sublevels:   # streaming comes later, district by district, once the map is down
            sl = _sublevel(world, "%s/%s/D%02d" % (ROOT, realm_dir(realm), d))
            unreal.EditorLevelUtils.move_actors_to_level(made, sl, False, False)
            lv = sl.get_loaded_level()
            if lv is not None:
                pending.append(lv.get_outermost())
        total += n_inst
        if len(pending) >= save_every:
            P.save_packages_proven(pending)
            pending = []
        yield "%s D%02d: %d plots as one actor%s" % (realm, d, n_inst, " + ground" if g is not None else "")
    if pending:
        P.save_packages_proven(pending)
    P.save_world()
    if sublevels:
        import daedalus_islands
        daedalus_islands.write(prefixes=[ROOT + "/" + realm_dir(realm)])
        yield "islands.json updated"
    return {"realm": realm, "districts": len(list(districts)), "plots": total}


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
