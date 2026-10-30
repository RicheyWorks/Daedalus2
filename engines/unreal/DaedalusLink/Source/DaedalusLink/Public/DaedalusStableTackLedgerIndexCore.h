// SPDX-License-Identifier: MIT
// G545 Tack Ledger Index (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.TackLedgerIndex line for line (stable_tack_ledger_index_parity.txt,
// checked by StableCoresParityTest.java and stable_tack_ledger_index_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* LedgerQuest = "q_quick_ledger";
constexpr int64_t LedgerInvalid = -1;

// A filing: total page flips and the insertion order (preorder) of the search tree.
struct LedgerFiling { int64_t Flips = 0; std::vector<int> Order; };

// Seeded lookup frequencies in [1, MaxFreq] (Java TackLedgerIndex.frequencies).
inline std::vector<int> LedgerFrequencies(int64_t Seed, int N, int MaxFreq)
{
	StableRng Rng(Seed);
	std::vector<int> F(N);
	for (int& V : F) V = 1 + Rng.NextInt(MaxFreq);
	return F;
}

namespace ledger_detail {

inline void Preorder(const std::vector<std::vector<int>>& Root, int i, int j, std::vector<int>& Order)
{
	if (i >= j) return;
	const int r = Root[i][j];
	Order.push_back(r);
	Preorder(Root, i, r, Order);
	Preorder(Root, r + 1, j, Order);
}

inline void Greedy(const std::vector<int>& Freq, int i, int j, std::vector<int>& Order)
{
	if (i >= j) return;
	int r = i;
	for (int k = i + 1; k < j; ++k)
		if (Freq[k] > Freq[r]) r = k;
	Order.push_back(r);
	Greedy(Freq, i, r, Order);
	Greedy(Freq, r + 1, j, Order);
}

} // namespace ledger_detail

// Flips for an insertion order (depth times frequency), or LedgerInvalid when it repeats or skips an entry.
inline int64_t LedgerFlips(const std::vector<int>& Freq, const std::vector<int>& Order)
{
	const int N = static_cast<int>(Freq.size());
	if (static_cast<int>(Order.size()) != N) return LedgerInvalid;
	std::vector<bool> Seen(N, false);
	std::vector<int> Left(N, -1), Right(N, -1);
	int64_t Total = 0;
	for (int k = 0; k < N; ++k)
	{
		const int c = Order[k];
		if (c < 0 || c >= N || Seen[c]) return LedgerInvalid;
		Seen[c] = true;
		int Depth = 1;
		if (k > 0)
			for (int v = Order[0];;)
			{
				++Depth;
				int& Child = c < v ? Left[v] : Right[v];
				if (Child < 0) { Child = c; break; }
				v = Child;
			}
		Total += static_cast<int64_t>(Depth) * Freq[c];
	}
	return Total;
}

// Optimal binary search tree, exactly (interval DP with Knuth's root bounds).
inline LedgerFiling LedgerBest(const std::vector<int>& Freq)
{
	const int N = static_cast<int>(Freq.size());
	std::vector<int64_t> Prefix(N + 1, 0);
	for (int i = 0; i < N; ++i) Prefix[i + 1] = Prefix[i] + Freq[i];
	std::vector<std::vector<int64_t>> Cost(N + 1, std::vector<int64_t>(N + 1, 0));
	std::vector<std::vector<int>> Root(N + 1, std::vector<int>(N + 1, 0));
	for (int i = 0; i < N; ++i) { Cost[i][i + 1] = Freq[i]; Root[i][i + 1] = i; }
	for (int Len = 2; Len <= N; ++Len)
		for (int i = 0; i + Len <= N; ++i)
		{
			const int j = i + Len;
			int64_t BestCost = std::numeric_limits<int64_t>::max();
			int BestRoot = -1;
			for (int r = Root[i][j - 1]; r <= Root[i + 1][j]; ++r)
				if (Cost[i][r] + Cost[r + 1][j] < BestCost) { BestCost = Cost[i][r] + Cost[r + 1][j]; BestRoot = r; }
			Cost[i][j] = BestCost + Prefix[j] - Prefix[i];
			Root[i][j] = BestRoot;
		}
	LedgerFiling F{ Cost[0][N], {} };
	ledger_detail::Preorder(Root, 0, N, F.Order);
	return F;
}

// Naive habit: the most-asked entry goes at the root of every range (lowest index on ties).
inline LedgerFiling LedgerMostAskedRoot(const std::vector<int>& Freq)
{
	LedgerFiling F;
	ledger_detail::Greedy(Freq, 0, static_cast<int>(Freq.size()), F.Order);
	F.Flips = LedgerFlips(Freq, F.Order);
	return F;
}

inline bool LedgerQuestDone(const std::vector<int>& Freq, const std::vector<int>& Order)
{
	const int64_t Got = LedgerFlips(Freq, Order);
	return Got != LedgerInvalid && Got == LedgerBest(Freq).Flips;
}

} } // namespace daedalus::stable
