// SPDX-License-Identifier: MIT
// Fair Par Calibrator (G600, Prismheart balance lane) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/FairPar.java, which stays the rules authority.
// A seeded casual bot plays a marsh cabinet many times; the sorted bot scores (survival = 1 - crash risk) set bronze,
// silver and gold pars so about 60 %, 25 % and 5 % of bot runs reach each tier. The exact optimum is PERFECT and caps
// gold. Separated() is false when the tiers collapse (casual play already lands near the optimum).
// Cabinets (G602): DROUGHT01 (G570), SPREAD01 (G583), COHORTS01 (G585), TRANS01 (G589), REEDCEIL01 (G591), REEDREL01 (G593);
// MarshTable() is the Daedalus par-board hook for all six on their default tuning.
// Golden vectors: engines/unreal/core-test/marsh_fair_par_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: the bot hashes (seed, run, pick, salt) statelessly with the SplitMix64 finalizer, mirroring the Java core.
// It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include "DaedalusMarshCraneSpreadCore.h"
#include "DaedalusMarshDroughtOddsCore.h"
#include "DaedalusMarshReedReleaseCore.h"
#include "DaedalusMarshTranslocationPlanCore.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace daedalus { namespace marsh {

enum class FairTier { None, Bronze, Silver, Gold, Perfect };

struct FairPars
{
	int Runs = 0;
	double Bronze = 0, Silver = 0, Gold = 0, Perfect = 0;
	double BronzeHit = 0, SilverHit = 0, GoldHit = 0, Median = 0;

	bool Separated() const { return Bronze < Silver && Silver < Gold && Gold < Perfect; }
	FairTier Tier(double Score) const
	{
		if (Score >= Perfect) return FairTier::Perfect;
		if (Score >= Gold) return FairTier::Gold;
		if (Score >= Silver) return FairTier::Silver;
		return Score >= Bronze ? FairTier::Bronze : FairTier::None;
	}
};

class FairPar
{
public:
	static constexpr int TierPercent[3] = { 60, 25, 5 };

	static double Uniform(int64_t Seed, int Run, int Pick, int Salt)
	{
		uint64_t Z = static_cast<uint64_t>(Seed) + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Run) + 1)
			+ 0xBF58476D1CE4E5B9ULL * static_cast<uint64_t>(static_cast<int64_t>(Pick) + 1)
			+ 0x94D049BB133111EBULL * static_cast<uint64_t>(static_cast<int64_t>(Salt) + 1);
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z ^= Z >> 31;
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
	static int Pick(int64_t Seed, int Run, int PickIndex, int Salt, int Bound)
	{
		return std::min(Bound, static_cast<int>(Uniform(Seed, Run, PickIndex, Salt) * (Bound + 1)));
	}

	// The casual bot's schedule; empty for a budget that cannot fit (Java throws).
	static std::vector<int> BotSchedule(int64_t Seed, int Run, int Budget, int PerYear, int Years)
	{
		if (Budget < 0 || PerYear < 0 || Years < 1 || static_cast<int64_t>(PerYear) * Years < Budget) return {};
		std::vector<int> Out(static_cast<size_t>(Years), 0);
		int Left = Budget;
		for (int Y = 0; Y < Years; ++Y)
		{
			Out[Y] = Pick(Seed, Run, Y, 0, std::min(PerYear, Left));
			Left -= Out[Y];
		}
		for (int Y = 0; Y < Years && Left > 0; ++Y)
		{
			const int Add = std::min(PerYear - Out[Y], Left);
			Out[Y] += Add;
			Left -= Add;
		}
		return Out;
	}

	// Pars from bot scores and the exact optimum; Ok is false for no scores or a NaN (Java throws).
	static FairPars Calibrate(std::vector<double> Scores, double Perfect, bool& Ok)
	{
		FairPars P;
		Ok = !Scores.empty() && Perfect == Perfect;
		for (double V : Scores) Ok = Ok && V == V;
		if (!Ok) return P;
		std::sort(Scores.begin(), Scores.end());
		const int N = static_cast<int>(Scores.size());
		double Par[3], Hit[3];
		for (int T = 0; T < 3; ++T)
		{
			const int Reach = (N * TierPercent[T] + 99) / 100;
			Par[T] = std::min(Scores[static_cast<size_t>(N - std::max(1, Reach))], Perfect);
			int Count = 0;
			for (double V : Scores) Count += V >= Par[T] ? 1 : 0;
			Hit[T] = static_cast<double>(Count) / N;
		}
		P.Runs = N;
		P.Bronze = Par[0]; P.Silver = Par[1]; P.Gold = Par[2]; P.Perfect = Perfect;
		P.BronzeHit = Hit[0]; P.SilverHit = Hit[1]; P.GoldHit = Hit[2];
		P.Median = Scores[static_cast<size_t>((N - 1) / 2)];
		return P;
	}

	static std::vector<double> TranslocationScores(const TranslocationPlan& Plan, int Runs, int64_t Seed)
	{
		const TranslocationSettings& S = Plan.Settings();
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R) Out.push_back(1 - Plan.Risk(BotSchedule(Seed, R, S.Budget, S.PerYear, S.ReleaseYears)));
		return Out;
	}
	static FairPars Translocation(const TranslocationPlan& Plan, int Runs, int64_t Seed, bool& Ok)
	{
		return Calibrate(TranslocationScores(Plan, Runs, Seed), 1 - Plan.Best().Risk, Ok);
	}

	static std::vector<double> ReedReleaseScores(const ReedRelease& Rr, int Runs, int64_t Seed)
	{
		const ReedReleaseSettings& S = Rr.Settings();
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R)
		{
			const double Ha = S.ReedOptions[static_cast<size_t>(Pick(Seed, R, 0, 1, static_cast<int>(S.ReedOptions.size()) - 1))];
			Out.push_back(1 - Rr.Risk(Ha, BotSchedule(Seed, R, S.Budget, S.PerYear, S.ReleaseYears)));
		}
		return Out;
	}
	static FairPars ReedReleasePars(const ReedRelease& Rr, int Runs, int64_t Seed, bool& Ok)
	{
		return Calibrate(ReedReleaseScores(Rr, Runs, Seed), 1 - Rr.Best().Risk, Ok);
	}
	// COHORTS01: split Birds over the four cohorts, scored in adult equivalents; optimum by trying every split.
	static FairPars Cohorts(const CraneCohorts& Flock, int Birds, int Runs, int64_t Seed, bool& Ok)
	{
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R)
		{
			const std::vector<int> B = BotSchedule(Seed, R, Birds, Birds, CraneCohorts::Cohorts);
			if (B.size() != 4) { Ok = false; return {}; }
			Out.push_back(Flock.AdultEquivalents({ B[0], B[1], B[2], B[3] }));
		}
		int Best = 0;
		for (int A = 0; A <= Birds; ++A)
			for (int B = 0; A + B <= Birds; ++B)
				for (int C = 0; A + B + C <= Birds; ++C) Best = std::max(Best, Flock.AdultEquivalents({ A, B, C, Birds - A - B - C }));
		return Calibrate(Out, Best, Ok);
	}

	// REEDCEIL01: pick a reedbed for one seeded noisy run; score = lowest crane count. Ok false for no options.
	static FairPars ReedCeilingPars(const ReedSettings& Marsh, const std::vector<double>& Options, double Hawks, int Years,
		int64_t RunSeed, int Runs, int64_t Seed, bool& Ok)
	{
		if (Options.empty()) { Ok = false; return {}; }
		std::vector<double> Value;
		double Best = -std::numeric_limits<double>::infinity();
		for (double H : Options)
		{
			const ReedCeiling Rc(Marsh.WithReed(H));
			Value.push_back(Rc.Noisy(Rc.Settings().Capacity() * 0.6, Hawks, Years, RunSeed).MinCranes);
			Best = std::max(Best, Value.back());
		}
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R) Out.push_back(Value[static_cast<size_t>(Pick(Seed, R, 0, 2, static_cast<int>(Options.size()) - 1))]);
		return Calibrate(Out, Best, Ok);
	}

	// DROUGHT01: guess the chance of hitting the threshold within Years; score = 1 - |guess - exact|.
	static FairPars DroughtOddsPars(const DroughtOdds& Odds, double Years, int Runs, int64_t Seed, bool& Ok)
	{
		const double Truth = Odds.Within(Years);
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R) Out.push_back(1 - std::fabs(Uniform(Seed, R, 0, 3) - Truth));
		return Calibrate(Out, 1, Ok);
	}

	// SPREAD01: guess the year the seeded front first reaches Km (never = last year); score = 1 - |error| / years.
	static FairPars CraneSpreadPars(const CraneSpread& Marsh, double Km, int64_t RunSeed, int Runs, int64_t Seed, bool& Ok)
	{
		const int Years = Marsh.Settings().Years;
		const int Reached = Marsh.Run(RunSeed).YearReached(Km);
		const int Truth = Reached < 0 ? Years : Reached;
		std::vector<double> Out;
		for (int R = 0; R < Runs; ++R) Out.push_back(1 - static_cast<double>(std::abs(Pick(Seed, R, 0, 4, Years) - Truth)) / Years);
		return Calibrate(Out, 1, Ok);
	}

	// Daedalus hook: the Prismheart par board for the six marsh cabinets on their default tuning (same order and seeds
	// as Java's marshTable()).
	static std::vector<std::pair<std::string, FairPars>> MarshTable(bool& Ok)
	{
		std::vector<std::pair<std::string, FairPars>> Out;
		bool All = true, One = false;
		Out.emplace_back("DROUGHT01", DroughtOddsPars(DroughtOdds(DroughtSettings()), 20, 200, 800, One)); All = All && One;
		SpreadSettings Sp; Sp.Years = 40;
		Out.emplace_back("SPREAD01", CraneSpreadPars(CraneSpread(Sp), 5, 11, 200, 801, One)); All = All && One;
		const CraneCohorts Flock{ CohortSettings() };
		Out.emplace_back("COHORTS01", Cohorts(Flock, 12, 200, 802, One)); All = All && One;
		Out.emplace_back("TRANS01", Translocation(TranslocationPlan(Flock, TranslocationSettings(), 7), 200, 600, One)); All = All && One;
		Out.emplace_back("REEDCEIL01", ReedCeilingPars(ReedSettings(), { 10, 25, 40, 55, 80, 110, 150 }, 5, 40, 17, 200, 804, One));
		All = All && One;
		Out.emplace_back("REEDREL01", ReedReleasePars(ReedRelease(ReedReleaseSettings(), 23), 120, 700, One)); All = All && One;
		Ok = All;
		return Out;
	}
};

}} // namespace daedalus::marsh
