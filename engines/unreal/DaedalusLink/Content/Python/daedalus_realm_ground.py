# SPDX-License-Identifier: MIT
"""Lay down a 3D realm's base layer (BASE-LAYER.md rows 1-3, 9-10): hub ground, spawn, gate landing, docks, the
environment kit standing on the ground, and the first rings of lands (Richey 2026-10-13: "get everything laid down
in each realm then polish").

    import daedalus_realm_ground as R
    R.import_kit("GALLERY-CITY", r"C:\\Users\\730ri\\Documents\\Codex\\2026-10-13\\gallery-buildout\\environment")
    R.lay("GALLERY-CITY")      # hub slab, markers, kit, lands (rings 1..6); idempotent by label
    R.report("GALLERY-CITY")

Realms share World Zero's persistent level at fixed origins 40 km apart (ORIGINS, cm): far enough that no realm's
25.6 km grid touches another, inside UE5's default 880 km world. Streaming by district (ADR-063) comes after the
material is down; everything a realm owns sits in folder Realms/<REALM>/... so it can be moved to sublevels later.
Pure parts (origins, the kit layout) are testable headless.
"""
import hashlib
import json
import os

import daedalus_land_grid as G

try:
    import unreal   # noqa: F401
    HAVE_UNREAL = True
except ImportError:
    HAVE_UNREAL = False

# realm origin = its hub cell centre, in world cm, relative to World Zero's hub (14850, -9500)
WZ = (14850.0, -9500.0)
STEP = 4000000.0    # 40 km
ORIGINS = {
    "WORLD-ZERO": WZ,
    "GALLERY-CITY": (WZ[0] + STEP, WZ[1]),          # east
    "PARCELS": (WZ[0] - STEP, WZ[1]),               # west
    "BRICKS": (WZ[0], WZ[1] + STEP),                # north
    "LABYRINTH": (WZ[0], WZ[1] - STEP),             # south
}
GROUND_Z = 5220.0        # World Zero's spawn height: every realm's hub floats at the same altitude
HUB_CELLS = 3            # the hub island is a 3x3 estate (768 m)
KIT_ROOT = "/Game/Daedalus/Art/Env"
STAMP = "daedalus_kit_sha256"
KIT_PITCH_CM = 2400.0    # the showcase grid: one prop every 24 m
KIT_COLS = 6
CUBE = "/Engine/BasicShapes/Cube.Cube"

# where the special props stand, as (east, north) fractions of the hub half-width; the rest fill the showcase grid
SPECIAL = {
    "RainbowFrame": (0.0, -0.8),       # gate landing, south edge, facing the plaza
    "AirlockEntry": (0.8, 0.3), "UnderwaterAirlock": (0.8, 0.3),
    "BoatDock": (0.8, -0.3),
    "DroneDock": (-0.8, 0.0), "Helipad": (-0.8, 0.0), "RepairBay": (-0.8, 0.0), "HangarFrame": (-0.8, 0.4),
    "ConcertPlatform": (0.0, 0.8),
    "QuestNoticeboard": (0.3, -0.5), "Noticeboard": (0.3, -0.5),
}


def kind(asset_id):
    """'FloorTile' from 'Prop_Gallery_FloorTile'."""
    return asset_id.split("_", 2)[-1]


def hub_half_cm(pitch_m=G.PITCH_M):
    return HUB_CELLS * pitch_m * 100.0 / 2.0


def hub_cells():
    """Deed numbers of the 3x3 hub estate (cells 49..51)."""
    r = HUB_CELLS // 2
    return {G.number(x, y) for x in range(G.HUB - r, G.HUB + r + 1) for y in range(G.HUB - r, G.HUB + r + 1)}


def layout(asset_ids, origin, ground=GROUND_Z):
    """{asset id: (x, y, z, yaw)} world cm for the kit: specials at their edge spots, the rest on a grid in the
    plaza's north-west quarter, 24 m apart, so every prop stands on the hub and nothing overlaps."""
    half = hub_half_cm()
    out = {}
    rest = []
    for a in sorted(asset_ids):
        k = kind(a)
        if k in SPECIAL:
            fx, fy = SPECIAL[k]
            out[a] = (origin[0] + fx * half, origin[1] + fy * half, ground, 180.0 if fy > 0 else 0.0)
        else:
            rest.append(a)
    x0 = origin[0] - half * 0.6
    y0 = origin[1] + half * 0.1
    for i, a in enumerate(rest):
        c, r = i % KIT_COLS, i // KIT_COLS
        out[a] = (x0 + c * KIT_PITCH_CM, y0 + r * KIT_PITCH_CM, ground, 0.0)
    return out


def markers(origin, ground=GROUND_Z):
    half = hub_half_cm()
    return {"Spawn": (origin[0], origin[1] - half * 0.3, ground + 100.0, 90.0),
            "Gate": (origin[0], origin[1] - half * 0.8 + 600.0, ground + 100.0, 90.0),
            "Dock": (origin[0] + half * 0.8 - 600.0, origin[1] - half * 0.3, ground + 100.0, 180.0),
            "SubDock": (origin[0] + half * 0.8 - 600.0, origin[1] + half * 0.3, ground + 100.0, 180.0),
            "Mount": (origin[0] - half * 0.8 + 600.0, origin[1], ground + 100.0, 0.0)}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plan_kit(folder):
    """[(id, glb, sha)] for every Prop_*.glb (manifest sha when present)."""
    manifest = {}
    mp = os.path.join(folder, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp, encoding="utf-8") as f:
                for a in json.load(f).get("assets", []):
                    manifest[a.get("id")] = a.get("sha256", "")
        except (ValueError, OSError):
            pass
    out = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".glb") and not name.startswith("Mob_"):
            aid = name[:-4]
            out.append((aid, os.path.join(folder, name), manifest.get(aid) or sha256(os.path.join(folder, name))))
    return out


# ---- editor side ----------------------------------------------------------------------------------------------

def _realm_dir(realm):
    return realm.replace("-", "")


def _mesh_path(realm, aid):
    return "%s/%s/%s/%s" % (KIT_ROOT, _realm_dir(realm), aid, aid)


def _find_mesh(dest):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for d in reg.get_assets_by_path(dest, recursive=True):
        if str(d.asset_class_path.asset_name) == "StaticMesh":
            return str(d.package_name) + "." + str(d.asset_name)
    return None


def import_kit(realm, folder, force=False):
    """Import the environment GLBs as StaticMeshes under /Game/Daedalus/Art/Env/<Realm>/<id>/. Idempotent by SHA."""
    summary = {"imported": [], "skipped": [], "failed": []}
    for aid, glb, sha in plan_kit(folder):
        dest = "%s/%s/%s" % (KIT_ROOT, _realm_dir(realm), aid)
        existing = _find_mesh(dest)
        if existing and not force:
            stamp = unreal.EditorAssetLibrary.get_metadata_tag(unreal.load_asset(existing), STAMP)
            if stamp == sha:
                summary["skipped"].append(aid)
                continue
        task = unreal.AssetImportTask()
        task.filename = glb
        task.destination_path = dest
        task.destination_name = aid
        task.automated = True
        task.replace_existing = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = _find_mesh(dest)
        if not mesh:
            summary["failed"].append(aid)
            continue
        unreal.EditorAssetLibrary.set_metadata_tag(unreal.load_asset(mesh), STAMP, sha)
        unreal.EditorAssetLibrary.save_asset(mesh, only_if_is_dirty=False)
        summary["imported"].append(aid)
    print("kit %s: %d imported, %d skipped, %d failed" % (realm, len(summary["imported"]), len(summary["skipped"]), len(summary["failed"])))
    return summary


def _kit_meshes(realm):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    out = {}
    for d in reg.get_assets_by_path("%s/%s" % (KIT_ROOT, _realm_dir(realm)), recursive=True):
        if str(d.asset_class_path.asset_name) == "StaticMesh":
            out[str(d.asset_name)] = str(d.package_name) + "." + str(d.asset_name)
    return out


def _labels():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return {a.get_actor_label(): a for a in sub.get_all_level_actors()}


def lay(realm, rings=6):
    """Hub slab + markers + kit + lands. Idempotent: an actor whose label exists is left alone."""
    import daedalus_plots as P
    if realm not in ORIGINS or realm == "WORLD-ZERO":
        raise ValueError("lay() is for the 3D realms other than World Zero: %s" % sorted(k for k in ORIGINS if k != "WORLD-ZERO"))
    origin = ORIGINS[realm]
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    have = _labels()
    folder = "Realms/%s" % realm
    tag = unreal.Name("Realm:%s" % realm)
    made = {"slab": 0, "markers": 0, "kit": 0, "kit_missing": []}
    half = hub_half_cm()
    # 1. the hub slab
    label = "Hub_%s" % realm
    if label not in have:
        cube = unreal.load_asset(CUBE)
        slab = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(origin[0], origin[1], GROUND_Z - 100.0))
        slab.static_mesh_component.set_static_mesh(cube)
        slab.set_actor_scale3d(unreal.Vector(half * 2 / 100.0, half * 2 / 100.0, 2.0))
        slab.set_actor_label(label)
        slab.set_folder_path(folder)
        slab.tags = [unreal.Name("Hub"), tag]
        made["slab"] = 1
    # 2. markers
    for name, (x, y, z, yaw) in markers(origin).items():
        label = "%s_%s" % (name, realm)
        if label in have:
            continue
        m = sub.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(x, y, z), unreal.Rotator(0.0, yaw, 0.0))
        m.set_actor_label(label)
        m.set_folder_path(folder + "/Markers")
        m.tags = [unreal.Name(name), tag]
        made["markers"] += 1
    # 3. the kit on the ground
    meshes = _kit_meshes(realm)
    for aid, (x, y, z, yaw) in layout(meshes.keys(), origin).items():
        label = "Kit_%s" % aid
        if label in have:
            continue
        a = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0.0, yaw, 0.0))
        a.static_mesh_component.set_static_mesh(unreal.load_asset(meshes[aid]))
        a.set_actor_label(label)
        a.set_folder_path(folder + "/Kit")
        a.tags = [unreal.Name("Kit"), unreal.Name(kind(aid)), tag]
        made["kit"] += 1
    if not meshes:
        made["kit_missing"] = ["no meshes under %s/%s: run import_kit first" % (KIT_ROOT, _realm_dir(realm))]
    # 4. lands around the hub
    lands = P.apply(rings, realm=realm, hub_cm=origin, ground=GROUND_Z, hub_cells=hub_cells())
    __import__('daedalus_plots').save_world()
    return {"realm": realm, "origin": origin, "made": made, "lands": {k: lands[k] for k in ("free_cells", "made", "skipped")}}


CASTS = {"GALLERY-CITY": "gallery-city", "PARCELS": "parcels", "BRICKS": "bricks", "LABYRINTH": "labyrinth", "WORLD-ZERO": "world-zero"}
CAST_RADIUS_CM = 6000.0


def cast_roles(dcs_text):
    """The 'who' names of a .dcs, in script order."""
    return [l[4:].strip() for l in dcs_text.splitlines() if l.startswith("who ")]


def cast_ring(n, centre, ground=GROUND_Z, radius=CAST_RADIUS_CM):
    """n points on a circle round the spawn, each facing the centre: (x, y, z, yaw)."""
    import math
    out = []
    for i in range(n):
        a = 2 * math.pi * i / max(n, 1)
        x, y = centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)
        yaw = math.degrees(math.atan2(centre[1] - y, centre[0] - x))
        out.append((x, y, ground, yaw))
    return out


def _dcs_path(catalog):
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_plugins_dir()), "DaedalusLink", "Content", "Casts", catalog + ".dcs")


def lay_cast(realm):
    """One ADaedalusTalker per 'who' of the realm's .dcs, in a ring round the spawn marker, bound to its imported
    art when the art is there (Rebind). Idempotent by label."""
    catalog = CASTS[realm]
    with open(_dcs_path(catalog), encoding="utf-8") as f:
        roles = cast_roles(f.read())
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    have = _labels()
    if realm == "WORLD-ZERO":   # the hub has no Spawn marker: the cross-realm NPCs ring the PlayerStart
        ps = next((a for a in sub.get_all_level_actors() if a.get_class().get_name() == "PlayerStart"), None)
        l = ps.get_actor_location() if ps else unreal.Vector(ORIGINS[realm][0], ORIGINS[realm][1], GROUND_Z + 100.0)
        centre = (l.x, l.y, l.z - 100.0, 0.0)
    else:
        centre = markers(ORIGINS[realm])["Spawn"]
    made, bound, unbound = 0, [], []
    for who, (x, y, z, yaw) in zip(roles, cast_ring(len(roles), centre, ground=centre[2], radius=CAST_RADIUS_CM if realm != "WORLD-ZERO" else 2500.0)):
        label = "Talker_%s_%s" % (realm, "".join(w[:1].upper() + w[1:] for w in "".join(c if c.isalnum() else " " for c in who).split()))
        if label in have:
            t = have[label]
        else:
            t = sub.spawn_actor_from_class(unreal.DaedalusTalker, unreal.Vector(x, y, z), unreal.Rotator(0.0, yaw, 0.0))
            t.set_editor_property("cast", catalog)
            t.set_editor_property("who", who)
            t.set_actor_label(label)
            t.set_folder_path("Realms/%s/Cast" % realm)
            t.tags = [unreal.Name("Talker"), unreal.Name("Realm:%s" % realm)]
            made += 1
        (bound if t.rebind() else unbound).append(t.art_id())
    __import__('daedalus_plots').save_world()
    return {"realm": realm, "roles": len(roles), "made": made, "bound": len(bound), "unbound": unbound}


CREATURE_ROOT = "/Game/Daedalus/Art/Creatures"
CREATURE_RADIUS_CM = 11000.0


CREATURE_PREFIX = {"GALLERY-CITY": "Mob_Gallery_", "PARCELS": "Mob_Parcels_", "BRICKS": "Mob_Bricks_", "LABYRINTH": "Mob_Lab_"}


def lay_creatures(realm, folder):
    """DO NOT run this from one bridge call for a whole folder: 22 imports in one call blocked the game thread and
    the GPU watchdog killed the editor (2026-10-13 22:19). Use tools/unreal_play/import_cast.py <folder>
    --root /Game/Daedalus/Art/Creatures --place REALM, which imports one GLB per call and then place_creatures()."""
    raise RuntimeError("lay_creatures is retired: run tools/unreal_play/import_cast.py %s --root %s --place %s" % (folder, CREATURE_ROOT, realm))


def place_creatures(realm):
    """Stand every imported creature of the realm (by id prefix under /Game/Daedalus/Art/Creatures) in an outer
    ring round the spawn playing its Idle clip, as a SkeletalMeshActor labelled Creature_<Id>. Encounters spawn the
    live ones; these are the realm's bestiary, laid down. Idempotent by label."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    pre = CREATURE_PREFIX[realm]
    ids = sorted({str(d.package_path).split("/")[5] for d in reg.get_assets_by_path(CREATURE_ROOT, recursive=True)
                  if len(str(d.package_path).split("/")) > 5 and str(d.package_path).split("/")[5].startswith(pre)})
    s = {"imported": [], "skipped": ids, "failed": []}
    centre = markers(ORIGINS[realm])["Spawn"]
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    have = _labels()
    made, no_mesh = 0, []
    for aid, (x, y, z, yaw) in zip(ids, cast_ring(len(ids), centre, radius=CREATURE_RADIUS_CM)):
        label = "Creature_%s" % aid
        if label in have:
            continue
        mesh, idle = None, None
        for d in reg.get_assets_by_path("%s/%s" % (CREATURE_ROOT, aid), recursive=True):
            cls = str(d.asset_class_path.asset_name)
            path = str(d.package_name) + "." + str(d.asset_name)
            if cls == "SkeletalMesh" and not mesh:
                mesh = path
            if cls == "AnimSequence" and (idle is None or "Idle" in str(d.asset_name)):
                idle = path
        if not mesh:
            no_mesh.append(aid)
            continue
        a = sub.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0.0, yaw, 0.0))
        a.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset(mesh))
        if idle:
            c = a.skeletal_mesh_component
            c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            c.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=unreal.load_asset(idle), saved_looping=True, saved_playing=True))
        a.set_actor_label(label)
        a.set_folder_path("Realms/%s/Creatures" % realm)
        a.tags = [unreal.Name("Creature"), unreal.Name("Realm:%s" % realm)]
        made += 1
    __import__('daedalus_plots').save_world()
    return {"realm": realm, "imported": len(s["imported"]), "skipped": len(s["skipped"]), "failed": s["failed"], "placed": made, "no_mesh": no_mesh}


PORTALS = {   # marker -> (Target, Via, Detail) for a 3D realm's crossings; the hub's four gates point outward
    "Gate": ("WORLD-ZERO", "gate", ""),
    "Dock": ("OCEAN", "dock", "boat:{realm_lower}-dock"),
    "SubDock": ("OCEAN", "dock", "sub:{realm_lower}-airlock"),
}
HUB_GATES = {"GALLERY-CITY": (1.0, 0.0), "PARCELS": (-1.0, 0.0), "BRICKS": (0.0, 1.0), "LABYRINTH": (0.0, -1.0)}   # east/west/north/south of the PlayerStart


def portal_plan(realm):
    """[(label, target, via, detail, (x, y, z, yaw))]: one walk-in portal per marker (daedalus_realm_ground markers),
    or, for World Zero, four gates 40 m from the spawn pointing at the four realms. Pure."""
    out = []
    if realm == "WORLD-ZERO":
        for to, (ex, ny) in HUB_GATES.items():
            out.append(("Portal_WORLD-ZERO_to_%s" % to, to, "gate", "", (ex * 4000.0, ny * 4000.0, 0.0, 0.0)))
        return out
    m = markers(ORIGINS[realm])
    for name, (target, via, detail) in PORTALS.items():
        if name in m:
            x, y, z, yaw = m[name]
            out.append(("Portal_%s_%s" % (realm, name), target, via, detail.format(realm_lower=realm.lower()), (x, y, z, yaw)))
    return out


def lay_portals(realm):
    """Spawn ADaedalusRealmPortal at each marker (idempotent by label). World Zero's are relative to the PlayerStart."""
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    have = _labels()
    base = (0.0, 0.0, 0.0)
    if realm == "WORLD-ZERO":
        ps = next((a for a in sub.get_all_level_actors() if a.get_class().get_name() == "PlayerStart"), None)
        l = ps.get_actor_location() if ps else unreal.Vector(ORIGINS[realm][0], ORIGINS[realm][1], GROUND_Z + 100.0)
        base = (l.x, l.y, l.z - 100.0)
    made = 0
    for label, target, via, detail, (x, y, z, yaw) in portal_plan(realm):
        if label in have:
            continue
        a = sub.spawn_actor_from_class(unreal.DaedalusRealmPortal, unreal.Vector(base[0] + x, base[1] + y, base[2] + z + 250.0), unreal.Rotator(0.0, yaw, 0.0))
        a.set_editor_property("target", target)
        a.set_editor_property("via", via)
        a.set_editor_property("detail", detail)
        a.set_actor_label(label)
        a.set_folder_path("Realms/%s/Portals" % realm if realm != "WORLD-ZERO" else "Daedalus/Portals")
        a.tags = [unreal.Name("Portal"), unreal.Name("Realm:%s" % realm)]
        made += 1
    __import__('daedalus_plots').save_world()
    return {"realm": realm, "made": made, "portals": len(portal_plan(realm))}


def lay_cast_steps(realms):
    """One realm per editor tick: lay_cast for each (daedalus.steps shape)."""
    out = {}
    for r in realms:
        if r in CASTS:
            out[r] = lay_cast(r)
            yield "%s cast: %s" % (r, out[r])
    return out


def lay_portals_steps(realms):
    out = {}
    for r in realms:
        out[r] = lay_portals(r)
        yield "%s portals: %s" % (r, out[r])
    return out


def report(realm):
    import daedalus_plots as P
    have = _labels()
    tag = "Realm:%s" % realm
    mine = [l for l, a in have.items() if any(str(t) == tag for t in a.tags)]
    return {"realm": realm, "actors": len(mine), "hub": "Hub_%s" % realm in have,
            "markers": sorted(l for l in mine if l.endswith("_" + realm) and not l.startswith("Hub_")),
            "kit": sum(1 for l in mine if l.startswith("Kit_")), "cast": sum(1 for l in mine if l.startswith("Talker_")),
            "creatures": sum(1 for l in mine if l.startswith("Creature_")), "portals": sum(1 for l in mine if l.startswith("Portal_")),
            "lands": P.report(realm)}
