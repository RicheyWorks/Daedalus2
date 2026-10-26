# SPDX-License-Identifier: MIT
"""Portal data projection for the existing RPG demo, with no alternate engine.

Read canonical JSON through the builder's existing J(name) seam. All adapted
objects are detached copies; this module never changes realm source data or art.
There are no authored Portal boss records in this export, so this slice uses
existing field/cave encounters rather than inventing bosses or progression.
"""
from collections import deque
from copy import deepcopy


CONTRACT = "daedalus.portal-demo/v1"
REALM = "portal"
QUEST = [("Cave", "Old Mine")]


def grid_cells(grid):
    """Reject malformed or unbounded map input before projecting a browser map."""
    if not isinstance(grid, list) or not grid or len(grid) > 128:
        raise ValueError("map requires 1..128 rows")
    width = len(grid[0]) if isinstance(grid[0], list) else 0
    if not 1 <= width <= 128 or any(not isinstance(row, list) or len(row) != width for row in grid):
        raise ValueError("map requires rectangular 1..128 columns")
    if any(not isinstance(cell, str) or not cell for row in grid for cell in row):
        raise ValueError("map cells require nonempty tile names")
    return width, len(grid)


def reachable(grid, walkable, start):
    """Existing four-direction foot travel; no carving or invented connections."""
    width, height = grid_cells(grid)
    x, y = start
    if not (0 <= x < width and 0 <= y < height) or grid[y][x] not in walkable:
        raise ValueError("spawn is not a walkable map cell")
    seen, queue = {(x, y)}, deque([(x, y)])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            point = x + dx, y + dy
            if (0 <= point[0] < width and 0 <= point[1] < height
                    and point not in seen and grid[point[1]][point[0]] in walkable):
                seen.add(point)
                queue.append(point)
    return seen


def _find(grid, tile):
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == tile:
                return x, y
    raise ValueError("missing world landmark: " + tile)


def project(read):
    """Return canonical Portal inputs plus bounded demo-only adaptation metadata.

    The one exported Portal town template is reused at the Village landmark.
    The Old Mine's unexported fourth-floor stair is closed in this detached
    projection. Neither adaptation is written back to the canonical JSON.
    """
    town_data = deepcopy(read("town-tiles.json"))
    world_data = deepcopy(read("worldmap-tiles.json"))
    dungeon_data = deepcopy(read("dungeons.json"))
    town = town_data["demo_towns"][REALM]
    world = world_data["demo_maps"][REALM]
    grid_cells(town["grid"])
    grid_cells(world)
    town_walk = {item["tile"] for item in town_data["tiles"] if item["realm"] == REALM and item["walkable"]}
    world_walk = {item["tile"] for item in world_data["tiles"] if item["realm"] == REALM and item["walkable"]}
    spawn = {"x": 11, "y": 15, "facing": "up"}  # the existing demo's town entry
    town_seen = reachable(town["grid"], town_walk, (spawn["x"], spawn["y"]))
    if not any((x, len(town["grid"]) - 1) in town_seen for x in range(len(town["grid"][0]))):
        raise ValueError("Portal town exit is unreachable")
    world_seen = reachable(world, world_walk, _find(world, "Town"))
    for tile in ("Cave", "Castle", "Village", "Shrine"):
        if _find(world, tile) not in world_seen:
            raise ValueError("Portal world landmark is unreachable: " + tile)
    quest = []
    sealed = []
    for landmark, name in QUEST:
        source = next((item for item in dungeon_data["dungeons"][REALM] if item["name"] == name), None)
        if source is None or not source.get("floors"):
            raise ValueError("missing Portal dungeon: " + name)
        dungeon = deepcopy(source)
        for index, floor in enumerate(dungeon["floors"]):
            if floor.get("floor") != index + 1:
                raise ValueError("Portal dungeon floors must be contiguous from one")
            width, height = grid_cells(floor["grid"])
            for direction in ("stairs_up", "stairs_down"):
                stair = floor.get(direction)
                if stair is None:
                    continue
                if type(stair.get("x")) is not int or type(stair.get("y")) is not int:
                    raise ValueError("stair coordinates must be integers")
                x, y = stair["x"], stair["y"]
                if not 0 <= x < width or not 0 <= y < height:
                    raise ValueError("stair coordinates outside dungeon")
                expected_tile = "StairsUp" if direction == "stairs_up" else "StairsDown"
                if floor["grid"][y][x] != expected_tile:
                    raise ValueError("stair does not match its authored tile")
                destination = ("overworld" if index == 0 else "floor " + str(index)) if direction == "stairs_up" else "floor " + str(index + 2)
                if stair.get("to") != destination:
                    raise ValueError("unexpected Portal stair destination")
            entry = floor.get("stairs_up")
            if entry is None:
                raise ValueError("Portal dungeon requires an entry stair")
            floor_seen = reachable(floor["grid"], set(dungeon_data["walkable"]) | {"Hazard", "StairsUp", "StairsDown"}, (entry["x"], entry["y"]))
            lower = floor.get("stairs_down")
            if lower and (lower["x"], lower["y"]) not in floor_seen:
                raise ValueError("Portal dungeon descent is unreachable")
            if index == len(dungeon["floors"]) - 1 and floor.get("stairs_down"):
                stair = floor["stairs_down"]
                floor["grid"][stair["y"]][stair["x"]] = "Floor"
                floor["stairs_down"] = None
                sealed.append({"dungeon": name, "floor": floor["floor"], "reason": "destination floor not exported"})
        dungeon.update(landmark=landmark, final=False, boss_data=None, boss_backdrop="cave")
        quest.append(dungeon)
    village = deepcopy(town)
    village.update(name="Portal Village", landmark="Village", spawn=spawn, exit_row=len(town["grid"]) - 1)
    return {
        "realm_key": REALM, "name": "Portal Realm", "screen": [256, 224],
        "party_prefix": "Portal", "backdrop_prefix": "Portal", "quest": QUEST[:],
        "town": town, "world": world, "village": village, "dungeons": quest,
        "encounters": deepcopy(read("portal-encounters.json"))["zones"],
        "bestiary": deepcopy(read("portal-bestiary.json")), "fish": [], "sky_loot": [],
        "runtime": {
            "contract": CONTRACT, "realm_key": REALM, "save_key": "portal.save.v1",
            "start_level": 1, "start_spawn": spawn,
            "intro": ["WELCOME TO THE PORTAL REALM. THE OLD MINE LIES BEYOND THE TOWN.",
                      "TALK WITH A. OPEN THE MENU WITH START. REST AT THE INN TO SAVE THIS JOURNEY."],
            "dialogue": {"Guard": ["THE ROAD LEADS OUT INTO THE PORTAL REALM."],
                         "Child": ["HAVE YOU SEEN THE OLD MINE?"],
                         "Elder": ["REST AT THE INN BEFORE EXPLORING THE OLD MINE."],
                         "Ruler": ["WELCOME, TRAVELLERS OF THE PORTAL REALM."]},
        },
        "projection_notes": {"sealed_stairs": sealed, "village_uses_existing_town_template": True,
                             "boss_progression": "not authored in this source export"},
    }
