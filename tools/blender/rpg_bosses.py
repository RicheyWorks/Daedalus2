# SPDX-License-Identifier: MIT
"""Prismheart Realm bosses (ADR-067) — original. One Warden guards each Prism Shard's dungeon, two keep the road,
and the Prism Devourer waits at the end. Bodies reuse realm_rpg_cast / rpg_bestiary archetypes, doubled in voxel
scale and crowned or armoured. Registered as voxel_creatures family "prism_boss" (export name Mob_Prism_Boss_<Name>).
`write_data(root)` writes data/rpg/prism-bosses.json (stats, dungeon, shard, phases, weakness, drops).
"""
import json
import os

import voxel_creatures as VC
import voxel_dragons as VD
import realm_rpg_cast as RC
import rpg_bestiary as BE

C = RC.col
S2 = lambda p: RC.scale_plan(p, 2)   # noqa: E731

BOSSES = [
    # name, body builder, dungeon, shard, level, hp, atk, def, spd, element, weakness, phases, drops
    ("PyreWarden", lambda: S2(RC.golem(C((.35, .15, .10)), C((1.0, .45, .10)), 1.3, crystal=C((1, .8, .3)))), "Cinder Forge", "Fire", 18, 2200, 46, 30, 8, "fire", "tide",
     ["armour up: magma plates", "plates crack: eruption every 3 turns"], ["Shard of Fire", "Emberforge Titan summon"]),
    ("TideWarden", lambda: S2(RC.serpent(C((.15, .35, .65)), C((.45, .85, .95)), 1.6, hood=True)), "Drowned Spire", "Tide", 22, 2800, 50, 28, 11, "water", "gale",
     ["coils in the pool (untargetable on even turns)", "flood: whole party drenched"], ["Shard of Tide", "Tidecoil summon"]),
    ("GaleWarden", lambda: S2(VC._bird(C((.80, .92, .85)), C((.45, .75, .65)), size=2.0, crest=C((.95, .95, .55)), wing_len=16)), "Windcut Aerie", "Gale", 26, 3200, 54, 24, 18, "air", "stone",
     ["airborne: only lances and bows reach", "grounded after a Starlancer leap"], ["Shard of Gale", "Galewing summon"]),
    ("StoneWarden", lambda: S2(BE.BODY["behemoth"](1.2, ((.45, .40, .32), (.75, .70, .60)))), "Rootdeep Hollow", "Stone", 30, 4200, 60, 40, 6, "earth", "fire",
     ["quake each turn", "rootbound: roots must be cut first"], ["Shard of Stone", "Rootfather summon"]),
    ("LightWarden", lambda: RC.add_crown(S2(RC.orb(C((.98, .95, .70)), C((.55, .80, 1.0)), 1.4)), C((1, .95, .6)), 4), "Sunwell Sanctum", "Light", 34, 4600, 58, 34, 14, "light", "shade",
     ["blinding halo", "splits into three mirror orbs"], ["Shard of Light", "Starfall summon"]),
    ("ShadeWarden", lambda: S2(VD.plan("dragon_shadow_elder_04")), "Umbral Vault", "Shade", 38, 5400, 66, 36, 13, "dark", "light",
     ["shadow breath", "night falls: party blinded until a light spell"], ["Shard of Shade", "Glacier Stag summon"]),
    ("ClockworkColossus", lambda: S2(RC.golem(C((.70, .55, .25)), C((.45, .40, .35)), 1.5, crystal=C((.35, .85, .95)))), "Gearwright's Folly", "-", 24, 3000, 52, 44, 5, "none", "tide",
     ["steam vents", "overheats: defence drops for two turns"], ["Prism Sentry core", "Gearwright's master wrench"]),
    ("HollowKing", lambda: RC.add_crown(S2(BE.BODY["knight"](1.2, ((.25, .22, .30), (.65, .15, .20)))), C((.95, .78, .25)), 3), "Fallen Keep", "-", 32, 4400, 62, 46, 9, "dark", "light",
     ["summons two Hollow Armors", "alone: doubled attacks"], ["Crown of the Keep", "Bladeward's oath-blade"]),
    ("PrismDevourer", lambda: RC.add_crown(S2(VD.plan("dragon_crystal_elder_07")), C((.95, .55, 1.0)), 5), "The Shattered Heart", "all", 50, 12000, 84, 50, 15, "all", "none",
     ["devours one shard each phase (immune to that element)", "glass form: reflects spells", "heart exposed: all summons answer"], ["The Prism Heart", "credits"]),
]
KEYS = {}
for b in BOSSES:
    k = "prism_boss_%s" % b[0].lower()
    KEYS[k] = b
    VC.NAMES[k] = "Mob_Prism_Boss_%s" % b[0]


def plan(key):
    return KEYS[key][1]()


VC.EXTRA["prism_boss"] = (tuple(KEYS), plan)


def write_data(root):
    d = os.path.join(root, "data", "rpg")
    os.makedirs(d, exist_ok=True)
    rows = [{"key": k, "name": b[0], "export_name": VC.NAMES[k], "dungeon": b[2], "shard": b[3], "level": b[4], "hp": b[5], "attack": b[6],
             "defence": b[7], "speed": b[8], "element": b[9], "weakness": b[10], "phases": b[11], "drops": b[12],
             "sprite": "engines/unreal/art/claude-battle-sprites/prism/Battle_Prism_Boss_%s.png" % b[0]} for k, b in KEYS.items()]
    with open(os.path.join(d, "prism-bosses.json"), "w", encoding="utf-8") as f:
        json.dump({"realm": "Prismheart Realm", "schema": "daedalus.bosses/v1", "source": "tools/blender/rpg_bosses.py", "bosses": rows}, f, indent=1)
    return d


if __name__ == "__main__":
    miss = set()
    for k in KEYS:
        for v in plan(k).values():
            for *_, c in v:
                if c not in RC.PAL:
                    miss.add(c)
    print(len(KEYS), "bosses; missing", sorted(miss)[:5])
    print(write_data(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
