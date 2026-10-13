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
    """A project-owned colour material: the engine's basic shape material (it has a Color parameter) tinted. The
    island's ground pieces are engine basic shapes, not Nanite meshes, so this base needs no Nanite usage."""
    path = "/Game/Claude/Materials/" + name
    mi = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if mi is None:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mi = tools.create_asset(name, "/Game/Claude/Materials", unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(
        mi, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        mi, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
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


# What the islanders say: morning | day | dusk | night. All original.
ISLANDER_LINES = {
    "Baker_Fen": "Starbread's in the oven. It rises best while Dawnthistle opens.|Comet eggs and orbit milk, that's the whole secret. "
                 "Well, and the hour.|Come to the plaza later, I bring the heels of the loaves.|Shh. The dough is sleeping, and so should you.",
    "Shepherd_Lio": "The lumewool flock glows brighter before rain. Watch them, not the sky.|Hay and herb stems. Never feed them "
                    "Eclipsebell, they glow for a week.|Count the flock with me? Forty-one. Forty-one and a half, the lamb.|"
                    "At night the flock is a little moon on the hillside.",
    "Beekeeper_Mara": "The nebula bees only work a bloom in its hour. They read the clock better than I do.|Honey from a Noonspire "
                      "hour tastes of brass and sunlight.|Bees home at dusk. The hive hums like a kettle.|Night bees? Only in stories. "
                      "And in my dreams, lately.",
    "LensGrinder_Tov": "Grit in the lens is a storm in the sky. Hand me that cloth.|The great telescope lost three lenses in the Long "
                       "Storm. I've ground two.|Hold this up to the dusk. See the second ring? That's no reflection.|The stars are "
                       "sharper after midnight, when the island stops breathing.",
    "ChartMaker_Ilse": "Every chart is a promise between the sky and the soil.|The Keeper's charts drew each constellation over its "
                       "two herbs. Find the herbs, you've found the chart.|Twelve charts, twelve pairs. The storm can't scatter "
                       "what you remember.|Pick a bloom in its hour and it remembers you.",
    "Ferryman_Bram": "Arks come in on the morning updraft. Mind the dock edge, it's a long fall.|I ferried a man to the Lens Forge "
                     "isle once. He came back with eyes like brass.|Dusk crossings are calm. The fragments drift slower.|Sleep. "
                     "The sky will still be broken in the morning.",
    "Child_Pip": "I found a star chart once! It was a leaf. But it looked like a chart.|Keeper Ostra says the moon is closer every "
                 "year. Is it coming to visit?|Race you to the well! Loser drinks the cloudy water.|I'm not tired. I'm watching for "
                 "the eclipse brew glow.",
    "Cartographer_Wen": "Our isle drifts nine paces east each year. I measure it with the well rope.|There are more isles in the Reach "
                        "than on any chart: the Bloomfields, the Tidewells, the Lens Forge.|At dusk you can see the Vault isle's "
                        "lamps, far to the south.|The map is never finished. That's what makes it a map.",
}


def ensure_sublevel():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    name = SUB.split("/")[-1]
    if not any(name in l.get_path_name() for l in unreal.EditorLevelUtils.get_levels(world)):
        if not unreal.EditorAssetLibrary.does_asset_exist(SUB):
            unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, SUB, False)
        else:
            unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingDynamic)
    # A dynamic streaming level doesn't load in Play unless told to: the island and its game would be missing.
    s = unreal.GameplayStatics.get_streaming_level(world, name)
    if s is not None and not s.get_editor_property("initially_loaded"):
        s.set_editor_property("initially_loaded", True)
        s.set_editor_property("initially_visible", True)
        world.modify()
    LES.set_current_level_by_name(name)
    return name


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

    # ---- the land: a seeded voxel isle (ADR-058) when the build has it, else the basic-shape terraces
    isle = None
    if hasattr(unreal, "DaedalusVoxelIsle"):
        isle = EAS.spawn_actor_from_class(unreal.DaedalusVoxelIsle, ORIGIN, unreal.Rotator(0.0, 0.0, 0.0))
        isle.tags = [TAG]
        isle.set_actor_label("Orr_Isle")
        isle.set_folder_path("ClaudeIsland")
        for k, v in (("seed", seed), ("radius", 140), ("summit_height", 16), ("depth", 70),
                     ("pond_at", unreal.IntPoint(-70, 45)), ("pond_radius", 14)):
            isle.set_editor_property(k, v)
        isle.build()
    else:
        spawn(cyl, at(0, 0, -1000), 0, (R_DECK / 50, R_DECK / 50, 20), grass, "Orr_Deck")
        spawn(cone, at(0, 0, -6500), 0, (R_DECK / 50 * 0.95, R_DECK / 50 * 0.95, 90), rock, "Orr_Underrock").set_actor_rotation(
            unreal.Rotator(180.0, 0.0, 0.0), False)
        for i, (r, h) in enumerate([(5200, 600), (3200, 1200), (1800, 1800)]):
            spawn(cyl, at(0, 0, h / 2 - 300), 0, (r / 50, r / 50, h / 100), grass if i < 2 else rock, "Orr_Terrace_%d" % i)
        spawn(cyl, at(-7000, 4500, 3), 0, (24, 24, 0.06), water_m, "Orr_Pond", collide=False)
    top = 1500.0
    for k in range(8):
        a = k * math.pi / 4
        for j in range(22):   # stepping-stone paths that follow the ground
            r = 1800 + j * 450
            x, y = math.cos(a) * r, math.sin(a) * r
            if isle is not None and not isle.is_land(ORIGIN.x + x, ORIGIN.y + y):
                continue
            z = (isle.top_z(ORIGIN.x + x, ORIGIN.y + y) - ORIGIN.z) if isle is not None else 2
            spawn(cube, at(x, y, z + 1), math.degrees(a), (3.6, 1.4, 0.06), path_m, collide=False)

    cat = orr_build.catalogue()
    by = {}
    for asset, kind, family, p in cat:
        by.setdefault(family, []).append((asset, kind, p))
    placed = 0

    def ground(x, y):
        if isle is not None:
            return isle.top_z(ORIGIN.x + x, ORIGIN.y + y) - ORIGIN.z
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
                put(asset, kind, math.cos(a) * r, math.sin(a) * r, None, math.degrees(a), 3.5)
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
    if not hasattr(unreal, "DaedalusIslander"):
        for asset, kind, p in by.get("person", []):
            key = asset.replace("Mob_Orr_", "")
            if key in spots:
                x, y = spots[key]
                put(asset, kind, x, y, None, math.degrees(math.atan2(-y, -x)))
    else:
        homes = {"Baker_Fen": (-5600, -8200), "Shepherd_Lio": (8800, -1200), "Beekeeper_Mara": (7600, 5200),
                 "LensGrinder_Tov": (-5200, -3800), "ChartMaker_Ilse": (3600, 7600), "Ferryman_Bram": (-1800, 9800),
                 "Child_Pip": (2200, -8600), "Cartographer_Wen": (-8400, 2600)}
        for who, line in ISLANDER_LINES.items():
            if who not in spots:
                continue
            wx, wy = spots[who]
            hx, hy = homes[who]
            a = EAS.spawn_actor_from_class(unreal.DaedalusIslander, at(hx, hy, ground(hx, hy)), unreal.Rotator(0, 0, 0))
            a.tags = [TAG]
            a.set_folder_path("ClaudeIsland/Play")
            a.set_actor_label("Orr_Islander_" + who)
            a.set_editor_property("who", who)
            a.set_editor_property("home", at(hx, hy, ground(hx, hy)))
            a.set_editor_property("work", at(wx, wy, ground(wx, wy)))
            a.set_editor_property("plaza", at(0 + (sum(map(ord, who)) % 7) * 150 - 450, -5600 - (sum(map(ord, who)) % 5) * 120, ground(0, -5600)))
            a.set_editor_property("lines", line)
            placed += 1

    # ---- night: a warm light at every lantern, so the paths glow after dusk
    lights = 0
    for a in EAS.get_all_level_actors():
        if TAG in [str(t) for t in a.tags] and "Lantern" in a.get_actor_label():
            p_ = a.get_actor_location()
            L = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(p_.x, p_.y, p_.z + 160), unreal.Rotator(0, 0, 0))
            L.tags = [TAG]
            L.set_folder_path("ClaudeIsland/Lights")
            c = L.get_component_by_class(unreal.PointLightComponent)
            c.set_intensity(2500.0)
            c.set_light_color(unreal.LinearColor(1.0, 0.72, 0.38, 1.0))
            c.set_attenuation_radius(900.0)
            c.set_cast_shadows(False)
            lights += 1

    # ---- the pens come alive: the island's own livestock wander their paddocks (ADR-055 critters)
    if hasattr(unreal, "DaedalusCritter"):
        herd = [("Mob_Orr_Lumewool", 6, (7400, -2200)), ("Mob_Orr_CometHen", 6, (6600, -3300)),
                ("Mob_Orr_OrbitGoat", 4, (8200, -3200)), ("Mob_Orr_NebulaBee", 5, (7600, 5200)),
                ("Mob_Orr_Lumewool_Young", 3, (7600, -2600)), ("Mob_Orr_StarMoth", 4, (-3000, 3000)),
                ("Mob_Orr_DewNewt", 3, (-7000, 3000)), ("Mob_Orr_GearFox", 2, (-4000, -9000))]
        n = 0
        for species, count, (cx, cy) in herd:
            for k in range(count):
                x, y = cx + rng.uniform(-500, 500), cy + rng.uniform(-500, 500)
                c = EAS.spawn_actor_from_class(unreal.DaedalusCritter, at(x, y, ground(x, y) + 50), unreal.Rotator(0, 0, 0))
                c.tags = [TAG]
                c.set_folder_path("ClaudeIsland/Life")
                c.set_editor_property("species", species)
                c.set_editor_property("seed", 1000 + n)
                c.set_editor_property("range", 700.0)
                n += 1

    # ---- the sky: moonlets, fragments, clouds and streaks above the island
    for i, (asset, kind, p) in enumerate(by["sky"]):
        a = 2 * math.pi * i / len(by["sky"])
        put(asset, kind, math.cos(a) * 16000, math.sin(a) * 16000, 9000 + (i % 3) * 3000)

    play = place_play(rng, ground)

    LES.save_all_dirty_levels()
    return {"play": play, "placed": placed, "of": len(cat), "sublevel": SUB, "origin": [ORIGIN.x, ORIGIN.y, ORIGIN.z]}


def place_play(rng, ground=lambda x, y: 0.0):
    """The game (ADR-057): the Keeper at the dock, the clogged filter on the aqueduct, a kettle in the plaza, one
    living starbloom per species beside its bed, and the twelve star charts scattered over the rim (the Lantern chart
    in the herb rings). Needs the DaedalusLink build that has the Orrery classes."""
    if not hasattr(unreal, "DaedalusStarbloom"):
        return "Orrery classes not built yet"
    out = {"starblooms": 0, "charts": 0}

    def actor(cls, x, y, z, yaw=0.0, label=None, **props):
        a = EAS.spawn_actor_from_class(cls, at(x, y, ground(x, y) + z), unreal.Rotator(0.0, 0.0, yaw))
        a.tags = [TAG]
        a.set_folder_path("ClaudeIsland/Play")
        if label:
            a.set_actor_label(label)
        for k, v in props.items():
            a.set_editor_property(k, v)
        return a

    actor(unreal.DaedalusKeeper, 0, 10500, 0, -90.0, "Orr_Keeper_Ostra")
    actor(unreal.DaedalusWaterFilter, -1200 - 16 * 330, 2300, 0, 90.0, "Orr_Play_Filter")
    actor(unreal.DaedalusKettle, 0, -5600, 0, 0.0, "Orr_Play_Kettle")
    actor(unreal.DaedalusKettle, 2200, 1200, 0, 0.0, "Orr_Play_Kettle_Summit")
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
