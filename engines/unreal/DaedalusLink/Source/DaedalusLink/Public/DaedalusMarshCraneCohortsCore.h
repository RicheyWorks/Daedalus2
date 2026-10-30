// SPDX-License-Identifier: MIT
// Crane Cohorts (G194, C++ port G585) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/CraneCohorts.java, which stays the rules
// authority. The sky-crane flock as a 4x4 Leslie matrix (chick, juvenile, subadult, adult). It gives the dominant
// eigenvalue lambda (shifted power iteration plus a Rayleigh quotient), the stable age distribution, reproductive value
// (chick = 1), elasticities, the best cohort to release, adult equivalents, and a seeded projection with demographic
// noise (binomial survival, Poisson chicks).
// Golden vectors: engines/unreal/core-test/marsh_crane_cohorts_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in G570/G583, the Java core hashes (seed, year, cohort, bird, salt) statelessly with the SplitMix64
// finalizer. Uniform() mirrors that hash. It is not a new generator (docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct CohortSettings
{
	double ChickSurvival = 0.5;
	double JuvenileSurvival = 0.7;
	double SubadultSurvival = 0.85;
	double AdultSurvival = 0.9;
	double SubadultFecundity = 0.15;
	double AdultFecundity = 0.45;
	int Years = 30;

	static bool Prob(double P) { return P >= 0 && P <= 1; }
	bool Valid() const
	{
		if (!Prob(ChickSurvival) || !Prob(JuvenileSurvival) || !Prob(SubadultSurvival) || !Prob(AdultSurvival)
			|| !(SubadultFecundity >= 0) || !(AdultFecundity >= 0) || std::isinf(SubadultFecundity)
			|| std::isinf(AdultFecundity) || Years < 1)
			return false;
		return !(AdultSurvival == 0 && SubadultFecundity == 0 && AdultFecundity == 0);
	}
	CohortSettings WithAdultSurvival(double P) const { CohortSettings C = *this; C.AdultSurvival = P; return C; }
};

enum class CohortOutcome { Growing, Steady, Declining, Extinct };

struct CohortYear
{
	int Index = 0, Chicks = 0, Juveniles = 0, Subadults = 0, Adults = 0;
	int Total() const { return Chicks + Juveniles + Subadults + Adults; }
};

struct CohortReport
{
	CohortOutcome Outcome = CohortOutcome::Steady;
	int Flock = 0;
	std::vector<CohortYear> Years;
};

namespace cohort_detail {
inline uint64_t Mix(uint64_t Z)
{
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
	return Z ^ (Z >> 31);
}
inline uint64_t AsBits(int64_t V) { return static_cast<uint64_t>(V); }
// Java: mix(seed ^ C); mix(h ^ t); mix(h ^ ((long) cohort << 32 | (bird & 0xFFFFFFFFL))); mix(h ^ salt).
inline double Uniform(int64_t Seed, int Year, int Cohort, int Bird, int Salt)
{
	uint64_t H = Mix(AsBits(Seed) ^ 0x9E3779B97F4A7C15ull);
	H = Mix(H ^ AsBits(Year));
	H = Mix(H ^ ((AsBits(Cohort) << 32) | (AsBits(Bird) & 0xFFFFFFFFull)));
	H = Mix(H ^ AsBits(Salt));
	return static_cast<double>(H >> 11) * 0x1.0p-53;
}
// Java (int) Math.round(x): round half up to a saturated long (NaN -> 0), then keep the low 32 bits.
inline int JavaRoundToInt(double X)
{
	if (std::isnan(X)) return 0;
	const double R = std::floor(X + 0.5);
	int64_t L;
	if (R >= 9223372036854775807.0) L = INT64_MAX;
	else if (R <= -9223372036854775808.0) L = INT64_MIN;
	else L = static_cast<int64_t>(R);
	const uint32_t Low = static_cast<uint32_t>(static_cast<uint64_t>(L));
	return Low <= 0x7FFFFFFFu ? static_cast<int>(Low) : static_cast<int>(static_cast<int64_t>(Low) - 4294967296LL);
}
} // namespace cohort_detail

class CraneCohorts
{
public:
	static constexpr int Cohorts = 4, Chick = 0, Juvenile = 1, Subadult = 2, Adult = 3;
	using Vec = std::array<double, 4>;
	using Flock = std::array<int, 4>;

	explicit CraneCohorts(const CohortSettings& In) : S(In)
	{
		M = { { { 0, 0, S.SubadultFecundity, S.AdultFecundity }, { S.ChickSurvival, 0, 0, 0 },
			{ 0, S.JuvenileSurvival, 0, 0 }, { 0, 0, S.SubadultSurvival, S.AdultSurvival } } };
		const Vec W = Power(false);
		Lambda = Rayleigh(W);
		Right = Normalise(W);
		Vec V = Power(true);
		const double Scale = V[Chick] > 0 ? V[Chick] : V[Adult];
		for (double& X : V) X /= Scale;
		Left = V;
	}

	const CohortSettings& Settings() const { return S; }
	double Entry(int Row, int Col) const { return M[Row][Col]; }
	double GetLambda() const { return Lambda; }
	CohortOutcome Trend() const
	{
		if (Lambda > 1 + 1e-9) return CohortOutcome::Growing;
		return Lambda < 1 - 1e-9 ? CohortOutcome::Declining : CohortOutcome::Steady;
	}
	const Vec& StableAges() const { return Right; }
	const Vec& ReproductiveValue() const { return Left; }

	double Elasticity(int Row, int Col) const
	{
		double Dot = 0;
		for (int I = 0; I < Cohorts; ++I) Dot += Left[I] * Right[I];
		return M[Row][Col] * Left[Row] * Right[Col] / (Lambda * Dot);
	}

	int BestRelease() const
	{
		int Best = 0;
		for (int I = 1; I < Cohorts; ++I)
			if (Left[I] > Left[Best]) Best = I;
		return Best;
	}

	// -1 for a negative cohort (Java throws). A flock whose adults are worth ~0 overflows exactly as Java does.
	int AdultEquivalents(const Flock& Birds) const
	{
		double Sum = 0;
		for (int I = 0; I < Cohorts; ++I)
		{
			if (Birds[I] < 0) return -1;
			Sum += Birds[I] * Left[I];
		}
		return cohort_detail::JavaRoundToInt(Sum / Left[Adult]); // Java's long-to-int wrap kept for parity
	}

	Vec Step(const Vec& N) const
	{
		Vec Out{};
		for (int I = 0; I < Cohorts; ++I)
			for (int J = 0; J < Cohorts; ++J) Out[I] += M[I][J] * N[J];
		return Out;
	}

	// Empty report (no years) for a negative cohort (Java throws).
	CohortReport Project(const Flock& Start, int64_t RunSeed) const
	{
		CohortReport R;
		for (int B : Start)
			if (B < 0) return R;
		Flock N = Start;
		R.Years.push_back(MakeYear(0, N));
		for (int T = 1; T <= S.Years; ++T)
		{
			Flock Next{};
			Next[Chick] = Poisson(S.SubadultFecundity * N[Subadult] + S.AdultFecundity * N[Adult], RunSeed, T);
			Next[Juvenile] = Binomial(N[Chick], S.ChickSurvival, RunSeed, T, Chick);
			Next[Subadult] = Binomial(N[Juvenile], S.JuvenileSurvival, RunSeed, T, Juvenile);
			Next[Adult] = Binomial(N[Subadult], S.SubadultSurvival, RunSeed, T, Subadult)
				+ Binomial(N[Adult], S.AdultSurvival, RunSeed, T, Adult);
			N = Next;
			R.Years.push_back(MakeYear(T, N));
			if (Total(N) == 0) break;
		}
		R.Flock = Total(N);
		const int Begin = Total(Start);
		R.Outcome = R.Flock == 0 ? CohortOutcome::Extinct
			: R.Flock > Begin ? CohortOutcome::Growing
			: R.Flock < Begin ? CohortOutcome::Declining : CohortOutcome::Steady;
		return R;
	}

private:
	CohortSettings S;
	std::array<Vec, 4> M{};
	double Lambda = 0;
	Vec Right{}, Left{};

	Vec Power(bool Transpose) const
	{
		Vec X = { 0.25, 0.25, 0.25, 0.25 };
		for (int It = 0; It < 200000; ++It)
		{
			Vec Y{};
			for (int I = 0; I < Cohorts; ++I)
				for (int J = 0; J < Cohorts; ++J) Y[I] += (Transpose ? M[J][I] : M[I][J]) * X[J];
			for (int I = 0; I < Cohorts; ++I) Y[I] = 0.5 * (Y[I] + X[I]); // shifted step: periodic matrices converge
			Y = Normalise(Y);
			double Diff = 0;
			for (int I = 0; I < Cohorts; ++I) Diff = std::fmax(Diff, std::fabs(Y[I] - X[I]));
			X = Y;
			if (Diff < 1e-14) break;
		}
		return X;
	}
	double Rayleigh(const Vec& W) const
	{
		const Vec Aw = Step(W);
		double Num = 0, Den = 0;
		for (int I = 0; I < Cohorts; ++I) { Num += Aw[I] * W[I]; Den += W[I] * W[I]; }
		return Num / Den;
	}
	static Vec Normalise(const Vec& X)
	{
		double Sum = 0;
		for (double V : X) Sum += V;
		Vec Out{};
		for (int I = 0; I < Cohorts; ++I) Out[I] = X[I] / Sum;
		return Out;
	}
	static int Total(const Flock& N) { return N[0] + N[1] + N[2] + N[3]; }
	static CohortYear MakeYear(int T, const Flock& N) { return { T, N[Chick], N[Juvenile], N[Subadult], N[Adult] }; }

	static int Binomial(int N, double P, int64_t Seed, int T, int Cohort)
	{
		int K = 0;
		for (int B = 0; B < N; ++B)
			if (cohort_detail::Uniform(Seed, T, Cohort, B, 1) < P) ++K;
		return K;
	}
	static int Poisson(double Mean, int64_t Seed, int T)
	{
		if (Mean <= 0) return 0;
		if (Mean > 40)
		{
			const double U1 = std::fmax(cohort_detail::Uniform(Seed, T, Cohorts, 0, 2), 1e-300);
			const double U2 = cohort_detail::Uniform(Seed, T, Cohorts, 1, 2);
			const double Z = std::sqrt(-2 * std::log(U1)) * std::cos(2 * 3.141592653589793 * U2);
			return static_cast<int>(std::fmax(0.0, std::floor(Mean + std::sqrt(Mean) * Z + 0.5)));
		}
		const double Limit = std::exp(-Mean);
		double Prod = 1;
		int K = -1, Draw = 0;
		do
		{
			++K;
			Prod *= cohort_detail::Uniform(Seed, T, Cohorts, Draw++, 2);
		} while (Prod > Limit);
		return K;
	}
};

}} // namespace daedalus::marsh
