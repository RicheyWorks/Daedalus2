// SPDX-License-Identifier: MIT
// G165: plain C++17 port of G152 Void Crossing (daedalus-core world/forge/VoidCrossing.java), header-only and Unreal-ready.
// Sail a launched G24 ark to its shard day by day: seeded storms and cold snaps fixed at departure, spare-rivet
// patches, water at the drydock rates, the thirstiest head lost on a dry day, a breach below 30. Encode() gives the
// same VXC 1 line as VoidCrossing.Crossing.encode(); VoidCrossingParityTest.java checks that line for line.
#pragma once

#include "DaedalusArkDrydockCore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int VoidBreach = 30;
constexpr int VoidMaxSpares = 12;

enum class VoidOutcome : int { Sailing = 0, Arrived, ArrivedWithLosses, Breached, NotLaunched };
inline const char* VoidOutcomeName(VoidOutcome O)
{
	static const char* N[] = { "SAILING", "ARRIVED", "ARRIVED_WITH_LOSSES", "BREACHED", "NOT_LAUNCHED" };
	return N[static_cast<int>(O)];
}

struct VoidDay { bool Cold; int StormSeam; int Damage; };

inline std::string VoidLine(VoidOutcome O, const Voyage& V)
{
	switch (O)
	{
	case VoidOutcome::Sailing: return std::string("Holding course for ") + V.Shard + ". Keep a hand on the rivet crate.";
	case VoidOutcome::Arrived: return std::string("Moored at ") + V.Shard + ", every head aboard. She remembers the forge.";
	case VoidOutcome::ArrivedWithLosses: return std::string("We made ") + V.Shard + ", but the hold ran dry. Load more water next time.";
	case VoidOutcome::Breached: return "Seam's open to the void. We're limping home. Temper both, smith.";
	default: return "Brannoc never cleared her off the slip. Fix the hull first.";
	}
}

// One ark's crossing, held by the host. Construct, check Valid() (false where Java throws), then Sail() once a day.
struct VoidCrossing
{
	Ark A;
	Voyage V;
	bool Tonic;
	std::vector<VoidDay> Weather;
	std::vector<int> Launch, Seam;
	int Aboard[LifeCount];
	int Lost[LifeCount];
	int Spares, Water, Day = 0, Patches = 0, IdleDays = 0;
	VoidOutcome Outcome = VoidOutcome::NotLaunched;
	bool Ok;

	VoidCrossing(const Ark& InArk, const Voyage& InV, bool InTonic, int InSpares, int64_t Seed)
		: A(InArk), V(InV), Tonic(InTonic), Spares(InSpares), Water(InArk.WaterDl), Ok(InSpares >= 0 && InSpares <= VoidMaxSpares)
	{
		const int N = static_cast<int>(A.Plates.size());
		for (int i = 0; i < N; ++i) Launch.push_back(SeamStrength(A, i));
		Seam = Launch;
		for (int L = 0; L < LifeCount; ++L) { Aboard[L] = A.Manifest[L]; Lost[L] = 0; }
		SplitRng Rng(Seed ^ 0x701DLL);
		for (int d = 0; d < V.Days; ++d)
		{
			const bool Cold = Rng.NextInt(5) == 0;
			const bool Storm = Rng.NextInt(2) == 0;
			const int S = Rng.NextInt(N > 1 ? N : 1);
			const int Dmg = 15 + Rng.NextInt(26);
			Weather.push_back(Storm && N > 0 ? VoidDay{ Cold, S, Dmg } : VoidDay{ Cold, -1, 0 });
		}
		ArkInspection I;
		Ok = Ok && Inspect(A, V, I);
		Outcome = Ok && I.Ready ? VoidOutcome::Sailing : VoidOutcome::NotLaunched;
	}

	bool Valid() const { return Ok; }
	// Today's weather; null once the crossing is over.
	const VoidDay* Today() const { return Outcome == VoidOutcome::Sailing ? &Weather[Day] : nullptr; }

	int NeedToday(bool Cold) const
	{
		const int Crew = ArkInfo(A.C).Crew * ArkCrewDl;
		int Need = Tonic ? Crew * 3 / 4 : Cold ? Crew * 2 : Crew;
		for (int L = 0; L < LifeCount; ++L) Need += LifeOf(static_cast<Life>(L)).DlPerDay * Aboard[L];
		return Need;
	}

	int MinSeam() const
	{
		if (Seam.empty()) return 0;
		int M = Seam[0];
		for (int S : Seam) M = S < M ? S : M;
		return M;
	}

	int WeakestPatchable() const
	{
		int Best = -1;
		for (int i = 0; i < static_cast<int>(Seam.size()); ++i)
			if (Seam[i] < Launch[i] && (Best < 0 || Seam[i] < Seam[Best])) Best = i;
		return Best;
	}

	int LostHead() const { int N = 0; for (int L = 0; L < LifeCount; ++L) N += Lost[L]; return N; }

	// Sail one day; PatchSeam is the seam to patch, or -1 to hold.
	VoidOutcome Sail(int PatchSeam)
	{
		if (Outcome != VoidOutcome::Sailing) return Outcome;
		const VoidDay W = Weather[Day];
		const bool CanWork = !W.Cold || Tonic;
		if (!CanWork) ++IdleDays;
		else if (PatchSeam >= 0 && PatchSeam < static_cast<int>(Seam.size()) && Spares > 0 && Seam[PatchSeam] < Launch[PatchSeam])
		{
			--Spares; ++Patches;
			const int P = Seam[PatchSeam] + ArkMissingRivetCost;
			Seam[PatchSeam] = P < Launch[PatchSeam] ? P : Launch[PatchSeam];
		}
		if (W.StormSeam >= 0) { const int S = Seam[W.StormSeam] - W.Damage; Seam[W.StormSeam] = S > 0 ? S : 0; }
		const int Need = NeedToday(W.Cold);
		if (Water >= Need) Water -= Need;
		else
		{
			Water = 0;
			int Worst = -1;
			for (int L = 0; L < LifeCount; ++L)
			{
				const int Dl = LifeOf(static_cast<Life>(L)).DlPerDay;
				if (Aboard[L] > 0 && Dl > 0 && (Worst < 0 || Dl > LifeOf(static_cast<Life>(Worst)).DlPerDay)) Worst = L;
			}
			if (Worst >= 0) { --Aboard[Worst]; ++Lost[Worst]; }
		}
		++Day;
		if (MinSeam() < VoidBreach) Outcome = VoidOutcome::Breached;
		else if (Day == V.Days) Outcome = LostHead() == 0 ? VoidOutcome::Arrived : VoidOutcome::ArrivedWithLosses;
		return Outcome;
	}
};

// The reference crew: every working day, patch the weakest seam that has taken damage.
inline VoidCrossing VoidBosun(const Ark& A, const Voyage& V, bool Tonic, int Spares, int64_t Seed)
{
	VoidCrossing C(A, V, Tonic, Spares, Seed);
	while (C.Outcome == VoidOutcome::Sailing) C.Sail(C.WeakestPatchable());
	return C;
}

// VXC 1 single-line encoding, the same text as VoidCrossing.Crossing.encode().
inline std::string Encode(const VoidCrossing& C)
{
	int Storms = 0, Colds = 0;
	for (const VoidDay& W : C.Weather) { Storms += W.StormSeam >= 0 ? 1 : 0; Colds += W.Cold ? 1 : 0; }
	std::string Shard = C.V.Shard;
	for (char& Ch : Shard) if (Ch == ' ') Ch = '_';
	return std::string("VXC 1 ") + VoidOutcomeName(C.Outcome) + " to=" + Shard + " day=" + std::to_string(C.Day) + "/" + std::to_string(C.V.Days)
		+ " storms=" + std::to_string(Storms) + " cold=" + std::to_string(Colds) + " minSeam=" + std::to_string(C.MinSeam()) + " patches="
		+ std::to_string(C.Patches) + " spares=" + std::to_string(C.Spares) + " idle=" + std::to_string(C.IdleDays) + " water="
		+ std::to_string(C.Water) + " lost=" + std::to_string(C.LostHead()) + " | " + VoidLine(C.Outcome, C.V);
}

}} // namespace daedalus::forge
