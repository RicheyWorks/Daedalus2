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
constexpr int FogMaxBlasts = 8;
constexpr int FogInvalid = -1;

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
	const int T = 1 + Below(FogMaxBlasts);
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

// Total cost of a lane sequence, or FogInvalid when it is the wrong length or names a missing lane.
inline int FogCost(const FogHarbour& H, const std::vector<int>& Lanes)
{
	if (static_cast<int>(Lanes.size()) != H.Blasts()) return FogInvalid;
	int Total = 0;
	for (int k = 0; k < H.Blasts(); ++k)
	{
		const int L = Lanes[k];
		if (L < 0 || L >= H.Channels()) return FogInvalid;
		Total += (k == 0 ? H.Open[L] : H.Drift[Lanes[k - 1]][L]) + H.Echo[L][H.Heard[k]];
	}
	return Total;
}

// Cheapest lane sequence for all blasts at once (Viterbi, integer min-sum); ties go to the lower lane.
inline FogTrack FogBest(const FogHarbour& H)
{
	const int S = H.Channels(), T = H.Blasts();
	if (T == 0) return {};
	std::vector<std::vector<int>> Cost(T, std::vector<int>(S, 0)), From(T, std::vector<int>(S, 0));
	for (int i = 0; i < S; ++i) Cost[0][i] = H.Open[i] + H.Echo[i][H.Heard[0]];
	for (int k = 1; k < T; ++k)
		for (int j = 0; j < S; ++j)
		{
			int Prev = 0;
			for (int i = 1; i < S; ++i)
				if (Cost[k - 1][i] + H.Drift[i][j] < Cost[k - 1][Prev] + H.Drift[Prev][j]) Prev = i;
			Cost[k][j] = Cost[k - 1][Prev] + H.Drift[Prev][j] + H.Echo[j][H.Heard[k]];
			From[k][j] = Prev;
		}
	int Last = 0;
	for (int i = 1; i < S; ++i)
		if (Cost[T - 1][i] < Cost[T - 1][Last]) Last = i;
	FogTrack Track{ Cost[T - 1][Last], std::vector<int>(T, Last) };
	for (int k = T - 1; k > 0; --k) Track.Lanes[k - 1] = From[k][Track.Lanes[k]];
	return Track;
}

// The dockhand's habit: each blast on its own, the lane its echo surprises least (lower lane on ties).
inline FogTrack FogLoudestEcho(const FogHarbour& H)
{
	FogTrack Track;
	for (int k = 0; k < H.Blasts(); ++k)
	{
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

} } // namespace daedalus::pilot
