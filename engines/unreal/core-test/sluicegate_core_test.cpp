// SPDX-License-Identifier: MIT
// Sluicegate parity: DaedalusSluicegateCore.h must regenerate every field in sluicegate_parity.txt from seed + difficulty
// alone (CPython-compatible seeding) and keep the same gates as the Python gatekeeper, push for push.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public sluicegate_core_test.cpp -o sluicegate_core_test && ./sluicegate_core_test sluicegate_parity.txt
#include "DaedalusSluicegateCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::sluicegate;

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
	O << "game s=" << Seed << " d=" << Diff << " size=" << G.Size() << " turns=" << G.Turns << " gates=" << G.GatesLeft << " head=" << G.Head.R << "," << G.Head.C
	  << " mill=" << (G.Mill == NoCell ? std::string("-") : std::to_string(G.Mill.R) + "," + std::to_string(G.Mill.C)) << " cisterns=" << Game::CellsString(G.Cisterns) << " field=" << G.FieldString();
	return O.str();
}

std::string ActName(Cell X) { return X == NoCell ? "wait" : std::to_string(X.R) + "," + std::to_string(X.C); }

std::string MoveLine(int Turn, Cell X, const Game& G, const std::string& Result)
{
	std::ostringstream O;
	O << "move t=" << Turn << " act=" << ActName(X) << " wet=" << Game::CellsString(G.Wet) << " gates=" << Game::CellsString(G.Gates) << " left=" << G.GatesLeft << " filled=" << G.Filled
	  << " turns=" << G.Turns << " score=" << G.Score << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Result;
	return O.str();
}

/** A hand-set field: rows of '.' channel, '#' rock, 'H' the headgate. */
Game Lay(const std::vector<std::string>& Rows, const std::vector<Cell>& Cisterns, Cell Mill, int Gates, int Turns, int Flow)
{
	Game G; G.Start(1, "easy");
	static Difficulty Custom; Custom = { "custom", static_cast<int>(Rows.size()), static_cast<int>(Cisterns.size()), Gates, Flow, Turns, 0 };
	G.Diff = &Custom;
	for (size_t R = 0; R < Rows.size(); ++R)
		for (size_t C = 0; C < Rows.size(); ++C)
		{
			G.Field[R][C] = Rows[R][C] == '#' ? Rock : Channel;
			if (Rows[R][C] == 'H') G.Head = { static_cast<int>(R), static_cast<int>(C) };
		}
	G.Wet = { G.Head }; G.Cisterns = Cisterns; G.Mill = Mill; G.Gates.clear(); G.GatesLeft = Gates; G.Turns = Turns; G.Filled = 0; G.Score = 0; G.Over = G.Won = false;
	return G;
}

/** `r,c;r,c` → cells; "-" → none. */
std::vector<Cell> ParseCells(const std::string& Text)
{
	std::vector<Cell> Out;
	if (Text == "-") return Out;
	std::stringstream S(Text); std::string Item;
	while (std::getline(S, Item, ';'))
	{
		const size_t Comma = Item.find(',');
		Out.push_back({ std::stoi(Item.substr(0, Comma)), std::stoi(Item.substr(Comma + 1)) });
	}
	return Out;
}

Cell ParseAct(const std::string& Text) { return Text == "wait" ? NoCell : ParseCells(Text).front(); }

std::vector<std::string> SplitRows(const std::string& Text)
{
	std::vector<std::string> Rows;
	std::stringstream S(Text); std::string Row;
	while (std::getline(S, Row, ';')) Rows.push_back(Row);
	return Rows;
}

int UnitChecks()
{
	int Fails = 0; int Reached = 0, Filled = 0; std::string Text;
	{
		Game G = Lay({ "..H..", ".....", ".....", ".....", "....." }, { { 4, 4 } }, NoCell, 4, 10, 2);
		G.Step(NoCell, Reached, Filled, Text);
		if (Reached != 2 || G.Wet.size() != 3 || G.Wet[1] != Cell{ 0, 3 } || G.Wet[2] != Cell{ 1, 2 }) { std::printf("FAIL flow wets east then south, Flow of them\n"); ++Fails; }
		G.Step(NoCell, Reached, Filled, Text);
		if (G.Wet.size() != 5 || G.Wet[3] != Cell{ 0, 1 } || G.Wet[4] != Cell{ 0, 4 }) { std::printf("FAIL the next push continues from the first wet cells in order\n"); ++Fails; }
	}
	{
		Game G = Lay({ "..H..", ".....", ".....", ".....", "....." }, { { 4, 4 } }, NoCell, 4, 10, 2);
		if (G.Step({ 0, 3 }, Reached, Filled, Text) != Game::Act::Ok || G.Wet[1] != Cell{ 1, 2 } || G.Wet[2] != Cell{ 0, 1 } || G.GatesLeft != 3) { std::printf("FAIL a gate blocks a branch\n"); ++Fails; }
		if (G.Step({ 0, 3 }, Reached, Filled, Text) != Game::Act::NotGateable || G.Step({ 0, 1 }, Reached, Filled, Text) != Game::Act::NotGateable || G.Step({ 9, 9 }, Reached, Filled, Text) != Game::Act::BadCell)
		{ std::printf("FAIL gated, wet and off-field cells are refused\n"); ++Fails; }
		G.GatesLeft = 0;
		if (G.Step({ 3, 2 }, Reached, Filled, Text) != Game::Act::NoGates) { std::printf("FAIL no gates left\n"); ++Fails; }
	}
	{
		Game G = Lay({ "H##", ".##", ".##" }, { { 2, 0 } }, NoCell, 3, 5, 1);
		G.Step(NoCell, Reached, Filled, Text); G.Step(NoCell, Reached, Filled, Text);
		if (!G.Won || G.Score != CisternScore + 3 * GateBonus + 3 * TurnBonus || Text.find("brims") == std::string::npos) { std::printf("FAIL a filled cistern wins with the bonuses\n"); ++Fails; }
	}
	{
		Game G = Lay({ "H.", ".." }, { { 1, 1 } }, { 1, 0 }, 2, 5, 2);
		G.Step(NoCell, Reached, Filled, Text);
		if (!G.Over || G.Won || Text.find("mill wheel floods") == std::string::npos) { std::printf("FAIL the mill floods\n"); ++Fails; }
	}
	{
		Game G = Lay({ "H.#", "..#", "##." }, { { 2, 2 } }, NoCell, 2, 2, 2);
		G.Step(NoCell, Reached, Filled, Text); G.Step(NoCell, Reached, Filled, Text);
		if (!G.Over || G.Won || Text.find("headgate closes") == std::string::npos) { std::printf("FAIL the headgate closes\n"); ++Fails; }
		Game D = Lay({ "H.#", "###", "..." }, { { 2, 0 } }, NoCell, 2, 9, 2);
		D.Step(NoCell, Reached, Filled, Text); D.Step(NoCell, Reached, Filled, Text);
		if (!D.Over || D.Won || Text.find("runs dry") == std::string::npos) { std::printf("FAIL the channel runs dry\n"); ++Fails; }
	}
	return Fails;
}

/** Iteration 2: random legal actions on every seeded field; the bookkeeping, preview and win conditions must hold. */
int InvariantSweep()
{
	int Fails = 0, Steps = 0, Fields = 0;
	static const char* Diffs[] = { "easy", "normal", "hard" };
	for (std::uint32_t Seed = 0; Seed < 200 && Fails == 0; ++Seed)
		for (const char* Diff : Diffs)
		{
			Game G; G.Start(Seed, Diff); ++Fields;
			std::uint32_t Pick = Seed * 2654435761u + 7u;
			while (!G.Over)
			{
				Pick = Pick * 1664525u + 1013904223u;
				std::vector<Cell> Legal{ NoCell };
				if (G.GatesLeft > 0) for (int R = 0; R < G.Size(); ++R) for (int C = 0; C < G.Size(); ++C) if (G.Gateable({ R, C })) Legal.push_back({ R, C });
				const Cell X = Legal[(Pick >> 16) % Legal.size()];
				std::vector<Cell> Expected; int ExpectedFilled = 0; bool ExpectedFlood = false;
				if (!G.Preview(X, Expected, ExpectedFilled, ExpectedFlood)) { std::printf("FAIL sweep: preview refused a legal action (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				const size_t WetBefore = G.Wet.size(); const int TurnsBefore = G.Turns, FilledBefore = G.Filled, GatesBefore = G.GatesLeft;
				int Reached = 0, Filled = 0; std::string Text;
				if (G.Step(X, Reached, Filled, Text) != Game::Act::Ok) { std::printf("FAIL sweep: legal action refused (seed %u %s)\n", Seed, Diff); ++Fails; break; }
				++Steps;
				bool Ok = static_cast<size_t>(Reached) == Expected.size() && Filled == ExpectedFilled && G.Wet.size() == WetBefore + static_cast<size_t>(Reached)
				          && G.Turns == TurnsBefore - 1 && G.Filled == FilledBefore + Filled && G.GatesLeft == GatesBefore - (X == NoCell ? 0 : 1)
				          && G.Filled <= static_cast<int>(G.Cisterns.size()) && (!ExpectedFlood || (G.Over && !G.Won));
				for (size_t I = 0; I < Expected.size() && Ok; ++I) Ok = G.Wet[WetBefore + I] == Expected[I];
				for (const Cell& W : G.Wet) if (!G.IsChannel(W) || G.IsGate(W)) Ok = false;
				if (!Ok) { std::printf("FAIL sweep: invariant broke (seed %u %s step %d)\n", Seed, Diff, Steps); ++Fails; break; }
				const bool MillWet = G.Mill != NoCell && G.IsWet(G.Mill);
				if (G.Over && G.Won != (G.Filled == static_cast<int>(G.Cisterns.size()) && !MillWet)) { std::printf("FAIL sweep: win flag (seed %u %s)\n", Seed, Diff); ++Fails; break; }
			}
		}
	std::printf("sweep: %d fields, %d random actions, invariants held\n", Fields, Steps);
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: sluicegate_core_test sluicegate_parity.txt\n"); return 2; }
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
			if (Got != Line) { std::printf("FAIL field differs\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			if (Skip) continue;
			const Cell X = G.DemoAction();
			int Reached = 0, Filled = 0; std::string Result;
			const Game::Act R = G.Step(X, Reached, Filled, Result);
			++Turn;
			const std::string Got = MoveLine(Turn, X, G, Result);
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL s=%u %s turn %d\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Turn, Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("vector ", 0) == 0)   // iteration 4: hand-set corner cases, scripted action + gatekeeper pick
		{
			++Games; Skip = false; Turn = 0;
			std::vector<std::string> Rows = SplitRows(Field(Line, "field"));
			const std::vector<Cell> Gated = ParseCells(Field(Line, "gated"));
			const Cell HeadCell = ParseCells(Field(Line, "head")).front();
			Rows[static_cast<size_t>(HeadCell.R)][static_cast<size_t>(HeadCell.C)] = 'H';
			const std::string MillText = Field(Line, "mill");
			G = Lay(Rows, ParseCells(Field(Line, "cisterns")), MillText == "-" ? NoCell : ParseCells(MillText).front(), std::stoi(Field(Line, "gates")) + static_cast<int>(Gated.size()), std::stoi(Field(Line, "turns")), std::stoi(Field(Line, "flow")));
			G.Wet = ParseCells(Field(Line, "wet")); G.Gates = Gated; G.GatesLeft = std::stoi(Field(Line, "gates"));
			G.Filled = 0; for (const Cell& C : G.Cisterns) if (G.IsWet(C)) ++G.Filled;
		}
		else if (Line.rfind("step ", 0) == 0)
		{
			if (Skip) continue;
			const Cell X = ParseAct(Field(Line, "act")), Demo = ParseAct(Field(Line, "demo"));
			const Cell Pick = G.DemoAction();
			if (Pick != Demo) { std::printf("FAIL vector gatekeeper: want %s got %s\n  %s\n", ActName(Demo).c_str(), ActName(Pick).c_str(), Line.c_str()); ++Fails; }
			int Reached = 0, Filled = 0; std::string Result;
			const Game::Act R = G.Step(X, Reached, Filled, Result);
			const std::string Tail = MoveLine(0, X, G, Result);
			const std::string Got = "step act=" + Field(Line, "act") + " demo=" + Field(Line, "demo") + Tail.substr(Tail.find(" wet="));
			if (R != Game::Act::Ok || Got != Line) { std::printf("FAIL vector step\n  want %s\n  got  %s\n", Line.c_str(), Got.c_str()); ++Fails; Skip = true; }
		}
		else if (Line.rfind("end  ", 0) == 0)
		{
			if (Skip) continue;
			std::ostringstream E; E << "end  score=" << G.Score << " won=" << (G.Won ? 1 : 0) << " filled=" << G.Filled << " turns=" << G.Turns;
			if (E.str() != Line || !G.Over) { std::printf("FAIL s=%u %s end\n  want %s\n  got  %s\n", Seed, Diff.c_str(), Line.c_str(), E.str().c_str()); ++Fails; }
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
	}
	std::printf("%s sluicegate: %d fields regenerated from seed, %d failures\n", Fails ? "FAIL" : "OK", Games, Fails);
	return Fails ? 1 : 0;
}
