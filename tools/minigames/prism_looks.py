#!/usr/bin/env python3
"""Prism Looks: Refraction Skins palette table for the Prismheart cabinets (art-master-flex, Looks lane).

Data only, cosmetic only: a skin recolours a cabinet's marquee, trim and glow and never touches rules, scores or
balance. Each of the 11 Satchel games gets three original skins: a house skin (always worn), a skin unlocked by the
game's Verdant Warden seal and one unlocked by its Heartglass seal (seal indices from prism_satchel.SEALS).
Colours are 0xRRGGBB integers. Every skin must keep its accent at least MIN_LUMA_GAP luma away from its base
(integer Rec.601 luma, 0..255) so trim text stays readable; the table is checked at import.

Python is the authority; DaedalusPrismLooksCore.h must match prism_looks_parity.txt byte for byte.
"""
import sys

SEAL_NAMES = ("none", "ember", "tide", "verdant", "gale", "umbra", "heartglass")
MIN_LUMA_GAP = 60

# game -> tuple of (skin id, display name, base, accent, glow, seal index needed)
SKINS = {
    "facetlock": (("facetlock_house", "Lattice Dawn", 0x1B2440, 0xE8D7A0, 0x7FD4FF, 0),
                  ("facetlock_verdant", "Copper Hinge", 0x2E1A12, 0xF0B27A, 0xFF8A3D, 3),
                  ("facetlock_heart", "Glassbound Key", 0x0E1E2A, 0xD9F7FF, 0xB48CFF, 6)),
    "glimmerloom": (("glimmerloom_house", "Warp and Weft", 0x2A1B3D, 0xF2D6E8, 0xFF7AC8, 0),
                    ("glimmerloom_verdant", "Indigo Bolt", 0x101A3A, 0xA9C4FF, 0x4F7BFF, 3),
                    ("glimmerloom_heart", "Spun Starlight", 0x15121F, 0xFFF4C2, 0xFFE066, 6)),
    "glowmoss": (("glowmoss_house", "Mossbed Lantern", 0x13261A, 0xC8F0A0, 0x6BFF8E, 0),
                 ("glowmoss_verdant", "Fernshade", 0x0F1F14, 0x9FE3B8, 0x2EE6A6, 3),
                 ("glowmoss_heart", "Sporelight Crown", 0x1C1430, 0xE6FFB3, 0xD2FF4D, 6)),
    "lumenpath": (("lumenpath_house", "Beamwright", 0x2B1608, 0xFFD9A0, 0xFFB000, 0),
                  ("lumenpath_verdant", "Kiln Mirror", 0x331010, 0xFFC2B0, 0xFF5A36, 3),
                  ("lumenpath_heart", "Noon Refractor", 0x1A1A2E, 0xFFFBE6, 0xFFF06A, 6)),
    "prismcairn": (("prismcairn_house", "Stacked Slate", 0x22262B, 0xD8DEE6, 0x8FD18B, 0),
                   ("prismcairn_verdant", "Lichen Cairn", 0x1B2617, 0xD6E8B0, 0xA6E05A, 3),
                   ("prismcairn_heart", "Summit Geode", 0x241032, 0xF0D9FF, 0xC77DFF, 6)),
    "prismvault": (("prismvault_house", "Strongroom Umber", 0x1E1612, 0xE0C9A6, 0xC9A14A, 0),
                   ("prismvault_verdant", "Tumbler Teal", 0x0D2426, 0xA8E6E0, 0x2BC4B4, 3),
                   ("prismvault_heart", "Sealed Sunburst", 0x14100A, 0xFFE9B0, 0xFFC93C, 6)),
    "shadewatch": (("shadewatch_house", "Night Sentry", 0x0C0E1A, 0xB8C2E6, 0x6A7BFF, 0),
                   ("shadewatch_verdant", "Owl Ember", 0x1A0E0C, 0xE6B8A8, 0xFF6B4A, 3),
                   ("shadewatch_heart", "Eclipse Watch", 0x07070C, 0xE8E8FF, 0xFFFFFF, 6)),
    "shardfall": (("shardfall_house", "Falling Ember", 0x2A0F0A, 0xFFC7A8, 0xFF6A2B, 0),
                  ("shardfall_verdant", "Cinder Rain", 0x1A1A1A, 0xE6E6E6, 0xFF9E40, 3),
                  ("shardfall_heart", "Meteor Choir", 0x100A24, 0xFFE0F0, 0xFF4FD8, 6)),
    "shardring": (("shardring_house", "Tidal Ring", 0x0A1E2E, 0xBFE6FF, 0x3FB8FF, 0),
                  ("shardring_verdant", "Kelp Halo", 0x0E2418, 0xBEEBC8, 0x46D98A, 3),
                  ("shardring_heart", "Moonwater Crown", 0x0B0B22, 0xE0E8FF, 0x9FB4FF, 6)),
    "spiritkite": (("spiritkite_house", "Gale Ribbon", 0x14263A, 0xDDF0FF, 0x8AE0FF, 0),
                   ("spiritkite_verdant", "Thistle Draft", 0x2A1530, 0xF0D0F5, 0xD27BFF, 3),
                   ("spiritkite_heart", "Aurora Tail", 0x061A1A, 0xD8FFF4, 0x5CFFD0, 6)),
    "wardens_accord": (("wardens_accord_house", "Oathstone Blue", 0x14203A, 0xD6DCF0, 0x5C8CFF, 0),
                       ("wardens_accord_verdant", "Grove Pact", 0x182614, 0xDCEBC4, 0x8CCF4E, 3),
                       ("wardens_accord_heart", "Heartglass Charter", 0x1E0F1E, 0xFFE3F2, 0xFF7AB6, 6)),
}


def luma(rgb):
    r, g, b = (rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255
    return (299 * r + 587 * g + 114 * b) // 1000


def luma_gap(skin):
    return abs(luma(skin[3]) - luma(skin[2]))


def check_table():
    seen = set()
    for game, skins in SKINS.items():
        if len(skins) != 3 or [s[5] for s in skins] != [0, 3, 6]:
            raise ValueError(f"{game}: needs house, verdant and heartglass skins")
        for s in skins:
            if s[0] in seen or not s[0].startswith(game + "_"):
                raise ValueError(f"bad or duplicate skin id {s[0]!r}")
            seen.add(s[0])
            if any(not 0 <= c <= 0xFFFFFF for c in s[2:5]):
                raise ValueError(f"{s[0]}: colour out of range")
            if luma_gap(s) < MIN_LUMA_GAP:
                raise ValueError(f"{s[0]}: accent too close to base ({luma_gap(s)})")


def unlocked(game, seal):
    """Skin ids a player with this best seal on this game may wear (house always)."""
    if game not in SKINS:
        raise ValueError(f"unknown game {game!r}")
    if not isinstance(seal, int) or isinstance(seal, bool) or not 0 <= seal < len(SEAL_NAMES):
        raise ValueError("seal is a whole number 0..6")
    return [s[0] for s in SKINS[game] if s[5] <= seal]


def pick(game, seal, skin_id):
    """The skin to show: the requested one if worn legally, else the house skin (never an error)."""
    ok = unlocked(game, seal)
    return skin_id if skin_id in ok else SKINS[game][0][0]


check_table()

if __name__ == "__main__":
    for g in sorted(SKINS):
        for s in SKINS[g]:
            print(f"{g:15} {s[0]:24} {s[1]:20} {s[2]:06X} {s[3]:06X} {s[4]:06X} {SEAL_NAMES[s[5]]:10} gap={luma_gap(s)}")
    sys.exit(0)
