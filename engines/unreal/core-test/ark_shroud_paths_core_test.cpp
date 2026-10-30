// SPDX-License-Identifier: MIT
// G520 The Shroud Paths C++ port (G572), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_shroud_paths_core_test.cpp
//   ./a.out ark_shroud_paths_parity.txt
#include "DaedalusArkShroudPathsCore.h"
#include "DaedalusStableRandom.h"
#include "ark_trees_test.h"
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

// Brute force: walk both spars up to their meeting spar with plain parent links.
struct Naive
{
	std::vector<int> Parent, Depth;
	std::vector<int64_t> Strain;

	std::vector<int> Path(int A, int B) const
	{
		std::vector<int> Out;
		while (A != B)
		{
			if (Depth[A] < Depth[B]) std::swap(A, B);
			Out.push_back(A);
			A = Parent[A];
		}
		Out.push_back(A);
		return Out;
	}
};

std::vector<std::string> ParityLines()
{
	std::vector<std::string> Out;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(s);
		const int N = 1 + Rng.NextInt(12);
		std::vector<ShroudLine> Lines;
		std::string Held;
		for (int v = 1; v < N; ++v)
		{
			Lines.push_back({ Rng.NextInt(v), v });
			Held += (v > 1 ? "," : "") + S(Lines.back().A) + "-" + S(v);
		}
		std::vector<int64_t> Strain(N);
		for (int64_t& X : Strain) X = Rng.NextInt(41) - 20;
		ShroudPaths Board(N, Lines, Strain);
		std::string Q;
		for (int k = 0; k < 6; ++k)
		{
			if (k == 3)
			{
				const int V = Rng.NextInt(N);
				const int64_t Value = Rng.NextInt(41) - 20;
				Board.Set(V, Value);
				Q += " set=" + S(V) + ":" + S(Value);
			}
			const int A = Rng.NextInt(N), B = Rng.NextInt(N);
			Q += " q=" + S(A) + "-" + S(B) + ":" + S(Board.PathMax(A, B)) + "/" + S(Board.PathSum(A, B)) + "/"
				+ S(Board.Meet(A, B)) + "/" + S(Board.PathLength(A, B));
		}
		Out.push_back("seed=" + S(s) + " n=" + S(N) + " lines=" + (Held.empty() ? "-" : Held) + " strain="
			+ ark_test::Join(Strain) + Q);
	}
	return Out;
}

// Random trees with re-tensions, every answer against the naive walk.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(520);
	for (int Round = 0; Round < 40; ++Round)
	{
		const int N = 1 + Rng.NextInt(60);
		Naive T{ std::vector<int>(N, -1), std::vector<int>(N, 0), std::vector<int64_t>(N) };
		std::vector<ShroudLine> Lines;
		for (int v = 1; v < N; ++v)
		{
			const int P = Rng.NextInt(v);
			// Shuffle line ends so the build has to find the tree from spar 0 itself.
			Lines.push_back(Rng.NextBoolean() ? ShroudLine{ P, v } : ShroudLine{ v, P });
			T.Parent[v] = P;
			T.Depth[v] = T.Depth[P] + 1;
		}
		for (int64_t& X : T.Strain) X = Rng.NextInt(2001) - 1000;
		ShroudPaths Board(N, Lines, T.Strain);
		for (int k = 0; k < 80; ++k)
		{
			if (k % 7 == 0)
			{
				const int V = Rng.NextInt(N);
				T.Strain[V] = Rng.NextInt(2001) - 1000;
				Board.Set(V, T.Strain[V]);
			}
			const int A = Rng.NextInt(N), B = Rng.NextInt(N);
			const std::vector<int> P = T.Path(A, B);
			int64_t Max = T.Strain[P[0]], Sum = 0;
			for (int V : P) { Max = std::max(Max, T.Strain[V]); Sum += T.Strain[V]; }
			if (Board.PathMax(A, B) != Max || Board.PathSum(A, B) != Sum || Board.Meet(A, B) != P.back()
				|| Board.PathLength(A, B) != static_cast<int>(P.size()) || Board.Strain(A) != T.Strain[A])
				return false;
		}
	}
	return true;
}

// The longest allowed chain, end to end: deep paths stay iterative.
bool LongChain()
{
	const int N = ShroudMaxSpars;
	std::vector<ShroudLine> Lines;
	std::vector<int64_t> Strain(N);
	for (int v = 0; v < N; ++v) Strain[v] = v % 1000;
	for (int v = 1; v < N; ++v) Lines.push_back({ v - 1, v });
	ShroudPaths Board(N, Lines, Strain);
	Board.Set(N / 2, 5000);
	return Board.PathMax(0, N - 1) == 5000 && Board.PathLength(0, N - 1) == N && Board.Meet(N - 1, 7) == 7;
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_shroud_paths_parity.txt", ParityLines());
	Check("path max, sum, meet and length match a naive walk on random trees", MatchesBruteForce());
	Check("200,000-spar chain", LongChain());
	Check("a cycle is not a tree", !ShroudPaths(3, { { 0, 1 }, { 1, 0 } }, { 1, 2, 3 }).Valid());
	Check("a self line is refused", !ShroudPaths(2, { { 1, 1 } }, { 1, 2 }).Valid());
	Check("missing strains are refused", !ShroudPaths(2, { { 0, 1 } }, { 1 }).Valid());
	const ShroudPaths Board(3, { { 0, 1 }, { 1, 2 } }, { 4, -9, 7 });
	Check("heaviest strain wins the quest", ShroudQuest(Board, 0, 2, 7) && !ShroudQuest(Board, 0, 2, 4));
	Check("a spar off the board loses the quest", !ShroudQuest(Board, 0, 3, 7));
	return stable_test::Finish();
}
