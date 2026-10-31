// SPDX-License-Identifier: MIT
// Shuntline parity: DaedalusShuntlineCore.h must regenerate every train in shuntline_parity.txt from seed + difficulty
// alone (CPython-compatible seeding, redraw-until-solvable) and shunt the same way move for move.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shuntline_core_test.cpp -o shuntline_core_test && ./shuntline_core_test shuntline_parity.txt
#include "DaedalusShuntlineCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::shuntline;

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
	O << "game s=" << Seed << " d=" << Diff << " cars=" << G.Cars() << " sidings=" << G.Diff->Sidings << " length=" << G.Diff->Length << " moves=" << G.Diff->Moves << " train=" << G.TrainString();
	return O.str();
}

std::string MoveLine(int Turn, const Action& A, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << ActionText(A) << " index=" << G.Index() << " sidings=" << G.SidingsString() << " outbound=" << G.OutboundString() << " moves=" << G.Moves()
	  << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set yard for rule checks. */
Game Lay(const std::vector<int>& Train, int Sidings, int Length, int Moves, int Destinations)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", static_cast<int>(Train.size()), Destinations, Sidings, Length, Moves };
	G.Diff = &Custom; G.Train = Train; G.State = Yard{}; G.State.Moves = Moves; G.Outbound.clear(); G.Score = 0; G.Over = G.Won = false;
	return G;
}

const Action Out = OutAction, S0{ Kind::Shunt, 0 }, S1{ Kind::Shunt, 1 }, P0{ Kind::Pull, 0 };

int UnitChecks()
{
	int Fails = 0; std::string Text;
	{
		Game G = Lay({ 2, 1, 3 }, 2, 3, 20, 3);
		std::array<Action, 1 + 2 * MaxSidings> Acts{};
		if (G.Actions(Acts) != 3 || !(Acts[0] == Out) || !(Acts[1] == S0) || !(Acts[2] == S1)) { std::printf("FAIL fresh yard actions\n"); ++Fails; }
		G.Step(S0, Text);
		if (G.SidingAt(0).N != 1 || G.Index() != 1 || G.Moves() != 19 || Text != "s0: carriage 2 onto siding 0") { std::printf("FAIL shunt\n"); ++Fails; }
		G.Step(Out, Text);
		if (G.Actions(Acts) != 4 || !(Acts[3] == P0)) { std::printf("FAIL pull becomes legal\n"); ++Fails; }
		G.Step(P0, Text); G.Step(Out, Text);
		if (!G.Won || G.Score != 3 * GroupScore + 16 * MoveBonus || Text.find("made up") == std::string::npos) { std::printf("FAIL the train is made up\n"); ++Fails; }
	}
	{
		Game G = Lay({ 3, 1, 1, 1, 1 }, 1, 2, 20, 3);
		G.Step(Out, Text);
		std::array<Action, 1 + 2 * MaxSidings> Acts{};
		if (G.Actions(Acts) != 1 || !(Acts[0] == S0)) { std::printf("FAIL a lower tag may not leave after a higher one\n"); ++Fails; }
		G.Step(S0, Text); G.Step(S0, Text);
		if (!G.Over || G.Won || Text.find("blocked") == std::string::npos) { std::printf("FAIL the yard blocks\n"); ++Fails; }
		if (G.Step(Out, Text) != Game::Act::GameOver) { std::printf("FAIL a finished yard refuses moves\n"); ++Fails; }
	}
	{
		Game G = Lay({ 1, 2 }, 2, 3, 1, 2);
		G.Step(Out, Text);
		if (!G.Over || G.Won || G.Score != GroupScore || Text.find("shift ends") == std::string::npos) { std::printf("FAIL the shift ends\n"); ++Fails; }
		Game H = Lay({ 1 }, 1, 1, 5, 1);
		if (H.Step(P0, Text) != Game::Act::Illegal) { std::printf("FAIL illegal pull refused\n"); ++Fails; }
	}
	{
		Action A;
		if (!ActionFromText("out", A) || !(A == Out) || !ActionFromText("s1", A) || !(A == S1) || !ActionFromText("p0", A) || !(A == P0) || ActionFromText("q2", A)) { std::printf("FAIL action text round trip\n"); ++Fails; }
	}
	return Fails;
}

/** Iteration 2: random legal actions on every seeded train; order, lengths, counts and end conditions must hold. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0, Trains = 0;
	static const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff); ++Trains;
			std::uint32_t Pick = Seed * 2654435761u + 7u;
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				std::array<Action, 1 + 2 * MaxSidings> Acts{};
				const int N = G.Actions(Acts);
				if (N == 0) { std::printf("FAIL sweep: live yard with no legal move (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const Action A = Acts[static_cast<size_t>((Pick >> 16) % static_cast<std::uint32_t>(N))];
				int Car = 0; bool Leaves = false;
				if (!G.Preview(A, Car, Leaves)) { std::printf("FAIL sweep: preview refused a legal move (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const size_t OutBefore = G.Outbound.size(); const int MovesBefore = G.Moves();
				std::string Text;
				if (G.Step(A, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal move refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = G.Moves() == MovesBefore - 1 && G.Outbound.size() == OutBefore + (Leaves ? 1 : 0) && (!Leaves || G.Outbound.back() == Car);
				for (size_t I = 1; I < G.Outbound.size() && Ok; ++I) Ok = G.Outbound[I - 1] <= G.Outbound[I];
				int Parked = 0; for (int S = 0; S < G.Diff->Sidings; ++S) { Parked += G.SidingAt(S).N; if (G.SidingAt(S).N > G.Diff->Length) Ok = false; }
				Ok = Ok && static_cast<int>(G.Outbound.size()) + Parked == G.Index();
				if (!Ok) { std::printf("FAIL sweep: invariant broke (seed %u %s step %d)\n", Seed, Diff, Steps); ++Fails; break; }
				if (G.Over && G.Won != (static_cast<int>(G.Outbound.size()) == G.Cars())) { std::printf("FAIL sweep: win flag (seed %u %s)\n", Seed, Diff); ++Fails; break; }
			}
		}
	std::printf("sweep: %d trains, %d random moves, invariants held\n", Trains, Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shuntline_core_test shuntline_parity.txt\n"); return 2; }
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
			if (Got != Line) { std::printf("FAIL train differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Action A = G.DemoAction();
			std::string Result;
			const Game::Act R = G.Step(A, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, A, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " out=" << G.Outbound.size() << " moves=" << G.Moves();
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s shuntline: %d trains regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
