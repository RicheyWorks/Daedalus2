// SPDX-License-Identifier: MIT
// G527 The Swell Crests (art-master-flex), plain C++17, header-only, no Unreal types (G572 port).
// Cartesian tree of the wave heights in the ark's wake (tallest at the root, leftmost on ties), built in O(n) with a
// stack; each crest's reign window, how many windows it rules, and the crest of any window by binary-lifting LCA.
// Must agree with com.daedalus.world.ark.SwellCrests line for line (ark_swell_crests_parity.txt, checked by
// ArkTreesParityTest.java and ark_swell_crests_core_test.cpp).
#pragma once
#include <cstdint>
#include <utility>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* SwellCrestsQuest = "q_swell_crests";
constexpr int SwellMaxWaves = 300000;

// The lookout's swell chart. Valid() is false for no waves or more than SwellMaxWaves; wave arguments must
// satisfy Has(), and windows A <= B.
class SwellCrests
{
public:
	explicit SwellCrests(const std::vector<int64_t>& Heights)
	{
		const int N = static_cast<int>(Heights.size());
		if (N < 1 || N > SwellMaxWaves) return;
		Parent.assign(N, -1);
		Left.assign(N, -1);
		Right.assign(N, -1);
		std::vector<int> Stack;
		Stack.reserve(N);
		for (int i = 0; i < N; ++i)
		{
			int Last = -1;
			while (!Stack.empty() && Heights[Stack.back()] < Heights[i])
			{
				Last = Stack.back();
				Stack.pop_back();
			}
			Left[i] = Last;
			if (!Stack.empty()) Right[Stack.back()] = i;
			Stack.push_back(i);
		}
		Root = Stack.front();
		for (int i = 0; i < N; ++i)
		{
			if (Left[i] >= 0) Parent[Left[i]] = i;
			if (Right[i] >= 0) Parent[Right[i]] = i;
		}

		From.assign(N, 0);
		To.assign(N, N - 1);
		Depth.assign(N, 0);
		std::vector<int> Order{ Root };
		Order.reserve(N);
		for (size_t h = 0; h < Order.size(); ++h)
		{
			const int V = Order[h];
			if (const int C = Left[V]; C >= 0)
			{
				From[C] = From[V];
				To[C] = V - 1;
				Depth[C] = Depth[V] + 1;
				Order.push_back(C);
			}
			if (const int C = Right[V]; C >= 0)
			{
				From[C] = V + 1;
				To[C] = To[V];
				Depth[C] = Depth[V] + 1;
				Order.push_back(C);
			}
		}

		int Levels = 1;
		while ((1 << Levels) < N) ++Levels;
		Up.assign(Levels + 1, std::vector<int>(N));
		for (int i = 0; i < N; ++i) Up[0][i] = Parent[i] < 0 ? i : Parent[i];
		for (int k = 1; k <= Levels; ++k)
			for (int i = 0; i < N; ++i) Up[k][i] = Up[k - 1][Up[k - 1][i]];
		Waves = N;
	}

	bool Valid() const { return Waves > 0; }
	int Size() const { return Waves; }
	bool Has(int i) const { return i >= 0 && i < Waves; }

	// The tallest wave (leftmost on ties), the tree root.
	int RootWave() const { return Root; }
	int ParentOf(int i) const { return Parent[i]; }
	int LeftChild(int i) const { return Left[i]; }
	int RightChild(int i) const { return Right[i]; }
	// Widest window [ReignFrom, ReignTo] where wave i is the leftmost tallest.
	int ReignFrom(int i) const { return From[i]; }
	int ReignTo(int i) const { return To[i]; }
	// Number of windows [a, b] whose leftmost tallest wave is i.
	int64_t WindowsRuled(int i) const { return static_cast<int64_t>(i - From[i] + 1) * (To[i] - i + 1); }

	// Leftmost tallest wave in window [A, B]: the lowest common ancestor of A and B.
	int Crest(int A, int B) const
	{
		int X = A, Y = B;
		if (Depth[X] < Depth[Y]) std::swap(X, Y);
		for (int k = 0, d = Depth[X] - Depth[Y]; d > 0; ++k, d >>= 1)
			if (d & 1) X = Up[k][X];
		if (X == Y) return X;
		for (int k = static_cast<int>(Up.size()) - 1; k >= 0; --k)
		{
			if (Up[k][X] != Up[k][Y]) { X = Up[k][X]; Y = Up[k][Y]; }
		}
		return Parent[X];
	}

private:
	int Waves = 0, Root = -1;
	std::vector<int> Parent, Left, Right, From, To, Depth;
	std::vector<std::vector<int>> Up;
};

// Quest q_swell_crests: which wave crests highest in window [A, B]; -1 for a window off the chart.
inline int SwellQuest(const SwellCrests& Chart, int A, int B)
{
	return Chart.Valid() && Chart.Has(A) && Chart.Has(B) && A <= B ? Chart.Crest(A, B) : -1;
}

} } // namespace daedalus::ark
