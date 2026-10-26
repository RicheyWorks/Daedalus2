// SPDX-License-Identifier: MIT
// G87 Forge Commissions C++ port (G98), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public forge_commissions_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public forge_commissions_core_test.cpp
// Run with --write to regenerate forge_commissions_parity.txt (read by ForgeCommissionsParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusForgeCommissionsCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static Grade G(Weapon W, Material M, int T) { Grade Out{}; GradeWeapon(W, M, T, Out); return Out; }

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	Check("board seeded", Encode(CommissionBoard(7)[0]) == Encode(CommissionBoard(7)[0]) && CommissionBoard(7).size() == 3
		&& Encode(CommissionBoard(7)[0]) == "CMS 1 day=7 slot=0 HESPER SWORD COPPER min=FINE due=3 price=18");
	bool Tiers = true;
	for (int T = 0; T < 4; ++T) Tiers = Tiers && std::strcmp(Tier(MinTierTemper(static_cast<MinTier>(T))), MinTierName(static_cast<MinTier>(T))) == 0;
	Check("min tiers are ForgeGrades tiers", Tiers);
	const Commission C{ 1, 0, Patron::Brannoc, Weapon::Sword, Material::Steel, MinTier::Standard, 2, 40 };
	Delivery D;
	Deliver(C, G(Weapon::Sword, Material::Steel, 90), 2, 50, D);
	Check("clean work pays with tip", D.V == Verdict::Paid && D.Coins == 40 && D.TipCoins == 16 && D.RegardDelta == 5 && D.Line == "Rings true. That one goes on the ark.");
	Deliver(C, G(Weapon::Sword, Material::Steel, 90), 3, 50, D);
	Check("late pays half", D.V == Verdict::PaidLate && D.Coins == 20 && D.TipCoins == 0 && D.RegardDelta == 1);
	Deliver(C, G(Weapon::Sword, Material::Steel, 49), 1, 50, D);
	Check("soft comes back", D.V == Verdict::UnderTempered && !D.Paid() && D.Line == "Drydock Master Brannoc Slagg: Soft. Take it back to the quench.");
	Check("negative shifts refused", !Deliver(C, G(Weapon::Sword, Material::Steel, 90), -1, 50, D));
	CommissionLedger L;
	for (int i = 0; i < 30; ++i) L.Record(C, G(Weapon::Blaster, Material::Steel, 90), 1, D);
	Check("ledger clamps regard", L.Regard[0] == 0 && L.Coins == 0 && L.Delivered == 0 && Encode(D) == "CMD 1 WRONG_WEAPON coins=0 tip=0 regard-3 | Drydock Master Brannoc Slagg: That's not what I pinned.");

	if (WriteOut)
	{
		std::FILE* F = std::fopen("forge_commissions_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# forge_commissions_core_test.cpp --write: CMS/CMD 1 parity (hephaestus). Days 0..99, one running ledger.\n", F);
		CommissionLedger Book;
		for (int Day = 0; Day < 100; ++Day)
		{
			SplitRng Rng(static_cast<int64_t>(Day) * 13 + 5);
			for (const Commission& K : CommissionBoard(Day))
			{
				const Weapon W = Rng.NextInt(6) == 0 ? (K.W == Weapon::Sword ? Weapon::Blaster : Weapon::Sword) : K.W;
				Material M = K.M;
				if (Rng.NextInt(6) == 0) { int I = 0; while (CommissionMetal(I) != K.M) ++I; M = CommissionMetal((I + 1) % CommissionMetalCount); }
				const int T = Rng.NextInt(101);
				const int Shifts = Rng.NextInt(5);
				Delivery Dv;
				Book.Record(K, G(W, M, T), Shifts, Dv);
				std::fprintf(F, "%s | t=%d shifts=%d -> %s | coins=%d delivered=%d regard=%d\n", Encode(K).c_str(), T, Shifts, Encode(Dv).c_str(),
					Book.Coins, Book.Delivered, Book.Regard[static_cast<int>(K.P)]);
			}
		}
		std::fclose(F);
		std::printf("wrote forge_commissions_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
