// SPDX-License-Identifier: MIT
// G66 Record Exchange C++ port, checked without Unreal. Build (MSVC, from this folder, vcvars64):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I ..\DaedalusLink\Source\DaedalusLink\Public record_exchange_core_test.cpp
// Run from this folder (reads ../ytm-island/found_tunes.csv). --write regenerates record_exchange_parity.txt,
// which RecordExchangeParityTest (daedalus-core) replays line for line against the Java chapter.
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusRecordExchangeCore.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
using namespace daedalus;
using namespace daedalus::exchange;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static int Idx(const std::vector<seedsong::Tune>& T, const std::string& R) { for (size_t I = 0; I < T.size(); ++I) if (T[I].LearnedFrom == R) return static_cast<int>(I); return -1; }

struct Sim
{
	const std::vector<seedsong::Tune>& Tunes; seedsong::Chapter C; Exchange X; std::map<std::string, int> Store;
	Sim(const std::vector<seedsong::Tune>& T, int64_t Seed) : Tunes(T), C(T, seedsong::Chain::Island(), Seed), X(T, Island(), Seed) {}
	int Count(const std::string& K) const { const auto It = Store.find(K); return It == Store.end() ? 0 : It->second; }
	std::string Press(const std::string& E, int I)
	{
		const std::string& R = Tunes[I].LearnedFrom;
		const Outcome O = X.Press(E, R, C.IsRestored(R));
		if (O == Outcome::Pressed) ++Store[CopyOf(R)];
		return OutcomeName(O);
	}
	std::string Sell(const std::string& E, const std::string& Tr, const std::string& R)
	{
		const Trade T = X.TradeWith(E, Tr, R, Count(CopyOf(R)) >= 1);
		if (T.Result == Outcome::Traded) { --Store[CopyOf(R)]; Store[T.Good] += T.Amount; }
		return std::string(OutcomeName(T.Result)) + ":" + T.Good + ":" + std::to_string(T.Amount) + ":" + (T.Wanted ? "1" : "0");
	}
	std::string Quest() const { return std::to_string(X.Q.Current) + "/" + std::to_string(X.Q.Count); }
};

static std::vector<std::string> Scenario(const std::vector<seedsong::Tune>& Tunes, int64_t Seed)
{
	std::vector<std::string> Out;
	Sim S(Tunes, Seed);
	std::string L = "restore s=" + std::to_string(Seed);
	for (size_t I = 0; I < Tunes.size(); ++I)
		if (I % 4 != 3) L += " " + std::to_string(I) + "=" + seedsong::OutcomeName(S.C.Apply("r" + std::to_string(I), Tunes[I].LearnedFrom, Tunes[I].Herbs, true, seedsong::BrewOutcome::Brewed).Result);
	Out.push_back(L);
	for (int D = 1; D <= 5; ++D)
	{
		const std::string Ds = std::to_string(D);
		std::string W = "day s=" + std::to_string(Seed) + " d=" + Ds + " day=" + std::to_string(S.X.Day) + " wants=";
		for (const Trader& T : S.X.Traders) { W += T.Id + ":"; for (const std::string& R : S.X.WantsToday(T.Id)) W += std::to_string(Idx(Tunes, R)) + "|"; W += ";"; }
		W += " press=";
		for (int I = 0; I < static_cast<int>(Tunes.size()); ++I) W += S.Press("p" + Ds + "_" + std::to_string(I), I) + ",";
		if (D == 1) W += " again=" + S.Press("p1_0", 0) + "," + S.Press("p1_0x", 0);
		Out.push_back(W);
		std::string T2 = "sell s=" + std::to_string(Seed) + " d=" + Ds;
		for (const Trader& T : S.X.Traders)
		{
			int K = 0;
			for (const std::string& R : S.X.WantsToday(T.Id)) { T2 += " " + T.Id + "#" + std::to_string(Idx(Tunes, R)) + "=" + S.Sell("t" + Ds + T.Id + std::to_string(K), T.Id, R); ++K; }
		}
		const int Dov = S.X.Price("dov", Tunes[0].LearnedFrom);
		T2 += " dovPrice=" + std::to_string(Dov) + " dov=" + S.Sell("y" + Ds, "dov", Tunes[0].LearnedFrom);
		T2 += " pell=" + S.Sell("x" + Ds, "pell", Tunes[static_cast<size_t>(D) % Tunes.size()].LearnedFrom);
		T2 += " q=" + S.Quest();
		const std::string Said = S.X.Talk("k" + Ds);
		T2 += " talk=" + Said + " | q=" + S.Quest() + " goods=" + std::to_string(S.Count("rope")) + "," + std::to_string(S.Count("choir_stone_blank")) + "," + std::to_string(S.Count("Egg")) + "," + std::to_string(S.Count("fish"));
		T2 += " line=" + TraderLine(S.X);
		Out.push_back(T2);
		S.X.NextDay();
	}
	const std::string& R0 = Tunes[0].LearnedFrom;
	std::string E = "edge s=" + std::to_string(Seed);
	E += " zed=" + S.Sell("e1", "zed", R0);
	E += " nope=" + S.Sell("e2", "pell", "Item_YTM_Record_Nope");
	E += " nocopy=" + S.Sell("e3", "pell", Tunes[3].LearnedFrom);
	E += " blank=" + S.Sell(" ", "pell", R0);
	E += " dup=" + S.Sell("x1", "pell", R0);
	E += " pressNope=" + std::string(OutcomeName(S.X.Press("e4", "Item_YTM_Record_Nope", true)));
	E += " pressRaw=" + S.Press("e5", 3);
	E += " priceZed=" + std::to_string(S.X.Price("zed", R0)) + " copy=" + CopyOf(R0) + " done=" + (S.X.Q.Complete() ? "1" : "0");
	Out.push_back(E);
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	std::ifstream In("../ytm-island/found_tunes.csv", std::ios::binary);
	std::stringstream SS; SS << In.rdbuf();
	std::vector<seedsong::Tune> Tunes;
	Check("found_tunes.csv parses to 12 tunes", seedsong::ParseTunes(SS.str(), Tunes) && Tunes.size() == 12);
	if (Tunes.size() != 12) return 1;
	Check("island has 4 traders wanting 7 tunes a day", Island().size() == 4 && Island()[0].Good == "rope" && Island()[2].Good == "Egg");
	Exchange A(Tunes, Island(), 2026);
	const std::vector<std::string> W = A.WantsToday("pell");
	Check("wants are distinct and deterministic", W.size() == 2 && W[0] != W[1] && W == A.WantsToday("pell") && A.WantsToday("zed").empty());
	Check("unrestored records do not press; restored press once a day", A.Press("a", Tunes[0].LearnedFrom, false) == Outcome::NotRestored && A.Press("b", Tunes[0].LearnedFrom, true) == Outcome::Pressed && A.Press("c", Tunes[0].LearnedFrom, true) == Outcome::PressedToday && A.Press("b", Tunes[0].LearnedFrom, true) == Outcome::Duplicate);
	const int P0 = A.Price("ida", Tunes[0].LearnedFrom);
	const Trade T1 = A.TradeWith("t1", "ida", Tunes[0].LearnedFrom, true);
	Check("a trade pays the price, then the price halves", T1.Result == Outcome::Traded && T1.Amount == P0 && P0 > 0 && A.Price("ida", Tunes[0].LearnedFrom) == P0 / 2);
	Check("no copy and blank events are refused cleanly", A.TradeWith("t2", "ida", Tunes[0].LearnedFrom, false).Result == Outcome::NoCopy && A.TradeWith("  ", "ida", Tunes[0].LearnedFrom, true).Result == Outcome::Ignored);
	std::vector<std::string> Lines;
	for (int64_t S = 0; S < 10; ++S) for (const std::string& L : Scenario(Tunes, S)) Lines.push_back(L);
	bool AnyDone = false, AnyRefused = false;
	for (const std::string& L : Lines) { AnyDone = AnyDone || (L.rfind("edge ", 0) == 0 && L.find(" done=1") != std::string::npos); AnyRefused = AnyRefused || L.find("REFUSED") != std::string::npos; }
	Check("scripted exchanges finish the quest and reach REFUSED", AnyDone && AnyRefused);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("record_exchange_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# record_exchange_core_test.cpp --write: G66 Record Exchange parity (unreal-epic-boss). 10 seeds x 5 scripted days, 4 traders.\n", F);
		for (const std::string& L : Lines) std::fprintf(F, "%s\n", L.c_str());
		std::fclose(F);
		std::printf("wrote record_exchange_parity.txt (%d lines)\n", static_cast<int>(Lines.size()));
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}