// SPDX-License-Identifier: MIT
// Shardscale parity: DaedalusShardscaleCore.h must regenerate every line in shardscale_parity.txt from seed + difficulty
// alone (CPython-compatible seeding, redraw-until-solvable) and weigh the same way turn for turn.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shardscale_core_test.cpp -o shardscale_core_test && ./shardscale_core_test shardscale_parity.txt
#include "DaedalusShardscaleCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::shardscale;

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
	O << "game s=" << Seed << " d=" << Diff << " shards=" << G.Diff->Shards << " cap=" << G.Diff->Cap << " tol=" << G.Diff->Tolerance << " bench=" << G.Diff->Bench << " line=" << G.LineString();
	return O.str();
}

std::string MoveLine(int Turn, const Action& A, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << ActionText(A) << " index=" << G.Index << " left=" << G.Left << " right=" << G.Right << " held=" << G.HeldString() << " used=" << G.BenchUsed
	  << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set line for rule checks. */
Game Lay(const std::vector<int>& Line, int Cap, int Tolerance, int BenchSize)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", static_cast<int>(Line.size()), Cap, Tolerance, BenchSize };
	G.Diff = &Custom; G.Line = Line; G.Index = G.Left = G.Right = G.BenchUsed = 0; G.Held = Bench{}; G.Tipped = false; G.Score = 0; G.Over = G.Won = false;
	return G;
}

const Action L{ Kind::Left, Action::Next }, R{ Kind::Right, Action::Next }, H{ Kind::Hold, Action::Next };

int UnitChecks()
{
	int Fails = 0; std::string Text;
	{
		Game G = Lay({ 3, 4, 2 }, 5, 1, 2);
		G.Step(L, Text);
		if (G.Left != 3 || G.Index != 1 || Text != "left 3: pans 3/0") { std::printf("FAIL left places the next shard\n"); ++Fails; }
		G.Step(H, Text);
		if (G.Held.N != 1 || G.Held.W[0] != 4 || G.BenchUsed != 1 || Text != "hold 4: bench [4]") { std::printf("FAIL hold benches the next shard\n"); ++Fails; }
		G.Step(R, Text);
		if (G.Over) { std::printf("FAIL a benched shard still has to be placed\n"); ++Fails; }
		G.Step({ Kind::Right, 0 }, Text);
		if (!G.Over || G.Won || G.Right != 6 || Text.find("askew") == std::string::npos) { std::printf("FAIL placing the benched shard ends the weighing\n"); ++Fails; }
	}
	{
		Game G = Lay({ 9, 1 }, 5, 1, 2);
		G.Step(L, Text);
		if (!G.Over || G.Won || !G.Tipped || Text.find("tips") == std::string::npos || G.Score != 0) { std::printf("FAIL a tip loses at once\n"); ++Fails; }
		if (G.Step(R, Text) != Game::Act::GameOver) { std::printf("FAIL a finished weighing refuses actions\n"); ++Fails; }
	}
	{
		Game G = Lay({ 4, 4 }, 5, 1, 2);
		G.Step(L, Text); G.Step(R, Text);
		if (!G.Won || G.Score != WinScore + SlackScore + 2 * BenchScore) { std::printf("FAIL level with slack and unused bench scores\n"); ++Fails; }
		Game B = Lay({ 4, 3 }, 5, 1, 1);
		B.Step(H, Text); B.Step(L, Text); B.Step({ Kind::Right, 0 }, Text);
		if (!B.Won || B.Score != WinScore) { std::printf("FAIL level at the tolerance with the bench used scores the base\n"); ++Fails; }
	}
	{
		Game G = Lay({ 3, 4, 2 }, 5, 1, 1);
		G.Step(H, Text);
		if (G.Step(H, Text) != Game::Act::Illegal || G.Step({ Kind::Left, 1 }, Text) != Game::Act::Illegal || G.Step({ Kind::Right, 5 }, Text) != Game::Act::Illegal) { std::printf("FAIL illegal actions are refused\n"); ++Fails; }
	}
	{
		Action A;
		if (!ActionFromText("l", A) || !(A == L) || !ActionFromText("r2", A) || !(A == Action{ Kind::Right, 2 }) || !ActionFromText("hold", A) || !(A == H) || ActionFromText("lx", A)) { std::printf("FAIL action text round trip\n"); ++Fails; }
	}
	return Fails;
}

/** Iteration 2: random legal actions on every seeded line; bookkeeping, preview and end conditions must hold. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0, Lines = 0;
	static const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff); ++Lines;
			std::uint32_t Pick = Seed * 2654435761u + 7u;
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				std::array<Action, 3 + 2 * MaxBench> Acts{};
				const int Count = G.Actions(Acts);
				if (Count == 0) { std::printf("FAIL sweep: no legal action (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const Action A = Acts[static_cast<size_t>((Pick >> 16) % static_cast<std::uint32_t>(Count))];
				int After = 0; bool Tips = false, Ends = false;
				if (!G.Preview(A, After, Tips, Ends)) { std::printf("FAIL sweep: preview refused a legal action (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const int Placed = G.Left + G.Right, HeldSum = [&] { int S = 0; for (int I = 0; I < G.Held.N; ++I) S += G.Held.W[static_cast<size_t>(I)]; return S; }();
				std::string Text;
				if (G.Step(A, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal action refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				int LineSum = 0; for (int I = 0; I < G.Index; ++I) LineSum += G.Line[static_cast<size_t>(I)];
				int NewHeld = 0; for (int I = 0; I < G.Held.N; ++I) NewHeld += G.Held.W[static_cast<size_t>(I)];
				const bool Ok = G.Difference() == After && Tips == G.Tipped && (!Tips || G.Over) && (Ends == (G.Over && !G.Tipped) || Tips)
				                && G.Left + G.Right + NewHeld == LineSum && (Placed + HeldSum <= LineSum) && G.Held.N <= G.Diff->Bench && G.BenchUsed >= G.Held.N
				                && (G.Tipped || std::abs(G.Difference()) <= G.Diff->Cap);
				if (!Ok) { std::printf("FAIL sweep: invariant broke (seed %u %s step %d)\n", Seed, Diff, Steps); ++Fails; break; }
				if (G.Over && G.Won != (!G.Tipped && G.Remaining() == 0 && std::abs(G.Difference()) <= G.Diff->Tolerance)) { std::printf("FAIL sweep: win flag (seed %u %s)\n", Seed, Diff); ++Fails; break; }
			}
		}
	std::printf("sweep: %d lines, %d random actions, invariants held\n", Lines, Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shardscale_core_test shardscale_parity.txt\n"); return 2; }
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
			if (Got != Line) { std::printf("FAIL line differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Action A = G.DemoAction();
			std::string Result;
			const Game::Act R2 = G.Step(A, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, A, G, Result);
			if (R2 != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " left=" << G.Left << " right=" << G.Right;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s shardscale: %d lines regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
