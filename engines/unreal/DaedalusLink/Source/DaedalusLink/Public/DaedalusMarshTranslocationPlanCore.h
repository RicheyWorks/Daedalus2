// SPDX-License-Identifier: MIT
// Translocation Plan (G251, C++ port G589) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/TranslocationPlan.java, which stays the rules
// authority. Plans how to spend an aviary budget of birds over the first release years so the G194 Leslie flock
// (DaedalusMarshCraneCohortsCore.h) is least likely to fall below a crash threshold under log-normal environmental
// shocks. All schedules share the same hashed shocks (common random numbers). Best() searches every schedule; Greedy()
// adds one bird at a time. BackLoaded(), RiskInterval() (Wilson 95 %), Problem(), Survival(), the pruned search, Polish(),
// GreedyPolished() and CohortRisks() came with the G589 iterations.
// Golden vectors: engines/unreal/core-test/marsh_translocation_plan_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in G570/G583/G585, the Java core hashes (seed, run, year, salt) statelessly with the SplitMix64
// finalizer. Uniform() mirrors that hash. It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include "DaedalusMarshCraneCohortsCore.h"
#include <algorithm>
#include <array>
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

	// The first reason this tuning cannot run, or nullptr if it can (same order and strings as Java's problem()).
	const char* Problem() const
	{
		if (Start < 0) return "start must be at least 0";
		if (Budget < 0) return "budget must be at least 0";
		if (PerYear < 0) return "perYear must be at least 0";
		if (ReleaseYears < 1) return "releaseYears must be at least 1";
		if (Horizon < ReleaseYears) return "horizon must cover the release years";
		if (!(Threshold > 0)) return "threshold must be above 0";
		if (!(Sigma >= 0) || std::isinf(Sigma)) return "sigma must be finite and at least 0";
		if (Cohort < 0 || Cohort >= CraneCohorts::Cohorts) return "cohort must be a G194 cohort index";
		if (Runs < 1) return "runs must be at least 1";
		if (static_cast<int64_t>(PerYear) * ReleaseYears < Budget) return "budget does not fit perYear x releaseYears";
		return nullptr;
	}
	bool Valid() const { return Problem() == nullptr; }
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
	TranslocationPlan(const CraneCohorts& InFlock, const TranslocationSettings& In, int64_t Seed) : Flock(InFlock), S(In), SeedValue(Seed)
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

	// Local search: move one bird from year I to year J (first improving move, I then J ascending) while the risk
	// strictly drops. Schedule empty and risk -1 for a bad start.
	TranslocationPlanResult Polish(std::vector<int> Cur) const
	{
		double R = Risk(Cur);
		if (R < 0) return { {}, -1 };
		bool Moved = true;
		const int N = static_cast<int>(Cur.size());
		while (Moved && R > 0)
		{
			Moved = false;
			for (int I = 0; I < N && !Moved; ++I)
				for (int J = 0; J < N && !Moved; ++J)
				{
					if (I == J || Cur[I] == 0 || Cur[J] >= S.PerYear) continue;
					--Cur[I];
					++Cur[J];
					const double Next = Risk(Cur);
					if (Next < R) { R = Next; Moved = true; }
					else { ++Cur[I]; --Cur[J]; }
				}
		}
		return { Cur, R };
	}

	TranslocationPlanResult GreedyPolished() const { return Polish(Greedy().Schedule); }

	// Polished-greedy risk for releasing into each G194 cohort, on the same shocks.
	std::array<double, 4> CohortRisks() const
	{
		std::array<double, 4> Out{};
		for (int C = 0; C < CraneCohorts::Cohorts; ++C)
		{
			TranslocationSettings Sc = S;
			Sc.Cohort = C;
			Out[C] = TranslocationPlan(Flock, Sc, SeedValue).GreedyPolished().Risk;
		}
		return Out;
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

	// Share of runs not yet crashed by the census at the end of each year (horizon entries); empty for a bad schedule.
	std::vector<double> Survival(const std::vector<int>& Schedule) const
	{
		if (!ValidSchedule(Schedule)) return {};
		std::vector<int> CrashedBy(S.Horizon, 0);
		for (int R = 0; R < S.Runs; ++R)
		{
			const int Year = FirstCrash(Schedule, R);
			if (Year >= 0) ++CrashedBy[Year];
		}
		std::vector<double> Out(S.Horizon);
		int Crashed = 0;
		for (int T = 0; T < S.Horizon; ++T)
		{
			Crashed += CrashedBy[T];
			Out[T] = 1 - static_cast<double>(Crashed) / S.Runs;
		}
		return Out;
	}

	// Every bird as late as possible (the last year first).
	std::vector<int> BackLoaded() const
	{
		std::vector<int> Out(S.ReleaseYears, 0);
		int Left = S.Budget;
		for (int Y = S.ReleaseYears - 1; Y >= 0 && Left > 0; --Y)
		{
			Out[Y] = std::min(S.PerYear, Left);
			Left -= Out[Y];
		}
		return Out;
	}

	// 95 % Wilson score interval {low, high} for a schedule's crash risk; {-1, -1} for a bad schedule.
	std::array<double, 2> RiskInterval(const std::vector<int>& Schedule) const
	{
		const double P = Risk(Schedule);
		if (P < 0) return { -1, -1 };
		const double N = S.Runs, Z = 1.959963984540054, Z2 = Z * Z;
		const double Centre = (P + Z2 / (2 * N)) / (1 + Z2 / N);
		const double Half = Z / (1 + Z2 / N) * std::sqrt(P * (1 - P) / N + Z2 / (4 * N * N));
		return { P == 0 ? 0.0 : std::fmax(0.0, Centre - Half), P == 1 ? 1.0 : std::fmin(1.0, Centre + Half) };
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
	int64_t SeedValue = 0;
	std::vector<double> Shock;

	bool ValidSchedule(const std::vector<int>& Schedule) const
	{
		if (static_cast<int>(Schedule.size()) != S.ReleaseYears) return false;
		for (int V : Schedule)
			if (V < 0 || V > S.PerYear) return false;
		return true;
	}

	// Pruned exhaustive search (same answer as scoring every schedule): stop at zero risk, and stop counting a
	// schedule's crashes once they reach the best so far, since only a strictly lower count can replace it.
	void Search(int Year, int Left, std::vector<int>& Cur, TranslocationPlanResult& Holder, bool& Have) const
	{
		if (Have && Holder.Risk == 0) return;
		if (Year == static_cast<int>(Cur.size()) - 1)
		{
			if (Left > S.PerYear) return;
			Cur[Year] = Left;
			const int Limit = Have ? static_cast<int>(std::floor(Holder.Risk * S.Runs + 0.5)) : std::numeric_limits<int>::max();
			int Crashes = 0;
			for (int R = 0; R < S.Runs && Crashes < Limit; ++R)
				if (Crashes_(Cur, R)) ++Crashes;
			if (Crashes < Limit) { Holder = { Cur, static_cast<double>(Crashes) / S.Runs }; Have = true; }
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

	bool Crashes_(const std::vector<int>& Schedule, int Run) const { return FirstCrash(Schedule, Run) >= 0; }

	// First census year the run falls below the threshold, or -1.
	int FirstCrash(const std::vector<int>& Schedule, int Run) const
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
			if (Total < S.Threshold) return T;
		}
		return -1;
	}
};

}} // namespace daedalus::marsh
