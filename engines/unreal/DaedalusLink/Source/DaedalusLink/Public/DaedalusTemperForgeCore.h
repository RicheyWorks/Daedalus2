// SPDX-License-Identifier: MIT
// G19 Anvil and Quench (hephaestus), plain C++17, header-only, no Unreal types.
// Must agree byte for byte with com.daedalus.world.forge.TemperForge (temper_forge_parity.txt, checked by
// TemperForgeParityTest.java). Integer math only; blank seeding ports java.util.SplittableRandom exactly.
#pragma once
#include "DaedalusForgeGradesCore.h"
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int TemperAmbientC = 20;
constexpr int TemperFirstBeatMs = 1000;
constexpr int TemperCoolCPerS = 25;
constexpr int TemperCrackedCap = 30;
constexpr int TemperArkPlate = 60;
constexpr int TemperOverworkPm = 100;

enum class Quench : int { Magma = 0, Spring, Dual };
enum class TemperStrike : int { Perfect = 0, Good, Miss, Crack, Wasted };

inline const char* QuenchName(Quench Q) { return Q == Quench::Magma ? "MAGMA" : Q == Quench::Spring ? "SPRING" : "DUAL"; }
inline char StrikeLetter(TemperStrike S) { static const char L[] = "PGMCW"; return L[static_cast<int>(S)]; }

// java.util.SplittableRandom, the parts TemperForge uses (nextInt(bound) as in JDK 17+ RandomSupport).
struct SplitRng
{
	uint64_t Seed;
	explicit SplitRng(int64_t S) : Seed(static_cast<uint64_t>(S)) {}
	static int32_t Mix32(uint64_t Z)
	{
		Z = (Z ^ (Z >> 33)) * 0x62a9d9ed799705f5ULL;
		return static_cast<int32_t>(static_cast<uint32_t>(((Z ^ (Z >> 28)) * 0xcb24d0a5c88c35b3ULL) >> 32));
	}
	int32_t NextInt() { Seed += 0x9e3779b97f4a7c15ULL; return Mix32(Seed); }
	int32_t NextInt(int32_t Bound)
	{
		int32_t R = NextInt();
		const int32_t M = Bound - 1;
		if ((Bound & M) == 0) return R & M;
		for (int32_t U = static_cast<int32_t>(static_cast<uint32_t>(R) >> 1);
			static_cast<int32_t>(static_cast<uint32_t>(U) + static_cast<uint32_t>(M) - static_cast<uint32_t>(R = U % Bound)) < 0;
			U = static_cast<int32_t>(static_cast<uint32_t>(NextInt()) >> 1)) {}
		return R;
	}
};

struct TemperMetal { Material M; int TargetC, BandC, HeatRateCPerS, PerfectMs, GoodMs; };

inline bool Forgeable(Material M)
{
	return M == Material::Copper || M == Material::Bronze || M == Material::Iron || M == Material::Steel || M == Material::Starmetal;
}

// False for wood, stone and obsidian (Java throws IllegalArgumentException).
inline bool MetalOf(Material M, TemperMetal& Out)
{
	switch (M)
	{
	case Material::Copper: Out = { M, 700, 45, 140, 80, 170 }; return true;
	case Material::Bronze: Out = { M, 760, 40, 130, 75, 160 }; return true;
	case Material::Iron: Out = { M, 850, 40, 120, 70, 150 }; return true;
	case Material::Steel: Out = { M, 900, 35, 110, 60, 135 }; return true;
	case Material::Starmetal: Out = { M, 1100, 25, 100, 45, 110 }; return true;
	default: return false;
	}
}

struct TemperBlank
{
	TemperMetal Mt; int Strikes; int BeatMs;
	int HeatAt(int Ms) const
	{
		const int Raw = TemperAmbientC + static_cast<int>(static_cast<int64_t>(Mt.HeatRateCPerS) * Ms / 1000);
		return Raw < Mt.TargetC + 300 ? Raw : Mt.TargetC + 300;
	}
	int BeatOffset(int I) const { return TemperFirstBeatMs + I * BeatMs; }
	int QuenchTargetC() const { return Mt.TargetC - static_cast<int>(static_cast<int64_t>(TemperCoolCPerS) * BeatOffset(Strikes) / 1000); }
	int WorkableC() const { return Mt.TargetC - 250; }
	int IdealPullMs() const
	{
		const int64_t N = static_cast<int64_t>(Mt.TargetC - TemperAmbientC) * 1000;
		return static_cast<int>((N + Mt.HeatRateCPerS - 1) / Mt.HeatRateCPerS);
	}
};

inline bool MakeBlank(Material M, int64_t Seed, TemperBlank& Out)
{
	TemperMetal Mt;
	if (!MetalOf(M, Mt)) return false;
	SplitRng Rng(Seed ^ 0xF0E6ELL);
	const int Strikes = 5 + Rng.NextInt(4);
	const int Beat = 520 + 20 * Rng.NextInt(14);
	Out = { Mt, Strikes, Beat };
	return true;
}

struct TemperRun { int PullMs; std::vector<int> StrikesMs; int QuenchMs; Quench Q; };

struct TemperResult
{
	int HeatPm, HammerPm, QuenchPm; std::vector<TemperStrike> Strikes; bool Cracked; int Temper; const char* TierName; Quench Q; bool ArkPlate;
};

inline int HeatScore(const TemperBlank& B, int HeatC)
{
	const int Diff = HeatC - B.Mt.TargetC;
	const int Off = (Diff < 0 ? -Diff : Diff) - B.Mt.BandC;
	const int S = 1000 - 10 * (Off > 0 ? Off : 0);
	return S > 0 ? S : 0;
}

inline int Cooled(int PulledC, int PullMs, int Ms) { return PulledC - static_cast<int>(static_cast<int64_t>(TemperCoolCPerS) * (Ms - PullMs) / 1000); }

// Judge a run. False when the run is malformed (quench before pull, strikes out of order); Java throws.
inline bool Judge(const TemperBlank& B, const TemperRun& R, TemperResult& Out)
{
	if (R.PullMs < 0 || R.QuenchMs < R.PullMs) return false;
	const int PulledC = B.HeatAt(R.PullMs);
	const int Heat = HeatScore(B, PulledC);
	std::vector<TemperStrike> Strikes;
	bool Cracked = false;
	int64_t Hammer = 0;
	int Last = R.PullMs;
	for (size_t i = 0; i < R.StrikesMs.size(); ++i)
	{
		const int At = R.StrikesMs[i];
		if (At < Last) return false;
		Last = At;
		TemperStrike S;
		if (At > R.QuenchMs) S = TemperStrike::Wasted;
		else if (static_cast<int>(i) >= B.Strikes) { S = TemperStrike::Miss; Hammer -= TemperOverworkPm; }
		else if (Cooled(PulledC, R.PullMs, At) < B.WorkableC()) { S = TemperStrike::Crack; Cracked = true; }
		else
		{
			const int Dt0 = At - (R.PullMs + B.BeatOffset(static_cast<int>(i)));
			const int Dt = Dt0 < 0 ? -Dt0 : Dt0;
			S = Dt <= B.Mt.PerfectMs ? TemperStrike::Perfect : Dt <= B.Mt.GoodMs ? TemperStrike::Good : TemperStrike::Miss;
			Hammer += S == TemperStrike::Perfect ? 1000 : S == TemperStrike::Good ? 600 : 0;
		}
		Strikes.push_back(S);
	}
	int64_t H = Hammer / B.Strikes;
	if (H > 1000) H = 1000;
	if (H < 0) H = 0;
	const int HammerPm = static_cast<int>(H);
	const int QuenchedC = Cooled(PulledC, R.PullMs, R.QuenchMs);
	const int QDiff = QuenchedC - B.QuenchTargetC();
	const int QBand = R.Q == Quench::Dual ? 15 : 30;
	const int QOff = (QDiff < 0 ? -QDiff : QDiff) - QBand;
	const int Q0 = 1000 - 8 * (QOff > 0 ? QOff : 0);
	const int QuenchPm = Q0 > 0 ? Q0 : 0;
	const int64_t Total = 300LL * Heat + 450LL * HammerPm + 250LL * QuenchPm;
	int Temper = static_cast<int>(Total / 10000);
	if (Cracked && Temper > TemperCrackedCap) Temper = TemperCrackedCap;
	const bool Ark = R.Q == Quench::Dual && !Cracked && Temper >= TemperArkPlate;
	Out = { Heat, HammerPm, QuenchPm, Strikes, Cracked, Temper, Tier(Temper), R.Q, Ark };
	return true;
}

inline TemperRun IdealRun(const TemperBlank& B, Quench Q)
{
	TemperRun R;
	R.PullMs = B.IdealPullMs();
	for (int i = 0; i < B.Strikes; ++i) R.StrikesMs.push_back(R.PullMs + B.BeatOffset(i));
	const int PulledC = B.HeatAt(R.PullMs);
	const int ByHeat = (PulledC - B.QuenchTargetC()) * 1000 / TemperCoolCPerS;
	const int LastBeat = B.BeatOffset(B.Strikes - 1);
	R.QuenchMs = R.PullMs + (LastBeat > ByHeat ? LastBeat : ByHeat);
	R.Q = Q;
	return R;
}

// TFG 1 single-line encoding, stable for parity tests and the link.
inline std::string Encode(const TemperResult& R)
{
	std::string S;
	for (TemperStrike K : R.Strikes) S += StrikeLetter(K);
	if (S.empty()) S = "-";
	char Buf[160];
	std::snprintf(Buf, sizeof(Buf), "TFG 1 %s heat=%d hammer=%d quench=%d t=%d tier=%s cracked=%d ark=%d strikes=%s",
		QuenchName(R.Q), R.HeatPm, R.HammerPm, R.QuenchPm, R.Temper, R.TierName, R.Cracked ? 1 : 0, R.ArkPlate ? 1 : 0, S.c_str());
	return std::string(Buf);
}

}} // namespace daedalus::forge
