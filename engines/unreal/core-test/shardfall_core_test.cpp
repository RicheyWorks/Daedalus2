// SPDX-License-Identifier: MIT
// Shardfall Gamble parity: DaedalusShardfallCore.h regenerates every seam bag in shardfall_parity.txt from seed +
// difficulty alone (CPython-compatible shuffle) and replays every demo draw/bank byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shardfall_core_test.cpp -o shardfall_core_test && ./shardfall_core_test shardfall_parity.txt
#include "DaedalusShardfallCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::shardfall;

namespace {
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string Res(Game::Draw D, int V) { return D == Game::Draw::Collapse ? "collapse" : D == Game::Draw::Cracked ? "cracked" : "+" + std::to_string(V); }
int UnitChecks()
{
	int Fails = 0;
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(0, "normal") || G.Bag.size() != 15 || G.CrackedLeft() != 3 || G.Round != 1) { std::printf("FAIL normal seam has 12 shards + 3 cracked\n"); ++Fails; }
	int Sum = 0; for (int V : G.Bag) Sum += V; if (Sum != 35) { std::printf("FAIL bag keeps the value multiset\n"); ++Fails; }
	Game E; E.Start(0, "easy"); Game::Draw D; int V; int B;
	while (!E.Bag.empty() && E.DrawShard(D, V) == Game::Act::Ok && D != Game::Draw::Collapse) {}
	if (!E.Bag.empty() && E.DrawShard(D, V) == Game::Act::EmptySeam) { std::printf("FAIL unexpected\n"); ++Fails; }
	Game Bk; Bk.Start(3, "hard"); Bk.Bank(B); if (Bk.Round != 2 || Bk.History.size() != 1 || Bk.History[0] != 0) { std::printf("FAIL banking an empty pot opens the next round\n"); ++Fails; }
	return Fails;
}
} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shardfall_core_test shardfall_parity.txt\n"); return 2; }
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
			std::ostringstream O; O << "game s=" << Seed << " d=" << Diff << " round=" << G.Round << " bag=" << G.BagString();
			if (O.str() != Line) { std::printf("FAIL seam differs\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const bool Bank = G.DemoBank();
			++Turn; std::string R; Game::Act A;
			if (Bank) { int B = 0; A = G.Bank(B); R = "banked_" + std::to_string(B); }
			else { Game::Draw D; int V; A = G.DrawShard(D, V); R = Res(D, V); }
			std::ostringstream O; O << "move t=" << Turn << " act=" << (Bank ? "bank" : "draw") << " res=" << R << " round=" << G.Round << " pot=" << G.Pot << " cracks=" << G.Cracks << " score=" << G.Score
			  << " bag=" << G.BagString() << " history=" << G.HistoryString() << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
			if (A != Game::Act::Ok || O.str() != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " rounds=" << G.Round;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s shardfall: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
