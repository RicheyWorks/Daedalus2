// SPDX-License-Identifier: MIT
// Shardring Resonance parity: replays engines/unreal/core-test/shardring_parity.txt (generated from the Python rules
// by tools/minigames/shardring_parity.py) through DaedalusShardringCore.h. The fixture's `rng` lines feed the Oracle;
// the core's GreedyMove and SetShard must reproduce every `move` and `end` line byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shardring_core_test.cpp -o shardring_core_test && ./shardring_core_test shardring_parity.txt
#include "DaedalusShardringCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::shardring;

namespace {

struct FixtureOracle : Oracle
{
	std::vector<std::pair<std::string, std::string>> Events; size_t At = 0; int Errors = 0;
	Hue Draw() override
	{
		if (At >= Events.size() || Events[At].first != "draw") { ++Errors; return Hue::None; }
		return HueFromName(Events[At++].second);
	}
	int SpiritPick(const std::vector<int>&) override
	{
		if (At >= Events.size() || Events[At].first != "spirit") { ++Errors; return -1; }
		return std::stoi(Events[At++].second);
	}
};

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::string MoveLine(int Turn, int Facet, int Gained, const Game& G)
{
	std::ostringstream O;
	O << "move t=" << Turn << " facet=" << Facet << " gained=" << Gained << " score=" << G.Score << " chain=" << G.Chain
	  << " pouch=" << G.Pouch << " cur=" << HueName(G.Current) << " next=" << HueName(G.Next) << " spirits=" << G.Spirits.size()
	  << " ring=" << G.RingString() << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
	return O.str();
}

std::string EndLine(const Game& G)
{
	std::ostringstream O;
	O << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " spirits=";
	for (size_t I = 0; I < G.Spirits.size(); ++I) O << (I ? "," : "") << SpiritName(G.Spirits[I]);
	return O.str();
}

struct Block { std::string Header; std::vector<std::pair<std::string, std::string>> Rng; std::vector<std::string> Moves; std::string End; };

int Replay(const Block& B, int& Games)
{
	int Fails = 0;
	FixtureOracle O; O.Events = B.Rng;
	Game G;
	if (!G.Start(Field(B.Header, "d"), O)) { std::printf("FAIL %s: unknown difficulty\n", B.Header.c_str()); return 1; }
	if (G.Facets() != std::stoi(Field(B.Header, "facets")) || G.Diff->Hues != std::stoi(Field(B.Header, "hues")) || G.Pouch != std::stoi(Field(B.Header, "shards")))
	{ std::printf("FAIL %s: difficulty table differs\n", B.Header.c_str()); ++Fails; }
	int Turn = 0;
	for (const std::string& Expected : B.Moves)
	{
		const int Facet = G.GreedyMove();
		int Gained = 0;
		const Game::Place R = G.SetShard(Facet, O, Gained);
		++Turn;
		const std::string Got = MoveLine(Turn, Facet, Gained, G);
		if (R != Game::Place::Ok || Got != Expected)
		{
			std::printf("FAIL %s turn %d (place=%d)\n  want %s\n  got  %s\n", B.Header.c_str(), Turn, static_cast<int>(R), Expected.c_str(), Got.c_str());
			++Fails; break;
		}
	}
	if (!G.Over) { std::printf("FAIL %s: fixture ended but game is not over\n", B.Header.c_str()); ++Fails; }
	const std::string GotEnd = EndLine(G);
	if (GotEnd != B.End) { std::printf("FAIL %s end\n  want %s\n  got  %s\n", B.Header.c_str(), B.End.c_str(), GotEnd.c_str()); ++Fails; }
	if (O.At != O.Events.size() || O.Errors) { std::printf("FAIL %s: oracle consumed %zu of %zu events, %d errors\n", B.Header.c_str(), O.At, O.Events.size(), O.Errors); ++Fails; }
	++Games;
	return Fails;
}

int UnitChecks()
{
	int Fails = 0;
	struct Fixed : Oracle { Hue H; explicit Fixed(Hue InH) : H(InH) {} Hue Draw() override { return H; } int SpiritPick(const std::vector<int>& F) override { return F.front(); } };
	Fixed O(Hue::Ember);
	Game G; G.Start("hard", O);
	int Gained = 0;
	if (G.SetShard(99, O, Gained) != Game::Place::BadFacet) { std::printf("FAIL bad facet accepted\n"); ++Fails; }
	G.SetShard(0, O, Gained); G.SetShard(1, O, Gained);
	if (G.SetShard(1, O, Gained) != Game::Place::BadFacet) { std::printf("FAIL occupied facet accepted\n"); ++Fails; }
	G.SetShard(2, O, Gained);                       // run of 3 ember: 9 * chain 1
	if (Gained != 9 || G.Score != 9 || G.Chain != 1 || G.RingString() != "........") { std::printf("FAIL resonance arithmetic: gained %d score %d chain %d ring %s\n", Gained, G.Score, G.Chain, G.RingString().c_str()); ++Fails; }
	G.SetShard(0, O, Gained); G.SetShard(1, O, Gained); G.SetShard(7, O, Gained);   // wrap-around run 7,0,1; chain reset to 0 by the two plain moves, so 9 * chain 1
	if (Gained != 9 || G.Chain != 1) { std::printf("FAIL circular run / chain: gained %d chain %d\n", Gained, G.Chain); ++Fails; }
	G.SetShard(3, O, Gained); G.SetShard(4, O, Gained); G.SetShard(5, O, Gained);   // third ember resonance -> spirit, +25, extra clear
	if (G.Spirits.size() != 1 || G.Spirits[0] != Hue::Ember || Gained != 9 * 1 + SpiritBonus) { std::printf("FAIL spirit summon: spirits %zu gained %d\n", G.Spirits.size(), Gained); ++Fails; }
	Game Unknown; if (Unknown.Start("legendary", O)) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shardring_core_test shardring_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks(), Games = 0;
	std::vector<Block> Blocks; std::string Line;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0) { Blocks.push_back(Block()); Blocks.back().Header = Line; continue; }
		if (Blocks.empty()) { std::printf("FAIL line before first game: %s\n", Line.c_str()); return 1; }
		if (Line.rfind("rng  ", 0) == 0) { std::istringstream S(Line.substr(5)); std::string K, V; S >> K >> V; Blocks.back().Rng.emplace_back(K, V); }
		else if (Line.rfind("move ", 0) == 0) Blocks.back().Moves.push_back(Line);
		else if (Line.rfind("end  ", 0) == 0) Blocks.back().End = Line;
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	for (const Block& B : Blocks) Fails += Replay(B, Games);
	std::printf("%s shardring: %d games replayed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
