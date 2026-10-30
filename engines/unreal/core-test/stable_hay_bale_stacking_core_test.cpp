// SPDX-License-Identifier: MIT
// G542 Hay Bale Stacking C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_hay_bale_stacking_core_test.cpp
//   ./a.out stable_hay_bale_stacking_parity.txt
#include "DaedalusStableHayBaleStackingCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_hay_bale_stacking_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const Bales S = BaleSeed(s, s % 10);
		const BaleStack B = BaleBest(S), G = BaleBiggestFirst(S);
		Lines.push_back("seed=" + std::to_string(s) + " a=" + Join(S.A) + " b=" + Join(S.B) + " height=" + Join(S.Height) + " weight="
			+ Join(S.Weight) + " strength=" + Join(S.Strength) + " best=" + std::to_string(B.Height) + ":" + Join(B.BottomUp) + " biggest="
			+ std::to_string(G.Height) + ":" + Join(G.BottomUp));
	}
	stable_test::CheckParity(Path, Lines);
	const Bales S = BaleSeed(7, 12);
	Check("best stack wins the quest", BaleQuestDone(S, BaleBest(S).BottomUp));
	Check("biggest first never beats best", BaleBiggestFirst(S).Height <= BaleBest(S).Height);
	Check("repeated bale is invalid", BaleStackHeight(S, { 0, 0 }) == BaleInvalid);
	Check("missing bale is invalid", BaleStackHeight(S, { 99 }) == BaleInvalid);
	return stable_test::Finish();
}
