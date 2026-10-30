// SPDX-License-Identifier: MIT
// G540 Lantern Posts C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_lantern_posts_core_test.cpp
//   ./a.out stable_lantern_posts_parity.txt
#include "DaedalusStableLanternPostsCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_lantern_posts_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const int N = 1 + s % 12, Reach = s % 4;
		const std::vector<int> Parent = LanternYard(s, N), Price = LanternPrices(s, N, 9);
		const LanternPlan B = LanternBest(Parent, Price, Reach), G = LanternBusiestFirst(Parent, Price, Reach);
		Lines.push_back("seed=" + std::to_string(s) + " parent=" + Join(Parent) + " price=" + Join(Price) + " reach=" + std::to_string(Reach)
			+ " best=" + std::to_string(B.Cost) + ":" + Join(B.Lighter) + " busiest=" + std::to_string(G.Cost) + ":" + Join(G.Lighter));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> Parent = LanternYard(7, 12), Price = LanternPrices(7, 12, 9);
	const LanternPlan B = LanternBest(Parent, Price, 2);
	Check("best plan wins the quest", LanternQuestDone(Parent, Price, 2, B.Lighter));
	Check("busiest first never beats best", LanternBusiestFirst(Parent, Price, 2).Cost >= B.Cost);
	Check("lighting from a stranger is infeasible", LanternLight(Parent, Price, 2, std::vector<int>(12, 11)) == LanternInfeasible);
	Check("short plan is infeasible", LanternLight(Parent, Price, 2, { -1 }) == LanternInfeasible);
	return stable_test::Finish();
}
