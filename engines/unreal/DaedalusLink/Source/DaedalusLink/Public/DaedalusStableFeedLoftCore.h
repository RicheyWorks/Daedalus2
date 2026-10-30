// SPDX-License-Identifier: MIT
// G516 Feed Loft (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.FeedLoft line for line (stable_feed_loft_parity.txt,
// checked by StableCoresParityTest.java and stable_feed_loft_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* FeedLoftQuest = "q_full_manger";

struct Bale { int Weight, Bulk, Nourishment; };
struct LoftLoad { int Nourishment = 0; std::vector<int> Bales; };

// Seeded hay delivery (Java FeedLoft.delivery): weight and bulk in [1, MaxSize], nourishment in [1, 20].
inline std::vector<Bale> LoftDelivery(int64_t Seed, int N, int MaxSize)
{
	StableRng Rng(Seed);
	std::vector<Bale> Out;
	for (int i = 0; i < N; ++i)
	{
		const int W = 1 + Rng.NextInt(MaxSize);
		const int B = 1 + Rng.NextInt(MaxSize);
		Out.push_back({ W, B, 1 + Rng.NextInt(20) });
	}
	return Out;
}

// Most nourishment within both the weight and the bulk limit (two-constraint 0/1 knapsack).
inline LoftLoad LoftBest(const std::vector<Bale>& Bales, int MaxWeight, int MaxBulk)
{
	const int N = static_cast<int>(Bales.size());
	const int W1 = MaxWeight + 1, K1 = MaxBulk + 1;
	std::vector<int> V(static_cast<size_t>(N + 1) * W1 * K1, 0);
	auto At = [&](int i, int w, int k) -> int& { return V[(static_cast<size_t>(i) * W1 + w) * K1 + k]; };
	for (int i = 1; i <= N; ++i)
	{
		const Bale& B = Bales[i - 1];
		for (int w = 0; w <= MaxWeight; ++w)
		{
			for (int k = 0; k <= MaxBulk; ++k)
			{
				const int Skip = At(i - 1, w, k);
				const int Take = B.Weight <= w && B.Bulk <= k ? At(i - 1, w - B.Weight, k - B.Bulk) + B.Nourishment : -1;
				At(i, w, k) = std::max(Skip, Take);
			}
		}
	}
	LoftLoad L;
	L.Nourishment = At(N, MaxWeight, MaxBulk);
	int w = MaxWeight, k = MaxBulk;
	for (int i = N; i >= 1; --i)
	{
		if (At(i, w, k) != At(i - 1, w, k))
		{
			L.Bales.insert(L.Bales.begin(), i - 1);
			w -= Bales[i - 1].Weight;
			k -= Bales[i - 1].Bulk;
		}
	}
	return L;
}

// The habit: best nourishment per unit weight first, ignoring bulk; take whatever still fits.
inline LoftLoad LoftGreedy(const std::vector<Bale>& Bales, int MaxWeight, int MaxBulk)
{
	std::vector<int> Order(Bales.size());
	for (size_t i = 0; i < Order.size(); ++i) Order[i] = static_cast<int>(i);
	std::stable_sort(Order.begin(), Order.end(), [&](int A, int B) {
		const int64_t L = static_cast<int64_t>(Bales[A].Nourishment) * std::max(1, Bales[B].Weight);
		const int64_t R = static_cast<int64_t>(Bales[B].Nourishment) * std::max(1, Bales[A].Weight);
		return L != R ? L > R : A < B;
	});
	LoftLoad Out;
	int w = 0, k = 0;
	for (int Idx : Order)
	{
		const Bale& B = Bales[Idx];
		if (w + B.Weight <= MaxWeight && k + B.Bulk <= MaxBulk)
		{
			w += B.Weight;
			k += B.Bulk;
			Out.Nourishment += B.Nourishment;
			Out.Bales.push_back(Idx);
		}
	}
	std::sort(Out.Bales.begin(), Out.Bales.end());
	return Out;
}

// Nourishment of a chosen stack, or -1 when an index repeats, is out of range or a limit is broken.
inline int LoftStack(const std::vector<Bale>& Bales, const std::vector<int>& Chosen, int MaxWeight, int MaxBulk)
{
	std::vector<bool> Used(Bales.size(), false);
	int w = 0, k = 0, Total = 0;
	for (int Idx : Chosen)
	{
		if (Idx < 0 || Idx >= static_cast<int>(Bales.size()) || Used[Idx]) return -1;
		Used[Idx] = true;
		w += Bales[Idx].Weight;
		k += Bales[Idx].Bulk;
		Total += Bales[Idx].Nourishment;
	}
	return w <= MaxWeight && k <= MaxBulk ? Total : -1;
}

inline bool LoftQuest(const std::vector<Bale>& Bales, const std::vector<int>& Chosen, int MaxWeight, int MaxBulk)
{
	const int Got = LoftStack(Bales, Chosen, MaxWeight, MaxBulk);
	return Got >= 0 && Got == LoftBest(Bales, MaxWeight, MaxBulk).Nourishment;
}

} } // namespace daedalus::stable
