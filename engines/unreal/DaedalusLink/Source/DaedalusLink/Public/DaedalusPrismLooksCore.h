// SPDX-License-Identifier: MIT
// Prism Looks: Refraction Skins palette table for the 11 Prismheart cabinets (art-master-flex, Looks lane).
// Header-only C++17 port of tools/minigames/prism_looks.py (Python rules are the authority); parity is checked by
// engines/unreal/core-test/prism_looks_core_test.cpp against prism_looks_parity.txt. Cosmetic data only: no rules,
// scores or balance. Integer only, no RNG, no I/O, no exceptions, no engine includes.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus::prism_looks {

constexpr int SealCount = 7;  // prism_satchel Seals: none, ember, tide, verdant, gale, umbra, heartglass
constexpr int MinLumaGap = 60;

struct Skin
{
	const char* Game;
	const char* Id;
	const char* Name;
	uint32_t Base;    // 0xRRGGBB marquee and body
	uint32_t Accent;  // 0xRRGGBB trim and text, at least MinLumaGap luma from Base
	uint32_t Glow;    // 0xRRGGBB emissive
	int Seal;         // best Warden seal needed on this game (0 house, 3 verdant, 6 heartglass)
};

// Sorted by game, three skins each (house, verdant, heartglass).
inline const std::array<Skin, 33> Skins = {{
	{"facetlock", "facetlock_house", "Lattice Dawn", 0x1B2440, 0xE8D7A0, 0x7FD4FF, 0},
	{"facetlock", "facetlock_verdant", "Copper Hinge", 0x2E1A12, 0xF0B27A, 0xFF8A3D, 3},
	{"facetlock", "facetlock_heart", "Glassbound Key", 0x0E1E2A, 0xD9F7FF, 0xB48CFF, 6},
	{"glimmerloom", "glimmerloom_house", "Warp and Weft", 0x2A1B3D, 0xF2D6E8, 0xFF7AC8, 0},
	{"glimmerloom", "glimmerloom_verdant", "Indigo Bolt", 0x101A3A, 0xA9C4FF, 0x4F7BFF, 3},
	{"glimmerloom", "glimmerloom_heart", "Spun Starlight", 0x15121F, 0xFFF4C2, 0xFFE066, 6},
	{"glowmoss", "glowmoss_house", "Mossbed Lantern", 0x13261A, 0xC8F0A0, 0x6BFF8E, 0},
	{"glowmoss", "glowmoss_verdant", "Fernshade", 0x0F1F14, 0x9FE3B8, 0x2EE6A6, 3},
	{"glowmoss", "glowmoss_heart", "Sporelight Crown", 0x1C1430, 0xE6FFB3, 0xD2FF4D, 6},
	{"lumenpath", "lumenpath_house", "Beamwright", 0x2B1608, 0xFFD9A0, 0xFFB000, 0},
	{"lumenpath", "lumenpath_verdant", "Kiln Mirror", 0x331010, 0xFFC2B0, 0xFF5A36, 3},
	{"lumenpath", "lumenpath_heart", "Noon Refractor", 0x1A1A2E, 0xFFFBE6, 0xFFF06A, 6},
	{"prismcairn", "prismcairn_house", "Stacked Slate", 0x22262B, 0xD8DEE6, 0x8FD18B, 0},
	{"prismcairn", "prismcairn_verdant", "Lichen Cairn", 0x1B2617, 0xD6E8B0, 0xA6E05A, 3},
	{"prismcairn", "prismcairn_heart", "Summit Geode", 0x241032, 0xF0D9FF, 0xC77DFF, 6},
	{"prismvault", "prismvault_house", "Strongroom Umber", 0x1E1612, 0xE0C9A6, 0xC9A14A, 0},
	{"prismvault", "prismvault_verdant", "Tumbler Teal", 0x0D2426, 0xA8E6E0, 0x2BC4B4, 3},
	{"prismvault", "prismvault_heart", "Sealed Sunburst", 0x14100A, 0xFFE9B0, 0xFFC93C, 6},
	{"shadewatch", "shadewatch_house", "Night Sentry", 0x0C0E1A, 0xB8C2E6, 0x6A7BFF, 0},
	{"shadewatch", "shadewatch_verdant", "Owl Ember", 0x1A0E0C, 0xE6B8A8, 0xFF6B4A, 3},
	{"shadewatch", "shadewatch_heart", "Eclipse Watch", 0x07070C, 0xE8E8FF, 0xFFFFFF, 6},
	{"shardfall", "shardfall_house", "Falling Ember", 0x2A0F0A, 0xFFC7A8, 0xFF6A2B, 0},
	{"shardfall", "shardfall_verdant", "Cinder Rain", 0x1A1A1A, 0xE6E6E6, 0xFF9E40, 3},
	{"shardfall", "shardfall_heart", "Meteor Choir", 0x100A24, 0xFFE0F0, 0xFF4FD8, 6},
	{"shardring", "shardring_house", "Tidal Ring", 0x0A1E2E, 0xBFE6FF, 0x3FB8FF, 0},
	{"shardring", "shardring_verdant", "Kelp Halo", 0x0E2418, 0xBEEBC8, 0x46D98A, 3},
	{"shardring", "shardring_heart", "Moonwater Crown", 0x0B0B22, 0xE0E8FF, 0x9FB4FF, 6},
	{"spiritkite", "spiritkite_house", "Gale Ribbon", 0x14263A, 0xDDF0FF, 0x8AE0FF, 0},
	{"spiritkite", "spiritkite_verdant", "Thistle Draft", 0x2A1530, 0xF0D0F5, 0xD27BFF, 3},
	{"spiritkite", "spiritkite_heart", "Aurora Tail", 0x061A1A, 0xD8FFF4, 0x5CFFD0, 6},
	{"wardens_accord", "wardens_accord_house", "Oathstone Blue", 0x14203A, 0xD6DCF0, 0x5C8CFF, 0},
	{"wardens_accord", "wardens_accord_verdant", "Grove Pact", 0x182614, 0xDCEBC4, 0x8CCF4E, 3},
	{"wardens_accord", "wardens_accord_heart", "Heartglass Charter", 0x1E0F1E, 0xFFE3F2, 0xFF7AB6, 6},
}};

inline int Luma(uint32_t Rgb)
{
	const int R = static_cast<int>((Rgb >> 16) & 255u), G = static_cast<int>((Rgb >> 8) & 255u), B = static_cast<int>(Rgb & 255u);
	return (299 * R + 587 * G + 114 * B) / 1000;
}

inline int LumaGap(const Skin& S)
{
	const int D = Luma(S.Accent) - Luma(S.Base);
	return D < 0 ? -D : D;
}

inline bool KnownGame(const std::string& Game)
{
	for (const Skin& S : Skins)
		if (Game == S.Game) return true;
	return false;
}

// Skin ids a player with this best seal may wear on this game; false for an unknown game or a seal outside 0..6.
inline bool Unlocked(const std::string& Game, int Seal, std::vector<std::string>& Out)
{
	Out.clear();
	if (!KnownGame(Game) || Seal < 0 || Seal >= SealCount) return false;
	for (const Skin& S : Skins)
		if (Game == S.Game && S.Seal <= Seal) Out.emplace_back(S.Id);
	return true;
}

// The skin to show: the wanted one if legally worn, else the game's house skin. Empty for a bad game or seal.
inline std::string Pick(const std::string& Game, int Seal, const std::string& Want)
{
	std::vector<std::string> Ok;
	if (!Unlocked(Game, Seal, Ok)) return std::string();
	for (const std::string& Id : Ok)
		if (Id == Want) return Id;
	return Ok.front();
}

}  // namespace daedalus::prism_looks
