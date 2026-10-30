// SPDX-License-Identifier: MIT
// Fair Par Calibrator (G600, Prismheart balance lane) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/FairPar.java, which stays the rules authority.
// A seeded casual bot plays a marsh cabinet many times; the sorted bot scores (survival = 1 - crash risk) set bronze,
// silver and gold pars so about 60 %, 25 % and 5 % of bot runs reach each tier. The exact optimum is PERFECT and caps
// gold. Separated() is false when the tiers collapse (casual play already lands near the optimum).
// Cabinets: TRANS01 (DaedalusMarshTranslocationPlanCore.h) and REEDREL01 (DaedalusMarshReedReleaseCore.h).
// Golden vectors: engines/unreal/core-test/marsh_fair_par_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: the bot hashes (seed, run, pick, salt) statelessly with the SplitMix64 finalizer, mirroring the Java core.
// It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include "DaedalusMarshReedReleaseCore.h"
#include "DaedalusMarshTranslocationPlanCore.h"
#include <algorithm>
#include <cstdint>
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
};

}} // namespace daedalus::marsh
