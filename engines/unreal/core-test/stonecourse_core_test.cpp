// SPDX-License-Identifier: MIT
// Stonecourse parity: DaedalusStonecourseCore.h must regenerate every supply in stonecourse_parity.txt from seed +
// difficulty alone (CPython-compatible seeding, redraw-until-solvable) and lay the same wall turn for turn.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stonecourse_core_test.cpp -o stonecourse_core_test && ./stonecourse_core_test stonecourse_parity.txt
#include "DaedalusStonecourseCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::stonecourse;

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
	O << "game s=" << Seed << " d=" << Diff << " width=" << G.Width() << " courses=" << G.Courses() << " skips=" << G.Diff->Skips << " stones=" << G.StonesString();
	return O.str();
}

std::string MoveLine(int Turn, int Action, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << ActionText(Action) << " index=" << G.Index << " wall=" << G.WallString() << " locked=" << G.Locked << " skips=" << G.SkipsLeft
	  << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set wall for rule checks: rows from the footing, '0'/'1'. */
Game Lay(const std::vector<int>& Stones, int Width, const std::vector<std::string>& Rows, int Skips)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", Width, static_cast<int>(Rows.size()), static_cast<int>(Stones.size()), Skips };
	G.Diff = &Custom; G.Stones = Stones; G.Cells.clear();
	for (const std::string& Row : Rows) G.Cells += Row;
	G.Index = 0; G.Locked = 0; for (int K = 0; K < G.Courses(); ++K) if (G.CourseFull(K)) ++G.Locked;
	G.SkipsLeft = Skips; G.Score = 0; G.Over = G.Won = false;
	return G;
}

std::vector<int> ParseInts(const std::string& Text)
{
	std::vector<int> Out;
	if (Text == "-") return Out;
	std::stringstream S(Text); std::string Item;
	while (std::getline(S, Item, ',')) Out.push_back(std::stoi(Item));
	return Out;
}
std::vector<std::string> SplitRows(const std::string& Text)
{
	std::vector<std::string> Rows;
	std::stringstream S(Text); std::string Row;
	while (std::getline(S, Row, ';')) Rows.push_back(Row);
	return Rows;
}

int UnitChecks()
{
	int Fails = 0; std::string Text;
	{
		Game G = Lay({ 2, 2, 1, 3 }, 5, { "00000", "00000", "00000" }, 1);
		if (G.Landing(0) != 0) { std::printf("FAIL footing supports the first stone\n"); ++Fails; }
		G.Step(0, Text);
		if (G.Landing(0) != 1 || G.Landing(1) != -1) { std::printf("FAIL a stone rests only on full support\n"); ++Fails; }
		G.Step(2, Text);
		std::array<int, MaxWallWidth> Cols{};
		if (G.Placements(Cols) != 5) { std::printf("FAIL a 1-stone rests anywhere on the open footing or a filled cell\n"); ++Fails; }
		G.Step(4, Text);
		if (G.Locked != 1 || G.Score != CourseScore || Text.find("the course locks") == std::string::npos) { std::printf("FAIL a full course locks\n"); ++Fails; }
	}
	{
		Game G = Lay({ 3, 3 }, 5, { "11011", "00000" }, 1);
		std::array<int, MaxWallWidth> Cols{};
		if (G.Placements(Cols) != 0 || G.Step(0, Text) != Game::Act::NoRest || G.Step(7, Text) != Game::Act::NoRest || G.Index != 0) { std::printf("FAIL gaps and overhang are refused\n"); ++Fails; }
		G.Step(Skip, Text);
		if (!G.Over || G.Won || G.SkipsLeft != 0 || Text.find("fits nowhere") == std::string::npos) { std::printf("FAIL no placement and no skips ends the build\n"); ++Fails; }
		if (G.Step(Skip, Text) != Game::Act::GameOver) { std::printf("FAIL a finished build refuses actions\n"); ++Fails; }
	}
	{
		Game G = Lay({ 1, 1 }, 3, { "000" }, 1);
		G.Step(0, Text); G.Step(1, Text);
		if (!G.Over || G.Won || Text.find("supply runs out") == std::string::npos) { std::printf("FAIL the supply runs out\n"); ++Fails; }
		Game F = Lay({ 3, 2, 1 }, 3, { "000" }, 2);
		F.Step(0, Text);
		if (!F.Won || F.Score != CourseScore + 2 * StoneBonus + 2 * SkipBonus || Text.find("the wall stands") == std::string::npos) { std::printf("FAIL a finished wall scores the bonuses\n"); ++Fails; }
		Game S = Lay({ 1 }, 3, { "000" }, 0);
		if (S.Step(Skip, Text) != Game::Act::NoSkips) { std::printf("FAIL no skips left\n"); ++Fails; }
	}
	{
		int A = 0;
		if (!ActionFromText("skip", A) || A != Skip || !ActionFromText("4", A) || A != 4 || ActionFromText("x", A) || ActionText(Skip) != "skip" || ActionText(3) != "3") { std::printf("FAIL action text round trip\n"); ++Fails; }
	}
	return Fails;
}

/** Iteration 2: random legal actions on every seeded wall; support, bookkeeping, preview and end conditions must hold. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0, Walls = 0;
	static const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 150 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff); ++Walls;
			std::uint32_t Pick = Seed * 2654435761u + 7u;
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				std::array<int, MaxWallWidth> Cols{};
				const int N = G.Placements(Cols);
				std::vector<int> Legal(Cols.begin(), Cols.begin() + N);
				if (G.SkipsLeft > 0) Legal.push_back(Skip);
				if (Legal.empty()) { std::printf("FAIL sweep: live build with no legal action (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const int A = Legal[(Pick >> 16) % Legal.size()];
				int Course = -1; bool Locks = false;
				if (!G.Preview(A, Course, Locks)) { std::printf("FAIL sweep: preview refused a legal action (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const int LockedBefore = G.Locked, IndexBefore = G.Index, SkipsBefore = G.SkipsLeft;
				std::string Text;
				if (G.Step(A, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal action refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = G.Index == IndexBefore + 1 && G.SkipsLeft == SkipsBefore - (A == Skip ? 1 : 0) && G.Locked == LockedBefore + ((A != Skip && Locks) ? 1 : 0);
				for (int K = 1; K < G.Courses() && Ok; ++K) for (int C = 0; C < G.Width(); ++C) if (G.Filled(K, C) && !G.Filled(K - 1, C)) Ok = false;
				int Full = 0; for (int K = 0; K < G.Courses(); ++K) if (G.CourseFull(K)) ++Full;
				Ok = Ok && Full == G.Locked;
				if (!Ok) { std::printf("FAIL sweep: invariant broke (seed %u %s step %d)\n", Seed, Diff, Steps); ++Fails; break; }
				if (G.Over && G.Won != (G.Locked == G.Courses())) { std::printf("FAIL sweep: win flag (seed %u %s)\n", Seed, Diff); ++Fails; break; }
			}
		}
	std::printf("sweep: %d walls, %d random actions, invariants held\n", Walls, Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: stonecourse_core_test stonecourse_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks() + InvariantSweep(), Games = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; int Turn = 0; bool Skipping = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Turn = 0; Skipping = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skipping = true; continue; }
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL supply differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skipping = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skipping) continue;
			const int A = G.DemoAction();
			std::string Result;
			const Game::Act R = G.Step(A, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, A, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skipping = true; }
		}
		else if (Line.rfind("vector ", 0) == 0)   // iteration 4: hand-set corner cases, scripted action + mason pick
		{
			++Games; Skipping = false; Turn = 0;
			G = Lay(ParseInts(Field(Line, "stones")), std::stoi(Field(Line, "width")), SplitRows(Field(Line, "wall")), std::stoi(Field(Line, "skips")));
			G.Index = std::stoi(Field(Line, "index"));
		}
		else if (Line.rfind("step ", 0) == 0)
		{
			if (Skipping) continue;
			int A = 0, Demo = 0;
			if (!ActionFromText(Field(Line, "act"), A) || !ActionFromText(Field(Line, "demo"), Demo)) { std::printf("FAIL bad step line: %s\n", Line.c_str()); ++Fails; Skipping = true; continue; }
			const int Pick = G.DemoAction();
			if (Pick != Demo) { std::printf("FAIL vector mason: want %s got %s\n  %s\n", ActionText(Demo).c_str(), ActionText(Pick).c_str(), Line.c_str()); ++Fails; }
			std::string Result;
			const Game::Act R = G.Step(A, Result);
			const std::string Tail = MoveLine(0, A, G, Result);
			const std::string Got = "step act=" + Field(Line, "act") + " demo=" + Field(Line, "demo") + Tail.substr(Tail.find(" index="));
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL vector step\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skipping = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skipping) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " locked=" << G.Locked << " index=" << G.Index;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s stonecourse: %d walls regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
