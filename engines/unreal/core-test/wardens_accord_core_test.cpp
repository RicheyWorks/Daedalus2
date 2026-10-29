// SPDX-License-Identifier: MIT
// Wardens' Accord parity: DaedalusWardensAccordCore.h must regenerate every altar in wardens_accord_parity.txt from
// seed + difficulty alone (CPython-compatible seeding) and replay every demo move byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public wardens_accord_core_test.cpp -o wardens_accord_core_test && ./wardens_accord_core_test wardens_accord_parity.txt
#include "DaedalusWardensAccordCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::wardens;

namespace {
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string State(const Game& G) { return "pouch=" + G.PouchString() + " offer=" + G.OfferString() + " spirits=" + G.SpiritsString(); }

int UnitChecks()
{
	int Fails = 0;
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(0, "normal") || G.Spirits.size() != 4 || G.Offer.size() != 3 || G.Rounds != 14 || G.Over) { std::printf("FAIL normal start\n"); ++Fails; }
	int Gained = 0;
	if (G.Take(3, Gained) != Game::Act::BadIndex) { std::printf("FAIL take index 3 accepted\n"); ++Fails; }
	if (G.Summon(0, Gained) != Game::Act::NotAffordable) { std::printf("FAIL summon with an empty pouch accepted\n"); ++Fails; }
	if (G.Take(0, Gained) != Game::Act::Ok || G.Rounds != 13) { std::printf("FAIL take spends a round\n"); ++Fails; }
	for (const Spirit& S : G.Spirits) { int Total = 0; for (const auto& P : S.Cost) Total += P.second; if (Total < 2 || Total > 4 || S.Value != Total * 5 + (S.Cost.size() == 2 ? 5 : 0)) { std::printf("FAIL spirit cost/value arithmetic\n"); ++Fails; break; } }
	return Fails;
}
} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: wardens_accord_core_test wardens_accord_parity.txt\n"); return 2; }
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
			std::ostringstream O; O << "game s=" << Seed << " d=" << Diff << " rounds=" << G.Rounds << " target=" << G.Diff->Target << " " << State(G);
			if (O.str() != Line) { std::printf("FAIL altar differs\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const std::pair<bool, int> A = G.DemoAction();
			int Gained = 0;
			const Game::Act R = A.first ? G.Summon(A.second, Gained) : G.Take(A.second, Gained);
			++Turn;
			std::ostringstream O; O << "move t=" << Turn << " kind=" << (A.first ? "summon" : "take") << " i=" << A.second << " gained=" << Gained << " score=" << G.Score
			  << " rounds=" << G.Rounds << " " << State(G) << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL s=%u %s turn %d (act=%d)\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, static_cast<int>(R), Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " summoned=";
			for (size_t I = 0; I < G.Summoned.size(); ++I) E << (I ? "," : "") << G.Summoned[I];
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s wardens_accord: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
