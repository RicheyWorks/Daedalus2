// SPDX-License-Identifier: MIT
// Reed Release (G507, C++ port G593) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/ReedRelease.java, which stays the rules authority.
// G251 Translocation Plan meets G504 Reed Ceiling: choose a reedbed size and a release schedule for aviary cranes.
// The marsh runs the G504 hawk/crane dynamics (DaedalusMarshReedCeilingCore.h) one RK4 season at a time, with seeded
// log-normal crane shocks shared by every plan. Best() is the brute force over reed options and schedules; Fast()
// does a greedy schedule per reed option.
// Golden vectors: engines/unreal/core-test/marsh_reed_release_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in the other marsh ports, the Java core hashes (seed, run, season, salt) statelessly with the SplitMix64
// finalizer. Uniform() mirrors that hash. It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include "DaedalusMarshReedCeilingCore.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace marsh {

struct ReedReleaseSettings
{
	ReedSettings Marsh;
	std::vector<double> ReedOptions = { 10, 25, 40, 55, 80, 110, 150 };
	double StartCranes = 6;
	double StartHawks = 3;
	int Budget = 8;
	int PerYear = 4;
	int ReleaseYears = 4;
	int Horizon = 40;
	double Threshold = 4;
	double Sigma = 0.15;
	int Runs = 150;

	bool Valid() const
	{
		if (ReedOptions.empty() || !(StartCranes >= 0) || !(StartHawks >= 0) || Budget < 0 || PerYear < 0
			|| ReleaseYears < 1 || Horizon <= ReleaseYears || !(Threshold > 0) || !(Sigma >= 0) || std::isinf(Sigma)
			|| Runs < 1 || static_cast<int64_t>(PerYear) * ReleaseYears < Budget || !Marsh.Valid())
			return false;
		for (double H : ReedOptions)
			if (!(H > 0) || std::isinf(H)) return false;
		return true;
	}
};

struct ReedReleasePlan
{
	double Hectares = 0;
	std::vector<int> Schedule;
	double Risk = 0;
};

namespace reedrel_detail {
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
	uint64_t H = Mix(AsBits(Seed) ^ 0x3C6EF372FE94F82Bull);
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
} // namespace reedrel_detail

class ReedRelease
{
public:
	ReedRelease(const ReedReleaseSettings& In, int64_t Seed) : S(In)
	{
		Shock.assign(static_cast<size_t>(S.Runs) * S.Horizon, 0.0);
		const double Sg = S.Sigma;
		for (int R = 0; R < S.Runs; ++R)
			for (int T = 0; T < S.Horizon; ++T)
				Shock[static_cast<size_t>(R) * S.Horizon + T] = std::exp(Sg * reedrel_detail::Normal(Seed, R, T) - Sg * Sg / 2);
	}
	const ReedReleaseSettings& Settings() const { return S; }

	// Crash risk for a reedbed and schedule; -1 for a bad schedule or reedbed (Java throws).
	double Risk(double Hectares, const std::vector<int>& Schedule) const
	{
		if (!ValidSchedule(Schedule)) return -1;
		const ReedSettings Ms = S.Marsh.WithReed(Hectares);
		if (!Ms.Valid()) return -1;
		const ReedCeiling M(Ms);
		int Crashes = 0;
		for (int R = 0; R < S.Runs; ++R)
			if (Crashes_(M, Schedule, R)) ++Crashes;
		return static_cast<double>(Crashes) / S.Runs;
	}

	ReedReleasePlan Best() const
	{
		ReedReleasePlan Out;
		bool Have = false;
		for (double H : S.ReedOptions)
		{
			const ReedReleasePlan P = BestSchedule(H);
			if (!Have || P.Risk < Out.Risk) { Out = P; Have = true; }
		}
		return Out;
	}

	ReedReleasePlan BestSchedule(double Hectares) const
	{
		std::vector<int> Cur(S.ReleaseYears, 0);
		ReedReleasePlan Holder;
		bool Have = false;
		Search(Hectares, 0, S.Budget, Cur, Holder, Have);
		return Holder;
	}

	ReedReleasePlan Fast() const
	{
		ReedReleasePlan Out;
		bool Have = false;
		for (double H : S.ReedOptions)
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
					const double R = Risk(H, Cur);
					--Cur[Y];
					if (R < BestRisk) { BestRisk = R; BestYear = Y; }
				}
				++Cur[BestYear];
			}
			const ReedReleasePlan P{ H, Cur, Risk(H, Cur) };
			if (!Have || P.Risk < Out.Risk) { Out = P; Have = true; }
		}
		return Out;
	}

private:
	static constexpr double Dt = 0.05;
	static constexpr int Steps = 20;
	ReedReleaseSettings S;
	std::vector<double> Shock;

	bool ValidSchedule(const std::vector<int>& Schedule) const
	{
		if (static_cast<int>(Schedule.size()) != S.ReleaseYears) return false;
		for (int V : Schedule)
			if (V < 0 || V > S.PerYear) return false;
		return true;
	}

	void Search(double H, int Year, int Left, std::vector<int>& Cur, ReedReleasePlan& Holder, bool& Have) const
	{
		if (Year == static_cast<int>(Cur.size()) - 1)
		{
			if (Left > S.PerYear) return;
			Cur[Year] = Left;
			const double R = Risk(H, Cur);
			if (!Have || R < Holder.Risk) { Holder = { H, Cur, R }; Have = true; }
			Cur[Year] = 0;
			return;
		}
		for (int K = std::min(Left, S.PerYear); K >= 0; --K)
		{
			Cur[Year] = K;
			Search(H, Year + 1, Left - K, Cur, Holder, Have);
		}
		Cur[Year] = 0;
	}

	bool Crashes_(const ReedCeiling& M, const std::vector<int>& Schedule, int Run) const
	{
		double N = S.StartCranes, P = S.StartHawks;
		const int Len = static_cast<int>(Schedule.size());
		for (int T = 0; T < S.Horizon; ++T)
		{
			if (T < Len) N += Schedule[T];
			for (int I = 0; I < Steps; ++I)
			{
				const auto K1 = M.Rate(N, P);
				const auto K2 = M.Rate(N + Dt / 2 * K1[0], P + Dt / 2 * K1[1]);
				const auto K3 = M.Rate(N + Dt / 2 * K2[0], P + Dt / 2 * K2[1]);
				const auto K4 = M.Rate(N + Dt * K3[0], P + Dt * K3[1]);
				N = std::max(0.0, N + Dt / 6 * (K1[0] + 2 * K2[0] + 2 * K3[0] + K4[0]));
				P = std::max(0.0, P + Dt / 6 * (K1[1] + 2 * K2[1] + 2 * K3[1] + K4[1]));
			}
			N *= Shock[static_cast<size_t>(Run) * S.Horizon + T];
			if (T >= Len && N < S.Threshold) return true;
		}
		return false;
	}
};

}} // namespace daedalus::marsh
