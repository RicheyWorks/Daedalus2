// SPDX-License-Identifier: MIT
// G530 Tack Room Pegs (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.TackRoomPegs line for line (stable_tack_room_pegs_parity.txt,
// checked by StableCoresParityTest.java and stable_tack_room_pegs_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* TackRoomQuest = "q_tidy_tack_room";
constexpr int MaxTack = 14;

struct TackRoom { int Pegs = 0; std::vector<int> PegOf; };

// Seeded tack weights in [1, Limit] (Java TackRoomPegs.weights).
inline std::vector<int> TackWeights(int64_t Seed, int N, int Limit)
{
	StableRng Rng(Seed);
	std::vector<int> W(N);
	for (int& V : W) V = 1 + Rng.NextInt(Limit);
	return W;
}

// Seeded mutual feud masks: each pair feuds with probability Percent/100 (Java TackRoomPegs.feuds).
inline std::vector<int> TackFeuds(int64_t Seed, int N, int Percent)
{
	StableRng Rng(Seed ^ 0x5DEECE66DLL);
	std::vector<int> F(N, 0);
	for (int i = 0; i < N; ++i)
		for (int j = i + 1; j < N; ++j)
			if (Rng.NextInt(100) < Percent) { F[i] |= 1 << j; F[j] |= 1 << i; }
	return F;
}

// Fewest pegs, exactly: DP over subsets of tack, each peg one light, feud-free subset.
inline TackRoom TackBest(const std::vector<int>& Weight, const std::vector<int>& Feud, int Limit)
{
	const int N = static_cast<int>(Weight.size());
	const int States = 1 << N;
	std::vector<bool> Ok(States, false);
	std::vector<int> Load(States, 0), Pegs(States, 0), Pick(States, 0);
	Ok[0] = true;
	for (int s = 1; s < States; ++s)
	{
		int Low = 0;
		while (((s >> Low) & 1) == 0) ++Low;
		const int Rest = s & (s - 1);
		Load[s] = Load[Rest] + Weight[Low];
		Ok[s] = Ok[Rest] && Load[s] <= Limit && (Feud[Low] & Rest) == 0;
	}
	for (int s = 1; s < States; ++s)
	{
		const int Low = s & -s;
		const int Rest = s ^ Low;
		Pegs[s] = std::numeric_limits<int>::max();
		for (int t = Rest;; t = (t - 1) & Rest)
		{
			const int Group = t | Low;
			if (Ok[Group] && Pegs[s ^ Group] + 1 < Pegs[s]) { Pegs[s] = Pegs[s ^ Group] + 1; Pick[s] = Group; }
			if (t == 0) break;
		}
	}
	TackRoom R;
	R.Pegs = Pegs[States - 1];
	R.PegOf.assign(N, 0);
	int Peg = 0;
	for (int s = States - 1; s != 0; s ^= Pick[s], ++Peg)
		for (int i = 0; i < N; ++i)
			if (Pick[s] & (1 << i)) R.PegOf[i] = Peg;
	return R;
}

// Naive first fit in tack order: first peg with room and no feud, else a new peg.
inline TackRoom TackFirstFit(const std::vector<int>& Weight, const std::vector<int>& Feud, int Limit)
{
	std::vector<int> PegLoad, PegMembers;
	TackRoom R;
	for (size_t i = 0; i < Weight.size(); ++i)
	{
		size_t Chosen = PegLoad.size();
		for (size_t p = 0; p < PegLoad.size(); ++p)
			if (PegLoad[p] + Weight[i] <= Limit && (Feud[i] & PegMembers[p]) == 0) { Chosen = p; break; }
		if (Chosen == PegLoad.size()) { PegLoad.push_back(0); PegMembers.push_back(0); }
		PegLoad[Chosen] += Weight[i];
		PegMembers[Chosen] |= 1 << i;
		R.PegOf.push_back(static_cast<int>(Chosen));
	}
	R.Pegs = static_cast<int>(PegLoad.size());
	return R;
}

// Pegs used by a hanging, or -1 when a peg is overloaded, a feud shares a peg or a peg is out of range.
inline int TackHang(const std::vector<int>& Weight, const std::vector<int>& Feud, int Limit, const std::vector<int>& PegOf)
{
	const int N = static_cast<int>(Weight.size());
	if (static_cast<int>(PegOf.size()) != N) return -1;
	std::vector<int> Load(N, 0), Members(N, 0);
	int Used = 0;
	for (int i = 0; i < N; ++i)
	{
		const int p = PegOf[i];
		if (p < 0 || p >= N || (Feud[i] & Members[p]) != 0) return -1;
		if (Members[p] == 0) ++Used;
		Load[p] += Weight[i];
		Members[p] |= 1 << i;
		if (Load[p] > Limit) return -1;
	}
	return Used;
}

inline bool TackQuest(const std::vector<int>& Weight, const std::vector<int>& Feud, int Limit, const std::vector<int>& PegOf)
{
	const int Got = TackHang(Weight, Feud, Limit, PegOf);
	return Got >= 0 && Got == TackBest(Weight, Feud, Limit).Pegs;
}

} } // namespace daedalus::stable
