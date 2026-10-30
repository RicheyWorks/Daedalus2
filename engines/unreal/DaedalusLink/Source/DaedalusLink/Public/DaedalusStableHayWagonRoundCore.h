// SPDX-License-Identifier: MIT
// G532 Hay Wagon Round (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.HayWagonRound line for line (stable_hay_wagon_round_parity.txt,
// checked by StableCoresParityTest.java and stable_hay_wagon_round_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* HayWagonQuest = "q_hay_on_time";
constexpr int MaxWagonStalls = 12;
constexpr int WagonInfeasible = -1;

// Barn is stop 0; stalls are 1..Stalls() with feeding windows [Open, Close].
struct Yard
{
	std::vector<int> X, Y, Open, Close;
	int Stalls() const { return static_cast<int>(X.size()) - 1; }
	int Dist(int A, int B) const { return std::abs(X[A] - X[B]) + std::abs(Y[A] - Y[B]); }
};
struct WagonRound { int Finish = 0; std::vector<int> Order; };

// Seeded yard (Java HayWagonRound.yard): windows cut around a random order so a round always exists.
inline Yard WagonYard(int64_t Seed, int Stalls, int Size, int Slack)
{
	StableRng Rng(Seed);
	const int N = Stalls + 1;
	Yard Y{ std::vector<int>(N, 0), std::vector<int>(N, 0), std::vector<int>(N, 0), std::vector<int>(N, 0) };
	for (int i = 1; i < N; ++i) { Y.X[i] = Rng.NextInt(Size); Y.Y[i] = Rng.NextInt(Size); }
	Y.X[0] = Size / 2;
	Y.Y[0] = Size / 2;
	std::vector<int> Perm(Stalls);
	for (int i = 0; i < Stalls; ++i) Perm[i] = i + 1;
	for (int i = Stalls - 1; i > 0; --i) std::swap(Perm[i], Perm[Rng.NextInt(i + 1)]);
	Y.Close[0] = std::numeric_limits<int>::max() / 4;
	int T = 0, At = 0;
	for (int s : Perm)
	{
		T += Y.Dist(At, s);
		const int Lo = Rng.NextInt(Slack + 1);
		const int Hi = Rng.NextInt(Slack + 1);
		Y.Open[s] = std::max(0, T - Lo);
		Y.Close[s] = T + Hi;
		At = s;
	}
	return Y;
}

// Earliest return feeding every stall in its window: Held-Karp keeping the earliest feed time per state.
inline WagonRound WagonBest(const Yard& Y)
{
	const int M = Y.Stalls();
	if (M == 0) return {};
	constexpr int Unset = std::numeric_limits<int>::max();
	const int States = 1 << M;
	std::vector<std::vector<int>> Fed(States, std::vector<int>(M, Unset)), Prev(States, std::vector<int>(M, -1));
	for (int j = 0; j < M; ++j)
	{
		const int Arrive = std::max(Y.Open[j + 1], Y.Dist(0, j + 1));
		if (Arrive <= Y.Close[j + 1]) Fed[1 << j][j] = Arrive;
	}
	for (int s = 1; s < States; ++s)
		for (int j = 0; j < M; ++j)
		{
			if (Fed[s][j] == Unset) continue;
			for (int k = 0; k < M; ++k)
			{
				if (s & (1 << k)) continue;
				const int Arrive = std::max(Y.Open[k + 1], Fed[s][j] + Y.Dist(j + 1, k + 1));
				const int Ns = s | (1 << k);
				if (Arrive <= Y.Close[k + 1] && Arrive < Fed[Ns][k]) { Fed[Ns][k] = Arrive; Prev[Ns][k] = j; }
			}
		}
	const int Full = States - 1;
	int BestFinish = Unset, Last = -1;
	for (int j = 0; j < M; ++j)
		if (Fed[Full][j] != Unset && Fed[Full][j] + Y.Dist(j + 1, 0) < BestFinish) { BestFinish = Fed[Full][j] + Y.Dist(j + 1, 0); Last = j; }
	if (Last < 0) return { WagonInfeasible, {} };
	WagonRound R{ BestFinish, std::vector<int>(M, 0) };
	for (int Pos = M - 1, s = Full; Pos >= 0; --Pos)
	{
		R.Order[Pos] = Last + 1;
		const int P = Prev[s][Last];
		s ^= 1 << Last;
		Last = P;
	}
	return R;
}

// Naive habit: nearest unfed stall still reachable before it closes, ties to the lower id.
inline WagonRound WagonNearest(const Yard& Y)
{
	const int M = Y.Stalls();
	std::vector<bool> Done(M + 1, false);
	WagonRound R;
	int At = 0, T = 0;
	for (int Step = 0; Step < M; ++Step)
	{
		int Pick = -1;
		for (int k = 1; k <= M; ++k)
			if (!Done[k] && T + Y.Dist(At, k) <= Y.Close[k] && (Pick < 0 || Y.Dist(At, k) < Y.Dist(At, Pick))) Pick = k;
		if (Pick < 0) return { WagonInfeasible, {} };
		T = std::max(Y.Open[Pick], T + Y.Dist(At, Pick));
		Done[Pick] = true;
		R.Order.push_back(Pick);
		At = Pick;
	}
	R.Finish = T + Y.Dist(At, 0);
	return R;
}

// Return time of a stall order, or WagonInfeasible when it misses a window, repeats or skips a stall.
inline int WagonDrive(const Yard& Y, const std::vector<int>& Order)
{
	const int M = Y.Stalls();
	if (static_cast<int>(Order.size()) != M) return WagonInfeasible;
	std::vector<bool> Seen(M + 1, false);
	int At = 0, T = 0;
	for (int s : Order)
	{
		if (s < 1 || s > M || Seen[s]) return WagonInfeasible;
		Seen[s] = true;
		T = std::max(Y.Open[s], T + Y.Dist(At, s));
		if (T > Y.Close[s]) return WagonInfeasible;
		At = s;
	}
	return T + Y.Dist(At, 0);
}

inline bool WagonQuest(const Yard& Y, const std::vector<int>& Order)
{
	const int Got = WagonDrive(Y, Order);
	return Got != WagonInfeasible && Got == WagonBest(Y).Finish;
}

} } // namespace daedalus::stable
