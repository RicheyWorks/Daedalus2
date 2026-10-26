// SPDX-License-Identifier: MIT
// G53 Choir Stones C++ port, checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public choir_stones_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public choir_stones_core_test.cpp
// --write regenerates choir_stones_parity.txt (read by ChoirStonesParityTest.java, line for line).
// Every state-changing call is its own statement: operator+ operand order is unspecified in C++.
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusChoirStonesCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus;
using namespace daedalus::stones;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static const char* const Rec[] = { "Item_YTM_Record_AmericanOldTime", "Item_YTM_Record_Alpine", "Item_YTM_Record_CelticPipes", "Item_YTM_Record_Gamelan" };
static bool Restored(int I) { return I < 3; } // the Java side restores tunes 0..2 on a real SeedSongSpring

static std::string Bridges(const std::vector<Bridge>& V) { std::string S; for (size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I].first) + "-" + std::to_string(V[I].second); return S; }
static std::string Ints(const std::vector<int>& V) { std::string S; for (size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I]); return S; }

/** Scripted chapter replayed by ChoirStonesParityTest.run(). */
static std::vector<std::string> Run(int64_t Seed, int N)
{
	std::vector<std::string> Out;
	hunt::FragmentMap M; hunt::SeededMap(Seed * 7 + N, N, M);
	Choir C(M, Seed);
	int StonesLeft = 2, Rope = 6;
	auto CarveT = [&](const std::string& Ev, int F, int R, int Tier) {
		const Outcome O = C.Carve(Ev, F, Rec[R], Tier, Restored(R), StonesLeft > 0);
		if (O == Outcome::Carved) --StonesLeft;
		return std::string(OutcomeName(O));
	};
	const std::string A = CarveT("c0", N - 1, 0, 4);
	const std::string B = CarveT("c0", N - 1, 0, 4);
	const std::string Cc = CarveT("c1", N - 1, 1, 3);
	const std::string D = CarveT("c2", N / 2, 0, 3);
	const std::string E = CarveT("c3", 1, 3, 3);
	const std::string F = CarveT("c4", 99, 1, 3);
	const std::string L0 = MasonLine(C);
	Out.push_back("carve s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " a=" + A + " dup=" + B + " taken=" + Cc + " used=" + D + " scratched=" + E +
		" unknown=" + F + " stones=" + std::to_string(C.Stones.size()) + " range=" + std::to_string(C.Stones[0].Range) + " line=" + L0);
	for (int Nt = 1; Nt <= 12; ++Nt)
	{
		std::string Second = "-";
		if (Nt == 3) Second = CarveT("c5", N / 2, 1, 2);
		const Night Ni = C.Shake(Nt);
		std::string Re = "-";
		for (const auto& P : C.L.Strength)
			if (P.second == 0)
			{
				if (C.L.Restring(P.first.first, P.first.second, Rope >= RopePerBridge)) { Rope -= RopePerBridge; Re = std::to_string(P.first.first) + "-" + std::to_string(P.first.second); }
				break;
			}
		std::string Said = "-";
		const hunt::Quest::Step* Due = C.Q.CurrentStep();
		if (Due && Due->Type == "talk") Said = C.Talk("t" + std::to_string(Nt));
		const std::string Line = MasonLine(C);
		Out.push_back("night s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " k=" + std::to_string(Nt) + " carve=" + Second + " frayed=" + Bridges(Ni.Frayed) +
			" snapped=" + Bridges(Ni.Snapped) + " cut=" + Ints(Ni.CutOff) + " held=" + (Ni.Held ? "1" : "0") + " heldN=" + std::to_string(C.HeldNights) +
			" re=" + Re + " rope=" + std::to_string(Rope) + " q=" + std::to_string(C.Q.Current) + "/" + std::to_string(C.Q.Count) + " said=" + Said + " line=" + Line);
	}
	const Night Again = C.Shake(12);
	const std::string NoStone = CarveT("c6", 2, 2, 1);
	Out.push_back("end s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " again=" + (Again.Valid ? "night" : "null") + " last=" + NoStone +
		" done=" + (C.Q.Complete() ? "1" : "0"));
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	Check("range by tier", Range(0) == 1 && Range(1) == 1 && Range(2) == 2 && Range(3) == 2 && Range(4) == 3 && Range(9) == 3);
	Check("frays per night", FraysPerNight(9) == 3 && FraysPerNight(24) == 7);
	hunt::FragmentMap Line; hunt::MapOf(3, { { 0, 1 }, { 1, 2 } }, Line);
	Ledger L(Line);
	Check("ledger starts strong", L.StrengthOf(1, 0) == 3 && L.StrengthOf(0, 2) == -1 && L.CutOff().empty());
	L.Fray({ 1, 2 }); L.Fray({ 1, 2 });
	const bool Snap = L.Fray({ 1, 2 });
	Check("third fray snaps and cuts off", Snap && L.CutOff() == std::vector<int>{ 2 } && !L.Fray({ 1, 2 }));
	Check("restring needs rope", !L.Restring(1, 2, false) && L.Restring(2, 1, true) && L.StrengthOf(1, 2) == 3 && !L.Restring(1, 2, true));
	Choir C(Line, 1);
	Check("carve order of checks", C.Carve(" ", 0, "r", 4, true, true) == Outcome::Ignored && C.Carve("a", 5, "r", 4, true, true) == Outcome::UnknownFragment &&
		C.Carve("a", 0, "r", 4, false, true) == Outcome::NotRestored && C.Carve("a", 0, "r", 4, true, false) == Outcome::NoStone && C.Carve("a", 0, "r", 4, true, true) == Outcome::Carved &&
		C.Carve("a", 1, "q", 4, true, true) == Outcome::Duplicate);
	Check("one stone line", MasonLine(C) == OneStone());
	std::vector<std::string> Lines;
	for (int64_t S = 0; S < 10; ++S) for (int N : { 9, 16, 24 }) for (const std::string& X : Run(S, N)) Lines.push_back(X);
	int Done = 0, Cut = 0; for (const std::string& X : Lines) { Done += X.find(" done=1") != std::string::npos; Cut += X.find(" held=0 ") != std::string::npos; }
	Check("scenario reaches both outcomes", Done > 0 && Cut > 0);
	std::printf("quests done %d of 30, nights cut off %d\n", Done, Cut);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("choir_stones_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# choir_stones_core_test.cpp --write: G53 Choir Stones parity (unreal-epic-boss). 10 seeds x shelves of 9/16/24, 12 nights.\n", F);
		for (const std::string& X : Lines) std::fprintf(F, "%s\n", X.c_str());
		std::fclose(F);
		std::printf("wrote choir_stones_parity.txt (%d lines)\n", static_cast<int>(Lines.size()));
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}