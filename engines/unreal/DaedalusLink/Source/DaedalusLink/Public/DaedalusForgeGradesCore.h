// SPDX-License-Identifier: MIT
// DFW 1, Forge Weapon Grades (hephaestus). Plain C++17, header-only, no Unreal types.
// Must agree byte for byte with com.daedalus.world.forge.ForgeGrades (forge_grades_parity.txt, checked by
// ForgeGradesParityTest.java). Integer per-mille math only, so there is no float formatting to drift.
#pragma once
#include <cstdint>
#include <cstdio>
#include <string>

namespace daedalus { namespace forge {

enum class Weapon : int { Sword = 0, Blaster = 1 };
enum class Material : int { Wood = 0, Stone, Copper, Bronze, Iron, Steel, Obsidian, Starmetal };
constexpr int WeaponCount = 2;
constexpr int MaterialCount = 8;

struct Grade
{
	Weapon W; Material M; int Temper; const char* Tier;
	int DamagePm, HeatPm, SpreadPm, Durability;
};

inline const char* WeaponName(Weapon W) { return W == Weapon::Sword ? "SWORD" : "BLASTER"; }
inline const char* MaterialName(Material M)
{
	static const char* N[MaterialCount] = { "WOOD", "STONE", "COPPER", "BRONZE", "IRON", "STEEL", "OBSIDIAN", "STARMETAL" };
	return N[static_cast<int>(M)];
}
inline int BaseDamagePm(Material M)
{
	static const int D[MaterialCount] = { 800, 900, 950, 1000, 1050, 1120, 1180, 1250 };
	return D[static_cast<int>(M)];
}
inline int BaseDurability(Material M)
{
	static const int D[MaterialCount] = { 60, 90, 120, 160, 200, 280, 140, 360 };
	return D[static_cast<int>(M)];
}

inline bool ValidTemper(int T) { return T >= 0 && T <= 100; }

// Tier label for a 0-100 temper score. Returns nullptr when out of range (Java throws IllegalArgumentException).
inline const char* Tier(int T)
{
	if (!ValidTemper(T)) return nullptr;
	if (T >= 95) return "MASTERWORK";
	if (T >= 80) return "FINE";
	if (T >= 50) return "STANDARD";
	if (T >= 20) return "CRUDE";
	return "BRITTLE";
}

// Grade a forged weapon. Returns false (and leaves Out alone) when temper is out of 0..100.
inline bool GradeWeapon(Weapon W, Material M, int Temper, Grade& Out)
{
	if (!ValidTemper(Temper)) return false;
	const int Delta = Temper - 50;
	int Damage = BaseDamagePm(M) * (1000 + 3 * Delta) / 1000;
	const int Durability = BaseDurability(M) * (500 + 10 * Temper) / 1000;
	int Heat = 1000, Spread = 1000;
	if (W == Weapon::Blaster)
	{
		Heat = 1000 - 4 * Delta;
		Spread = 1000 - 2 * Delta;
		if (M == Material::Obsidian) Heat += 100;
	}
	else if (M == Material::Obsidian)
	{
		Damage += 60;
	}
	Out = Grade{ W, M, Temper, Tier(Temper), Damage, Heat, Spread, Durability < 1 ? 1 : Durability };
	return true;
}

// Single-line DFW 1 encoding, identical to WeaponGrade.encode() in Java.
inline std::string Encode(const Grade& G)
{
	char Buf[160];
	std::snprintf(Buf, sizeof Buf, "DFW 1 %s %s t=%d tier=%s dmg=%d heat=%d spread=%d dur=%d",
		WeaponName(G.W), MaterialName(G.M), G.Temper, G.Tier, G.DamagePm, G.HeatPm, G.SpreadPm, G.Durability);
	return std::string(Buf);
}

}} // namespace daedalus::forge
