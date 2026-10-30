// SPDX-License-Identifier: MIT
// G547 Stall Plaques C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_stall_plaques_core_test.cpp
//   ./a.out stable_stall_plaques_parity.txt
#include "DaedalusStableStallPlaquesCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_stall_plaques_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const std::vector<int> L = PlaqueNames(s, s % 15, 1, 6);
		const PlaqueLayout B = PlaqueBest(L, 12), G = PlaqueFillEachLine(L, 12);
		Lines.push_back("seed=" + std::to_string(s) + " len=" + Join(L) + " best=" + std::to_string(B.Ugliness) + ":" + Join(B.Breaks)
			+ " fill=" + std::to_string(G.Ugliness) + ":" + Join(G.Breaks));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> L = PlaqueNames(7, 14, 1, 6);
	Check("best layout wins the quest", PlaqueQuestDone(L, 12, PlaqueBest(L, 12).Breaks));
	Check("filling each line never beats best", PlaqueFillEachLine(L, 12).Ugliness >= PlaqueBest(L, 12).Ugliness);
	Check("empty line is invalid", PlaqueUgliness(L, 12, { 2, 2 }) == PlaqueInvalid);
	Check("one line for everything overflows", PlaqueUgliness(L, 12, {}) == PlaqueInvalid);
	return stable_test::Finish();
}
