// SPDX-License-Identifier: MIT
// Reactive Battlefield Ecology (ADR-061): the C++ DBE 1 reader agrees with the Java writer, checked without Unreal.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public ecology_core_test.cpp
#include "DaedalusEcologyCore.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
using namespace daedalus::ecology;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static bool Refuses(const std::string& S, const char* Needle) { Field F; Result R = ReadSnapshot(S, F); return !R.Ok && R.Error.find(Needle) != std::string::npos; }

static std::string Slurp(const char* Path)
{
	std::ifstream In(Path, std::ios::binary); std::ostringstream S; S << In.rdbuf(); std::string T = S.str(), U;
	for (char C : T) { if (C != '\r') { U += C; } } // git may check fixtures out with CRLF
	return U;
}

int main(int Argc, char** Argv)
{
	const bool Write = Argc > 1 && std::strcmp(Argv[1], "--write") == 0;
	// Same shape BattlefieldEcologyTest asserts for Dbe.write: 6x6, 100 cm cells, seed 42.
	const std::string Snap = "DBE 1\ngrid 6 6 100 0 0 42\ntick 1\nrow 0 wwmmss\nrow 1 wwmmss\nrow 2 ..ppoo\nrow 3 ..ppoo\nrow 4 mmmmmm\nrow 5 ssssss\nfire 2 2 3\n";
	Field F; Result R = ReadSnapshot(Snap, F);
	Check("reads a Java DBE 1 snapshot", R.Ok && F.W == 6 && F.H == 6 && F.Seed == 42 && F.Tick == 1);
	Check("oak cover 0.80 at cell 4,2", R.Ok && F.CoverAt(450, 250) == 0.80);
	Check("pine concealment 0.70", R.Ok && F.ConcealmentAt(250, 350) == 0.70);
	Check("fire cell burns, neighbour does not", R.Ok && F.BurningAt(250, 250) && !F.BurningAt(350, 250));
	Check("points outside clamp like Java cellI/cellJ", R.Ok && F.CodeAt(-5000, -5000) == 'w' && F.CodeAt(9e6, 9e6) == 's');
	Check("CRLF accepted", ReadSnapshot("DBE 1\r\ngrid 1 1 100 0 0 1\r\ntick 0\r\nrow 0 o\r\n", F).Ok);
	Check("refuses DBE 2 on line 1", Refuses("DBE 2\n", "line 1"));
	Check("refuses short row", Refuses("DBE 1\ngrid 2 1 100 0 0 1\ntick 0\nrow 0 o\n", "line 4"));
	Check("refuses rows out of order", Refuses("DBE 1\ngrid 1 2 100 0 0 1\ntick 0\nrow 1 o\nrow 0 o\n", "in order"));
	Check("refuses unknown code", Refuses("DBE 1\ngrid 1 1 100 0 0 1\ntick 0\nrow 0 x\n", "unknown"));
	Check("refuses fire on wetland", Refuses("DBE 1\ngrid 1 1 100 0 0 1\ntick 0\nrow 0 w\nfire 0 0 2\n", "cannot burn"));
	Check("refuses fire ticks 65", Refuses("DBE 1\ngrid 1 1 100 0 0 1\ntick 0\nrow 0 o\nfire 0 0 65\n", "1..64"));
	Check("refuses missing rows", Refuses("DBE 1\ngrid 1 3 100 0 0 1\ntick 0\nrow 0 o\n", "row lines"));
	std::string E; Result W = WriteEvents({{EventKind::IGNITE, 250, 250, 0, 150}, {EventKind::DOUSE, 0, 0, 0, 0}}, E);
	Check("writes DBE-E 1 events", W.Ok && E == "DBE-E 1\nevent IGNITE 250 250 0 150\nevent DOUSE 0 0 0 0\n");
	Check("refuses radius over 100000", !WriteEvents({{EventKind::BLAST, 0, 0, 0, 100001}}, E).Ok);
	Check("refuses 257 events", !WriteEvents(std::vector<Event>(257, Event{EventKind::BLAST, 0, 0, 0, 1}), E).Ok);
	// Offline round trip (no Unreal): Java wrote ecology_roundtrip.dbe (BattlefieldDemo.scene(7)); C++ must read it,
	// answer like Java at the battlefield-check points, and write the IGNITE that EcologyRoundTripTest applies in Java.
	const std::string Demo = Slurp("ecology_roundtrip.dbe");
	Field D; Result DR = ReadSnapshot(Demo, D);
	Check("round trip: reads Java BattlefieldDemo snapshot", DR.Ok && D.W == 40 && D.H == 30 && D.Seed == 7);
	Check("round trip: meadow at the squad 900,1500 cover 0.05 conceal 0.35", DR.Ok && D.CoverAt(900, 1500) == 0.05 && D.ConcealmentAt(900, 1500) == 0.35);
	Check("round trip: oak wood at 2000,1500 cover 0.80 conceal 0.60", DR.Ok && D.CoverAt(2000, 1500) == 0.80 && D.ConcealmentAt(2000, 1500) == 0.60);
	Check("round trip: nothing burns at tick 0", DR.Ok && !D.BurningAt(2000, 1500) && !D.BurningAt(3900, 1500));
	std::string Ev; Result EW = WriteEvents({{EventKind::IGNITE, 2000, 1500, 0, 150}}, Ev);
	if (Write && EW.Ok) { std::ofstream("ecology_roundtrip_events.txt", std::ios::binary) << Ev; }
	Check("round trip: IGNITE events match ecology_roundtrip_events.txt", EW.Ok && Ev == Slurp("ecology_roundtrip_events.txt"));
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}