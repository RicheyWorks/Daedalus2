// SPDX-License-Identifier: MIT
// G24 Ark Drydock C++ port (G31), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public ark_drydock_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_drydock_core_test.cpp
// Run with --write to regenerate ark_drydock_parity.txt (read by ArkDrydockParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusArkDrydockCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static Ark Good()
{
	Ark A{ ArkClass::Skiff, {}, {}, {}, 0 };
	for (int i = 0; i < 6; ++i) { A.Plates.push_back({ 90, i == 3 ? Quench::Spring : Quench::Magma, true }); A.Rivets.push_back(4); }
	A.Manifest[static_cast<int>(Life::Emberhen)] = 2; A.Manifest[static_cast<int>(Life::Ashgoat)] = 2;
	A.Manifest[static_cast<int>(Life::VentBees)] = 1; A.Manifest[static_cast<int>(Life::Pet)] = 1; A.Manifest[static_cast<int>(Life::SeedCrate)] = 2;
	A.WaterDl = 1150;
	return A;
}

// The parity arks; ArkDrydockParityTest.java builds exactly the same ones.
static Ark Generated(int Seed, int V, const Voyage& Vo)
{
	const ArkClass C = static_cast<ArkClass>(Seed % ArkClassCount);
	const ArkClassInfo I = ArkInfo(C);
	SplitRng Rng(static_cast<int64_t>(Seed) * 31 + 7);
	Ark A{ C, {}, {}, {}, 0 };
	const int N = I.Plates - (Rng.NextInt(8) == 0 ? 1 : 0);
	for (int k = 0; k < N; ++k)
	{
		const int T = 40 + Rng.NextInt(61);
		const Quench Q = static_cast<Quench>(Rng.NextInt(3));
		const bool S = Rng.NextInt(10) != 0;
		A.Plates.push_back({ T, Q, S });
	}
	for (int k = 0; k < N; ++k) A.Rivets.push_back(2 + Rng.NextInt(3));
	for (int L = 0; L < LifeCount; ++L) A.Manifest[L] = Rng.NextInt(4);
	A.WaterDl = Rng.NextInt(I.HoldDl + 1000);
	if (V >= 1)
	{
		A.Plates.assign(I.Plates, ArkPlate{ 90, Quench::Dual, true });
		A.Rivets.assign(I.Plates, ArkRivetsPerSeam);
	}
	if (V >= 2)
	{
		for (int L = 0; L < LifeCount; ++L) if (LifeOf(static_cast<Life>(L)).Pairs) A.Manifest[L] -= A.Manifest[L] % 2;
		A.WaterDl = WaterNeedDl(A, Vo);
	}
	return A;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	const Voyage Five{ "Kennel Isle", 5 };
	ArkInspection I;
	Inspect(Good(), Five, I);
	Check("good skiff launches", I.Ready && I.Integrity == 90 && I.WaterNeedDl == 1150 && I.BerthsUsed == 8 && std::string(ArkQuestStep(I)) == "launch");
	Check("send-off line", I.Line == "Tempered both ways. Knock the chocks out. 5 days to Kennel Isle, and the forge goes with you.");
	{
		Ark A = Good();
		for (ArkPlate& P : A.Plates) P.Q = Quench::Magma;
		Inspect(A, Five, I);
		Check("all magma is brittle", !I.Ready && I.Reasons.size() == 1 && I.Reasons[0] == ArkReason::Brittle);
		for (ArkPlate& P : A.Plates) P.Q = Quench::Spring;
		Inspect(A, Five, I);
		Check("all spring is soft", I.Reasons.size() == 1 && I.Reasons[0] == ArkReason::Soft);
	}
	{
		Ark A = Good(); A.Plates[1].Temper = 40; A.Rivets[4] = 1;
		Check("seam maths", SeamStrength(A, 0) == 65 && SeamStrength(A, 4) == 60 && SeamStrength(A, 5) == 90);
		A.Rivets[4] = 0; Inspect(A, Five, I);
		Check("weak seam", I.Reasons.size() == 1 && I.Reasons[0] == ArkReason::WeakSeam && std::string(ArkQuestStep(I)) == "rivet_seams");
	}
	{
		Ark A = Good(); A.Manifest[static_cast<int>(Life::Forgeox)] = 1; A.WaterDl = 2000; Inspect(A, Five, I);
		Check("unpaired ox", I.Reasons.size() == 1 && I.Reasons[0] == ArkReason::Unpaired);
		A = Good(); A.WaterDl = 1149; Inspect(A, Five, I);
		Check("thirsty hold", I.Reasons.size() == 1 && I.Reasons[0] == ArkReason::ThirstyHold);
		A = Good(); A.Manifest[0] = -1;
		Check("negative count refused", !Inspect(A, Five, I));
	}
	bool Ranged = true;
	for (int s = 0; s < 200; ++s)
	{
		const Voyage V = MakeVoyage(s);
		if (V.Days < 3 || V.Days > 9) Ranged = false;
	}
	Check("voyages 3..9 days", Ranged);

	if (WriteOut)
	{
		std::FILE* F = std::fopen("ark_drydock_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# ark_drydock_core_test.cpp --write: ADK 1 parity (hephaestus). Seed 0..59 x variant 0..2.\n", F);
		for (int Seed = 0; Seed < 60; ++Seed)
			for (int V = 0; V < 3; ++V)
			{
				const Voyage Vo = MakeVoyage(Seed);
				ArkInspection R;
				Inspect(Generated(Seed, V, Vo), Vo, R);
				std::fprintf(F, "seed=%d v=%d %s %s %d | %s\n", Seed, V, ArkInfo(static_cast<ArkClass>(Seed % ArkClassCount)).Name, Vo.Shard, Vo.Days, Encode(R).c_str());
			}
		std::fclose(F);
		std::printf("wrote ark_drydock_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
