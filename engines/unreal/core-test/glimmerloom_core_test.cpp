// SPDX-License-Identifier: MIT
// Glimmerloom Ledger parity: DaedalusGlimmerloomCore.h must regenerate every market in glimmerloom_parity.txt from
// seed + difficulty alone (CPython-compatible seeding) and replay every demo action byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public glimmerloom_core_test.cpp -o glimmerloom_core_test && ./glimmerloom_core_test glimmerloom_parity.txt
#include "DaedalusGlimmerloomCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::glimmerloom;

namespace {

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::string Ints(const std::vector<int>& Xs)
{
	std::string S;
	for (size_t I = 0; I < Xs.size(); ++I) S += (I ? "," : "") + std::to_string(Xs[I]);
	return S;
}

std::string ActString(const Action& A)
{
	if (A.K == Kind::Rest) return "rest";
	return std::string(A.K == Kind::Buy ? "buy:" : "sell:") + std::to_string(A.Hue) + ":" + std::to_string(A.Count);
}

std::string StateString(const Game& G)
{
	std::ostringstream O;
	O << "day=" << G.Day << " purse=" << G.Purse << " score=" << G.Score << " prices=" << Ints(G.Prices) << " satchel=" << Ints(G.Satchel)
	  << " moves=" << Ints(G.Moves) << " rumor=" << G.RumorHue << ":" << (G.RumorRise ? "rise" : "fall");
	return O.str();
}

int UnitChecks()
{
	int Fails = 0;
	Game G; std::string Res;
	if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(1, "hard") || G.Prices.size() != 5 || G.Purse != 100) { std::printf("FAIL hard start\n"); ++Fails; }
	G.Prices[0] = 10;
	if (G.Step({ Kind::Buy, 0, 3 }, Res) != Game::Act::Ok || G.Purse != 70 || G.Satchel[0] != 3) { std::printf("FAIL buy\n"); ++Fails; }
	if (G.Step({ Kind::Sell, 0, 2 }, Res) != Game::Act::Ok || G.Purse != 70 + 2 * 9 || Res != "purse 88") { std::printf("FAIL taxed sell\n"); ++Fails; }
	if (G.Step({ Kind::Sell, 0, 5 }, Res) != Game::Act::NotHeld) { std::printf("FAIL oversell accepted\n"); ++Fails; }
	if (G.Step({ Kind::Buy, 0, 99 }, Res) != Game::Act::NoRoom) { std::printf("FAIL overbuy accepted\n"); ++Fails; }
	if (G.Step({ Kind::Buy, 9, 1 }, Res) != Game::Act::BadPick || G.Step({ Kind::Buy, 0, 0 }, Res) != Game::Act::BadPick) { std::printf("FAIL bad pick accepted\n"); ++Fails; }
	G.Start(2, "normal"); G.Prices = { Low, High, 10, 10 }; G.Moves = { -3, 3, 2, -1 };
	if (G.Step({}, Res) != Game::Act::Ok || G.Prices != std::vector<int>{ Low, High, 12, 9 } || Res != "day 2") { std::printf("FAIL rest clamps prices\n"); ++Fails; }
	G.Day = G.Diff->Days; G.Satchel = { 0, 4, 0, 0 }; G.Moves = { 0, 0, 0, 0 }; G.Purse = G.Diff->Target - 4 * G.Prices[1];
	if (G.Step({}, Res) != Game::Act::Ok || !G.Over || !G.Won || G.Score != G.Diff->Target) { std::printf("FAIL last day sells all\n"); ++Fails; }
	if (G.Step({}, Res) != Game::Act::GameOver) { std::printf("FAIL move after close\n"); ++Fails; }
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: glimmerloom_core_test glimmerloom_parity.txt\n"); return 2; }
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
			const std::string Got = "game s=" + std::to_string(Seed) + " d=" + Diff + " " + StateString(G);
			if (Got != Line) { std::printf("FAIL opening differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Action A = G.DemoAction();
			std::string Res;
			const Game::Act R = G.Step(A, Res);
			++Turn;
			std::ostringstream O;
			O << "move t=" << Turn << " act=" << ActString(A) << " " << StateString(G) << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Res;
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL s=%u %s turn %d (act=%d)\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, static_cast<int>(R), Line.c_str(), O.str().c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0);
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s glimmerloom: %d markets regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
