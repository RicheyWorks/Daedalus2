// SPDX-License-Identifier: MIT
// G532 Hay Wagon Round C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_hay_wagon_round_core_test.cpp
//   ./a.out stable_hay_wagon_round_parity.txt
#include "DaedalusStableHayWagonRoundCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_hay_wagon_round_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const Yard Y = WagonYard(s, s % 9, 10, 6);
		const WagonRound B = WagonBest(Y), G = WagonNearest(Y);
		Lines.push_back("seed=" + std::to_string(s) + " x=" + Join(Y.X) + " y=" + Join(Y.Y) + " open=" + Join(Y.Open) + " close="
			+ Join(Y.Close) + " best=" + std::to_string(B.Finish) + ":" + Join(B.Order) + " nearest=" + std::to_string(G.Finish) + ":"
			+ Join(G.Order));
	}
	stable_test::CheckParity(Path, Lines);
	const Yard Y = WagonYard(7, 8, 10, 6);
	Check("best round wins the quest", WagonQuest(Y, WagonBest(Y).Order));
	Check("nearest never beats best", WagonNearest(Y).Finish == WagonInfeasible || WagonNearest(Y).Finish >= WagonBest(Y).Finish);
	Check("repeated stall is infeasible", WagonDrive(Y, { 1, 1, 2, 3, 4, 5, 6, 7 }) == WagonInfeasible);
	Check("short round is infeasible", WagonDrive(Y, { 1 }) == WagonInfeasible);
	return stable_test::Finish();
}
