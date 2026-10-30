// SPDX-License-Identifier: MIT
// G569 The Tow Lines C++ port (G584), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_tow_lines_core_test.cpp
//   ./a.out ark_tow_lines_parity.txt
#include "DaedalusArkTowLinesCore.h"
#include "DaedalusStableRandom.h"
#include "ark_trees_test.h"
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

// Brute force: an edge set with a breadth-first walk for every question.
struct Naive
{
	std::vector<std::vector<int>> Adj;
	std::vector<int64_t> Load;

	// Skiffs on the path from A to B, or empty when not joined.
	std::vector<int> Path(int A, int B) const
	{
		std::vector<int> From(Adj.size(), -2), Queue{ A };
		From[A] = -1;
		for (size_t i = 0; i < Queue.size(); ++i)
			for (int W : Adj[Queue[i]])
				if (From[W] == -2) { From[W] = Queue[i]; Queue.push_back(W); }
		std::vector<int> Out;
		if (From[B] == -2) return Out;
		for (int V = B; V != -1; V = From[V]) Out.push_back(V);
		return Out;
	}

	void Drop(int A, int B)
	{
		Adj[A].erase(std::find(Adj[A].begin(), Adj[A].end(), B));
		Adj[B].erase(std::find(Adj[B].begin(), Adj[B].end(), A));
	}
};

std::vector<std::string> ParityLines()
{
	std::vector<std::string> Out;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(s);
		const int N = 1 + Rng.NextInt(10);
		std::vector<int64_t> Loads(N);
		for (int64_t& X : Loads) X = Rng.NextInt(41) - 20;
		TowLines Board(Loads);
		std::vector<TowLine> Tied;
		std::string Ops;
		for (int k = 0; k < 14; ++k)
		{
			const int Kind = Rng.NextInt(4);
			if (Kind == 1 && !Tied.empty())
			{
				const int Pick = Rng.NextInt(static_cast<int>(Tied.size()));
				const TowLine L = Tied[Pick];
				Tied.erase(Tied.begin() + Pick);
				const bool Flipped = Rng.NextBoolean();
				const int A = Flipped ? L.B : L.A, B = Flipped ? L.A : L.B;
				Ops += " cut=" + S(A) + "-" + S(B) + ":" + (Board.Cut(A, B) ? "1" : "0");
			}
			else if (Kind == 2)
			{
				const int V = Rng.NextInt(N);
				const int64_t Value = Rng.NextInt(41) - 20;
				Board.SetLoad(V, Value);
				Ops += " load=" + S(V) + ":" + S(Value);
			}
			else
			{
				const int A = Rng.NextInt(N), B = Rng.NextInt(N);
				if (Kind == 3)
				{
					Ops += " q=" + S(A) + "-" + S(B) + ":"
						+ (Board.Joined(A, B) ? S(Board.PathMax(A, B)) + "/" + S(Board.PathSum(A, B)) : "-");
				}
				else
				{
					const bool TiedNow = Board.Link(A, B);
					if (TiedNow) Tied.push_back({ A, B });
					Ops += " link=" + S(A) + "-" + S(B) + ":" + (TiedNow ? "1" : "0");
				}
			}
		}
		Out.push_back("seed=" + S(s) + " n=" + S(N) + " loads=" + ark_test::Join(Loads) + Ops);
	}
	return Out;
}

// Random ties, cuts (real and bogus), load changes and questions, every answer against the naive walk.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(569);
	for (int Round = 0; Round < 40; ++Round)
	{
		const int N = 1 + Rng.NextInt(40);
		Naive T{ std::vector<std::vector<int>>(N), std::vector<int64_t>(N) };
		for (int64_t& X : T.Load) X = Rng.NextInt(2001) - 1000;
		TowLines Board(T.Load);
		for (int k = 0; k < 300; ++k)
		{
			const int Kind = Rng.NextInt(5), A = Rng.NextInt(N), B = Rng.NextInt(N);
			const std::vector<int> P = T.Path(A, B);
			const bool Line = std::find(T.Adj[A].begin(), T.Adj[A].end(), B) != T.Adj[A].end();
			if (Kind <= 1)
			{
				if (Board.Link(A, B) != P.empty()) return false;
				if (P.empty()) { T.Adj[A].push_back(B); T.Adj[B].push_back(A); }
			}
			else if (Kind == 2)
			{
				if (Board.Cut(A, B) != Line) return false;
				if (Line) T.Drop(A, B);
			}
			else if (Kind == 3)
			{
				T.Load[A] = Rng.NextInt(2001) - 1000;
				Board.SetLoad(A, T.Load[A]);
			}
			else
			{
				if (Board.Joined(A, B) == P.empty()) return false;
				int64_t Max = TowUnjoined, Sum = 0;
				for (int V : P) { Max = std::max(Max, T.Load[V]); Sum += T.Load[V]; }
				if (Board.PathMax(A, B) != Max || Board.PathSum(A, B) != Sum || Board.Load(A) != T.Load[A])
					return false;
			}
		}
	}
	return true;
}

// The largest allowed chain, tied end to end in a shuffled order: deep paths stay iterative.
bool LongChain()
{
	const int N = TowMaxSkiffs;
	std::vector<int64_t> Loads(N);
	for (int v = 0; v < N; ++v) Loads[v] = v % 1000;
	TowLines Board(Loads);
	bool OK = true;
	for (int v = 1; v < N; v += 2) OK &= Board.Link(v - 1, v);
	for (int v = 2; v < N; v += 2) OK &= Board.Link(v - 1, v);
	Board.SetLoad(N / 2, 5000);
	OK &= Board.PathMax(0, N - 1) == 5000 && Board.PathSum(N - 1, N - 1) == Loads[N - 1];
	OK &= Board.Cut(N / 2, N / 2 + 1) && !Board.Joined(0, N - 1) && Board.PathMax(N - 1, N / 2 + 1) == 999;
	return OK;
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_tow_lines_parity.txt", ParityLines());
	Check("link, cut, joined and path max/sum match a naive walk on random forests", MatchesBruteForce());
	Check("300,000-skiff chain", LongChain());
	Check("an empty fleet is refused", !TowLines({}).Valid());
	TowLines Board({ 4, -9, 7 });
	Check("off-board skiffs are refused", !Board.Link(0, 3) && !Board.Cut(-1, 0) && !Board.Joined(0, 5)
		&& Board.PathMax(0, 3) == TowUnjoined);
	Check("a loop is refused", Board.Link(0, 1) && Board.Link(1, 2) && !Board.Link(2, 0) && !Board.Cut(0, 2));
	Check("heaviest load wins the quest", TowQuest({ 4, -9, 7 }, { { 0, 1 }, { 1, 2 }, { 2, 0 } }, 0, 2) == 7
		&& TowQuest({ 4, -9, 7 }, { { 0, 1 } }, 0, 2) == -1);
	return stable_test::Finish();
}
