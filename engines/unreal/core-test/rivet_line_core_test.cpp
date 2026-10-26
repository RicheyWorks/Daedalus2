// SPDX-License-Identifier: MIT
// G104 Rivet Line C++ port (G112), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public rivet_line_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public rivet_line_core_test.cpp
// Run with --write to regenerate rivet_line_parity.txt (read by RivetLineParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusRivetLineCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

// The parity hands; RivetLineParityTest.java plays exactly the same ones. 0 master, 1 eager, 2 sloppy.
static std::vector<RivetSet> Hand(const RivetTray& T, int Seed, int H)
{
	if (H == 0) return RivetMaster(T);
	SplitRng Rng(static_cast<int64_t>(Seed) * 17 + static_cast<int>(T.C) * 3 + H);
	std::vector<RivetSet> Out;
	const int N = H == 1 ? T.Holes() : T.Holes() - Rng.NextInt(5);
	for (int i = 0; i < N; ++i)
	{
		const int At = H == 1 ? T.ReadyMs[i] - 300 + Rng.NextInt(700) : T.ReadyMs[i] + Rng.NextInt(1200);
		const int Strikes = H == 1 ? 1 + Rng.NextInt(4) : Rng.NextInt(5);
		Out.push_back({ At, Strikes });
	}
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;

	bool Seeded = true;
	for (int C = 0; C < ArkClassCount; ++C)
	{
		const RivetTray T = MakeRivetTray(static_cast<ArkClass>(C), 11);
		Seeded = Seeded && T.Holes() == ArkInfo(static_cast<ArkClass>(C)).Plates * ArkRivetsPerSeam
			&& T.ReadyMs == MakeRivetTray(static_cast<ArkClass>(C), 11).ReadyMs;
		for (int Ms : T.ReadyMs) Seeded = Seeded && Ms >= 1500 && Ms <= 2450 && Ms % 50 == 0;
	}
	Seeded = Seeded && MakeRivetTray(ArkClass::Skiff, 12).ReadyMs != MakeRivetTray(ArkClass::Skiff, 11).ReadyMs;
	Check("tray is seeded, one rivet per hole", Seeded);

	const RivetSet Early{ 1999, 3 }, OnTime{ 2000, 3 }, Edge{ 2800, 5 }, Late{ 2801, 3 }, Two{ 2400, 2 }, One{ 2400, 1 };
	Check("seats follow window and strikes", SeatRivet(2000, &Early) == RivetSeat::Spoiled && SeatRivet(2000, nullptr) == RivetSeat::Spoiled
		&& SeatRivet(2000, &OnTime) == RivetSeat::Tight && SeatRivet(2000, &Edge) == RivetSeat::Tight
		&& SeatRivet(2000, &Late) == RivetSeat::Loose && SeatRivet(2000, &Two) == RivetSeat::Snug && SeatRivet(2000, &One) == RivetSeat::Loose);

	const RivetTray Sk = MakeRivetTray(ArkClass::Skiff, 3);
	const RivetResult M = JudgeRivets(Sk, RivetMaster(Sk));
	bool Full = M.Tight == 24 && M.Snug == 0 && M.Loose == 0 && M.Spoiled == 0 && M.RivetsPerSeam.size() == 6;
	for (int R : M.RivetsPerSeam) Full = Full && R == ArkRivetsPerSeam;
	Check("master fills every hole", Full && M.Line == "Every hole filled hot. She'll hold the void.");

	const RivetResult None = JudgeRivets(Sk, {});
	Check("no sets spoil the line", None.Spoiled == 24 && None.Line == "You're hitting them before they glow. Wait for the colour.");

	std::vector<RivetSet> Few = RivetMaster(Sk);
	for (int i = 0; i < 4; ++i) Few[i].Strikes = 1;
	const RivetResult F = JudgeRivets(Sk, Few);
	Check("loose heads cost the first seam", F.Loose == 4 && F.RivetsPerSeam[0] == 0 && F.RivetsPerSeam[1] == 4
		&& F.Line == "A few loose heads. Drill them out or the seams pay for it.");

	Ark A{ ArkClass::Skiff, {}, F.RivetsPerSeam, {}, 0 };
	A.Plates.assign(6, ArkPlate{ 90, Quench::Dual, true });
	Check("rivets feed the drydock seams", SeamStrength(A, 0) == SeamStrength(A, 1) - ArkRivetsPerSeam * ArkMissingRivetCost);

	const RivetResult Enc = JudgeRivets(Sk, Few);
	Check("encode is stable", Encode(Enc) == Encode(F) && Encode(F).rfind("RVL 1 SKIFF holes=24 tight=20 snug=0 loose=4 spoiled=0 seams=0,4,4,4,4,4 seats=LLLLTTTT", 0) == 0);

	if (WriteOut)
	{
		std::FILE* Fp = std::fopen("rivet_line_parity.txt", "wb");
		if (!Fp) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# rivet_line_core_test.cpp --write: RVL 1 parity (hephaestus). 3 ark classes x seeds 0..39 x hands master/eager/sloppy.\n", Fp);
		for (int C = 0; C < ArkClassCount; ++C)
			for (int Seed = 0; Seed < 40; ++Seed)
			{
				const RivetTray T = MakeRivetTray(static_cast<ArkClass>(C), Seed);
				for (int H = 0; H < 3; ++H)
					std::fprintf(Fp, "c=%d seed=%d hand=%d %s\n", C, Seed, H, Encode(JudgeRivets(T, Hand(T, Seed, H))).c_str());
			}
		std::fclose(Fp);
		std::printf("wrote rivet_line_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
