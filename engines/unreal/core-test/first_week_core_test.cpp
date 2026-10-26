// SPDX-License-Identifier: MIT
// G62 The First Week Home C++ port, checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public first_week_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public first_week_core_test.cpp
// --write regenerates first_week_parity.txt (read by FirstWeekParityTest.java, line for line). The plot store is a
// std::map here; every state-changing call is its own statement (operator+ operand order is unspecified).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusFirstWeekCore.h"
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
using namespace daedalus;
using namespace daedalus::week;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

struct Plot
{
	std::map<std::string, int> C;
	int Count(const std::string& K) const { const auto It = C.find(K); return It == C.end() ? 0 : It->second; }
	bool Take(const std::string& K, int N) { if (Count(K) < N) return false; C[K] -= N; return true; }
	void Add(const std::string& K, int N) { C[K] += N; }
	bool Cook(const std::string& R)
	{
		const auto Need = Needs(R);
		if (Need.empty()) return false;
		for (const auto& P : Need) if (Count(P.first) < P.second) return false;
		for (const auto& P : Need) Take(P.first, P.second);
		Add(Cooked(R), 1);
		return true;
	}
};

static Plot Stocked()
{
	Plot P;
	const std::pair<const char*, int> S[] = { { "water", 6 }, { "raw_water", 16 }, { "Item_YTM_Tonic_Found_desert_thirst", 1 }, { "Bacon", 4 }, { "Spudlet", 4 }, { "Egg", 8 },
		{ "Fasage", 4 }, { "Pumplet", 2 }, { "Groat", 10 }, { "Milk", 4 }, { "Gloryroot", 1 }, { "Kelpweed", 1 }, { "Bitroot", 1 }, { "Clover", 1 }, { "Mimint", 1 }, { "Moonbean", 1 } };
	for (const auto& X : S) P.Add(X.first, X.second);
	return P;
}

static Outcome DrinkT(FirstWeek& W, Plot& P, const std::string& Ev, Water K)
{
	const char* Item = WaterItem(K);
	const Outcome O = W.Drink(Ev, K, Item ? P.Count(Item) >= 1 : true);
	if (O == Outcome::Drank && Item) P.Take(Item, 1);
	return O;
}

static std::string DayStr(const Day& D)
{
	if (!D.Valid) return "null";
	return std::to_string(D.N) + "," + std::to_string(D.Thirst) + "," + std::to_string(D.Hunger) + "," + std::to_string(D.Health) + "," + (D.Sick ? "1" : "0") + "," + (D.Tonic ? "1" : "0") + "," + (D.Survived ? "1" : "0");
}

static std::vector<std::string> Run(int64_t Seed)
{
	std::vector<std::string> Out;
	FirstWeek W(Seed); Plot P = Stocked();
	const std::string G = WickLine(W);
	Out.push_back("start s=" + std::to_string(Seed) + " line=" + G);
	for (int D = 1; D <= 9; ++D)
	{
		const std::string Ev = "w" + std::to_string(D);
		const Water K = (D + Seed) % 3 == 0 ? Water::Clean : Water::Raw;
		const Outcome Wo = DrinkT(W, P, Ev, K);
		const Outcome Vo = DrinkT(W, P, "v" + std::to_string(D), Water::Raw);
		std::string Extra = "-";
		if (D == 1) Extra = OutcomeName(DrinkT(W, P, Ev, Water::Raw));
		if (D == 2) Extra = OutcomeName(DrinkT(W, P, "s2", Water::Salt));
		const std::string R = Recipes()[static_cast<size_t>((Seed + D) % 8)].Name;
		const bool Cooked1 = P.Cook(R);
		const std::string CI = Cooked(R);
		const Outcome Eo = W.Eat("e" + std::to_string(D), CI, P.Count(CI) >= 1);
		if (Eo == Outcome::Ate) P.Take(CI, 1);
		std::string Tn = "-";
		if (D == 4)
		{
			const Outcome T1 = W.TakeTonic("t4", P.Count(DesertThirstTonic()) >= 1);
			if (T1 == Outcome::Tonic) P.Take(DesertThirstTonic(), 1);
			const Outcome T2 = W.TakeTonic("t4b", P.Count(DesertThirstTonic()) >= 1);
			Tn = std::string(OutcomeName(T1)) + "/" + OutcomeName(T2);
		}
		const std::string Mid = WickLine(W);
		const Day Dy = W.EndDay();
		std::string Said = "-";
		const hunt::Quest::Step* Due = W.Q.CurrentStep();
		if (Due && Due->Type == "talk") Said = W.Talk("k" + std::to_string(D));
		const std::string After = WickLine(W);
		Out.push_back("d s=" + std::to_string(Seed) + " d=" + std::to_string(D) + " w=" + (K == Water::Clean ? "CLEAN:" : "RAW:") + OutcomeName(Wo) + " v=" + OutcomeName(Vo) + " extra=" + Extra + " cook=" + R + ":" +
			(Cooked1 ? "1" : "0") + " eat=" + OutcomeName(Eo) + " tonic=" + Tn + " mid=" + Mid + " day=" + DayStr(Dy) + " q=" + std::to_string(W.Q.Current) + "/" +
			std::to_string(W.Q.Count) + " said=" + Said + " line=" + After + " water=" + std::to_string(P.Count("water")) + " raw=" + std::to_string(P.Count("raw_water")));
	}
	const Outcome Z = DrinkT(W, P, "z", Water::Clean);
	Out.push_back("end s=" + std::to_string(Seed) + " late=" + OutcomeName(Z) + " lost=" + (W.Lost() ? "1" : "0") + " health=" + std::to_string(W.Health) + " done=" + (W.Q.Complete() ? "1" : "0"));
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	Check("restore table", RestoreOf("Stew") == 35 && RestoreOf("Omelet") == 45 && RestoreOf("Porridge") == 25 && RestoreOf("Roast") == 35 && RestoreOf("Salad") == 45 && RestoreOf("Nope") == 0);
	Check("needs merge and map clean water", Needs("Bread") == std::vector<std::pair<std::string, int>>{ { "Groat", 2 }, { "water", 1 } } && Needs("Nope").empty());
	Check("recipe of cooked", RecipeOf("Item_YTM_Food_Pie_Cooked") == "Pie" && RecipeOf("Item_YTM_Food_Pie").empty());
	forge::SplitRng R(42); const double X = NextDouble(R);
	Check("nextDouble in [0,1)", X >= 0.0 && X < 1.0);
	FirstWeek W(1);
	Check("greeting, then sea lowers thirst", WickLine(W) == Greeting() && W.Drink("s", Water::Salt, false) == Outcome::Drank && W.Thirst == 70);
	Check("no water, nothing to use", W.Drink("c", Water::Clean, false) == Outcome::NothingToUse && W.Drink("c", Water::Clean, true) == Outcome::Drank && W.Thirst == 100);
	std::vector<std::string> Lines;
	for (int64_t S = 0; S < 20; ++S) for (const std::string& L : Run(S)) Lines.push_back(L);
	int Done = 0, Lost = 0, Sick = 0;
	for (const std::string& L : Lines) { Done += L.find(" done=1") != std::string::npos; Lost += L.find(" lost=1") != std::string::npos; Sick += L.find(",1,0,") != std::string::npos || L.find(",1,1,") != std::string::npos; }
	std::printf("weeks done %d lost %d sick-days~%d\n", Done, Lost, Sick);
	Check("scenario reaches a finished week", Done > 0);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("first_week_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# first_week_core_test.cpp --write: G62 First Week Home parity (unreal-epic-boss). 20 seeds x 9 scripted days.\n", F);
		for (const std::string& L : Lines) std::fprintf(F, "%s\n", L.c_str());
		std::fclose(F);
		std::printf("wrote first_week_parity.txt (%d lines)\n", static_cast<int>(Lines.size()));
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}