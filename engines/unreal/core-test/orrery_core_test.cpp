// SPDX-License-Identifier: MIT
// The Orrery Reach's rules, checked without Unreal. Build:
//   g++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public orrery_core_test.cpp
#include "DaedalusOrreryCore.h"
#include <cmath>
#include <cstdio>
#include <set>
#include <string>
using namespace daedalus::orrery;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

int main(int argc, char** argv)
{
	// --- the table
	std::set<int> Hours; std::set<std::string> Names;
	bool PairsOK = true;
	for (const Herb& H : Herbs()) { Hours.insert(H.Hour); Names.insert(H.Name); }
	for (const char* C : Constellations())
	{
		int Day = 0, Night = 0;
		for (const Herb& H : Herbs()) if (std::string(H.Constellation) == C) (IsDay(H.Hour) ? Day : Night)++;
		PairsOK = PairsOK && Day == 1 && Night == 1;
	}
	Check("24 herbs cover all 24 hours once", Hours.size() == 24 && *Hours.begin() == 0 && *Hours.rbegin() == 23);
	Check("herb names unique", Names.size() == 24);
	Check("each constellation has exactly one day and one night bloom", PairsOK);
	Check("day is 06:00..17:59", IsDay(6) && IsDay(17) && !IsDay(18) && !IsDay(5) && !IsDay(0));

	// --- picking
	Check("bloom opens in its own hour", CanPick("Sunsprig", 8.0) && CanPick("Sunsprig", 8.99));
	Check("bloom closed outside its hour", !CanPick("Sunsprig", 7.99) && !CanPick("Sunsprig", 9.0));
	Check("hour wraps past midnight", CanPick("Midnightmint", 24.5) && CanPick("Galaxygrass", -3.5));
	Check("NaN hour picks nothing odd", WholeHour(std::nan("")) == 0);
	Check("unknown herb never picks", !CanPick("Moonweed", 0.0));

	// --- brews
	Check("same constellation brews", BrewOf("Sunsprig", "Duskmallow") == "Lantern Brew");
	Check("day+night of different constellations is an eclipse",
		BrewOf("Sunsprig", "Moonvetch") == "Eclipse Brew: Totality");   // (8 + 21) % 8 = 5
	Check("two day blooms of different constellations make nothing", BrewOf("Sunsprig", "Orbitfern").empty());
	Check("a herb with itself makes nothing", BrewOf("Sunsprig", "Sunsprig").empty());
	Check("unknown herb makes nothing", BrewOf("Sunsprig", "Moonweed").empty());
	bool Sym = true;
	for (const Herb& A : Herbs()) for (const Herb& B : Herbs()) Sym = Sym && BrewOf(A.Name, B.Name) == BrewOf(B.Name, A.Name);
	Check("brewing is symmetric for all 576 pairs", Sym);

	// --- steeping
	std::vector<std::string> Satchel{"Sunsprig"}; std::vector<std::string> Brews; Logbook Book;
	auto Before = Satchel;
	Check("gritty water refuses and changes nothing", PlanSteep(false, Satchel).Failure == Refusal::GrittyWater && Satchel == Before);
	Check("empty satchel refuses", PlanSteep(true, {}).Failure == Refusal::EmptySatchel);
	Check("unknown herb in satchel refuses", PlanSteep(true, {"Moonweed"}).Failure == Refusal::UnknownHerb);
	SteepResult R = PlanSteep(true, Satchel);
	Check("one herb makes a tea", R.Made == Kind::Tea && R.Name == "Sunsprig Tea" && R.Used == 1);
	Book.Step = 4; ApplySteep(R, Satchel, Brews, Book);
	Check("tea uses the herb and credits step 5", Satchel.empty() && Brews.size() == 1 && Book.Step == 5);
	Satchel = {"Orbitfern", "Sunsprig", "Duskmallow"};
	R = PlanSteep(true, Satchel); ApplySteep(R, Satchel, Brews, Book);
	Check("brew uses the last two only", R.Made == Kind::Brew && Satchel == std::vector<std::string>{"Orbitfern"});
	Check("brew credits step 6", Book.Step == 6);
	Satchel = {"Sunsprig", "Orbitfern"};
	R = PlanSteep(true, Satchel);
	Check("no brew between last two falls back to a tea of the last", R.Made == Kind::Tea && R.Name == "Orbitfern Tea");
	Logbook Fresh; Satchel = {"Sunsprig", "Duskmallow"};
	R = PlanSteep(true, Satchel); ApplySteep(R, Satchel, Brews, Fresh);
	Check("a brew before step 4 credits nothing", Fresh.Step == 0);
	SteepResult Bad; Bad.Failure = Refusal::GrittyWater; Bad.Used = 1; Satchel = {"Sunsprig"};
	ApplySteep(Bad, Satchel, Brews, Book);
	Check("a refused plan applies nothing", Satchel.size() == 1);
	SteepResult Over = PlanSteep(true, {"Sunsprig", "Duskmallow"}); Satchel = {"Sunsprig"};
	ApplySteep(Over, Satchel, Brews, Book);
	Check("a stale plan bigger than the satchel applies nothing", Satchel.size() == 1);

	// --- logbook
	Logbook L;
	Check("steps cannot skip", !L.Advance(2) && L.Step == 0);
	Check("steps move one at a time", L.Advance(1) && L.Advance(2) && L.Step == 2);
	Check("steps never go back", !L.Advance(1) && L.Step == 2);
	L.Step = 6;
	Check("step 7 needs all twelve charts", !L.Advance(7) && L.Step == 6);
	Check("unknown chart refused", !L.AddChart("Teapot"));
	for (const char* C : Constellations()) L.AddChart(C);
	Check("charts are unique", !L.AddChart("Kite") && L.Charts.size() == 12);
	Check("twelve charts open step 7", L.Advance(7) && L.Step == 7);
	L.Credit(Kind::Eclipse);
	Check("eclipse brew reaches the last step", L.Step == 8);
	Check("nothing past the last step", !L.Advance(9) && L.Step == 8);
	Logbook Early; for (const char* C : Constellations()) Early.AddChart(C); Early.Step = 5;
	Check("reaching 6 with all charts goes on to 7", Early.Advance(6) && Early.Step == 7);
	Check("step text is clamped", std::string(StepText(-3)) == StepText(0) && std::string(StepText(99)) == StepText(8));

	// The parity file for the browser (static/orrery-core.js): the table, then every ordered pair's brew.
	if (argc > 2 && std::string(argv[1]) == "--write")
	{
		FILE* F = std::fopen(argv[2], "w");
		std::fprintf(F, "# orrery_core_test.cpp --write: herbs (name hour constellation day), then BrewOf(a, b) for all 576 pairs\n");
		for (const Herb& H : Herbs()) std::fprintf(F, "herb %s %d %s %d\n", H.Name, H.Hour, H.Constellation, IsDay(H.Hour) ? 1 : 0);
		for (const Herb& A : Herbs())
			for (const Herb& B : Herbs()) std::fprintf(F, "brew %s %s %s\n", A.Name, B.Name, BrewOf(A.Name, B.Name).empty() ? "-" : BrewOf(A.Name, B.Name).c_str());
		std::fclose(F);
		std::printf("wrote %s\n", argv[2]);
	}
	std::printf("%d/%d\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
