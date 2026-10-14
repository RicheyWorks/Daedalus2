# SPDX-License-Identifier: MIT
"""Bounded, additive first ground for the seven realms; no imports or gameplay changes.

Review ``plan(realm)`` headless, then in an existing editor use ``apply(realm)``.
Each call handles one realm and at most one 32-cell native terrain patch. Existing
labels without Owned:CodexBaseLayer are preserved, including hubs, kits, lands,
casts and arrival markers. WORLD-ZERO keeps its existing island ground.
``apply`` does not save packages; the live operator owns review and saving.
"""
import daedalus_land_grid as G
import daedalus_realm_ground as R

OWNER_TAG = "Owned:CodexBaseLayer"
REALMS = ("WORLD-ZERO", "GALLERY-CITY", "PARCELS", "BRICKS", "LABYRINTH", "PORTAL", "OCEAN")
ORIGINS = dict(R.ORIGINS)
ORIGINS.update({"PORTAL": (R.WZ[0] + R.STEP, R.WZ[1] + R.STEP),
                "OCEAN": (R.WZ[0] + R.STEP, R.WZ[1] - R.STEP)})
GROUND_Z = R.GROUND_Z
CUBE = R.CUBE
PLANE = "/Engine/BasicShapes/Plane.Plane"
WATER_MATERIAL = "/DaedalusLink/Ocean/Materials/M_OceanWater.M_OceanWater"
MAX_CELLS = 32
SPACING_M = 100.0  # Native component rejects spacing >100 m.
ROAD_WIDTH_CM = 2400.0
ROAD_THICK_CM = 200.0
GRID_MIN_M = (-G.HUB - 0.5) * G.PITCH_M
GRID_MAX_M = (G.SIDE - G.HUB - 0.5) * G.PITCH_M


def disposition(existing_tags=None):
    """Missing actor -> create; only an explicitly owned existing actor -> update."""
    if existing_tags is None:
        return "create"
    return "update" if OWNER_TAG in {str(t) for t in existing_tags} else "preserve"


def bounds(realm):
    x, y = ORIGINS[realm]
    return (x + GRID_MIN_M * 100, y + GRID_MIN_M * 100,
            x + GRID_MAX_M * 100, y + GRID_MAX_M * 100)


def _actor(label, kind, realm, location, scale=(1.0, 1.0, 1.0), **extra):
    spec = {"label": label, "kind": kind, "location_cm": tuple(location),
            "scale": tuple(scale), "tags": (OWNER_TAG, "Realm:" + realm, "BaseLayer"),
            "collision": kind != "marker", "yaw": 0.0}
    spec.update(extra)
    return spec


def _road(label, realm, start, end, top=GROUND_Z, width=ROAD_WIDTH_CM):
    """Axis-aligned solid Cube; endpoint overlap joins adjacent route pieces."""
    dx, dy = abs(end[0] - start[0]), abs(end[1] - start[1])
    if dx and dy:
        raise ValueError("road endpoints must be axis-aligned")
    return _actor(label, "cube", realm,
                  ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, top - ROAD_THICK_CM / 2),
                  ((dx + width) / 100, (dy + width) / 100, ROAD_THICK_CM / 100),
                  role="route", route_start_cm=tuple(start), route_end_cm=tuple(end), top_cm=top)


def _markers(realm):
    if realm != "WORLD-ZERO":
        return R.markers(ORIGINS[realm])
    # World Zero's documented 432 m footprint, rather than a new 768 m blanket.
    x, y = ORIGINS[realm]
    half = 21600.0
    return {"Spawn": (x, y - half * 0.3, GROUND_Z + 100, 90),
            "Gate": (x, y - half * 0.8 + 600, GROUND_Z + 100, 90),
            "Dock": (x + half * 0.8 - 600, y - half * 0.3, GROUND_Z + 100, 180),
            "SubDock": (x + half * 0.8 - 600, y + half * 0.3, GROUND_Z + 100, 180),
            "Mount": (x - half * 0.8 + 600, y, GROUND_Z + 100, 0)}


def plan(realm, cells=16, world_zero_routes=False):
    """Pure, bounded actor plan. Native XY scale covers the complete 25.6 km grid.

    Native Z stays unscaled: prairie hills remain +/-3.6 m; the ocean seabed
    remains -25..-65 m below water. Prairie terrain is lowered 3.6 m so it cannot
    bury the existing hub, plot slabs or kit at ground height. Roads remain at
    their existing top Z=5220 cm. Sampling y=0 maps exactly to the realm origin.
    """
    if realm not in REALMS:
        raise ValueError("unknown realm: %s" % realm)
    if isinstance(cells, bool) or not isinstance(cells, int) or not 1 <= cells <= MAX_CELLS:
        raise ValueError("cells must be an integer in 1..32")
    origin = ORIGINS[realm]
    box = bounds(realm)
    markers = _markers(realm)
    actors = []
    if realm != "WORLD-ZERO":
        span_m = G.SIDE * G.PITCH_M
        xy = span_m / (cells * SPACING_M)
        ocean = realm == "OCEAN"
        terrain_z = GROUND_Z - 100.0 if ocean else GROUND_Z - 360.0
        actors.append(_actor("BaseSurface_" + realm, "terrain", realm,
                             (box[0], box[1], terrain_z), (xy, xy, 1.0),
                             cells=cells, spacing_metres=SPACING_M,
                             sample_origin_metres=(GRID_MIN_M / xy, GRID_MIN_M / xy),
                             ocean=ocean, role="seabed" if ocean else "terrain"))
        if ocean:
            actors.append(_actor("BaseWater_" + realm, "plane", realm,
                                 ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, terrain_z),
                                 (span_m, span_m, 1.0), collision=False,
                                 material=WATER_MATERIAL, role="water"))
            actors.append(_actor("BaseHarbor_" + realm, "cube", realm,
                                 (origin[0], origin[1], GROUND_Z - ROAD_THICK_CM / 2),
                                 (128.0, 128.0, ROAD_THICK_CM / 100), role="harbor", top_cm=GROUND_Z))
        else:
            # Road endpoints stay inside the exact asymmetric grid boundaries.
            inset = ROAD_WIDTH_CM / 2
            actors.append(_road("BaseRoadEW_" + realm, realm,
                                (box[0] + inset, origin[1]), (box[2] - inset, origin[1])))
            actors.append(_road("BaseRoadNS_" + realm, realm,
                                (origin[0], box[1] + inset), (origin[0], box[3] - inset)))
    # Ocean's narrow harbor routes, or an opt-in World Zero affordance, never
    # fill the existing world with a slab. Modern routes meet the road cross.
    routes = realm != "WORLD-ZERO" or world_zero_routes
    if routes:
        for name, marker in markers.items():
            endpoint = marker[:2]
            elbow = (endpoint[0], origin[1])
            if realm == "OCEAN" or realm == "WORLD-ZERO":
                actors.append(_road("BaseRoute_%s_X_%s" % (name, realm), realm, origin, elbow))
            actors.append(_road("BaseRoute_%s_Y_%s" % (name, realm), realm, elbow, endpoint))
    for name, (x, y, z, yaw) in markers.items():
        actors.append(_actor(name + "_" + realm, "marker", realm, (x, y, z),
                             yaw=yaw, marker=name,
                             tags=(OWNER_TAG, "Realm:" + realm, "BaseLayer", name)))
    return {"realm": realm, "origin_cm": origin, "bounds_cm": box,
            "markers": markers, "actors": actors, "uses_existing_ground": realm == "WORLD-ZERO",
            "terrain_vertices": 0 if realm == "WORLD-ZERO" else (cells + 1) ** 2}


def _index(actors):
    out = {}
    for actor in actors:
        out.setdefault(actor.get_actor_label(), []).append(actor)
    return out


def apply(realm, cells=16, world_zero_routes=False, dry_run=False):
    """Apply one realm, ownership guarded. No destruction, asset writes or saving.

    Duplicate labels are preserved and reported as conflicts. Wrong-class owned
    actors are also preserved. Native assets/classes are preflighted before any
    mutation. Return the exact created/updated/preserved labels for live proof.
    """
    import unreal
    planned = plan(realm, cells, world_zero_routes)
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    have = _index(sub.get_all_level_actors())
    classes = {"cube": unreal.StaticMeshActor, "plane": unreal.StaticMeshActor,
               "marker": unreal.TargetPoint,
               "terrain": getattr(unreal, "DaedalusExplorationTerrain", None)}
    result = {"realm": realm, "created": [], "updated": [], "preserved": [], "conflicts": [],
              "terrain_vertices": planned["terrain_vertices"], "saved": False, "dry_run": dry_run}
    pending = []
    for spec in planned["actors"]:
        matches = have.get(spec["label"], [])
        if len(matches) > 1:
            result["conflicts"].append(spec["label"] + ": duplicate label")
            continue
        actor = matches[0] if matches else None
        action = disposition(actor.tags if actor is not None else None)
        if action == "preserve":
            result["preserved"].append(spec["label"])
        elif actor is not None and classes[spec["kind"]] is not None and not isinstance(actor, classes[spec["kind"]]):
            result["conflicts"].append(spec["label"] + ": owned actor has wrong class")
        else:
            pending.append((spec, actor, action))
    if dry_run:
        for spec, actor, action in pending:
            result["created" if action == "create" else "updated"].append(spec["label"])
        return result
    if any(spec["kind"] == "terrain" for spec, _, _ in pending):
        cls = classes["terrain"]
        if cls is None:
            raise RuntimeError("DaedalusExplorationTerrain is not installed; no actors changed")
    assets = {}
    for path in {CUBE if s["kind"] == "cube" else PLANE for s, _, _ in pending if s["kind"] in ("cube", "plane")}:
        asset = unreal.load_asset(path)
        if asset is None:
            raise RuntimeError("required mesh missing: " + path)
        assets[path] = asset
    for path in {s["material"] for s, _, _ in pending if s.get("material")}:
        asset = unreal.load_asset(path)
        if asset is None:
            raise RuntimeError("required material missing: " + path)
        assets[path] = asset
    for spec, actor, action in pending:
        cls = classes[spec["kind"]]
        if actor is not None and not isinstance(actor, cls):
            result["conflicts"].append(spec["label"] + ": owned actor has wrong class")
            continue
        if actor is not None and spec["kind"] == "terrain":
            # An earlier live patch may have 256 cells. Reduce it before any
            # transform/property change that can invoke OnConstruction again.
            actor.set_editor_property("cells", spec["cells"])
        location = unreal.Vector(*spec["location_cm"])
        rotation = unreal.Rotator(0.0, spec["yaw"], 0.0)
        if actor is None:
            actor = sub.spawn_actor_from_class(cls, location, rotation)
            if actor is None:
                raise RuntimeError("spawn failed: " + spec["label"])
        else:
            actor.set_actor_location(location, False, False)
            actor.set_actor_rotation(rotation, False)
        actor.set_actor_label(spec["label"])
        actor.set_folder_path("Realms/%s/BaseLayer" % realm)
        actor.tags = [unreal.Name(t) for t in spec["tags"]]
        actor.set_actor_scale3d(unreal.Vector(*spec["scale"]))
        if spec["kind"] in ("cube", "plane"):
            component = actor.static_mesh_component
            component.set_static_mesh(assets[CUBE if spec["kind"] == "cube" else PLANE])
            component.set_collision_profile_name("BlockAll" if spec["collision"] else "NoCollision")
            component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS if spec["collision"] else unreal.CollisionEnabled.NO_COLLISION)
            if spec.get("material"):
                component.set_material(0, assets[spec["material"]])
        elif spec["kind"] == "terrain":
            # Set cells first: subsequent property reconstructions stay bounded.
            actor.set_editor_property("cells", spec["cells"])
            actor.set_editor_property("spacing_metres", spec["spacing_metres"])
            actor.set_editor_property("sample_origin_metres", unreal.Vector2D(*spec["sample_origin_metres"]))
            actor.set_editor_property("ocean", spec["ocean"])
        result["created" if action == "create" else "updated"].append(spec["label"])
    return result
