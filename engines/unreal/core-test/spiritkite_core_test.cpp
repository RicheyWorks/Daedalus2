// SPDX-License-Identifier: MIT
// Spiritkite Weave parity: DaedalusSpiritkiteCore.h must regenerate every sky in spiritkite_parity.txt (lanes, lantern
// values, the exact best round trip's target and plan) from seed + difficulty alone (CPython-compatible seeding) and
// replay every demo hop byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public spiritkite_core_test.cpp -o spiritkite_core_test && ./spiritkite_core_test spiritkite_parity.txt
#include "DaedalusSpiritkiteCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::spiritkite;

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
	return A.K == Kind::Land ? "land" : "fly:" + std::to_string(A.Isle);
}

std::string StateString(const Game& G)
{
	std::ostringstream O;
	O << "at=" << G.At << " wind=" << G.Wind << " score=" << G.Score << " gathered=" << Ints(G.Gathered) << " trail=" << Ints(G.Trail);
	return O.str();
}

std::string Opening(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	std::string Lanes;
	for (size_t I = 0; I < G.Lanes.size(); ++I)
	{
		const Lane& L = G.Lanes[I];
		Lanes += (I ? "," : "") + std::to_string(L.A) + "-" + std::to_string(L.B) + "-" + std::to_string(L.Wind);
	}
	return "game s=" + std::to_string(Seed) + " d=" + Diff + " lanes=" + Lanes + " values=" + Ints(G.Values) + " target=" + std::to_string(G.Target)
		+ " plan=" + Ints(G.Plan) + " " + StateString(G);
}

int UnitChecks()
{
	int Fails = 0;
	// Halfway ties round to even like Python: dist 1 -> 0.5 -> 0, dist 3 -> 1.5 -> 2, dist 5 -> 2.5 -> 2.
	if (Game::LaneWind({ 0, 0 }, { 1, 0 }) != 1 || Game::LaneWind({ 0, 0 }, { 3, 0 }) != 3 || Game::LaneWind({ 0, 0 }, { 3, 4 }) != 3)
	{
		std::printf("FAIL lane wind rounding\n"); ++Fails;
	}
	// Line 0-1-2 with winds 2 and 2: a budget of 8 reaches both (Python plans 2 then 1), 4 only isle 1, 3 nothing.
	const std::vector<Lane> Line = { { 0, 1, 2 }, { 1, 2, 2 } };
	const Matrix D = Shortest(3, Line);
	if (D[0][2] != 4 || D[2][0] != 4) { std::printf("FAIL shortest\n"); ++Fails; }
	const std::vector<int> Values = { 0, 3, 5 };
	const Tour Full = BestTour(D, Values, 8), Half = BestTour(D, Values, 4), None = BestTour(D, Values, 3);
	if (Full.Best != 8 || Full.Order != std::vector<int>{ 2, 1 }) { std::printf("FAIL full tour\n"); ++Fails; }
	if (Half.Best != 3 || Half.Order != std::vector<int>{ 1 }) { std::printf("FAIL half tour\n"); ++Fails; }
	if (None.Best != 0 || !None.Order.empty()) { std::printf("FAIL empty tour\n"); ++Fails; }
	// Triangle 0-1 (1), 1-2 (3), 0-2 (4), wind 8: most lanterns is both isles (score 8 + 0 wind), but with target 3
	// isle 1 alone scores 3 + 6 = 9, so the best-score plan is { 1 } (spiritkite.best_tour with a target).
	const Matrix Tri = Shortest(3, { { 0, 1, 1 }, { 1, 2, 3 }, { 0, 2, 4 } });
	const Tour TopTour = BestTour(Tri, Values, 8, 3);
	if (TopTour.Best != 8 || TopTour.Order != std::vector<int>{ 1 }) { std::printf("FAIL best-score tour\n"); ++Fails; }

	Game G; std::string Res;
	if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(1, "hard") || G.Isles() != 10 || G.Wind != 26 || G.Lanes.size() != 14 || G.Target < 1) { std::printf("FAIL hard start\n"); ++Fails; }
	G.Lanes = Line; G.Values = Values; G.Restore(); G.Target = 3; G.Wind = 5;
	if (G.Step({ Kind::Fly, 2 }, Res) != Game::Act::NoLane || G.Step({ Kind::Fly, 9 }, Res) != Game::Act::NoLane) { std::printf("FAIL missing lane accepted\n"); ++Fails; }
	if (G.Step({ Kind::Fly, 1 }, Res) != Game::Act::Ok || Res != "+3" || G.Wind != 3 || G.Score != 3) { std::printf("FAIL fly\n"); ++Fails; }
	{
		Game Fresh; Fresh.Start(1, "normal"); std::string R0;
		if (Fresh.Step({ Kind::Land, 0 }, R0) != Game::Act::FlyFirst || Fresh.Over) { std::printf("FAIL land before flying accepted\n"); ++Fails; }
	}
	if (G.Step({ Kind::Land, 0 }, Res) != Game::Act::NotAnchor) { std::printf("FAIL land away from anchor\n"); ++Fails; }
	if (G.Step({ Kind::Fly, 0 }, Res) != Game::Act::Ok || Res != "+0") { std::printf("FAIL fly home\n"); ++Fails; }
	if (G.Step({ Kind::Land, 0 }, Res) != Game::Act::Ok || !G.Over || !G.Won || G.Score != 3 + 1 || Res != "landed with 3") { std::printf("FAIL land\n"); ++Fails; }
	if (G.Step({ Kind::Land, 0 }, Res) != Game::Act::GameOver) { std::printf("FAIL move after landing\n"); ++Fails; }
	G.Start(1, "hard"); G.Lanes = Line; G.Values = Values; G.Restore(); G.Wind = 3;
	if (G.Step({ Kind::Fly, 1 }, Res) != Game::Act::Ok || Res != "the kite is lost" || !G.Over || G.Won) { std::printf("FAIL lost kite\n"); ++Fails; }
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: spiritkite_core_test spiritkite_parity.txt\n"); return 2; }
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
			const std::string Got = Opening(Seed, Diff, G);
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
	std::printf("%s spiritkite: %d skies regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
