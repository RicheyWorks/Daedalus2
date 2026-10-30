// SPDX-License-Identifier: MIT
// Reed Ceiling (G504, C++ port G591) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/ReedCeiling.java, which stays the rules authority.
// Marsh hawks and sky-cranes as a Rosenzweig-MacArthur predator-prey model, with the reedbed setting crane capacity
// K. It gives the equilibrium (N*, P*), the Hopf capacity K_H = 2 N* + 1/(a h) (the paradox of enrichment), the regime,
// the Jacobian trace, a plain RK4 run, and yearly seasons with seeded log-normal crane shocks. FromCohorts takes
// r = ln lambda from the G194 flock (DaedalusMarshCraneCohortsCore.h).
// Golden vectors: engines/unreal/core-test/marsh_reed_ceiling_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in the other marsh ports, the Java core hashes (seed, year, salt) statelessly with the SplitMix64
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

struct ReedSettings
{
	double R = 0.4;
	double ReedHectares = 40;
	double CranesPerHectare = 2;
	double Attack = 0.02;
	double Handling = 0.5;
	double Conversion = 0.6;
	double Mortality = 0.15;

	static bool Pos(double X) { return X > 0 && !std::isinf(X); }
	bool Valid() const
	{
		return Pos(R) && Pos(ReedHectares) && Pos(CranesPerHectare) && Pos(Attack) && Pos(Handling) && Pos(Conversion)
			&& Pos(Mortality) && Conversion > Mortality * Handling;
	}
	double Capacity() const { return ReedHectares * CranesPerHectare; }
	ReedSettings WithReed(double Hectares) const { ReedSettings C = *this; C.ReedHectares = Hectares; return C; }
	ReedSettings WithGrowth(double Growth) const { ReedSettings C = *this; C.R = Growth; return C; }
};

enum class ReedRegime { NoHawks, Stable, Cycles };

struct ReedPoint
{
	double Year = 0, Cranes = 0, Hawks = 0;
};

struct ReedRun
{
	std::vector<ReedPoint> Points;
	double MinCranes = 0, MaxCranes = 0, FinalHawks = 0;
	bool Ok = true; // false where Java throws
	double Amplitude() const { return MaxCranes - MinCranes; }
};

namespace reed_detail {
inline uint64_t Mix(uint64_t Z)
{
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
	return Z ^ (Z >> 31);
}
// Java: mix(seed ^ C); mix(h ^ y); mix(h ^ salt).
inline double Uniform(int64_t Seed, int Year, int Salt)
{
	uint64_t H = Mix(static_cast<uint64_t>(Seed) ^ 0xBB67AE8584CAA73Bull);
	H = Mix(H ^ static_cast<uint64_t>(static_cast<int64_t>(Year)));
	H = Mix(H ^ static_cast<uint64_t>(static_cast<int64_t>(Salt)));
	return static_cast<double>(H >> 11) * 0x1.0p-53;
}
inline double Normal(int64_t Seed, int Year)
{
	const double U1 = std::fmax(Uniform(Seed, Year, 0), 1e-300);
	const double U2 = Uniform(Seed, Year, 1);
	return std::sqrt(-2 * std::log(U1)) * std::cos(2 * 3.141592653589793 * U2);
}
// Java (int) Math.round for the step counts that occur here (non-negative, well inside int range).
inline int RoundInt(double X) { return static_cast<int>(std::floor(X + 0.5)); }
} // namespace reed_detail

class ReedCeiling
{
public:
	explicit ReedCeiling(const ReedSettings& In) : S(In) {}

	// r = ln lambda of a growing G194 flock; Ok is false (Java throws) when the flock does not grow.
	static ReedCeiling FromCohorts(const CraneCohorts& Flock, const ReedSettings& In, bool& Ok)
	{
		Ok = Flock.GetLambda() > 1;
		return ReedCeiling(Ok ? In.WithGrowth(std::log(Flock.GetLambda())) : In);
	}

	const ReedSettings& Settings() const { return S; }

	double CranesStar() const { return S.Mortality / (S.Attack * (S.Conversion - S.Mortality * S.Handling)); }
	double HawksStar() const
	{
		const double N = CranesStar(), K = S.Capacity();
		if (K <= N) return 0;
		return (S.R / S.Attack) * (1 - N / K) * (1 + S.Attack * S.Handling * N);
	}
	double HopfCapacity() const { return 2 * CranesStar() + 1 / (S.Attack * S.Handling); }
	double CycleHectares() const { return HopfCapacity() / S.CranesPerHectare; }
	double HawkHectares() const { return CranesStar() / S.CranesPerHectare; }
	ReedRegime Regime() const
	{
		const double K = S.Capacity();
		if (K <= CranesStar()) return ReedRegime::NoHawks;
		return K < HopfCapacity() ? ReedRegime::Stable : ReedRegime::Cycles;
	}

	std::array<double, 2> Rate(double N, double P) const
	{
		const double Eat = S.Attack * N * P / (1 + S.Attack * S.Handling * N);
		return { S.R * N * (1 - N / S.Capacity()) - Eat, S.Conversion * Eat - S.Mortality * P };
	}

	double Trace() const
	{
		const double N = CranesStar(), K = S.Capacity(), Ah = S.Attack * S.Handling;
		return S.R * N * Ah * (K - 1 / Ah - 2 * N) / (K * (1 + Ah * N));
	}

	ReedRun Integrate(double N0, double P0, double Years, double Dt) const
	{
		ReedRun Out;
		if (!(N0 >= 0) || !(P0 >= 0) || !(Years > 0) || !(Dt > 0) || Dt > 1) { Out.Ok = false; return Out; }
		double N = N0, P = P0;
		const int Steps = reed_detail::RoundInt(Years / Dt);
		const int PerYear = std::max(1, reed_detail::RoundInt(1 / Dt));
		const int Tail = Steps - Steps / 4;
		double Lo = std::numeric_limits<double>::infinity(), Hi = 0;
		Out.Points.push_back({ 0, N, P });
		for (int I = 1; I <= Steps; ++I)
		{
			const auto K1 = Rate(N, P);
			const auto K2 = Rate(N + Dt / 2 * K1[0], P + Dt / 2 * K1[1]);
			const auto K3 = Rate(N + Dt / 2 * K2[0], P + Dt / 2 * K2[1]);
			const auto K4 = Rate(N + Dt * K3[0], P + Dt * K3[1]);
			N = std::max(0.0, N + Dt / 6 * (K1[0] + 2 * K2[0] + 2 * K3[0] + K4[0]));
			P = std::max(0.0, P + Dt / 6 * (K1[1] + 2 * K2[1] + 2 * K3[1] + K4[1]));
			if (I >= Tail) { Lo = std::min(Lo, N); Hi = std::max(Hi, N); }
			if (I % PerYear == 0) Out.Points.push_back({ I * Dt, N, P });
		}
		Out.MinCranes = Lo;
		Out.MaxCranes = Hi;
		Out.FinalHawks = P;
		return Out;
	}

	ReedRun Noisy(double N0, double P0, int Years, int64_t Seed) const
	{
		ReedRun Out;
		if (Years < 1) { Out.Ok = false; return Out; }
		double N = N0, P = P0;
		const double Sigma = 0.1;
		double Lo = std::numeric_limits<double>::infinity(), Hi = 0;
		Out.Points.push_back({ 0, N, P });
		for (int Y = 1; Y <= Years; ++Y)
		{
			const ReedRun Season = Integrate(N, P, 1, 0.05);
			const ReedPoint& Last = Season.Points.back();
			N = Last.Cranes * std::exp(Sigma * reed_detail::Normal(Seed, Y) - Sigma * Sigma / 2);
			P = Last.Hawks;
			if (Y > Years - Years / 4) { Lo = std::min(Lo, N); Hi = std::max(Hi, N); }
			Out.Points.push_back({ static_cast<double>(Y), N, P });
		}
		Out.MinCranes = Lo;
		Out.MaxCranes = Hi;
		Out.FinalHawks = P;
		return Out;
	}

private:
	ReedSettings S;
};

}} // namespace daedalus::marsh
