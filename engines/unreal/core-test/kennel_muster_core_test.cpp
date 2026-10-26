// SPDX-License-Identifier: MIT
// G128: DaedalusKennelMusterCore.h replays the Java G107 muster parity table (KennelMusterParityFixtureTest) and unit checks.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public kennel_muster_core_test.cpp -o kennel_muster_core_test && ./kennel_muster_core_test kennel_muster_parity.txt
#include "DaedalusKennelMusterCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
using namespace daedalus::kennel::muster;

int main(int Argc, char** Argv)
{
	int Total = 0, Bad = 0, Crews = 0;
	auto Check = [&](bool bOk, const std::string& What) { ++Total; if (!bOk) { ++Bad; std::printf("FAIL %s\n", What.c_str()); } };

	// Unit checks: the chapter's own crew (G107 test) and the gates.
	{
		FHound Elder{70, 95}, Adult{25, 85}, JuvA{12, 60}, JuvB{13, 55}, Pup{5, 30}, Newborn{1, 100};
		Check(Fits(Adult, 1) && !Fits(Elder, 1) && Fits(Elder, 0) && !Fits(JuvA, 0) && Fits(JuvA, 2), "post gates");
		Check(Fits(Pup, 3) && !Fits(Pup, 2) && !Fits(Newborn, 3), "young gates");
		FRoster R;
		Check(Assign({Elder, Adult, JuvA, JuvB}, R) && R.Full() && R.Hound[0] == 0 && R.Hound[1] == 1 && R.Hound[2] == 2
			&& R.Hound[3] == 3 && R.TotalPct == 52 + 32 + 50 + 67, "Hull Bay crew");
		Check(Assign({Pup, Newborn, JuvA}, R) && R.Filled == 2 && R.Hound[2] == 2 && R.Hound[3] == 0 && !CanMuster(R), "crew short");
		Check(Assign({}, R) && R.Filled == 0 && R.TotalPct == 0, "empty crew");
		Check(!Assign(std::vector<FHound>(9, Adult), R), "more than 8 hounds refused");
		Check(Launches(3) && Launches(4) && !Launches(2), "launch rule");
	}

	std::ifstream In(Argc > 1 ? Argv[1] : "kennel_muster_parity.txt");
	std::string Line;
	if (!std::getline(In, Line) || Line.rfind("MUSTER 1", 0) != 0) { std::printf("FAIL header\n"); return 1; }
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') { Line.pop_back(); }
		if (Line.empty()) { continue; }
		std::istringstream S(Line);
		std::string Kind; S >> Kind;
		if (Kind == "fits")
		{
			FHound H; int P = 0, Want = 0; S >> H.CareDays >> H.Bond >> P >> Want;
			Check(P >= 0 && P < NumPosts && (Fits(H, P) ? 1 : 0) == Want, Line);
		}
		else if (Kind == "crew")
		{
			int N = 0; S >> N;
			std::vector<FHound> Hs(static_cast<size_t>(N > 0 ? N : 0));
			for (FHound& H : Hs) { S >> H.CareDays >> H.Bond; }
			std::string Eq; int Filled = 0, Pct = 0, Idx[NumPosts] = {0, 0, 0, 0};
			S >> Eq >> Filled >> Pct >> Idx[0] >> Idx[1] >> Idx[2] >> Idx[3];
			FRoster R;
			bool bOk = !S.fail() && Eq == "=" && Assign(Hs, R) && R.Filled == Filled && R.TotalPct == Pct;
			for (int P = 0; P < NumPosts; ++P) { bOk = bOk && R.Hound[P] == Idx[P]; }
			Check(bOk, Line);
			++Crews;
		}
		else { Check(false, "unknown line " + Line); }
	}
	Check(Crews >= 300, "parity table has the crews");
	std::printf("%s kennel muster core: %d/%d (%d crews)\n", Bad == 0 ? "OK" : "FAIL", Total - Bad, Total, Crews);
	return Bad == 0 ? 0 : 1;
}
