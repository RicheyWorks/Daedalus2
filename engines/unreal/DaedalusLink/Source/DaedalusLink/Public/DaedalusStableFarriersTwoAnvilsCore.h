// SPDX-License-Identifier: MIT
// G535 Farrier's Two Anvils (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.FarriersTwoAnvils line for line (stable_farriers_two_anvils_parity.txt,
// checked by StableCoresParityTest.java and stable_farriers_two_anvils_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* TwoAnvilsQuest = "q_two_anvils";
constexpr int MaxAnvilJobs = 10;
constexpr int MaxAnvilTime = 9;
constexpr int AnvilInvalid = -1;

struct AnvilPlan { int Makespan = 0; std::vector<int> Start, Anvil; };

// Seeded durations in [1, MaxAnvilTime] (Java FarriersTwoAnvils.durations).
inline std::vector<int> AnvilDurations(int64_t Seed, int N)
{
	StableRng Rng(Seed);
	std::vector<int> P(N);
	for (int& V : P) V = 1 + Rng.NextInt(MaxAnvilTime);
	return P;
}

// Seeded predecessor masks: job j waits for each earlier job with probability Percent/100.
inline std::vector<int> AnvilLinks(int64_t Seed, int N, int Percent)
{
	StableRng Rng(Seed ^ static_cast<int64_t>(0x9E3779B97F4A7C15ULL));
	std::vector<int> Pred(N, 0);
	for (int j = 0; j < N; ++j)
		for (int i = 0; i < j; ++i)
			if (Rng.NextInt(100) < Percent) Pred[j] |= 1 << i;
	return Pred;
}

namespace anvil_detail {

// Memoised event search over (jobs done, job on the other anvil, its time left).
struct Search
{
	const std::vector<int>& Time;
	const std::vector<int>& Pred;
	std::vector<int> Memo;
	int N;

	Search(const std::vector<int>& InTime, const std::vector<int>& InPred)
		: Time(InTime), Pred(InPred), Memo((1 << InTime.size()) * (InTime.size() + 1) * (MaxAnvilTime + 1), -1),
		  N(static_cast<int>(InTime.size())) {}

	int Ready(int Done, int Run) const
	{
		int R = 0;
		for (int k = 0; k < N; ++k)
			if ((Done & (1 << k)) == 0 && k != Run && (Pred[k] & Done) == Pred[k]) R |= 1 << k;
		return R;
	}

	int Step(int Done, int Run, int Rem, int k)
	{
		const int P = Time[k];
		if (P < Rem) return P + Solve(Done | (1 << k), Run, Rem - P);
		if (P > Rem) return Rem + Solve(Done | (1 << Run), k, P - Rem);
		return Rem + Solve(Done | (1 << Run) | (1 << k), -1, 0);
	}

	int Solve(int Done, int Run, int Rem)
	{
		if (Done == (1 << N) - 1) return 0;
		const int Key = (Done * (N + 1) + Run + 1) * (MaxAnvilTime + 1) + Rem;
		if (Memo[Key] >= 0) return Memo[Key];
		const int ReadyMask = Ready(Done, Run);
		int Best = std::numeric_limits<int>::max();
		if (Run < 0)
		{
			for (int k = 0; k < N; ++k)
				if (ReadyMask & (1 << k)) Best = std::min(Best, Solve(Done, k, Time[k]));
		}
		else
		{
			Best = Rem + Solve(Done | (1 << Run), -1, 0);
			for (int k = 0; k < N; ++k)
				if (ReadyMask & (1 << k)) Best = std::min(Best, Step(Done, Run, Rem, k));
		}
		Memo[Key] = Best;
		return Best;
	}
};

} // namespace anvil_detail

// Earliest finish on two anvils respecting the links; replays the search to recover the schedule.
inline AnvilPlan AnvilBest(const std::vector<int>& Time, const std::vector<int>& Pred)
{
	const int N = static_cast<int>(Time.size());
	anvil_detail::Search S(Time, Pred);
	AnvilPlan Plan{ S.Solve(0, -1, 0), std::vector<int>(N, 0), std::vector<int>(N, 0) };
	int Done = 0, Run = -1, Rem = 0, Busy = 0, T = 0;
	const int Full = (1 << N) - 1;
	while (Done != Full)
	{
		const int Want = S.Solve(Done, Run, Rem);
		const int ReadyMask = S.Ready(Done, Run);
		if (Run < 0)
		{
			for (int k = 0; k < N; ++k)
				if ((ReadyMask & (1 << k)) && S.Solve(Done, k, Time[k]) == Want)
				{
					Plan.Start[k] = T;
					Plan.Anvil[k] = 0;
					Busy = 0;
					Run = k;
					Rem = Time[k];
					break;
				}
			continue;
		}
		const int Free = 1 - Busy;
		int Pick = -1;
		for (int k = 0; k < N && Pick < 0; ++k)
			if ((ReadyMask & (1 << k)) && S.Step(Done, Run, Rem, k) == Want) Pick = k;
		if (Pick < 0)
		{
			T += Rem;
			Done |= 1 << Run;
			Run = -1;
			Rem = 0;
			continue;
		}
		Plan.Start[Pick] = T;
		Plan.Anvil[Pick] = Free;
		const int P = Time[Pick];
		if (P < Rem) { T += P; Done |= 1 << Pick; Rem -= P; }
		else if (P > Rem) { T += Rem; Done |= 1 << Run; Run = Pick; Busy = Free; Rem = P - Rem; }
		else { T += Rem; Done |= (1 << Run) | (1 << Pick); Run = -1; Rem = 0; }
	}
	return Plan;
}

// Graham list scheduling in job order: a free anvil never idles while some job is ready.
inline AnvilPlan AnvilListSchedule(const std::vector<int>& Time, const std::vector<int>& Pred)
{
	const int N = static_cast<int>(Time.size());
	AnvilPlan Plan{ 0, std::vector<int>(N, 0), std::vector<int>(N, 0) };
	std::vector<int> Finish(N, 0);
	std::vector<bool> Started(N, false);
	int FreeAt[2] = { 0, 0 };
	auto ReadyAt = [&](int k, int T) {
		for (int i = 0; i < N; ++i)
			if ((Pred[k] & (1 << i)) && (!Started[i] || Finish[i] > T)) return false;
		return true;
	};
	for (int Left = N; Left > 0;)
	{
		const int A = FreeAt[0] <= FreeAt[1] ? 0 : 1;
		const int T = FreeAt[A];
		int Pick = -1;
		for (int k = 0; k < N && Pick < 0; ++k)
			if (!Started[k] && ReadyAt(k, T)) Pick = k;
		if (Pick < 0)
		{
			int Next = std::numeric_limits<int>::max();
			for (int k = 0; k < N; ++k)
				if (Started[k] && Finish[k] > T) Next = std::min(Next, Finish[k]);
			FreeAt[A] = Next;
			continue;
		}
		Started[Pick] = true;
		Plan.Start[Pick] = T;
		Plan.Anvil[Pick] = A;
		Finish[Pick] = T + Time[Pick];
		FreeAt[A] = Finish[Pick];
		Plan.Makespan = std::max(Plan.Makespan, Finish[Pick]);
		--Left;
	}
	return Plan;
}

// Makespan of a schedule, or AnvilInvalid when a link is broken, an anvil overlaps or a field is bad.
inline int AnvilFinish(const std::vector<int>& Time, const std::vector<int>& Pred, const std::vector<int>& Start,
	const std::vector<int>& Anvil)
{
	const int N = static_cast<int>(Time.size());
	if (static_cast<int>(Start.size()) != N || static_cast<int>(Anvil.size()) != N) return AnvilInvalid;
	int Makespan = 0;
	for (int j = 0; j < N; ++j)
	{
		if (Start[j] < 0 || (Anvil[j] != 0 && Anvil[j] != 1)) return AnvilInvalid;
		for (int i = 0; i < N; ++i)
		{
			if ((Pred[j] & (1 << i)) && Start[i] + Time[i] > Start[j]) return AnvilInvalid;
			if (i != j && Anvil[i] == Anvil[j] && Start[i] < Start[j] + Time[j] && Start[j] < Start[i] + Time[i]) return AnvilInvalid;
		}
		Makespan = std::max(Makespan, Start[j] + Time[j]);
	}
	return Makespan;
}

inline bool AnvilQuest(const std::vector<int>& Time, const std::vector<int>& Pred, const std::vector<int>& Start,
	const std::vector<int>& Anvil)
{
	const int Got = AnvilFinish(Time, Pred, Start, Anvil);
	return Got != AnvilInvalid && Got == AnvilBest(Time, Pred).Makespan;
}

} } // namespace daedalus::stable
