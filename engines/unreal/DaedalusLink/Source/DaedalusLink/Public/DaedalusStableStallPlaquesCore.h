// SPDX-License-Identifier: MIT
// G547 Stall Plaques (2hot2trot), plain C++17, header-only, no Unreal types (G567 port).
// Must agree with com.daedalus.world.stable.StallPlaques line for line (stable_stall_plaques_parity.txt,
// checked by StableCoresParityTest.java and stable_stall_plaques_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <cstdint>
#include <limits>
#include <vector>

namespace daedalus { namespace stable {

constexpr const char* PlaqueQuest = "q_neat_plaques";
constexpr int64_t PlaqueInvalid = -1;

// A layout: total squared slack (last line free) and the index of the first name on each new line.
struct PlaqueLayout { int64_t Ugliness = 0; std::vector<int> Breaks; };

// Seeded name lengths in [MinLen, MaxLen] (Java StallPlaques.names).
inline std::vector<int> PlaqueNames(int64_t Seed, int N, int MinLen, int MaxLen)
{
	StableRng Rng(Seed);
	std::vector<int> L(N);
	for (int& V : L) V = MinLen + Rng.NextInt(MaxLen - MinLen + 1);
	return L;
}

// Ugliness of a line breaking, or PlaqueInvalid when a line is empty, overflows or a break is out of range.
inline int64_t PlaqueUgliness(const std::vector<int>& Len, int Width, const std::vector<int>& Breaks)
{
	const int N = static_cast<int>(Len.size());
	const int B = static_cast<int>(Breaks.size());
	int64_t Total = 0;
	for (int k = 0, Start = 0; k <= B; ++k)
	{
		const int End = k < B ? Breaks[k] : N;
		if ((End <= Start && !(N == 0 && B == 0)) || End > N) return PlaqueInvalid;
		int Used = -1;
		for (int i = Start; i < End; ++i) Used += Len[i] + 1;
		if (Used > Width) return PlaqueInvalid;
		if (k < B) Total += static_cast<int64_t>(Width - Used) * (Width - Used);
		Start = End;
	}
	return Total;
}

// Least ugliness, exactly: DP from the last name backwards over where the current line ends.
inline PlaqueLayout PlaqueBest(const std::vector<int>& Len, int Width)
{
	const int N = static_cast<int>(Len.size());
	std::vector<int64_t> Cost(N + 1, 0);
	std::vector<int> Next(N + 1, N);
	for (int i = N - 1; i >= 0; --i)
	{
		Cost[i] = std::numeric_limits<int64_t>::max();
		int Used = -1;
		for (int j = i; j < N; ++j)
		{
			Used += Len[j] + 1;
			if (Used > Width) break;
			const int64_t Slack = Width - Used;
			const int64_t C = (j == N - 1 ? 0 : Slack * Slack) + Cost[j + 1];
			if (C < Cost[i]) { Cost[i] = C; Next[i] = j + 1; }
		}
	}
	PlaqueLayout L{ Cost[0], {} };
	for (int i = Next[0]; i < N; i = Next[i]) L.Breaks.push_back(i);
	return L;
}

// Naive habit: fill each line as full as it goes.
inline PlaqueLayout PlaqueFillEachLine(const std::vector<int>& Len, int Width)
{
	PlaqueLayout L;
	int Used = -1;
	for (int i = 0; i < static_cast<int>(Len.size()); ++i)
	{
		if (Used + Len[i] + 1 > Width) { L.Breaks.push_back(i); Used = -1; }
		Used += Len[i] + 1;
	}
	L.Ugliness = PlaqueUgliness(Len, Width, L.Breaks);
	return L;
}

inline bool PlaqueQuestDone(const std::vector<int>& Len, int Width, const std::vector<int>& Breaks)
{
	const int64_t Got = PlaqueUgliness(Len, Width, Breaks);
	return Got != PlaqueInvalid && Got == PlaqueBest(Len, Width).Ugliness;
}

} } // namespace daedalus::stable
