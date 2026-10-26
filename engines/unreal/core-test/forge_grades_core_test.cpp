// SPDX-License-Identifier: MIT
// DFW 1 (Forge Weapon Grades) C++ port, checked without Unreal. Build:
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public forge_grades_core_test.cpp
// Run with --write to regenerate forge_grades_parity.txt (read by ForgeGradesParityTest.java, which must match line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusForgeGradesCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static std::string Enc(Weapon W, Material M, int T) { Grade G; return GradeWeapon(W, M, T, G) ? Encode(G) : std::string("REFUSED"); }

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	Check("neutral bronze sword golden", Enc(Weapon::Sword, Material::Bronze, 50) == "DFW 1 SWORD BRONZE t=50 tier=STANDARD dmg=1000 heat=1000 spread=1000 dur=160");
	Check("masterwork starmetal blaster golden", Enc(Weapon::Blaster, Material::Starmetal, 100) == "DFW 1 BLASTER STARMETAL t=100 tier=MASTERWORK dmg=1437 heat=800 spread=900 dur=540");
	Check("obsidian sword +60 damage", [] { Grade G; GradeWeapon(Weapon::Sword, Material::Obsidian, 50, G); return G.DamagePm == 1240; }());
	Check("obsidian blaster +100 heat", [] { Grade G; GradeWeapon(Weapon::Blaster, Material::Obsidian, 50, G); return G.HeatPm == 1100; }());
	Check("tiers", std::string(Tier(0)) == "BRITTLE" && std::string(Tier(20)) == "CRUDE" && std::string(Tier(50)) == "STANDARD"
		&& std::string(Tier(80)) == "FINE" && std::string(Tier(95)) == "MASTERWORK" && std::string(Tier(19)) == "BRITTLE" && std::string(Tier(94)) == "FINE");
	Check("out of range refused", Enc(Weapon::Sword, Material::Iron, 101) == "REFUSED" && Enc(Weapon::Sword, Material::Iron, -1) == "REFUSED" && Tier(101) == nullptr);

	bool Bounded = true, Monotonic = true;
	for (int w = 0; w < WeaponCount; ++w)
		for (int m = 0; m < MaterialCount; ++m)
		{
			int PrevD = -1, PrevU = -1;
			for (int t = 0; t <= 100; ++t)
			{
				Grade G; GradeWeapon(static_cast<Weapon>(w), static_cast<Material>(m), t, G);
				if (G.DamagePm < PrevD || G.Durability < PrevU) Monotonic = false;
				if (G.DamagePm <= 0 || G.DamagePm > 1500 || G.HeatPm < 800 || G.HeatPm > 1300 || G.SpreadPm < 900 || G.SpreadPm > 1100 || G.Durability < 1) Bounded = false;
				PrevD = G.DamagePm; PrevU = G.Durability;
			}
		}
	Check("bounded for all 1616 cases", Bounded);
	Check("monotonic in temper", Monotonic);
	Check("deterministic", Enc(Weapon::Blaster, Material::Iron, 73) == Enc(Weapon::Blaster, Material::Iron, 73));

	if (WriteOut)
	{
		std::FILE* F = std::fopen("forge_grades_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# forge_grades_core_test.cpp --write: DFW 1 parity (hephaestus). One line per weapon x material x temper 0..100.\n", F);
		for (int w = 0; w < WeaponCount; ++w)
			for (int m = 0; m < MaterialCount; ++m)
				for (int t = 0; t <= 100; ++t)
					std::fprintf(F, "%s\n", Enc(static_cast<Weapon>(w), static_cast<Material>(m), t).c_str());
		std::fclose(F);
		std::printf("wrote forge_grades_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
