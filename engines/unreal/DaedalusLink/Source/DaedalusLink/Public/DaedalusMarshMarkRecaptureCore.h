// SPDX-License-Identifier: MIT
// MarkRecapture "Tag and Count" (G156, C++ port G615), plain C++17, header-only, standard library only, no Unreal
// types. Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/MarkRecapture.java, which stays the rules
// authority. A two-session hare census with tag loss, turnover and trap response, scored by the Lincoln-Petersen and
// Chapman estimates, the Seber variance and a 95% band. Golden vectors:
// engines/unreal/core-test/marsh_mark_recapture_parity.txt, written by MarshCoresParityTest.java and replayed by
// marsh_mark_recapture_core_test.cpp.
//
// Seeding: MarkRecapture hashes (seed, session, hare, salt) through the SplitMix64 finalizer with its own key layout,
// so Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here). It is not a
// new generator. The catch chance uses std::pow where Java uses Math.pow and may differ in the last ulp, so the test
// allows a census to differ on a rare roll that lands exactly on the chance (see the test). Where Java throws on
// R > min(M, C) or negative counts, the static estimators here return NaN.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace daedalus { namespace marsh {

struct MarkRecaptureSettings
{
	int Population = 240;
	int Traps = 60;
	double PerTrap = 0.012;
	double TagLoss = 0;
	double TrapResponse = 1;
	double Turnover = 0;

	bool Valid() const
	{
		return Population >= 1 && Traps >= 2 && PerTrap > 0 && PerTrap < 1 && TagLoss >= 0 && TagLoss <= 1
			&& TrapResponse >= 0 && !std::isinf(TrapResponse) && Turnover >= 0 && Turnover <= 1;
	}
};

enum class CensusVerdict : int { Accurate = 0, Rough, Misleading };
inline const char* CensusVerdictName(CensusVerdict V)
{
	return V == CensusVerdict::Accurate ? "ACCURATE" : V == CensusVerdict::Rough ? "ROUGH" : "MISLEADING";
}

namespace mark_recapture {
inline bool Bad(int M, int C, int R) { return M < 0 || C < 0 || R < 0 || R > M || R > C; }
/** Lincoln-Petersen M*C/R; +infinity when R is 0. */
inline double LincolnPetersen(int M, int C, int R)
{
	if (Bad(M, C, R)) return std::numeric_limits<double>::quiet_NaN();
	return R == 0 ? std::numeric_limits<double>::infinity() : static_cast<double>(M) * C / R;
}
/** Chapman (M+1)(C+1)/(R+1) - 1. */
inline double Chapman(int M, int C, int R)
{
	if (Bad(M, C, R)) return std::numeric_limits<double>::quiet_NaN();
	return (M + 1.0) * (C + 1.0) / (R + 1.0) - 1;
}
/** Seber variance (M+1)(C+1)(M-R)(C-R) / ((R+1)^2 (R+2)). */
inline double SeberVariance(int M, int C, int R)
{
	if (Bad(M, C, R)) return std::numeric_limits<double>::quiet_NaN();
	return (M + 1.0) * (C + 1.0) * (M - R) * (C - R) / ((R + 1.0) * (R + 1.0) * (R + 2.0));
}
} // namespace mark_recapture

struct Census
{
	static constexpr double AccurateBand = 0.15;
	static constexpr double RoughBand = 0.35;

	int Marked = 0, Caught = 0, Recaptured = 0, Truth = 0;

	double LincolnPetersen() const { return mark_recapture::LincolnPetersen(Marked, Caught, Recaptured); }
	double Chapman() const { return mark_recapture::Chapman(Marked, Caught, Recaptured); }
	double Variance() const { return mark_recapture::SeberVariance(Marked, Caught, Recaptured); }
	int Handled() const { return Marked + Caught - Recaptured; }
	double Low() const { return std::max(static_cast<double>(Handled()), Chapman() - 1.96 * std::sqrt(Variance())); }
	double High() const { return std::max(Low(), Chapman() + 1.96 * std::sqrt(Variance())); }
	double Error() const { return (Chapman() - Truth) / Truth; }
	CensusVerdict Verdict() const
	{
		const double E = std::fabs(Error());
		return E <= AccurateBand ? CensusVerdict::Accurate : E <= RoughBand ? CensusVerdict::Rough : CensusVerdict::Misleading;
	}
	int Quota(double Rate) const { return static_cast<int>(std::floor(Rate * Low())); }
	int GreedyQuota(double Rate) const { return static_cast<int>(std::floor(Rate * Chapman())); }
	bool Safe(int Take, double Rate) const { return Take <= Rate * Truth; }
	/** A safe quota keeps the refuge MEADOW (true); an overharvest lets it scrub over (false). */
	bool Meadow(double Rate) const { return Safe(Quota(Rate), Rate); }
};

class MarkRecapture
{
public:
	MarkRecapture(const MarkRecaptureSettings& S, int64_t Seed) : Set(S), SeedBits(static_cast<uint64_t>(Seed)) {}

	/** Splits trap-nights across the sessions. False (plan unchanged) unless both are >= 1 and fit the budget. */
	bool Plan(int TrapsFirst, int TrapsSecond)
	{
		if (TrapsFirst < 1 || TrapsSecond < 1 || static_cast<long long>(TrapsFirst) + TrapsSecond > Set.Traps) return false;
		First = TrapsFirst;
		Second = TrapsSecond;
		return true;
	}

	/** Catch chance for one hare in a session of T trap-nights. */
	double CatchChance(int T) const { return 1 - std::pow(1 - Set.PerTrap, T); }

	/** Runs both sessions; an unplanned census splits evenly. Truth is 0 (not run) when the settings are invalid. */
	Census Run() const
	{
		Census Out;
		if (!Set.Valid()) return Out;
		int T1 = First, T2 = Second;
		if (T1 == 0)
		{
			T1 = Set.Traps / 2;
			T2 = Set.Traps - T1;
		}
		const double P1 = CatchChance(T1), P2 = CatchChance(T2);
		const double P2Caught = std::min(1.0, P2 * Set.TrapResponse);
		int M = 0, C = 0, R = 0;
		for (int H = 0; H < Set.Population; H++)
		{
			const bool CaughtOnce = Roll(1, H, 1) < P1;
			if (CaughtOnce) M++;
			const bool Replaced = Roll(1, H, 2) < Set.Turnover;
			const bool Tagged = CaughtOnce && !Replaced && !(Roll(1, H, 3) < Set.TagLoss);
			const double P = CaughtOnce && !Replaced ? P2Caught : P2;
			if (Roll(2, H, 4) < P)
			{
				C++;
				if (Tagged) R++;
			}
		}
		Out.Marked = M;
		Out.Caught = C;
		Out.Recaptured = R;
		Out.Truth = Set.Population;
		return Out;
	}

private:
	MarkRecaptureSettings Set;
	uint64_t SeedBits;
	int First = 0, Second = 0;

	double Roll(int Session, int64_t Hare, int Salt) const
	{
		uint64_t Z = SeedBits + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Session) + 1)
			+ 0xBF58476D1CE4E5B9ULL * static_cast<uint64_t>(Hare + 1) + 0x94D049BB133111EBULL * static_cast<uint64_t>(static_cast<int64_t>(Salt));
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
};

}} // namespace daedalus::marsh
