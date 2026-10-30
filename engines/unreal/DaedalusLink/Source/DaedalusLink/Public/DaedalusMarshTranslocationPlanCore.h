// SPDX-License-Identifier: MIT
// Translocation Plan (G251, C++ port G589) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/TranslocationPlan.java, which stays the rules
// authority. Plans how to spend an aviary budget of birds over the first release years so the G194 Leslie flock
// (DaedalusMarshCraneCohortsCore.h) is least likely to fall below a crash threshold under log-normal environmental
// shocks. All schedules share the same hashed shocks (common random numbers). Best() searches every schedule; Greedy()
// adds one bird at a time.
// Golden vectors: engines/unreal/core-test/marsh_translocation_plan_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in G570/G583/G585, the Java core hashes (seed, run, year, salt) statelessly with the SplitMix64
// finalizer. Uniform() mirrors that hash. It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include "DaedalusMarshCraneCohortsCore.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace marsh {

struct TranslocationSettings
{
	int Start = 12;
	int Budget = 10;
	int PerYear = 6;
	int ReleaseYears = 5;
	int Horizon = 30;
	double Threshold = 10;
	double Sigma = 0.2;
	int Cohort = CraneCohorts::Adult;
	int Runs = 400;

	bool Valid() const
	{
		return !(Start < 0 || Budget < 0 || PerYear < 0 || ReleaseYears < 1 || Horizon < ReleaseYears || !(Threshold > 0)
			|| !(Sigma >= 0) || std::isinf(Sigma) || Cohort < 0 || Cohort >= CraneCohorts::Cohorts || Runs < 1
			|| static_cast<int64_t>(PerYear) * ReleaseYears < Budget);
	}
};

struct TranslocationPlanResult
{
	std::vector<int> Schedule;
	double Risk = 0;
	int Total() const
	{
		int S = 0;
		for (int V : Schedule) S += V;
		return S;
	}
};

namespace transloc_detail {
inline uint64_t Mix(uint64_t Z)
{
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
	return Z ^ (Z >> 31);
}
inline uint64_t AsBits(int64_t V) { return static_cast<uint64_t>(V); }
// Java: mix(seed ^ C); mix(h ^ ((long) run << 32 | (t & 0xFFFFFFFFL))); mix(h ^ salt).
inline double Uniform(int64_t Seed, int Run, int T, int Salt)
{
	uint64_t H = Mix(AsBits(Seed) ^ 0x6A09E667F3BCC909ull);
	H = Mix(H ^ ((AsBits(Run) << 32) | (AsBits(T) & 0xFFFFFFFFull)));
	H = Mix(H ^ AsBits(Salt));
	return static_cast<double>(H >> 11) * 0x1.0p-53;
}
inline double Normal(int64_t Seed, int Run, int T)
{
	const double U1 = std::fmax(Uniform(Seed, Run, T, 0), 1e-300);
	const double U2 = Uniform(Seed, Run, T, 1);
	return std::sqrt(-2 * std::log(U1)) * std::cos(2 * 3.141592653589793 * U2);
}
} // namespace transloc_detail

class TranslocationPlan
{
public:
	TranslocationPlan(const CraneCohorts& InFlock, const TranslocationSettings& In, int64_t Seed) : Flock(InFlock), S(In)
	{
		Shock.assign(static_cast<size_t>(S.Runs) * S.Horizon, 0.0);
		const double Sg = S.Sigma;
		for (int R = 0; R < S.Runs; ++R)
			for (int T = 0; T < S.Horizon; ++T)
				Shock[static_cast<size_t>(R) * S.Horizon + T] = std::exp(Sg * transloc_detail::Normal(Seed, R, T) - Sg * Sg / 2);
	}
	const TranslocationSettings& Settings() const { return S; }

	// Crash risk of a schedule (one entry per release year); -1 for a bad schedule (Java throws).
	double Risk(const std::vector<int>& Schedule) const
	{
		if (!ValidSchedule(Schedule)) return -1;
		int Crashes = 0;
		for (int R = 0; R < S.Runs; ++R)
			if (Crashes_(Schedule, R)) ++Crashes;
		return static_cast<double>(Crashes) / S.Runs;
	}

	TranslocationPlanResult Best() const
	{
		std::vector<int> Cur(S.ReleaseYears, 0);
		TranslocationPlanResult Holder;
		bool Have = false;
		Search(0, S.Budget, Cur, Holder, Have);
		return Holder;
	}

	TranslocationPlanResult Greedy() const
	{
		std::vector<int> Cur(S.ReleaseYears, 0);
		for (int B = 0; B < S.Budget; ++B)
		{
			int BestYear = -1;
			double BestRisk = std::numeric_limits<double>::infinity();
			for (int Y = 0; Y < static_cast<int>(Cur.size()); ++Y)
			{
				if (Cur[Y] >= S.PerYear) continue;
				++Cur[Y];
				const double R = Risk(Cur);
				--Cur[Y];
				if (R < BestRisk) { BestRisk = R; BestYear = Y; }
			}
			++Cur[BestYear];
		}
		return { Cur, Risk(Cur) };
	}

	std::vector<int> FrontLoaded() const
	{
		std::vector<int> Out(S.ReleaseYears, 0);
		int Left = S.Budget;
		for (size_t Y = 0; Y < Out.size() && Left > 0; ++Y)
		{
			Out[Y] = std::min(S.PerYear, Left);
			Left -= Out[Y];
		}
		return Out;
	}

	std::vector<int> Even() const
	{
		std::vector<int> Out(S.ReleaseYears, 0);
		const int N = S.ReleaseYears;
		for (int Y = 0; Y < N; ++Y) Out[Y] = S.Budget / N + (Y < S.Budget % N ? 1 : 0);
		return Out;
	}

private:
	CraneCohorts Flock;
	TranslocationSettings S;
	std::vector<double> Shock;

	bool ValidSchedule(const std::vector<int>& Schedule) const
	{
		if (static_cast<int>(Schedule.size()) != S.ReleaseYears) return false;
		for (int V : Schedule)
			if (V < 0 || V > S.PerYear) return false;
		return true;
	}

	void Search(int Year, int Left, std::vector<int>& Cur, TranslocationPlanResult& Holder, bool& Have) const
	{
		if (Year == static_cast<int>(Cur.size()) - 1)
		{
			if (Left > S.PerYear) return;
			Cur[Year] = Left;
			const double R = Risk(Cur);
			if (!Have || R < Holder.Risk) { Holder = { Cur, R }; Have = true; }
			Cur[Year] = 0;
			return;
		}
		for (int K = std::min(Left, S.PerYear); K >= 0; --K)
		{
			Cur[Year] = K;
			Search(Year + 1, Left - K, Cur, Holder, Have);
		}
		Cur[Year] = 0;
	}

	bool Crashes_(const std::vector<int>& Schedule, int Run) const
	{
		CraneCohorts::Vec N{};
		N[CraneCohorts::Adult] = S.Start;
		for (int T = 0; T < S.Horizon; ++T)
		{
			if (T < static_cast<int>(Schedule.size())) N[S.Cohort] += Schedule[T];
			N = Flock.Step(N);
			const double F = Shock[static_cast<size_t>(Run) * S.Horizon + T];
			double Total = 0;
			for (double& V : N) { V *= F; Total += V; }
			if (Total < S.Threshold) return true;
		}
		return false;
	}
};

}} // namespace daedalus::marsh
