// SPDX-License-Identifier: MIT
// G152 Void Crossing C++ port (G165), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public void_crossing_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public void_crossing_core_test.cpp
// Run with --write to regenerate void_crossing_parity.txt (read by VoidCrossingParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusVoidCrossingCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

// The G24 test skiff with every plate at Temper and water ExtraDl over the need (VoidCrossingTest.ark).
static Ark Skiff(int Temper, const Voyage& V, int ExtraDl)
{
	Ark A{ ArkClass::Skiff, {}, {}, {}, 0 };
	for (int i = 0; i < 6; ++i) { A.Plates.push_back({ Temper, i == 3 ? Quench::Spring : Quench::Magma, true }); A.Rivets.push_back(ArkRivetsPerSeam); }
	A.Manifest[static_cast<int>(Life::Emberhen)] = 2; A.Manifest[static_cast<int>(Life::Ashgoat)] = 2;
	A.Manifest[static_cast<int>(Life::VentBees)] = 1; A.Manifest[static_cast<int>(Life::Pet)] = 1; A.Manifest[static_cast<int>(Life::SeedCrate)] = 2;
	A.WaterDl = WaterNeedDl(A, V) + ExtraDl;
	return A;
}

// The parity arks; VoidCrossingParityTest.java builds exactly the same ones.
static Ark Generated(int Seed, const Voyage& V)
{
	SplitRng Rng(static_cast<int64_t>(Seed) * 29 + 3);
	const ArkClass C = static_cast<ArkClass>(Seed % ArkClassCount);
	const ArkClassInfo I = ArkInfo(C);
	Ark A{ C, {}, {}, {}, 0 };
	for (int k = 0; k < I.Plates; ++k)
	{
		const int T = 60 + Rng.NextInt(41);
		const Quench Q = k == 0 ? Quench::Dual : static_cast<Quench>(Rng.NextInt(3));
		A.Plates.push_back({ T, Q, true });
		A.Rivets.push_back(Rng.NextInt(8) == 0 ? ArkRivetsPerSeam - 1 : ArkRivetsPerSeam);
	}
	for (int L = 0; L < LifeCount; ++L)
	{
		const LifeInfo F = LifeOf(static_cast<Life>(L));
		A.Manifest[L] = F.Pairs ? 2 * Rng.NextInt(2) : Rng.NextInt(3);
	}
	const int Extra = Rng.NextInt(300);
	A.WaterDl = WaterNeedDl(A, V) + Extra - (Rng.NextInt(10) == 0 ? 400 : 0);
	if (A.WaterDl < 0) A.WaterDl = 0;
	return A;
}

static VoidCrossing Play(const Ark& A, const Voyage& V, bool Tonic, int Spares, int Seed, int H)
{
	if (H == 0) return VoidBosun(A, V, Tonic, Spares, Seed);
	VoidCrossing C(A, V, Tonic, Spares, Seed);
	SplitRng Rng(static_cast<int64_t>(Seed) * 7 + (Tonic ? 2 : 0) + Spares);
	const int N = static_cast<int>(A.Plates.size());
	while (C.Outcome == VoidOutcome::Sailing) C.Sail(H == 1 ? -1 : Rng.NextInt(N + 1) - 1);
	return C;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	const Voyage Kennel{ "Kennel Isle", 6 };

	const Ark A = Skiff(90, Kennel, 0);
	VoidCrossing X(A, Kennel, false, 6, 21);
	bool Fixed = X.Weather.size() == 6;
	const VoidCrossing Y(A, Kennel, true, 0, 21);
	for (int d = 0; d < 6; ++d) Fixed = Fixed && X.Weather[d].Cold == Y.Weather[d].Cold && X.Weather[d].StormSeam == Y.Weather[d].StormSeam && X.Weather[d].Damage == Y.Weather[d].Damage;
	Check("weather fixed at departure", Fixed && X.Today() == &X.Weather[0]);

	VoidCrossing Leaky(Skiff(90, Kennel, -1), Kennel, true, 3, 1);
	Check("an uncleared ark never sails", Leaky.Valid() && Leaky.Outcome == VoidOutcome::NotLaunched && Leaky.Sail(0) == VoidOutcome::NotLaunched && Leaky.Day == 0
		&& !VoidCrossing(A, Kennel, false, 13, 1).Valid());

	int64_t Calm = -1;
	for (int64_t S = 0; S < 10000 && Calm < 0; ++S)
	{
		const VoidCrossing T(A, Kennel, false, 0, S);
		bool Quiet = true;
		for (const VoidDay& W : T.Weather) Quiet = Quiet && !W.Cold && W.StormSeam < 0;
		if (Quiet) Calm = S;
	}
	VoidCrossing C(A, Kennel, false, 2, Calm);
	while (C.Outcome == VoidOutcome::Sailing) C.Sail(-1);
	Check("a calm crossing drinks exactly the drydock need", C.Outcome == VoidOutcome::Arrived && C.Water == 0 && C.MinSeam() == 90);
	Check("encode matches Java", Encode(VoidCrossing(A, Kennel, false, 2, Calm)) == "VXC 1 SAILING to=Kennel_Isle day=0/6 storms=0 cold=0 minSeam=90 patches=0 spares=2 idle=0 water="
		+ std::to_string(A.WaterDl) + " lost=0 | Holding course for Kennel Isle. Keep a hand on the rivet crate.");

	int TonicLoss = 0, BareLoss = 0;
	for (int S = 0; S < 200; ++S)
	{
		TonicLoss += VoidBosun(Skiff(70, Kennel, 0), Kennel, true, 6, S).LostHead();
		BareLoss += VoidBosun(Skiff(70, Kennel, 0), Kennel, false, 6, S).LostHead();
	}
	Check("the tonic saves the hold", TonicLoss == 0 && BareLoss > 0);

	const Ark Weak = Skiff(62, Kennel, 0);
	int64_t Hard = -1;
	for (int64_t S = 0; S < 10000 && Hard < 0; ++S) if (VoidCrossing(Weak, Kennel, true, 12, S).Weather[0].Damage > 62 - VoidBreach) Hard = S;
	VoidCrossing B(Weak, Kennel, true, 12, Hard);
	Check("a seam under thirty breaches", B.Sail(-1) == VoidOutcome::Breached && B.Day == 1 && VoidLine(B.Outcome, Kennel) == "Seam's open to the void. We're limping home. Temper both, smith.");

	if (WriteOut)
	{
		std::FILE* F = std::fopen("void_crossing_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# void_crossing_core_test.cpp --write: VXC 1 parity (hephaestus). Seeds 0..99 x tonic 0/1 x spares 0/6 x hands bosun/hold/random.\n", F);
		for (int Seed = 0; Seed < 100; ++Seed)
		{
			const Voyage V = MakeVoyage(Seed);
			const Ark G = Generated(Seed, V);
			for (int T = 0; T < 2; ++T)
				for (int Sp = 0; Sp <= 6; Sp += 6)
					for (int H = 0; H < 3; ++H)
						std::fprintf(F, "seed=%d tonic=%d spares=%d hand=%d %s\n", Seed, T, Sp, H, Encode(Play(G, V, T == 1, Sp, Seed, H)).c_str());
		}
		std::fclose(F);
		std::printf("wrote void_crossing_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
