// SPDX-License-Identifier: MIT
// G539 Water Trough Fill (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.WaterTroughFill line for line (stable_water_trough_fill_parity.txt,
// checked by StableCoresParityTest.java and stable_water_trough_fill_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* TroughQuest = "q_troughs_full";
constexpr int TroughInfeasible = -1;

// Directed pipes from the well (node 0) to the trough (node Nodes - 1).
struct TroughPipes { int Nodes = 2; std::vector<int> From, To, Cap, Cost; };
struct TroughPlan { int Cost = 0; std::vector<int> Flow; };

// Seeded network (Java WaterTroughFill.pipes): downhill pipes are likelier than uphill ones.
inline TroughPipes TroughSeed(int64_t Seed, int Nodes, int MaxCap)
{
	StableRng Rng(Seed);
	TroughPipes P;
	P.Nodes = Nodes;
	for (int i = 0; i < Nodes; ++i)
		for (int j = 0; j < Nodes; ++j)
			if (i != j && Rng.NextInt(5) < (i < j ? 3 : 1))
			{
				P.From.push_back(i);
				P.To.push_back(j);
				P.Cap.push_back(1 + Rng.NextInt(MaxCap));
				P.Cost.push_back(1 + Rng.NextInt(9));
			}
	return P;
}

namespace trough_detail {

// Successive shortest paths (Bellman-Ford); Undo allows pushing water back along a used pipe.
inline TroughPlan Route(const TroughPipes& P, int Demand, bool Undo)
{
	constexpr int Inf = std::numeric_limits<int>::max();
	const int E = static_cast<int>(P.From.size());
	const int N = P.Nodes, Sink = N - 1;
	TroughPlan Plan{ 0, std::vector<int>(E, 0) };
	for (int Sent = 0; Sent < Demand;)
	{
		std::vector<int> Dist(N, Inf), Via(N, -1);
		Dist[0] = 0;
		for (int Round = 0; Round < N; ++Round)
		{
			bool Moved = false;
			for (int i = 0; i < E; ++i)
			{
				const int A = P.From[i], B = P.To[i];
				if (Dist[A] != Inf && Plan.Flow[i] < P.Cap[i] && Dist[A] + P.Cost[i] < Dist[B]) { Dist[B] = Dist[A] + P.Cost[i]; Via[B] = 2 * i; Moved = true; }
				if (Undo && Dist[B] != Inf && Plan.Flow[i] > 0 && Dist[B] - P.Cost[i] < Dist[A]) { Dist[A] = Dist[B] - P.Cost[i]; Via[A] = 2 * i + 1; Moved = true; }
			}
			if (!Moved) break;
		}
		if (Dist[Sink] == Inf) return { TroughInfeasible, {} };
		int Push = Demand - Sent;
		for (int v = Sink; v != 0;)
		{
			const int i = Via[v] / 2;
			if (Via[v] % 2 == 0) { Push = std::min(Push, P.Cap[i] - Plan.Flow[i]); v = P.From[i]; }
			else { Push = std::min(Push, Plan.Flow[i]); v = P.To[i]; }
		}
		for (int v = Sink; v != 0;)
		{
			const int i = Via[v] / 2;
			if (Via[v] % 2 == 0) { Plan.Flow[i] += Push; v = P.From[i]; }
			else { Plan.Flow[i] -= Push; v = P.To[i]; }
		}
		Sent += Push;
		Plan.Cost += Push * Dist[Sink];
	}
	return Plan;
}

} // namespace trough_detail

// Least pumping cost to deliver Demand units (min-cost flow with undo along used pipes).
inline TroughPlan TroughBest(const TroughPipes& P, int Demand) { return trough_detail::Route(P, Demand, true); }

// Naive habit: keep sending along the cheapest pipe path with room left, never undoing.
inline TroughPlan TroughCheapestPath(const TroughPipes& P, int Demand) { return trough_detail::Route(P, Demand, false); }

// Cost of a flow, or TroughInfeasible when a pipe overflows, water pools at a junction or the demand is missed.
inline int TroughPump(const TroughPipes& P, int Demand, const std::vector<int>& Flow)
{
	const int E = static_cast<int>(P.From.size());
	if (static_cast<int>(Flow.size()) != E) return TroughInfeasible;
	std::vector<int> Balance(P.Nodes, 0);
	int Total = 0;
	for (int i = 0; i < E; ++i)
	{
		if (Flow[i] < 0 || Flow[i] > P.Cap[i]) return TroughInfeasible;
		Balance[P.From[i]] -= Flow[i];
		Balance[P.To[i]] += Flow[i];
		Total += Flow[i] * P.Cost[i];
	}
	for (int v = 1; v < P.Nodes - 1; ++v)
		if (Balance[v] != 0) return TroughInfeasible;
	if (Balance[0] != -Demand || Balance[P.Nodes - 1] != Demand) return TroughInfeasible;
	return Total;
}

inline bool TroughQuestDone(const TroughPipes& P, int Demand, const std::vector<int>& Flow)
{
	const int Got = TroughPump(P, Demand, Flow);
	return Got != TroughInfeasible && Got == TroughBest(P, Demand).Cost;
}

} } // namespace daedalus::stable
