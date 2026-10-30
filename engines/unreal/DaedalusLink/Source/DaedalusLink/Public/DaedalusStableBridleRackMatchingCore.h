// SPDX-License-Identifier: MIT
// G537 Bridle Rack Matching (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.BridleRackMatching line for line (stable_bridle_rack_matching_parity.txt,
// checked by StableCoresParityTest.java and stable_bridle_rack_matching_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* BridleQuest = "q_all_tacked";
constexpr int MaxBridleHorses = 10;
constexpr int BridleInfeasible = -1;

// Time[groom][horse]; a groom may tack a horse when Skill[groom] >= Temper[horse].
struct BridleStable { std::vector<int> Temper, Skill; std::vector<std::vector<int>> Time; };
struct BridlePairing { int Ready = 0; std::vector<int> GroomOf; };

// Seeded stable (Java temperaments, skills and times, each with its own seed stream).
inline BridleStable BridleSeed(int64_t Seed, int N)
{
	BridleStable S;
	StableRng TemperRng(Seed);
	for (int i = 0; i < N; ++i) S.Temper.push_back(1 + TemperRng.NextInt(5));
	StableRng SkillRng(Seed ^ 0x2545F4914F6CDD1DLL);
	for (int i = 0; i < N; ++i) S.Skill.push_back(S.Temper[i] + SkillRng.NextInt(2));
	for (int i = N - 1; i > 0; --i) std::swap(S.Skill[i], S.Skill[SkillRng.NextInt(i + 1)]);
	StableRng TimeRng(Seed ^ 0x6A09E667F3BCC909LL);
	S.Time.assign(N, std::vector<int>(N, 0));
	for (auto& Row : S.Time)
		for (int& V : Row) V = 1 + TimeRng.NextInt(20);
	return S;
}

namespace bridle_detail {

inline bool Augment(const BridleStable& S, int Limit, int H, std::vector<bool>& Seen, std::vector<int>& HorseOf,
	std::vector<int>& GroomOf)
{
	for (size_t g = 0; g < S.Skill.size(); ++g)
		if (!Seen[g] && S.Skill[g] >= S.Temper[H] && S.Time[g][H] <= Limit)
		{
			Seen[g] = true;
			if (HorseOf[g] < 0 || Augment(S, Limit, HorseOf[g], Seen, HorseOf, GroomOf))
			{
				HorseOf[g] = H;
				GroomOf[H] = static_cast<int>(g);
				return true;
			}
		}
	return false;
}

} // namespace bridle_detail

// Bottleneck assignment: the lowest time limit whose allowed fast pairs hold a perfect matching.
inline BridlePairing BridleBest(const BridleStable& S)
{
	const int N = static_cast<int>(S.Skill.size());
	if (N == 0) return {};
	std::vector<int> Limits;
	for (int g = 0; g < N; ++g)
		for (int h = 0; h < N; ++h)
			if (S.Skill[g] >= S.Temper[h]) Limits.push_back(S.Time[g][h]);
	std::sort(Limits.begin(), Limits.end());
	Limits.erase(std::unique(Limits.begin(), Limits.end()), Limits.end());
	for (int Limit : Limits)
	{
		std::vector<int> HorseOf(N, -1), GroomOf(N, -1);
		int Matched = 0;
		for (int h = 0; h < N; ++h)
		{
			std::vector<bool> Seen(N, false);
			if (bridle_detail::Augment(S, Limit, h, Seen, HorseOf, GroomOf)) ++Matched;
		}
		if (Matched == N) return { Limit, GroomOf };
	}
	return { BridleInfeasible, {} };
}

// Naive habit: repeatedly take the quickest allowed pair of a free groom and an untacked horse.
inline BridlePairing BridleCheapestFirst(const BridleStable& S)
{
	const int N = static_cast<int>(S.Skill.size());
	std::vector<bool> Busy(N, false);
	BridlePairing P{ 0, std::vector<int>(N, -1) };
	for (int Step = 0; Step < N; ++Step)
	{
		int Bg = -1, Bh = -1;
		for (int h = 0; h < N; ++h)
			for (int g = 0; g < N; ++g)
				if (P.GroomOf[h] < 0 && !Busy[g] && S.Skill[g] >= S.Temper[h] && (Bg < 0 || S.Time[g][h] < S.Time[Bg][Bh]))
				{
					Bg = g;
					Bh = h;
				}
		if (Bg < 0) return { BridleInfeasible, {} };
		Busy[Bg] = true;
		P.GroomOf[Bh] = Bg;
		P.Ready = std::max(P.Ready, S.Time[Bg][Bh]);
	}
	return P;
}

// Ready time of a pairing, or BridleInfeasible when a groom is reused, out of range or not skilled enough.
inline int BridleReady(const BridleStable& S, const std::vector<int>& GroomOf)
{
	const int N = static_cast<int>(S.Skill.size());
	if (static_cast<int>(GroomOf.size()) != N) return BridleInfeasible;
	std::vector<bool> Used(N, false);
	int Ready = 0;
	for (int h = 0; h < N; ++h)
	{
		const int g = GroomOf[h];
		if (g < 0 || g >= N || Used[g] || S.Skill[g] < S.Temper[h]) return BridleInfeasible;
		Used[g] = true;
		Ready = std::max(Ready, S.Time[g][h]);
	}
	return Ready;
}

inline bool BridleQuestDone(const BridleStable& S, const std::vector<int>& GroomOf)
{
	const int Got = BridleReady(S, GroomOf);
	return Got != BridleInfeasible && Got == BridleBest(S).Ready;
}

} } // namespace daedalus::stable
