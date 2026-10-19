// SPDX-License-Identifier: MIT
// G33 Seed-Song Spring C++ port, checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public seed_song_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public seed_song_core_test.cpp
// Run from this folder (reads ../ytm-island/found_tunes.csv). --write regenerates seed_song_parity.txt
// (read by SeedSongParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusSeedSongCore.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
using namespace daedalus::seedsong;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static std::string Join(const std::vector<std::string>& V, const char* D)
{
	std::string S; for (size_t I = 0; I < V.size(); ++I) S += (I ? D : "") + V[I]; return S;
}

static std::string TallyOf(const Chapter& C)
{
	const Tally T = C.GetTally();
	return std::to_string(T.Restored) + "," + std::to_string(T.Skipped) + "," + std::to_string(T.SpringsPurified) + "," + std::to_string(T.CleanDraws) +
		" q=" + std::to_string(C.Q.Current) + "/" + std::to_string(C.Q.Count);
}

/** The scripted chapter replayed by SeedSongParityTest.scenario(). Every bench brew is stocked, so BREWED. */
static std::vector<std::string> Scenario(const std::vector<Tune>& Tunes, int64_t Seed)
{
	std::vector<std::string> Out;
	Chapter C(Tunes, Chain::Island(), Seed);
	for (size_t I = 0; I < Tunes.size(); ++I)
	{
		const Tune& T = Tunes[I];
		std::string L = "run s=" + std::to_string(Seed) + " i=" + std::to_string(I) + " a=";
		if (I % 3 == 1)
		{
			std::vector<std::string> Rev(T.Herbs.rbegin(), T.Herbs.rend());
			L += OutcomeName(C.Apply("r" + std::to_string(I) + "a", T.LearnedFrom, Rev, true, BrewOutcome::Brewed).Result);
		}
		else L += "-";
		const Restore R = C.Apply("r" + std::to_string(I) + "b", T.LearnedFrom, T.Herbs, true, BrewOutcome::Brewed);
		L += std::string(" b=") + OutcomeName(R.Result) + " spring=" + (R.Purified ? R.Purified->Id : "-") + " tally=" + TallyOf(C);
		if (I == 2 || I == 7)
		{
			const Draw D = C.DrawAt("d" + std::to_string(I), "spring_1"), D2 = C.DrawAt("d" + std::to_string(I) + "x", "spring_12");
			L += std::string(" draw=") + DrawName(D.Outcome) + ":" + D.Item + ":" + std::to_string(D.Amount) + " far=" + DrawName(D2.Outcome) + ":" + D2.Item + ":" + std::to_string(D2.Amount);
			L += " talk=" + C.Talk("k" + std::to_string(I)) + " | tally=" + TallyOf(C);
		}
		Out.push_back(L + " keeper=" + KeeperLine(C));
	}
	const std::string E = std::string("edge s=") + std::to_string(Seed) + " dup=" + OutcomeName(C.Apply("r0b", Tunes[0].LearnedFrom, Tunes[0].Herbs, true, BrewOutcome::Brewed).Result) +
		" unknown=" + OutcomeName(C.Apply("e1", "Item_YTM_Record_Nope", Tunes[0].Herbs, true, BrewOutcome::Brewed).Result) +
		" already=" + OutcomeName(C.Apply("e2", Tunes[0].LearnedFrom, Tunes[0].Herbs, true, BrewOutcome::Brewed).Result) +
		" blank=" + OutcomeName(C.Apply(" ", Tunes[0].LearnedFrom, Tunes[0].Herbs, true, BrewOutcome::Brewed).Result) +
		" unknownSpring=" + DrawName(C.DrawAt("e3", "spring_99").Outcome) + " drawDup=" + DrawName(C.DrawAt("d2", "spring_1").Outcome) +
		" questDone=" + (C.Q.Complete() ? "1" : "0");
	Out.push_back(E);
	Chapter F(Tunes, Chain::Island(), Seed);
	Out.push_back(std::string("fresh s=") + std::to_string(Seed) + " noRecord=" + OutcomeName(F.Apply("f1", Tunes[0].LearnedFrom, Tunes[0].Herbs, false, BrewOutcome::Brewed).Result) +
		" missingHerbs=" + OutcomeName(F.Apply("f2", Tunes[0].LearnedFrom, Tunes[0].Herbs, true, BrewOutcome::MissingHerbs).Result) +
		" cloudy=" + DrawName(F.DrawAt("f3", "spring_1").Outcome) + " keeper=" + KeeperLine(F) + " talk=" + F.Talk("f4"));
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	std::ifstream In("../ytm-island/found_tunes.csv", std::ios::binary);
	std::stringstream SS; SS << In.rdbuf();
	std::vector<Tune> Tunes;
	Check("found_tunes.csv parses to 12 tunes", ParseTunes(SS.str(), Tunes) && Tunes.size() == 12);
	if (Tunes.size() != 12) { std::printf("%d/%d passed\n", Passed, Total); return 1; }
	Check("java hash", JavaHash("") == 0 && JavaHash("a") == 97 && JavaHash("abc") == 96354 && JavaHash("polygenelubricants") == static_cast<int32_t>(0x80000000u));
	bool Bounds = true;
	for (int64_t S = 0; S < 64; ++S)
		for (const Tune& T : Tunes) { Record R; Bounds = Bounds && MakeRecord(T, S, R) && R.Missing >= 1 && R.Missing <= 2 && R.Heard().size() >= 2; }
	Check("scratch eats 1-2 and leaves 2+", Bounds);
	Tune Short{ "x", "y", { "A", "B" }, { 1, 2 }, "z" }; Record Bad;
	Check("two-herb tune refused", !MakeRecord(Short, 1, Bad));
	Chapter C(Tunes, Chain::Island(), 2026);
	Check("twelve records, greeting", C.Records.size() == 12 && KeeperLine(C) == Greeting());
	const Tune& T0 = Tunes[0];
	std::vector<std::string> Lowered; for (const std::string& H : T0.Herbs) Lowered.push_back(Lower(H));
	Check("restoration is case-insensitive", C.Find(T0.LearnedFrom)->RestoredBy(Lowered));
	Check("no record, no brew", C.PreCheck("p", T0.LearnedFrom, false) == Outcome::NoRecord);
	const Restore R = C.Apply("r", T0.LearnedFrom, T0.Herbs, true, BrewOutcome::Brewed);
	Check("restore purifies spring_1", R.Result == Outcome::Restored && R.Purified && R.Purified->Id == "spring_1" && C.Springs.Clean("spring_1"));
	const Draw D = C.DrawAt("d", "spring_1");
	Check("clean draw gives water x4", D.Outcome == DrawOutcome::Clean && D.Item == "water" && D.Amount == 4);

	std::vector<std::string> Lines;
	for (int64_t S = 0; S < 20; ++S)
		for (size_t I = 0; I < Tunes.size(); ++I)
		{
			Record Rr; MakeRecord(Tunes[I], S, Rr);
			Lines.push_back("rec s=" + std::to_string(S) + " t=" + std::to_string(I) + " missing=" + std::to_string(Rr.Missing) + " heard=" + Join(Rr.Heard(), "|") +
				" home=" + (Rr.ComesHome() ? "1" : "0") + " | " + Hint(Rr));
		}
	for (const Spring& Sp : Chain::Island().Springs) Lines.push_back("spring " + Sp.Id + " " + Sp.Name + " " + std::to_string(Sp.Yield));
	for (int64_t S = 0; S < 10; ++S) for (const std::string& L : Scenario(Tunes, S)) Lines.push_back(L);
	Check("parity lines", Lines.size() == 240 + 12 + 10 * 14);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("seed_song_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# seed_song_core_test.cpp --write: G33 Seed-Song Spring parity (unreal-epic-boss). 20 seeds x 12 records, 12 springs, 10 scripted chapters.\n", F);
		for (const std::string& L : Lines) std::fprintf(F, "%s\n", L.c_str());
		std::fclose(F);
		std::printf("wrote seed_song_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}