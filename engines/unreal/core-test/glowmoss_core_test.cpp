// SPDX-License-Identifier: MIT
// Glowmoss Delve parity: DaedalusGlowmossCore.h must regenerate every shaft in glowmoss_parity.txt (crystals,
// darkness, glowmoss, footing, the exact best delve's target and plan) from seed + difficulty alone (CPython-compatible
// seeding) and replay every demo dig, hint and mid-shaft probe byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public glowmoss_core_test.cpp -o glowmoss_core_test && ./glowmoss_core_test glowmoss_parity.txt
#include "DaedalusGlowmossCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::glowmoss;

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

std::string GridString(const Grid& Rows)
{
	std::string S;
	for (size_t R = 0; R < Rows.size(); ++R)
	{
		if (R) S += "/";
		for (int X : Rows[R]) S += std::to_string(X);
	}
	return S;
}

std::string ActString(const Action& A)
{
	return A.K == Kind::Climb ? "climb" : "dig:" + std::to_string(A.Col);
}

std::string StateString(const Game& G)
{
	std::ostringstream O;
	O << "row=" << G.Row << " col=" << G.Col << " light=" << G.Light << " crystals=" << G.Crystals << " score=" << G.Score << " path=" << Ints(G.Path)
	  << " hint=" << (G.Over ? std::string("-") : ActString(G.Hint()));
	return O.str();
}

std::string Opening(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	return "game s=" + std::to_string(Seed) + " d=" + Diff + " code=" + SeedCode(Seed, *G.Diff) + " gems=" + GridString(G.Cells.Gems) + " dark=" + GridString(G.Cells.Dark)
		+ " moss=" + GridString(G.Cells.Moss) + " unstable=" + GridString(G.Cells.Unstable) + " best=" + std::to_string(G.Best) + " target=" + std::to_string(G.Target) + " plan=" + Ints(G.Plan) + " " + StateString(G);
}

int UnitChecks()
{
	int Fails = 0;
	if (ClimbCost(Surface) != 0 || ClimbCost(0) != 1 || ClimbCost(1) != 1 || ClimbCost(2) != 2 || ClimbCost(4) != 3) { std::printf("FAIL climb cost\n"); ++Fails; }
	if (FirstDigCol(0) != 0 || LastDigCol(3, 4) != 3 || FirstDigCol(2) != 1 || LastDigCol(2, 4) != 3) { std::printf("FAIL dig reach\n"); ++Fails; }
	const Difficulty Tiny{ "tiny", 2, 3, 6, 3, 0, 0, 100 };
	if (AfterDig(6, Tiny, 2, false) != 3 || AfterDig(6, Tiny, 0, true) != 6 || AfterDig(1, Tiny, 1, true) != 2) { std::printf("FAIL after dig\n"); ++Fails; }
	// Same shafts as test_glowmoss.test_best_delve_exact and test_unstable_ledge_falls.
	const Grid Flat{ { 0, 0 }, { 0, 0 }, { 0, 0 } };
	Shaft S{ { { 1, 9 }, { 5, 1 }, { 1, 1 } }, { { 0, 2 }, { 0, 0 }, { 0, 0 } }, Flat, Flat };
	const Delve Dry = BestDelve(Tiny, S);
	if (Dry.Best != 14 || Dry.Plan != std::vector<int>{ 1, 0 }) { std::printf("FAIL best delve\n"); ++Fails; }
	S.Moss[0][1] = 1;
	const Delve Mossy = BestDelve(Tiny, S);
	if (Mossy.Best != 15 || Mossy.Plan != std::vector<int>{ 1, 0, 0 }) { std::printf("FAIL best delve with glowmoss\n"); ++Fails; }
	S.Moss[0][1] = 0;
	Difficulty Dim = Tiny; Dim.Light = 1;
	if (BestDelve(Dim, S).Best != 0 || !BestDelve(Dim, S).Plan.empty()) { std::printf("FAIL unreachable shaft\n"); ++Fails; }
	S.Unstable[0][1] = 1;
	const Landing Fall = Land(Tiny, S, 0, 1, 6);
	if (Fall.Row != 1 || Fall.Light != 3 || Fall.Got != 10 || !Fall.Fell || Fall.Mossy) { std::printf("FAIL unstable fall\n"); ++Fails; }
	S.Unstable[2][0] = 1;
	if (Land(Tiny, S, 2, 0, 6).Fell) { std::printf("FAIL fall below the floor\n"); ++Fails; }

	Game G; std::string Res;
	if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(1, "hard") || G.Cells.Unstable.size() != 12 || G.Col != 2 || G.Light != 10 || G.Target < 1 || G.Target > G.Best) { std::printf("FAIL hard start\n"); ++Fails; }
	if (G.Step({ Kind::Dig, G.Col + 2 }, Res) != Game::Act::OutOfReach) { std::printf("FAIL far dig accepted\n"); ++Fails; }
	G.Row = G.Diff->Rows - 1;
	if (G.Step({ Kind::Dig, G.Col }, Res) != Game::Act::Floor || G.Hint().K != Kind::Climb) { std::printf("FAIL dig through the floor\n"); ++Fails; }

	std::uint32_t CodeSeed = 0; const Difficulty* CodeDiff = nullptr;
	if (SeedCode(1337, *FindDifficulty("normal")) != "GLOW-N-1337" || !ParseSeedCode("  glow-h-42 ", CodeSeed, CodeDiff) || CodeSeed != 42 || CodeDiff != FindDifficulty("hard"))
	{
		std::printf("FAIL seed code round trip\n"); ++Fails;
	}
	for (const char* Bad : { "x", "GLOW-Q-1", "GLOW-N-", "GLOW-N-1x", "GLOWN-1", "GLOW-N-1234567890" })
	{
		if (ParseSeedCode(Bad, CodeSeed, CodeDiff)) { std::printf("FAIL bad seed code accepted: %s\n", Bad); ++Fails; }
	}
	if (DailySeed(2026, 10, 30) != 20261030u) { std::printf("FAIL daily seed\n"); ++Fails; }
	G.Start(3, "normal");
	const size_t Mid = static_cast<size_t>(G.Col);
	G.Light = 1 + G.Cells.Dark[0][Mid];
	G.Cells.Moss[0][Mid] = 0;
	G.Cells.Unstable[0][Mid] = 0;
	if (G.Step({ Kind::Dig, G.Col }, Res) != Game::Act::Ok || Res != "the lamp gutters out" || !G.Over || G.Won) { std::printf("FAIL guttering\n"); ++Fails; }
	if (G.Step({ Kind::Climb, 0 }, Res) != Game::Act::GameOver) { std::printf("FAIL move after game over\n"); ++Fails; }
	G.Start(4, "normal");
	if (G.Step({ Kind::Climb, 0 }, Res) != Game::Act::Ok || Res != "climbed out with 0" || G.Won || G.Score != 0) { std::printf("FAIL empty climb\n"); ++Fails; }
	G.Start(5, "easy");
	while (!G.Over) G.Step(G.DemoAction(), Res);
	if (!G.Won || !G.Perfect || G.Score != G.Crystals + G.Light + PerfectBonus) { std::printf("FAIL perfect delve bonus\n"); ++Fails; }
	return Fails;
}

/** Invariants every shaft keeps, swept over seeds beyond the fixture (mirrors test_glowmoss.Properties). */
int PropertySweep(int& Shafts)
{
	constexpr std::uint32_t SweepSeeds = 200;
	int Fails = 0;
	for (int I = 0; I < DifficultyCount; ++I)
	{
		const std::string Name = Difficulties()[I].Name;
		for (std::uint32_t Seed = 0; Seed < SweepSeeds; ++Seed)
		{
			++Shafts;
			Game G, Twin; std::string Res;
			G.Start(Seed, Name);
			Twin.Start(Seed, Name);
			std::uint32_t CodeSeed = 0; const Difficulty* CodeDiff = nullptr;
			const bool Same = G.Cells.Gems == Twin.Cells.Gems && G.Cells.Unstable == Twin.Cells.Unstable && G.Plan == Twin.Plan && G.Target == Twin.Target;
			const bool Code = ParseSeedCode(SeedCode(Seed, *G.Diff), CodeSeed, CodeDiff) && CodeSeed == Seed && CodeDiff == G.Diff;
			bool HintsMatch = true;
			while (!G.Over)
			{
				const Action A = G.DemoAction();
				const Action H = G.Hint();
				HintsMatch = HintsMatch && H.K == A.K && H.Col == A.Col;
				G.Step(A, Res);
			}
			if (!Same || !Code || !HintsMatch || G.Target < 1 || G.Target > G.Best || !G.Won || !G.Perfect || G.Crystals != G.Best)
			{
				std::printf("FAIL property s=%u %s same=%d code=%d hints=%d target=%d best=%d won=%d\n", Seed, Name.c_str(), Same, Code, HintsMatch, G.Target, G.Best, G.Won);
				++Fails;
			}
		}
	}
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: glowmoss_core_test glowmoss_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Swept = 0;
	int Fails = UnitChecks() + PropertySweep(Swept), Games = 0;
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
		else if (Line.rfind("probe ", 0) == 0)
		{
			if (Skip) continue;
			const int C = std::stoi(Field(Line, "c"));
			const Delve Probe = BestDelve(*G.Diff, G.Cells, { C, C, G.Diff->Light - 1 - C });
			const std::string Got = "probe c=" + std::to_string(C) + " best=" + std::to_string(Probe.Best) + " plan=" + Ints(Probe.Plan);
			if (Got != Line) { std::printf("FAIL s=%u %s probe\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), Got.c_str()); ++Fails; }
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
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " perfect=" << (G.Perfect ? 1 : 0);
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s glowmoss: %d shafts regenerated from seed, %d swept for invariants, %d failures\n", Fails ? "FAIL" : "OK", Games, Swept, Fails);
	return Fails ? 1 : 0;
}
