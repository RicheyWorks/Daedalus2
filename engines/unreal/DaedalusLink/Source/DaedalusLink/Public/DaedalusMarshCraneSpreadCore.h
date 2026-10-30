// SPDX-License-Identifier: MIT
// Crane Spread (G200, C++ port G583) in plain C++17: header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/CraneSpread.java, which stays the rules
// authority. The sky-crane flock spreads along a line of marsh cells: Beverton-Holt growth, then a discretised Laplace
// dispersal kernel, with the release reedbed held full. Also gives the spreading speed c* = min ln(lambda M(s)) / s, and
// a seeded run with demographic noise (Poisson, or a rounded normal above mean 40).
// Golden vectors: engines/unreal/core-test/marsh_crane_spread_parity.txt, written by MarshCoresParityTest.java.
//
// Seeding: as in G570, the Java core hashes (seed, year, cell, draw) statelessly with the SplitMix64 finalizer. Uniform()
// mirrors that hash. It is not a new generator (see docs/mechanics/NATIVE-PORT-PATTERN.md, rule 3).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct SpreadSettings
{
	double Lambda = 1.5;
	double Dispersal = 1.0; // mean dispersal distance b, km
	double Cell = 0.25;     // km
	double Capacity = 100;
	int Years = 200;

	bool Valid() const
	{
		return Lambda > 0 && Dispersal > 0 && Cell > 0 && Capacity > 0 && !std::isinf(Lambda) && !std::isinf(Dispersal)
			&& !std::isinf(Capacity) && Years >= 1 && !(Dispersal / Cell > 400) && !(Cell > Dispersal * 4);
	}
};

struct SpreadYear
{
	int Index = 0;
	double Front = 0; // km, furthest cell at half capacity
	double Birds = 0;
};

struct SpreadReport
{
	std::vector<SpreadYear> Years;
	double Speed = 0; // km/yr over the second half

	int YearReached(double Km) const
	{
		for (const SpreadYear& Y : Years)
			if (Y.Front >= Km) return Y.Index;
		return -1;
	}
};

namespace spread_detail {
inline uint64_t Mix(uint64_t Z)
{
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
	return Z ^ (Z >> 31);
}
inline uint64_t AsBits(int64_t V) { return static_cast<uint64_t>(V); }
// Java: mix(seed ^ C); mix(h ^ t); mix(h ^ ((long) cell << 32 | (draw & 0xFFFFFFFFL))); mix(h ^ 3).
inline double Uniform(int64_t Seed, int Year, int Cell, int Draw)
{
	uint64_t H = Mix(AsBits(Seed) ^ 0xD1B54A32D192ED03ull);
	H = Mix(H ^ AsBits(Year));
	H = Mix(H ^ ((AsBits(Cell) << 32) | (AsBits(Draw) & 0xFFFFFFFFull)));
	H = Mix(H ^ 3ull);
	return static_cast<double>(H >> 11) * 0x1.0p-53;
}
inline double JavaRound(double X) { return std::floor(X + 0.5); } // Math.round for the values that occur here
inline double Poisson(double Mean, int64_t Seed, int Year, int Cell)
{
	if (Mean <= 0) return 0;
	if (Mean > 40)
	{
		const double U1 = std::fmax(Uniform(Seed, Year, Cell, 0), 1e-300);
		const double U2 = Uniform(Seed, Year, Cell, 1);
		const double Z = std::sqrt(-2 * std::log(U1)) * std::cos(2 * 3.141592653589793 * U2);
		return std::fmax(0.0, JavaRound(Mean + std::sqrt(Mean) * Z));
	}
	const double Limit = std::exp(-Mean);
	double Prod = 1;
	int K = -1, Draw = 2;
	do
	{
		++K;
		Prod *= Uniform(Seed, Year, Cell, Draw++);
	} while (Prod > Limit);
	return K;
}
} // namespace spread_detail

class CraneSpread
{
public:
	static constexpr int Source = 4; // release cells held at capacity

	explicit CraneSpread(const SpreadSettings& In) : S(In)
	{
		Reach = static_cast<int>(std::ceil(30 * S.Dispersal / S.Cell));
		Kernel.assign(2 * static_cast<size_t>(Reach) + 1, 0.0);
		double Sum = 0;
		for (int J = -Reach; J <= Reach; ++J)
		{
			Kernel[J + Reach] = std::exp(-std::abs(J) * S.Cell / S.Dispersal);
			Sum += Kernel[J + Reach];
		}
		for (double& K : Kernel) K /= Sum;
	}
	const SpreadSettings& Settings() const { return S; }

	double Mgf(double Sv) const
	{
		double M = 0;
		for (int J = -Reach; J <= Reach; ++J) M += Kernel[J + Reach] * std::exp(Sv * J * S.Cell);
		return M;
	}

	double SpreadingSpeed() const
	{
		if (S.Lambda <= 1) return 0;
		double Lo = 1e-6, Hi = 0.999 / S.Dispersal;
		const double G = (std::sqrt(5.0) - 1) / 2;
		for (int It = 0; It < 200; ++It)
		{
			const double A = Hi - G * (Hi - Lo), B = Lo + G * (Hi - Lo);
			if (SpeedAt(A) < SpeedAt(B)) Hi = B; else Lo = A;
		}
		return SpeedAt((Lo + Hi) / 2);
	}

	SpreadReport Run() const { return Simulate(false, 0); }
	SpreadReport Run(int64_t RunSeed) const { return Simulate(true, RunSeed); }

private:
	SpreadSettings S;
	std::vector<double> Kernel;
	int Reach = 0;

	double SpeedAt(double Sv) const { return std::log(S.Lambda * Mgf(Sv)) / Sv; }

	double Front(const std::vector<double>& N) const
	{
		size_t Last = 0;
		for (size_t I = 0; I < N.size(); ++I)
			if (N[I] >= S.Capacity / 2) Last = I;
		return static_cast<double>(Last) * S.Cell;
	}
	static double Sum(const std::vector<double>& N)
	{
		double T = 0;
		for (double V : N) T += V;
		return T;
	}

	SpreadReport Simulate(bool Noisy, int64_t RunSeed) const
	{
		const double SpeedGuess = std::fmax(SpreadingSpeed(), 0.0) * 1.2 + S.Dispersal;
		const int Cells = static_cast<int>(std::ceil(SpeedGuess * S.Years / S.Cell)) + 2 * Reach + Source + 8;
		const double Cap = S.Capacity, Lam = S.Lambda;
		std::vector<double> N(Cells, 0.0), Grown(Cells), Next(Cells);
		for (int I = 0; I < Source; ++I) N[I] = Cap;
		SpreadReport R;
		R.Years.push_back({ 0, Front(N), Sum(N) });
		for (int T = 1; T <= S.Years; ++T)
		{
			for (int I = 0; I < Cells; ++I) Grown[I] = Lam * N[I] / (1 + (Lam - 1) * N[I] / Cap);
			std::fill(Next.begin(), Next.end(), 0.0);
			for (int I = 0; I < Cells; ++I)
			{
				if (Grown[I] == 0) continue;
				const int From = std::max(0, I - Reach), To = std::min(Cells - 1, I + Reach);
				for (int K = From; K <= To; ++K) Next[K] += Grown[I] * Kernel[K - I + Reach];
			}
			if (Noisy)
				for (int I = 0; I < Cells; ++I) Next[I] = spread_detail::Poisson(Next[I], RunSeed, T, I);
			for (int I = 0; I < Source; ++I) Next[I] = Cap;
			N.swap(Next);
			R.Years.push_back({ T, Front(N), Sum(N) });
		}
		const int Half = S.Years / 2;
		R.Speed = (R.Years[S.Years].Front - R.Years[Half].Front) / (S.Years - Half);
		return R;
	}
};

}} // namespace daedalus::marsh
