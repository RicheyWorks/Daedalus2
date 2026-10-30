// SPDX-License-Identifier: MIT
// G251 Translocation Plan C++ port (G589), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_translocation_plan_core_test.cpp
//   ./a.out marsh_translocation_plan_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java): front-loaded, even, best and greedy schedules,
// each with its crash risk, plus back-loaded, the Wilson interval of the best risk and the settings problem strings. Risks are crash counts over seeded runs, so they must match within one run (a libm last-ulp
// difference in exp/log/cos could move one borderline run). Schedules must match exactly.
#include "DaedalusMarshTranslocationPlanCore.h"
#include "marsh_parity.h"
#include <cstdlib>
#include <sstream>
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Num;

static std::vector<int> ParseCsv(const std::string& V)
{
	std::vector<int> Out;
	std::stringstream Ss(V);
	std::string Part;
	while (std::getline(Ss, Part, ',')) Out.push_back(std::atoi(Part.c_str()));
	return Out;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_translocation_plan_parity.txt";
	std::vector<std::string> Lines, Problems;
	for (const std::string& L : marsh_test::ParityLines(Path)) (L.rfind("problem ", 0) == 0 ? Problems : Lines).push_back(L);
	Check("golden file has 9 plans and 12 settings checks", Lines.size() == 9 && Problems.size() == 12);
	const CohortSettings Flocks[3] = { { 0.5, 0.7, 0.85, 0.9, 0.15, 0.45, 10 }, { 0.5, 0.7, 0.85, 0.8, 0.15, 0.45, 10 },
		{ 0.6, 0.8, 0.9, 0.95, 0.3, 1.2, 10 } };
	int Exact = 0, Risks = 0;
	for (size_t L = 0; L < Lines.size(); ++L)
	{
		const std::string& H = Lines[L];
		TranslocationSettings S;
		S.Start = static_cast<int>(marsh_test::Int(H, "start"));
		S.Budget = static_cast<int>(marsh_test::Int(H, "budget"));
		S.PerYear = static_cast<int>(marsh_test::Int(H, "perYear"));
		S.ReleaseYears = static_cast<int>(marsh_test::Int(H, "releaseYears"));
		S.Horizon = static_cast<int>(marsh_test::Int(H, "horizon"));
		S.Threshold = Num(H, "threshold");
		S.Sigma = Num(H, "sigma");
		S.Cohort = static_cast<int>(marsh_test::Int(H, "cohort"));
		S.Runs = static_cast<int>(marsh_test::Int(H, "runs"));
		const std::string Tag = "plan " + std::to_string(L);
		Check(Tag + " valid", S.Valid());
		const TranslocationPlan P(CraneCohorts(Flocks[marsh_test::Int(H, "flock")]), S, marsh_test::Int(H, "seed"));
		const double OneRun = 1.0 / S.Runs + 1e-12;
		auto RiskOk = [&](double Got, const char* Key) {
			const double Want = Num(H, Key);
			++Risks;
			Exact += Got == Want;
			return std::fabs(Got - Want) <= OneRun;
		};
		Check(Tag + " front-loaded", P.FrontLoaded() == ParseCsv(marsh_test::Field(H, "front")) && RiskOk(P.Risk(P.FrontLoaded()), "frontRisk"));
		Check(Tag + " even", P.Even() == ParseCsv(marsh_test::Field(H, "even")) && RiskOk(P.Risk(P.Even()), "evenRisk"));
		Check(Tag + " back-loaded", P.BackLoaded() == ParseCsv(marsh_test::Field(H, "back")) && RiskOk(P.Risk(P.BackLoaded()), "backRisk"));
		const TranslocationPlanResult B = P.Best();
		Check(Tag + " best schedule", B.Schedule == ParseCsv(marsh_test::Field(H, "best")) && B.Total() == S.Budget);
		Check(Tag + " best risk", RiskOk(B.Risk, "bestRisk"));
		const TranslocationPlanResult G = P.Greedy();
		Check(Tag + " greedy schedule", G.Schedule == ParseCsv(marsh_test::Field(H, "greedy")) && G.Total() == S.Budget);
		Check(Tag + " greedy risk", RiskOk(G.Risk, "greedyRisk"));
		const auto Ci = P.RiskInterval(B.Schedule);
		Check(Tag + " Wilson interval", marsh_test::Close(Ci[0], Num(H, "bestLo"), 1e-12) && marsh_test::Close(Ci[1], Num(H, "bestHi"), 1e-12)
			&& Ci[0] <= B.Risk && B.Risk <= Ci[1]);
		{
			const std::vector<double> Sv = P.Survival(B.Schedule);
			std::vector<double> Sample;
			for (size_t T = 0; T < Sv.size(); T += 5) Sample.push_back(Sv[T]);
			Sample.push_back(Sv.back());
			std::stringstream Ws(marsh_test::Field(H, "survival"));
			std::string Part;
			bool SvOk = Sv.size() == static_cast<size_t>(S.Horizon);
			size_t K = 0;
			while (std::getline(Ws, Part, ',')) SvOk = SvOk && K < Sample.size() && marsh_test::Close(Sample[K++], std::strtod(Part.c_str(), nullptr), 1e-12);
			Check(Tag + " survival curve", SvOk && K == Sample.size() && marsh_test::Close(Sv.back(), 1 - B.Risk, 1e-12));
		}
		Check(Tag + " best is no worse than greedy, front or even",
			B.Risk <= G.Risk && B.Risk <= P.Risk(P.FrontLoaded()) && B.Risk <= P.Risk(P.Even()));
	}
	Check("risks identical on every case", Risks == 45 && Exact == Risks);
	for (const std::string& Q : Problems)
	{
		TranslocationSettings S;
		S.Start = static_cast<int>(marsh_test::Int(Q, "start"));
		S.Budget = static_cast<int>(marsh_test::Int(Q, "budget"));
		S.PerYear = static_cast<int>(marsh_test::Int(Q, "perYear"));
		S.ReleaseYears = static_cast<int>(marsh_test::Int(Q, "releaseYears"));
		S.Horizon = static_cast<int>(marsh_test::Int(Q, "horizon"));
		S.Threshold = Num(Q, "threshold");
		S.Sigma = Num(Q, "sigma");
		S.Cohort = static_cast<int>(marsh_test::Int(Q, "cohort"));
		S.Runs = static_cast<int>(marsh_test::Int(Q, "runs"));
		std::string Want = marsh_test::Field(Q, "why");
		for (char& C : Want) if (C == '_') C = ' ';
		const char* Got = S.Problem();
		Check("settings problem: " + Want, Want == "ok" ? Got == nullptr && S.Valid() : Got != nullptr && Want == Got && !S.Valid());
	}

	// Engine-free property checks mirroring TranslocationPlanTest.
	const TranslocationSettings D;
	Check("default settings valid", D.Valid());
	TranslocationSettings Small = D; Small.Runs = 60;
	const TranslocationPlan P(CraneCohorts(CohortSettings()), Small, 3);
	const TranslocationPlan Q(CraneCohorts(CohortSettings()), Small, 3);
	Check("same seed same risk", P.Risk(P.Even()) == Q.Risk(Q.Even()));
	Check("front-loaded fills year 0 first", P.FrontLoaded() == std::vector<int>({ 6, 4, 0, 0, 0 }));
	Check("even spreads the budget", P.Even() == std::vector<int>({ 2, 2, 2, 2, 2 }));
	{
		const std::vector<double> Sv = P.Survival(P.Even());
		bool Falls = true;
		for (size_t T = 1; T < Sv.size(); ++T) Falls = Falls && Sv[T] <= Sv[T - 1];
		Check("survival never rises and rejects a bad schedule", Falls && P.Survival({ 1 }).empty());
	}
	Check("back-loaded fills the last years", P.BackLoaded() == std::vector<int>({ 0, 0, 0, 4, 6 }));
	const auto Bad = P.RiskInterval({ 1, 2 });
	Check("interval rejects a bad schedule", Bad[0] < 0 && Bad[1] < 0);
	TranslocationSettings Calm = Small; Calm.Sigma = 0;
	const TranslocationPlan C(CraneCohorts(CohortSettings()), Calm, 3);
	Check("no noise, growing flock above threshold: no crash", C.Risk(C.Even()) == 0);
	TranslocationSettings Lots = Small; Lots.Threshold = 1e9;
	const TranslocationPlan X(CraneCohorts(CohortSettings()), Lots, 3);
	Check("unreachable threshold: certain crash", X.Risk(X.Even()) == 1);
	{
		// The pruned Best() must equal scoring every schedule (earliest-heavy first, ties keep the first).
		TranslocationSettings E = Small; E.Budget = 7;
		const TranslocationPlan Pe(CraneCohorts(CohortSettings()), E, 7);
		std::vector<int> Odo(E.ReleaseYears, E.PerYear), BestSeen;
		double BestRisk = 2;
		while (true)
		{
			int Sum = 0;
			for (int V : Odo) Sum += V;
			if (Sum == E.Budget) { const double R = Pe.Risk(Odo); if (R < BestRisk) { BestRisk = R; BestSeen = Odo; } }
			int I = E.ReleaseYears - 1;
			while (I >= 0 && Odo[I] == 0) Odo[I--] = E.PerYear;
			if (I < 0) break;
			--Odo[I];
		}
		const TranslocationPlanResult Bp = Pe.Best();
		Check("pruned best equals scoring every schedule", Bp.Risk == BestRisk && Bp.Schedule == BestSeen);
	}
	Check("bad schedules rejected", P.Risk({ 1, 2 }) < 0 && P.Risk({ 7, 0, 0, 0, 0 }) < 0 && P.Risk({ -1, 0, 0, 0, 0 }) < 0);
	TranslocationSettings Bad1 = D; Bad1.PerYear = 1;
	TranslocationSettings Bad2 = D; Bad2.Cohort = 4;
	TranslocationSettings Bad3 = D; Bad3.Horizon = 2;
	TranslocationSettings Bad4 = D; Bad4.Threshold = 0;
	Check("bad settings rejected", !Bad1.Valid() && !Bad2.Valid() && !Bad3.Valid() && !Bad4.Valid());
	return marsh_test::Summary("marsh translocation plan core");
}
