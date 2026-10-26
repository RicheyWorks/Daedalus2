// SPDX-License-Identifier: MIT
// G132 Meteor Scar Dig C++ port (G143), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public scar_dig_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public scar_dig_core_test.cpp
// Run with --write to regenerate scar_dig_parity.txt (read by ScarDigParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusScarDigCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static ScarPlan Rock() { ScarPlan P; P.Cells.assign(ScarCells, ScarCell::Rock); return P; }
static std::vector<ScarAction> Swings(int X, int Y, int N) { return std::vector<ScarAction>(N, ScarAction::Swing(X, Y)); }

// The parity hands; ScarDigParityTest.java plays exactly the same ones. 0 prospector, 1 wild (random swings and drinks).
static std::vector<ScarAction> Hand(const ScarPlan& P, const ScarKit& K, int Seed, int KitNo, int H)
{
	if (H == 0) return ScarProspector(P, K);
	SplitRng Rng(static_cast<int64_t>(Seed) * 41 + KitNo * 5 + H);
	std::vector<ScarAction> Out;
	const int N = 10 + Rng.NextInt(50);
	for (int i = 0; i < N; ++i)
	{
		if (Rng.NextInt(8) == 0) Out.push_back(ScarAction::Drink());
		else { const int X = Rng.NextInt(ScarSize + 1) - (H == 2 ? 1 : 0); const int Y = Rng.NextInt(ScarSize); Out.push_back(ScarAction::Swing(X, Y)); }
	}
	return Out;
}

static ScarKit KitOf(int I) { const ScarKit K[4] = { { false, false, 0 }, { false, false, 3 }, { true, false, 1 }, { true, true, 3 } }; return K[I]; }

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	const ScarKit Bare{ false, false, 0 };

	int Star = 0;
	bool Same = MakeScarPlan(4).Cells == MakeScarPlan(4).Cells && MakeScarPlan(5).Cells != MakeScarPlan(4).Cells;
	for (int S = 0; S < 200; ++S) for (ScarCell C : MakeScarPlan(S).Cells) Star += C == ScarCell::Starmetal;
	Check("scar is seeded, about 6% starmetal", Same && Star * 1000 / (200 * ScarCells) >= 45 && Star * 1000 / (200 * ScarCells) <= 75);

	ScarResult R{};
	ScarPlan P = Rock();
	P.Cells[0] = ScarCell::Starmetal;
	Check("bad kit refused", !RunScarDig(P, ScarKit{ false, false, 4 }, {}, R) && !RunScarDig(ScarPlan{}, Bare, {}, R));
	RunScarDig(P, Bare, Swings(0, 0, 4), R);
	Check("starmetal takes four strikes", R.Starmetal == 1 && R.Water == ScarStartWater - 8);
	RunScarDig(P, ScarKit{ true, true, 0 }, Swings(0, 0, 2), R);
	Check("drydock shift strikes twice, prospector rounds up", R.Starmetal == 2 && R.Ingots == 1 && ScarLuck(11) == 13);

	P.Cells[1] = ScarCell::Vent;
	RunScarDig(P, ScarKit{ false, false, 1 }, { ScarAction::Swing(1, 0), ScarAction::Drink(), ScarAction::Drink() }, R);
	Check("vent scalds, canteen caps, dry canteen wasted", R.Water == ScarStartWater && R.Wasted == 1);

	std::vector<ScarAction> A = Swings(0, 0, 4);
	auto More = Swings(4, 4, 40);
	A.insert(A.end(), More.begin(), More.end());
	RunScarDig(P, Bare, A, R);
	Check("fainting halves the haul", R.Fainted && R.Water == 0 && R.Swings == 30 && R.Starmetal == 0
		&& R.Line == "The scar took your water before your ore. Canteen first, pick second.");

	P = Rock();
	P.Cells[0] = ScarCell::Slag;
	RunScarDig(P, Bare, Swings(0, 0, 1), R);
	Check("encode matches Java", Encode(R) == "SCR 1 star=0 ember=0 slag=1 broken=1 swings=1 wasted=0 water=58 fainted=0 ingots=0 | Rock and slag. The veins glow; the rock doesn't.");

	if (WriteOut)
	{
		std::FILE* F = std::fopen("scar_dig_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# scar_dig_core_test.cpp --write: SCR 1 parity (hephaestus). Seeds 0..49 x 4 kits x hands prospector/wild/wild-off-edge.\n", F);
		for (int Seed = 0; Seed < 50; ++Seed)
		{
			const ScarPlan Pl = MakeScarPlan(Seed);
			for (int K = 0; K < 4; ++K)
				for (int H = 0; H < 3; ++H)
				{
					ScarResult Rs{};
					RunScarDig(Pl, KitOf(K), Hand(Pl, KitOf(K), Seed, K, H), Rs);
					std::fprintf(F, "seed=%d kit=%d hand=%d %s\n", Seed, K, H, Encode(Rs).c_str());
				}
		}
		std::fclose(F);
		std::printf("wrote scar_dig_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
