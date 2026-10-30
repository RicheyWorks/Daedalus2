// SPDX-License-Identifier: MIT
// G516 Feed Loft C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_feed_loft_core_test.cpp
//   ./a.out stable_feed_loft_parity.txt
#include "DaedalusStableFeedLoftCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_feed_loft_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const std::vector<Bale> Bales = LoftDelivery(s, s % 9, 6);
		const int W = s % 15, K = (s * 7) % 15;
		std::string Held;
		for (const Bale& B : Bales)
			Held += (Held.empty() ? "" : ",") + std::to_string(B.Weight) + "/" + std::to_string(B.Bulk) + "/" + std::to_string(B.Nourishment);
		const LoftLoad Best = LoftBest(Bales, W, K), Greedy = LoftGreedy(Bales, W, K);
		Lines.push_back("seed=" + std::to_string(s) + " weight=" + std::to_string(W) + " bulk=" + std::to_string(K)
			+ " bales=" + (Held.empty() ? "-" : Held) + " best=" + std::to_string(Best.Nourishment) + ":" + Join(Best.Bales)
			+ " greedy=" + std::to_string(Greedy.Nourishment) + ":" + Join(Greedy.Bales));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<Bale> Bales = { { 2, 5, 9 }, { 3, 1, 6 }, { 3, 1, 6 } };
	Check("best load wins the quest", LoftQuest(Bales, LoftBest(Bales, 6, 4).Bales, 6, 4));
	Check("repeated bale stacks -1", LoftStack(Bales, { 1, 1 }, 6, 4) == -1);
	Check("over the bulk limit stacks -1", LoftStack(Bales, { 0 }, 6, 4) == -1);
	Check("missing bale stacks -1", LoftStack(Bales, { 3 }, 6, 4) == -1);
	return stable_test::Finish();
}
