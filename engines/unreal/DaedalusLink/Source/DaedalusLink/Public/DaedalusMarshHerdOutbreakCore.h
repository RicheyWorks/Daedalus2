// SPDX-License-Identifier: MIT
// HerdOutbreak "Hoof Blight" (G172, C++ port G613), plain C++17, header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/HerdOutbreak.java, which stays the rules
// authority. A seeded Reed-Frost epidemic: each generation a susceptible animal falls sick with chance
// 1 - (1 - p)^I, p = r0/herd (scaled by the fence factor from the fence generation on); vaccinated animals are immune.
// Golden vectors: engines/unreal/core-test/marsh_herd_outbreak_parity.txt, written by MarshCoresParityTest.java and
// replayed by marsh_herd_outbreak_core_test.cpp.
//
// Seeding: HerdOutbreak hashes (seed, generation, animal) through the SplitMix64 finalizer with its own key layout,
// so Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here). It is not a
// new generator. std::pow / std::exp stand in for Math.pow / Math.exp and may differ in the last ulp, so the test
// allows a run to differ on a rare roll that lands exactly on the infection chance (see the test).
#pragma once
#include <climits>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct HerdOutbreakSettings
{
	int Herd = 200;
	double R0 = 2.5;
	int Doses = 150;
	int Generations = 60;

	bool Valid() const { return Herd >= 2 && R0 >= 0 && R0 <= Herd && Doses >= 0 && Generations >= 1; }
};

enum class HerdOutcome : int { Contained = 0, Outbreak, Epidemic };
inline const char* HerdOutcomeName(HerdOutcome O)
{
	return O == HerdOutcome::Contained ? "CONTAINED" : O == HerdOutcome::Outbreak ? "OUTBREAK" : "EPIDEMIC";
}

struct HerdGeneration { int Index = 0, Sick = 0, Susceptible = 0; };

struct HerdReport
{
	HerdOutcome Outcome = HerdOutcome::Epidemic;
	int Sick = 0;
	double Share = 0;
	int Vaccinated = 0;
	std::vector<HerdGeneration> Generations;
	bool Ok = false;
	/** A contained herd keeps the pasture MEADOW (true); otherwise it scrubs over (false). */
	bool Meadow() const { return Outcome == HerdOutcome::Contained; }
};

class HerdOutbreak
{
public:
	static constexpr double ContainedShare = 0.1; // sick share at most for CONTAINED
	static constexpr double EpidemicShare = 0.5;  // sick share above which it is an EPIDEMIC

	HerdOutbreak(const HerdOutbreakSettings& S, int64_t Seed) : Set(S), SeedBits(static_cast<uint64_t>(Seed)) {}

	/** Vaccinates N animals before the blight. False if over the doses or leaving no one to catch it. */
	bool Vaccinate(int N)
	{
		if (N < 0 || N > Set.Doses || N > Set.Herd - 1) return false;
		Vaccinated = N;
		return true;
	}

	/** Quarantine fence from generation Gen, scaling contact by Factor (0..1). */
	bool Fence(int Gen, double Factor)
	{
		if (Gen < 0 || !(Factor >= 0 && Factor <= 1)) return false;
		FenceAt = Gen;
		FenceFactor = Factor;
		return true;
	}

	/** Herd-immunity threshold 1 - 1/r0 (0 when r0 <= 1). */
	double Threshold() const { return Set.R0 <= 1 ? 0 : 1 - 1 / Set.R0; }

	/** Final-size share z solving z = 1 - exp(-r z) (0 when r <= 1), by the same 200-step bisection as Java. */
	static double FinalSize(double R)
	{
		if (!(R > 1)) return 0;
		double Lo = 1e-12, Hi = 1;
		for (int I = 0; I < 200; I++)
		{
			const double Mid = (Lo + Hi) / 2;
			if (Mid - 1 + std::exp(-R * Mid) < 0) Lo = Mid;
			else Hi = Mid;
		}
		return (Lo + Hi) / 2;
	}

	/** Runs the blight. Ok=false when the settings are invalid. */
	HerdReport Run() const
	{
		HerdReport R;
		if (!Set.Valid()) return R;
		const int N = Set.Herd;
		// 0 susceptible, 1 infectious, 2 removed (vaccinated or recovered), 3 sick this generation
		std::vector<unsigned char> State(static_cast<size_t>(N), 0);
		for (int I = 0; I < Vaccinated; I++) State[static_cast<size_t>(1 + I)] = 2;
		State[0] = 1;
		int Infectious = 1, Sick = 1;
		for (int G = 0; G < Set.Generations && Infectious > 0; G++)
		{
			const double P = Set.R0 / N * (G >= FenceAt ? FenceFactor : 1);
			const double Hit = 1 - std::pow(1 - P, Infectious);
			int Fresh = 0, Left = 0;
			for (int I = 0; I < N; I++)
			{
				unsigned char& St = State[static_cast<size_t>(I)];
				if (St == 1) St = 2;
				else if (St == 0)
				{
					if (Roll(G, I) < Hit) { St = 3; Fresh++; }
					else Left++;
				}
			}
			for (unsigned char& St : State) if (St == 3) St = 1;
			Infectious = Fresh;
			Sick += Fresh;
			R.Generations.push_back(HerdGeneration{G + 1, Fresh, Left});
		}
		R.Sick = Sick;
		R.Share = static_cast<double>(Sick) / N;
		R.Outcome = R.Share <= ContainedShare ? HerdOutcome::Contained : R.Share > EpidemicShare ? HerdOutcome::Epidemic : HerdOutcome::Outbreak;
		R.Vaccinated = Vaccinated;
		R.Ok = true;
		return R;
	}

private:
	HerdOutbreakSettings Set;
	uint64_t SeedBits;
	int Vaccinated = 0;
	int FenceAt = INT_MAX;
	double FenceFactor = 1;

	double Roll(int Gen, int64_t Animal) const
	{
		uint64_t Z = SeedBits + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Gen) + 1)
			+ 0xBF58476D1CE4E5B9ULL * static_cast<uint64_t>(Animal + 1);
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
};

}} // namespace daedalus::marsh
