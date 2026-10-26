// SPDX-License-Identifier: MIT
// G46 Ark Record Hunt C++ port, checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public record_hunt_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public record_hunt_core_test.cpp
// --write regenerates record_hunt_parity.txt (read by RecordHuntParityTest.java, line for line).
// Every state-changing call is its own statement: operator+ operand order is unspecified in C++.
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusRecordHuntCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::hunt;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static std::string Join(const std::vector<std::string>& V) { std::string S; for (size_t I = 0; I < V.size(); ++I) S += (I ? "|" : "") + V[I]; return S; }

static std::string MapLine(int64_t Seed, int N, const FragmentMap& M)
{
	std::string S = "map s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " links=";
	for (int F = 0; F < M.Size(); ++F)
	{
		S += (F ? ";" : "") + std::to_string(F) + ":";
		bool First = true;
		for (int V : M.Links[F]) { S += (First ? "" : ",") + std::to_string(V); First = false; }
	}
	S += " home=";
	for (int F = 0; F < M.Size(); ++F) S += (F ? "," : "") + std::to_string(M.Distance(Home, F));
	S += " far=" + FragmentName(M.Size() - 1);
	return S;
}

static std::vector<std::string> Records() { std::vector<std::string> R; for (int I = 0; I < 6; ++I) R.push_back("Item_YTM_Record_H" + std::to_string(I)); return R; }

/** The scripted hunter replayed by RecordHuntParityTest.run(). */
static std::vector<std::string> Run(int64_t Seed, int N)
{
	std::vector<std::string> Out;
	FragmentMap M; SeededMap(Seed * 31 + N, N, M);
	Out.push_back(MapLine(Seed, N, M));
	RecordHunt H; MakeHunt(M, Records(), Seed, 5, H);
	std::string W = "where s=" + std::to_string(Seed) + " n=" + std::to_string(N);
	for (const auto& P : H.Where) W += " " + P.first.substr(16) + "@" + std::to_string(P.second);
	Out.push_back(W);
	for (int T = 0; T < 80; ++T)
	{
		const std::string Ev = "e" + std::to_string(T);
		std::string Op; Step S{ Outcome::Ignored, 0, 0, {} }; std::string Said;
		if (T % 11 == 5) { Op = "bad"; S = H.Walk(Ev, H.At); }
		else if (H.Stamina == 0) { Op = "rest"; S = H.Rest(H.Day + 1); }
		else
		{
			const Hint Ht = H.GetHint();
			if (!Ht.Valid)
			{
				if (H.At != Home) { Op = "home"; S = H.Walk(Ev, M.NextStep(H.At, Home)); }
				else { Op = "talk"; Said = H.Talk(Ev); }
			}
			else if (Ht.Distance == 0) { Op = "search"; S = H.Search(Ev); }
			else { Op = "walk"; S = H.Walk(Ev, Ht.Toward); }
		}
		const std::string Line = ArchivistLine(H);
		std::string L = "h s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " t=" + std::to_string(T) + " op=" + Op;
		if (Op == "talk") L += " said=" + Said;
		else L += std::string(" ") + OutcomeName(S.Result) + " at=" + std::to_string(S.At) + " st=" + std::to_string(S.Stamina) + " found=" + Join(S.Found);
		L += " day=" + std::to_string(H.Day) + " rem=" + std::to_string(H.Remaining()) + " q=" + std::to_string(H.Q.Current) + "/" + std::to_string(H.Q.Count) + " line=" + Line;
		Out.push_back(L);
		if (Op == "talk") break;
	}
	const Step R = H.Rest(H.Day);
	const Step B = H.Search(" ");
	const std::string Again = H.Talk("z");
	Out.push_back("end s=" + std::to_string(Seed) + " n=" + std::to_string(N) + " restAgain=" + OutcomeName(R.Result) + " blank=" + OutcomeName(B.Result) +
		" done=" + (H.Q.Complete() ? "1" : "0") + " talk=" + Again);
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	FragmentMap M;
	Check("3 and 65 fragments refused", !SeededMap(1, 3, M) && !SeededMap(1, 65, M));
	bool Connected = true;
	for (int64_t S = 0; S < 50; ++S) for (int N = 4; N <= 64; N += 6) { SeededMap(S, N, M); for (int D : M.Dist[Home]) Connected = Connected && D >= 0; }
	Check("seeded shelves are connected", Connected);
	Check("map of refuses an island cut off", !MapOf(3, { { 0, 1 } }, M) && MapOf(3, { { 0, 1 }, { 1, 2 } }, M) && M.NextStep(0, 2) == 1);
	Check("names wrap", FragmentName(0) == "Homestead" && FragmentName(15) == "Hollow Bell" && FragmentName(16) == "Reed Shelf 2" && FragmentName(31) == "Reed Shelf 3");
	FragmentMap Line; MapOf(4, { { 0, 1 }, { 1, 2 }, { 2, 3 } }, Line);
	RecordHunt H;
	Check("no records refused", !MakeHunt(Line, {}, 1, 3, H) && !MakeHunt(Line, { "a" }, 1, 0, H) && !MakeHunt(Line, { "a", "a" }, 1, 3, H));
	MakeHunt(Line, { "a" }, 1, 2, H);
	const Step NB = H.Walk("w0", 2);
	Check("no bridge, no stamina spent", NB.Result == Outcome::NoBridge && H.Stamina == 2);
	H.Walk("w1", 1); H.Walk("w2", 2);
	const Step Tired = H.Walk("w3", 3);
	Check("tired after two", Tired.Result == Outcome::Tired && ArchivistLine(H) == TiredLine());
	std::vector<std::string> Lines;
	for (int64_t S = 0; S < 10; ++S) for (int N : { 4, 9, 16, 24 }) for (const std::string& L : Run(S, N)) Lines.push_back(L);
	bool AllHome = true; for (const std::string& L : Lines) if (L.rfind("end ", 0) == 0) AllHome = AllHome && L.find(" done=1 ") != std::string::npos;
	Check("every scripted hunt finishes the quest", AllHome);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("record_hunt_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# record_hunt_core_test.cpp --write: G46 Ark Record Hunt parity (unreal-epic-boss). 10 seeds x shelves of 4/9/16/24, scripted hunter.\n", F);
		for (const std::string& L : Lines) std::fprintf(F, "%s\n", L.c_str());
		std::fclose(F);
		std::printf("wrote record_hunt_parity.txt (%d lines)\n", static_cast<int>(Lines.size()));
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}