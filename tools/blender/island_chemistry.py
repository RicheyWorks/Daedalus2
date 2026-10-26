# SPDX-License-Identifier: MIT
"""The seeded chemistry of an island (Richey 13:33: "the seed also needs a randomness of the chemistry of what we need
in our world ... the materials the island's built with and what's on the island is appropriate ... why does the tree
fruit, what do we do with the fruit, do we sell it ... adding to the MULE mechanic").

One call, `profile(seed)`, rolls everything the generators and the game need to agree on, so a Blender island and
the server's economy read the same facts from the same seed:

- geology  (ADR-050): grade COMMON/RICH/LEGENDARY, ore multipliers, starmetal crater, cave count, heartstone size
- water    (RingInfusion/tonics): spring purity, whether the well water needs the filter hut, fish in the lake
- soil     : fertility -> crop rows and yield; which crops; orchard species and what their fruit is for
- flora    (world dresser species + RingInfusion herbs): the herb set that grows here (3-6 of the six), tree species
- fauna    (kennel tonics): livestock kinds, hens, bees
- power    : what runs the island - windmill (wind), water wheel (stream), crystal lamp (crystal), forge (coal)
- economy  (M.U.L.E.-style four goods): FOOD, ENERGY, ORE, CRYSTAL supply from the above and which the island lacks,
  so trade between islands has a reason; the shop's stock follows the surplus, the inn's menu follows the crops.

Pure Python (no Blender, no Unreal). `manifest(seed)` returns the JSON the exporter writes next to the FBX.
"""
import json
import random
import zlib

HERBS = ("dawnleaf", "rillprism", "cinderbud", "stillmoss", "stridefern", "clearbell")   # docs/mechanics/RingInfusion.md
HERB_ESSENCE = {"dawnleaf": "warm", "rillprism": "cool", "cinderbud": "warm", "stillmoss": "calm", "stridefern": "quick", "clearbell": "cool"}
ORCHARD = {   # species -> (fruit, uses) ; uses name the mechanic that consumes it
    "apple": ("apple", ("eat", "sell", "cider@inn", "pony_treat@kennel")),
    "cherry": ("cherry", ("eat", "sell", "pie@inn", "dye_red@craft")),
    "plum": ("plum", ("eat", "sell", "jam@inn", "tonic_sweetener@brew")),
    "orange": ("orange", ("eat", "sell", "marmalade@inn", "clearbell_pairing@brew")),
    "pear": ("pear", ("eat", "sell", "perry@inn")),
    "lemon": ("lemon", ("sell", "filter_rinse@waterworks", "tonic_sour@brew")),
    "peach": ("peach", ("eat", "sell", "cobbler@inn", "waystone_offering@shrine")),
}
CROPS = {"barley": "skyfarer_ration@inn", "turnip": "stew@inn", "sunroot": "mana_draught@brew", "wheat": "bread@inn", "carrot": "stew@inn", "pumpkin": "lantern@craft", "beet": "dye_purple@craft", "corn": "feed@kennel", "cabbage": "stew@inn"}
LIVESTOCK = {"duneback": "mount@stable", "sheep": "wool@craft", "hen": "egg@inn", "cow": "milk@inn", "goat": "milk@inn", "bee": "honey@brew"}
FISH = ("rillperch", "glassfin", "skytrout", "ember_koi")
GRADES = (("COMMON", 0.70, 1.0, 1.0), ("RICH", 0.25, 2.2, 3.0), ("LEGENDARY", 0.05, 3.0, 3.0))   # ADR-050 odds and multipliers


# Every realm has its own chemistry (Richey 13:34): the same seed rolls different materials, flora, power and goods
# depending on the realm type. Each entry says what the realm is made of and which mechanic sheet row consumes it.
REALMS = {
    "WORLD-ZERO": {"type": "sky islands (asteroid-shattered planet)", "materials": ("grass", "dirt", "rock", "sand", "deepstone", "heartstone"),
                   "ores": ("coal", "copper", "iron", "gold", "starmetal"), "herbs": HERBS, "orchard": tuple(ORCHARD), "crops": tuple(CROPS),
                   "livestock": tuple(LIVESTOCK), "power": ("windmill", "water_wheel", "crystal_lamp"), "water": "sky rivers, lakes, waterfalls",
                   "story": "docs/adr/ADR-040 + REALMS.md: heal the planet with the Heartstones; arks tow lands together",
                   "mechanics": ("ADR-049 dig/build", "ADR-050 ores/heartstone", "RingInfusion brews", "Kennel tonics", "ADR-054 town", "airship docks")},
    "LABYRINTH": {"type": "stone maze realm (Daedalus itself)", "materials": ("stone", "moss", "torch_iron", "chalk", "thread", "bone"),
                  "ores": ("iron", "silver"), "herbs": ("stillmoss", "clearbell"), "orchard": ("plum",), "crops": ("pumpkin", "beet"),
                  "livestock": ("goat",), "power": ("torch_oil", "echo_bell"), "water": "cisterns and drips",
                  "story": "Mechanics sheet LAB01-LAB11: chalk charges, thread routes, echo bells, Halloween folklore lives here only",
                  "mechanics": ("LAB01 chalk", "LAB02 thread", "LAB03 echo bell", "LAB06 hornback troughs", "LAB09 Halloween")},
    "GALLERY-CITY": {"type": "living-paintings city", "materials": ("canvas", "frame_wood", "pigment", "glass", "plaster"),
                     "ores": ("copper", "cobalt"), "herbs": ("rillprism", "dawnleaf"), "orchard": ("cherry", "orange"), "crops": ("beet",),
                     "livestock": ("bee",), "power": ("colour_prism", "drone_fans"), "water": "fountains and canals",
                     "story": "GAL01-GAL03: restore murals, make colour useful; pigments come from beets, cherries, cobalt",
                     "mechanics": ("GAL01 colour knowledge", "GAL02 frame streets", "GAL03 curator proof")},
    "PARCELS": {"type": "patchwork farm suburbs with mail routes", "materials": ("soil", "fence_wood", "brick", "tin", "hay"),
                "ores": ("iron", "tin"), "herbs": ("stridefern", "dawnleaf", "stillmoss"), "orchard": ("apple", "pear"), "crops": tuple(CROPS),
                "livestock": ("cow", "hen", "sheep"), "power": ("windmill", "helipad_fuel"), "water": "ponds, irrigation ditches, troughs",
                "story": "PAR01-PAR03: mail, farming, boundary help; the AMF trough feeds companions",
                "mechanics": ("PAR01 mail/farming", "PAR02 roads/fields", "PAR03 trough")},
    "BRICKS": {"type": "modular construction realm (repair after the Unmaker)", "materials": ("brick", "stud_plastic", "runway_tar", "gear_metal"),
               "ores": ("iron", "copper", "gold"), "herbs": ("cinderbud",), "orchard": ("lemon",), "crops": ("corn",),
               "livestock": ("hen",), "power": ("workshop_generator", "plane_fuel"), "water": "sea docks",
               "story": "BRK01-BRK03: repair scattered assemblies, restore the airfield, plane/hover cart travel",
               "mechanics": ("BRK01 repair", "BRK02 modules", "BRK03 transport")},
    "PORTAL": {"type": "8-bit console-RPG realm (towns, caves, castles; original names only, REALMS.md)", "materials": ("stone", "wood", "iron", "dragon_scale", "egg_shell"),
               "ores": ("iron", "silver", "gold"), "herbs": tuple(HERBS), "orchard": ("apple", "plum"), "crops": ("wheat", "cabbage"),
               "livestock": ("cow", "hen", "bee"), "power": ("torch_oil", "dragon_fire"), "water": "wells, the keeper's waterworks",
               "story": "PORT01-PORT12: keys and gates, inns and shops, land eggs that hatch, RingInfusion brews",
               "mechanics": ("PORT01 keys", "PORT03 inn/shop", "PORT06 egg stages", "RingInfusion")},
    "PRISMHEART": {"type": "16-bit crystal-era party RPG (ADR-067): crystal shrines, an airship, job classes, summon spirits",
                   "materials": ("stone", "wood", "prism_glass", "skysilk", "brass"),
                   "ores": ("iron", "silver", "gold", "starmetal"), "herbs": tuple(HERBS), "orchard": ("pear", "peach", "lemon"),
                   "crops": ("barley", "turnip", "sunroot"), "livestock": ("duneback", "hen", "goat"),
                   "power": ("crystal_lamp", "water_wheel", "windmill"), "water": "harbour cisterns and shrine springs",
                   "story": "ADR-067: six Prism Shards, the Skyfarer airship opens the map, waystones save, summon spirits answer shard-bearers",
                   "mechanics": ("PRISM01 job classes", "PRISM02 waystones", "PRISM03 shards + summons", "PRISM04 airship travel", "RingInfusion")},
}


# Chemistry algorithm version, written into every profile. v1 (until 2026-10-15) seeded from hash(realm), which Python
# salts per process, so v1 profiles are NOT reproducible. Manifests written under v1 stay as historical records:
# do not regenerate them. Re-rolling an old seed under v2 gives new chemistry; the geometry hooks are unchanged.
CHEM_ALGORITHM = "v2-crc32"


def profile(seed, realm="WORLD-ZERO"):
    realm = realm.upper()
    R = REALMS.get(realm, REALMS["WORLD-ZERO"])
    # zlib.crc32, not hash(): str hashes are salted per process (PYTHONHASHSEED), which made every island's chemistry
    # change from run to run. crc32 is stable, so the same seed and realm give the same chemistry in any process.
    rng = random.Random((seed * 1_000_003 + 17) ^ (zlib.crc32(realm.encode("utf-8")) & 0xFFFF))
    r = rng.random()
    grade = GRADES[0]
    acc = 0.0
    for g in GRADES:
        acc += g[1]
        if r < acc:
            grade = g
            break
    fertility = round(rng.uniform(0.3, 1.0), 2)
    purity = round(rng.uniform(0.2, 1.0), 2)
    pick = lambda pool, lo, hi: sorted(rng.sample(sorted(pool), min(len(pool), rng.randint(lo, hi))))
    herbs = pick(R["herbs"], 2, 6)
    orchard = pick(R["orchard"], 1, 3)
    crops = pick(R["crops"], 1, 2 if fertility < 0.6 else 3)
    livestock = pick(R["livestock"], 1, 3)
    fish = sorted(rng.sample(FISH, 2))
    power = rng.choice(R["power"])
    caves = rng.randint(1, 3)
    # the four goods, M.U.L.E.-style: what the island makes and what it must buy
    food = round(fertility * (len(crops) + len(orchard) * 0.5 + len(livestock) * 0.5), 2)
    energy = {"windmill": 1.0, "water_wheel": 1.3, "crystal_lamp": 0.8}.get(power, 1.0)
    ore = grade[2]
    crystal = round(grade[3] * 0.5 + (1.0 if grade[0] == "LEGENDARY" else 0.0), 2)
    goods = {"FOOD": food, "ENERGY": energy, "ORE": ore, "CRYSTAL": crystal}
    # Codex's salvage PowerUnit (contest-island-production: codex_salvage_assembly.py, seed 86100): GearboxHousing +
    # DriveShaft + TurbineRotor + CrystalBattery on a support frame. Our chemistry says what each part is made of and
    # where the island gets it, so a power unit is something you BUILD from the island's goods (Arc-Raiders salvage
    # vibe): rotor turned by wind or water, battery charged by crystal, gearbox forged from copper + iron.
    power_unit = {
        "parts": {"GearboxHousing": ["copper", "iron"], "DriveShaft": ["iron"], "TurbineRotor": ["iron", "copper"] if power == "windmill" else ["iron", "plank"],
                  "CrystalBattery": ["crystal"], "SupportFrame": ["rock", "plank"]},
        "drive": {"windmill": "wind at the rim", "water_wheel": "the stream", "crystal_lamp": "crystal only (no rotor)"}.get(power, "unknown"),
        "salvageable": grade[0] != "COMMON",      # rich/legendary lands start with a broken unit to repair
        "energy_per_unit": energy,
        "source": "codex_salvage_assembly.py PowerUnit (asset-only; wiring/snapping not implemented)",
    }
    surplus = max(goods, key=goods.get)
    need = min(goods, key=goods.get)
    return {
        "algorithm": CHEM_ALGORITHM,
        "seed": seed,
        "realm": realm,
        "realm_type": R["type"],
        "materials": list(R["materials"]),
        "ores_here": list(R["ores"]),
        "mechanics": list(R["mechanics"]),
        "story": R["story"],
        "geology": {"grade": grade[0], "ore_mult": grade[2], "gold_mult": grade[3], "starmetal_crater": grade[0] == "LEGENDARY",
                    "caves": caves, "heartstone_radius_m": 3 + (2 if grade[0] != "COMMON" else 0)},
        "water": {"spring_purity": purity, "filter_needed": purity < 0.6, "fish": fish},
        "soil": {"fertility": fertility, "crops": crops, "crop_rows": 3 + int(fertility * 4)},
        "flora": {"herbs": herbs, "herb_essences": {h: HERB_ESSENCE[h] for h in herbs},
                  "orchard": {s: {"fruit": ORCHARD[s][0], "uses": list(ORCHARD[s][1])} for s in orchard}},
        "fauna": {"livestock": {k: LIVESTOCK[k] for k in livestock}},
        "power_unit": power_unit,
        "power": {"source": power, "note": {"windmill": "mills the wheat; needs wind - sails face the rim",
                                            "water_wheel": "driven by the stream; sits by the filter hut",
                                            "crystal_lamp": "a crystal from the keel lights the smithy and the dock"}.get(power, "realm power source")},
        "economy": {"goods": goods, "surplus": surplus, "need": need,
                    "shop_stock": [ORCHARD[s][0] for s in orchard] + crops + herbs[:2],
                    "inn_menu": [CROPS.get(c, c) for c in crops] + [u for s in orchard for u in ORCHARD[s][1] if u.endswith("@inn")]},
    }


def manifest(seed, realm="WORLD-ZERO"):
    return json.dumps(profile(seed, realm), indent=1, sort_keys=True)


if __name__ == "__main__":
    import sys
    print(manifest(int(sys.argv[1]) if len(sys.argv) > 1 else 1, sys.argv[2] if len(sys.argv) > 2 else "WORLD-ZERO"))
