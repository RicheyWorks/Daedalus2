// SPDX-License-Identifier: MIT
// Drought Odds (G202, C++ port G570), plain C++17, header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/DroughtOdds.java, which stays the rules
// authority. Quasi-extinction risk of the sky-crane flock under log-normal environmental noise: inverse-Gaussian
// hitting probability within T years (Dennis, Munholland and Scott 1991), ultimate risk, median years, and a seeded
// Monte Carlo check. Golden vectors: engines/unreal/core-test/marsh_drought_odds_parity.txt, written by
// MarshCoresParityTest.java and replayed by marsh_drought_odds_core_test.cpp (floats compared with a tolerance).
//
// Seeding: DroughtOdds hashes (seed, run, step, salt) with the SplitMix64 finalizer rather than drawing from a
// stateful generator. Neither DaedalusPyRandomCore.h (CPython MT19937) nor DaedalusStableRandom.h
// (java.util.SplittableRandom streams) reproduces that hash, so Hash() below mirrors the Java core line for line.
// It is not a new generator.
#pragma once
#include <cmath>
#include <cstdint>
#include <limits>

namespace daedalus { namespace marsh {

struct DroughtSettings
{
	double Mu = 0.028587456851912472;   // ln 1.029, the default G194 flock
	double Sigma = 0.15;
	int Start = 40;
	int Threshold = 10;

	bool Valid() const
	{
		return std::isfinite(Mu) && Sigma > 0 && std::isfinite(Sigma) && Threshold >= 1 && Start > Threshold;
	}
	double Distance() const { return std::log(static_cast<double>(Start) / Threshold); }
};

namespace drought_detail {
inline uint64_t Mix(uint64_t Z)
{
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
	return Z ^ (Z >> 31);
}
// Java: mix(seed ^ C); mix(h ^ ((long) run << 32 | (step & 0xFFFFFFFFL))); mix(h ^ salt).
inline double Uniform(int64_t Seed, int Run, int Step, int Salt)
{
	uint64_t H = Mix(static_cast<uint64_t>(Seed) ^ 0x2545F4914F6CDD1Dull);
	const uint64_t Key = (static_cast<uint64_t>(static_cast<int64_t>(Run)) << 32)
		| (static_cast<uint64_t>(static_cast<int64_t>(Step)) & 0xFFFFFFFFull);
	H = Mix(H ^ Key);
	H = Mix(H ^ static_cast<uint64_t>(static_cast<int64_t>(Salt)));
	return static_cast<double>(H >> 11) * 0x1.0p-53;
}
inline double Normal(int64_t Seed, int Run, int Step)
{
	const double U1 = std::fmax(Uniform(Seed, Run, Step, 0), 1e-300);
	const double U2 = Uniform(Seed, Run, Step, 1);
	return std::sqrt(-2 * std::log(U1)) * std::cos(2 * 3.141592653589793 * U2);
}
} // namespace drought_detail

// Standard normal CDF, Abramowitz and Stegun 7.1.26 (same constants as Java).
inline double Phi(double Z)
{
	const double X = std::fabs(Z) / std::sqrt(2.0);
	const double T = 1 / (1 + 0.3275911 * X);
	const double Y = 1 - (((((1.061405429 * T - 1.453152027) * T) + 1.421413741) * T - 0.284496736) * T
		+ 0.254829592) * T * std::exp(-X * X);
	return Z >= 0 ? 0.5 * (1 + Y) : 0.5 * (1 - Y);
}

class DroughtOdds
{
public:
	explicit DroughtOdds(const DroughtSettings& In) : S(In) {}
	const DroughtSettings& Settings() const { return S; }

	// Chance of reaching the threshold within Years; -1 for negative or NaN years.
	double Within(double Years) const
	{
		if (!(Years >= 0)) return -1;
		if (Years == 0) return 0;
		const double D = S.Distance(), Mu = S.Mu, Sd = S.Sigma * std::sqrt(Years);
		const double First = Phi((-D - Mu * Years) / Sd);
		const double LogW = -2 * Mu * D / (S.Sigma * S.Sigma);
		const double Second = Phi((-D + Mu * Years) / Sd);
		const double G = First + (Second == 0 ? 0 : std::exp(LogW + std::log(Second)));
		return std::fmin(1.0, std::fmax(0.0, G));
	}

	double Ultimate() const
	{
		if (S.Mu <= 0) return 1;
		return std::exp(-2 * S.Mu * S.Distance() / (S.Sigma * S.Sigma));
	}

	// Median years among flocks that do hit (bisection), +infinity if hits are vanishingly rare.
	double MedianYears() const
	{
		const double Target = 0.5 * Ultimate();
		const double Inf = std::numeric_limits<double>::infinity();
		if (Target <= 0) return Inf;
		double Lo = 0, Hi = 1;
		while (Within(Hi) < Target)
		{
			Hi *= 2;
			if (Hi > 1e7) return Inf;
		}
		for (int It = 0; It < 200; ++It)
		{
			const double Mid = (Lo + Hi) / 2;
			if (Within(Mid) < Target) Lo = Mid; else Hi = Mid;
		}
		return (Lo + Hi) / 2;
	}

	// Monte Carlo hits out of Runs within Years (Substeps steps a year); -1 for bad sizes.
	int SimulateHits(int Runs, int Years, int Substeps, int64_t Seed) const
	{
		if (Runs < 1 || Years < 1 || Substeps < 1) return -1;
		const double D = S.Distance(), Dt = 1.0 / Substeps;
		const double Drift = S.Mu * Dt, Sd = S.Sigma * std::sqrt(Dt);
		const int Steps = Years * Substeps;
		int Hits = 0;
		for (int R = 0; R < Runs; ++R)
		{
			double X = 0;
			for (int K = 0; K < Steps; ++K)
			{
				X += Drift + Sd * drought_detail::Normal(Seed, R, K);
				if (X <= -D) { ++Hits; break; }
			}
		}
		return Hits;
	}
	double Simulate(int Runs, int Years, int Substeps, int64_t Seed) const
	{
		const int H = SimulateHits(Runs, Years, Substeps, Seed);
		return H < 0 ? -1 : static_cast<double>(H) / Runs;
	}

private:
	DroughtSettings S;
};

}} // namespace daedalus::marsh
