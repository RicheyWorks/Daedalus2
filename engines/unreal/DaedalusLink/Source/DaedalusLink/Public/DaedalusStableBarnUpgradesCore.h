// SPDX-License-Identifier: MIT
// G548 Barn Upgrades (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.BarnUpgrades line for line (stable_barn_upgrades_parity.txt,
// checked by StableCoresParityTest.java and stable_barn_upgrades_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* BarnQuest = "q_paying_barn";
constexpr int MaxBarnUpgrades = 30;

// A build: coin earned and the bitmask of upgrades chosen.
struct BarnBuild { int64_t Coin = 0; int Chosen = 0; };

// Seeded values (Java BarnUpgrades.values): the first Base upgrades cost coin, the rest earn it.
inline std::vector<int> BarnValues(int64_t Seed, int N, int Base, int MaxGain, int MaxCost)
{
	StableRng Rng(Seed);
	std::vector<int> V(N);
	for (int i = 0; i < N; ++i) V[i] = i < Base ? -1 - Rng.NextInt(MaxCost) : 1 + Rng.NextInt(MaxGain);
	return V;
}

// Seeded prerequisites: each earner needs each groundwork upgrade with probability Percent/100.
inline std::vector<int> BarnNeeds(int64_t Seed, int N, int Base, int Percent)
{
	StableRng Rng(Seed ^ 0x3C6EF372FE94F82BLL);
	std::vector<int> Need(N, 0);
	for (int i = Base; i < N; ++i)
		for (int j = 0; j < Base; ++j)
			if (Rng.NextInt(100) < Percent) Need[i] |= 1 << j;
	return Need;
}

inline int64_t BarnCoin(const std::vector<int>& Value, int Chosen)
{
	int64_t Total = 0;
	for (size_t i = 0; i < Value.size(); ++i)
		if (Chosen & (1 << i)) Total += Value[i];
	return Total;
}

// Smallest prerequisite-closed set containing Mask.
inline int BarnClosure(const std::vector<int>& Need, int Mask)
{
	int C = Mask;
	for (bool Grew = true; Grew;)
	{
		Grew = false;
		for (size_t i = 0; i < Need.size(); ++i)
			if ((C & (1 << i)) && (Need[i] & ~C)) { C |= Need[i]; Grew = true; }
	}
	return C;
}

inline bool BarnClosed(const std::vector<int>& Need, int Chosen)
{
	for (size_t i = 0; i < Need.size(); ++i)
		if ((Chosen & (1 << i)) && (Need[i] & ~Chosen)) return false;
	return true;
}

// Most coin from a prerequisite-closed set, exactly: maximum-weight closure via min cut (Edmonds-Karp).
inline BarnBuild BarnBest(const std::vector<int>& Value, const std::vector<int>& Need)
{
	const int N = static_cast<int>(Value.size());
	const int S = N, T = N + 1, M = N + 2;
	int64_t Big = 1, Positive = 0;
	for (int V : Value) { Big += std::abs(V); Positive += std::max(0, V); }
	std::vector<std::vector<int64_t>> Cap(M, std::vector<int64_t>(M, 0));
	for (int i = 0; i < N; ++i)
	{
		if (Value[i] > 0) Cap[S][i] = Value[i];
		else if (Value[i] < 0) Cap[i][T] = -Value[i];
		for (int j = 0; j < N; ++j)
			if (Need[i] & (1 << j)) Cap[i][j] = Big;
	}
	for (int64_t Flow = 0;;)
	{
		std::vector<int> Prev(M, -1);
		Prev[S] = S;
		std::deque<int> Queue{ S };
		while (!Queue.empty() && Prev[T] < 0)
		{
			const int U = Queue.front();
			Queue.pop_front();
			for (int V = 0; V < M; ++V)
				if (Prev[V] < 0 && Cap[U][V] > 0) { Prev[V] = U; Queue.push_back(V); }
		}
		if (Prev[T] < 0)
		{
			int Chosen = 0;
			for (int i = 0; i < N; ++i)
				if (Prev[i] >= 0) Chosen |= 1 << i;
			return { Positive - Flow, Chosen };
		}
		int64_t Push = std::numeric_limits<int64_t>::max();
		for (int V = T; V != S; V = Prev[V]) Push = std::min(Push, Cap[Prev[V]][V]);
		for (int V = T; V != S; V = Prev[V]) { Cap[Prev[V]][V] -= Push; Cap[V][Prev[V]] += Push; }
		Flow += Push;
	}
}

// Naive habit: add any single upgrade (with its prerequisites) that pays on its own, until none does.
inline BarnBuild BarnOneAtATime(const std::vector<int>& Value, const std::vector<int>& Need)
{
	int Built = 0;
	for (bool Grew = true; Grew;)
	{
		Grew = false;
		for (size_t i = 0; i < Value.size(); ++i)
		{
			if (Built & (1 << i)) continue;
			const int Add = BarnClosure(Need, 1 << i) & ~Built;
			if (BarnCoin(Value, Add) > 0) { Built |= Add; Grew = true; }
		}
	}
	return { BarnCoin(Value, Built), Built };
}

inline bool BarnQuestDone(const std::vector<int>& Value, const std::vector<int>& Need, int Chosen)
{
	return (static_cast<uint32_t>(Chosen) >> Value.size()) == 0 && BarnClosed(Need, Chosen) && BarnCoin(Value, Chosen) == BarnBest(Value, Need).Coin;
}

} } // namespace daedalus::stable
