// SPDX-License-Identifier: MIT
// G527 The Swell Crests C++ port (G572), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_swell_crests_core_test.cpp
//   ./a.out ark_swell_crests_parity.txt
#include "DaedalusArkSwellCrestsCore.h"
#include "DaedalusStableRandom.h"
#include "ark_trees_test.h"
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

std::vector<std::string> ParityLines()
{
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(s);
		const int N = 1 + Rng.NextInt(14);
		std::vector<int64_t> Heights(N);
		for (int64_t& H : Heights) H = Rng.NextInt(6);
		const SwellCrests Chart(Heights);
		std::vector<int64_t> Parents, Reigns, Ruled;
		for (int i = 0; i < N; ++i)
		{
			Parents.push_back(Chart.ParentOf(i));
			Reigns.push_back(Chart.ReignFrom(i) * int64_t{ 100 } + Chart.ReignTo(i));
			Ruled.push_back(Chart.WindowsRuled(i));
		}
		std::string Q;
		for (int k = 0; k < 5; ++k)
		{
			const int A = Rng.NextInt(N);
			const int B = A + Rng.NextInt(N - A);
			Q += " crest=" + S(A) + "-" + S(B) + ":" + S(Chart.Crest(A, B));
		}
		Lines.push_back("seed=" + S(s) + " heights=" + ark_test::Join(Heights) + " root=" + S(Chart.RootWave())
			+ " parents=" + ark_test::Join(Parents) + " reigns=" + ark_test::Join(Reigns) + " ruled="
			+ ark_test::Join(Ruled) + Q);
	}
	return Lines;
}

// Every window of random logs against a linear scan; windows ruled must count each window exactly once.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(527);
	for (int Round = 0; Round < 60; ++Round)
	{
		const int N = 1 + Rng.NextInt(40);
		std::vector<int64_t> H(N);
		for (int64_t& X : H) X = Rng.NextInt(1 + Round % 9);
		const SwellCrests Chart(H);
		std::vector<int64_t> Ruled(N, 0);
		for (int a = 0; a < N; ++a)
		{
			int Best = a;
			for (int b = a; b < N; ++b)
			{
				if (H[b] > H[Best]) Best = b;
				if (Chart.Crest(a, b) != Best) return false;
				++Ruled[Best];
			}
		}
		for (int i = 0; i < N; ++i)
		{
			const bool Window = Chart.ReignFrom(i) <= i && i <= Chart.ReignTo(i);
			if (!Window || Chart.WindowsRuled(i) != Ruled[i]) return false;
		}
	}
	return true;
}

// The longest allowed falling log is one deep left spine.
bool LongLog()
{
	std::vector<int64_t> H(SwellMaxWaves);
	for (int i = 0; i < SwellMaxWaves; ++i) H[i] = SwellMaxWaves - i;
	const SwellCrests Chart(H);
	const int Last = SwellMaxWaves - 1;
	return Chart.RootWave() == 0 && Chart.Crest(Last - 1, Last) == Last - 1 && Chart.Crest(0, Last) == 0
		&& Chart.WindowsRuled(0) == SwellMaxWaves;
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_swell_crests_parity.txt", ParityLines());
	Check("window crests and windows ruled match a linear scan", MatchesBruteForce());
	Check("300,000-wave falling log", LongLog());
	Check("no waves is no chart", !SwellCrests({}).Valid());
	const SwellCrests Chart({ 3, 5, 5, 1 });
	Check("leftmost tallest is the root", Chart.RootWave() == 1 && Chart.ParentOf(2) == 1);
	Check("quest names the window crest", SwellQuest(Chart, 2, 3) == 2 && SwellQuest(Chart, 0, 3) == 1);
	Check("a window off the chart has no crest", SwellQuest(Chart, 2, 4) == -1 && SwellQuest(Chart, 3, 2) == -1);
	return stable_test::Finish();
}
