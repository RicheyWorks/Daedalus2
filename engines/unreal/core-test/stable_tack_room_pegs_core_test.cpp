// SPDX-License-Identifier: MIT
// G530 Tack Room Pegs C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_tack_room_pegs_core_test.cpp
//   ./a.out stable_tack_room_pegs_parity.txt
#include "DaedalusStableTackRoomPegsCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_tack_room_pegs_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const std::vector<int> W = TackWeights(s, s % 11, 10), F = TackFeuds(s, s % 11, 25);
		const TackRoom B = TackBest(W, F, 10), G = TackFirstFit(W, F, 10);
		Lines.push_back("seed=" + std::to_string(s) + " weight=" + Join(W) + " feud=" + Join(F) + " best=" + std::to_string(B.Pegs) + ":"
			+ Join(B.PegOf) + " firstfit=" + std::to_string(G.Pegs) + ":" + Join(G.PegOf));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> W = TackWeights(7, 10, 10), F = TackFeuds(7, 10, 25);
	Check("best hanging wins the quest", TackQuest(W, F, 10, TackBest(W, F, 10).PegOf));
	Check("first fit never beats best", TackFirstFit(W, F, 10).Pegs >= TackBest(W, F, 10).Pegs);
	Check("short hanging is illegal", TackHang(W, F, 10, { 0 }) == -1);
	Check("one peg for everything overloads", TackHang(W, F, 10, std::vector<int>(10, 0)) == -1);
	return stable_test::Finish();
}
