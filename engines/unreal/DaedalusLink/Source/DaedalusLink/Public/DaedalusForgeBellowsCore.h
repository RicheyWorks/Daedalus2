// SPDX-License-Identifier: MIT
// G57 Bellows Shift, plain C++17 for the Unreal binding (G69). A port of daedalus-core world/forge/ForgeBellows.java
// with no Unreal types. Byte parity with Java goes through engines/unreal/core-test/forge_bellows_parity.txt
// (ForgeBellowsParityTest).
#pragma once
#include "DaedalusTemperForgeCore.h"
#include <cstdio>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int BellowsTicks = 120, BellowsTickMs = 250, BellowsStartC = 600, BellowsPumpC = 30, BellowsGustC = 30;
constexpr int BellowsCoal = 3, BellowsCinderDropC = 120, BellowsOxBonusPct = 15, BellowsMaxOxen = 2, BellowsCinderBands = 3;

enum class BellowsTier : int { Steady = 0, Warm, Fitful, Cold };
inline const char* BellowsTierName(BellowsTier T)
{
	static const char* const N[] = { "STEADY", "WARM", "FITFUL", "COLD" };
	return N[static_cast<int>(T)];
}

/** One shift at the bellows: the metal, the working oxen and the seeded draught. */
struct BellowsPlan { TemperMetal Metal; int Oxen; std::vector<bool> Gusts; };

inline int BellowsPumpOf(const BellowsPlan& P) { return BellowsPumpC * (100 + BellowsOxBonusPct * P.Oxen) / 100; }

/** Fails (false) for an unforgeable material or an ox count outside 0..2. */
inline bool MakeBellowsPlan(Material M, int Oxen, int64_t Seed, BellowsPlan& Out)
{
	if (Oxen < 0 || Oxen > BellowsMaxOxen || !MetalOf(M, Out.Metal)) return false;
	Out.Oxen = Oxen;
	SplitRng Rng(Seed ^ 0xBE11LL);
	Out.Gusts.assign(BellowsTicks, false);
	for (int T = 0; T < BellowsTicks; ++T) Out.Gusts[T] = Rng.NextInt(12) == 0;
	return true;
}

/** One tick of the firebed: pump, draught, then the bed's own loss (never below 20). */
inline int BellowsStep(const BellowsPlan& P, int T, int Heat, bool Pump)
{
	const int H = Heat + (Pump ? BellowsPumpOf(P) : 0) - (P.Gusts[T] ? BellowsGustC : 0);
	const int N = H - (H - 20) / 40;
	return N < 20 ? 20 : N;
}

inline const char* BellowsLine(BellowsTier T, bool Doused, int Oxen)
{
	if (Doused) return "You choked her on cinders. Rake the bed, fetch coal, and pump like you mean it, not like you're angry.";
	switch (T)
	{
	case BellowsTier::Steady: return "Steady as the caldera. Pull the blank, it's ready.";
	case BellowsTier::Warm: return "Warm enough to work. Keep the rhythm and the blank will forgive you.";
	case BellowsTier::Fitful: return Oxen == 0 ? "Forgeox on the bellows buys you time. Don't waste it." : "Fits and starts. Watch the colour, not your arm.";
	default: return Oxen == 0 ? "Forgeox on the bellows buys you time. Don't waste it." : "Cold bed, cold iron. Again.";
	}
}

struct BellowsResult { int InBandTicks, InBandPm, Cinders; bool Doused; int PeakC, FinalC; BellowsTier Tier; bool ReadyToPull; int ForgeSpeedPm; const char* Line; };

inline int BellowsAbs(int V) { return V < 0 ? -V : V; }

/** Play Pumps (one flag per tick; missing ticks are no pump) against the plan. */
inline BellowsResult RunBellows(const BellowsPlan& P, const std::vector<bool>& Pumps)
{
	const int Target = P.Metal.TargetC, Band = P.Metal.BandC;
	int Heat = BellowsStartC, Coal = BellowsCoal, In = 0, Cinders = 0, Peak = Heat;
	bool Out = false;
	for (int T = 0; T < BellowsTicks; ++T)
	{
		const bool Pump = !Out && T < static_cast<int>(Pumps.size()) && Pumps[T];
		Heat = BellowsStep(P, T, Heat, Pump);
		if (Out) Heat = Heat - 40 < 20 ? 20 : Heat - 40;
		else if (Heat > Target + BellowsCinderBands * Band) { ++Cinders; --Coal; Heat -= BellowsCinderDropC; Out = Coal == 0; }
		if (Heat > Peak) Peak = Heat;
		if (BellowsAbs(Heat - Target) <= Band) ++In;
	}
	const int Pm = In * 1000 / BellowsTicks;
	const BellowsTier Tier = Pm >= 850 ? BellowsTier::Steady : Pm >= 600 ? BellowsTier::Warm : Pm >= 300 ? BellowsTier::Fitful : BellowsTier::Cold;
	return { In, Pm, Cinders, Out, Peak, Heat, Tier, !Out && BellowsAbs(Heat - Target) <= Band, 1000 + 10 * BellowsOxBonusPct * P.Oxen, BellowsLine(Tier, Out, P.Oxen) };
}

/** The bellows master's shift: pump only when the bed would otherwise fall below target. */
inline std::vector<bool> BellowsSteadyHand(const BellowsPlan& P)
{
	std::vector<bool> Pumps(BellowsTicks, false);
	int Heat = BellowsStartC;
	for (int T = 0; T < BellowsTicks; ++T)
	{
		Pumps[T] = BellowsStep(P, T, Heat, false) < P.Metal.TargetC;
		Heat = BellowsStep(P, T, Heat, Pumps[T]);
	}
	return Pumps;
}

/** One-line BLW 1 summary (same text as ForgeBellows.Result.encode()). */
inline std::string Encode(const BellowsResult& R)
{
	char Buf[320];
	std::snprintf(Buf, sizeof Buf, "BLW 1 in=%d pm=%d cinders=%d doused=%d peak=%d final=%d %s ready=%d speed=%d | %s", R.InBandTicks, R.InBandPm,
		R.Cinders, R.Doused ? 1 : 0, R.PeakC, R.FinalC, BellowsTierName(R.Tier), R.ReadyToPull ? 1 : 0, R.ForgeSpeedPm, R.Line);
	return Buf;
}

}} // namespace daedalus::forge
