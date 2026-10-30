// SPDX-License-Identifier: MIT
// G586 Fog Channel Pilot (2hot2trot), plain C++17, header-only, no Unreal types.
// Must agree with com.daedalus.world.pilot.FogChannelPilot line for line (pilot_fog_channel_parity.txt, written by
// FogChannelPilotTest.java and replayed by pilot_fog_channel_core_test.cpp). Scenarios are drawn from
// daedalus::pyrandom::PyRandom (CPython random.Random(str)), the same draws as Java's PyStringRandom.
#pragma once
#include "DaedalusPyRandomCore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace pilot {

constexpr const char* FogChannelQuest = "q_pilot_through_fog";
constexpr int FogEchoes = 3;
constexpr int FogMaxChannels = 4;
constexpr int FogMaxBlasts = 16;    // longest fog a harbour may hold (the pea-soup tier reaches it)
constexpr int FogClassicBlasts = 8; // blast cap of the classic FogSeed draw, so the G586 parity seeds never move
constexpr int FogMissed = FogEchoes; // a blast whose echo never came back: costs nothing anywhere
constexpr int FogInvalid = -1;
constexpr int FogParSlack = 2; // a reading within this many points of par still earns two stars
constexpr const char* FogEchoNames[FogEchoes + 1] = { "dull", "ring", "clang", "silence" };

// Difficulty tiers (Java FogChannelPilot.Tier): blast range, echo cost spread, percent of echoes missed.
// Greedy loses on CALM 146, FOG 233, PEA_SOUP 264 of seeds 1..300.
enum class EFogTier : int { Calm, Fog, PeaSoup };
struct FogTierSpec { int MinBlasts, MaxBlasts, EchoSpread, MissPercent; const char* SeedPrefix; };
constexpr FogTierSpec FogTiers[3] = { { 2, 5, 14, 0, "calm-" }, { 4, 10, 7, 10, "fog-" }, { 8, 16, 4, 30, "pea-soup-" } };
constexpr const FogTierSpec& FogTierOf(EFogTier T) noexcept { return FogTiers[static_cast<int>(T)]; }

// Opening, drift (lane i to lane j) and echo (lane, echo kind) costs, plus the echo heard on every blast.
struct FogHarbour
{
	std::vector<int> Open;
	std::vector<std::vector<int>> Drift, Echo;
	std::vector<int> Heard;
	int Channels() const { return static_cast<int>(Open.size()); }
	int Blasts() const { return static_cast<int>(Heard.size()); }
};
// A reading of the fog: total cost and the lane named for every blast.
struct FogTrack { int Cost = 0; std::vector<int> Lanes; };

// Seeded harbour, same draw order as Java FogChannelPilot.harbour: channels, blasts, opening costs, drift rows
// (staying put is cheap, changing lanes dear), echo rows, then the echoes heard.
inline FogHarbour FogSeed(const std::string& Seed)
{
	pyrandom::PyRandom Rng(Seed);
	auto Below = [&Rng](int N) { return static_cast<int>(Rng.Below(static_cast<std::uint32_t>(N))); };
	const int S = 2 + Below(3);
	const int T = 1 + Below(FogClassicBlasts);
	FogHarbour H;
	for (int i = 0; i < S; ++i) H.Open.push_back(Below(6));
	H.Drift.assign(S, std::vector<int>(S, 0));
	for (int i = 0; i < S; ++i)
		for (int j = 0; j < S; ++j) H.Drift[i][j] = i == j ? Below(3) : 2 + Below(8);
	H.Echo.assign(S, std::vector<int>(FogEchoes, 0));
	for (auto& Row : H.Echo)
		for (int& E : Row) E = Below(7);
	for (int k = 0; k < T; ++k) H.Heard.push_back(Below(FogEchoes));
	return H;
}

// Tiered harbour, same draw order as Java FogChannelPilot.harbour(seed, tier): channels, blasts in the tier range,
// opening and drift costs as FogSeed, echo costs below the tier spread, then per blast a miss draw below 100 and,
// if heard, the echo kind.
inline FogHarbour FogSeedTier(const std::string& Seed, EFogTier Tier)
{
	const FogTierSpec& Spec = FogTierOf(Tier);
	pyrandom::PyRandom Rng(Seed);
	auto Below = [&Rng](int N) { return static_cast<int>(Rng.Below(static_cast<std::uint32_t>(N))); };
	const int S = 2 + Below(3);
	const int T = Spec.MinBlasts + Below(Spec.MaxBlasts - Spec.MinBlasts + 1);
	FogHarbour H;
	for (int i = 0; i < S; ++i) H.Open.push_back(Below(6));
	H.Drift.assign(S, std::vector<int>(S, 0));
	for (int i = 0; i < S; ++i)
		for (int j = 0; j < S; ++j) H.Drift[i][j] = i == j ? Below(3) : 2 + Below(8);
	H.Echo.assign(S, std::vector<int>(FogEchoes, 0));
	for (auto& Row : H.Echo)
		for (int& E : Row) E = Below(Spec.EchoSpread);
	for (int k = 0; k < T; ++k) H.Heard.push_back(Below(100) < Spec.MissPercent ? FogMissed : Below(FogEchoes));
	return H;
}

// Echo cost of blast K from lane L; a missed echo costs nothing anywhere.
inline int FogEchoCost(const FogHarbour& H, int L, int K) noexcept
{
	const int E = H.Heard[K];
	return E == FogMissed ? 0 : H.Echo[L][E];
}

// Same checks as the Java Harbour constructor: 1..FogMaxChannels lanes, square drift, FogEchoes echo costs per lane,
// no negative cost, at most FogMaxBlasts blasts and only known echoes. Every other function refuses a bad harbour.
inline bool FogValid(const FogHarbour& H) noexcept
{
	const int S = H.Channels();
	if (S < 1 || S > FogMaxChannels || static_cast<int>(H.Drift.size()) != S || static_cast<int>(H.Echo.size()) != S
		|| H.Blasts() > FogMaxBlasts)
		return false;
	for (int i = 0; i < S; ++i)
	{
		if (static_cast<int>(H.Drift[i].size()) != S || static_cast<int>(H.Echo[i].size()) != FogEchoes || H.Open[i] < 0) return false;
		for (int D : H.Drift[i]) if (D < 0) return false;
		for (int E : H.Echo[i]) if (E < 0) return false;
	}
	for (int E : H.Heard) if (E < 0 || E > FogMissed) return false;
	return true;
}

// Total cost of a lane sequence, or FogInvalid when it is the wrong length or names a missing lane.
inline int FogCost(const FogHarbour& H, const std::vector<int>& Lanes)
{
	if (!FogValid(H) || static_cast<int>(Lanes.size()) != H.Blasts()) return FogInvalid;
	int Total = 0;
	for (int k = 0; k < H.Blasts(); ++k)
	{
		const int L = Lanes[k];
		if (L < 0 || L >= H.Channels()) return FogInvalid;
		Total += (k == 0 ? H.Open[L] : H.Drift[Lanes[k - 1]][L]) + FogEchoCost(H, L, k);
	}
	return Total;
}

// Cheapest lane sequence for all blasts at once (Viterbi, integer min-sum); ties go to the lower lane.
inline FogTrack FogBest(const FogHarbour& H)
{
	if (!FogValid(H)) return { FogInvalid, {} };
	const int S = H.Channels(), T = H.Blasts();
	if (T == 0) return {};
	std::vector<std::vector<int>> Cost(T, std::vector<int>(S, 0)), From(T, std::vector<int>(S, 0));
	for (int i = 0; i < S; ++i) Cost[0][i] = H.Open[i] + FogEchoCost(H, i, 0);
	for (int k = 1; k < T; ++k)
		for (int j = 0; j < S; ++j)
		{
			int Prev = 0;
			for (int i = 1; i < S; ++i)
				if (Cost[k - 1][i] + H.Drift[i][j] < Cost[k - 1][Prev] + H.Drift[Prev][j]) Prev = i;
			Cost[k][j] = Cost[k - 1][Prev] + H.Drift[Prev][j] + FogEchoCost(H, j, k);
			From[k][j] = Prev;
		}
	int Last = 0;
	for (int i = 1; i < S; ++i)
		if (Cost[T - 1][i] < Cost[T - 1][Last]) Last = i;
	FogTrack Track{ Cost[T - 1][Last], std::vector<int>(T, Last) };
	for (int k = T - 1; k > 0; --k) Track.Lanes[k - 1] = From[k][Track.Lanes[k]];
	return Track;
}

// The dockhand's habit: each blast on its own, the lane its echo surprises least (lower lane on ties); on a missed
// echo the dockhand holds the last lane (lane 0 before any echo).
inline FogTrack FogLoudestEcho(const FogHarbour& H)
{
	if (!FogValid(H)) return { FogInvalid, {} };
	FogTrack Track;
	for (int k = 0; k < H.Blasts(); ++k)
	{
		if (H.Heard[k] == FogMissed)
		{
			Track.Lanes.push_back(k == 0 ? 0 : Track.Lanes.back());
			continue;
		}
		int Pick = 0;
		for (int i = 1; i < H.Channels(); ++i)
			if (H.Echo[i][H.Heard[k]] < H.Echo[Pick][H.Heard[k]]) Pick = i;
		Track.Lanes.push_back(Pick);
	}
	Track.Cost = FogCost(H, Track.Lanes);
	return Track;
}

// Quest q_pilot_through_fog: the pilot's reading is a real track and no track explains the fog better.
inline bool FogQuestDone(const FogHarbour& H, const std::vector<int>& Lanes)
{
	const int Got = FogCost(H, Lanes);
	return Got != FogInvalid && Got == FogBest(H).Cost;
}

// How a reading scores against par (the best cost): 3 stars at par, 2 within FogParSlack, 1 otherwise, 0 invalid.
struct FogJudgement { int Cost = FogInvalid, Par = FogInvalid, Stars = 0; bool QuestDone = false; };

inline FogJudgement FogJudge(const FogHarbour& H, const std::vector<int>& Lanes)
{
	FogJudgement J;
	J.Cost = FogCost(H, Lanes);
	J.Par = FogBest(H).Cost;
	J.Stars = J.Cost == FogInvalid ? 0 : J.Cost == J.Par ? 3 : J.Cost <= J.Par + FogParSlack ? 2 : 1;
	J.QuestDone = J.Stars == 3;
	return J;
}

// One blast of the best reading: lane, echo heard, what it cost and what the echo alone suggested.
struct FogStep { int Blast = 0, Lane = 0, Heard = 0, MoveCost = 0, EchoCost = 0, GreedyLane = 0; };

// Why the pilot chose each lane (Java FogChannelPilot.explain); empty for a bad harbour.
inline std::vector<FogStep> FogExplain(const FogHarbour& H)
{
	std::vector<FogStep> Out;
	if (!FogValid(H)) return Out;
	const FogTrack B = FogBest(H), G = FogLoudestEcho(H);
	for (int k = 0; k < H.Blasts(); ++k)
	{
		const int L = B.Lanes[k];
		Out.push_back({ k, L, H.Heard[k], k == 0 ? H.Open[L] : H.Drift[B.Lanes[k - 1]][L], FogEchoCost(H, L, k), G.Lanes[k] });
	}
	return Out;
}

// The explanation in plain words, one line per blast, identical to Java FogChannelPilot.explainText.
inline std::vector<std::string> FogExplainText(const FogHarbour& H)
{
	const std::vector<FogStep> Steps = FogExplain(H);
	std::vector<std::string> Out;
	for (const FogStep& St : Steps)
	{
		const bool Hold = St.Blast > 0 && Steps[St.Blast - 1].Lane == St.Lane;
		const char* Move = St.Blast == 0 ? "open" : Hold ? "hold" : "drift";
		const char* Why = St.Blast == 0 ? "open" : Hold ? "stay" : "drift";
		std::string Line = "blast " + std::to_string(St.Blast + 1) + ": heard " + FogEchoNames[St.Heard] + ", " + Move + " lane "
			+ std::to_string(St.Lane) + " (+" + std::to_string(St.MoveCost) + " " + Why + ", +" + std::to_string(St.EchoCost) + " echo)";
		if (St.GreedyLane != St.Lane) Line += "; the echo alone says lane " + std::to_string(St.GreedyLane);
		Out.push_back(Line);
	}
	return Out;
}

} } // namespace daedalus::pilot
