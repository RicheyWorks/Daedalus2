// SPDX-License-Identifier: MIT
// G523 Paddock Rotation C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_paddock_rotation_core_test.cpp
//   ./a.out stable_paddock_rotation_parity.txt
#include "DaedalusStablePaddockRotationCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_paddock_rotation_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const Pasture P = PaddockSeed(s, 1 + s % 4);
		const int Days = s % 9;
		const GrazingSeason B = PaddockBest(P, Days), G = PaddockGreedy(P, Days);
		Lines.push_back("seed=" + std::to_string(s) + " days=" + std::to_string(Days) + " cap=" + Join(P.Cap) + " growth="
			+ Join(P.Growth) + " best=" + std::to_string(B.Grass) + ":" + Join(B.Plan) + " greedy=" + std::to_string(G.Grass)
			+ ":" + Join(G.Plan));
	}
	stable_test::CheckParity(Path, Lines);
	const Pasture P{ { 8, 3 }, { 2, 3 } };
	Check("best season wins the quest", PaddockQuestDone(P, PaddockBest(P, 5).Plan, 5));
	Check("wrong length grazes -1", PaddockGraze(P, { 0 }, 5) == -1);
	Check("missing paddock grazes -1", PaddockGraze(P, { 0, 2 }, 2) == -1);
	Check("greedy never beats best", PaddockGreedy(P, 7).Grass <= PaddockBest(P, 7).Grass);
	return stable_test::Finish();
}
