// SPDX-License-Identifier: MIT
// ShoalHarvest "Net Quota" (G176, C++ port G612), plain C++17, header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/ShoalHarvest.java, which stays the rules
// authority. A noisy logistic shoal B' = B + r*B*(1 - B/K)*eps is fished each year under a fixed QUOTA (tonnes) or a
// fixed EFFORT (share). Golden vectors: engines/unreal/core-test/marsh_shoal_harvest_parity.txt, written by
// MarshCoresParityTest.java and replayed by marsh_shoal_harvest_core_test.cpp.
//
// Seeding: ShoalHarvest hashes (seed, year) through the SplitMix64 finalizer, so Roll() below mirrors the Java core
// line for line (Java long arithmetic wraps like uint64_t here). It is not a new generator. The run uses only + - * /
// and min/max (no libm), in the same order as Java, so results replay bit for bit.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct ShoalHarvestSettings
{
	double Capacity = 1000;
	double Growth = 0.6;
	double Noise = 0.5;
	int Years = 50;
	double Collapse = 0.05;

	bool Valid() const
	{
		return Capacity > 0 && !std::isinf(Capacity) && Growth > 0 && Growth <= 1 && Noise >= 0 && Noise < 1 && Years >= 1
			&& Collapse >= 0 && Collapse < 1;
	}
};

enum class ShoalRule : int { Quota = 0, Effort };
enum class ShoalOutcome : int { Thriving = 0, Depleted, Collapsed };
inline const char* ShoalOutcomeName(ShoalOutcome O)
{
	return O == ShoalOutcome::Thriving ? "THRIVING" : O == ShoalOutcome::Depleted ? "DEPLETED" : "COLLAPSED";
}

struct ShoalYear { int Index = 0; double Shoal = 0, Catch = 0; };

struct ShoalReport
{
	ShoalOutcome Outcome = ShoalOutcome::Collapsed;
	double Shoal = 0, Total = 0;
	std::vector<ShoalYear> Years;
	bool Ok = false;
	double MeanCatch() const { return Years.empty() ? 0 : Total / static_cast<double>(Years.size()); }
	/** A thriving shoal keeps the banks WETLAND (kelp, true); otherwise BARE (false). */
	bool Kelp() const { return Outcome == ShoalOutcome::Thriving; }
};

class ShoalHarvest
{
public:
	ShoalHarvest(const ShoalHarvestSettings& S, int64_t Seed) : Set(S), SeedBits(static_cast<uint64_t>(Seed)) {}

	double Msy() const { return Set.Growth * Set.Capacity / 4; }
	double MsyEffort() const { const double U = Set.Growth / 2; return U / (1 + U); }

	/** Fishes from half capacity; Level is tonnes for Quota, a share 0..1 for Effort. Ok=false on bad input. */
	ShoalReport Run(ShoalRule Rule, double Level) const
	{
		ShoalReport R;
		if (!Set.Valid() || !(Level >= 0) || std::isinf(Level) || (Rule == ShoalRule::Effort && Level > 1)) return R;
		double B = Set.Capacity / 2;
		double Total = 0;
		bool Collapsed = false;
		R.Years.reserve(static_cast<size_t>(Set.Years));
		for (int Y = 0; Y < Set.Years; Y++)
		{
			const double Eps = 1 + Set.Noise * (2 * Roll(Y) - 1);
			B = std::max(0.0, B + Set.Growth * B * (1 - B / Set.Capacity) * Eps);
			const double Take = Rule == ShoalRule::Quota ? std::min(Level, B) : Level * B;
			R.Years.push_back(ShoalYear{Y, B, Take});
			B -= Take;
			Total += Take;
			if (B < Set.Collapse * Set.Capacity)
			{
				Collapsed = true;
				B = std::max(B, 0.0);
			}
		}
		R.Outcome = Collapsed ? ShoalOutcome::Collapsed : B >= Set.Capacity / 4 ? ShoalOutcome::Thriving : ShoalOutcome::Depleted;
		R.Shoal = B;
		R.Total = Total;
		R.Ok = true;
		return R;
	}

private:
	ShoalHarvestSettings Set;
	uint64_t SeedBits;

	double Roll(int Year) const
	{
		uint64_t Z = SeedBits + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Year) + 1);
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
};

}} // namespace daedalus::marsh
