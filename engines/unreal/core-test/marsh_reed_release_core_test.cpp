// SPDX-License-Identifier: MIT
// G507 Reed Release C++ port (G593), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_reed_release_core_test.cpp
//   ./a.out marsh_reed_release_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java) for 4 plans: the exhaustive best schedule per reed
// option with its risk, the overall best, and the greedy fast plan. Risks are crash counts over seeded runs, so the
// test allows one run of slack (exp/log/cos may differ in the last ulp), but expects every risk to match exactly here.
// Schedules and chosen reedbeds must match exactly.
#include "DaedalusMarshReedReleaseCore.h"
#include "marsh_parity.h"
#include <cstdlib>
#include <sstream>
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Num;

template <typename T> static std::vector<T> ParseCsv(const std::string& V)
{
	std::vector<T> Out;
	std::stringstream Ss(V);
	std::string Part;
	while (std::getline(Ss, Part, ',')) Out.push_back(static_cast<T>(std::strtod(Part.c_str(), nullptr)));
	return Out;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_reed_release_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 4 plans", Lines.size() == 4);
	int Risks = 0, Exact = 0;
	for (size_t L = 0; L < Lines.size(); ++L)
	{
		const std::string& H = Lines[L];
		ReedReleaseSettings S;
		S.ReedOptions = ParseCsv<double>(marsh_test::Field(H, "reed"));
		S.StartCranes = Num(H, "n0"); S.StartHawks = Num(H, "p0");
		S.Budget = static_cast<int>(marsh_test::Int(H, "budget")); S.PerYear = static_cast<int>(marsh_test::Int(H, "perYear"));
		S.ReleaseYears = static_cast<int>(marsh_test::Int(H, "releaseYears")); S.Horizon = static_cast<int>(marsh_test::Int(H, "horizon"));
		S.Threshold = Num(H, "threshold"); S.Sigma = Num(H, "sigma"); S.Runs = static_cast<int>(marsh_test::Int(H, "runs"));
		const std::string Tag = "plan " + std::to_string(L);
		Check(Tag + " valid", S.Valid());
		const ReedRelease R(S, marsh_test::Int(H, "seed"));
		const double OneRun = 1.0 / S.Runs + 1e-12;
		auto RiskOk = [&](double Got, const std::string& Key) {
			const double Want = Num(H, Key);
			++Risks;
			Exact += Got == Want;
			return std::fabs(Got - Want) <= OneRun;
		};
		bool PerReed = true;
		for (size_t I = 0; I < S.ReedOptions.size(); ++I)
		{
			const ReedReleasePlan P = R.BestSchedule(S.ReedOptions[I]);
			const std::string Si = std::to_string(I);
			PerReed = PerReed && P.Schedule == ParseCsv<int>(marsh_test::Field(H, "sched" + Si)) && RiskOk(P.Risk, "risk" + Si);
		}
		Check(Tag + " best schedule per reed option", PerReed);
		const ReedReleasePlan B = R.Best(), F = R.Fast();
		Check(Tag + " best plan", B.Hectares == Num(H, "bestHa") && B.Schedule == ParseCsv<int>(marsh_test::Field(H, "best")) && RiskOk(B.Risk, "bestRisk"));
		Check(Tag + " fast plan", F.Hectares == Num(H, "fastHa") && F.Schedule == ParseCsv<int>(marsh_test::Field(H, "fast")) && RiskOk(F.Risk, "fastRisk"));
		Check(Tag + " brute force no worse than greedy", B.Risk <= F.Risk);
	}
	Check("every risk identical", Risks > 0 && Exact == Risks);

	// Engine-free property checks mirroring ReedReleaseTest.
	ReedReleaseSettings D;
	Check("default settings valid", D.Valid());
	D.Runs = 30;
	const ReedRelease P(D, 5), Q(D, 5);
	const std::vector<int> Even = { 2, 2, 2, 2 };
	Check("same seed same risk", P.Risk(40, Even) == Q.Risk(40, Even) && P.Risk(40, Even) >= 0 && P.Risk(40, Even) <= 1);
	Check("bad schedules and reedbeds rejected", P.Risk(40, { 1, 1 }) < 0 && P.Risk(40, { 5, 0, 0, 0 }) < 0
		&& P.Risk(0, Even) < 0 && P.Risk(-3, Even) < 0);
	ReedReleaseSettings Calm = D; Calm.Sigma = 0; Calm.Threshold = 1e-9; Calm.Horizon = 10;
	Check("unreachable crash: zero risk", ReedRelease(Calm, 1).Risk(40, Even) == 0);
	ReedReleaseSettings Doom = D; Doom.Threshold = 1e9; Doom.Horizon = 10;
	Check("unreachable ceiling: certain crash", ReedRelease(Doom, 1).Risk(40, Even) == 1);
	ReedReleaseSettings Bad1 = D; Bad1.ReedOptions.clear();
	ReedReleaseSettings Bad2 = D; Bad2.ReedOptions.push_back(0);
	ReedReleaseSettings Bad3 = D; Bad3.Horizon = 4;
	ReedReleaseSettings Bad4 = D; Bad4.PerYear = 1;
	Check("bad settings rejected", !Bad1.Valid() && !Bad2.Valid() && !Bad3.Valid() && !Bad4.Valid());
	return marsh_test::Summary("marsh reed release core");
}
