// SPDX-License-Identifier: MIT
// Lumenpath Refraction parity: DaedalusLumenpathCore.h must regenerate every lattice in lumenpath_parity.txt from
// seed + difficulty alone (CPython-compatible seeding) and replay every demo move byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public lumenpath_core_test.cpp -o lumenpath_core_test && ./lumenpath_core_test lumenpath_parity.txt
#include "DaedalusLumenpathCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::lumenpath;

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
	O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " src=" << G.SourceRow << " moves=" << G.Moves << " lit=" << G.Lit
	  << " grid=" << G.GridString() << " crystals=";
	for (size_t I = 0; I < G.Crystals.size(); ++I) O << (I ? ";" : "") << G.Crystals[I].first << "," << G.Crystals[I].second;
	O << " solution=";
	for (size_t I = 0; I < G.Solution.size(); ++I) O << (I ? ";" : "") << G.Solution[I].R << "," << G.Solution[I].C << "," << G.Solution[I].M;
	return O.str();
}

std::string MoveLine(int Turn, int R, int C, int Gained, const Game& G)
{
	std::ostringstream O;
	O << "move t=" << Turn << " r=" << R << " c=" << C << " gained=" << Gained << " score=" << G.Score << " lit=" << G.Lit << " moves=" << G.Moves
	  << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " grid=" << G.GridString();
	return O.str();
}

int UnitChecks()
{
	int Fails = 0;
	std::vector<std::string> Grid = { "...", "/.*", "..." };
	const std::vector<Cell> P = Trace(Grid, 1);
	if (P.size() != 2 || P[0] != Cell{ 1, 0 } || P[1] != Cell{ 0, 0 }) { std::printf("FAIL trace turns north on '/' (got %zu cells)\n", P.size()); ++Fails; }
	Grid = { "...", "\\.*", "..." };
	const std::vector<Cell> Q = Trace(Grid, 1);
	if (Q.size() != 2 || Q[1] != Cell{ 2, 0 }) { std::printf("FAIL trace turns south on '\\\\'\n"); ++Fails; }
	Grid = { "..#", "...", "..." };
	if (Trace(Grid, 0).size() != 2) { std::printf("FAIL cracked stone stops the beam\n"); ++Fails; }
	Game G; if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(0, "easy") || G.Size() != 5 || G.Over) { std::printf("FAIL easy start\n"); ++Fails; }
	int Gained = 0;
	if (G.Toggle(99, 0, Gained) != Game::Act::BadCell) { std::printf("FAIL out-of-range cell accepted\n"); ++Fails; }
	const Cell K = G.Crystals.front();
	if (G.Toggle(K.first, K.second, Gained) != Game::Act::BadCell) { std::printf("FAIL crystal cell accepted a mirror\n"); ++Fails; }
	// Round 2 (prometheus 2): a stray mirror off the solution is the hint's first target, so the hint can undo it.
	for (std::uint32_t Seed = 0; Seed < 20; ++Seed)
	{
		Game H; H.Start(Seed, "normal");
		Cell Stray{ -1, -1 };
		for (int I = 0; I < H.Size() && Stray.first < 0; ++I)
			for (int J = 0; J < H.Size() && Stray.first < 0; ++J)
			{
				bool Mine = false;
				for (const Mirror& M : H.Solution) Mine = Mine || (M.R == I && M.C == J);
				if (!Mine && H.Grid[static_cast<size_t>(I)][static_cast<size_t>(J)] == '.') Stray = { I, J };
			}
		H.Toggle(Stray.first, Stray.second, Gained);
		if (!H.Over && H.DemoAction() != Stray) { std::printf("FAIL seed %u: hint does not clear the stray mirror first\n", Seed); ++Fails; }
	}
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: lumenpath_core_test lumenpath_parity.txt\n"); return 2; }
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
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL lattice differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Cell A = G.DemoAction();
			int Gained = 0;
			const Game::Act R = G.Toggle(A.first, A.second, Gained);
			++Turn;
			const std::string Got = MoveLine(Turn, A.first, A.second, Gained, G);
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
	std::printf("%s lumenpath: %d games regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
