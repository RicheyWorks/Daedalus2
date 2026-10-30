// SPDX-License-Identifier: MIT
// Prismvault Weigh parity: DaedalusPrismvaultCore.h regenerates every vault in prismvault_parity.txt from seed +
// difficulty alone and replays every demo weighing and naming byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public prismvault_core_test.cpp -o prismvault_core_test && ./prismvault_core_test prismvault_parity.txt
#include "DaedalusPrismvaultCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::prismvault;

namespace {
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string Lst(const std::vector<int>& V) { return V.empty() ? "-" : Game::ListString(V); }
int UnitChecks()
{
	int Fails = 0;
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(0, "easy") || G.Shards() != 8 || G.Weighings != 3 || G.Candidates.size() != 8) { std::printf("FAIL easy start\n"); ++Fails; }
	char R = '?';
	if (G.Weigh({ 0, 1 }, { 1, 2 }, R) != Game::Act::BadGroups || G.Weigh({ 0 }, { 1, 2 }, R) != Game::Act::BadGroups || G.Weigh({}, {}, R) != Game::Act::BadGroups || G.Weigh({ 0 }, { 99 }, R) != Game::Act::BadGroups) { std::printf("FAIL bad groups accepted\n"); ++Fails; }
	if (G.Weigh({ 2, 0 }, { 1, 1, 3 }, R) != Game::Act::Ok || G.Weighings != 2 || G.Log.size() != 1 || G.Log[0].Left != std::vector<int>{ 0, 2 } || G.Log[0].Right != std::vector<int>{ 1, 3 }) { std::printf("FAIL weighing sorts, dedupes and logs as Python does\n"); ++Fails; }
	if (G.Weigh({ 1, 0 }, { 3, 2 }, R) != Game::Act::Ok || G.Weighings != 1 || G.Log.size() != 2) { std::printf("FAIL second weighing\n"); ++Fails; }
	int Gained = 0;
	if (G.Name(99, Gained) != Game::Act::BadShard) { std::printf("FAIL naming out of range accepted\n"); ++Fails; }
	Game Wrong; Wrong.Start(0, "easy"); Wrong.Name((Wrong.Hollow + 1) % 8, Gained);
	if (!Wrong.Over || Wrong.Won || Gained != 0) { std::printf("FAIL a wrong name loses\n"); ++Fails; }
	return Fails;
}
} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: prismvault_core_test prismvault_parity.txt\n"); return 2; }
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
			std::ostringstream O; O << "game s=" << Seed << " d=" << Diff << " shards=" << G.Shards() << " hollow=" << G.Hollow << " weighings=" << G.Weighings << " candidates=" << Lst(G.Candidates);
			if (O.str() != Line) { std::printf("FAIL vault differs\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Game::Demo A = G.DemoAction();
			++Turn;
			std::ostringstream O;
			if (A.IsName)
			{
				int Gained = 0; const Game::Act R = G.Name(A.Shard, Gained);
				O << "move t=" << Turn << " kind=name left=- right=- shard=" << A.Shard << " res=- gained=" << Gained << " score=" << G.Score << " weighings=" << G.Weighings << " candidates=" << Lst(G.Candidates) << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
				if (R != Game::Act::Ok) { std::printf("FAIL s=%u %s turn %d name refused\n", Seed, Diff.c_str(), Turn); ++Fails; Skip = true; continue; }
			}
			else
			{
				char Res = '?'; const Game::Act R = G.Weigh(A.Left, A.Right, Res);
				O << "move t=" << Turn << " kind=weigh left=" << Lst(A.Left) << " right=" << Lst(A.Right) << " shard=-1 res=" << Res << " gained=0 score=" << G.Score << " weighings=" << G.Weighings << " candidates=" << Lst(G.Candidates) << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
				if (R != Game::Act::Ok) { std::printf("FAIL s=%u %s turn %d weigh refused\n", Seed, Diff.c_str(), Turn); ++Fails; Skip = true; continue; }
			}
			if (O.str() != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0);
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s prismvault: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
