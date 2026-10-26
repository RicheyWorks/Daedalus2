// SPDX-License-Identifier: MIT
// Kennel Isle pet state for the Unreal binding (contest G102), header-only and engine-free.
// Composes the G84 rules in DaedalusKennelCore.h (G37 bond, G61 drills, G65 growth) into one pet:
//   care during a day -> EndDay (bond step + care-day growth with a seeded spurt roll) -> drills gated by tier and stage.
// UDaedalusKennelPet (DaedalusKennel.h) only forwards to this; core-test/kennel_pet_core_test.cpp tests it with gcc and clang.
#pragma once

#include "DaedalusKennelCore.h"
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>

namespace daedalus { namespace kennel {

/** FNV-1a 64 over the pet key. */
inline uint64_t KeyHash(const std::string& Key)
{
	uint64_t H = 14695981039346656037ull;
	for (unsigned char C : Key) { H ^= C; H *= 1099511628211ull; }
	return H;
}

/** Seeded 0..99 roll for (pet, day, salt): same pet, same day, same salt, same roll on every machine. */
inline int Roll100(const std::string& Key, int Day, int Salt)
{
	uint64_t H = KeyHash(Key);
	H ^= static_cast<uint64_t>(static_cast<uint32_t>(Day)) * 0x9E3779B97F4A7C15ull;
	H ^= static_cast<uint64_t>(static_cast<uint32_t>(Salt)) * 0xC2B2AE3D27D4EB4Full;
	H ^= H >> 33; H *= 0xff51afd7ed558ccdull;
	H ^= H >> 33; H *= 0xc4ceb9fe1a85ec53ull;
	H ^= H >> 33;
	return static_cast<int>(H % 100ull);
}

enum class ECare { Feed = 0, Water, Tonic, Fetch, Unknown };
enum class EDrill { Obeyed = 0, Failed, TierLocked, StageLocked, Unknown };

inline ECare CareOf(const char* Name)
{
	static const char* N[] = {"feed", "water", "tonic", "fetch"};
	for (int I = 0; I < 4; ++I) { if (std::strcmp(Name, N[I]) == 0) { return static_cast<ECare>(I); } }
	return ECare::Unknown;
}

inline const char* DrillName(EDrill D)
{
	static const char* N[] = {"OBEYED", "FAILED", "TIER_LOCKED", "STAGE_LOCKED", "UNKNOWN"};
	return N[static_cast<int>(D)];
}

constexpr int MaxCareDays = 9999;
constexpr int MaxFetchPerDay = 99;
constexpr int SpurtSalt = 0;
constexpr int DrillSaltBase = 1000;

/** What one EndDay did, for the UE delegate and the console. */
struct FDayReport
{
	int Day = 0, BondBefore = 0, BondAfter = 0, CareBefore = 0, CareAfter = 0, Roll = 0;
	bool bNeglected = false;
	ETier TierBefore = ETier::Wary, TierAfter = ETier::Wary;
	EStage StageBefore = EStage::Newborn, StageAfter = EStage::Newborn;
	bool TierChanged() const { return TierBefore != TierAfter; }
	bool StageChanged() const { return StageBefore != StageAfter; }
};

struct FPet
{
	std::string Key;
	int Bond = 0, CareDays = 0, Day = 0, DrillsToday = 0;
	FCare Today;

	ETier Tier() const { return TierOf(Bond); }
	EStage Stage() const { return StageOf(CareDays); }

	/** Feed, water and tonic count once a day; a repeat returns false and changes nothing. */
	bool Care(ECare C, int Catches = 1)
	{
		switch (C)
		{
		case ECare::Feed: if (Today.bFed) { return false; } Today.bFed = true; return true;
		case ECare::Water: if (Today.bWatered) { return false; } Today.bWatered = true; return true;
		case ECare::Tonic: if (Today.bTonic) { return false; } Today.bTonic = true; return true;
		case ECare::Fetch:
			if (Catches <= 0 || Today.FetchCatches >= MaxFetchPerDay) { return false; }
			Today.FetchCatches = std::min(MaxFetchPerDay, Today.FetchCatches + Catches);
			return true;
		case ECare::Unknown: break;
		}
		return false;
	}

	/** Close the day: G65 growth with the seeded spurt roll, G37 bond step, then a fresh day. */
	FDayReport EndDay(const FBondRules& R = FBondRules())
	{
		FDayReport Rep;
		Rep.Day = Day; Rep.BondBefore = Bond; Rep.CareBefore = CareDays;
		Rep.TierBefore = Tier(); Rep.StageBefore = Stage();
		Rep.bNeglected = Today.Neglected();
		Rep.Roll = Roll100(Key, Day, SpurtSalt);
		CareDays = std::min(MaxCareDays, GrowCareDays(CareDays, Today, Rep.Roll));
		Bond = StepBond(Bond, Today, R);
		Rep.BondAfter = Bond; Rep.CareAfter = CareDays;
		Rep.TierAfter = Tier(); Rep.StageAfter = Stage();
		++Day; DrillsToday = 0; Today = FCare();
		return Rep;
	}

	/** A G61 drill: stage gate, then tier gate, then a seeded roll against SuccessPct. Locked drills do not roll. */
	EDrill Drill(ECommand C, int* OutRoll = nullptr, int* OutPct = nullptr)
	{
		if (OutRoll) { *OutRoll = -1; }
		if (OutPct) { *OutPct = C == ECommand::Unknown ? 0 : SuccessPct(Bond, C); }
		if (C == ECommand::Unknown) { return EDrill::Unknown; }
		if (!StageAllows(Stage(), C)) { return EDrill::StageLocked; }
		if (!Obeys(Bond, C)) { return EDrill::TierLocked; }
		const int Roll = Roll100(Key, Day, DrillSaltBase + DrillsToday++);
		if (OutRoll) { *OutRoll = Roll; }
		return Roll < SuccessPct(Bond, C) ? EDrill::Obeyed : EDrill::Failed;
	}
};

/** "Bond_62" -> 62 when Prefix is "Bond_" and the rest is 1-4 digits; clamped to [Lo, Hi]. */
inline bool IntFromTag(const std::string& Tag, const char* Prefix, int Lo, int Hi, int& Out)
{
	const size_t P = std::strlen(Prefix);
	if (Tag.size() <= P || Tag.size() > P + 4 || Tag.compare(0, P, Prefix) != 0) { return false; }
	int V = 0;
	for (size_t I = P; I < Tag.size(); ++I)
	{
		if (Tag[I] < '0' || Tag[I] > '9') { return false; }
		V = V * 10 + (Tag[I] - '0');
	}
	Out = std::max(Lo, std::min(Hi, V));
	return true;
}

/** A placed pet's starting state from its actor tags (Bond_NN, CareDays_NN); missing tags leave 0. First valid tag wins. */
inline FPet PetFromTags(const std::vector<std::string>& Tags, const std::string& Key)
{
	FPet P; P.Key = Key;
	bool bBond = false, bCare = false;
	for (const std::string& T : Tags)
	{
		int V = 0;
		if (!bBond && IntFromTag(T, "Bond_", 0, FBondRules().Max, V)) { P.Bond = V; bBond = true; }
		else if (!bCare && IntFromTag(T, "CareDays_", 0, MaxCareDays, V)) { P.CareDays = V; bCare = true; }
	}
	return P;
}

/** One status line for the console and logs. */
inline std::string StatusLine(const FPet& P)
{
	std::string S = P.Key + " day=" + std::to_string(P.Day) + " bond=" + std::to_string(P.Bond) + " tier=" + TierName(P.Tier())
		+ " caredays=" + std::to_string(P.CareDays) + " stage=" + StageName(P.Stage())
		+ " fed=" + (P.Today.bFed ? "1" : "0") + " watered=" + (P.Today.bWatered ? "1" : "0")
		+ " tonic=" + (P.Today.bTonic ? "1" : "0") + " fetch=" + std::to_string(P.Today.FetchCatches);
	return S;
}

}} // namespace daedalus::kennel
