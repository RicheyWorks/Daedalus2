// SPDX-License-Identifier: MIT
// G539 Water Trough Fill C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_water_trough_fill_core_test.cpp
//   ./a.out stable_water_trough_fill_parity.txt
#include "DaedalusStableWaterTroughFillCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_water_trough_fill_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const TroughPipes P = TroughSeed(s, 2 + s % 8, 5);
		const int Demand = 1 + s % 6;
		const TroughPlan B = TroughBest(P, Demand), G = TroughCheapestPath(P, Demand);
		Lines.push_back("seed=" + std::to_string(s) + " nodes=" + std::to_string(P.Nodes) + " from=" + Join(P.From) + " to=" + Join(P.To)
			+ " cap=" + Join(P.Cap) + " cost=" + Join(P.Cost) + " demand=" + std::to_string(Demand) + " best=" + std::to_string(B.Cost) + ":"
			+ Join(B.Flow) + " cheapest=" + std::to_string(G.Cost) + ":" + Join(G.Flow));
	}
	stable_test::CheckParity(Path, Lines);
	const TroughPipes P = TroughSeed(7, 8, 5);
	const TroughPlan B = TroughBest(P, 3);
	Check("best plan wins the quest", B.Cost == TroughInfeasible || TroughQuestDone(P, 3, B.Flow));
	Check("cheapest path never beats best", TroughCheapestPath(P, 3).Cost == TroughInfeasible || TroughCheapestPath(P, 3).Cost >= B.Cost);
	Check("no flow misses the demand", TroughPump(P, 3, std::vector<int>(P.From.size(), 0)) == TroughInfeasible);
	Check("short flow is infeasible", TroughPump(P, 3, { 1 }) == TroughInfeasible);
	return stable_test::Finish();
}
