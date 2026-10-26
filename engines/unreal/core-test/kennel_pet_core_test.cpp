// SPDX-License-Identifier: MIT
// G102: the Kennel Unreal binding's engine-free pet core (DaedalusKennelPetCore.h) over the G84 rules.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public kennel_pet_core_test.cpp -o kennel_pet_core_test && ./kennel_pet_core_test
#include "DaedalusKennelPetCore.h"
#include <cstdio>
using namespace daedalus::kennel;

static int GTotal = 0, GBad = 0;
static void Check(bool bOk, const char* What)
{
	++GTotal;
	if (!bOk) { ++GBad; std::printf("FAIL %s\n", What); }
}

static FPet Make(const char* Key, int Bond, int CareDays)
{
	FPet P; P.Key = Key; P.Bond = Bond; P.CareDays = CareDays; return P;
}

int main()
{
	// Rolls: in range, deterministic, salt/day/key sensitive, roughly uniform.
	{
		int Buckets[10] = {0};
		bool bRange = true;
		for (int D = 0; D < 2000; ++D)
		{
			const int R = Roll100("Pup_A", D, 0);
			bRange = bRange && R >= 0 && R < 100;
			if (R >= 0 && R < 100) { ++Buckets[R / 10]; }
		}
		Check(bRange, "roll in 0..99");
		bool bFlat = true;
		for (int B : Buckets) { bFlat = bFlat && B > 120 && B < 280; }
		Check(bFlat, "roll roughly uniform over 2000 days");
		Check(Roll100("Pup_A", 7, 3) == Roll100("Pup_A", 7, 3), "roll deterministic");
		int Diff = 0;
		for (int D = 0; D < 50; ++D) { Diff += Roll100("Pup_A", D, 0) != Roll100("Pup_B", D, 0); }
		Check(Diff > 35, "different pets roll differently");
		Diff = 0;
		for (int D = 0; D < 50; ++D) { Diff += Roll100("Pup_A", D, 0) != Roll100("Pup_A", D, 1000); }
		Check(Diff > 35, "spurt and drill salts differ");
		Check(KeyHash("") == 14695981039346656037ull, "fnv offset basis");
		Check(KeyHash("a") == 0xaf63dc4c8601ec8cull, "fnv-1a 'a'");
		Check(Roll100("Pup_A", 0, 0) == 57, "golden roll Pup_A day 0");
	}

	// Names.
	Check(CareOf("feed") == ECare::Feed && CareOf("water") == ECare::Water && CareOf("tonic") == ECare::Tonic
		&& CareOf("fetch") == ECare::Fetch && CareOf("Feed") == ECare::Unknown && CareOf("") == ECare::Unknown, "care names");
	Check(std::strcmp(DrillName(EDrill::StageLocked), "STAGE_LOCKED") == 0 && std::strcmp(DrillName(EDrill::Obeyed), "OBEYED") == 0, "drill names");

	// Tags.
	{
		int V = -1;
		Check(IntFromTag("Bond_62", "Bond_", 0, 100, V) && V == 62, "Bond_62");
		Check(IntFromTag("Bond_250", "Bond_", 0, 100, V) && V == 100, "Bond_250 clamps");
		Check(!IntFromTag("Bond_", "Bond_", 0, 100, V), "Bond_ empty");
		Check(!IntFromTag("Bond_6x", "Bond_", 0, 100, V), "Bond_6x");
		Check(!IntFromTag("Bond_12345", "Bond_", 0, 100, V), "Bond_ too long");
		Check(!IntFromTag("Bond_-4", "Bond_", 0, 100, V), "Bond_-4");
		Check(!IntFromTag("bond_40", "Bond_", 0, 100, V), "prefix case");
		const FPet P = PetFromTags({"AMF_Wild", "Coat_Spotted", "Bond_55", "CareDays_12", "Bond_99", "CareDays_x"}, "Hound_3");
		Check(P.Key == "Hound_3" && P.Bond == 55 && P.CareDays == 12 && P.Day == 0, "pet from tags, first valid wins");
		Check(P.Tier() == ETier::Loyal && P.Stage() == EStage::Juvenile, "pet from tags tier/stage");
		const FPet Q = PetFromTags({"CareDays_bad", "CareDays_4"}, "Q");
		Check(Q.Bond == 0 && Q.CareDays == 4, "bad tag skipped, later valid tag used");
	}

	// Care once a day; fetch accumulates and caps.
	{
		FPet P = Make("Pup_A", 30, 5);
		Check(P.Care(ECare::Feed) && !P.Care(ECare::Feed), "feed once");
		Check(P.Care(ECare::Water) && !P.Care(ECare::Water), "water once");
		Check(P.Care(ECare::Tonic) && !P.Care(ECare::Tonic), "tonic once");
		Check(P.Care(ECare::Fetch, 3) && P.Care(ECare::Fetch, 4) && P.Today.FetchCatches == 7, "fetch accumulates");
		Check(!P.Care(ECare::Fetch, 0) && !P.Care(ECare::Fetch, -2) && !P.Care(ECare::Unknown), "bad care refused");
		Check(P.Care(ECare::Fetch, 500) && P.Today.FetchCatches == MaxFetchPerDay && !P.Care(ECare::Fetch, 1), "fetch caps");
	}

	// EndDay equals the G84 rules applied directly, every day, for a scripted 90-day run.
	{
		FPet P = Make("Hound_Run", 0, 0);
		bool bSame = true, bReset = true;
		for (int D = 0; D < 90; ++D)
		{
			FCare C;
			C.bFed = D % 9 != 4; C.bWatered = D % 13 != 7; C.bTonic = D % 3 == 0; C.FetchCatches = D % 4;
			if (C.bFed) { P.Care(ECare::Feed); }
			if (C.bWatered) { P.Care(ECare::Water); }
			if (C.bTonic) { P.Care(ECare::Tonic); }
			if (C.FetchCatches) { P.Care(ECare::Fetch, C.FetchCatches); }
			const int B0 = P.Bond, D0 = P.CareDays;
			const int Roll = Roll100("Hound_Run", D, SpurtSalt);
			const FDayReport R = P.EndDay();
			bSame = bSame && R.Day == D && R.Roll == Roll && R.BondBefore == B0 && R.CareBefore == D0
				&& R.BondAfter == StepBond(B0, C) && R.CareAfter == GrowCareDays(D0, C, Roll)
				&& P.Bond == R.BondAfter && P.CareDays == R.CareAfter && R.bNeglected == C.Neglected()
				&& R.TierAfter == TierOf(P.Bond) && R.StageAfter == StageOf(P.CareDays);
			bReset = bReset && P.Day == D + 1 && !P.Today.bFed && !P.Today.bWatered && !P.Today.bTonic && P.Today.FetchCatches == 0;
		}
		Check(bSame, "EndDay == StepBond + GrowCareDays for 90 days");
		Check(bReset, "EndDay starts a fresh day");
		Check(P.Stage() == EStage::Elder && P.Tier() == ETier::Devoted, "90 mostly-cared days: elder, devoted");
	}

	// Neglect: no growth, bond falls, tier drops reported.
	{
		FPet P = Make("Pup_N", 26, 3);
		P.Care(ECare::Feed);
		const FDayReport R = P.EndDay();
		Check(R.bNeglected && P.CareDays == 3 && P.Bond == 15, "neglect: no growth, -11 bond");
		Check(R.TierChanged() && R.TierBefore == ETier::Familiar && R.TierAfter == ETier::Wary && !R.StageChanged(), "tier drop reported");
		FPet Z = Make("Pup_Z", 5, 0);
		Z.EndDay();
		Check(Z.Bond == 0, "bond floors at 0");
	}

	// Newborn to pup in three cared days (no spurt without tonic/fetch).
	{
		FPet P = Make("Pup_S", 0, 0);
		FDayReport R;
		for (int D = 0; D < 3; ++D) { P.Care(ECare::Feed); P.Care(ECare::Water); R = P.EndDay(); }
		Check(P.CareDays == 3 && R.StageChanged() && R.StageAfter == EStage::Pup && P.Bond == 15, "three plain cared days");
	}

	// Drills: stage gate before tier gate; locked drills do not consume a roll; seeded and repeatable.
	{
		int Roll = 0, Pct = 0;
		FPet Newborn = Make("D", 100, 0);
		Check(Newborn.Drill(ECommand::Come, &Roll, &Pct) == EDrill::StageLocked && Roll == -1 && Pct == 90, "newborn stage-locked");
		FPet Wary = Make("D", 10, 30);
		Check(Wary.Drill(ECommand::Come, &Roll) == EDrill::TierLocked && Roll == -1 && Wary.DrillsToday == 0, "wary adult tier-locked");
		FPet Elder = Make("D", 100, 70);
		Check(Elder.Drill(ECommand::Rescue) == EDrill::StageLocked, "elder cannot rescue");
		FPet Pup = Make("D", 90, 5);
		Check(Pup.Drill(ECommand::Stay) == EDrill::StageLocked && Pup.Drill(ECommand::Come) != EDrill::StageLocked, "pup only comes");
		Check(Make("D", 90, 30).Drill(ECommand::Unknown, &Roll, &Pct) == EDrill::Unknown && Pct == 0, "unknown command");

		FPet A = Make("Hound_D", 80, 30), B = Make("Hound_D", 80, 30);
		int Obeyed = 0; bool bSame = true, bMatch = true;
		for (int I = 0; I < 200; ++I)
		{
			int RA = 0, RB = 0, P = 0;
			const EDrill EA = A.Drill(ECommand::Guard, &RA, &P), EB = B.Drill(ECommand::Guard, &RB);
			bSame = bSame && EA == EB && RA == RB;
			bMatch = bMatch && RA == Roll100("Hound_D", 0, DrillSaltBase + I) && P == SuccessPct(80, ECommand::Guard)
				&& (EA == EDrill::Obeyed) == (RA < P);
			Obeyed += EA == EDrill::Obeyed;
		}
		Check(bSame, "same pet, same drills, same outcomes");
		Check(bMatch, "drill roll uses day + drill counter salt");
		Check(Obeyed > 80 && Obeyed < 140, "guard at bond 80 obeys about 45%");
		Check(A.DrillsToday == 200, "drill counter");
		A.EndDay();
		Check(A.DrillsToday == 0 && A.Day == 1, "drill counter resets each day");
	}

	// Status line.
	{
		FPet P = Make("Pup_A", 55, 12);
		P.Care(ECare::Feed); P.Care(ECare::Fetch, 2);
		Check(StatusLine(P) == "Pup_A day=0 bond=55 tier=LOYAL caredays=12 stage=JUVENILE fed=1 watered=0 tonic=0 fetch=2", "status line");
	}

	std::printf("%s kennel pet core: %d/%d\n", GBad == 0 ? "OK" : "FAIL", GTotal - GBad, GTotal);
	return GBad == 0 ? 0 : 1;
}
