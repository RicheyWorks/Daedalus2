// SPDX-License-Identifier: MIT
// G520 The Shroud Paths (art-master-flex), plain C++17, header-only, no Unreal types (G572 port).
// Heavy-light decomposition of the ark's rigging tree: heaviest and total strain on the path between two spars,
// single-spar re-tensions, and where two paths meet. Must agree with com.daedalus.world.ark.ShroudPaths line for
// line (ark_shroud_paths_parity.txt, checked by ArkTreesParityTest.java and ark_shroud_paths_core_test.cpp).
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* ShroudPathsQuest = "q_shroud_paths";
constexpr int ShroudMaxSpars = 200000;

struct ShroudLine { int A, B; };

// The rigger's tally board. Build with spars 0..N-1, N-1 lines forming a tree, and one strain per spar; Valid()
// is false (and every query is off) when the lines are not such a tree. Spar arguments must satisfy Has().
class ShroudPaths
{
public:
	ShroudPaths(int N, const std::vector<ShroudLine>& Lines, const std::vector<int64_t>& Strain)
	{
		if (N < 1 || N > ShroudMaxSpars || static_cast<int>(Lines.size()) != N - 1
			|| static_cast<int>(Strain.size()) != N) return;
		std::vector<int> Start(N + 1, 0);
		for (const ShroudLine& L : Lines)
		{
			if (L.A < 0 || L.B < 0 || L.A >= N || L.B >= N || L.A == L.B) return;
			++Start[L.A + 1];
			++Start[L.B + 1];
		}
		for (int i = 0; i < N; ++i) Start[i + 1] += Start[i];
		std::vector<int> Adj(Start.back()), Fill(Start.begin(), Start.end() - 1);
		for (const ShroudLine& L : Lines)
		{
			Adj[Fill[L.A]++] = L.B;
			Adj[Fill[L.B]++] = L.A;
		}

		// Breadth-first from spar 0 in adjacency order, exactly as the Java walk.
		Parent.assign(N, Unseen);
		Depth.assign(N, 0);
		Parent[0] = -1;
		std::vector<int> Order(N, 0);
		int Seen = 1;
		for (int i = 0; i < Seen; ++i)
		{
			const int V = Order[i];
			for (int k = Start[V]; k < Start[V + 1]; ++k)
			{
				const int W = Adj[k];
				if (Parent[W] != Unseen) continue;
				Parent[W] = V;
				Depth[W] = Depth[V] + 1;
				Order[Seen++] = W;
			}
		}
		if (Seen != N) return;

		// Heavy child = the first child with the largest subtree.
		std::vector<int> Sub(N, 0), Heavy(N, -1);
		for (int i = N - 1; i >= 0; --i)
		{
			const int V = Order[i], P = Parent[V];
			++Sub[V];
			if (P < 0) continue;
			Sub[P] += Sub[V];
			if (Heavy[P] < 0 || Sub[V] > Sub[Heavy[P]]) Heavy[P] = V;
		}
		Head.assign(N, 0);
		Pos.assign(N, 0);
		int Next = 0;
		for (int V : Order)
		{
			if (Parent[V] >= 0 && Heavy[Parent[V]] == V) continue;
			for (int U = V; U >= 0; U = Heavy[U])
			{
				Head[U] = V;
				Pos[U] = Next++;
			}
		}

		Size = 1;
		while (Size < N) Size <<= 1;
		Max.assign(2 * static_cast<size_t>(Size), Lowest);
		Sum.assign(2 * static_cast<size_t>(Size), 0);
		for (int V = 0; V < N; ++V) Max[Size + Pos[V]] = Sum[Size + Pos[V]] = Strain[V];
		for (int i = Size - 1; i >= 1; --i) Pull(i);
		Spars = N;
	}

	bool Valid() const { return Spars > 0; }
	int SparCount() const { return Spars; }
	bool Has(int V) const { return V >= 0 && V < Spars; }

	int64_t Strain(int V) const { return Sum[Size + Pos[V]]; }

	// Re-tensions spar V.
	void Set(int V, int64_t Value)
	{
		int i = Size + Pos[V];
		Max[i] = Sum[i] = Value;
		for (i >>= 1; i >= 1; i >>= 1) Pull(i);
	}

	int64_t PathMax(int A, int B) const { return Walk(A, B).Max; }
	int64_t PathSum(int A, int B) const { return Walk(A, B).Sum; }
	// The spar where the paths from A and B up to spar 0 meet.
	int Meet(int A, int B) const { return Walk(A, B).Meet; }
	// Spars on the path between A and B, both ends included.
	int PathLength(int A, int B) const { return Depth[A] + Depth[B] - 2 * Depth[Meet(A, B)] + 1; }

private:
	static constexpr int Unseen = -2;
	static constexpr int64_t Lowest = std::numeric_limits<int64_t>::min();

	struct Tally { int64_t Max = Lowest, Sum = 0; int Meet = -1; };

	int Spars = 0, Size = 0;
	std::vector<int> Parent, Depth, Head, Pos;
	std::vector<int64_t> Max, Sum;

	void Pull(int i)
	{
		Max[i] = std::max(Max[2 * i], Max[2 * i + 1]);
		Sum[i] = Sum[2 * i] + Sum[2 * i + 1];
	}

	// Folds chain positions Lo..Hi (inclusive) into T.
	void Range(int Lo, int Hi, Tally& T) const
	{
		for (int L = Lo + Size, R = Hi + Size + 1; L < R; L >>= 1, R >>= 1)
		{
			if (L & 1) { T.Max = std::max(T.Max, Max[L]); T.Sum += Sum[L++]; }
			if (R & 1) { T.Max = std::max(T.Max, Max[--R]); T.Sum += Sum[R]; }
		}
	}

	Tally Walk(int A, int B) const
	{
		Tally T;
		int U = A, V = B;
		while (Head[U] != Head[V])
		{
			if (Depth[Head[U]] < Depth[Head[V]]) std::swap(U, V);
			Range(Pos[Head[U]], Pos[U], T);
			U = Parent[Head[U]];
		}
		Range(std::min(Pos[U], Pos[V]), std::max(Pos[U], Pos[V]), T);
		T.Meet = Depth[U] < Depth[V] ? U : V;
		return T;
	}
};

// Quest q_shroud_paths: the player's answer must be the heaviest strain between spars A and B.
inline bool ShroudQuest(const ShroudPaths& Board, int A, int B, int64_t Answer)
{
	return Board.Valid() && Board.Has(A) && Board.Has(B) && Board.PathMax(A, B) == Answer;
}

} } // namespace daedalus::ark
