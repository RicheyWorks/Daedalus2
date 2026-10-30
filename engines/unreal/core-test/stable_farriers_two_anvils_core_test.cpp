// SPDX-License-Identifier: MIT
// G535 Farrier's Two Anvils C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_farriers_two_anvils_core_test.cpp
//   ./a.out stable_farriers_two_anvils_parity.txt
#include "DaedalusStableFarriersTwoAnvilsCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_farriers_two_anvils_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const std::vector<int> T = AnvilDurations(s, s % 9), P = AnvilLinks(s, s % 9, 30);
		const AnvilPlan B = AnvilBest(T, P), G = AnvilListSchedule(T, P);
		Lines.push_back("seed=" + std::to_string(s) + " time=" + Join(T) + " pred=" + Join(P) + " best=" + std::to_string(B.Makespan) + ":"
			+ Join(B.Start) + ":" + Join(B.Anvil) + " list=" + std::to_string(G.Makespan) + ":" + Join(G.Start) + ":" + Join(G.Anvil));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> T = AnvilDurations(7, 8), P = AnvilLinks(7, 8, 30);
	const AnvilPlan B = AnvilBest(T, P);
	Check("best schedule wins the quest", AnvilQuest(T, P, B.Start, B.Anvil));
	Check("list schedule never beats best", AnvilListSchedule(T, P).Makespan >= B.Makespan);
	Check("everything at once on one anvil is invalid", AnvilFinish(T, P, std::vector<int>(8, 0), std::vector<int>(8, 0)) == AnvilInvalid);
	Check("third anvil is invalid", AnvilFinish(T, P, B.Start, std::vector<int>(8, 2)) == AnvilInvalid);
	return stable_test::Finish();
}
