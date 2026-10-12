"""Project rules. Override any key with --config my.json (merged shallowly)."""
import json

DEFAULT_CONFIG = {
    "default_world": "Sky Islands (World Zero)",
    "unassigned": "Unassigned",
    # name token (the part after Kind_) -> (world, owner)
    "tags": {
        "BUF": ["Buffffff Island", "buffffff"],
        "AMF": ["Kennel Isle (Art Master Flex)", "art-master-flex"],
        "YTM": ["Youtube Master Island", "youtube-master"],
        "Orr": ["Orrery Reach (Claude Island)", "unreal-team"],
        "SOL": ["Sol Reach / Sol Island (Codex)", "team-codex"],
        "DS": ["DiskSaver Island", "disk-saver"],
        "BBIsle": ["Blender Boss Island", "blender-boss"],
        "OR": ["OddsReaper Island", "oddsreaper"],
        "Odds": ["OddsReaper Island", "oddsreaper"],
        "PROM": ["Prometheus Island", "prometheus"],
        "Pyth": ["Pythagoras Island", "pythagoras"],
        "Poot": ["Pootscoot Island", "pootscoot"],
        "Heph": ["Hephaestus Island", "hephaestus"],
        "Ark2H": ["Ark Dock Isle (2Hot2Trot)", "2hot2trot"],
        "Realm": ["Portal Realm (8-bit)", "shared"],
    },
    # path fragment (lowercase, / separators) -> (world, owner); first match wins
    "folders": [
        ["art/buffffff/", "Buffffff Island", "buffffff"],
        ["art/glb/amf/", "Kennel Isle (Art Master Flex)", "art-master-flex"],
        ["art/notes/amf/", "Kennel Isle (Art Master Flex)", "art-master-flex"],
        ["art/glb/pythagoras/", "Pythagoras Island", "pythagoras"],
        ["content/pythagoras/", "Pythagoras Island", "pythagoras"],
        ["art/oddsreaper/", "OddsReaper Island", "oddsreaper"],
        ["art/prometheus_island/", "Prometheus Island", "prometheus"],
        ["art/notes/disksaver/", "DiskSaver Island", "disk-saver"],
        ["art/sol-reach", "Sol Reach / Sol Island (Codex)", "team-codex"],
        ["content/codex/pootscootisland/", "Pootscoot Island", "pootscoot"],
        ["content/daedalus/world_zero/", "Sky Islands (World Zero)", "shared"],
    ],
    # ordered keyword rules: first match on lowercase "kind name" wins
    "categories": [
        ["water", ["water", "well", "cistern", "trough", "aqua", "spring", "aqueduct", "rain", "still", "pump", "filter"]],
        ["chests/containers", ["chest", "crate", "barrel", "locker", "box", "sack", "basket", "jar", "urn", "vault"]],
        ["herbs", ["herb", "yarrow", "selfheal", "valerian", "mullein", "sorrel", "wintergreen", "ramsons", "meadowsweet", "tonic", "brew", "potion", "succession"]],
        ["NFT landmarks", ["nft", "deed", "landmark", "monument", "statue", "spire", "obelisk", "beacon", "orrery", "portal", "gate"]],
        ["fauna/livestock", ["mob_", "goat", "hen", "cow", "pig", "sheep", "buffalo", "coop", "pen", "hive", "feeder", "hayrack", "shelter", "livestock", "capybara"]],
        ["weapons/armor", ["wpn", "sword", "spear", "blade", "axe_", "bow", "shield", "mail", "armor", "helm"]],
        ["tools", ["tool_", "pickaxe", "hoe", "shovel", "hammer"]],
        ["vehicles/arks", ["veh_", "ark", "boat", "kart", "plane", "drone", "heli"]],
        ["buildings", ["bld_", "house", "cottage", "barn", "tower", "shop", "hut", "bridge", "dock", "wall"]],
        ["food/crops", ["food", "crop", "berry", "fruit", "seed", "grain", "bread", "wheat", "carrot", "dish", "egg", "milk"]],
        ["flora", ["tree", "bloom", "flower", "shroom", "mushroom", "fern", "moss", "vine", "root", "cactus", "grass", "shrub", "alder", "hazel", "elder", "bramble", "gorse", "clover", "sedge", "log", "stump", "leaf", "flora"]],
        ["ores/materials", ["ore", "ingot", "nugget", "coal", "copper", "iron", "gold", "crystal", "starmetal", "gem", "stone", "rock"]],
        ["sky", ["sky_", "cloud", "star", "moon", "sun"]],
        ["items (other)", ["item_"]],
        ["props (other)", ["prop_"]],
    ],
    # worlds always listed (zero-filled) even when no asset maps to them yet
    "worlds": ["Sky Islands (World Zero)", "Portal Realm (8-bit)", "Parcels", "Bricks", "Gallery City", "The Labyrinth", "Space (Phase 2)",
               "Hephaestus Island", "Ark Dock Isle (2Hot2Trot)"],
    "kinds": ["Tool", "Item", "Mob", "Veh", "Bld", "Prop", "Sky", "Wpn"],
}


def load(path=None):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path:
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg
