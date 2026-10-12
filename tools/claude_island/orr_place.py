# SPDX-License-Identifier: MIT
"""Claude Island (The Orrery Reach): lay the island and all 500 items out in the open Unreal editor.

Run inside the editor (bridge execute_python, or the Python console):

    import sys; sys.path.insert(0, r"C:\\Users\\730ri\\projects\\Daedalus2\\tools\\claude_island")
    import orr_place; result = orr_place.run()

Everything goes into its own streaming sublevel, /Game/Claude/ClaudeIsland_Sub, so no other team's work is touched
(the contest rule). The island sits 4 km east of the unreal-team ARK_ORIGIN (0,0,0), inside the +/-8 km cell. It is
double size: a 240 m terrace disc on a hanging rock, a summit with the observatory, and districts.
- **Herb rings:** 24 starbloom species in constellation beds, each showing its four stages.
- **Water:** summit spring, then aqueduct, then filters, then cistern, then well, then troughs. Dew nets sit on the
  rim.
- **Pens:** livestock pens with troughs, the barn, the coop and the apiary.
- **Plaza:** a market of brews, goods and food; the steeping house; workshop racks with tools and weapons.
- **Edges:** crop fields, an ark dock with the vehicles, and moonlets and debris in the sky above.

Running it again first clears the sublevel's actors (tagged ClaudeIsland), so it is safe to repeat.
"""
import math
import os
import random
import sys
import types

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.modules.setdefault("bpy", types.ModuleType("bpy"))
sys.modules.setdefault("bmesh", types.ModuleType("bmesh"))
sys.path.insert(0, HERE)
import orr_build  # noqa: E402

ORIGIN = unreal.Vector(400000.0, 0.0, 5000.0)   # 4 km east of ARK_ORIGIN 0,0,0; the deck 50 m up
SUB = "/Game/Claude/ClaudeIsland_Sub"
TAG = "ClaudeIsland"
R_DECK = 12000.0                                  # 240 m across: double a land's 92 cubes x 100 cm

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def mesh_path(asset, kind):
    return "/Game/Daedalus/Art/%s/%s/%s/StaticMeshes/%s" % (kind, asset, asset, asset)


def _color_mi(name, rgb):
    """A project-owned colour material on the Nanite-ready base (ADR-055)."""
    path = "/Game/Claude/Materials/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    parent = unreal.load_asset("/Game/Daedalus/Materials/Gltf/MI_Default_Opaque_DS")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi = tools.create_asset(name, "/Game/Claude/Materials", unreal.MaterialInstanceConstant,
                            unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
    for p in unreal.MaterialEditingLibrary.get_vector_parameter_names(parent):
        if "color" in str(p).lower() or "base" in str(p).lower():
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                mi, p, unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
            break
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return mi


def spawn(mesh, loc, yaw=0.0, scale=(1.0, 1.0, 1.0), mat=None, label=None, collide=True):
    m = unreal.load_asset(mesh) if isinstance(mesh, str) else mesh
    if m is None:
        return None
    a = EAS.spawn_actor_from_object(m, loc, unreal.Rotator(0.0, 0.0, yaw))
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.tags = [TAG]
    if label:
        a.set_actor_label(label)
    a.set_folder_path("ClaudeIsland")
    smc = a.static_mesh_component
    if mat is not None:
        for i in range(smc.get_num_materials()):
            smc.set_material(i, mat)
    if not collide:
        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def at(x, y, z=0.0):
    return unreal.Vector(ORIGIN.x + x, ORIGIN.y + y, ORIGIN.z + z)


def ensure_sublevel():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for lvl in unreal.EditorLevelUtils.get_levels(world):
        if SUB.split("/")[-1] in lvl.get_path_name():
            unreal.EditorLevelUtils.make_level_current(lvl)
            return lvl
    if not unreal.EditorAssetLibrary.does_asset_exist(SUB):
        streaming = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, False)
    else:
        streaming = unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingDynamic)
    lvl = streaming.get_loaded_level()
    unreal.EditorLevelUtils.make_level_current(lvl)
    return lvl


def clear():
    for a in EAS.get_all_level_actors():
        if TAG in [str(t) for t in a.tags]:
            EAS.destroy_actor(a)


def run(seed=7):
    rng = random.Random(seed)
    ensure_sublevel()
    clear()
    grass = _color_mi("MI_Orr_Grass", (0.22, 0.5, 0.25))
    rock = _color_mi("MI_Orr_Rock", (0.33, 0.3, 0.38))
    path_m = _color_mi("MI_Orr_Path", (0.75, 0.7, 0.55))
    water_m = _color_mi("MI_Orr_Water", (0.15, 0.45, 0.85))
    soil = _color_mi("MI_Orr_Soil", (0.35, 0.24, 0.15))
    cyl, cone, cube = "/Engine/BasicShapes/Cylinder", "/Engine/BasicShapes/Cone", "/Engine/BasicShapes/Cube"

    # ---- the land: deck, hanging rock, summit terraces, paths, a pond
    spawn(cyl, at(0, 0, -1000), 0, (R_DECK / 50, R_DECK / 50, 20), grass, "Orr_Deck")
    spawn(cone, at(0, 0, -6500), 0, (R_DECK / 50 * 0.95, R_DECK / 50 * 0.95, 90), rock, "Orr_Underrock").set_actor_rotation(
        unreal.Rotator(180.0, 0.0, 0.0), False)
    for i, (r, h) in enumerate([(5200, 600), (3200, 1200), (1800, 1800)]):
        spawn(cyl, at(0, 0, h / 2 - 300), 0, (r / 50, r / 50, h / 100), grass if i < 2 else rock, "Orr_Terrace_%d" % i)
    top = 1500.0
    for k in range(8):
        a = k * math.pi / 4
        spawn(cube, at(math.cos(a) * 8000, math.sin(a) * 8000, 2), math.degrees(a), (110, 3, 0.05), path_m, "Orr_Spoke_%d" % k,
              collide=False)
    spawn(cyl, at(-7000, 4500, 3), 0, (24, 24, 0.06), water_m, "Orr_Pond", collide=False)

    cat = orr_build.catalogue()
    by = {}
    for asset, kind, family, p in cat:
        by.setdefault(family, []).append((asset, kind, p))
    placed = 0

    def ground(x, y):
        r = math.hypot(x, y)
        return 1500.0 if r < 1800 else 900.0 if r < 3200 else 300.0 if r < 5200 else 0.0

    def put(asset, kind, x, y, z=None, yaw=None, s=1.0):
        nonlocal placed
        z = ground(x, y) if z is None else z
        a = spawn(mesh_path(asset, kind), at(x, y, z), rng.uniform(0, 360) if yaw is None else yaw, (s, s, s), label=asset)
        placed += 1 if a else 0
        return a

    # ---- summit: the observatory, with the astronomy pieces on the terraces round it
    obs = [b for b in by["building"] if "Observatory_Dome" in b[0]][0]
    put(obs[0], obs[1], 0, 0, None, 0)
    astro = by["astro"]
    for i, (asset, kind, p) in enumerate(astro):
        ring = 0 if i < 30 else 1
        n = 30 if ring == 0 else len(astro) - 30
        j = i if ring == 0 else i - 30
        a = 2 * math.pi * j / n
        r = 2300 if ring == 0 else 4100
        put(asset, kind, math.cos(a) * r, math.sin(a) * r, None, math.degrees(a) + 90)

    # ---- the starbloom rings: 24 species, each a bed of its four stages, in constellation order
    herbs = by["herb"]
    for i in range(24):
        a = 2 * math.pi * i / 24
        for s in range(4):
            asset, kind, p = herbs[i * 4 + s]
            r = 6000 + s * 140
            for dup in range(1):
                put(asset, kind, math.cos(a) * r, math.sin(a) * r, None, math.degrees(a), 2.0)
        spawn(cube, at(math.cos(a) * 6200, math.sin(a) * 6200, 1), math.degrees(a), (7, 2.2, 0.06), soil, collide=False)

    # ---- buildings round the outer ring, facing the summit
    blds = [b for b in by["building"] if b[0] != obs[0]]
    for i, (asset, kind, p) in enumerate(blds):
        a = 2 * math.pi * (i + 0.5) / len(blds)
        put(asset, kind, math.cos(a) * 9600, math.sin(a) * 9600, None, math.degrees(a) + 90)

    # ---- water: summit spring down the west spoke to the pens, dew nets on the rim
    water = by["water"]
    line = [w for w in water if "Dew" not in w[0]]
    dew = [w for w in water if "Dew" in w[0]]
    for i, (asset, kind, p) in enumerate(line):
        d = 1200 + i * 330
        put(asset, kind, -d, 1800 + (i % 2) * 260, None, 90)
    for i, (asset, kind, p) in enumerate(dew):
        a = 2 * math.pi * i / len(dew) + 0.2
        put(asset, kind, math.cos(a) * 11300, math.sin(a) * 11300, None, math.degrees(a))

    # ---- the pens, east: livestock with their troughs and fences
    beasts = by["beast"]
    for i, (asset, kind, p) in enumerate(beasts):
        put(asset, kind, 6500 + (i % 4) * 700, -3000 + (i // 4) * 900, 0)
    fences = [d for d in by["decor"] if "Fence" in d[0]]
    for i, (asset, kind, p) in enumerate(fences):
        put(asset, kind, 6200 + i * 330, -3600, None, 0)

    # ---- the plaza, south: brews, teas, goods and food on market rows
    goods = by["tea"] + by["brew"] + by["goods"]
    for i, (asset, kind, p) in enumerate(goods):
        put(asset, kind, -2400 + (i % 14) * 360, -6200 - (i // 14) * 360, None, 0, 1.5)

    # ---- interior pieces round the plaza pavilion; tools and weapons on the workshop racks
    for i, (asset, kind, p) in enumerate(by["interior"]):
        a = 2 * math.pi * i / len(by["interior"])
        put(asset, kind, 3800 + math.cos(a) * 900, -6800 + math.sin(a) * 900, None, math.degrees(a) + 180)
    for i, (asset, kind, p) in enumerate(by["tool"] + by["weapon"]):
        put(asset, kind, -7600 + (i % 8) * 220, -2400 - (i // 8) * 300, None, 0, 1.5)

    # ---- decor along the spokes (lanterns, benches, tiles, planters, signs, banners)
    others = [d for d in by["decor"] if "Fence" not in d[0]]
    for i, (asset, kind, p) in enumerate(others):
        spoke = i % 8
        a = spoke * math.pi / 4 + 0.03
        r = 2600 + (i // 8) * 900
        put(asset, kind, math.cos(a) * r + math.sin(a) * 260, math.sin(a) * r - math.cos(a) * 260, None, math.degrees(a))

    # ---- crop fields, south-west
    for i, (asset, kind, p) in enumerate(by["crop"]):
        put(asset, kind, -6500 - (i % 6) * 350, -5000 - (i // 6) * 350, None, 0, 2.0)

    # ---- the ark dock, north rim, with the vehicles
    for i, (asset, kind, p) in enumerate(by["vehicle"]):
        put(asset, kind, -2500 + i * 1000, 12400, None, 0)
    spawn(cube, at(0, 12400, -40), 0, (70, 14, 0.8), soil, "Orr_Dock_Deck")

    # ---- the islanders, each at their trade (Keeper Ostra is the playable NPC, placed by place_play)
    spots = {"Baker_Fen": (-1200, -6600), "Shepherd_Lio": (7200, -2400), "Beekeeper_Mara": (6000, 3600),
             "LensGrinder_Tov": (-3400, -1200), "ChartMaker_Ilse": (2400, 2400), "Ferryman_Bram": (2000, 12000),
             "Child_Pip": (300, -5200), "Cartographer_Wen": (-2400, 2600)}
    for asset, kind, p in by.get("person", []):
        key = asset.replace("Mob_Orr_", "")
        if key in spots:
            x, y = spots[key]
            put(asset, kind, x, y, None, math.degrees(math.atan2(-y, -x)))

    # ---- the sky: moonlets, fragments, clouds and streaks above the island
    for i, (asset, kind, p) in enumerate(by["sky"]):
        a = 2 * math.pi * i / len(by["sky"])
        put(asset, kind, math.cos(a) * 16000, math.sin(a) * 16000, 9000 + (i % 3) * 3000)

    play = place_play(rng)

    unreal.EditorLevelLibrary.save_current_level()
    return {"play": play, "placed": placed, "of": len(cat), "sublevel": SUB, "origin": [ORIGIN.x, ORIGIN.y, ORIGIN.z]}


def place_play(rng):
    """The game (ADR-057): the Keeper at the dock, the clogged filter on the aqueduct, a kettle in the plaza, one
    living starbloom per species beside its bed, and the twelve star charts scattered over the rim (the Lantern chart
    in the herb rings). Needs the DaedalusLink build that has the Orrery classes."""
    if not hasattr(unreal, "DaedalusStarbloom"):
        return "Orrery classes not built yet"
    out = {"starblooms": 0, "charts": 0}

    def actor(cls, x, y, z, yaw=0.0, label=None, **props):
        a = EAS.spawn_actor_from_class(cls, at(x, y, z), unreal.Rotator(0.0, 0.0, yaw))
        a.tags = [TAG]
        a.set_folder_path("ClaudeIsland/Play")
        if label:
            a.set_actor_label(label)
        for k, v in props.items():
            a.set_editor_property(k, v)
        return a

    actor(unreal.DaedalusKeeper, 0, 11600, 0, -90.0, "Orr_Keeper_Ostra")
    actor(unreal.DaedalusWaterFilter, -1200 - 16 * 330, 2300, 0, 90.0, "Orr_Play_Filter")
    actor(unreal.DaedalusKettle, 0, -5600, 0, 0.0, "Orr_Play_Kettle")
    actor(unreal.DaedalusKettle, 2200, 1200, 900, 0.0, "Orr_Play_Kettle_Summit")
    herbs = [h for h in orr_build.HERBS]
    for i, name in enumerate(herbs):
        a = 2 * math.pi * i / 24
        actor(unreal.DaedalusStarbloom, math.cos(a) * 5600, math.sin(a) * 5600, 0, math.degrees(a), "Orr_Bloom_" + name,
              species=name)
        out["starblooms"] += 1
    for i, c in enumerate(orr_build.CONSTELLATIONS):
        if c == "Lantern":
            x, y = math.cos(0.4) * 6600, math.sin(0.4) * 6600
        else:
            a = 2 * math.pi * i / 12 + rng.uniform(-0.2, 0.2)
            r = rng.uniform(10200, 11500)
            x, y = math.cos(a) * r, math.sin(a) * r
        actor(unreal.DaedalusStarChart, x, y, 60, 0.0, "Orr_Chart_" + c, constellation=c)
        out["charts"] += 1
    return out


def shoot(path):
    """A hero view of the whole island from the south-east, high up."""
    cam = at(-17000, -21000, 15000)
    look = at(0, 0, 0)
    rot = unreal.MathLibrary.find_look_at_rotation(cam, look)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(cam, rot)
    return {"camera": [cam.x, cam.y, cam.z]}
