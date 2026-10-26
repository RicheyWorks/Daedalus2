// SPDX-License-Identifier: MIT
// G42 q_forge_temper C++ port (G51), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public forge_temper_quest_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public forge_temper_quest_core_test.cpp
// Run with --write to regenerate forge_temper_quest_parity.txt (read by ForgeTemperQuestParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusForgeTemperQuestCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static TemperResult Forged(Quench Q)
{
	TemperBlank B;
	MakeBlank(Material::Steel, 7, B);
	TemperResult R;
	Judge(B, IdealRun(B, Q), R);
	return R;
}

static void AllPens(ForgeTemperQuest& Q)
{
	for (int P = 0; P < QuestPenCount; ++P) Q.WaterPen(static_cast<Life>(P), LifeOf(static_cast<Life>(P)).DlPerDay);
}

// The parity script; ForgeTemperQuestParityTest.java plays exactly the same events.
static const char* const Sources[] = { "HotSpring_Clean", "SteamVentCatch", "RainCatch_Ash", "SaltStill_Basalt", "AshWell_Dirty", "QuenchTrough_Forge" };
static const Material Metals[] = { Material::Copper, Material::Bronze, Material::Iron, Material::Steel, Material::Starmetal };

static void Play(int Seed, std::FILE* F)
{
	SplitRng Rng(static_cast<int64_t>(Seed) * 131 + 9);
	ForgeTemperQuest Q;
	for (int E = 0; E < 60; ++E)
	{
		const int Kind = Rng.NextInt(9);
		QuestOutcome O = QuestOutcome::Progress;
		char Ev[48];
		switch (Kind)
		{
		case 0: { const int S = Rng.NextInt(6); O = Q.Drink(Sources[S]); std::snprintf(Ev, sizeof Ev, "drink %s", Sources[S]); break; }
		case 1: { const int P = Rng.NextInt(LifeCount); const int Dl = Rng.NextInt(130); O = Q.WaterPen(static_cast<Life>(P), Dl); std::snprintf(Ev, sizeof Ev, "pen %s %d", LifeOf(static_cast<Life>(P)).Id, Dl); break; }
		case 2: { const int Bd = Rng.NextInt(4); const int Dl = Rng.NextInt(15); O = Q.WaterBed(Bd, Dl); std::snprintf(Ev, sizeof Ev, "bed %d %d", Bd, Dl); break; }
		case 3:
		{
			const int R = Rng.NextInt(9); const Quench P = static_cast<Quench>(Rng.NextInt(3));
			const char* Recipe = R < 8 ? QuestDualCookbook()[R] : "tea_ashmint_draught";
			O = Q.QuenchTonic(Recipe, P); std::snprintf(Ev, sizeof Ev, "tonic %s %d", Recipe, static_cast<int>(P)); break;
		}
		case 4:
		{
			const int M = Rng.NextInt(5); const int BS = Rng.NextInt(1000); const Quench P = static_cast<Quench>(Rng.NextInt(3));
			TemperBlank B; MakeBlank(Metals[M], BS, B); TemperResult R; Judge(B, IdealRun(B, P), R);
			O = Q.LeavePlate(R); std::snprintf(Ev, sizeof Ev, "plate %d %d %d", M, BS, static_cast<int>(P)); break;
		}
		case 5: Q.EndShift(); std::snprintf(Ev, sizeof Ev, "bell"); break;
		case 7: { const int Bd = Rng.NextInt(QuestBeds); O = Q.WaterBed(Bd, QuestBedDl); std::snprintf(Ev, sizeof Ev, "bed %d %d", Bd, QuestBedDl); break; }
		default: { const int P = Rng.NextInt(QuestPenCount); const int Dl = LifeOf(static_cast<Life>(P)).DlPerDay; O = Q.WaterPen(static_cast<Life>(P), Dl); std::snprintf(Ev, sizeof Ev, "pen %s %d", LifeOf(static_cast<Life>(P)).Id, Dl); break; }
		}
		if (F) std::fprintf(F, "s=%d e=%d %s -> %s %s %d\n", Seed, E, Ev, Kind == 5 ? "-" : QuestOutcomeName(O), QuestStepName(Q.Current()), Q.Glow());
	}
	if (F) std::fprintf(F, "s=%d | %s\n", Seed, Encode(Q).c_str());
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	{
		ForgeTemperQuest Q;
		Check("dirty water refused", Q.Drink("AshWell_Dirty") == QuestOutcome::DirtyWater && Q.Drink("QuenchTrough_Forge") == QuestOutcome::DirtyWater && Q.Glow() == 0);
		Check("arrival", Q.Drink("HotSpring_Clean") == QuestOutcome::StepDone && Q.Glow() == 30 && Q.Current() == QuestStep::Pens);
		AllPens(Q);
		Check("pens", Q.Current() == QuestStep::Tonic && Q.Glow() == 60);
		Check("tonic must be dual and from the book", Q.QuenchTonic("tea_ashmint_draught", Quench::Dual) == QuestOutcome::UnknownRecipe
			&& Q.QuenchTonic("dual_void_crossing", Quench::Magma) == QuestOutcome::NotDual
			&& Q.QuenchTonic("dual_drydock_shift", Quench::Dual) == QuestOutcome::StepDone && Q.Tonic == "dual_drydock_shift");
		Check("only stamped plates", Q.LeavePlate(Forged(Quench::Magma)) == QuestOutcome::NotStamped
			&& Q.LeavePlate(Forged(Quench::Dual)) == QuestOutcome::StepDone && Q.Glow() == 70);
		Q.WaterBed(0, 10); Q.WaterBed(1, 10);
		Check("beds then glow 100 completes", Q.WaterBed(2, 10) == QuestOutcome::QuestComplete && Q.Complete() && Q.Glow() == 100
			&& Q.Current() == QuestStep::Complete && Q.Drink("SteamVentCatch") == QuestOutcome::AlreadyDone);
		Check("encode", Encode(Q) == "FTQ 1 COMPLETE glow=100 tonic=dual_drydock_shift shifts=0 done=111111");
	}
	{
		ForgeTemperQuest Q;
		for (int P = 0; P < 5; ++P) Q.WaterPen(static_cast<Life>(P), LifeOf(static_cast<Life>(P)).DlPerDay);
		Q.WaterBed(0, 10);
		const int Before = Q.Glow();
		Q.EndShift();
		Check("shift bell dries unfinished troughs and beds", Before == 35 && Q.Glow() == 0 && Q.Shifts == 1);
		Check("not a pen / bad amounts", Q.WaterPen(Life::Pet, 50) == QuestOutcome::NotAPen && Q.WaterPen(Life::Ashgoat, 0) == QuestOutcome::BadAmount
			&& Q.WaterBed(3, 10) == QuestOutcome::NoSuchBed && Q.WaterBed(0, 9) == QuestOutcome::BadAmount);
	}
	Check("keeper line", std::strstr(QuestKeeperLine(QuestStep::Complete), "tempered") != nullptr);

	if (WriteOut)
	{
		std::FILE* F = std::fopen("forge_temper_quest_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# forge_temper_quest_core_test.cpp --write: FTQ 1 parity (hephaestus). Seeds 0..99, 60 events each.\n", F);
		for (int Seed = 0; Seed < 100; ++Seed) Play(Seed, F);
		std::fclose(F);
		std::printf("wrote forge_temper_quest_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
