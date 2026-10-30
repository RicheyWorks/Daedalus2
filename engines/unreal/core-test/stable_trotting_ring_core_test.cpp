// SPDX-License-Identifier: MIT
// G506 Trotting Ring C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_trotting_ring_core_test.cpp
//   ./a.out stable_trotting_ring_parity.txt
#include "DaedalusStableTrottingRingCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_trotting_ring_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const int Stamina = s % 5;
		const std::vector<int> Calls = RingCalls(s, s % 13);
		const RingRound B = RingBest(Calls, Stamina), E = RingEager(Calls, Stamina);
		Lines.push_back("seed=" + std::to_string(s) + " stamina=" + std::to_string(Stamina) + " calls=" + Join(Calls)
			+ " best=" + std::to_string(B.Score) + ":" + Join(B.Gaits) + " eager=" + std::to_string(E.Score) + ":"
			+ Join(E.Gaits) + " rescore=" + std::to_string(RingScore(Calls, E.Gaits, Stamina)));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> Calls = { Canter, Canter, Canter };
	Check("best round wins the quest", RingQuest(Calls, RingBest(Calls, 2).Gaits, 2));
	Check("out of stamina scores -1", RingScore(Calls, { Canter, Canter, Canter }, 2) == -1);
	Check("unknown gait scores -1", RingScore(Calls, { Walk, 3, Walk }, 2) == -1);
	Check("wrong length scores -1", RingScore(Calls, { Walk }, 2) == -1);
	return stable_test::Finish();
}
