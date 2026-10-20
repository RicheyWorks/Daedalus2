// SPDX-License-Identifier: MIT
// G170 Shard Landfall in plain C++17 (daedalus-core world/forge/ShardLandfall.java), header-only and Unreal-ready.
// Land an arrived G152 ark's hold on its shard: a seeded pasture (forage cap, pair prices), whole pairs only, seed
// crates plant, hives land singly, the rest sells at the quay, over the cap = OVERGRAZED. ShardBest() is the same
// exact bounded-knapsack DP as ShardLandfall.best(); Encode() gives the same SLF 1 line as Landing.encode().
#pragma once

#include "DaedalusVoidCrossingCore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int ShardSeedCrateScrip = 5;
constexpr int ShardDlPerScrip = 100;
constexpr int ShardPairedCount = 5; // Emberhen..Cinderwool, the first five Life values

enum class ShardGrade : int { Thriving = 0, Settled, Thin, Overgrazed, NothingAshore };
inline const char* ShardGradeName(ShardGrade G)
{
	static const char* N[] = { "THRIVING", "SETTLED", "THIN", "OVERGRAZED", "NOTHING_ASHORE" };
	return N[static_cast<int>(G)];
}

// What the ark brings to the quay.
struct ShardHold { std::string Shard; int Aboard[LifeCount]; int WaterDl; int Spares; bool Arrived; };

inline ShardHold HoldOf(const VoidCrossing& C)
{
	ShardHold H{ C.V.Shard, {}, C.Water, C.Spares, C.Outcome == VoidOutcome::Arrived || C.Outcome == VoidOutcome::ArrivedWithLosses };
	for (int L = 0; L < LifeCount; ++L) H.Aboard[L] = C.Aboard[L];
	return H;
}

struct ShardPasture
{
	std::string Shard;
	int ForageCap;
	int PairPrice[ShardPairedCount];
	int HivePrice;
	int Sell(int K) const { const int Q = PairPrice[K] / 4; return Q > 1 ? Q : 1; }
};

inline ShardPasture MakePasture(const std::string& Shard, int64_t Seed)
{
	uint64_t H = 0;
	for (char Ch : Shard) H = H * 31u + static_cast<uint64_t>(static_cast<unsigned char>(Ch));
	const uint64_t Mixed = static_cast<uint64_t>(Seed) ^ (H * 0x9E37u) ^ 0x51Fu;
	SplitRng Rng(static_cast<int64_t>(Mixed));
	ShardPasture P{ Shard, 0, {}, 0 };
	P.ForageCap = 100 + 50 * Rng.NextInt(9);
	for (int K = 0; K < ShardPairedCount; ++K) P.PairPrice[K] = 4 + Rng.NextInt(17);
	P.HivePrice = 3 + Rng.NextInt(4);
	return P;
}

struct ShardPlan { int Pairs[ShardPairedCount]; int Hives; };

inline int ShardForage(const ShardPlan& P)
{
	int F = P.Hives * LifeOf(Life::VentBees).DlPerDay;
	for (int K = 0; K < ShardPairedCount; ++K) F += 2 * LifeOf(static_cast<Life>(K)).DlPerDay * P.Pairs[K];
	return F;
}

inline int ShardMaxUnits(const ShardHold& H, int I) { return I < ShardPairedCount ? H.Aboard[I] / 2 : H.Aboard[static_cast<int>(Life::VentBees)]; }
inline int ShardWeight(int I) { return I < ShardPairedCount ? 2 * LifeOf(static_cast<Life>(I)).DlPerDay : LifeOf(Life::VentBees).DlPerDay; }
inline int ShardGain(const ShardPasture& P, int I) { return I < ShardPairedCount ? P.PairPrice[I] - 2 * P.Sell(I) : P.HivePrice - 1; }

inline int ShardHerdScrip(const ShardPasture& P, const ShardPlan& Pl)
{
	int S = Pl.Hives * P.HivePrice;
	for (int K = 0; K < ShardPairedCount; ++K) S += Pl.Pairs[K] * P.PairPrice[K];
	return S;
}

inline int ShardQuayScrip(const ShardHold& H, const ShardPasture& P, const ShardPlan& Pl)
{
	int S = H.WaterDl / ShardDlPerScrip + H.Spares + (H.Aboard[static_cast<int>(Life::VentBees)] - Pl.Hives);
	for (int K = 0; K < ShardPairedCount; ++K) S += (H.Aboard[K] - 2 * Pl.Pairs[K]) * P.Sell(K);
	return S;
}

inline int ShardScore(const ShardHold& H, const ShardPasture& P, const ShardPlan& Pl)
{
	const int Herd = ShardForage(Pl) > P.ForageCap ? 0 : ShardHerdScrip(P, Pl);
	return Herd + ShardQuayScrip(H, P, Pl) + ShardSeedCrateScrip * H.Aboard[static_cast<int>(Life::SeedCrate)];
}

// Exact bounded knapsack over forage, the same table walk and tie rule as ShardLandfall.best().
inline ShardPlan ShardBest(const ShardHold& H, const ShardPasture& P)
{
	const int Cap = P.ForageCap;
	const int N = ShardPairedCount + 1;
	std::vector<std::vector<int>> Dp(N + 1, std::vector<int>(Cap + 1, 0)), Take(N + 1, std::vector<int>(Cap + 1, 0));
	for (int i = 1; i <= N; ++i)
	{
		const int W = ShardWeight(i - 1), G = ShardGain(P, i - 1), Max = ShardMaxUnits(H, i - 1);
		for (int c = 0; c <= Cap; ++c)
		{
			Dp[i][c] = Dp[i - 1][c];
			for (int t = 1; t <= Max && t * W <= c; ++t)
			{
				const int V = Dp[i - 1][c - t * W] + t * G;
				if (V > Dp[i][c]) { Dp[i][c] = V; Take[i][c] = t; }
			}
		}
	}
	ShardPlan Out{ {}, 0 };
	int c = Cap;
	for (int i = N; i >= 1; --i)
	{
		const int t = Take[i][c];
		if (i - 1 < ShardPairedCount) Out.Pairs[i - 1] = t; else Out.Hives = t;
		c -= t * ShardWeight(i - 1);
	}
	return Out;
}

struct ShardLanding { ShardGrade Grade; int Forage, HerdScrip, QuayScrip, Scrip, Best; ShardPlan Plan; ShardPasture Pasture; };

inline std::string ShardLine(ShardGrade G, const std::string& S)
{
	switch (G)
	{
	case ShardGrade::Thriving: return "Every pen on " + S + " is full and grazing easy. Tessaly says no ark ever landed better.";
	case ShardGrade::Settled: return "The herds will take on " + S + ". Tessaly would have penned one more pair.";
	case ShardGrade::Thin: return "Most of the hold went to the quay stalls. " + S + " wanted founders, not scrip.";
	case ShardGrade::Overgrazed: return "Too many mouths for the pasture. " + S + " is bare by the second week.";
	default: return "No ark moored at " + S + ". Tessaly keeps the pens swept and waits.";
	}
}

inline const char* ShardQuestStep(ShardGrade G)
{
	return G == ShardGrade::Thriving || G == ShardGrade::Settled ? "report_tessaly" : G == ShardGrade::NothingAshore ? "sail_again" : "replan_landing";
}

// Land Pl from H onto P. Returns false (Java throws) when the plan lands heads the hold does not have.
inline bool ShardLand(const ShardHold& H, const ShardPasture& P, const ShardPlan& Pl, ShardLanding& Out)
{
	for (int K = 0; K < ShardPairedCount; ++K) if (Pl.Pairs[K] < 0) return false;
	if (Pl.Hives < 0) return false;
	if (!H.Arrived) { Out = ShardLanding{ ShardGrade::NothingAshore, 0, 0, 0, 0, 0, Pl, P }; return true; }
	for (int i = 0; i <= ShardPairedCount; ++i)
		if ((i < ShardPairedCount ? Pl.Pairs[i] : Pl.Hives) > ShardMaxUnits(H, i)) return false;
	const int Best = ShardScore(H, P, ShardBest(H, P));
	const int Forage = ShardForage(Pl);
	const bool Over = Forage > P.ForageCap;
	const int Herd = Over ? 0 : ShardHerdScrip(P, Pl);
	const int Quay = ShardQuayScrip(H, P, Pl) + ShardSeedCrateScrip * H.Aboard[static_cast<int>(Life::SeedCrate)];
	const int Scrip = Herd + Quay;
	const ShardGrade G = Over ? ShardGrade::Overgrazed : Scrip == Best ? ShardGrade::Thriving : 4 * Scrip >= 3 * Best ? ShardGrade::Settled : ShardGrade::Thin;
	Out = ShardLanding{ G, Forage, Herd, Quay, Scrip, Best, Pl, P };
	return true;
}

// SLF 1 single-line encoding, the same text as ShardLandfall.Landing.encode().
inline std::string Encode(const ShardLanding& L)
{
	std::string Shard = L.Pasture.Shard;
	for (char& Ch : Shard) if (Ch == ' ') Ch = '_';
	std::string Pairs;
	for (int K = 0; K < ShardPairedCount; ++K)
	{
		if (K > 0) Pairs += ',';
		Pairs += std::string(LifeOf(static_cast<Life>(K)).Id) + ":" + std::to_string(L.Plan.Pairs[K]);
	}
	return std::string("SLF 1 ") + ShardGradeName(L.Grade) + " to=" + Shard + " cap=" + std::to_string(L.Pasture.ForageCap) + " forage="
		+ std::to_string(L.Forage) + " pairs=" + Pairs + " hives=" + std::to_string(L.Plan.Hives) + " herd=" + std::to_string(L.HerdScrip)
		+ " quay=" + std::to_string(L.QuayScrip) + " scrip=" + std::to_string(L.Scrip) + " best=" + std::to_string(L.Best) + " step="
		+ ShardQuestStep(L.Grade) + " | " + ShardLine(L.Grade, L.Pasture.Shard);
}

}} // namespace daedalus::forge
