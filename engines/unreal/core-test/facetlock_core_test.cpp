// SPDX-License-Identifier: MIT
// Facetlock Lattice parity: DaedalusFacetlockCore.h regenerates every scramble in facetlock_parity.txt from seed +
// difficulty alone and replays every demo move byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public facetlock_core_test.cpp -o facetlock_core_test && ./facetlock_core_test facetlock_parity.txt
#include "DaedalusFacetlockCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::facetlock;

namespace {
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
int UnitChecks()
{
	int Fails = 0;
	const std::vector<std::string> B = { "ETV", "ETV", "ETV" };
	if (Shift(B, { true, 0, 1 })[0] != "VET") { std::printf("FAIL row shift right wraps\n"); ++Fails; }
	if (Shift(B, { true, 0, -1 })[0] != "TVE") { std::printf("FAIL row shift left wraps\n"); ++Fails; }
	const std::vector<std::string> C = { "AAA", "BBB", "CCC" };
	if (Shift(C, { false, 1, 1 })[0][1] != 'C' || Shift(C, { false, 1, -1 })[0][1] != 'B') { std::printf("FAIL column shift wraps\n"); ++Fails; }
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(5, "normal") || G.Size() != 4 || G.Moves != 9 || G.Solved() || G.Over) { std::printf("FAIL normal start is scrambled with a budget of 9\n"); ++Fails; }
	int Gained = 0;
	if (G.Apply({ true, 7, 1 }, Gained) != Game::Act::BadMove || G.Apply({ true, 0, 2 }, Gained) != Game::Act::BadMove) { std::printf("FAIL bad move accepted\n"); ++Fails; }
	const size_t Before = G.Solution.size();
	G.Apply({ true, 0, 1 }, Gained);
	if (G.Solution.size() != Before + 1 && G.Solution.size() != Before - 1) { std::printf("FAIL solution tracks the move\n"); ++Fails; }
	return Fails;
}
} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: facetlock_core_test facetlock_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks(), Games = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; int Turn = 0; bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Turn = 0; Skip = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skip = true; continue; }
			std::ostringstream O; O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " moves=" << G.Moves << " board=" << G.BoardString() << " solution=" << G.SolutionString();
			if (O.str() != Line) { std::printf("FAIL scramble differs\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Move M = G.DemoAction();
			int Gained = 0;
			const Game::Act R = G.Apply(M, Gained);
			++Turn;
			std::ostringstream O; O << "move t=" << Turn << " kind=" << (M.Row ? 'r' : 'c') << " i=" << M.Index << " d=" << M.Dir << " gained=" << Gained << " score=" << G.Score
			  << " moves=" << G.Moves << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " board=" << G.BoardString() << " solution=" << G.SolutionString();
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0);
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s facetlock: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
