// SPDX-License-Identifier: MIT
// G540 Lantern Posts (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.LanternPosts line for line (stable_lantern_posts_parity.txt,
// checked by StableCoresParityTest.java and stable_lantern_posts_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* LanternQuest = "q_paths_lit";
constexpr int LanternInfeasible = -1;

// Lighter[e] is the junction whose lantern lights path e (e or its parent); -1 for the root.
struct LanternPlan { int Cost = 0; std::vector<int> Lighter; };

// Seeded yard tree (Java LanternPosts.yard): Parent[i] is an earlier junction, Parent[0] = -1.
inline std::vector<int> LanternYard(int64_t Seed, int N)
{
	StableRng Rng(Seed);
	std::vector<int> Parent(N, -1);
	for (int i = 1; i < N; ++i) Parent[i] = Rng.NextInt(i);
	return Parent;
}

// Seeded lantern prices in [1, MaxPrice] (Java LanternPosts.prices).
inline std::vector<int> LanternPrices(int64_t Seed, int N, int MaxPrice)
{
	StableRng Rng(Seed ^ static_cast<int64_t>(0xBB67AE8584CAA73BULL));
	std::vector<int> P(N);
	for (int& V : P) V = 1 + Rng.NextInt(MaxPrice);
	return P;
}

namespace lantern_detail {

constexpr int64_t Inf = std::numeric_limits<int64_t>::max() / 4;
// F[0][v]: v unlit, own path lit from above; F[1][v]: v lit, own path lit from above; F[2][v]: v lights its own path too.
using Table = std::vector<std::vector<int64_t>>;

// Cost of hanging at v with Slots child paths to light; Mine (optional) marks the children v lights.
inline int64_t Lit(const std::vector<int>& Parent, const std::vector<int>& Price, const Table& F, int v, int Slots,
	std::vector<bool>* Mine)
{
	const int N = static_cast<int>(Parent.size());
	int64_t Sum = Price[v];
	int Forced = 0;
	std::vector<int64_t> Gain;
	std::vector<int> Who;
	for (int c = v + 1; c < N; ++c)
	{
		if (Parent[c] != v) continue;
		const int64_t ByV = std::min(F[0][c], F[1][c]), Own = F[2][c];
		if (Own >= Inf)
		{
			++Forced;
			Sum = std::min(Inf, Sum + ByV);
			if (Mine) (*Mine)[c] = true;
		}
		else
		{
			Sum = std::min(Inf, Sum + Own);
			if (ByV < Own) { Gain.push_back(Own - ByV); Who.push_back(c); }
		}
	}
	if (Forced > Slots || Sum >= Inf) return Inf;
	std::vector<bool> Used(Gain.size(), false);
	for (int k = 0; k < Slots - Forced; ++k)
	{
		int Pick = -1;
		for (int i = 0; i < static_cast<int>(Gain.size()); ++i)
			if (!Used[i] && (Pick < 0 || Gain[i] > Gain[Pick])) Pick = i;
		if (Pick < 0) break;
		Used[Pick] = true;
		Sum -= Gain[Pick];
		if (Mine) (*Mine)[Who[Pick]] = true;
	}
	return Sum;
}

} // namespace lantern_detail

// Cheapest lanterns lighting every path, each lantern lighting at most Reach paths (tree DP).
inline LanternPlan LanternBest(const std::vector<int>& Parent, const std::vector<int>& Price, int Reach)
{
	using namespace lantern_detail;
	const int N = static_cast<int>(Parent.size());
	Table F(3, std::vector<int64_t>(N, 0));
	for (int v = N - 1; v >= 0; --v)
	{
		int64_t Own = 0;
		for (int c = v + 1; c < N; ++c)
			if (Parent[c] == v) Own = std::min(Inf, Own + F[2][c]);
		F[0][v] = Own;
		F[1][v] = Lit(Parent, Price, F, v, Reach, nullptr);
		F[2][v] = Reach >= 1 ? Lit(Parent, Price, F, v, Reach - 1, nullptr) : Inf;
	}
	const int64_t Total = std::min(F[0][0], F[1][0]);
	if (Total >= Inf) return { LanternInfeasible, {} };
	LanternPlan Plan{ static_cast<int>(Total), std::vector<int>(N, 0) };
	Plan.Lighter[0] = -1;
	std::vector<int> State(N, 0);
	State[0] = F[0][0] <= F[1][0] ? 0 : 1;
	for (int v = 0; v < N; ++v)
	{
		std::vector<bool> Mine(N, false);
		if (State[v] != 0) Lit(Parent, Price, F, v, State[v] == 1 ? Reach : Reach - 1, &Mine);
		for (int c = v + 1; c < N; ++c)
		{
			if (Parent[c] != v) continue;
			if (Mine[c]) { Plan.Lighter[c] = v; State[c] = F[0][c] <= F[1][c] ? 0 : 1; }
			else { Plan.Lighter[c] = c; State[c] = 2; }
		}
	}
	return Plan;
}

// Naive habit: hang where the most dark paths per coin are, until every path is lit.
inline LanternPlan LanternBusiestFirst(const std::vector<int>& Parent, const std::vector<int>& Price, int Reach)
{
	const int N = static_cast<int>(Parent.size());
	LanternPlan Plan{ 0, std::vector<int>(N, -2) };
	Plan.Lighter[0] = -1;
	auto DarkAt = [&](int v) {
		int D = 0;
		for (int e = 1; e < N; ++e)
			if (Plan.Lighter[e] == -2 && (e == v || Parent[e] == v)) ++D;
		return D;
	};
	std::vector<bool> Hung(N, false);
	for (int Dark = N - 1; Dark > 0;)
	{
		int Pick = -1, PickGain = 0;
		for (int v = 0; v < N; ++v)
		{
			if (Hung[v]) continue;
			const int Gain = std::min(Reach, DarkAt(v));
			if (Gain > 0 && (Pick < 0 || static_cast<int64_t>(Gain) * Price[Pick] > static_cast<int64_t>(PickGain) * Price[v])) { Pick = v; PickGain = Gain; }
		}
		if (Pick < 0) return { LanternInfeasible, {} };
		Hung[Pick] = true;
		Plan.Cost += Price[Pick];
		for (int e = 1, Left = Reach; e < N && Left > 0; ++e)
			if (Plan.Lighter[e] == -2 && (e == Pick || Parent[e] == Pick)) { Plan.Lighter[e] = Pick; --Left; --Dark; }
	}
	return Plan;
}

// Cost of a lighting plan, or LanternInfeasible when a path is lit from elsewhere or a lantern exceeds Reach.
inline int LanternLight(const std::vector<int>& Parent, const std::vector<int>& Price, int Reach, const std::vector<int>& Lighter)
{
	const int N = static_cast<int>(Parent.size());
	if (static_cast<int>(Lighter.size()) != N) return LanternInfeasible;
	std::vector<int> Load(N, 0);
	for (int e = 1; e < N; ++e)
	{
		const int v = Lighter[e];
		if (v != e && v != Parent[e]) return LanternInfeasible;
		if (++Load[v] > Reach) return LanternInfeasible;
	}
	int Cost = 0;
	for (int v = 0; v < N; ++v)
		if (Load[v] > 0) Cost += Price[v];
	return Cost;
}

inline bool LanternQuestDone(const std::vector<int>& Parent, const std::vector<int>& Price, int Reach, const std::vector<int>& Lighter)
{
	const int Got = LanternLight(Parent, Price, Reach, Lighter);
	return Got != LanternInfeasible && Got == LanternBest(Parent, Price, Reach).Cost;
}

} } // namespace daedalus::stable
