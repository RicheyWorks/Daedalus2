// SPDX-License-Identifier: MIT
// Fogbell Ferry parity: DaedalusFogbellCore.h must regenerate every flat in fogbell_parity.txt from seed + difficulty
// alone (CPython-compatible seeding) and steer the same demo path step for step.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public fogbell_core_test.cpp -o fogbell_core_test && ./fogbell_core_test fogbell_parity.txt
#include "DaedalusFogbellCore.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::fogbell;

namespace {

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::vector<std::string> Split(const std::string& S, char Sep)
{
	std::vector<std::string> Out; std::string Tok;
	for (char Ch : S) { if (Ch == Sep) { Out.push_back(Tok); Tok.clear(); } else Tok.push_back(Ch); }
	if (!S.empty()) Out.push_back(Tok);
	return Out;
}

std::string GameLine(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	std::ostringstream O;
	O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " heights=" << G.HeightsString() << " ferry=" << G.Ferry.R << "," << G.Ferry.C
	  << " harbour=" << G.Harbour.R << "," << G.Harbour.C << " passengers=" << Game::CellsString(G.Passengers);
	return O.str();
}

std::string MoveLine(Move M, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << G.Turn << " act=" << MoveName(M) << " ferry=" << G.Ferry.R << "," << G.Ferry.C << " tide=" << G.Tide() << " aboard=" << G.Aboard
	  << " passengers=" << Game::CellsString(G.Passengers) << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set flat for rule checks: rows of digit heights, ferry north-west, harbour south-east. */
Game Flat(const std::vector<std::string>& Rows, const std::vector<Cell>& Passengers, int Need)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", static_cast<int>(Rows.size()), static_cast<int>(Passengers.size()), Need };
	G.Diff = &Custom;
	G.Heights.clear();
	for (const std::string& Row : Rows) { std::vector<int> H; for (char Ch : Row) H.push_back(Ch - '0'); G.Heights.push_back(H); }
	G.Ferry = { 0, 0 }; G.Harbour = { static_cast<int>(Rows.size()) - 1, static_cast<int>(Rows.size()) - 1 };
	G.Passengers = Passengers; G.Aboard = 0; G.Turn = 0; G.Score = 0; G.Over = G.Won = false;
	return G;
}

int UnitChecks()
{
	int Fails = 0; std::string Text; Move M = Move::Wait;
	Game G = Flat({ "333", "333", "333" }, { { 0, 1 } }, 1);
	if (G.Step(Move::E, Text) != Game::Act::Ok || Text != "e: lantern aboard, tide 0" || G.Aboard != 1 || !G.Passengers.empty()) { std::printf("FAIL east onto a dock takes the lantern (%s)\n", Text.c_str()); ++Fails; }
	if (G.Step(Move::N, Text) != Game::Act::OffFlat) { std::printf("FAIL moving off the flat is refused\n"); ++Fails; }
	G = Flat({ "313", "333", "333" }, {}, 1); G.Turn = 3;
	if (G.Step(Move::E, Text) != Game::Act::UnderWater) { std::printf("FAIL a flooded cell is refused\n"); ++Fails; }
	G = Flat({ "313", "333", "333" }, {}, 1); G.Turn = 2; G.Ferry = { 0, 1 };
	if (G.Step(Move::Wait, Text) != Game::Act::Ok || !G.Over || G.Won || Text != "wait: the tide takes the ferry") { std::printf("FAIL the tide takes a ferry that waits on low ground (%s)\n", Text.c_str()); ++Fails; }
	G = Flat({ "33", "33" }, { { 0, 1 } }, 1); G.Step(Move::E, Text); G.Step(Move::S, Text);
	if (!G.Over || !G.Won || G.Score != PassengerScore + TideScore * (TideEvery * 2 - 2) || Text.find("bell rings clear") == std::string::npos) { std::printf("FAIL harbour with enough lanterns wins (%s score %d)\n", Text.c_str(), G.Score); ++Fails; }
	G = Flat({ "33", "33" }, { { 0, 1 } }, 1); G.Step(Move::S, Text); G.Step(Move::E, Text);
	if (!G.Over || G.Won || Text.find("too few lanterns") == std::string::npos) { std::printf("FAIL harbour short of lanterns loses\n"); ++Fails; }
	if (G.Step(Move::N, Text) != Game::Act::GameOver) { std::printf("FAIL a finished voyage refuses moves\n"); ++Fails; }
	G = Flat({ "3133", "3333", "3333", "3333" }, { { 0, 3 } }, 1); G.Turn = 2;
	if (!G.FirstStepTo({ { 0, 3 } }, M) || M != Move::S) { std::printf("FAIL BFS routes around a cell that floods on arrival (%s)\n", MoveName(M)); ++Fails; }
	G = Flat({ "3333", "3333", "3333", "3333" }, { { 0, 2 } }, 1);
	if (G.DemoAction() != Move::E) { std::printf("FAIL demo heads for the nearest lantern\n"); ++Fails; }
	G = Flat({ "31", "13" }, {}, 1); G.Turn = 3;
	if (G.DemoAction() != Move::Wait) { std::printf("FAIL a stranded ferry waits\n"); ++Fails; }
	Game H; if (H.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!H.Start(5, "hard") || H.Size() != 9 || H.Passengers.size() != 5 || H.Heights[0][0] != 9 || H.Heights[8][8] != 9) { std::printf("FAIL hard start\n"); ++Fails; }
	for (const Cell& P : H.Passengers) if (H.Heights[static_cast<size_t>(P.R)][static_cast<size_t>(P.C)] < 2 || P == H.Ferry || P == H.Harbour) { std::printf("FAIL docks sit on height >= 2 away from the corners\n"); ++Fails; break; }
	return Fails;
}

/** Iteration 2: 600 random voyages steered with random legal moves; every state must satisfy the rules' invariants. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0;
	const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff);
			const std::vector<std::vector<int>> Heights = G.Heights;
			std::uint32_t Pick = Seed * 2654435761u + 11u;
			while (!G.Over)
			{
				// collect the legal moves the way the rules define them, then pick one
				std::vector<Move> Legal;
				for (int I = 0; I < MoveCount; ++I)
				{
					const Move M = static_cast<Move>(I);
					const int R = G.Ferry.R + MoveDR(M), C = G.Ferry.C + MoveDC(M);
					if (G.Inside(R, C) && !G.Flooded(R, C)) Legal.push_back(M);
				}
				if (Legal.empty()) { std::printf("FAIL sweep: no legal move while dry (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				Pick = Pick * 1664525u + 1013904223u;
				const Move M = Legal[(Pick >> 16) % Legal.size()];
				const int TurnBefore = G.Turn; const Cell FerryBefore = G.Ferry;
				std::string Text;
				if (G.Step(M, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal move refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = G.Turn == TurnBefore + 1 && G.Heights == Heights && G.Aboard + static_cast<int>(G.Passengers.size()) == G.Diff->Passengers;
				Ok = Ok && std::abs(G.Ferry.R - FerryBefore.R) + std::abs(G.Ferry.C - FerryBefore.C) <= 1;
				if (G.Over)
				{
					const bool AtHarbour = G.Ferry == G.Harbour;
					Ok = Ok && (AtHarbour || G.Flooded(G.Ferry.R, G.Ferry.C)) && G.Won == (AtHarbour && G.Aboard >= G.Diff->Need);
					if (AtHarbour) Ok = Ok && G.Score == PassengerScore * G.Aboard + TideScore * std::max(0, TideEvery * G.Size() - G.Turn);
				}
				else Ok = Ok && !G.Flooded(G.Ferry.R, G.Ferry.C) && G.Score == 0;
				if (!Ok) { std::printf("FAIL sweep invariant (seed %u %s turn %d): %s\n", Seed, Diff, G.Turn, Text.c_str()); ++Fails; break; }
				if (G.Turn > TideEvery * G.Size()) { std::printf("FAIL sweep: voyage outlived the tide\n"); ++Fails; break; }
			}
			std::string Text;
			if (G.Step(Move::Wait, Text) != Game::Act::GameOver) { std::printf("FAIL sweep: finished voyage accepted a move\n"); ++Fails; }
		}
	if (!Fails) std::printf("sweep: 600 voyages, %d random legal moves, invariants held\n", Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: fogbell_core_test fogbell_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks() + InvariantSweep(), Games = 0, Vectors = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Skip = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skip = true; continue; }
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL flat differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Move M = G.DemoAction();
			std::string Result;
			const Game::Act R = G.Step(M, Result);
			const std::string Got = MoveLine(M, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), G.Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " aboard=" << G.Aboard << " turns=" << G.Turn;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else if (Line.rfind("vector ", 0) == 0)
		{
			// Hand-set flat: size / heights / ferry / turn / aboard / need / passengers replace the seeded state.
			Diff = "vector:" + Line.substr(7, Line.find(' ', 7) - 7); Skip = false; ++Vectors;
			G = Flat(Split(Field(Line, "heights"), '|'), {}, std::stoi(Field(Line, "need")));
			const std::vector<std::string> F = Split(Field(Line, "ferry"), ',');
			G.Ferry = { std::stoi(F[0]), std::stoi(F[1]) };
			G.Turn = std::stoi(Field(Line, "turn")); G.Aboard = std::stoi(Field(Line, "aboard"));
			G.Passengers.clear();
			if (Field(Line, "passengers") != "-")
				for (const std::string& Tok : Split(Field(Line, "passengers"), ';')) { const std::vector<std::string> P = Split(Tok, ','); G.Passengers.push_back({ std::stoi(P[0]), std::stoi(P[1]) }); }
		}
		else if (Line.rfind("step ", 0) == 0)
		{
			if (Skip) continue;
			Move M = Move::Wait; MoveFromName(Field(Line, "act"), M);
			const Move Demo = G.DemoAction();
			std::string Result;
			const Game::Act R = G.Step(M, Result);
			std::ostringstream O;
			O << "step act=" << MoveName(M) << " demo=" << MoveName(Demo) << " ferry=" << G.Ferry.R << "," << G.Ferry.C << " tide=" << G.Tide() << " aboard=" << G.Aboard
			  << " passengers=" << Game::CellsString(G.Passengers) << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL %s\n  want %s\n  got  %s\n", Diff.c_str(), Line.c_str(), O.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s fogbell: %d voyages regenerated from seed, %d edge vectors, %d failures\n", Fails ? "FAIL" : "OK", Games, Vectors, Fails);
	return Fails ? 1 : 0;
}
