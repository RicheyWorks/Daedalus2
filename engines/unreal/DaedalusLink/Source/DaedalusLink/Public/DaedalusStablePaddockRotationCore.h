// SPDX-License-Identifier: MIT
// G523 Paddock Rotation (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.PaddockRotation line for line (stable_paddock_rotation_parity.txt,
// checked by StableCoresParityTest.java and stable_paddock_rotation_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* PaddockQuest = "q_green_pasture";
constexpr int MaxPaddocks = 6;

struct Pasture { std::vector<int> Cap, Growth; };
struct GrazingSeason { int Grass = 0; std::vector<int> Plan; };

// Seeded paddocks (Java PaddockRotation.paddocks): growth in [1, 4], cap in [growth, 12].
inline Pasture PaddockSeed(int64_t Seed, int M)
{
	StableRng Rng(Seed);
	Pasture P;
	for (int p = 0; p < M; ++p)
	{
		const int G = 1 + Rng.NextInt(4);
		P.Growth.push_back(G);
		P.Cap.push_back(G + Rng.NextInt(13 - G));
	}
	return P;
}

namespace paddock_detail {

// Days of rest after which each paddock is full again.
inline std::vector<int> FullRest(const Pasture& P)
{
	std::vector<int> Full;
	for (size_t p = 0; p < P.Cap.size(); ++p) Full.push_back((P.Cap[p] + P.Growth[p] - 1) / P.Growth[p]);
	return Full;
}

inline int Grass(const Pasture& P, const std::vector<int>& Rest, int p) { return std::min(P.Cap[p], P.Growth[p] * Rest[p]); }

inline std::vector<int> Step(const std::vector<int>& Full, const std::vector<int>& Rest, int Grazed)
{
	std::vector<int> Next(Rest.size());
	for (size_t p = 0; p < Rest.size(); ++p) Next[p] = static_cast<int>(p) == Grazed ? 0 : std::min(Full[p], Rest[p] + 1);
	return Next;
}

inline int Solve(const Pasture& P, const std::vector<int>& Full, const std::vector<int>& Rest, int Left,
	std::unordered_map<int64_t, int>& Memo)
{
	if (Left == 0) return 0;
	int64_t Key = Left;
	for (size_t p = 0; p < Rest.size(); ++p) Key = Key * (Full[p] + 1) + Rest[p];
	const auto Hit = Memo.find(Key);
	if (Hit != Memo.end()) return Hit->second;
	int Best = 0;
	for (int p = 0; p < static_cast<int>(Rest.size()); ++p)
		Best = std::max(Best, Grass(P, Rest, p) + Solve(P, Full, Step(Full, Rest, p), Left - 1, Memo));
	Memo[Key] = Best;
	return Best;
}

} // namespace paddock_detail

// Most grass over the season, exactly: memoised search over each paddock's days of rest.
inline GrazingSeason PaddockBest(const Pasture& P, int Days)
{
	using namespace paddock_detail;
	const std::vector<int> Full = FullRest(P);
	std::unordered_map<int64_t, int> Memo;
	std::vector<int> Rest = Full;
	GrazingSeason S;
	S.Grass = Solve(P, Full, Rest, Days, Memo);
	for (int d = 0; d < Days; ++d)
	{
		const int Target = Solve(P, Full, Rest, Days - d, Memo);
		for (int p = 0; p < static_cast<int>(P.Cap.size()); ++p)
		{
			std::vector<int> Next = Step(Full, Rest, p);
			if (Grass(P, Rest, p) + Solve(P, Full, Next, Days - d - 1, Memo) == Target)
			{
				S.Plan.push_back(p);
				Rest = Next;
				break;
			}
		}
	}
	return S;
}

// The habit: graze whichever paddock has the most grass today (lowest index on ties).
inline GrazingSeason PaddockGreedy(const Pasture& P, int Days)
{
	using namespace paddock_detail;
	const std::vector<int> Full = FullRest(P);
	std::vector<int> Rest = Full;
	GrazingSeason S;
	for (int d = 0; d < Days; ++d)
	{
		int Pick = 0;
		for (int p = 1; p < static_cast<int>(P.Cap.size()); ++p)
			if (Grass(P, Rest, p) > Grass(P, Rest, Pick)) Pick = p;
		S.Grass += Grass(P, Rest, Pick);
		S.Plan.push_back(Pick);
		Rest = Step(Full, Rest, Pick);
	}
	return S;
}

// Grass eaten by a plan, or -1 when it has the wrong length or names a missing paddock.
inline int PaddockGraze(const Pasture& P, const std::vector<int>& Plan, int Days)
{
	using namespace paddock_detail;
	if (static_cast<int>(Plan.size()) != Days) return -1;
	const std::vector<int> Full = FullRest(P);
	std::vector<int> Rest = Full;
	int Total = 0;
	for (int p : Plan)
	{
		if (p < 0 || p >= static_cast<int>(P.Cap.size())) return -1;
		Total += Grass(P, Rest, p);
		Rest = Step(Full, Rest, p);
	}
	return Total;
}

inline bool PaddockQuestDone(const Pasture& P, const std::vector<int>& Plan, int Days)
{
	const int Got = PaddockGraze(P, Plan, Days);
	return Got >= 0 && Got == PaddockBest(P, Days).Grass;
}

} } // namespace daedalus::stable
