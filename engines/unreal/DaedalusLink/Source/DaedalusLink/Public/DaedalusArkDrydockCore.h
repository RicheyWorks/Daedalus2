// SPDX-License-Identifier: MIT
// G24 Ark Drydock (hephaestus), plain C++17, header-only, no Unreal types.
// Must agree byte for byte with com.daedalus.world.forge.ArkDrydock (ark_drydock_parity.txt, checked by
// ArkDrydockParityTest.java). Integer math only; voyage seeding uses the SplittableRandom port in
// DaedalusTemperForgeCore.h.
#pragma once
#include "DaedalusTemperForgeCore.h"
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int ArkRivetsPerSeam = 4;
constexpr int ArkMissingRivetCost = 10;
constexpr int ArkMinIntegrity = 60;
constexpr int ArkCrewDl = 20;

enum class ArkClass : int { Skiff = 0, Barge, Longark };
constexpr int ArkClassCount = 3;
struct ArkClassInfo { const char* Name; int Plates, Crew, Berths, HoldDl; };
inline ArkClassInfo ArkInfo(ArkClass C)
{
	static const ArkClassInfo I[ArkClassCount] = {
		{ "SKIFF", 6, 2, 12, 2000 }, { "BARGE", 10, 4, 24, 6000 }, { "LONGARK", 14, 6, 40, 12000 } };
	return I[static_cast<int>(C)];
}

enum class Life : int { Emberhen = 0, Ashgoat, Forgeox, Lavaboar, Cinderwool, VentBees, Pet, SeedCrate };
constexpr int LifeCount = 8;
struct LifeInfo { const char* Id; int DlPerDay; bool Pairs; };
inline LifeInfo LifeOf(Life L)
{
	static const LifeInfo I[LifeCount] = {
		{ "emberhen", 5, true }, { "ashgoat", 80, true }, { "forgeox", 120, true }, { "lavaboar", 60, true },
		{ "cinderwool", 60, true }, { "vent_bees", 10, false }, { "pet", 10, false }, { "seed_crate", 0, false } };
	return I[static_cast<int>(L)];
}

enum class ArkReason : int { HullIncomplete = 0, UnstampedPlate, Brittle, Soft, WeakSeam, OverCapacity, Unpaired, ThirstyHold, OverHold };
constexpr int ArkReasonCount = 9;
inline const char* ArkReasonName(ArkReason R)
{
	static const char* N[ArkReasonCount] = { "HULL_INCOMPLETE", "UNSTAMPED_PLATE", "BRITTLE", "SOFT", "WEAK_SEAM",
		"OVER_CAPACITY", "UNPAIRED", "THIRSTY_HOLD", "OVER_HOLD" };
	return N[static_cast<int>(R)];
}

// Drydock Master Brannoc Slagg's line for a launch blocker (q_ark_launch).
inline const char* ArkLine(ArkReason R)
{
	static const char* L[ArkReasonCount] = {
		"A ring with a gap is a funnel, not a hull. Every plate, every seam.",
		"No stamp, no trust. Take that plate back to the anvil and earn your mark.",
		"All fire, no water. She'd shatter on the first cold gust. Heat alone breaks.",
		"All spring, no fire. She'd sag like wet bread in the void. Water alone softens.",
		"One weak seam and the void finds it. Better plates there, or more rivets.",
		"Hesper says the hold is bursting. Leave some for the next ark.",
		"Two by two, or the herd ends where it lands. Find that one a mate.",
		"Count the days, count the mouths. You're short of water for that run.",
		"More water than tank. The rest will be ballast on the slipway floor." };
	return L[static_cast<int>(R)];
}

inline const char* ArkQuestStepFor(ArkReason R)
{
	switch (R)
	{
	case ArkReason::HullIncomplete: case ArkReason::UnstampedPlate: case ArkReason::Brittle: case ArkReason::Soft: return "forge_plates";
	case ArkReason::WeakSeam: return "rivet_seams";
	case ArkReason::OverCapacity: case ArkReason::Unpaired: return "load_life";
	default: return "water_hold";
	}
}

struct ArkPlate { int Temper; Quench Q; bool Stamped; };

// A plate forged at the anvil; a cracked blank never bears a stamp.
inline ArkPlate PlateOf(const TemperResult& R) { return { R.Temper, R.Q, !R.Cracked && R.Temper >= TemperArkPlate }; }

struct Voyage { const char* Shard; int Days; };
constexpr int ShardCount = 6;
inline const char* ShardName(int I)
{
	static const char* S[ShardCount] = { "Kennel Isle", "Glass Reef", "Sky Orchard", "Storm Anchorage", "Cinder Shoal", "Whistle Atoll" };
	return S[I];
}
inline Voyage MakeVoyage(int64_t Seed)
{
	SplitRng Rng(Seed ^ 0xA4CLL);
	const int S = Rng.NextInt(ShardCount);
	return { ShardName(S), 3 + Rng.NextInt(7) };
}

struct Ark { ArkClass C; std::vector<ArkPlate> Plates; std::vector<int> Rivets; int Manifest[LifeCount]; int WaterDl; };

inline int SeamStrength(const Ark& A, int I)
{
	const int N = static_cast<int>(A.Plates.size());
	const ArkPlate& P = A.Plates[I];
	const ArkPlate& Q = A.Plates[(I + 1) % N];
	const int R = I < static_cast<int>(A.Rivets.size()) ? A.Rivets[I] : 0;
	const int Missing = ArkRivetsPerSeam - R > 0 ? ArkRivetsPerSeam - R : 0;
	const int S = (P.Temper + Q.Temper) / 2 - ArkMissingRivetCost * Missing;
	return S > 0 ? S : 0;
}

inline int WaterNeedDl(const Ark& A, const Voyage& V)
{
	int64_t PerDay = static_cast<int64_t>(ArkInfo(A.C).Crew) * ArkCrewDl;
	for (int L = 0; L < LifeCount; ++L) PerDay += static_cast<int64_t>(LifeOf(static_cast<Life>(L)).DlPerDay) * A.Manifest[L];
	const int64_t Need = PerDay * V.Days;
	return Need > INT32_MAX ? INT32_MAX : static_cast<int>(Need);
}

struct ArkInspection { bool Ready; std::vector<ArkReason> Reasons; int Integrity, WaterNeedDl, BerthsUsed; std::string Line; };

// Pure inspection. False when a manifest count is negative (Java throws).
inline bool Inspect(const Ark& A, const Voyage& V, ArkInspection& Out)
{
	bool Why[ArkReasonCount] = {};
	const ArkClassInfo C = ArkInfo(A.C);
	const int N = static_cast<int>(A.Plates.size());
	if (N != C.Plates || static_cast<int>(A.Rivets.size()) != N) Why[static_cast<int>(ArkReason::HullIncomplete)] = true;
	bool Heat = false, Water = false;
	for (const ArkPlate& P : A.Plates)
	{
		if (!P.Stamped) Why[static_cast<int>(ArkReason::UnstampedPlate)] = true;
		Heat |= P.Q != Quench::Spring;
		Water |= P.Q != Quench::Magma;
	}
	if (N > 0 && !Water) Why[static_cast<int>(ArkReason::Brittle)] = true;
	if (N > 0 && !Heat) Why[static_cast<int>(ArkReason::Soft)] = true;
	int Integrity = N == 0 ? 0 : INT32_MAX;
	for (int i = 0; i < N; ++i) { const int S = SeamStrength(A, i); if (S < Integrity) Integrity = S; }
	if (Integrity < ArkMinIntegrity) Why[static_cast<int>(ArkReason::WeakSeam)] = true;
	int Berths = 0;
	for (int L = 0; L < LifeCount; ++L)
	{
		if (A.Manifest[L] < 0) return false;
		Berths += A.Manifest[L];
		if (LifeOf(static_cast<Life>(L)).Pairs && A.Manifest[L] % 2 != 0) Why[static_cast<int>(ArkReason::Unpaired)] = true;
	}
	if (Berths > C.Berths) Why[static_cast<int>(ArkReason::OverCapacity)] = true;
	const int Need = WaterNeedDl(A, V);
	if (A.WaterDl < Need) Why[static_cast<int>(ArkReason::ThirstyHold)] = true;
	if (A.WaterDl > C.HoldDl) Why[static_cast<int>(ArkReason::OverHold)] = true;
	Out.Reasons.clear();
	for (int R = 0; R < ArkReasonCount; ++R) if (Why[R]) Out.Reasons.push_back(static_cast<ArkReason>(R));
	Out.Ready = Out.Reasons.empty();
	Out.Integrity = Integrity; Out.WaterNeedDl = Need; Out.BerthsUsed = Berths;
	if (Out.Ready)
		Out.Line = std::string("Tempered both ways. Knock the chocks out. ") + std::to_string(V.Days) + " days to " + V.Shard + ", and the forge goes with you.";
	else
		Out.Line = ArkLine(Out.Reasons[0]);
	return true;
}

inline const char* ArkQuestStep(const ArkInspection& I) { return I.Ready ? "launch" : ArkQuestStepFor(I.Reasons[0]); }

// ADK 1 single-line encoding, stable for parity tests and the link.
inline std::string Encode(const ArkInspection& I)
{
	std::string R;
	for (size_t k = 0; k < I.Reasons.size(); ++k) { if (k) R += ','; R += ArkReasonName(I.Reasons[k]); }
	if (R.empty()) R = "-";
	return "ADK 1 ready=" + std::to_string(I.Ready ? 1 : 0) + " integrity=" + std::to_string(I.Integrity) + " water="
		+ std::to_string(I.WaterNeedDl) + " berths=" + std::to_string(I.BerthsUsed) + " reasons=" + R + " step="
		+ ArkQuestStep(I) + " line=" + I.Line;
}

}} // namespace daedalus::forge
