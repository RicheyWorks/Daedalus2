// SPDX-License-Identifier: MIT
// Metapopulation "Fritillary Meadows" (G183, C++ port G611), plain C++17, header-only, standard library only, no
// Unreal types. Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/Metapopulation.java, which stays
// the rules authority. A Levins metapopulation: each year an occupied meadow patch goes locally extinct with chance
// e and an empty one is colonised with chance 1 - (1 - c/n)^occupied; ploughed patches drop out from their plough
// year. Golden vectors: engines/unreal/core-test/marsh_metapopulation_parity.txt, written by
// MarshCoresParityTest.java and replayed by marsh_metapopulation_core_test.cpp.
//
// Seeding: Metapopulation hashes (seed, year, patch) through the SplitMix64 finalizer with its own key layout, so
// Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here). It is not a new
// generator. The colonisation chance uses std::pow where Java uses Math.pow; the two may differ in the last ulp, so
// the test allows a patch count to differ by a hair on rare crossings (see the test).
#pragma once
#include <algorithm>
#include <climits>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct MetapopulationSettings
{
	int Patches = 100;
	double Colonize = 0.5;
	double Extinction = 0.1;
	int Years = 200;
	int Start = 80;

	bool Valid() const
	{
		return Patches >= 2 && Colonize >= 0 && !std::isinf(Colonize) && Extinction > 0 && Extinction <= 1 && Years >= 1
			&& Start >= 0 && Start <= Patches;
	}
};

enum class MetapopulationOutcome : int { Flourishing = 0, Dwindling, Lost };
inline const char* MetapopulationOutcomeName(MetapopulationOutcome O)
{
	return O == MetapopulationOutcome::Flourishing ? "FLOURISHING" : O == MetapopulationOutcome::Dwindling ? "DWINDLING" : "LOST";
}

struct MetapopulationYear { int Index = 0, Occupied = 0, Ploughed = 0; };

struct MetapopulationReport
{
	MetapopulationOutcome Outcome = MetapopulationOutcome::Lost;
	double Occupancy = 0, LateMean = 0;
	std::vector<MetapopulationYear> Years;
	bool Ok = false;
	/** Flourishing butterflies keep the valley MEADOW (true); otherwise it goes to SCRUB (false). */
	bool Meadow() const { return Outcome == MetapopulationOutcome::Flourishing; }
};

class Metapopulation
{
public:
	static constexpr int Late = 50; // years averaged at the end for LateMean

	Metapopulation(const MetapopulationSettings& S, int64_t Seed)
		: S_(S), Seed_(Seed), PloughYear_(static_cast<size_t>(std::max(0, S.Patches)), INT_MAX) {}

	/** Ploughs Count more patches in Year (highest-numbered unploughed first). False if out of range or too few left. */
	bool Plough(int Year, int Count)
	{
		if (Year < 0 || Year >= S_.Years || Count < 0) return false;
		int Left = 0;
		for (int Y : PloughYear_) Left += Y == INT_MAX ? 1 : 0;
		if (Count > Left) return false;
		for (int I = S_.Patches - 1; I >= 0 && Count > 0; --I)
			if (PloughYear_[static_cast<size_t>(I)] == INT_MAX) { PloughYear_[static_cast<size_t>(I)] = Year; --Count; }
		return true;
	}

	/** Levins equilibrium occupancy 1 - D - e/c for ploughed share D (0 if negative; 0 when c is 0). */
	double Equilibrium(double Ploughed) const
	{
		if (!(S_.Colonize > 0)) return 0;
		return std::max(0.0, 1 - Ploughed - S_.Extinction / S_.Colonize);
	}

	/** The ploughed share at which the butterflies cannot persist: 1 - e/c (0 if they never can). */
	double PloughThreshold() const { return Equilibrium(0); }

	MetapopulationReport Run() const
	{
		MetapopulationReport R;
		if (!S_.Valid()) return R;
		const int N = S_.Patches;
		std::vector<char> Occ(static_cast<size_t>(N), 0), Next(static_cast<size_t>(N));
		int Occupied = 0;
		for (int I = 0; I < S_.Start; ++I) { Occ[static_cast<size_t>(I)] = 1; ++Occupied; }
		double LateSum = 0;
		for (int Y = 0; Y < S_.Years; ++Y)
		{
			const double Col = 1 - std::pow(std::max(0.0, 1 - S_.Colonize / N), Occupied);
			int Now = 0, Ploughed = 0;
			for (int I = 0; I < N; ++I)
			{
				Next[static_cast<size_t>(I)] = 0;
				if (PloughYear_[static_cast<size_t>(I)] <= Y) { ++Ploughed; continue; }
				const double Rr = Roll(Y, I);
				Next[static_cast<size_t>(I)] = Occ[static_cast<size_t>(I)] ? Rr >= S_.Extinction : Rr < Col;
				Now += Next[static_cast<size_t>(I)] ? 1 : 0;
			}
			Occ.swap(Next);
			Occupied = Now;
			R.Years.push_back({ Y, Now, Ploughed });
			if (Y >= S_.Years - Late) LateSum += Now;
		}
		const int Span = std::min(Late, S_.Years);
		R.LateMean = LateSum / Span / N;
		R.Occupancy = static_cast<double>(Occupied) / N;
		R.Outcome = Occupied == 0 ? MetapopulationOutcome::Lost
			: R.LateMean >= 0.5 * Equilibrium(0) ? MetapopulationOutcome::Flourishing : MetapopulationOutcome::Dwindling;
		R.Ok = true;
		return R;
	}

private:
	// Java: z = seed + 0x9E37..*(year+1) + 0xBF58..*(patch+1); SplitMix64 finalizer.
	double Roll(int Year, int64_t Patch) const
	{
		uint64_t Z = static_cast<uint64_t>(Seed_) + 0x9E3779B97F4A7C15ull * static_cast<uint64_t>(static_cast<int64_t>(Year + 1))
			+ 0xBF58476D1CE4E5B9ull * static_cast<uint64_t>(Patch + 1);
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}

	MetapopulationSettings S_;
	int64_t Seed_;
	std::vector<int> PloughYear_;
};

} } // namespace daedalus::marsh
