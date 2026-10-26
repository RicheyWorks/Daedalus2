// SPDX-License-Identifier: MIT
// G154: DaedalusKennelVoyageCore.h replays the Java G140/G147 voyage + landfall parity table (KennelVoyageParityFixtureTest).
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public kennel_voyage_core_test.cpp -o kennel_voyage_core_test && ./kennel_voyage_core_test kennel_voyage_parity.txt
#include "DaedalusKennelVoyageCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
using namespace daedalus::kennel::voyage;

int main(int Argc, char** Argv)
{
	int Total = 0, Bad = 0, Crossings = 0, Repairs = 0;
	auto Check = [&](bool bOk, const std::string& What) { ++Total; if (!bOk) { ++Bad; std::printf("FAIL %s\n", What.c_str()); } };

	// Unit checks mirroring KennelArkVoyageTest / KennelArkLandfallTest.
	{
		const int None[NumPosts] = {0, 0, 0, 0};
		const int All[NumPosts] = {100, 100, 100, 100};
		FVoyage V;
		Check(Cross(None, std::vector<ETrouble>(4, ETrouble::BoardingGust), std::vector<int>(4, 0), V) && !V.bArrived
			&& V.LegLog.size() == 4 && V.Hull == 0 && V.Fail == EVoyageFail::HullGaveWay, "hull gives way with no guard");
		Check(Cross(None, std::vector<ETrouble>(3, ETrouble::DryCasks), std::vector<int>(3, 0), V) && V.Water == 0
			&& V.Fail == EVoyageFail::CasksRanDry && V.LegLog.size() == 3, "dry casks");
		Check(Cross(All, std::vector<ETrouble>(6, ETrouble::Overboard), std::vector<int>(6, 99), V) && V.bArrived
			&& V.Hull == StartHull && V.Water == StartWater, "all answered");
		Check(!Cross(All, std::vector<ETrouble>(7, ETrouble::Overboard), std::vector<int>(7, 0), V), "seven legs refused");
		Check(!Cross(All, std::vector<ETrouble>(2, ETrouble::Overboard), std::vector<int>(1, 0), V), "short rolls refused");
		FLandfall L;
		const std::vector<int> Rolls(RollsPerDay * Days, 0);
		Check(Repair(None, 4, 3, 3, Rolls, L) && L.DayLog.size() == 3 && L.Hull == 4 && L.Water == 0 && L.Rescued == 0
			&& L.Fail == ELandfallFail::CasksRanDry, "no crew runs dry");
		Check(Repair(None, 1, 10, 0, Rolls, L) && L.DayLog.size() == Days && L.Water == 10 - Days
			&& L.Fail == ELandfallFail::NotMended, "not mended in time");
		Check(Repair(None, HullFull, 1, 1, Rolls, L) && L.bSeaworthy && L.DayLog.empty(), "full hull is seaworthy");
		Check(Repair(All, 4, 5, 1, Rolls, L) && L.bSeaworthy && L.DayLog.size() == 2 && L.Rescued == 1 && L.Hull == HullFull,
			"full crew mends in two days, one rescue");
		Check(!Repair(All, 0, 5, 0, Rolls, L) && !Repair(All, 11, 5, 0, Rolls, L) && !Repair(All, 5, 0, 0, Rolls, L)
			&& !Repair(All, 5, 5, 0, std::vector<int>(14, 0), L), "bad landfall input refused");
	}

	std::ifstream In(Argc > 1 ? Argv[1] : "kennel_voyage_parity.txt");
	std::string Line;
	if (!std::getline(In, Line) || Line.rfind("VOYAGE 1", 0) != 0) { std::printf("FAIL header\n"); return 1; }
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') { Line.pop_back(); }
		if (Line.empty()) { continue; }
		std::istringstream S(Line);
		std::string Kind; S >> Kind;
		int Pct[NumPosts] = {0, 0, 0, 0};
		S >> Pct[0] >> Pct[1] >> Pct[2] >> Pct[3];
		if (Kind == "cross")
		{
			int N = 0; S >> N;
			std::vector<ETrouble> Ts; std::vector<int> Rolls;
			for (int I = 0; I < N; ++I) { int T = 0; S >> T; Ts.push_back(static_cast<ETrouble>(T)); }
			for (int I = 0; I < N; ++I) { int R = 0; S >> R; Rolls.push_back(R); }
			std::string Eq; int Arrived = 0, NLegs = 0, Hull = 0, Water = 0, Fail = 0;
			S >> Eq >> Arrived >> NLegs >> Hull >> Water >> Fail;
			FVoyage V;
			bool bOk = !S.fail() && Eq == "=" && Cross(Pct, Ts, Rolls, V) && (V.bArrived ? 1 : 0) == Arrived
				&& static_cast<int>(V.LegLog.size()) == NLegs && V.Hull == Hull && V.Water == Water
				&& static_cast<int>(V.Fail) == Fail;
			for (int I = 0; bOk && I < NLegs; ++I) { int A = -1; S >> A; bOk = !S.fail() && (V.LegLog[static_cast<size_t>(I)].bAnswered ? 1 : 0) == A; }
			Check(bOk, Line);
			++Crossings;
		}
		else if (Kind == "repair")
		{
			int Hull0 = 0, Water0 = 0, Stranded = 0; S >> Hull0 >> Water0 >> Stranded;
			std::vector<int> Rolls(static_cast<size_t>(RollsPerDay * Days));
			for (int& R : Rolls) { S >> R; }
			std::string Eq; int Sea = 0, NDays = 0, Hull = 0, Water = 0, Rescued = 0, Fail = 0;
			S >> Eq >> Sea >> NDays >> Hull >> Water >> Rescued >> Fail;
			FLandfall L;
			bool bOk = !S.fail() && Eq == "=" && Repair(Pct, Hull0, Water0, Stranded, Rolls, L) && (L.bSeaworthy ? 1 : 0) == Sea
				&& static_cast<int>(L.DayLog.size()) == NDays && L.Hull == Hull && L.Water == Water && L.Rescued == Rescued
				&& static_cast<int>(L.Fail) == Fail;
			for (int I = 0; bOk && I < NDays; ++I)
			{
				std::string D; S >> D;
				const FDay& Day = L.DayLog[static_cast<size_t>(I)];
				bOk = !S.fail() && D == std::to_string(Day.Planks) + (Day.bRescued ? "r" : "");
			}
			Check(bOk, Line);
			++Repairs;
		}
		else { Check(false, "unknown line " + Line); }
	}
	Check(Crossings >= 300 && Repairs >= 300, "parity table has the crossings and repairs");
	std::printf("%s kennel voyage core: %d/%d (%d crossings, %d repairs)\n", Bad == 0 ? "OK" : "FAIL", Total - Bad, Total,
		Crossings, Repairs);
	return Bad == 0 ? 0 : 1;
}