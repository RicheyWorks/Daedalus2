// SPDX-License-Identifier: MIT
// G506 Trotting Ring (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.TrottingRing line for line (stable_trotting_ring_parity.txt,
// checked by StableCoresParityTest.java and stable_trotting_ring_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* TrottingRingQuest = "q_blue_rosette";
constexpr int Walk = 0, Trot = 1, Canter = 2;

struct RingRound { int Score = 0; std::vector<int> Gaits; };

// The judge's seeded calls, one gait per segment (Java TrottingRing.calls).
inline std::vector<int> RingCalls(int64_t Seed, int N)
{
	StableRng Rng(Seed);
	std::vector<int> Calls(static_cast<size_t>(std::max(N, 0)));
	for (int& C : Calls) C = Rng.NextInt(3);
	return Calls;
}

// Stamina spent by a gait; walking recovers one.
inline int GaitCost(int Gait) { return Gait == Walk ? -1 : Gait; }

// Points for riding Gait when the judge called Call: 2 exact, 1 off by one, 0 off by two.
inline int GaitPoints(int Call, int Gait) { return 2 - std::abs(Call - Gait); }

// Best score, exactly: DP over (segment, stamina left).
inline RingRound RingBest(const std::vector<int>& Calls, int MaxStamina)
{
	const int N = static_cast<int>(Calls.size());
	const int Neg = INT_MIN / 2;
	std::vector<std::vector<int>> Score(N + 1, std::vector<int>(MaxStamina + 1, 0));
	std::vector<std::vector<int>> Pick(N, std::vector<int>(MaxStamina + 1, Walk));
	for (int i = N - 1; i >= 0; --i)
	{
		for (int s = 0; s <= MaxStamina; ++s)
		{
			int BestScore = Neg, BestGait = Walk;
			for (int g = Walk; g <= Canter; ++g)
			{
				int Next = s - GaitCost(g);
				if (Next < 0) continue;
				Next = std::min(Next, MaxStamina);
				const int V = GaitPoints(Calls[i], g) + Score[i + 1][Next];
				if (V > BestScore) { BestScore = V; BestGait = g; }
			}
			Score[i][s] = BestScore;
			Pick[i][s] = BestGait;
		}
	}
	RingRound R;
	int s = MaxStamina;
	for (int i = 0; i < N; ++i)
	{
		R.Gaits.push_back(Pick[i][s]);
		s = std::min(s - GaitCost(R.Gaits.back()), MaxStamina);
	}
	R.Score = N == 0 ? 0 : Score[0][MaxStamina];
	return R;
}

// The eager habit: ride the called gait, dropping down only when out of stamina.
inline RingRound RingEager(const std::vector<int>& Calls, int MaxStamina)
{
	RingRound R;
	int s = MaxStamina;
	for (int Call : Calls)
	{
		int g = Call;
		while (s - GaitCost(g) < 0) --g;
		R.Gaits.push_back(g);
		R.Score += GaitPoints(Call, g);
		s = std::min(s - GaitCost(g), MaxStamina);
	}
	return R;
}

// Score of a ridden round, or -1 when a gait is unknown, the round is the wrong length or stamina runs out.
inline int RingScore(const std::vector<int>& Calls, const std::vector<int>& Gaits, int MaxStamina)
{
	if (Gaits.size() != Calls.size()) return -1;
	int s = MaxStamina, Total = 0;
	for (size_t i = 0; i < Calls.size(); ++i)
	{
		if (Gaits[i] < Walk || Gaits[i] > Canter) return -1;
		const int Next = s - GaitCost(Gaits[i]);
		if (Next < 0) return -1;
		s = std::min(Next, MaxStamina);
		Total += GaitPoints(Calls[i], Gaits[i]);
	}
	return Total;
}

inline bool RingQuest(const std::vector<int>& Calls, const std::vector<int>& Gaits, int MaxStamina)
{
	const int Got = RingScore(Calls, Gaits, MaxStamina);
	return Got >= 0 && Got == RingBest(Calls, MaxStamina).Score;
}

} } // namespace daedalus::stable
