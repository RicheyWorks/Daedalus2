// SPDX-License-Identifier: MIT
// G87 Forge Commissions, plain C++17 for the Unreal binding (G98). A port of daedalus-core
// world/forge/ForgeCommissions.java with no Unreal types. Byte parity with Java goes through
// engines/unreal/core-test/forge_commissions_parity.txt (ForgeCommissionsParityTest).
#pragma once
#include "DaedalusForgeGradesCore.h"
#include "DaedalusTemperForgeCore.h"
#include <cstdio>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int CommissionsPerDay = 3, CommissionStartRegard = 50, PatronCount = 5, CommissionMetalCount = 5;

enum class Patron : int { Brannoc = 0, Hesper, Ysolde, Ottar, Mira };
inline const char* PatronName(Patron P)
{
	static const char* const N[] = { "BRANNOC", "HESPER", "YSOLDE", "OTTAR", "MIRA" };
	return N[static_cast<int>(P)];
}
inline const char* PatronTitle(Patron P)
{
	static const char* const T[] = { "Drydock Master Brannoc Slagg", "Quartermaster Hesper Coalhand", "Old Keeper Ysolde Anvilward",
		"Ottar Flintwick, Kennel Isle warden", "Captain Mira Sootvane of Storm Anchorage" };
	return T[static_cast<int>(P)];
}

enum class MinTier : int { Crude = 0, Standard, Fine, Masterwork };
inline const char* MinTierName(MinTier T)
{
	static const char* const N[] = { "CRUDE", "STANDARD", "FINE", "MASTERWORK" };
	return N[static_cast<int>(T)];
}
inline int MinTierTemper(MinTier T) { static const int V[] = { 20, 50, 80, 95 }; return V[static_cast<int>(T)]; }
inline int TierFactorPct(MinTier T) { static const int V[] = { 60, 100, 150, 250 }; return V[static_cast<int>(T)]; }

enum class Verdict : int { Paid = 0, PaidLate, WrongWeapon, WrongMetal, UnderTempered };
inline const char* VerdictName(Verdict V)
{
	static const char* const N[] = { "PAID", "PAID_LATE", "WRONG_WEAPON", "WRONG_METAL", "UNDER_TEMPERED" };
	return N[static_cast<int>(V)];
}

inline Material CommissionMetal(int I)
{
	static const Material M[] = { Material::Copper, Material::Bronze, Material::Iron, Material::Steel, Material::Starmetal };
	return M[I];
}
inline int CommissionMetalPrice(int I) { static const int P[] = { 12, 18, 26, 40, 90 }; return P[I]; }

struct Commission { int Day, Slot; Patron P; Weapon W; Material M; MinTier Min; int DueShifts, PriceCoins; };

/** The order board for forge day Day; the same day always pins the same three commissions. */
inline std::vector<Commission> CommissionBoard(int64_t Day)
{
	SplitRng Rng(Day ^ 0xC0331LL);
	std::vector<Commission> Out;
	for (int Slot = 0; Slot < CommissionsPerDay; ++Slot)
	{
		const Patron P = static_cast<Patron>(Rng.NextInt(PatronCount));
		const Weapon W = static_cast<Weapon>(Rng.NextInt(2));
		const int M = Rng.NextInt(CommissionMetalCount);
		const int Roll = Rng.NextInt(10);
		const MinTier Min = Roll < 4 ? MinTier::Standard : Roll < 8 ? MinTier::Fine : Roll < 9 ? MinTier::Crude : MinTier::Masterwork;
		const int Due = 1 + Rng.NextInt(3);
		const int Price = CommissionMetalPrice(M) * TierFactorPct(Min) / 100 + (Due == 1 ? CommissionMetalPrice(M) / 4 : 0);
		Out.push_back({ static_cast<int>(Day), Slot, P, W, CommissionMetal(M), Min, Due, Price });
	}
	return Out;
}

inline int ClampRegard(int R) { return R < 0 ? 0 : R > 100 ? 100 : R; }

inline const char* CommissionThanks(Patron P, bool Late)
{
	static const char* const OnTime[] = { "Rings true. That one goes on the ark.", "Weighed, logged, paid. Clean work.",
		"Heat and water both. You listened.", "Good steel for the Kennel walls. The dogs thank you.", "It'll hold in a storm. Pleasure, smith." };
	static const char* const LateL[] = { "The tide doesn't wait and neither did I. Half, for half the patience.", "Logged late. The manifest has a long memory.",
		"Late is still tempered. Half, and a lesson.", "The pups went a day unguarded. Here's half.", "We sailed short a blade. Half pay, smith." };
	return (Late ? LateL : OnTime)[static_cast<int>(P)];
}

inline std::string CommissionComplaint(Patron P, Verdict V)
{
	const char* What = V == Verdict::WrongWeapon ? "That's not what I pinned." : V == Verdict::WrongMetal ? "Wrong metal. Read the board." : "Soft. Take it back to the quench.";
	return std::string(PatronTitle(P)) + ": " + What;
}

struct Delivery { Verdict V; int Coins, TipCoins, RegardDelta; std::string Line; bool Paid() const { return V == Verdict::Paid || V == Verdict::PaidLate; } };

/** Judge a delivery. Returns false (Java throws) for negative shifts. */
inline bool Deliver(const Commission& C, const Grade& Piece, int ShiftsTaken, int Regard, Delivery& Out)
{
	if (ShiftsTaken < 0) return false;
	if (Piece.W != C.W) { Out = { Verdict::WrongWeapon, 0, 0, -3, CommissionComplaint(C.P, Verdict::WrongWeapon) }; return true; }
	if (Piece.M != C.M) { Out = { Verdict::WrongMetal, 0, 0, -3, CommissionComplaint(C.P, Verdict::WrongMetal) }; return true; }
	if (Piece.Temper < MinTierTemper(C.Min)) { Out = { Verdict::UnderTempered, 0, 0, -3, CommissionComplaint(C.P, Verdict::UnderTempered) }; return true; }
	const int Over = Piece.Temper - MinTierTemper(C.Min);
	const int Tip = C.PriceCoins * Over * (50 + ClampRegard(Regard)) / 10000;
	if (ShiftsTaken > C.DueShifts) { Out = { Verdict::PaidLate, C.PriceCoins / 2, 0, 1, CommissionThanks(C.P, true) }; return true; }
	Out = { Verdict::Paid, C.PriceCoins, Tip, 5, CommissionThanks(C.P, false) };
	return true;
}

/** Each patron's regard for the smith (mirrors ForgeCommissions.Ledger). */
struct CommissionLedger
{
	int Regard[PatronCount] = { CommissionStartRegard, CommissionStartRegard, CommissionStartRegard, CommissionStartRegard, CommissionStartRegard };
	int Coins = 0, Delivered = 0;

	bool Record(const Commission& C, const Grade& Piece, int ShiftsTaken, Delivery& Out)
	{
		if (!Deliver(C, Piece, ShiftsTaken, Regard[static_cast<int>(C.P)], Out)) return false;
		int& R = Regard[static_cast<int>(C.P)];
		R = ClampRegard(R + Out.RegardDelta);
		Coins += Out.Coins + Out.TipCoins;
		if (Out.Paid()) ++Delivered;
		return true;
	}
};

/** CMS 1 lines (same text as ForgeCommissions.Commission.encode() / Delivery.encode()). */
inline std::string Encode(const Commission& C)
{
	char Buf[160];
	std::snprintf(Buf, sizeof Buf, "CMS 1 day=%d slot=%d %s %s %s min=%s due=%d price=%d", C.Day, C.Slot, PatronName(C.P), WeaponName(C.W),
		MaterialName(C.M), MinTierName(C.Min), C.DueShifts, C.PriceCoins);
	return Buf;
}
inline std::string Encode(const Delivery& D)
{
	char Buf[96];
	std::snprintf(Buf, sizeof Buf, "CMD 1 %s coins=%d tip=%d regard%+d | ", VerdictName(D.V), D.Coins, D.TipCoins, D.RegardDelta);
	return Buf + D.Line;
}

}} // namespace daedalus::forge
