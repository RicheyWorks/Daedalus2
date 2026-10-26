// SPDX-License-Identifier: MIT
// G84: DaedalusKennelCore.h replays the Java parity table (KennelParityFixtureTest) line by line.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public kennel_core_test.cpp -o kennel_core_test && ./kennel_core_test kennel_parity.txt
#include "DaedalusKennelCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
using namespace daedalus::kennel;

int main(int Argc, char** Argv)
{
	std::ifstream In(Argc > 1 ? Argv[1] : "kennel_parity.txt");
	std::string Line;
	int Total = 0, Bad = 0;
	if (!std::getline(In, Line) || Line.rfind("KENNEL 1", 0) != 0) { std::printf("FAIL header\n"); return 1; }
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') { Line.pop_back(); }
		if (Line.empty()) { continue; }
		std::istringstream S(Line);
		std::string Kind; S >> Kind; bool OK = false;
		if (Kind == "tier") { int B; std::string W; S >> B >> W; OK = W == TierName(TierOf(B)); }
		else if (Kind == "odds")
		{
			int B, P, O; std::string C; S >> B >> C >> P >> O; ECommand Cmd = CommandOf(C.c_str());
			OK = SuccessPct(B, Cmd) == P && (Obeys(B, Cmd) ? 1 : 0) == O;
		}
		else if (Kind == "step")
		{
			int B, F, W, T, K, N; S >> B >> F >> W >> T >> K >> N;
			FCare C; C.bFed = F; C.bWatered = W; C.bTonic = T; C.FetchCatches = K; OK = StepBond(B, C) == N;
		}
		else if (Kind == "stage") { int D; std::string W; S >> D >> W; OK = W == StageName(StageOf(D)); }
		else if (Kind == "grow")
		{
			int D, F, W, T, R, N, NB; S >> D >> F >> W >> T >> R >> N >> NB;
			FCare C; C.bFed = F; C.bWatered = W; C.bTonic = T;
			OK = GrowCareDays(D, C, R) == N && StepBond(40, C) == NB;
		}
		++Total;
		if (!OK) { ++Bad; std::printf("FAIL %s\n", Line.c_str()); }
	}
	bool Gates = StageAllows(EStage::Pup, ECommand::Come) && !StageAllows(EStage::Pup, ECommand::Stay)
		&& !StageAllows(EStage::Elder, ECommand::Rescue) && !Obeys(100, ECommand::Unknown);
	if (!Gates) { ++Bad; std::printf("FAIL stage gates\n"); }
	std::printf("%s kennel parity %d/%d\n", Bad == 0 && Total > 500 ? "PASS" : "FAIL", Total - Bad, Total);
	return Bad == 0 && Total > 500 ? 0 : 1;
}