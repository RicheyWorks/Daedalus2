# SPDX-License-Identifier: MIT
"""Point the camera at a Daedalus world, so nobody has to go looking for it (ADR-032).

The world's islands float far from the origin, so a fresh level opens onto empty sky. This module works out
where the world is from the actors in its "Daedalus/<world id>" folder, and then:
  * view_point(bounds): a spot back, up and to the side of the world, looking at its middle (pure maths,
    tested outside Unreal);
  * place_player_start(world_id): a PlayerStart at that spot, so Play begins looking at the islands;
  * frame_editor(world_id): moves the editor's viewport camera there.
init_unreal.py calls frame_editor once the Daedalus level is open in the editor.
"""

import math

try:
    import unreal  # present only inside the Unreal editor
except ImportError:  # pragma: no cover - tests import the maths only
    unreal = None

FOLDER = "Daedalus/"
START_LABEL = "Daedalus View"


def view_point(lo, hi):
    """Camera location and (pitch, yaw) that take in the box lo..hi (Unreal units, Z up).

    The camera sits south-west of the box, above it, far enough back that the box's widest side fits a 90°
    field of view with some sky around it. Returns ((x, y, z), (pitch, yaw)).
    """
    cx, cy, cz = [(a + b) / 2.0 for a, b in zip(lo, hi)]
    size = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1000.0)
    dist = size * 0.9
    # From the south-west, 35° up: a three-quarter view that shows the islands' sides and tops.
    yaw = 45.0
    pitch = -35.0
    horiz = dist * math.cos(math.radians(-pitch))
    x = cx - horiz * math.cos(math.radians(yaw))
    y = cy - horiz * math.sin(math.radians(yaw))
    z = cz + dist * math.sin(math.radians(-pitch))
    return (x, y, z), (pitch, yaw)


def world_bounds(world_id):
    """The box around every actor in the world's folder, or None if there is none."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    lo, hi = None, None
    for a in actors:
        if str(a.get_folder_path()) != FOLDER + world_id or isinstance(a, unreal.PlayerStart):
            continue
        origin, extent = a.get_actor_bounds(False)
        if extent.x == 0 and extent.y == 0 and extent.z == 0:
            continue  # the live actor has no geometry until Play
        a_lo = (origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
        a_hi = (origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)
        lo = a_lo if lo is None else tuple(min(p, q) for p, q in zip(lo, a_lo))
        hi = a_hi if hi is None else tuple(max(p, q) for p, q in zip(hi, a_hi))
    return (lo, hi) if lo is not None else None


def daedalus_worlds():
    """The world ids in the open level: Daedalus/<id> folders that hold chunk meshes.

    Other Daedalus/ folders (Atmosphere, Lamps, Show, Sky...) are scenery, not worlds; counting them made the
    hero look for islands in "Atmosphere" (seen live).
    """
    ids = set()
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        path = str(a.get_folder_path())
        if path.startswith(FOLDER) and len(path) > len(FOLDER) and a.get_actor_label().startswith("chunk_"):
            ids.add(path[len(FOLDER):].split("/")[0])
    return sorted(ids)


def place_player_start(world_id):
    """Put the level's one Daedalus PlayerStart at the view point; returns it, or None for an empty world."""
    b = world_bounds(world_id)
    if b is None:
        return None
    (x, y, z), (pitch, yaw) = view_point(*b)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart) and a.get_actor_label() == START_LABEL:
            actors.destroy_actor(a)
    start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x, y, z), unreal.Rotator(0, pitch, yaw))
    if start is not None:
        start.set_actor_label(START_LABEL)
        start.set_folder_path(FOLDER + world_id)
    return start


def frame_editor(world_id=None):
    """Move the editor viewport to look at the world (the first one in the level if no id is given)."""
    ids = [world_id] if world_id else daedalus_worlds()
    for wid in ids:
        b = world_bounds(wid)
        if b is None:
            continue
        (x, y, z), (pitch, yaw) = view_point(*b)
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
            unreal.Vector(x, y, z), unreal.Rotator(0, pitch, yaw))
        unreal.log("Daedalus: viewport framed on %s" % wid)
        return True
    return False
