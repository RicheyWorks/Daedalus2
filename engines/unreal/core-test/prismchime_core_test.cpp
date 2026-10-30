// SPDX-License-Identifier: MIT
// Prismchime Ring parity: DaedalusPrismchimeCore.h must regenerate every ring in prismchime_parity.txt from seed +
// difficulty alone (CPython-compatible seeding) and replay every demo tap byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public prismchime_core_test.cpp -o prismchime_core_test && ./prismchime_core_test prismchime_parity.txt
#include "DaedalusPrismchimeCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::prismchime;

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
	O << "game s=" << Seed << " d=" << Diff << " taps=" << G.Taps << " charge=" << G.ChargeString() << " facing=" << G.FacingString();
	return O.str();
}

std::string MoveLine(int Turn, int I, int Pealed, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " tap=" << I << " pealed=" << Pealed << " score=" << G.Score << " taps=" << G.Taps << " lit=" << G.LitString()
	  << " charge=" << G.ChargeString() << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** Hand-set ring for rule checks; the seed only matters for Start(). */
Game Fixed(std::vector<int> Charge, int Facing, int Taps)
{
	Game G; G.Start(1, "easy");
	G.Charge = Charge; G.Facing.assign(Charge.size(), Facing); G.Lit.assign(Charge.size(), false); G.Taps = Taps;
	return G;
}

int UnitChecks()
{
	int Fails = 0, Pealed = 0; std::string Text;
	Game G = Fixed({ 2, 0, 0, 0, 0, 0 }, 1, 6);
	if (G.Tap(0, Pealed, Text) != Game::Act::Ok || G.ChargeString() != "3,1,1,0,0,0" || Text != "tap 0: 0 peal(s)") { std::printf("FAIL tap pulses along the facing and resonates (%s | %s)\n", G.ChargeString().c_str(), Text.c_str()); ++Fails; }
	G = Fixed({ 2, 0, 0, 0, 0, 0 }, -1, 6); G.Tap(0, Pealed, Text);
	if (G.ChargeString() != "3,0,0,0,1,1") { std::printf("FAIL counter facing wraps the other way (%s)\n", G.ChargeString().c_str()); ++Fails; }
	G = Fixed({ 3, 0, 0, 0, 0, 0 }, 1, 6); G.Tap(0, Pealed, Text);
	if (Pealed != 1 || G.ChargeString() != "0,2,1,1,0,1" || G.LitString() != "100000" || G.Score != PealScore || G.Taps != 5) { std::printf("FAIL a peal lights, resets and charges both neighbours (%s)\n", G.ChargeString().c_str()); ++Fails; }
	G = Fixed({ 3, 3, 3, 0, 0, 0 }, 1, 6); G.Tap(0, Pealed, Text);
	if (Pealed != 3 || G.ChargeString() != "0,2,0,2,0,1" || G.LitString() != "111000") { std::printf("FAIL peals chain in fill order (%s %s)\n", G.ChargeString().c_str(), G.LitString().c_str()); ++Fails; }
	G = Fixed({ 3, 3, 3, 3, 3, 3 }, 1, 4); G.Tap(0, Pealed, Text);
	if (!G.Over || !G.Won || G.Score != 6 * PealScore + 3 * TapBonus || Text.find("every chime rings") == std::string::npos) { std::printf("FAIL a full ring wins with the tap bonus (score %d)\n", G.Score); ++Fails; }
	G = Fixed({ 1, 1, 1, 1, 1, 1 }, 1, 1); G.Tap(0, Pealed, Text);
	if (!G.Over || G.Won || Text.find("falls silent") == std::string::npos) { std::printf("FAIL the last tap without a full ring loses\n"); ++Fails; }
	if (G.Tap(0, Pealed, Text) != Game::Act::GameOver) { std::printf("FAIL a finished ring refuses taps\n"); ++Fails; }
	Game H; if (H.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!H.Start(7, "hard") || H.Chimes() != 10 || H.Taps != 8) { std::printf("FAIL hard start\n"); ++Fails; }
	for (int C : H.Charge) if (C < 1 || C > 2) { std::printf("FAIL start charges are 1 or 2\n"); ++Fails; break; }
	if (H.Tap(99, Pealed, Text) != Game::Act::BadChime) { std::printf("FAIL out-of-range chime accepted\n"); ++Fails; }
	return Fails;
}

/** Iteration 2: 600 random rings played with random taps; every state must satisfy the rules' invariants. */
int InvariantSweep()
{
	int Fails = 0, Taps = 0;
	const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff);
			std::uint32_t Pick = Seed * 2654435761u + 7u;   // a cheap independent stream for the tap choice
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				const int I = static_cast<int>(Pick >> 16) % G.Chimes();
				const int TapsBefore = G.Taps, LitBefore = G.LitCount(), PealsBefore = G.Peals;
				int PreviewPealed = 0, PreviewLit = 0; G.Preview(I, PreviewPealed, PreviewLit);
				int Pealed = 0; std::string Text;
				if (G.Tap(I, Pealed, Text) != Game::Act::Ok) { std::printf("FAIL sweep: tap refused mid-game (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Taps;
				bool Ok = G.Taps == TapsBefore - 1 && G.Peals - PealsBefore == Pealed && G.LitCount() >= LitBefore && G.LitCount() - LitBefore <= Pealed;
				if (PreviewPealed != Pealed || PreviewLit != G.LitCount() - LitBefore) { std::printf("FAIL preview differs from the tap (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				for (int C : G.Charge) if (C < 0 || C >= Peal) Ok = false;
				if (G.Score != PealScore * G.Peals + (G.Won ? TapBonus * G.Taps : 0)) Ok = false;
				if (G.Over != (G.AllLit() || G.Taps <= 0) || G.Won != G.AllLit()) Ok = false;
				if (!Ok) { std::printf("FAIL sweep invariant (seed %u %s tap %d): %s\n", Seed, Diff, I, Text.c_str()); ++Fails; break; }
			}
			int Pealed = 0; std::string Text;
			if (G.Tap(0, Pealed, Text) != Game::Act::GameOver) { std::printf("FAIL sweep: finished ring accepted a tap\n"); ++Fails; }
		}
	if (!Fails) std::printf("sweep: 600 rings, %d random taps, invariants held, every preview matched its tap\n", Taps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: prismchime_core_test prismchime_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks() + InvariantSweep(), Games = 0, Vectors = 0;
	std::string Line; Game G; std::uint32_t Seed = 0; std::string Diff; int Turn = 0; bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s"))); Diff = Field(Line, "d"); Turn = 0; Skip = false; ++Games;
			if (!G.Start(Seed, Diff)) { std::printf("FAIL %s: unknown difficulty\n", Line.c_str()); ++Fails; Skip = true; continue; }
			const std::string Got = GameLine(Seed, Diff, G);
			if (Got != Line) { std::printf("FAIL ring differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const int I = G.DemoAction();
			int Pealed = 0; std::string Result;
			const Game::Act R = G.Tap(I, Pealed, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, I, Pealed, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " peals=" << G.Peals;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else if (Line.rfind("vector ", 0) == 0)
		{
			// Hand-set ring: charge / facing / lit / taps replace the seeded state; the next line is one scripted tap.
			Diff = "vector:" + Line.substr(7, Line.find(' ', 7) - 7); Turn = 0; Skip = false; ++Vectors;
			G.Start(1, "easy");
			G.Charge.clear(); for (const std::string& Tok : Split(Field(Line, "charge"), ',')) G.Charge.push_back(std::stoi(Tok));
			G.Facing.clear(); for (const std::string& Tok : Split(Field(Line, "facing"), ',')) G.Facing.push_back(std::stoi(Tok));
			G.Lit.clear(); for (char Ch : Field(Line, "lit")) G.Lit.push_back(Ch == '1');
			G.Taps = std::stoi(Field(Line, "taps"));
		}
		else if (Line.rfind("tap ", 0) == 0)
		{
			if (Skip) continue;
			const int I = std::stoi(Field(Line, "i"));
			int Pealed = 0; std::string Result;
			const Game::Act R = G.Tap(I, Pealed, Result);
			std::ostringstream O;
			O << "tap i=" << I << " pealed=" << Pealed << " score=" << G.Score << " taps=" << G.Taps << " lit=" << G.LitString() << " charge=" << G.ChargeString()
			  << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL %s\n  want %s\n  got  %s\n", Diff.c_str(), Line.c_str(), O.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s prismchime: %d games regenerated from seed, %d edge vectors, %d failures\n", Fails ? "FAIL" : "OK", Games, Vectors, Fails);
	return Fails ? 1 : 0;
}
