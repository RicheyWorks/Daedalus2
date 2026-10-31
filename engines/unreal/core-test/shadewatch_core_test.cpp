// SPDX-License-Identifier: MIT
// Shadewatch Vigil parity: DaedalusShadewatchCore.h must regenerate every vigil in shadewatch_parity.txt from
// seed + difficulty alone (CPython-compatible seeding) and replay every demo action byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shadewatch_core_test.cpp -o shadewatch_core_test && ./shadewatch_core_test shadewatch_parity.txt
#include "DaedalusShadewatchCore.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::shadewatch;

namespace {

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::string ActString(const Action& A)
{
	return A.K == Kind::Flare ? "flare:" + std::to_string(A.Lane) : A.K == Kind::Nova ? "nova" : "kindle";
}

std::string GameLine(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	std::ostringstream O;
	O << "game s=" << Seed << " d=" << Diff << " hearts=" << G.Hearts << " light=" << G.Light << " lanes=" << G.LanesString();
	return O.str();
}

std::string MoveLine(int Turn, const Action& A, const Game& G, const std::string& Res)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << ActString(A) << " score=" << G.Score << " hearts=" << G.Hearts << " light=" << G.Light
	  << " burned=" << G.Burned << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " lanes=" << G.LanesString() << " res=" << Res;
	return O.str();
}

int UnitChecks()
{
	int Fails = 0;
	Game G; std::string Res;
	if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(1, "normal") || G.Lanes.size() != 3 || G.Hearts != 3 || G.Light != 1) { std::printf("FAIL normal start\n"); ++Fails; }
	if (G.Step({ Kind::Flare, 9 }, Res) != Game::Act::BadLane) { std::printf("FAIL bad lane accepted\n"); ++Fails; }
	if (G.Step({ Kind::Nova, 0 }, Res) != Game::Act::NoLight) { std::printf("FAIL nova without light accepted\n"); ++Fails; }
	G.Lanes = { { 0, 2, 5 }, { 1 }, { 3 } }; G.Light = 3;
	if (G.Step({ Kind::Nova, 0 }, Res) != Game::Act::Ok || G.Burned != 3 || G.Light != 0 || G.Lanes[0] != std::vector<int>{ 4 } || G.Lanes[2] != std::vector<int>{ 2 })
	{ std::printf("FAIL nova burns within reach (burned=%d)\n", G.Burned); ++Fails; }
	G.Start(2, "hard"); G.Hearts = 1; G.Lanes = { { 0 }, {}, {}, {} };
	if (G.Step({ Kind::Kindle, 0 }, Res) != Game::Act::Ok || !G.Over || G.Won || Res != "the heart dims") { std::printf("FAIL heart loss\n"); ++Fails; }
	if (G.Step({ Kind::Kindle, 0 }, Res) != Game::Act::GameOver) { std::printf("FAIL move after game over\n"); ++Fails; }
	return Fails;
}

} // namespace

namespace {
/** Spirit Boon levels (hephaestus R2-9): level 0 is the plain table, 1 and 2 add BoonDelta per level to Hearts. */
int BoonChecks()
{
	int Fails = 0;
	for (int I = 0; I < DifficultyCount; ++I)
	{
		const Difficulty& Base = Difficulties()[I];
		if (FindDifficulty(Base.Name, 0) != &Base || FindDifficulty(Base.Name, 3) || FindDifficulty(Base.Name, -1)) { std::printf("FAIL boon lookup\n"); ++Fails; }
		for (int L = 1; L <= 2; ++L)
		{
			const Difficulty* B = FindDifficulty(Base.Name, L);
			if (!B || B->Hearts != std::max(0, Base.Hearts + BoonDelta * L)) { std::printf("FAIL boon level %d on %s\n", L, Base.Name); ++Fails; }
			Game G;
			if (!G.Start(7, Base.Name, L) || G.Diff != B) { std::printf("FAIL boon start %d on %s\n", L, Base.Name); ++Fails; }
		}
	}
	return Fails;
}
}  // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shadewatch_core_test shadewatch_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = BoonChecks() + UnitChecks(), Games = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; int Turn = 0; bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Turn = 0; Skip = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skip = true; continue; }
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL opening differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Action A = G.DemoAction();
			std::string Res;
			const Game::Act R = G.Step(A, Res);
			++Turn;
			const std::string Got = MoveLine(Turn, A, G, Res);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d (act=%d)\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, static_cast<int>(R), Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0);
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s shadewatch: %d vigils regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
