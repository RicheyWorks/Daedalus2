// SPDX-License-Identifier: MIT
// G528 Shoeing Shed C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_shoeing_shed_core_test.cpp
//   ./a.out stable_shoeing_shed_parity.txt
#include "DaedalusStableShoeingShedCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_shoeing_shed_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const Shed S = ShedSeed(s, s % 9);
		const ShedQueue B = ShedBest(S), G = ShedSmith(S);
		Lines.push_back("seed=" + std::to_string(s) + " time=" + Join(S.Time) + " fret=" + Join(S.Fret) + " due=" + Join(S.Due)
			+ " best=" + std::to_string(B.Penalty) + ":" + Join(B.Order) + " smith=" + std::to_string(G.Penalty) + ":"
			+ Join(G.Order));
	}
	stable_test::CheckParity(Path, Lines);
	const Shed S = ShedSeed(7, 8);
	Check("best queue wins the quest", ShedQuest(S, ShedBest(S).Order));
	Check("Smith's rule never beats best", ShedSmith(S).Penalty >= ShedBest(S).Penalty);
	Check("repeated horse penalises -1", ShedPenalty(S, { 0, 0, 1, 2, 3, 4, 5, 6 }) == -1);
	Check("short order penalises -1", ShedPenalty(S, { 0 }) == -1);
	return stable_test::Finish();
}
