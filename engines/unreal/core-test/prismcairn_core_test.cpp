// SPDX-License-Identifier: MIT
// Prismcairn Duel parity: DaedalusPrismcairnCore.h regenerates every deal in prismcairn_parity.txt from seed +
// difficulty alone and replays every demo move and Warden reply byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public prismcairn_core_test.cpp -o prismcairn_core_test && ./prismcairn_core_test prismcairn_parity.txt
#include "DaedalusPrismcairnCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::prismcairn;

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
	if (Grundy({ 1, 2, 3 }, 3) != 0 || Grundy({ 4, 1, 7 }, 3) == 0) { std::printf("FAIL grundy\n"); ++Fails; }
	if (BestMove({ 4, 1, 7 }, 3) != std::pair<int, int>{ 0, 2 }) { std::printf("FAIL best move to a zero position\n"); ++Fails; }
	if (BestMove({ 1, 2, 3 }, 3) != std::pair<int, int>{ 0, 1 }) { std::printf("FAIL smallest legal move from a lost position\n"); ++Fails; }
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(0, "hard") || G.Cairns.size() != 5 || G.Round != 1 || Grundy(G.Cairns, 4) == 0) { std::printf("FAIL hard deal is winnable\n"); ++Fails; }
	Game::Outcome O; int WC, WT;
	if (G.Take(9, 1, O, WC, WT) != Game::Act::BadMove || G.Take(0, 0, O, WC, WT) != Game::Act::BadMove || G.Take(0, 5, O, WC, WT) != Game::Act::BadMove) { std::printf("FAIL bad move accepted\n"); ++Fails; }
	return Fails;
}
} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: prismcairn_core_test prismcairn_parity.txt\n"); return 2; }
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
			std::ostringstream O; O << "game s=" << Seed << " d=" << Diff << " round=" << G.Round << " cairns=" << G.CairnsString();
			if (O.str() != Line) { std::printf("FAIL deal differs\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const std::pair<int, int> A = G.DemoAction();
			Game::Outcome Out; int WC, WT;
			const Game::Act R = G.Take(A.first, A.second, Out, WC, WT);
			++Turn;
			std::ostringstream O; O << "move t=" << Turn << " i=" << A.first << " take=" << A.second << " out=" << (Out == Game::Outcome::YouLiftLast ? "you" : Out == Game::Outcome::WardenLiftsLast ? "warden_last" : "warden")
			  << " wi=" << WC << " wt=" << WT << " round=" << G.Round << " wins=" << G.Wins << " losses=" << G.Losses << " score=" << G.Score << " cairns=" << G.CairnsString() << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " rounds=" << G.Round;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s prismcairn: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
