// SPDX-License-Identifier: MIT
// G548 Barn Upgrades C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_barn_upgrades_core_test.cpp
//   ./a.out stable_barn_upgrades_parity.txt
#include "DaedalusStableBarnUpgradesCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_barn_upgrades_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const int N = s % 13;
		const std::vector<int> V = BarnValues(s, N, N / 2, 9, 9), Need = BarnNeeds(s, N, N / 2, 40);
		const BarnBuild B = BarnBest(V, Need), G = BarnOneAtATime(V, Need);
		Lines.push_back("seed=" + std::to_string(s) + " value=" + Join(V) + " need=" + Join(Need) + " best=" + std::to_string(B.Coin) + ":"
			+ std::to_string(B.Chosen) + " oneatatime=" + std::to_string(G.Coin) + ":" + std::to_string(G.Chosen));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> V = BarnValues(7, 12, 6, 9, 9), Need = BarnNeeds(7, 12, 6, 40);
	Check("best build wins the quest", BarnQuestDone(V, Need, BarnBest(V, Need).Chosen));
	Check("one at a time never beats best", BarnOneAtATime(V, Need).Coin <= BarnBest(V, Need).Coin);
	Check("closure is closed", BarnClosed(Need, BarnClosure(Need, 1 << 11)));
	Check("out-of-range upgrade fails the quest", !BarnQuestDone(V, Need, 1 << 12));
	return stable_test::Finish();
}
