// SPDX-License-Identifier: MIT
// G537 Bridle Rack Matching C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_bridle_rack_matching_core_test.cpp
//   ./a.out stable_bridle_rack_matching_parity.txt
#include "DaedalusStableBridleRackMatchingCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_bridle_rack_matching_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const BridleStable S = BridleSeed(s, s % 9);
		std::string Rows;
		for (const auto& Row : S.Time) Rows += (Rows.empty() ? "" : "/") + Join(Row);
		const BridlePairing B = BridleBest(S), G = BridleCheapestFirst(S);
		Lines.push_back("seed=" + std::to_string(s) + " temper=" + Join(S.Temper) + " skill=" + Join(S.Skill) + " time="
			+ (Rows.empty() ? "-" : Rows) + " best=" + std::to_string(B.Ready) + ":" + Join(B.GroomOf) + " cheapest="
			+ std::to_string(G.Ready) + ":" + Join(G.GroomOf));
	}
	stable_test::CheckParity(Path, Lines);
	const BridleStable S = BridleSeed(7, 8);
	Check("best pairing wins the quest", BridleQuestDone(S, BridleBest(S).GroomOf));
	Check("cheapest first never beats best", BridleCheapestFirst(S).Ready == BridleInfeasible || BridleCheapestFirst(S).Ready >= BridleBest(S).Ready);
	Check("reused groom is infeasible", BridleReady(S, std::vector<int>(8, 0)) == BridleInfeasible);
	Check("short pairing is infeasible", BridleReady(S, { 0 }) == BridleInfeasible);
	return stable_test::Finish();
}
