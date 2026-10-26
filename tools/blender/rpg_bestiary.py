# SPDX-License-Identifier: MIT
"""Random-encounter bestiaries for the Portal Realm (8-bit) and the Prismheart Realm (16-bit) — all original names.

Classic console RPGs fill the field with enemy *lines*: one body, re-coloured and re-named as it gets stronger
further from the start. Each realm here has 40 lines × 4 tiers = 160 enemy types, on top of the population-plan
cast (realm_rpg_cast.py). Every type has: body (rigged on the shared 8-bone rig), tier tint, zones where it appears,
level band, HP / attack / defence / speed / EXP / gold, a behaviour tag (the battle AI hint) and an element.

`types(realm)` lists them; `plan(key)` builds the voxel body; `encounters(realm)` builds the encounter tables
(zone → step rate + weighted formations of 1–6 enemies) written by `write_data()` to data/rpg/<realm>-bestiary.json
and data/rpg/<realm>-encounters.json. Registered in voxel_creatures.EXTRA as families "<realm>_bestiary".
"""
import json
import os
import random

import voxel_creatures as VC
import voxel_dragons as VD
import realm_rpg_cast as RC

C, PAL, tint = RC.col, RC.PAL, RC.tint
TIERS = 4
FEATURES = ("eye", "eye_w", "nose", "tooth", "hoof", "drg_eye", "drg_fang", "drg_claw")


def tierize(parts, mult, keep=FEATURES):
    """Tier recolour: every non-feature colour multiplied by the tier's tint (the classic palette swap)."""
    m = {}
    for v in parts.values():
        for *_, c in v:
            if c in m or c in keep:
                continue
            r, g, b = PAL[c]
            m[c] = C((r * mult[0], g * mult[1], b * mult[2]))
    return RC.recolor(parts, m)


Q = VC._quadruped
B = VC._bird
# body builders by key (size s) — the archetypes from realm_rpg_cast plus every voxel_creatures body
BODY = {
    "slime":    lambda s, a: RC.slime(C(a[0]), C(a[1]), s, drip=True),
    "wisp":     lambda s, a: RC.wisp(C(a[0]), C(a[1]), s),
    "orb":      lambda s, a: RC.orb(C(a[0]), C(a[1]), s),
    "cap":      lambda s, a: RC.mushroom(C(a[0]), C(a[1]), spots=C((1, 1, 1)), size=s),
    "golem":    lambda s, a: RC.golem(C(a[0]), C(a[1]), s, crystal=C(a[2]) if len(a) > 2 else None),
    "mimic":    lambda s, a: RC.mimic(C(a[0]), C(a[1]), s),
    "crab":     lambda s, a: RC.crab(C(a[0]), C(a[1]), s),
    "serpent":  lambda s, a: RC.serpent(C(a[0]), C(a[1]), s, hood=True),
    "turtle":   lambda s, a: RC.turtle(C(a[0]), C(a[1]), s, spikes=C(a[1])),
    "imp":      lambda s, a: RC.humanoid(C(a[0]), C(a[1]), trim=C(a[1]), hat=C(a[1]), hat_style="point", tool=C(a[0]), tool_kind="staff", size=.7 * s),
    "knight":   lambda s, a: RC.humanoid(C((.1, .1, .12)), C(a[0]), trim=C(a[1]), hat=C(a[0]), hat_style="helm", armor=C(a[0]), tool=C((.75, .75, .8)), tool_kind="sword", shield=C(a[1]), size=1.1 * s),
    "mage":     lambda s, a: RC.humanoid(C((.55, .65, .55)), C(a[0]), trim=C(a[1]), hat=C(a[0]), hat_style="hood", tool=C(a[1]), tool_kind="staff", cape=C(a[0]), size=s),
    "brute":    lambda s, a: RC.humanoid(C(a[0]), C(a[1]), trim=C(a[1]), size=1.45 * s, belly=True, tool=C((.4, .28, .16)), tool_kind="tool"),
    "bandit":   lambda s, a: RC.humanoid("skin", C(a[0]), trim=C(a[1]), hat=C(a[0]), hat_style="band", tool=C((.75, .75, .8)), tool_kind="dagger", size=s),
    "skeleton": lambda s, a: RC.humanoid(C((.93, .91, .85)), C((.85, .83, .78)), trim=C(a[0]), tool=C(a[1]), tool_kind="sword", shield=C(a[0]), size=s),
    "zombie":   lambda s, a: RC.recolor(VC._biped("zombie", C(a[0]), rot=1, size=s), {}),
    "wolf":     lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.1 * s, tail="bushy", snout=3),
    "boar":     lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.2 * s, horns="tooth", snout=3),
    "ram":      lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.2 * s, horns=C(a[1]), tail="short"),
    "cat":      lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.1 * s, tail="long", spots=C(a[1]), snout=2),
    "bear":     lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.6 * s, tail="short", snout=2),
    "toad":     lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=1.2 * s, tail=None, ears=None, snout=1, spots=C(a[1])),
    "behemoth": lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=2.0 * s, horns=C(a[1]), mane=C(a[1]), tail="long", snout=3),
    "rat":      lambda s, a: Q(fur=C(a[0]), belly=C(a[1]), size=.8 * s, tail="long", ears="up", snout=2),
    "lizard":   lambda s, a: RC.recolor(VC.plan("gila_monster"), {}),
    "bat":      lambda s, a: B(C(a[0]), C(a[1]), size=1.0 * s, beak_len=1, wing_len=12, tail_len=1, legs_h=1),
    "hawk":     lambda s, a: B(C(a[0]), C(a[1]), size=1.5 * s, beak_len=2, crest=C(a[1]), wing_len=11),
    "cock":     lambda s, a: B(C(a[0]), C(a[1]), size=1.3 * s, beak_len=1, crest=C((.9, .2, .2)), legs_h=4, tail_len=4),
    "bee":      lambda s, a: VC._bee(size=1.6 * s, body=(C(a[0]), "bee_k")),
    "beetle":   lambda s, a: VC._insect("beetle"),
    "spider":   lambda s, a: VC._insect("spider"),
    "scorpion": lambda s, a: VC._insect("scorpion"),
    "moth":     lambda s, a: VC._insect("moth"),
    "mantis":   lambda s, a: VC._insect("grasshopper"),
    "worm":     lambda s, a: VC._insect("centipede"),
    "snail":    lambda s, a: VC._insect("snail"),
    "jelly":    lambda s, a: VC._sea("jellyfish"),
    "squid":    lambda s, a: VC._sea("octopus"),
    "shark":    lambda s, a: VC._sea("shark"),
    "ray":      lambda s, a: VC._sea("manta"),
    "angler":   lambda s, a: VC._sea("anglerfish"),
    "raptor":   lambda s, a: VC._dino("raptor"),
    "tyrant":   lambda s, a: VC._dino("allosaurus"),
    "horned":   lambda s, a: VC._dino("triceratops"),
    "drake":    lambda s, a: VD.plan("dragon_%s_drake_03" % a[0]),
    "wyvern":   lambda s, a: VD.plan("dragon_%s_wyvern_02" % a[0]),
    "plant":    lambda s, a: VC._plant("venus_flytrap"),
    "pitcher":  lambda s, a: VC._plant("pitcher"),
}
CM = {"beetle": 30, "spider": 32, "scorpion": 34, "moth": 30, "mantis": 30, "worm": 32, "snail": 34, "jelly": 18, "squid": 16,
      "shark": 12, "ray": 14, "angler": 18, "raptor": 12, "tyrant": 11, "horned": 11, "lizard": 20, "plant": 25, "pitcher": 25, "bee": 22}

# tier tints: base, then three swaps (each line picks a set)
TINTS = {
    "warm":  [(1, 1, 1), (1.25, .75, .55), (.75, .55, 1.15), (1.3, 1.15, .45)],
    "cool":  [(1, 1, 1), (.65, .9, 1.3), (.6, 1.2, .7), (1.2, .55, .6)],
    "earth": [(1, 1, 1), (.75, .85, .55), (1.2, .9, .6), (.55, .55, .75)],
    "dark":  [(1, 1, 1), (.7, .55, .9), (1.3, .5, .4), (.45, .45, .55)],
    "gem":   [(1, 1, 1), (.6, 1.1, 1.3), (1.3, .7, 1.1), (1.35, 1.2, .5)],
}

# line: (body, base colours, tint set, [4 names], zones, base level, hp, atk, def, spd, behaviour, element, size)
PORTAL = [
    ("slime", ((.35, .65, .95), (.6, .85, 1)), "cool", ["Drip", "Mire Drip", "Moss Drip", "Brass Drip"], ["meadow", "forest"], 1, 6, 4, 2, 4, "simple", "none", .8),
    ("wisp", ((.8, .75, .6), (.65, .6, .45)), "warm", ["Dust Mote", "Ember Mote", "Cinder Mote", "Sun Mote"], ["meadow", "desert", "hills"], 2, 7, 5, 3, 8, "caster", "fire", 1),
    ("orb", ((.45, .35, .55), (.95, .8, .2)), "dark", ["Peeper", "Glare Orb", "Ruin Orb", "Hollow Orb"], ["cave", "castle"], 5, 18, 9, 6, 6, "caster", "dark", 1),
    ("cap", ((.85, .3, .3), (.92, .88, .8)), "earth", ["Sporeling", "Rotcap", "Glowcap", "Bloodcap"], ["forest", "swamp"], 2, 9, 5, 4, 3, "status_sleep", "earth", 1),
    ("bat", ((.25, .2, .3), (.45, .35, .5)), "dark", ["Flitterwing", "Cave Flitter", "Dusk Flitter", "Bloodwing"], ["cave", "forest"], 2, 8, 6, 2, 12, "erratic", "dark", 1),
    ("rat", ((.5, .45, .4), (.7, .6, .55)), "earth", ["Gnawer", "Sewer Gnawer", "Plague Gnawer", "Iron Gnawer"], ["town_ruins", "cave"], 1, 6, 5, 2, 9, "swarm", "none", 1),
    ("wolf", ((.45, .47, .5), (.7, .72, .75)), "cool", ["Grey Prowler", "Frost Prowler", "Moss Prowler", "Crimson Prowler"], ["hills", "forest", "snow"], 4, 16, 9, 5, 10, "pack", "none", 1),
    ("boar", ((.4, .28, .16), (.55, .4, .25)), "earth", ["Tusker", "Bramble Tusker", "Mud Tusker", "Iron Tusker"], ["forest", "meadow"], 3, 15, 8, 6, 6, "charge", "none", 1),
    ("toad", ((.4, .55, .3), (.7, .8, .4)), "earth", ["Croaker", "Bog Croaker", "Stone Croaker", "Venom Croaker"], ["swamp"], 3, 14, 7, 5, 4, "status_poison", "water", 1),
    ("bee", ((.95, .75, .2),), "warm", ["Stinger", "Red Stinger", "Violet Stinger", "Golden Stinger"], ["meadow", "forest"], 2, 8, 7, 3, 12, "status_poison", "none", 1),
    ("beetle", (), "gem", ["Horn Beetle", "Jade Beetle", "Ruby Beetle", "Gilt Beetle"], ["forest", "hills"], 4, 18, 8, 10, 4, "armored", "earth", 1),
    ("spider", (), "dark", ["Web Spinner", "Gloom Spinner", "Blood Spinner", "Ash Spinner"], ["cave", "forest"], 5, 17, 10, 6, 9, "status_bind", "dark", 1),
    ("scorpion", (), "warm", ["Sand Stinger", "Red Sting", "Black Sting", "Sun Sting"], ["desert"], 6, 22, 12, 9, 7, "status_poison", "earth", 1),
    ("worm", (), "earth", ["Tunneler", "Bog Tunneler", "Rock Tunneler", "Magma Tunneler"], ["cave", "desert"], 6, 26, 11, 6, 3, "ambush", "earth", 1),
    ("snail", (), "cool", ["Shellcrawl", "Mire Shell", "Frost Shell", "Opal Shell"], ["swamp", "coast"], 3, 16, 5, 12, 1, "armored", "water", 1),
    ("crab", ((.78, .45, .22), (.62, .35, .18)), "warm", ["Pincher", "Reef Pincher", "Ink Pincher", "Coral Pincher"], ["coast", "sea"], 5, 20, 11, 12, 4, "armored", "water", 1),
    ("jelly", (), "cool", ["Drift Bell", "Sting Bell", "Storm Bell", "Night Bell"], ["sea"], 6, 18, 9, 4, 6, "status_paralyze", "water", 1),
    ("shark", (), "cool", ["Fin Hunter", "Reef Hunter", "Deep Hunter", "Blood Hunter"], ["sea"], 9, 34, 16, 8, 11, "charge", "water", 1),
    ("squid", (), "dark", ["Inkling", "Reef Inkling", "Abyss Inkling", "Kraken Spawn"], ["sea"], 8, 30, 13, 7, 6, "multi_hit", "water", 1),
    ("serpent", ((.35, .55, .3), (.6, .5, .25)), "earth", ["Grass Coil", "Dune Coil", "Ice Coil", "Shadow Coil"], ["meadow", "desert", "snow", "cave"], 5, 20, 11, 6, 8, "status_poison", "none", 1),
    ("turtle", ((.35, .4, .25), (.45, .5, .3)), "earth", ["Shellback", "Spike Shell", "Moss Shell", "Basalt Shell"], ["coast", "swamp"], 6, 28, 8, 18, 2, "armored", "water", 1),
    ("imp", ((.55, .3, .65), (.95, .8, .3)), "dark", ["Trickling", "Hex Trickling", "Ember Trickling", "Void Trickling"], ["forest", "castle"], 7, 22, 9, 6, 11, "caster", "dark", 1),
    ("mage", ((.25, .2, .4), (.85, .75, .35)), "dark", ["Hedge Witch", "Bog Witch", "Frost Witch", "Ash Witch"], ["swamp", "tower"], 10, 30, 12, 8, 8, "caster_heal", "dark", 1),
    ("bandit", ((.4, .35, .25), (.6, .25, .2)), "earth", ["Footpad", "Highwayman", "Cutpurse", "Bandit Chief"], ["hills", "town_ruins"], 6, 24, 12, 8, 10, "steal", "none", 1),
    ("skeleton", ((.45, .4, .35), (.65, .62, .6)), "dark", ["Rattler", "Grave Rattler", "Crypt Rattler", "Bone Duke"], ["cave", "castle", "graveyard"], 8, 26, 13, 10, 7, "undead", "dark", 1),
    ("zombie", ((.4, .35, .25),), "earth", ["Shambler", "Bog Shambler", "Frost Shambler", "Plague Shambler"], ["graveyard", "swamp"], 7, 32, 12, 6, 2, "undead", "dark", 1),
    ("knight", ((.55, .57, .6), (.3, .3, .55)), "dark", ["Iron Squire", "Black Squire", "Rust Squire", "Gold Squire"], ["castle"], 12, 40, 17, 16, 7, "guard", "none", 1),
    ("brute", ((.45, .55, .35), (.4, .3, .2)), "earth", ["Bruiser", "Hill Bruiser", "Frost Bruiser", "Lava Bruiser"], ["hills", "snow"], 11, 55, 20, 9, 4, "heavy", "earth", 1),
    ("golem", ((.55, .52, .5), (.4, .38, .36), (.7, .85, 1)), "gem", ["Pebble Golem", "Clay Golem", "Iron Golem", "Star Golem"], ["mountain", "tower"], 14, 70, 22, 20, 3, "heavy", "earth", .9),
    ("mimic", ((.55, .35, .18), (.7, .65, .55)), "warm", ["Snapchest", "Toothchest", "Gilt Snapchest", "Doom Chest"], ["cave", "castle", "tower"], 10, 40, 22, 14, 6, "ambush", "none", 1),
    ("hawk", ((.5, .42, .32), (.85, .8, .7)), "cool", ["Cliff Kite", "Storm Kite", "Ash Kite", "Gale Kite"], ["mountain", "hills"], 7, 22, 12, 6, 14, "erratic", "air", 1),
    ("cock", ((.85, .75, .55), (.95, .9, .8)), "warm", ["Crestbeak", "Fire Crestbeak", "Stone Crestbeak", "Storm Crestbeak"], ["meadow", "hills"], 4, 14, 9, 5, 9, "status_stone", "none", 1),
    ("lizard", (), "warm", ["Sunscale", "Ember Scale", "Frost Scale", "Venom Scale"], ["desert", "mountain"], 7, 26, 12, 9, 8, "status_burn", "fire", 1),
    ("raptor", (), "earth", ["Clawrunner", "Dune Runner", "Ash Runner", "Night Runner"], ["hills", "desert"], 10, 36, 16, 9, 13, "pack", "none", 1),
    ("plant", (), "earth", ["Snapvine", "Mire Snap", "Thorn Snap", "Blood Snap"], ["swamp", "forest"], 5, 20, 10, 6, 1, "status_bind", "earth", 1),
    ("cat", ((.75, .55, .3), (.55, .35, .2)), "warm", ["Sandcat", "Rockcat", "Shadowcat", "Flamecat"], ["desert", "mountain"], 9, 30, 15, 8, 14, "multi_hit", "none", 1),
    ("bear", ((.4, .3, .2), (.55, .45, .35)), "cool", ["Grizzleback", "Frost Grizzle", "Moss Grizzle", "Ash Grizzle"], ["forest", "snow"], 12, 60, 22, 12, 5, "heavy", "none", 1),
    ("drake", ("fire",), "warm", ["Ember Drakeling", "Cinder Drake", "Smolder Drake", "Pyre Drake"], ["mountain", "volcano"], 16, 80, 26, 18, 9, "breath_fire", "fire", 1),
    ("wyvern", ("storm",), "cool", ["Sky Wyvernling", "Gale Wyvern", "Thunder Wyvern", "Tempest Wyvern"], ["mountain", "tower"], 18, 90, 28, 16, 13, "breath_bolt", "air", 1),
    ("behemoth", ((.35, .3, .22), (.75, .7, .6)), "dark", ["Hornback", "Ruin Hornback", "Iron Hornback", "Doom Hornback"], ["mountain", "castle"], 20, 140, 32, 22, 6, "heavy", "earth", 1),
]
PRISM = [
    ("slime", ((.7, .88, 1), (.92, .97, 1)), "cool", ["Gelfin", "Frost Gelfin", "Lava Gelfin", "Prism Gelfin"], ["plains", "forest"], 1, 10, 6, 3, 5, "simple", "water", .8),
    ("imp", ((.55, .3, .65), (.95, .8, .3)), "dark", ["Glimmerkin", "Hexkin", "Pyrekin", "Voidkin"], ["plains", "tower"], 2, 14, 7, 4, 10, "caster", "dark", 1),
    ("wolf", ((.2, .15, .12), (1, .45, .1)), "warm", ["Ash Hound", "Cinder Hound", "Frost Hound", "Storm Hound"], ["plains", "volcano", "snow"], 3, 22, 10, 6, 11, "pack", "fire", 1),
    ("cap", ((.45, .7, .55), (.9, .9, .85)), "earth", ["Mosspuff", "Sleepspore", "Gloomspore", "Kingspore"], ["forest", "swamp"], 2, 16, 6, 5, 3, "status_sleep", "earth", 1),
    ("bat", ((.3, .25, .35), (.5, .4, .55)), "dark", ["Skreel", "Cave Skreel", "Frost Skreel", "Vamp Skreel"], ["cave"], 3, 14, 8, 3, 14, "erratic", "dark", 1),
    ("hawk", ((.55, .75, .55), (.9, .85, .75)), "cool", ["Gale Harpy", "Storm Harpy", "Ash Harpy", "Sun Harpy"], ["mountain", "plains"], 8, 34, 14, 8, 15, "status_confuse", "air", 1),
    ("skeleton", ((.4, .38, .36), (.55, .55, .58)), "dark", ["Bone Lancer", "Grave Lancer", "Ice Lancer", "Doom Lancer"], ["crypt", "cave"], 6, 30, 14, 10, 7, "undead", "dark", 1),
    ("knight", ((.55, .55, .6), (.35, .35, .4)), "dark", ["Hollow Armor", "Rust Armor", "Rune Armor", "Black Armor"], ["castle", "crypt"], 12, 60, 20, 22, 6, "guard", "none", 1),
    ("golem", ((.7, .55, .25), (.45, .4, .35), (.35, .85, .95)), "gem", ["Cog Sentry", "Brass Sentry", "Steam Sentry", "Prism Sentry"], ["tower", "ruins"], 10, 55, 18, 20, 5, "heavy", "none", .9),
    ("golem", ((.95, .55, .55), (.8, .4, .45), (.95, .85, .7)), "cool", ["Coral Golem", "Tide Golem", "Pearl Golem", "Abyss Golem"], ["coast", "sea_cave"], 14, 80, 22, 24, 3, "heavy", "water", 1),
    ("turtle", ((.55, .58, .62), (.45, .4, .35)), "earth", ["Ironshell", "Moss Shell", "Lava Shell", "Star Shell"], ["coast", "volcano"], 9, 50, 12, 28, 2, "armored", "earth", 1.1),
    ("rat", ((.45, .4, .35), (.65, .55, .5)), "dark", ["Scrabbler", "Sewer Scrabbler", "Plague Scrabbler", "Rat Monarch"], ["town_ruins", "sewer"], 1, 9, 5, 2, 10, "swarm", "none", 1),
    ("lizard", (), "warm", ["Ember Newt", "Flame Newt", "Ice Newt", "Storm Newt"], ["volcano", "swamp"], 7, 32, 13, 10, 8, "status_burn", "fire", 1),
    ("scorpion", (), "warm", ["Dune Stalker", "Red Stalker", "Black Stalker", "Sun Stalker"], ["desert"], 9, 42, 16, 14, 7, "status_poison", "earth", 1),
    ("moth", (), "gem", ["Mirror Moth", "Dust Moth", "Moon Moth", "Prism Moth"], ["forest", "tower"], 6, 24, 9, 6, 12, "status_blind", "air", 1),
    ("mantis", (), "gem", ["Shardclaw", "Jade Shardclaw", "Ruby Shardclaw", "Gold Shardclaw"], ["crystal_cave"], 12, 50, 20, 14, 13, "multi_hit", "earth", 1),
    ("beetle", (), "gem", ["Quartz Scarab", "Topaz Scarab", "Onyx Scarab", "Royal Scarab"], ["desert", "crystal_cave"], 8, 40, 14, 18, 5, "armored", "earth", 1),
    ("orb", ((.15, .1, .25), (.85, .25, .85)), "dark", ["Void Eye", "Gaze Eye", "Doom Eye", "Night Eye"], ["tower", "crypt"], 14, 48, 18, 10, 9, "caster", "dark", 1.1),
    ("mage", ((.25, .25, .3), (1, .85, .35)), "dark", ["Lantern Ghoul", "Bog Ghoul", "Frost Ghoul", "Ember Ghoul"], ["swamp", "crypt"], 10, 44, 16, 10, 7, "caster_drain", "dark", 1),
    ("serpent", ((.8, .65, .4), (.6, .45, .25)), "earth", ["Sand Wyrm", "Glass Wyrm", "Mire Wyrm", "Grave Wyrm"], ["desert", "swamp"], 16, 90, 24, 14, 8, "ambush", "earth", 1.3),
    ("squid", (), "cool", ["Tide Kraken", "Reef Kraken", "Ink Kraken", "Deep Kraken"], ["sea"], 18, 110, 26, 14, 8, "multi_hit", "water", 1),
    ("jelly", (), "gem", ["Star Jelly", "Moon Jelly", "Storm Jelly", "Void Jelly"], ["sea", "sea_cave"], 8, 30, 12, 6, 6, "status_paralyze", "water", 1),
    ("ray", (), "cool", ["Glide Ray", "Storm Ray", "Ink Ray", "Sun Ray"], ["sea"], 12, 48, 18, 10, 13, "charge", "air", 1),
    ("angler", (), "dark", ["Lure Fish", "Deep Lure", "Abyss Lure", "Gloom Lure"], ["sea_cave"], 15, 60, 22, 12, 6, "ambush", "water", 1),
    ("ram", ((.85, .85, .9), (1, .9, .35)), "cool", ["Thunder Ram", "Frost Ram", "Ember Ram", "Storm Ram"], ["mountain", "snow"], 11, 56, 20, 14, 9, "charge", "air", 1),
    ("cat", ((.12, .1, .18), (.45, .25, .65)), "dark", ["Shade Panther", "Smoke Panther", "Blood Panther", "Star Panther"], ["forest", "ruins"], 13, 60, 22, 12, 15, "multi_hit", "dark", 1),
    ("bear", ((.3, .4, .25), (.4, .35, .25)), "earth", ["Moss Bruin", "Rock Bruin", "Ash Bruin", "Frost Bruin"], ["forest", "snow"], 15, 95, 26, 16, 5, "heavy", "earth", 1),
    ("behemoth", ((.3, .4, .25), (.75, .7, .6)), "dark", ["Moss Behemoth", "Ruin Behemoth", "Storm Behemoth", "Void Behemoth"], ["plains_far", "ruins"], 24, 220, 38, 26, 7, "heavy", "earth", 1),
    ("brute", ((.5, .5, .52), (.4, .4, .42)), "dark", ["Rune Gargoyle", "Gate Gargoyle", "Ice Gargoyle", "Ember Gargoyle"], ["castle", "tower"], 14, 70, 22, 22, 8, "guard", "dark", .9),
    ("bandit", ((.25, .25, .3), (.65, .15, .2)), "dark", ["Cutthroat", "Sky Pirate", "Sand Raider", "Shadow Raider"], ["plains", "airship"], 7, 34, 15, 9, 12, "steal", "none", 1),
    ("plant", (), "earth", ["Snaptrap", "Bog Snaptrap", "Thorn Snaptrap", "Blood Snaptrap"], ["forest", "swamp"], 6, 30, 13, 8, 1, "status_bind", "earth", 1),
    ("pitcher", (), "gem", ["Drinkbloom", "Acid Bloom", "Sleep Bloom", "Doom Bloom"], ["swamp"], 9, 36, 12, 9, 1, "status_poison", "earth", 1),
    ("wisp", ((.55, .95, .55), (.25, .55, .3)), "gem", ["Bog Lantern", "Will Lantern", "Grave Lantern", "Star Lantern"], ["swamp", "crypt"], 5, 20, 10, 5, 10, "caster", "light", 1),
    ("raptor", (), "warm", ["Clawstrider", "Sand Strider", "Ash Strider", "Thunder Strider"], ["plains", "desert"], 11, 50, 20, 10, 14, "pack", "none", 1),
    ("horned", (), "earth", ["Tricorn", "Iron Tricorn", "Moss Tricorn", "Magma Tricorn"], ["plains_far", "volcano"], 18, 130, 28, 24, 5, "charge", "earth", 1),
    ("tyrant", (), "dark", ["Fangking", "Ruin Fangking", "Storm Fangking", "Doom Fangking"], ["plains_far", "ruins"], 26, 260, 42, 22, 8, "heavy", "none", 1),
    ("drake", ("ice",), "cool", ["Rime Drakeling", "Frost Drake", "Glacier Drake", "Aurora Drake"], ["snow", "mountain"], 20, 140, 30, 20, 10, "breath_ice", "ice", 1),
    ("wyvern", ("shadow",), "dark", ["Dusk Wyvern", "Night Wyvern", "Blood Wyvern", "Void Wyvern"], ["crypt", "tower"], 22, 160, 32, 18, 14, "breath_dark", "dark", 1),
    ("mimic", ((.55, .15, .2), (.95, .78, .25)), "warm", ["Greedmaw", "Gilt Greedmaw", "Iron Greedmaw", "Prism Greedmaw"], ["tower", "crypt", "castle"], 15, 70, 28, 16, 7, "ambush", "none", 1),
    ("toad", ((.4, .6, .5), (.8, .85, .4)), "cool", ["Puddlehop", "Sleep Hop", "Ice Hop", "King Hop"], ["swamp", "plains"], 4, 22, 9, 6, 6, "status_sleep", "water", 1),
]
REALMS = {"portal": PORTAL, "prism": PRISM}
REALM_NAME = {"portal": "Portal Realm", "prism": "Prismheart Realm"}
ZONE_RATE = {   # steps between encounters (mean); towns and roads are safe
    "meadow": 32, "plains": 30, "plains_far": 24, "forest": 22, "hills": 24, "swamp": 18, "desert": 22, "snow": 22, "mountain": 18,
    "coast": 26, "sea": 20, "cave": 14, "crystal_cave": 14, "sea_cave": 14, "castle": 16, "tower": 14, "crypt": 12, "graveyard": 16,
    "town_ruins": 20, "ruins": 18, "sewer": 14, "volcano": 16, "airship": 30}


def _key(realm, t):
    return "%s_best_%s" % (realm, t.lower().replace(" ", "_").replace("'", ""))


TYPES = {}     # key -> dict(row)
for realm, lines in REALMS.items():
    for li, (body, base, tset, names, zones, lvl, hp, atk, df, spd, beh, elem, size) in enumerate(lines):
        for t in range(TIERS):
            mult = TINTS[tset][t]
            k = _key(realm, names[t])
            f = 1 + .55 * t
            TYPES[k] = {"key": k, "realm": REALM_NAME[realm], "name": names[t], "line": names[0], "tier": t + 1, "body": body,
                        "level": lvl + t * max(3, lvl // 2 + 2), "hp": int(hp * f * f), "attack": int(atk * f), "defence": int(df * f),
                        "speed": spd + t, "exp": int((hp + atk) * f * 1.2), "gold": int((hp // 2 + 3) * f),
                        "behaviour": beh, "element": elem, "zones": zones if t < 2 else zones + [z + "_deep" for z in zones[:1]],
                        "tint": list(mult), "_base": base, "_size": size * (1 + .08 * t), "voxel_cm": CM.get(body, 10) * (1 + .06 * t),
                        "export_name": "Mob_%s_%s" % ("Portal" if realm == "portal" else "Prism", names[t].replace(" ", "").replace("'", ""))}


def plan(key):
    r = TYPES[key]
    parts = BODY[r["body"]](r["_size"], r["_base"])
    return tierize(parts, r["tint"])


def types(realm):
    return [k for k, r in TYPES.items() if r["realm"] == REALM_NAME[realm]]


for realm in REALMS:
    VC.EXTRA["%s_bestiary" % realm] = (tuple(types(realm)), plan)
for k, r in TYPES.items():
    VC.NAMES[k] = r["export_name"]


def encounters(realm):
    """Zone -> mean steps between fights + weighted formations. Groups: swarmers come 3–6, normals 1–4 (mixed with a
    zone-mate), heavies 1–2, ambushers/mimics alone. Deep zones (`<zone>_deep`, far from the start) draw tiers 3–4."""
    rng = random.Random(len(realm) * 97)
    zones = {}
    for k in types(realm):
        for z in TYPES[k]["zones"]:
            zones.setdefault(z, []).append(k)
    out = {}
    for z, ks in sorted(zones.items()):
        forms = []
        for k in ks:
            r = TYPES[k]
            beh = r["behaviour"]
            n_lo, n_hi = (3, 6) if beh in ("swarm", "pack") else ((1, 1) if beh in ("ambush",) else ((1, 2) if beh in ("heavy", "guard") else (1, 4)))
            for n in range(n_lo, n_hi + 1):
                forms.append({"enemies": [k] * n, "weight": round(4 / (1 + abs(n - (n_lo + n_hi) / 2)) / r["tier"], 3)})
            mates = [m for m in ks if m != k and TYPES[m]["tier"] == r["tier"]]
            if mates and beh not in ("ambush", "heavy"):
                m = rng.choice(mates)
                forms.append({"enemies": [k, k, m], "weight": round(1.5 / r["tier"], 3)})
        base_zone = z.replace("_deep", "")
        lv = [TYPES[k]["level"] for k in ks]
        out[z] = {"steps_mean": ZONE_RATE.get(base_zone, 24) - (4 if z.endswith("_deep") else 0), "level_band": [min(lv), max(lv)],
                  "preemptive_chance": .08, "ambush_chance": .06 if not z.startswith(("cave", "crypt")) else .12,
                  "formations": sorted(forms, key=lambda f: -f["weight"])}
    return out


def write_data(root):
    d = os.path.join(root, "data", "rpg")
    os.makedirs(d, exist_ok=True)
    for realm in REALMS:
        rows = [{k: v for k, v in TYPES[k].items() if not k.startswith("_")} for k in types(realm)]
        with open(os.path.join(d, "%s-bestiary.json" % realm), "w", encoding="utf-8") as f:
            json.dump({"realm": REALM_NAME[realm], "schema": "daedalus.bestiary/v1", "source": "tools/blender/rpg_bestiary.py",
                       "note": "original names (REALMS.md rule 4); battle sprites: engines/unreal/art/claude-battle-sprites/<realm>/",
                       "types": rows}, f, indent=1)
        with open(os.path.join(d, "%s-encounters.json" % realm), "w", encoding="utf-8") as f:
            json.dump({"realm": REALM_NAME[realm], "schema": "daedalus.encounters/v1", "source": "tools/blender/rpg_bestiary.py",
                       "rule": "on each step in a zone, roll 1/steps_mean; pick a formation by weight; deep zones are far from the start",
                       "zones": encounters(realm)}, f, indent=1)
    return d


if __name__ == "__main__":
    import sys
    miss, empty = set(), []
    for k in TYPES:
        p = plan(k)
        if not sum(len(v) for v in p.values()):
            empty.append(k)
        for v in p.values():
            for *_, c in v:
                if c not in PAL:
                    miss.add(c)
    names = [r["export_name"] for r in TYPES.values()]
    dup = {n for n in names if names.count(n) > 1}
    print(len(TYPES), "types;", {r: len(types(r)) for r in REALMS}, "empty", empty[:3], "missing", sorted(miss)[:5], "dup", sorted(dup)[:5])
    if "--write" in sys.argv:
        print("wrote", write_data(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
    sys.exit(1 if miss or empty or dup else 0)
