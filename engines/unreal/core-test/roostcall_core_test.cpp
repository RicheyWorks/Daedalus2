// SPDX-License-Identifier: MIT
// Roostcall parity: DaedalusRoostcallCore.h must regenerate every yard in roostcall_parity.txt from seed + difficulty
// alone (CPython-compatible seeding) and herd the same demo path step for step.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public roostcall_core_test.cpp -o roostcall_core_test && ./roostcall_core_test roostcall_parity.txt
#include "DaedalusRoostcallCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::roostcall;

namespace {

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::string GameLine(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	std::ostringstream O;
	O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " turns=" << G.Turns << " whistler=" << G.Whistler.R << "," << G.Whistler.C << " birds=" << Game::CellsString(G.Birds);
	return O.str();
}

std::string MoveLine(int Turn, Move M, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << MoveName(M) << " whistler=" << G.Whistler.R << "," << G.Whistler.C << " birds=" << Game::CellsString(G.Birds) << " settled=" << G.Settled
	  << " turns=" << G.Turns << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set yard for rule checks. */
Game Yard(int Size, Cell Whistler, const std::vector<Cell>& Birds, int Turns)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", Size, static_cast<int>(Birds.size()), Turns };
	G.Diff = &Custom; G.Whistler = Whistler; G.Birds = Birds; G.Turns = Turns; G.Settled = 0; G.Score = 0; G.Over = G.Won = false;
	return G;
}

int UnitChecks()
{
	int Fails = 0; Cell To; int Flew = 0, Perched = 0; std::string Text;
	Game G = Yard(6, { 1, 1 }, { { 2, 1 } }, 10);
	if (!G.FleeStep(0, G.Whistler, To) || To != Cell{ 3, 1 }) { std::printf("FAIL whistler north: bird flees south\n"); ++Fails; }
	G = Yard(6, { 2, 3 }, { { 2, 1 } }, 10);
	if (!G.FleeStep(0, G.Whistler, To) || To != Cell{ 2, 0 }) { std::printf("FAIL whistler east: bird flees west\n"); ++Fails; }
	G = Yard(6, { 4, 4 }, { { 1, 1 } }, 10);
	if (G.FleeStep(0, G.Whistler, To)) { std::printf("FAIL a bird out of scare range stays\n"); ++Fails; }
	G = Yard(6, { 0, 4 }, { { 0, 5 } }, 10);
	if (!G.FleeStep(0, G.Whistler, To) || To != Cell{ 1, 5 }) { std::printf("FAIL beside a corner bird it goes down the edge\n"); ++Fails; }
	G = Yard(6, { 1, 4 }, { { 0, 5 } }, 10);
	if (G.FleeStep(0, G.Whistler, To)) { std::printf("FAIL nothing is strictly farther from a diagonal whistler\n"); ++Fails; }
	G = Yard(6, { 1, 1 }, { { 2, 1 }, { 3, 1 } }, 10);
	if (!G.FleeStep(0, G.Whistler, To) || To != Cell{ 2, 2 }) { std::printf("FAIL a bird with its back taken sidesteps east first\n"); ++Fails; }
	G = Yard(6, { 1, 1 }, { { 2, 1 }, { 3, 1 }, { 2, 2 }, { 2, 0 } }, 10);
	if (G.FleeStep(0, G.Whistler, To)) { std::printf("FAIL a boxed-in bird stays\n"); ++Fails; }
	G = Yard(6, { 2, 2 }, { { 1, 1 } }, 10);
	if (!G.FleeStep(0, G.Whistler, To) || To != Cell{ 0, 1 }) { std::printf("FAIL n wins the tie between n and w\n"); ++Fails; }
	G = Yard(6, { 2, 4 }, { { 3, 4 } }, 5); G.Step(Move::Wait, Flew, Perched, Text);
	if (!G.Over || !G.Won || Perched != 1 || G.Settled != 1 || G.Score != BirdScore + 4 || Text != "wait: 1 flew, every bird is home") { std::printf("FAIL a bird fleeing into the roost perches and wins (%s)\n", Text.c_str()); ++Fails; }
	G = Yard(6, { 0, 0 }, { { 5, 0 } }, 1); G.Step(Move::Wait, Flew, Perched, Text);
	if (!G.Over || G.Won || G.Score != 0 || Text != "wait: 0 flew, dusk falls with 0 home") { std::printf("FAIL dusk loses (%s)\n", Text.c_str()); ++Fails; }
	if (G.Step(Move::E, Flew, Perched, Text) != Game::Act::GameOver) { std::printf("FAIL a finished yard refuses moves\n"); ++Fails; }
	G = Yard(6, { 0, 0 }, { { 0, 1 } }, 10);
	if (G.Step(Move::N, Flew, Perched, Text) != Game::Act::OffYard || G.Step(Move::E, Flew, Perched, Text) != Game::Act::BirdThere) { std::printf("FAIL off-yard and bird cells are refused\n"); ++Fails; }
	Game H; if (H.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!H.Start(9, "hard") || H.Size() != 8 || H.Birds.size() != 5 || H.Turns != 48) { std::printf("FAIL hard start\n"); ++Fails; }
	for (const Cell& B : H.Birds) if (H.InRoost(B) || Chebyshev(B, H.Whistler) <= ScareRange) { std::printf("FAIL birds start outside the roost and out of reach\n"); ++Fails; break; }
	return Fails;
}

/** Iteration 2: 600 random yards walked with random legal moves; every state must satisfy the rules' invariants. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0;
	const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff);
			std::uint32_t Pick = Seed * 2654435761u + 13u;
			while (!G.Over)
			{
				std::vector<Move> Legal;
				for (int I = 0; I < MoveCount; ++I)
				{
					const Move M = static_cast<Move>(I);
					const Cell X{ G.Whistler.R + MoveDR(M), G.Whistler.C + MoveDC(M) };
					if (G.Inside(X) && G.BirdAt(X) < 0) Legal.push_back(M);
				}
				if (Legal.empty()) { std::printf("FAIL sweep: no legal move (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				Pick = Pick * 1664525u + 1013904223u;
				const Move M = Legal[(Pick >> 16) % Legal.size()];
				const int TurnsBefore = G.Turns, SettledBefore = G.Settled; const size_t BirdsBefore = G.Birds.size();
				int Flew = 0, Perched = 0; std::string Text;
				if (G.Step(M, Flew, Perched, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal move refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = G.Turns == TurnsBefore - 1 && G.Settled == SettledBefore + Perched && G.Birds.size() + static_cast<size_t>(Perched) == BirdsBefore
				          && G.Settled + static_cast<int>(G.Birds.size()) == G.Diff->Birds && Flew >= Perched && G.BirdAt(G.Whistler) < 0;
				for (size_t A = 0; A < G.Birds.size() && Ok; ++A)
				{
					if (!G.Inside(G.Birds[A]) || G.InRoost(G.Birds[A])) Ok = false;
					for (size_t B = A + 1; B < G.Birds.size(); ++B) if (G.Birds[A] == G.Birds[B]) Ok = false;
				}
				Ok = Ok && G.Over == (G.Birds.empty() || G.Turns <= 0) && G.Won == G.Birds.empty();
				Ok = Ok && (G.Over ? G.Score == BirdScore * G.Settled + (G.Won ? G.Turns : 0) : G.Score == 0);
				if (!Ok) { std::printf("FAIL sweep invariant (seed %u %s turns %d): %s\n", Seed, Diff, G.Turns, Text.c_str()); ++Fails; break; }
			}
			int Flew = 0, Perched = 0; std::string Text;
			if (G.Step(Move::Wait, Flew, Perched, Text) != Game::Act::GameOver) { std::printf("FAIL sweep: finished yard accepted a move\n"); ++Fails; }
		}
	if (!Fails) std::printf("sweep: 600 yards, %d random legal moves, invariants held\n", Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: roostcall_core_test roostcall_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks() + InvariantSweep(), Games = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; int Turn = 0; bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Turn = 0; Skip = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skip = true; continue; }
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL yard differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Move M = G.DemoAction();
			int Flew = 0, Perched = 0; std::string Result;
			const Game::Act R = G.Step(M, Flew, Perched, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, M, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " settled=" << G.Settled << " turns=" << G.Turns;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s roostcall: %d yards regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
