// SPDX-License-Identifier: MIT
// Emberkiln parity: DaedalusEmberkilnCore.h must regenerate every floor in emberkiln_parity.txt from seed + difficulty
// alone (CPython-compatible seeding) and stoke the same demo path coal for coal.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public emberkiln_core_test.cpp -o emberkiln_core_test && ./emberkiln_core_test emberkiln_parity.txt
#include "DaedalusEmberkilnCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::emberkiln;

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
	O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " coals=" << G.Coals << " floor=" << G.FloorString();
	return O.str();
}

std::string MoveLine(int Turn, Cell X, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << X.R << "," << X.C << " heat=" << G.HeatString() << " floor=" << G.FloorString() << " coals=" << G.Coals
	  << " glazed=" << G.GlazedCount << " cracked=" << G.CrackedCount << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set floor for rule checks: rows of digits, 0 stone, 2-4 targets. */
Game Floor(const char* const* Rows, int Size, int Coals)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", Size, 0, Coals };
	G.Diff = &Custom;
	for (auto& Row : G.Target) Row.fill(Stone);
	for (auto& Row : G.Heat) Row.fill(0);
	for (int R = 0; R < Size; ++R) for (int C = 0; C < Size; ++C) G.Target[static_cast<size_t>(R)][static_cast<size_t>(C)] = Rows[R][C] - '0';
	G.Coals = Coals; G.GlazedCount = G.CrackedCount = 0; G.Score = 0; G.Over = G.Won = false;
	return G;
}

int UnitChecks()
{
	int Fails = 0; Outcome Did; std::string Text;
	{
		static const char* Rows[] = { "333", "343", "333" };
		Game G = Floor(Rows, 3, 10);
		G.Step({ 1, 1 }, Did, Text);
		if (G.HeatAt({ 1, 1 }) != 2 || G.HeatAt({ 0, 1 }) != 1 || G.HeatAt({ 1, 0 }) != 1 || G.HeatAt({ 1, 2 }) != 1 || G.HeatAt({ 2, 1 }) != 1 || G.HeatAt({ 0, 0 }) != 0)
		{ std::printf("FAIL a coal heats the tile by two and the four neighbours by one\n"); ++Fails; }
	}
	{
		static const char* Rows[] = { "222", "232", "222" };
		Game G = Floor(Rows, 3, 10);
		G.Step({ 1, 1 }, Did, Text);
		G.Step({ 1, 1 }, Did, Text);
		if (G.TargetAt({ 1, 1 }) != Cracked || G.TargetAt({ 0, 1 }) != Glazed || Did.Glazes != 4 || Did.Cracks != 1 || G.Score != 4 * GlazeScore + CrackScore)
		{ std::printf("FAIL exact heat glazes and overshoot cracks\n"); ++Fails; }
	}
	{
		static const char* Rows[] = { "020", "232", "020" };
		Game G = Floor(Rows, 3, 10);
		G.Step({ 0, 0 }, Did, Text);
		if (G.HeatAt({ 0, 0 }) != 0 || G.HeatAt({ 0, 1 }) != 1 || G.HeatAt({ 1, 0 }) != 1) { std::printf("FAIL stone takes no heat but spreads\n"); ++Fails; }
		G.Step({ 1, 1 }, Did, Text);
		G.Step({ 0, 1 }, Did, Text);
		if (G.TargetAt({ 0, 1 }) != Glazed || G.TargetAt({ 1, 1 }) != Glazed) { std::printf("FAIL a coal on a glazed tile only warms neighbours\n"); ++Fails; }
	}
	{
		static const char* Rows[] = { "20", "00" };
		Game G = Floor(Rows, 2, 3);
		if (G.Step({ 0, 0 }, Did, Text) != Game::Act::Ok || !G.Won || G.Score != GlazeScore + 2 * CoalBonus || Text.find("shines") == std::string::npos)
		{ std::printf("FAIL glazing every tile wins with the coal bonus\n"); ++Fails; }
		if (G.Step({ 0, 0 }, Did, Text) != Game::Act::GameOver || G.Step({ 5, 5 }, Did, Text) != Game::Act::GameOver) { std::printf("FAIL a finished floor refuses coals\n"); ++Fails; }
	}
	{
		static const char* Rows[] = { "44", "44" };
		Game G = Floor(Rows, 2, 1);
		if (G.Step({ 9, 0 }, Did, Text) != Game::Act::OffFloor || G.Coals != 1) { std::printf("FAIL off-floor coals cost nothing\n"); ++Fails; }
		G.Step({ 0, 0 }, Did, Text);
		if (!G.Over || G.Won || Text.find("spent") == std::string::npos) { std::printf("FAIL spent coals lose\n"); ++Fails; }
	}
	return Fails;
}

/** Iteration 2: random legal coals on every seeded floor; the bookkeeping and the preview must hold throughout. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0, Floors = 0;
	static const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff); ++Floors;
			const int Clay = G.Diff->Size * G.Diff->Size - G.Diff->Stone;
			std::uint32_t Pick = Seed * 2654435761u + 7u;
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				const int S = G.Size();
				const Cell X{ static_cast<int>((Pick >> 16) % static_cast<std::uint32_t>(S)), static_cast<int>((Pick >> 8) % static_cast<std::uint32_t>(S)) };
				Outcome Expected; G.Preview(X, Expected);
				const int CoalsBefore = G.Coals, ScoreBefore = G.Score;
				Outcome Did; std::string Text;
				if (G.Step(X, Did, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal coal refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = Did.Glazes == Expected.Glazes && Did.Cracks == Expected.Cracks && G.Coals == CoalsBefore - 1
				          && G.GlazedCount + G.CrackedCount + G.Raw() == Clay
				          && (G.Won ? G.Score >= ScoreBefore : G.Score == ScoreBefore + GlazeScore * Did.Glazes + CrackScore * Did.Cracks);
				for (int R = 0; R < S && Ok; ++R)
					for (int C = 0; C < S && Ok; ++C)
					{
						const int T = G.TargetAt({ R, C }), H = G.HeatAt({ R, C });
						Ok = T == Stone ? H == 0 : T > 0 ? H < T : T == Glazed || T == Cracked;
					}
				if (!Ok) { std::printf("FAIL sweep: invariant broke (seed %u %s step %d)\n", Seed, Diff, Steps); ++Fails; break; }
				if (G.Over && !(G.Raw() == 0 || G.Coals == 0)) { std::printf("FAIL sweep: ended early (seed %u %s)\n", Seed, Diff); ++Fails; break; }
			}
		}
	std::printf("sweep: %d floors, %d random coals, invariants held\n", Floors, Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: emberkiln_core_test emberkiln_parity.txt\n"); return 2; }
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
			if (Got != Line) { std::printf("FAIL floor differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Cell X = G.DemoAction();
			Outcome Did; std::string Result;
			const Game::Act R = G.Step(X, Did, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, X, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " glazed=" << G.GlazedCount << " cracked=" << G.CrackedCount << " coals=" << G.Coals;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s emberkiln: %d floors regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
