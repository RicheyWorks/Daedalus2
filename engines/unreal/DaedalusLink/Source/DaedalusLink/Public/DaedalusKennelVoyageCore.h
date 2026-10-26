// SPDX-License-Identifier: MIT
// Kennel Isle ark voyage + landfall, header-only C++ twin of the Java G140 KennelArkVoyage.crossRolls and G147
// KennelArkLandfall.repairRolls (contest G154, art-master-flex). Engine-free so the UE leg tracker and Cinder Shelf repair
// widgets replay the server's rolls with the same rules. Parity table: engines/unreal/core-test/kennel_voyage_parity.txt,
// checked against Java by KennelVoyageParityFixtureTest and replayed by core-test/kennel_voyage_core_test.cpp. The
// seeded rolls themselves stay on the Java side.
#pragma once

#include <vector>

namespace daedalus { namespace kennel { namespace voyage {

/** Post order matches KennelArkMuster.ROLES: hatch guard, rescue swimmer, spring finder, deck runner. */
constexpr int NumPosts = 4;
constexpr int PostRescue = 1;
constexpr int PostFetch = 2;
constexpr int PostCome = 3;
constexpr int Legs = 6;
constexpr int StartHull = 10;
constexpr int StartWater = 10;
constexpr int Days = 5;
constexpr int HullFull = StartHull;
constexpr int FetchPlanks = 2;
constexpr int HaulPlanks = 1;
constexpr int RollsPerDay = 3;
constexpr int StrandedCount = 3;

/** KennelArkVoyage.Trouble, in ordinal order; each is answered by the post with the same index. */
enum class ETrouble : int { BoardingGust = 0, Overboard = 1, DryCasks = 2, JammedSignal = 3 };
constexpr int NumTroubles = 4;

inline int TroublePost(ETrouble T) { return static_cast<int>(T); }
inline int HullToll(ETrouble T) { static const int H[NumTroubles] = {3, 2, 0, 2}; return H[static_cast<int>(T)]; }
inline int WaterToll(ETrouble T) { static const int W[NumTroubles] = {0, 2, 4, 1}; return W[static_cast<int>(T)]; }

/** Voyage endings: arrived / "the hull gave way" / "the casks ran dry". */
enum class EVoyageFail : int { None = 0, HullGaveWay = 1, CasksRanDry = 2 };
/** Landfall endings: seaworthy / "the casks ran dry on the shelf" / "the hull was not mended in time". */
enum class ELandfallFail : int { None = 0, CasksRanDry = 1, NotMended = 2 };

struct FLeg
{
	ETrouble Trouble = ETrouble::BoardingGust;
	bool bAnswered = false;
	int Hull = 0;
	int Water = 0;
};

struct FVoyage
{
	bool bArrived = false;
	std::vector<FLeg> LegLog;
	int Hull = StartHull;
	int Water = StartWater;
	EVoyageFail Fail = EVoyageFail::None;
};

/**
 * KennelArkVoyage.crossRolls. Pct holds each post's odds (0 for an empty post, which always fails); one roll 0..99 per
 * trouble, answered when below the odds. Stops at the leg where hull or water reaches 0. False on bad input.
 */
inline bool Cross(const int (&Pct)[NumPosts], const std::vector<ETrouble>& Troubles, const std::vector<int>& Rolls, FVoyage& Out)
{
	Out = FVoyage();
	if (Troubles.size() > static_cast<size_t>(Legs) || Rolls.size() < Troubles.size()) { return false; }
	for (size_t I = 0; I < Troubles.size(); ++I)
	{
		const ETrouble T = Troubles[I];
		const bool bAnswered = Rolls[I] < Pct[TroublePost(T)];
		if (!bAnswered)
		{
			Out.Hull = Out.Hull > HullToll(T) ? Out.Hull - HullToll(T) : 0;
			Out.Water = Out.Water > WaterToll(T) ? Out.Water - WaterToll(T) : 0;
		}
		Out.LegLog.push_back(FLeg{T, bAnswered, Out.Hull, Out.Water});
		if (Out.Hull == 0 || Out.Water == 0)
		{
			Out.Fail = Out.Hull == 0 ? EVoyageFail::HullGaveWay : EVoyageFail::CasksRanDry;
			return true;
		}
	}
	Out.bArrived = true;
	return true;
}

struct FDay
{
	bool bFetched = false;
	bool bHauled = false;
	bool bRescued = false;
	int Planks = 0;
	int Hull = 0;
	int Water = 0;
};

struct FLandfall
{
	bool bSeaworthy = false;
	std::vector<FDay> DayLog;
	int Hull = 0;
	int Water = 0;
	int Rescued = 0;
	ELandfallFail Fail = ELandfallFail::None;
};

/**
 * KennelArkLandfall.repairRolls. RollsPerDay rolls per day (fetch, haul, rescue). Stranded is how many animals wait on
 * the shelf. Stops when the hull is full, the casks reach 0, or after Days days. False on bad input.
 */
inline bool Repair(const int (&Pct)[NumPosts], int Hull, int Water, int Stranded, const std::vector<int>& Rolls, FLandfall& Out)
{
	Out = FLandfall();
	if (Hull < 1 || Hull > HullFull || Water < 1 || Water > StartWater || Stranded < 0
		|| Rolls.size() < static_cast<size_t>(RollsPerDay * Days))
	{
		return false;
	}
	Out.Hull = Hull;
	Out.Water = Water;
	for (int D = 0; D < Days && Out.Hull < HullFull; ++D)
	{
		const size_t K = static_cast<size_t>(D * RollsPerDay);
		FDay Day;
		Day.bFetched = Rolls[K] < Pct[PostFetch];
		Day.bHauled = Rolls[K + 1] < Pct[PostCome];
		Day.bRescued = Rolls[K + 2] < Pct[PostRescue] && Out.Rescued < Stranded;
		if (Day.bRescued) { ++Out.Rescued; }
		Day.Planks = (Day.bFetched ? FetchPlanks : 0) + (Day.bHauled ? HaulPlanks : 0);
		Out.Hull = Out.Hull + Day.Planks < HullFull ? Out.Hull + Day.Planks : HullFull;
		--Out.Water;
		Day.Hull = Out.Hull;
		Day.Water = Out.Water;
		Out.DayLog.push_back(Day);
		if (Out.Water == 0)
		{
			Out.Fail = ELandfallFail::CasksRanDry;
			return true;
		}
	}
	Out.bSeaworthy = Out.Hull == HullFull;
	Out.Fail = Out.bSeaworthy ? ELandfallFail::None : ELandfallFail::NotMended;
	return true;
}

}}} // namespace daedalus::kennel::voyage