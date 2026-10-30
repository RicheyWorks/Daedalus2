// SPDX-License-Identifier: MIT
// G542 Hay Bale Stacking (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.HayBaleStacking line for line (stable_hay_bale_stacking_parity.txt,
// checked by StableCoresParityTest.java and stable_hay_bale_stacking_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* BaleQuest = "q_tall_stack";
constexpr int MaxBales = 16;
constexpr int MaxBaleWeight = 9;
constexpr int BaleInvalid = -1;

struct Bales
{
	std::vector<int> A, B, Height, Weight, Strength;
	int Size() const { return static_cast<int>(A.size()); }
	int Area(int i) const { return A[i] * B[i]; }
	// Top sits on Bottom when it is strictly smaller both ways (bales may turn).
	bool FitsOn(int Top, int Bottom) const
	{
		return std::min(A[Top], B[Top]) < std::min(A[Bottom], B[Bottom]) && std::max(A[Top], B[Top]) < std::max(A[Bottom], B[Bottom]);
	}
};
struct BaleStack { int Height = 0; std::vector<int> BottomUp; };

// Seeded bales (Java HayBaleStacking.bales).
inline Bales BaleSeed(int64_t Seed, int N)
{
	StableRng Rng(Seed);
	Bales S;
	for (int i = 0; i < N; ++i)
	{
		S.A.push_back(1 + Rng.NextInt(12));
		S.B.push_back(1 + Rng.NextInt(12));
		S.Height.push_back(1 + Rng.NextInt(9));
		S.Weight.push_back(1 + Rng.NextInt(5));
		S.Strength.push_back(Rng.NextInt(11));
	}
	return S;
}

// Height of a bottom-up stack, or BaleInvalid when a bale repeats, overhangs or is crushed.
inline int BaleStackHeight(const Bales& S, const std::vector<int>& BottomUp)
{
	const int N = S.Size();
	std::vector<bool> Used(N, false);
	int Height = 0;
	for (size_t k = 0; k < BottomUp.size(); ++k)
	{
		const int i = BottomUp[k];
		if (i < 0 || i >= N || Used[i] || (k > 0 && !S.FitsOn(i, BottomUp[k - 1]))) return BaleInvalid;
		Used[i] = true;
		Height += S.Height[i];
	}
	int Above = 0;
	for (size_t k = BottomUp.size(); k-- > 0;)
	{
		if (Above > S.Strength[BottomUp[k]]) return BaleInvalid;
		Above += S.Weight[BottomUp[k]];
	}
	return Height;
}

// Tallest legal stack: DP over (bottom bale, total weight) in rising area order.
inline BaleStack BaleBest(const Bales& S)
{
	const int N = S.Size();
	const int Cap = N * MaxBaleWeight;
	std::vector<int> Order(N);
	for (int i = 0; i < N; ++i) Order[i] = i;
	std::stable_sort(Order.begin(), Order.end(), [&](int X, int Y) { return S.Area(X) < S.Area(Y); });
	std::vector<std::vector<int>> Tall(N, std::vector<int>(Cap + 1, -1)), Next(N, std::vector<int>(Cap + 1, 0));
	for (int Oi = 0; Oi < N; ++Oi)
	{
		const int i = Order[Oi], Wi = S.Weight[i];
		Tall[i][Wi] = S.Height[i];
		Next[i][Wi] = -1;
		for (int Oj = 0; Oj < Oi; ++Oj)
		{
			const int j = Order[Oj];
			if (!S.FitsOn(j, i)) continue;
			for (int w = 1; w <= std::min(Cap - Wi, S.Strength[i]); ++w)
				if (Tall[j][w] >= 0 && Tall[j][w] + S.Height[i] > Tall[i][w + Wi]) { Tall[i][w + Wi] = Tall[j][w] + S.Height[i]; Next[i][w + Wi] = j; }
		}
	}
	int Bh = 0, Bi = -1, Bw = 0;
	for (int i = 0; i < N; ++i)
		for (int w = 0; w <= Cap; ++w)
			if (Tall[i][w] > Bh) { Bh = Tall[i][w]; Bi = i; Bw = w; }
	BaleStack R{ Bh, {} };
	while (Bi >= 0)
	{
		R.BottomUp.push_back(Bi);
		const int j = Next[Bi][Bw];
		Bw -= S.Weight[Bi];
		Bi = j;
	}
	return R;
}

// Naive habit: biggest bale first, keep each next bale that still leaves a legal stack.
inline BaleStack BaleBiggestFirst(const Bales& S)
{
	std::vector<int> Order(S.Size());
	for (int i = 0; i < S.Size(); ++i) Order[i] = i;
	std::stable_sort(Order.begin(), Order.end(), [&](int X, int Y) { return S.Area(X) != S.Area(Y) ? S.Area(X) > S.Area(Y) : X < Y; });
	BaleStack R;
	for (int i : Order)
	{
		R.BottomUp.push_back(i);
		if (BaleStackHeight(S, R.BottomUp) == BaleInvalid) R.BottomUp.pop_back();
	}
	R.Height = BaleStackHeight(S, R.BottomUp);
	return R;
}

inline bool BaleQuestDone(const Bales& S, const std::vector<int>& BottomUp)
{
	const int Got = BaleStackHeight(S, BottomUp);
	return Got != BaleInvalid && Got == BaleBest(S).Height;
}

} } // namespace daedalus::stable
