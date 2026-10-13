# SPDX-License-Identifier: MIT
"""The Orrery Reach: Claude Island's neighbouring isles, so the domain is a little archipelago, not one rock.

    import orr_reach; result = orr_reach.run()

They go in the same sublevel as Claude Island (/Game/Claude/ClaudeIsland_Sub) and stay inside the unreal-team cell
(+/-8 km of 0,0,0). Each is a Daedalus Voxel Isle with its own seed, size, height and colours, dressed from the
Orrery Reach's own items:
- the Bloomfields: wide and low, all herb beds, greenhouses and crop rows;
- the Tidewells: a lake isle of cisterns, wells and dew towers;
- the Lens Forge: a small, high, stony isle with the lens workshop, telescopes and meteorites;
- the Vault: the sealed isle far to the south, where the logbook ends.
The cartographer's lines and the logbook already name them, so the world matches the story.
"""
import math
import random

import unreal

import orr_build
import orr_place as P

ISLES = [
    # name, offset from Claude Island (cm), z offset, radius (cubes), summit, depth, seed, grass, stone, pond
    ("Bloomfields", (-3200, -24000), -1800, 70, 6, 40, 31, (0.44, 0.78, 0.30), (0.56, 0.48, 0.40), (20, -15, 10)),
    ("Tidewells", (22000, 16000), 1200, 60, 8, 50, 47, (0.30, 0.66, 0.42), (0.42, 0.46, 0.54), (0, 0, 22)),
    ("LensForge", (-22000, 14000), 4200, 38, 14, 45, 53, (0.52, 0.56, 0.38), (0.56, 0.54, 0.60), (0, 0, 0)),
    ("Vault", (6000, -52000), 2600, 46, 20, 60, 61, (0.30, 0.40, 0.58), (0.30, 0.30, 0.40), (0, 0, 0)),
]

DRESS = {
    "Bloomfields": ["Bld_Orr_Greenhouse_Day", "Bld_Orr_Greenhouse_Night", "Bld_Orr_Herb_Drying_Shed", "Bld_Orr_Windmill",
                    "Prop_Orr_Planter_Long", "Prop_Orr_Planter_Tiered", "Prop_Orr_Planter_Spiral", "Prop_Orr_Fence_Wattle",
                    "Prop_Orr_Sign_Welcome", "Prop_Orr_Lantern_Path"],
    "Tidewells": ["Bld_Orr_Cistern_House", "Bld_Orr_Well_House", "Bld_Orr_Dew_Tower", "Bld_Orr_Water_Mill",
                  "Prop_Orr_Cistern_Round", "Prop_Orr_Cistern_Square", "Prop_Orr_Well_Stone", "Prop_Orr_Dew_Net_Large",
                  "Prop_Orr_Drinking_Fountain", "Prop_Orr_Rain_Barrel"],
    "LensForge": ["Bld_Orr_Lens_Workshop", "Bld_Orr_Clock_Tower", "Prop_Orr_Telescope_Giant", "Prop_Orr_Telescope_Refractor",
                  "Prop_Orr_Meteorite_Starmetal", "Prop_Orr_Meteorite_Ember", "Prop_Orr_Lens_Prism", "Prop_Orr_Lens_Moon",
                  "Prop_Orr_Interior_Gear_Workbench", "Prop_Orr_Interior_Lens_Cabinet"],
    "Vault": ["Bld_Orr_Observatory_Tower", "Bld_Orr_Gate_Arch", "Bld_Orr_Bell_Tower", "Prop_Orr_Armillary_Heartstone",
              "Prop_Orr_Orrery_11Planet", "Prop_Orr_MoonPhase_Lamp_Blood", "Prop_Orr_MoonPhase_Lamp_Blue",
              "Prop_Orr_Sundial_Moon", "Prop_Orr_Banner_Crown", "Prop_Orr_Lantern_Orb"],
}


def run():
    P.ensure_sublevel()
    kinds = {a: k for a, k, *_ in orr_build.catalogue()}
    # clear the previous Reach isles (tagged OrreryReach) so this is safe to run again
    for a in P.EAS.get_all_level_actors():
        if "OrreryReach" in [str(t) for t in a.tags]:
            P.EAS.destroy_actor(a)
    out = {}
    for name, (dx, dy), dz, radius, summit, depth, seed, grass, stone, pond in ISLES:
        o = unreal.Vector(P.ORIGIN.x + dx, P.ORIGIN.y + dy, P.ORIGIN.z + dz)
        isle = P.EAS.spawn_actor_from_class(unreal.DaedalusVoxelIsle, o, unreal.Rotator(0.0, 0.0, 0.0))
        isle.tags = ["OrreryReach", P.TAG]
        isle.set_actor_label("Orr_Isle_" + name)
        isle.set_folder_path("ClaudeIsland/Reach/" + name)
        for k, v in (("seed", seed), ("radius", radius), ("summit_height", summit), ("depth", depth),
                     ("pond_at", unreal.IntPoint(pond[0], pond[1])), ("pond_radius", pond[2]),
                     ("grass_color", unreal.LinearColor(*grass, 1.0)), ("stone_color", unreal.LinearColor(*stone, 1.0))):
            isle.set_editor_property(k, v)
        isle.build()
        rng = random.Random(seed)
        placed = 0
        items = DRESS[name]
        for i, asset in enumerate(items):
            for tries in range(12):
                a = rng.uniform(0, 2 * math.pi)
                r = rng.uniform(0.15, 0.7) * radius * 100
                x, y = o.x + math.cos(a) * r, o.y + math.sin(a) * r
                if isle.is_land(x, y):
                    break
            m = unreal.load_asset(P.mesh_path(asset, kinds.get(asset, "Prop")))
            if m is None:
                continue
            act = P.EAS.spawn_actor_from_object(m, unreal.Vector(x, y, isle.top_z(x, y)), unreal.Rotator(0.0, 0.0, math.degrees(a) + 90))
            act.tags = ["OrreryReach", P.TAG]
            act.set_folder_path("ClaudeIsland/Reach/" + name)
            act.set_actor_label("Orr_%s_%s" % (name, asset))
            placed += 1
        # herb beds everywhere on the Bloomfields: a ring of every species in full bloom
        if name == "Bloomfields":
            for j, h in enumerate(orr_build.HERBS):
                a = 2 * math.pi * j / len(orr_build.HERBS)
                for s, stage in enumerate(("Bud", "Bloom")):
                    rr = radius * 100 * (0.45 + 0.06 * s)
                    x, y = o.x + math.cos(a) * rr, o.y + math.sin(a) * rr
                    m = unreal.load_asset(P.mesh_path("Prop_Orr_Herb_%s_%s" % (h, stage), "Prop"))
                    if m is None or not isle.is_land(x, y):
                        continue
                    act = P.EAS.spawn_actor_from_object(m, unreal.Vector(x, y, isle.top_z(x, y)), unreal.Rotator(0.0, 0.0, 0.0))
                    act.set_actor_scale3d(unreal.Vector(4.0, 4.0, 4.0))
                    act.tags = ["OrreryReach", P.TAG]
                    act.set_folder_path("ClaudeIsland/Reach/" + name)
                    placed += 1
        out[name] = {"isle": isle.stats(), "dressed": placed}
    # Sky bridges from Claude Island to three of them; the Vault stays out of reach on foot (the logbook's end).
    if hasattr(unreal, "DaedalusSkyBridge"):
        home = [a for a in P.EAS.get_all_level_actors() if a.get_actor_label() == "Orr_Isle"]
        isles = {a.get_actor_label(): a for a in P.EAS.get_all_level_actors() if a.get_actor_label().startswith("Orr_Isle_")}
        if home:
            h = home[0]
            for name in ("Bloomfields", "Tidewells", "LensForge"):
                t = isles.get("Orr_Isle_" + name)
                if t is None:
                    continue
                a, b = h.get_actor_location(), t.get_actor_location()
                d = unreal.Vector(b.x - a.x, b.y - a.y, 0.0)
                L = math.hypot(d.x, d.y)
                ux, uy = d.x / L, d.y / L
                ra = h.get_editor_property("radius") * 100 * 0.8
                rb = t.get_editor_property("radius") * 100 * 0.8
                sx, sy = a.x + ux * ra, a.y + uy * ra
                ex, ey = b.x - ux * rb, b.y - uy * rb
                start = unreal.Vector(sx, sy, h.top_z(sx, sy) + 20)
                end = unreal.Vector(ex, ey, t.top_z(ex, ey) + 20)
                br = P.EAS.spawn_actor_from_class(unreal.DaedalusSkyBridge, start, unreal.Rotator(0.0, 0.0, 0.0))
                br.tags = ["OrreryReach", P.TAG]
                br.set_actor_label("Orr_Bridge_" + name)
                br.set_folder_path("ClaudeIsland/Reach")
                br.set_editor_property("end", end)
                out["bridge_" + name] = br.build()
    P.LES.save_all_dirty_levels()
    return out
