// SPDX-License-Identifier: MIT
// AlleeRelease "Sky-Crane Return" (G142, C++ port G616), plain C++17, header-only, standard library only, no Unreal
// types. Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/AlleeRelease.java, which stays the rules
// authority. Scheduled crane releases onto the marsh: yearly survival, a mate-finding Allee effect
// N / (N + mateHalf) on the floor(N/2) pairs, and two eggs a nest that fledge with fledge * max(0, 1 - N/capacity).
// Golden vectors: engines/unreal/core-test/marsh_allee_release_parity.txt, written by MarshCoresParityTest.java and
// replayed by marsh_allee_release_core_test.cpp.
//
// Seeding: AlleeRelease hashes (seed, year, key, salt) through the SplitMix64 finalizer with its own key layout, so
// Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here). It is not a new
// generator. The core uses only + - * /, min/max and ceil in Java's order, so results replay bit for bit.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <vector>

namespace daedalus { namespace marsh {

struct AlleeReleaseSettings
{
	int Budget = 40;
	int Years = 40;
	double Survival = 0.75;
	double MateHalf = 30;
	double Fledge = 1.0;
	double Capacity = 150;
	int Goal = 50;

	bool Valid() const
	{
		return Budget >= 0 && Years >= 1 && Survival >= 0 && Survival <= 1 && MateHalf >= 0 && Fledge >= 0 && Fledge <= 1
			&& Capacity > 0 && Goal >= 1 && !std::isinf(MateHalf) && !std::isinf(Capacity);
	}
};

enum class AlleeOutcome : int { Established = 0, Lingering, Extinct };
inline const char* AlleeOutcomeName(AlleeOutcome O)
{
	return O == AlleeOutcome::Established ? "ESTABLISHED" : O == AlleeOutcome::Lingering ? "LINGERING" : "EXTINCT";
}

struct AlleeYear { int Index = 0, Released = 0, Flock = 0, Nests = 0, Fledged = 0; };

struct AlleeReport
{
	AlleeOutcome Outcome = AlleeOutcome::Extinct;
	int Flock = 0, Peak = 0;
	std::vector<AlleeYear> Years;
	bool Ok = false;
	/** An established flock keeps the marsh WETLAND (true); otherwise it scrubs over (false). */
	bool Wetland() const { return Outcome == AlleeOutcome::Established; }
};

class AlleeRelease
{
public:
	AlleeRelease(const AlleeReleaseSettings& S, int64_t Seed) : Set(S), SeedBits(static_cast<uint64_t>(Seed)) {}

	/** Schedules Birds for release in Year. False if the year is out of range or the aviary is short. */
	bool Release(int Year, int Birds)
	{
		if (Year < 0 || Year >= Set.Years || Birds < 1 || Birds > Left()) return false;
		Plan[Year] += Birds;
		return true;
	}

	/** Cranes still in the aviary. */
	int Left() const
	{
		int Used = 0;
		for (const auto& KV : Plan) Used += KV.second;
		return Set.Budget - Used;
	}

	/** Expected flock next year over this year from a flock of N (0 for N <= 0). */
	double Growth(double N) const
	{
		if (!(N > 0)) return 0;
		const double After = Set.Survival * N;
		const double Mate = After + Set.MateHalf <= 0 ? 0 : After / (After + Set.MateHalf);
		const double Chick = Set.Fledge * std::max(0.0, 1 - After / Set.Capacity);
		return (After + After / 2 * Mate * 2 * Chick) / N;
	}

	/** Allee threshold: the smallest whole flock with expected growth >= 1, or -1 if none. */
	int Threshold() const
	{
		const int Top = static_cast<int>(std::ceil(Set.Capacity));
		for (int N = 1; N <= Top; N++)
			if (Growth(N) >= 1) return N;
		return -1;
	}

	/** Runs the schedule. Ok=false when the settings are invalid. */
	AlleeReport Run() const
	{
		AlleeReport R;
		if (!Set.Valid()) return R;
		int Flock = 0, Peak = 0;
		for (int Y = 0; Y < Set.Years; Y++)
		{
			const auto It = Plan.find(Y);
			const int Released = It == Plan.end() ? 0 : It->second;
			Flock += Released;
			int Alive = 0;
			for (int B = 0; B < Flock; B++)
				if (Roll(Y, B, 1) < Set.Survival) Alive++;
			const double Mate = Alive + Set.MateHalf <= 0 ? 0 : Alive / (Alive + Set.MateHalf);
			const double Chick = Set.Fledge * std::max(0.0, 1 - Alive / Set.Capacity);
			int Nests = 0, Fledged = 0;
			for (int P = 0; P < Alive / 2; P++)
			{
				if (Roll(Y, P, 2) < Mate)
				{
					Nests++;
					for (int E = 0; E < 2; E++)
						if (Roll(Y, 2LL * P + E, 3) < Chick) Fledged++;
				}
			}
			Flock = Alive + Fledged;
			Peak = std::max(Peak, Flock);
			R.Years.push_back(AlleeYear{Y, Released, Flock, Nests, Fledged});
		}
		R.Outcome = Flock >= Set.Goal ? AlleeOutcome::Established : Flock > 0 ? AlleeOutcome::Lingering : AlleeOutcome::Extinct;
		R.Flock = Flock;
		R.Peak = Peak;
		R.Ok = true;
		return R;
	}

private:
	AlleeReleaseSettings Set;
	uint64_t SeedBits;
	std::map<int, int> Plan;

	double Roll(int Year, int64_t Key, int Salt) const
	{
		uint64_t Z = SeedBits + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Year) + 1)
			+ 0xBF58476D1CE4E5B9ULL * static_cast<uint64_t>(Key + 1) + 0x94D049BB133111EBULL * static_cast<uint64_t>(static_cast<int64_t>(Salt));
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
};

}} // namespace daedalus::marsh
