// SPDX-License-Identifier: MIT
// G600 Fair Par Calibrator, checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_fair_par_core_test.cpp
//   ./a.out marsh_fair_par_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java): pars from fixed score lists (exact), bot
// schedules and hashes (exact), and bot pars on TRANS01 and REEDREL01 cabinets. Cabinet scores are 1 - crash share over
// seeded runs, so pars must match within one cabinet run and hit shares within two bot runs (a libm last-ulp difference
// could move one borderline run). Also checks budget, ordering and refusal properties.
#include "DaedalusMarshFairParCore.h"
#include "marsh_parity.h"
#include <cstdlib>
#include <sstream>
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Num;

static std::vector<double> List(std::initializer_list<double> V) { return std::vector<double>(V); }

static std::vector<int> ParseCsv(const std::string& V)
{
	std::vector<int> Out;
	std::stringstream Ss(V);
	std::string Part;
	while (std::getline(Ss, Part, ',')) Out.push_back(std::atoi(Part.c_str()));
	return Out;
}

static bool ParsOk(const FairPars& P, const std::string& H, double ParTol, double HitTol)
{
	using marsh_test::Close;
	return P.Runs == marsh_test::Int(H, "runs") && std::fabs(P.Bronze - Num(H, "bronze")) <= ParTol
		&& std::fabs(P.Silver - Num(H, "silver")) <= ParTol && std::fabs(P.Gold - Num(H, "gold")) <= ParTol
		&& std::fabs(P.Perfect - Num(H, "perfect")) <= ParTol && std::fabs(P.BronzeHit - Num(H, "bronzeHit")) <= HitTol
		&& std::fabs(P.SilverHit - Num(H, "silverHit")) <= HitTol && std::fabs(P.GoldHit - Num(H, "goldHit")) <= HitTol
		&& std::fabs(P.Median - Num(H, "median")) <= ParTol && P.Separated() == (marsh_test::Field(H, "separated") == "true");
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_fair_par_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 16 lines", Lines.size() == 16);
	if (Lines.size() != 16) return marsh_test::Summary("marsh fair par core");

	const std::vector<double> Fixed[5] = { List({ 0.5 }), List({ 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 }),
		List({ 0.3, 0.3, 0.3, 0.3 }), List({ 0.9, 0.2, 0.55, 0.7, 0.2, 0.35, 0.8 }),
		List({ 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 }) };
	const double Perfect[5] = { 0.5, 0.95, 0.3, 0.75, 2.0 };
	for (int C = 0; C < 5; ++C)
	{
		bool Ok = false;
		const FairPars P = FairPar::Calibrate(Fixed[C], Perfect[C], Ok);
		Check("fixed " + std::to_string(C), Ok && ParsOk(P, Lines[C], 0, 1e-15));
	}
	for (int R = 0; R < 6; ++R)
	{
		const std::string& H = Lines[5 + R];
		Check("bot run " + std::to_string(R), FairPar::BotSchedule(41, R, 10, 6, 5) == ParseCsv(marsh_test::Field(H, "sched"))
			&& FairPar::Uniform(41, R, 2, 3) == Num(H, "u") && FairPar::Pick(41, R, 1, 0, 6) == marsh_test::Int(H, "pick"));
	}

	const CohortSettings Flocks[2] = { { 0.5, 0.7, 0.85, 0.9, 0.15, 0.45, 30 }, { 0.5, 0.7, 0.85, 0.8, 0.15, 0.45, 30 } };
	// start, budget, perYear, releaseYears, horizon, threshold, sigma, cohort, plan runs, bot runs, flock
	const double Plans[3][11] = { { 12, 10, 6, 5, 30, 10, 0.2, 3, 400, 200, 0 }, { 8, 6, 3, 3, 20, 6, 0.3, 3, 100, 60, 1 },
		{ 12, 8, 4, 4, 25, 10, 0.25, 2, 100, 50, 0 } };
	for (int C = 0; C < 3; ++C)
	{
		const double* Q = Plans[C];
		CohortSettings F = Flocks[static_cast<int>(Q[10])];
		F.Years = C == 0 ? 30 : 10;
		TranslocationSettings S;
		S.Start = static_cast<int>(Q[0]); S.Budget = static_cast<int>(Q[1]); S.PerYear = static_cast<int>(Q[2]);
		S.ReleaseYears = static_cast<int>(Q[3]); S.Horizon = static_cast<int>(Q[4]); S.Threshold = Q[5]; S.Sigma = Q[6];
		S.Cohort = static_cast<int>(Q[7]); S.Runs = static_cast<int>(Q[8]);
		const std::string& H = Lines[11 + C];
		const TranslocationPlan Plan(CraneCohorts(F), S, marsh_test::Int(H, "seed"));
		bool Ok = false;
		const FairPars P = FairPar::Translocation(Plan, static_cast<int>(Q[9]), 600 + C, Ok);
		Check("TRANS01 pars " + std::to_string(C), Ok && ParsOk(P, H, 1.0 / S.Runs + 1e-12, 2.0 / Q[9] + 1e-12));
		Check("TRANS01 ordered " + std::to_string(C), P.Bronze <= P.Silver && P.Silver <= P.Gold && P.Gold <= P.Perfect
			&& P.BronzeHit >= 0.6 && P.SilverHit >= 0.25 && P.GoldHit >= 0.05);
		bool Under = true;
		for (double V : FairPar::TranslocationScores(Plan, static_cast<int>(Q[9]), 600 + C)) Under = Under && V <= P.Perfect + 1e-12;
		Check("TRANS01 bot never beats the optimum " + std::to_string(C), Under && P.Tier(P.Perfect) == FairTier::Perfect);
	}
	const std::vector<double> Reeds[2] = { List({ 10, 25, 40, 55, 80, 110, 150 }), List({ 10, 40, 80, 150 }) };
	const int Rb[2][3] = { { 8, 4, 4 }, { 6, 3, 3 } }, Rh[2] = { 40, 25 }, Rr[2] = { 150, 40 }, Bots[2] = { 120, 60 };
	for (int C = 0; C < 2; ++C)
	{
		ReedReleaseSettings S;
		S.ReedOptions = Reeds[C]; S.StartCranes = 6; S.StartHawks = 3; S.Budget = Rb[C][0]; S.PerYear = Rb[C][1];
		S.ReleaseYears = Rb[C][2]; S.Horizon = Rh[C]; S.Threshold = 4; S.Sigma = 0.15; S.Runs = Rr[C];
		const std::string& H = Lines[14 + C];
		const ReedRelease R(S, marsh_test::Int(H, "seed"));
		bool Ok = false;
		const FairPars P = FairPar::ReedReleasePars(R, Bots[C], 700 + C, Ok);
		Check("REEDREL01 pars " + std::to_string(C), Ok && ParsOk(P, H, 1.0 / S.Runs + 1e-12, 2.0 / Bots[C] + 1e-12));
	}

	// Properties: whole budget within the cap, refusals, tiers.
	bool Budget = true;
	for (int R = 0; R < 300; ++R)
	{
		const std::vector<int> S = FairPar::BotSchedule(5, R, 10, 6, 5);
		int Sum = 0;
		for (int V : S) { Budget = Budget && V >= 0 && V <= 6; Sum += V; }
		Budget = Budget && Sum == 10;
	}
	Check("bot spends the whole budget within the yearly cap", Budget);
	Check("bot refuses a budget that cannot fit", FairPar::BotSchedule(5, 0, 11, 2, 5).empty());
	bool Ok = true;
	FairPar::Calibrate({}, 1, Ok);
	Check("calibrate refuses no scores", !Ok);
	const FairPars T = FairPar::Calibrate(Fixed[4], 2.0, Ok);
	Check("tiers", Ok && T.Tier(0.45) == FairTier::None && T.Tier(0.5) == FairTier::Bronze && T.Tier(0.85) == FairTier::Silver
		&& T.Tier(1.0) == FairTier::Gold && T.Tier(2.0) == FairTier::Perfect && T.Separated());
	return marsh_test::Summary("marsh fair par core");
}
