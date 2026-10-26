// SPDX-License-Identifier: MIT
// Kennel Isle care rules, header-only C++ twin of the Java companion code (contest G84):
//   G37 KennelBond (tiers, daily step, obeys), G61 KennelTraining (drill odds), G65 KennelGrowth (stages, care-day).
// Engine-free so the UE pet panel and the core-test parity check share one copy. Parity table:
// engines/unreal/core-test/kennel_parity.txt, written by KennelParityFixtureTest.
#pragma once

#include <algorithm>
#include <cstring>

namespace daedalus { namespace kennel {

enum class ETier { Wary = 0, Familiar, Loyal, Devoted };
enum class EStage { Newborn = 0, Pup, Juvenile, Adult, Elder };
enum class ECommand { Come = 0, Stay, Fetch, Guard, Rescue, Unknown };

struct FBondRules
{
	int FedGain = 4, WaterGain = 2, TonicGain = 3, FetchGainPerCatch = 1, FetchCap = 5;
	int NeglectPenalty = 10, DailyDecay = 1, Max = 100;
};

struct FCare
{
	bool bFed = false, bWatered = false, bTonic = false;
	int FetchCatches = 0;
	bool Neglected() const { return !bFed || !bWatered; }
};

inline const char* TierName(ETier T)
{
	static const char* N[] = {"WARY", "FAMILIAR", "LOYAL", "DEVOTED"};
	return N[static_cast<int>(T)];
}

inline const char* StageName(EStage S)
{
	static const char* N[] = {"NEWBORN", "PUP", "JUVENILE", "ADULT", "ELDER"};
	return N[static_cast<int>(S)];
}

inline ECommand CommandOf(const char* Name)
{
	static const char* N[] = {"come", "stay", "fetch", "guard", "rescue"};
	for (int I = 0; I < 5; ++I) { if (std::strcmp(Name, N[I]) == 0) { return static_cast<ECommand>(I); } }
	return ECommand::Unknown;
}

inline ETier TierOf(int Bond)
{
	return Bond >= 80 ? ETier::Devoted : Bond >= 50 ? ETier::Loyal : Bond >= 25 ? ETier::Familiar : ETier::Wary;
}

/** Commands unlock cumulatively: Familiar come; Loyal stay, fetch; Devoted guard, rescue. */
inline bool Obeys(int Bond, ECommand C)
{
	static const ETier Need[] = {ETier::Familiar, ETier::Loyal, ETier::Loyal, ETier::Devoted, ETier::Devoted};
	if (C == ECommand::Unknown) { return false; }
	return static_cast<int>(TierOf(Bond)) >= static_cast<int>(Need[static_cast<int>(C)]);
}

inline int StepBond(int Bond, const FCare& C, const FBondRules& R = FBondRules())
{
	int Next;
	if (C.Neglected()) { Next = Bond - R.NeglectPenalty - R.DailyDecay; }
	else
	{
		Next = Bond + R.FedGain + R.WaterGain + (C.bTonic ? R.TonicGain : 0)
			+ std::min(C.FetchCatches, R.FetchCap) * R.FetchGainPerCatch - R.DailyDecay;
	}
	return std::max(0, std::min(R.Max, Next));
}

inline int Difficulty(ECommand C)
{
	static const int D[] = {0, 10, 20, 35, 50};
	return C == ECommand::Unknown ? -1 : D[static_cast<int>(C)];
}

/** G61 drill success percent: clamp(40 + bond / 2 - difficulty, 5, 95). */
inline int SuccessPct(int Bond, ECommand C)
{
	return std::max(5, std::min(95, 40 + Bond / 2 - Difficulty(C)));
}

inline EStage StageOf(int CareDays)
{
	return CareDays >= 60 ? EStage::Elder : CareDays >= 21 ? EStage::Adult : CareDays >= 10 ? EStage::Juvenile
		: CareDays >= 3 ? EStage::Pup : EStage::Newborn;
}

inline bool StageAllows(EStage S, ECommand C)
{
	switch (S)
	{
	case EStage::Newborn: return false;
	case EStage::Pup: return C == ECommand::Come;
	case EStage::Juvenile: return C == ECommand::Come || C == ECommand::Stay || C == ECommand::Fetch;
	case EStage::Adult: return C != ECommand::Unknown;
	case EStage::Elder: return C != ECommand::Unknown && C != ECommand::Rescue;
	}
	return false;
}

constexpr int SpurtPct = 15;

/** G65 care-days after one day: +1 on a care-day, +1 more on a bonded care-day when Roll < SpurtPct. */
inline int GrowCareDays(int CareDays, const FCare& C, int Roll)
{
	if (C.Neglected()) { return CareDays; }
	const bool bBonded = C.bTonic || C.FetchCatches > 0;
	return CareDays + 1 + ((bBonded && Roll < SpurtPct) ? 1 : 0);
}

}} // namespace daedalus::kennel