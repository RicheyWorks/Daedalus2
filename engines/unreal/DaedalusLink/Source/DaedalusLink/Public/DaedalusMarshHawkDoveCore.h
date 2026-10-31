// SPDX-License-Identifier: MIT
// Hawk-Dove "Rut on the Ridge" (G188, C++ port G610), plain C++17, header-only, standard library only, no Unreal
// types. Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/HawkDove.java, which stays the rules
// authority. Hornback bulls meet random rivals each season over a resource worth V; a hawk fights (the loser pays
// C), a dove displays and backs down. Bulls breed in proportion to base + mean payoff (a seeded Wright-Fisher draw),
// so the herd's hawk share evolves toward the ESS V/C when C > V. Golden vectors:
// engines/unreal/core-test/marsh_hawk_dove_parity.txt, written by MarshCoresParityTest.java and replayed by
// marsh_hawk_dove_core_test.cpp.
//
// Seeding: HawkDove hashes (seed, season, bull, round, salt) through the SplitMix64 finalizer with its own key
// layout, so Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here).
// It is not a new generator.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace marsh {

struct HawkDoveSettings
{
	int Herd = 200;
	double Value = 4;
	double Cost = 10;
	double Base = 10;
	int Rounds = 10;
	int Seasons = 150;

	bool Valid() const
	{
		return Herd >= 2 && Value > 0 && Cost >= 0 && Base > 0 && !std::isinf(Value) && !std::isinf(Cost)
			&& !std::isinf(Base) && Rounds >= 1 && Seasons >= 1;
	}
};

enum class HawkDoveOutcome : int { Mixed = 0, AllHawk, AllDove };
inline const char* HawkDoveOutcomeName(HawkDoveOutcome O)
{
	return O == HawkDoveOutcome::AllHawk ? "ALL_HAWK" : O == HawkDoveOutcome::AllDove ? "ALL_DOVE" : "MIXED";
}

struct HawkDoveSeason { int Index = 0; double Hawks = 0, HawkPayoff = 0, DovePayoff = 0; }; // NaN payoff: absent

struct HawkDoveReport
{
	HawkDoveOutcome Outcome = HawkDoveOutcome::Mixed;
	double Hawks = 0, LateHawks = 0;
	std::vector<HawkDoveSeason> Seasons;
	bool Ok = false; // false when the start count was out of range (Java throws)
	/** Ridge cover: over 80 % late hawks tramples the grazing to BARE (true); otherwise MEADOW (false). */
	bool Bare() const { return LateHawks > 0.8; }
};

class HawkDove
{
public:
	static constexpr int Late = 50; // seasons averaged at the end for LateHawks

	HawkDove(const HawkDoveSettings& S, int64_t Seed) : S_(S), Seed_(Seed) {}

	/** The evolutionarily stable hawk share: V/C when C > V, otherwise 1. */
	double Ess() const { return S_.Cost > S_.Value ? S_.Value / S_.Cost : 1; }

	/** Expected payoff of one contest for a hawk (or dove) in a herd with hawk share H. */
	double ExpectedPayoff(bool Hawk, double H) const
	{
		const double V = S_.Value, C = S_.Cost;
		return Hawk ? H * (V - C) / 2 + (1 - H) * V : (1 - H) * V / 2;
	}

	/** Runs Seasons from a herd with Hawks of Herd bulls hawkish. */
	HawkDoveReport Run(int Hawks) const
	{
		HawkDoveReport R;
		if (!S_.Valid() || Hawks < 0 || Hawks > S_.Herd) return R;
		const int N = S_.Herd;
		std::vector<char> Hawk(static_cast<size_t>(N), 0);
		for (int I = 0; I < Hawks; ++I) Hawk[static_cast<size_t>(I)] = 1;
		double LateSum = 0;
		int Count = Hawks;
		std::vector<double> Pay(static_cast<size_t>(N)), Cum(static_cast<size_t>(N));
		std::vector<char> Next(static_cast<size_t>(N));
		for (int G = 0; G < S_.Seasons; ++G)
		{
			std::fill(Pay.begin(), Pay.end(), 0.0);
			for (int I = 0; I < N; ++I)
				for (int Rd = 0; Rd < S_.Rounds; ++Rd)
				{
					int J = static_cast<int>(Roll(G, I, Rd, 1) * (N - 1));
					if (J >= I) ++J;
					const bool Win = Roll(G, I, Rd, 2) < 0.5;
					Pay[static_cast<size_t>(I)] += Contest(Hawk[static_cast<size_t>(I)] != 0, Hawk[static_cast<size_t>(J)] != 0, Win);
				}
			double Fit = 0, Hp = 0, Dp = 0;
			for (int I = 0; I < N; ++I)
			{
				const double Mean = Pay[static_cast<size_t>(I)] / S_.Rounds;
				Fit += std::max(0.0, S_.Base + Mean);
				Cum[static_cast<size_t>(I)] = Fit;
				if (Hawk[static_cast<size_t>(I)]) Hp += Mean; else Dp += Mean;
			}
			int NextCount = 0;
			for (int C = 0; C < N; ++C)
			{
				const double X = Roll(G, C, 0, 3) * Fit;
				int Lo = 0, Hi = N - 1;
				while (Lo < Hi)
				{
					const int Mid = static_cast<int>((static_cast<unsigned>(Lo) + static_cast<unsigned>(Hi)) >> 1);
					if (Cum[static_cast<size_t>(Mid)] > X) Hi = Mid; else Lo = Mid + 1;
				}
				Next[static_cast<size_t>(C)] = Hawk[static_cast<size_t>(Lo)];
				NextCount += Next[static_cast<size_t>(C)] ? 1 : 0;
			}
			const double Nan = std::numeric_limits<double>::quiet_NaN();
			const double HawkPay = Count == 0 ? Nan : Hp / Count;
			const double DovePay = Count == N ? Nan : Dp / (N - Count);
			Hawk.swap(Next);
			Count = NextCount;
			R.Seasons.push_back({ G + 1, static_cast<double>(Count) / N, HawkPay, DovePay });
			if (G >= S_.Seasons - Late) LateSum += static_cast<double>(Count) / N;
		}
		R.Hawks = static_cast<double>(Count) / N;
		R.Outcome = Count == N ? HawkDoveOutcome::AllHawk : Count == 0 ? HawkDoveOutcome::AllDove : HawkDoveOutcome::Mixed;
		R.LateHawks = LateSum / std::min(Late, S_.Seasons);
		R.Ok = true;
		return R;
	}

private:
	double Contest(bool Me, bool Them, bool Win) const
	{
		if (Me && Them) return Win ? S_.Value : -S_.Cost;
		if (Me) return S_.Value;
		if (Them) return 0;
		return Win ? S_.Value : 0;
	}

	// Java: z = seed + 0x9E37..*(season+1) + 0xBF58..*(bull+1) + 0x94D0..*(salt + 4L*(round+1)); SplitMix64 finalizer.
	double Roll(int Season, int64_t Bull, int Round, int Salt) const
	{
		uint64_t Z = static_cast<uint64_t>(Seed_) + 0x9E3779B97F4A7C15ull * static_cast<uint64_t>(static_cast<int64_t>(Season + 1))
			+ 0xBF58476D1CE4E5B9ull * static_cast<uint64_t>(Bull + 1)
			+ 0x94D049BB133111EBull * static_cast<uint64_t>(static_cast<int64_t>(Salt) + 4LL * (Round + 1));
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}

	HawkDoveSettings S_;
	int64_t Seed_;
};

} } // namespace daedalus::marsh
