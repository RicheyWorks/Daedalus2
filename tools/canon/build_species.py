#!/usr/bin/env python3
"""Build Daedalus's species canon from the ComputerPets catalog (ADR-021).

    python tools/canon/build_species.py <ComputerPets>/web/src/lib/pets/catalog.ts \
        daedalus-core/src/main/resources/com/daedalus/world/ecology/species.tsv

ComputerPets owns the 221 kinds (key, name, rarity, temperament). This script adds the ecology a
sky island needs, from explicit tables below — every species is named in exactly one guild, so a
new kind in the catalog fails the build here instead of landing in a default bucket.

  guild     MEADOW | CANOPY | POND | DECOMPOSER | STARBORN | MARINE
  size      TINY | SMALL | MEDIUM | LARGE | SESSILE   (plants, fungi, corals: rooted)
  strategy  R | K   — r-selected (many young, fast, short-lived) or K-selected (few, slow, long)
  disperses 1 when it can cross open sky alone (wings, spores, wind); 0 when it needs an ark
"""
import re
import sys

GUILDS = {
    "MEADOW": """cat dog rabbit hamster guinea_pig turtle fox ferret hedgehog chinchilla iguana
        ball_python corn_snake kingsnake hognose garter boa milk_snake rosy_boa
        maidenhair saguaro venus_flytrap pitcher sundew orchid
        honeybee monarch luna firefly stick carpenter_ant ladybird mantis cicada bumblebee
        carpenter_bee mason_bee leafcutter stingless sweat_bee mining_bee honey_drone honey_queen
        honeycomb orb_weaver jumping_spider wolf_spider tarantula widow harvestman scorpion
        vinegaroon tick solifuge deer skunk opossum porcupine black_bear gecko skink horned_lizard
        box_turtle tuatara house_centipede velvet_worm field_cricket katydid grasshopper
        swallowtail lacewing earwig acorn_weevil click_beetle robber_fly penguin""",
    "CANOPY": """red_panda budgie parrot toucan green_tree_python carpet_python ginkgo oak
        crow raven barn_owl red_tail chickadee robin pileated hummingbird bat squirrel raccoon
        anole chameleon sloth lemur gibbon kinkajou colugo flying_squirrel howler tarsier potto
        koala""",
    "POND": """goldfish axolotl water_lily darner frog toad newt salamander caecilian crayfish
        pond_snail mussel leech stickleback paramecium amoeba euglena volvox diatom chlamydomonas
        stentor mallard canada_goose otter beaver capybara alligator crocodile snapper bass
        brook_trout catfish bluegill perch pike walleye paddlefish lamprey american_eel
        tardigrade planarian amphipod jewelwing""",
    "DECOMPOSER": """moss oyster fly_agaric morel chanterelle turkey_tail lions_mane puffball
        chicken_of_woods yeast lichen millipede pillbug earthworm springtail nematode coli
        haloarchaea""",
    "STARBORN": """dragon phoenix photovore choir nimbus silica terminator nexus halovore magneton
        umbral cyst cyber_dragon volt_dragon trace_dragon flux_dragon spark_dragon ion_dragon
        gauss_dragon relay_dragon fuse_dragon ground_dragon""",
    "MARINE": """octopus cuttlefish nautilus moon_jelly sea_star hermit_crab horseshoe_crab
        seahorse manta moray kelp fiddler_crab ghost_crab limpet barnacle chiton periwinkle
        sand_dollar sea_urchin knobbed_whelk lugworm brain_coral anemone clownfish parrotfish
        cleaner_shrimp sea_cucumber lionfish giant_clam eagle_ray grouper""",
}

SIZES = {
    "TINY": """honeybee firefly carpenter_ant ladybird bumblebee carpenter_bee mason_bee leafcutter
        stingless sweat_bee mining_bee honey_drone honey_queen tick springtail nematode coli
        haloarchaea paramecium amoeba euglena volvox diatom chlamydomonas stentor tardigrade
        planarian amphipod yeast earwig acorn_weevil click_beetle field_cricket aphid lacewing
        pillbug harvestman house_centipede millipede earthworm velvet_worm orb_weaver
        jumping_spider wolf_spider widow scorpion solifuge vinegaroon robber_fly grasshopper
        katydid cicada mantis stick luna monarch swallowtail darner jewelwing leech pond_snail
        mussel cyst limpet chiton periwinkle cleaner_shrimp""",
    "SMALL": """hamster guinea_pig rabbit chinchilla hedgehog ferret budgie chickadee robin
        hummingbird bat squirrel flying_squirrel gecko anole skink horned_lizard frog toad newt
        salamander caecilian crayfish stickleback goldfish bluegill perch axolotl tarsier
        chameleon garter hognose milk_snake rosy_boa corn_snake kingsnake tarantula box_turtle
        photovore choir nimbus halovore magneton umbral seahorse hermit_crab fiddler_crab
        ghost_crab sand_dollar sea_urchin sea_star clownfish lugworm knobbed_whelk""",
    "MEDIUM": """cat dog fox red_panda turtle parrot toucan penguin iguana ball_python boa
        green_tree_python carpet_python crow raven barn_owl red_tail pileated mallard
        canada_goose otter raccoon skunk opossum porcupine beaver tuatara snapper bass
        brook_trout catfish pike walleye lamprey american_eel paddlefish lemur kinkajou colugo
        potto sloth koala howler gibbon silica terminator nexus phoenix octopus cuttlefish
        nautilus moon_jelly horseshoe_crab moray parrotfish sea_cucumber lionfish""",
    "LARGE": """deer black_bear capybara alligator crocodile dragon cyber_dragon volt_dragon
        trace_dragon flux_dragon spark_dragon ion_dragon gauss_dragon relay_dragon fuse_dragon
        ground_dragon manta eagle_ray grouper""",
    "SESSILE": """moss maidenhair ginkgo oak water_lily orchid saguaro venus_flytrap pitcher sundew
        honeycomb oyster fly_agaric morel chanterelle turkey_tail lions_mane puffball
        chicken_of_woods lichen kelp brain_coral anemone barnacle giant_clam""",
}

# Crosses open sky without an ark: wings, spores, wind-borne cells.
DISPERSES = """budgie parrot toucan crow raven barn_owl red_tail chickadee robin pileated hummingbird
    mallard canada_goose bat phoenix honeybee monarch luna firefly darner ladybird bumblebee
    carpenter_bee mason_bee leafcutter stingless sweat_bee mining_bee honey_drone honey_queen
    cicada swallowtail jewelwing lacewing robber_fly click_beetle moss maidenhair oyster fly_agaric
    morel chanterelle turkey_tail lions_mane puffball chicken_of_woods yeast lichen coli
    haloarchaea nimbus dragon cyber_dragon volt_dragon flux_dragon spark_dragon ion_dragon""".split()


def table(groups):
    out = {}
    for name, keys in groups.items():
        for k in keys.split():
            out.setdefault(k, name)
    return out


def main(src, dst):
    text = open(src, encoding="utf-8").read()
    rows = re.findall(r'\{ key: "([^"]+)", displayName: "([^"]+)", rarity: "([A-Z]+)", '
                      r'temperament: "([^"]*)", habitat: "([^"]*)"', text)
    guild, size = table(GUILDS), table(SIZES)
    missing = [k for k, *_ in rows if k not in guild or k not in size]
    if missing:
        sys.exit("unclassified species (add them to the tables): " + ", ".join(missing))
    lines = ["# Daedalus species canon (ADR-021). Generated by tools/canon/build_species.py from the",
             "# ComputerPets catalog; edit the tables there, not this file.",
             "# key\tname\trarity\ttemperament\tguild\tsize\tstrategy\tdisperses"]
    for key, name, rarity, temperament, _habitat in rows:
        s = size[key]
        # Small, fast breeders are r-selected; big, slow, long-lived ones and rooted perennials K.
        strategy = "R" if s in ("TINY", "SMALL") else "K"
        if guild[key] == "DECOMPOSER":
            strategy = "R"
        lines.append("\t".join([key, name, rarity, temperament, guild[key], s, strategy,
                                "1" if key in DISPERSES else "0"]))
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(rows)} species -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
