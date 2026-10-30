// SPDX-License-Identifier: MIT
// G528 Shoeing Shed (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.ShoeingShed line for line (stable_shoeing_shed_parity.txt,
// checked by StableCoresParityTest.java and stable_shoeing_shed_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* ShoeingQuest = "q_sound_hooves";
constexpr int MaxShedHorses = 16;

struct Shed { std::vector<int> Time, Fret, Due; };
struct ShedQueue { int64_t Penalty = 0; std::vector<int> Order; };

// Seeded horses (Java ShoeingShed.horses): time in [1, 9], fret in [1, 5], due in [0, 4n].
inline Shed ShedSeed(int64_t Seed, int N)
{
	StableRng Rng(Seed);
	Shed S;
	for (int h = 0; h < N; ++h)
	{
		S.Time.push_back(1 + Rng.NextInt(9));
		S.Fret.push_back(1 + Rng.NextInt(5));
		S.Due.push_back(Rng.NextInt(4 * N + 1));
	}
	return S;
}

// Least total weighted lateness, exactly: DP over the set of horses already shod.
inline ShedQueue ShedBest(const Shed& S)
{
	const int N = static_cast<int>(S.Time.size());
	const int States = 1 << N;
	std::vector<int64_t> Cost(States, 0), Span(States, 0);
	std::vector<int> Last(States, 0);
	for (int s = 1; s < States; ++s)
	{
		int Low = 0;
		while (((s >> Low) & 1) == 0) ++Low;
		Span[s] = Span[s & (s - 1)] + S.Time[Low];
		Cost[s] = std::numeric_limits<int64_t>::max();
		for (int h = 0; h < N; ++h)
		{
			if ((s & (1 << h)) == 0) continue;
			const int64_t Late = std::max<int64_t>(0, Span[s] - S.Due[h]);
			const int64_t C = Cost[s ^ (1 << h)] + S.Fret[h] * Late;
			if (C < Cost[s]) { Cost[s] = C; Last[s] = h; }
		}
	}
	ShedQueue Q;
	Q.Penalty = Cost[States - 1];
	Q.Order.assign(N, 0);
	int s = States - 1;
	for (int k = N - 1; k >= 0; --k) { Q.Order[k] = Last[s]; s ^= 1 << Last[s]; }
	return Q;
}

// Total weighted lateness of an order, or -1 when it repeats, skips or names a missing horse.
inline int64_t ShedPenalty(const Shed& S, const std::vector<int>& Order)
{
	const int N = static_cast<int>(S.Time.size());
	if (static_cast<int>(Order.size()) != N) return -1;
	std::vector<bool> Seen(N, false);
	int64_t Clock = 0, Total = 0;
	for (int h : Order)
	{
		if (h < 0 || h >= N || Seen[h]) return -1;
		Seen[h] = true;
		Clock += S.Time[h];
		Total += S.Fret[h] * std::max<int64_t>(0, Clock - S.Due[h]);
	}
	return Total;
}

// Smith's rule: highest fret per minute of shoeing first (lowest index on ties).
inline ShedQueue ShedSmith(const Shed& S)
{
	ShedQueue Q;
	for (size_t i = 0; i < S.Time.size(); ++i) Q.Order.push_back(static_cast<int>(i));
	std::stable_sort(Q.Order.begin(), Q.Order.end(), [&](int A, int B) {
		const int64_t L = static_cast<int64_t>(S.Fret[A]) * S.Time[B];
		const int64_t R = static_cast<int64_t>(S.Fret[B]) * S.Time[A];
		return L != R ? L > R : A < B;
	});
	Q.Penalty = ShedPenalty(S, Q.Order);
	return Q;
}

inline bool ShedQuest(const Shed& S, const std::vector<int>& Order)
{
	const int64_t Got = ShedPenalty(S, Order);
	return Got >= 0 && Got == ShedBest(S).Penalty;
}

} } // namespace daedalus::stable
