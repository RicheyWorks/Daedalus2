// SPDX-License-Identifier: MIT
// G170 Shard Landfall C++ port, checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public shard_landfall_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public shard_landfall_core_test.cpp
// Run with --write to regenerate shard_landfall_parity.txt (read by ShardLandfallParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusShardLandfallCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static ShardHold Hold(int Em, int Goat, int Bees, int Pet, int Seeds, int Water, int Spares)
{
	ShardHold H{ "Glass Reef", {}, Water, Spares, true };
	H.Aboard[static_cast<int>(Life::Emberhen)] = Em; H.Aboard[static_cast<int>(Life::Ashgoat)] = Goat;
	H.Aboard[static_cast<int>(Life::VentBees)] = Bees; H.Aboard[static_cast<int>(Life::Pet)] = Pet; H.Aboard[static_cast<int>(Life::SeedCrate)] = Seeds;
	return H;
}

static ShardPasture Flat(int Cap, int Each, int Hive)
{
	ShardPasture P{ "Glass Reef", Cap, {}, Hive };
	for (int K = 0; K < ShardPairedCount; ++K) P.PairPrice[K] = Each;
	return P;
}

static ShardPlan Plan(int Em, int Goat, int Hives) { ShardPlan P{ {}, Hives }; P.Pairs[0] = Em; P.Pairs[1] = Goat; return P; }

static int Brute(const ShardHold& H, const ShardPasture& P)
{
	int Max[ShardPairedCount + 1], T[ShardPairedCount + 1] = {};
	for (int i = 0; i <= ShardPairedCount; ++i) Max[i] = ShardMaxUnits(H, i);
	int Best = -1;
	for (;;)
	{
		ShardPlan Pl{ {}, T[ShardPairedCount] };
		for (int K = 0; K < ShardPairedCount; ++K) Pl.Pairs[K] = T[K];
		const int S = ShardScore(H, P, Pl);
		Best = S > Best ? S : Best;
		int i = 0;
		while (i <= ShardPairedCount && T[i] == Max[i]) { T[i] = 0; ++i; }
		if (i > ShardPairedCount) return Best;
		++T[i];
	}
}

// The parity arks and hands of VoidCrossingParityTest (void_crossing_core_test.cpp).
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

static ShardPlan All(const ShardHold& H)
{
	ShardPlan P{ {}, H.Aboard[static_cast<int>(Life::VentBees)] };
	for (int K = 0; K < ShardPairedCount; ++K) P.Pairs[K] = H.Aboard[K] / 2;
	return P;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;

	SplitRng R(170);
	bool Exact = true;
	for (int64_t S = 0; S < 300; ++S)
	{
		ShardHold H{ "x", {}, 0, 0, true };
		for (int K = 0; K < ShardPairedCount; ++K) H.Aboard[K] = R.NextInt(6);
		H.Aboard[static_cast<int>(Life::VentBees)] = R.NextInt(4);
		H.Aboard[static_cast<int>(Life::SeedCrate)] = R.NextInt(3);
		H.Aboard[static_cast<int>(Life::Pet)] = R.NextInt(2);
		H.WaterDl = R.NextInt(2000);
		H.Spares = R.NextInt(13);
		const ShardPasture P = MakePasture(ShardName(static_cast<int>(S % ShardCount)), S);
		const ShardPlan B = ShardBest(H, P);
		ShardLanding L{};
		Exact = Exact && ShardForage(B) <= P.ForageCap && ShardScore(H, P, B) == Brute(H, P) && ShardLand(H, P, B, L) && L.Grade == ShardGrade::Thriving;
	}
	Check("exact DP = brute force on 300 seeded holds", Exact);

	ShardLanding L{};
	const ShardHold Broken = Hold(3, 1, 0, 0, 0, 0, 0);
	Check("a broken pair cannot land", !ShardLand(Broken, Flat(500, 20, 4), Plan(0, 1, 0), L) && !ShardLand(Broken, Flat(500, 20, 4), Plan(2, 0, 0), L)
		&& ShardLand(Broken, Flat(500, 20, 4), ShardBest(Broken, Flat(500, 20, 4)), L) && L.Scrip == 30 && L.Plan.Pairs[1] == 0);

	const ShardHold Goats = Hold(0, 2, 1, 0, 0, 0, 0);
	ShardLanding AtCap{}, Over{};
	Check("overgrazed exactly one dl over the cap", ShardLand(Goats, Flat(170, 12, 5), Plan(0, 1, 1), AtCap) && AtCap.Grade == ShardGrade::Thriving && AtCap.HerdScrip == 17
		&& ShardLand(Goats, Flat(169, 12, 5), Plan(0, 1, 1), Over) && Over.Grade == ShardGrade::Overgrazed && Over.Scrip == 0 && Over.Best == 13);

	const ShardHold Hand = Hold(2, 2, 1, 1, 2, 450, 3);
	ShardLanding None{}, Best{};
	Check("hand-checked scrip and SLF 1 encode", ShardLand(Hand, Flat(100, 8, 4), Plan(0, 0, 0), None) && None.QuayScrip == 26 && None.Best == 33 && None.Grade == ShardGrade::Settled
		&& ShardLand(Hand, Flat(100, 8, 4), ShardBest(Hand, Flat(100, 8, 4)), Best)
		&& Encode(Best) == "SLF 1 THRIVING to=Glass_Reef cap=100 forage=20 pairs=emberhen:1,ashgoat:0,forgeox:0,lavaboar:0,cinderwool:0 hives=1 herd=12 quay=21 scrip=33 best=33 step=report_tessaly | Every pen on Glass Reef is full and grazing easy. Tessaly says no ark ever landed better.");

	bool Same = true;
	for (int64_t S = 0; S < 50; ++S)
	{
		const ShardPasture A = MakePasture("Kennel Isle", S), B = MakePasture("Kennel Isle", S);
		Same = Same && A.ForageCap == B.ForageCap && A.HivePrice == B.HivePrice && std::memcmp(A.PairPrice, B.PairPrice, sizeof A.PairPrice) == 0
			&& A.ForageCap >= 100 && A.ForageCap <= 500 && A.HivePrice >= 3 && A.HivePrice <= 6;
	}
	Check("same seed, same pasture, bands held", Same);

	ShardHold Gone = Hold(0, 2, 0, 0, 0, 900, 4);
	Gone.Arrived = false;
	Check("nothing ashore from a breached ark", ShardLand(Gone, MakePasture("Cinder Shoal", 3), Plan(0, 0, 0), L) && L.Grade == ShardGrade::NothingAshore && L.Scrip == 0
		&& std::string(ShardQuestStep(L.Grade)) == "sail_again" && !ShardLand(Gone, MakePasture("Cinder Shoal", 3), Plan(-1, 0, 0), L));

	if (WriteOut)
	{
		std::FILE* F = std::fopen("shard_landfall_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# shard_landfall_core_test.cpp --write: SLF 1 parity (hephaestus). Seeds 0..49 x tonic 0/1 x spares 0/6 x hands bosun/hold/random x plans best/none/all.\n", F);
		for (int Seed = 0; Seed < 50; ++Seed)
		{
			const Voyage V = MakeVoyage(Seed);
			const Ark G = Generated(Seed, V);
			for (int T = 0; T < 2; ++T)
				for (int Sp = 0; Sp <= 6; Sp += 6)
					for (int H = 0; H < 3; ++H)
					{
						const ShardHold Hd = HoldOf(Play(G, V, T == 1, Sp, Seed, H));
						const ShardPasture P = MakePasture(Hd.Shard, Seed);
						const ShardPlan Plans[3] = { ShardBest(Hd, P), ShardPlan{ {}, 0 }, All(Hd) };
						const char* Names[3] = { "best", "none", "all" };
						for (int k = 0; k < 3; ++k)
						{
							ShardLanding Out{};
							if (!ShardLand(Hd, P, Plans[k], Out)) { std::printf("FAIL refused parity plan\n"); std::fclose(F); return 1; }
							std::fprintf(F, "seed=%d tonic=%d spares=%d hand=%d plan=%s %s\n", Seed, T, Sp, H, Names[k], Encode(Out).c_str());
						}
					}
		}
		std::fclose(F);
		std::printf("wrote shard_landfall_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
