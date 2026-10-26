// SPDX-License-Identifier: MIT
// G42 q_forge_temper (Hephaestus arrival quest), plain C++17 for the Unreal binding (G51).
// A port of daedalus-core world/forge/ForgeTemperQuest.java with no Unreal types. Byte parity with
// Java is checked through engines/unreal/core-test/forge_temper_quest_parity.txt (ForgeTemperQuestParityTest).
#pragma once
#include "DaedalusArkDrydockCore.h"
#include <cstdio>
#include <cstring>
#include <string>

namespace daedalus { namespace forge {

constexpr int QuestGlowWater = 30, QuestGlowAnimals = 30, QuestGlowHerbs = 30, QuestGlowTea = 10;
constexpr int QuestBeds = 3, QuestBedDl = 10, QuestPenCount = 6;

inline const char* const* QuestCleanSources()
{
	static const char* const S[] = { "HotSpring_Clean", "SteamVentCatch", "RainCatch_Ash", "SaltStill_Basalt", nullptr };
	return S;
}
inline const char* const* QuestDualCookbook()
{
	static const char* const D[] = { "dual_riveters_temper", "dual_lava_runner", "dual_caldera_canteen", "dual_quench_tub_draught",
		"dual_drydock_shift", "dual_void_crossing", "dual_ash_well_antidote", "dual_scar_prospector", nullptr };
	return D;
}
inline bool QuestListHas(const char* const* L, const char* S)
{
	for (; *L; ++L) if (std::strcmp(*L, S) == 0) return true;
	return false;
}
/** The six pens are the first six Life values (emberhen..vent bees); Pet and SeedCrate are not pens. */
inline bool QuestIsPen(Life L) { return static_cast<int>(L) < QuestPenCount; }

enum class QuestStep : int { Arrival = 0, Pens, Tonic, Plate, Glow, Complete };
constexpr int QuestStepCount = 6;
inline const char* QuestStepName(QuestStep S)
{
	static const char* const N[] = { "ARRIVAL", "PENS", "TONIC", "PLATE", "GLOW", "COMPLETE" };
	return N[static_cast<int>(S)];
}

enum class QuestOutcome : int { Progress = 0, StepDone, AlreadyDone, DirtyWater, NotAPen, NotDual, UnknownRecipe, NotStamped, BadAmount, NoSuchBed, QuestComplete };
inline const char* QuestOutcomeName(QuestOutcome O)
{
	static const char* const N[] = { "PROGRESS", "STEP_DONE", "ALREADY_DONE", "DIRTY_WATER", "NOT_A_PEN", "NOT_DUAL", "UNKNOWN_RECIPE",
		"NOT_STAMPED", "BAD_AMOUNT", "NO_SUCH_BED", "QUEST_COMPLETE" };
	return N[static_cast<int>(O)];
}

/** One player's q_forge_temper, held by the host (mirrors ForgeTemperQuest.Quest). */
struct ForgeTemperQuest
{
	bool Done[QuestStepCount] = {};
	int Trough[QuestPenCount] = {};
	bool Beds[QuestBeds] = {};
	bool BedsGlowing = false;
	std::string Tonic;
	int Shifts = 0;

	QuestOutcome Drink(const char* Source)
	{
		if (!QuestListHas(QuestCleanSources(), Source)) return QuestOutcome::DirtyWater;
		return Finish(QuestStep::Arrival);
	}

	QuestOutcome WaterPen(Life Pen, int Dl)
	{
		if (!QuestIsPen(Pen)) return QuestOutcome::NotAPen;
		if (Dl <= 0) return QuestOutcome::BadAmount;
		if (Has(QuestStep::Pens)) return QuestOutcome::AlreadyDone;
		Trough[static_cast<int>(Pen)] += Dl;
		for (int P = 0; P < QuestPenCount; ++P)
			if (Trough[P] < LifeOf(static_cast<Life>(P)).DlPerDay) return QuestOutcome::Progress;
		return Finish(QuestStep::Pens);
	}

	QuestOutcome WaterBed(int Bed, int Dl)
	{
		if (Bed < 0 || Bed >= QuestBeds) return QuestOutcome::NoSuchBed;
		if (Dl < QuestBedDl) return QuestOutcome::BadAmount;
		if (Beds[Bed]) return QuestOutcome::AlreadyDone;
		Beds[Bed] = true;
		bool All = true;
		for (bool B : Beds) All = All && B;
		BedsGlowing = BedsGlowing || All;
		return All ? CheckGlow() : QuestOutcome::Progress;
	}

	QuestOutcome QuenchTonic(const char* Recipe, Quench Path)
	{
		if (!QuestListHas(QuestDualCookbook(), Recipe)) return QuestOutcome::UnknownRecipe;
		if (Path != Quench::Dual) return QuestOutcome::NotDual;
		if (Tonic.empty()) Tonic = Recipe;
		return Finish(QuestStep::Tonic);
	}

	QuestOutcome LeavePlate(const TemperResult& Forged)
	{
		if (!Forged.ArkPlate) return QuestOutcome::NotStamped;
		return Finish(QuestStep::Plate);
	}

	void EndShift()
	{
		++Shifts;
		if (!Has(QuestStep::Pens)) for (int& T : Trough) T = 0;
		if (!BedsGlowing) for (bool& B : Beds) B = false;
	}

	int Glow() const
	{
		int Pens = 0;
		for (int P = 0; P < QuestPenCount; ++P)
			if (Has(QuestStep::Pens) || Trough[P] >= LifeOf(static_cast<Life>(P)).DlPerDay) ++Pens;
		int Wet = 0;
		for (bool B : Beds) Wet += B ? 1 : 0;
		return (Has(QuestStep::Arrival) ? QuestGlowWater : 0) + QuestGlowAnimals * Pens / QuestPenCount
			+ QuestGlowHerbs * (BedsGlowing ? QuestBeds : Wet) / QuestBeds + (Tonic.empty() ? 0 : QuestGlowTea);
	}

	QuestStep Current() const
	{
		for (int S = 0; S < QuestStepCount; ++S) if (!Done[S]) return static_cast<QuestStep>(S);
		return QuestStep::Complete;
	}

	bool Complete() const { return Has(QuestStep::Complete); }
	bool Has(QuestStep S) const { return Done[static_cast<int>(S)]; }

private:
	QuestOutcome Finish(QuestStep S)
	{
		if (Has(QuestStep::Complete)) return QuestOutcome::AlreadyDone;
		if (Has(S)) return QuestOutcome::AlreadyDone;
		Done[static_cast<int>(S)] = true;
		return CheckGlow() == QuestOutcome::QuestComplete ? QuestOutcome::QuestComplete : QuestOutcome::StepDone;
	}

	QuestOutcome CheckGlow()
	{
		if (Glow() == 100 && Has(QuestStep::Arrival) && Has(QuestStep::Pens) && Has(QuestStep::Tonic) && Has(QuestStep::Plate))
		{
			Done[static_cast<int>(QuestStep::Glow)] = true;
			Done[static_cast<int>(QuestStep::Complete)] = true;
			return QuestOutcome::QuestComplete;
		}
		return QuestOutcome::Progress;
	}
};

/** Old Keeper Ysolde Anvilward's line for a step (same text as ForgeTemperQuest.keeperLine). */
inline const char* QuestKeeperLine(QuestStep S)
{
	switch (S)
	{
	case QuestStep::Arrival: return "Drink first, smith. The caldera takes water twice as fast as you think. Clean springs only.";
	case QuestStep::Pens: return "Hens, goats, oxen, boars, wool and bees. Fill every trough before the shift bell, or start again.";
	case QuestStep::Tonic: return "Brew it at the mortar, then magma and spring within ten breaths. One dual tonic, from the book.";
	case QuestStep::Plate: return "Heat alone breaks. Water alone softens. Bring me a plate with your stamp on it.";
	case QuestStep::Glow: return "Water the three beds. When water, pens, herbs and tonic all run, the Great Forge will tell you.";
	default: return "She glows. You are tempered, smith. The drydock will take your plates now.";
	}
}

/** One-line FTQ 1 summary: step, glow, tonic, shifts, done flags. */
inline std::string Encode(const ForgeTemperQuest& Q)
{
	char Flags[QuestStepCount + 1];
	for (int S = 0; S < QuestStepCount; ++S) Flags[S] = Q.Done[S] ? '1' : '0';
	Flags[QuestStepCount] = 0;
	char Buf[160];
	std::snprintf(Buf, sizeof Buf, "FTQ 1 %s glow=%d tonic=%s shifts=%d done=%s", QuestStepName(Q.Current()), Q.Glow(),
		Q.Tonic.empty() ? "-" : Q.Tonic.c_str(), Q.Shifts, Flags);
	return Buf;
}

}} // namespace daedalus::forge
