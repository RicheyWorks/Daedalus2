// SPDX-License-Identifier: MIT
// G57 Bellows Shift C++ port (G69), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public forge_bellows_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public forge_bellows_core_test.cpp
// Run with --write to regenerate forge_bellows_parity.txt (read by ForgeBellowsParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusForgeBellowsCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static const Material Metals[] = { Material::Copper, Material::Bronze, Material::Iron, Material::Steel, Material::Starmetal };

static BellowsResult Steady(Material M, int Oxen, int64_t Seed)
{
	BellowsPlan P; MakeBellowsPlan(M, Oxen, Seed, P);
	return RunBellows(P, BellowsSteadyHand(P));
}

// The third parity input: seeded coin-flip pumps (ForgeBellowsParityTest.java builds the same).
static std::vector<bool> Fitful(int64_t Seed)
{
	SplitRng Rng(Seed * 7 + 3);
	std::vector<bool> V(BellowsTicks, false);
	for (int T = 0; T < BellowsTicks; ++T) V[T] = Rng.NextInt(2) == 0;
	return V;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	BellowsPlan P;
	Check("plan refuses wood and three oxen", !MakeBellowsPlan(Material::Wood, 0, 1, P) && !MakeBellowsPlan(Material::Iron, 3, 1, P) && !MakeBellowsPlan(Material::Iron, -1, 1, P));
	MakeBellowsPlan(Material::Steel, 0, 1, P); const int P0 = BellowsPumpOf(P);
	MakeBellowsPlan(Material::Steel, 2, 1, P);
	Check("pump +15% per ox", P0 == 30 && BellowsPumpOf(P) == 39);
	bool Soft = true;
	for (int S = 0; S < 10; ++S)
	{
		const BellowsResult R = Steady(Material::Copper, 0, S), B = Steady(Material::Bronze, 0, S);
		Soft = Soft && R.Tier == BellowsTier::Steady && B.Tier == BellowsTier::Steady && R.ReadyToPull && R.Cinders == 0;
	}
	Check("steady hand holds copper and bronze steady", Soft);
	int None = 0, Two = 0;
	for (int S = 0; S < 10; ++S) { None += Steady(Material::Starmetal, 0, S).InBandTicks; Two += Steady(Material::Starmetal, 2, S).InBandTicks; }
	Check("forgeox buys you time on starmetal", Two > None);
	MakeBellowsPlan(Material::Copper, 2, 1, P);
	const BellowsResult Spam = RunBellows(P, std::vector<bool>(BellowsTicks, true));
	Check("spam chokes the bed", Spam.Cinders == 3 && Spam.Doused && Spam.FinalC == 20 && Spam.Tier == BellowsTier::Cold && std::strstr(Spam.Line, "cinders"));
	MakeBellowsPlan(Material::Iron, 1, 5, P);
	const BellowsResult Cold = RunBellows(P, {});
	Check("no pumps falls to ambient", Cold.InBandTicks == 0 && Cold.FinalC == 20 && Cold.PeakC == BellowsStartC && std::string(Cold.Line) == "Cold bed, cold iron. Again.");
	Check("encode", Encode(Cold).rfind("BLW 1 in=0 pm=0 cinders=0 doused=0 peak=600 final=20 COLD ready=0 speed=1150 | ", 0) == 0);

	if (WriteOut)
	{
		std::FILE* F = std::fopen("forge_bellows_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# forge_bellows_core_test.cpp --write: BLW 1 parity (hephaestus). 5 metals x oxen 0..2 x seeds 0..19 x steady/spam/fitful.\n", F);
		for (int M = 0; M < 5; ++M)
			for (int Ox = 0; Ox <= BellowsMaxOxen; ++Ox)
				for (int S = 0; S < 20; ++S)
				{
					MakeBellowsPlan(Metals[M], Ox, S, P);
					std::fprintf(F, "m=%d ox=%d s=%d steady %s\n", M, Ox, S, Encode(RunBellows(P, BellowsSteadyHand(P))).c_str());
					std::fprintf(F, "m=%d ox=%d s=%d spam %s\n", M, Ox, S, Encode(RunBellows(P, std::vector<bool>(BellowsTicks, true))).c_str());
					std::fprintf(F, "m=%d ox=%d s=%d fitful %s\n", M, Ox, S, Encode(RunBellows(P, Fitful(S))).c_str());
				}
		std::fclose(F);
		std::printf("wrote forge_bellows_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
