// SPDX-License-Identifier: MIT
// Kennel Isle ark muster roster, header-only C++ twin of the Java G107 KennelArkMuster (contest G128, art-master-flex).
// Engine-free so the UE muster widget shows the same crew the server would pick. Parity table:
// engines/unreal/core-test/kennel_muster_parity.txt, checked against Java by KennelMusterParityFixtureTest and
// replayed by core-test/kennel_muster_core_test.cpp. Seeded dawn rolls stay on the Java side.
#pragma once

#include "DaedalusKennelCore.h"
#include <cstdint>
#include <vector>

namespace daedalus { namespace kennel { namespace muster {

/** Post order matches KennelArkMuster.ROLES: hatch guard, rescue swimmer, spring finder, deck runner. */
constexpr int NumPosts = 4;
constexpr int LaunchNeed = 3;
constexpr int QuestTries = 3;
constexpr int MaxHounds = 8;

inline ECommand PostCommand(int Post)
{
	static const ECommand C[NumPosts] = {ECommand::Guard, ECommand::Rescue, ECommand::Fetch, ECommand::Come};
	return C[Post];
}

struct FHound
{
	int CareDays = 0;
	int Bond = 0;
};

/** KennelArkMuster.fits: the stage allows the command and the bond tier obeys it. */
inline bool Fits(const FHound& H, int Post)
{
	const ECommand C = PostCommand(Post);
	return StageAllows(StageOf(H.CareDays), C) && Obeys(H.Bond, C);
}

struct FRoster
{
	int Hound[NumPosts] = {-1, -1, -1, -1};
	int Pct[NumPosts] = {0, 0, 0, 0};
	int Filled = 0;
	int TotalPct = 0;
	bool Full() const { return Filled == NumPosts; }
};

namespace detail {
inline void Search(const std::vector<FHound>& Hs, int Post, int* Cur, std::vector<bool>& Used, int Filled, int Pct,
                   int* Best, int& BestFilled, int& BestPct)
{
	if (Post == NumPosts)
	{
		if (Filled > BestFilled || (Filled == BestFilled && Pct > BestPct))
		{
			BestFilled = Filled; BestPct = Pct;
			for (int I = 0; I < NumPosts; ++I) { Best[I] = Cur[I]; }
		}
		return;
	}
	for (size_t I = 0; I < Hs.size(); ++I)
	{
		if (Used[I] || !Fits(Hs[I], Post)) { continue; }
		Used[I] = true; Cur[Post] = static_cast<int>(I);
		Search(Hs, Post + 1, Cur, Used, Filled + 1, Pct + SuccessPct(Hs[I].Bond, PostCommand(Post)), Best, BestFilled, BestPct);
		Used[I] = false;
	}
	Cur[Post] = -1;
	Search(Hs, Post + 1, Cur, Used, Filled, Pct, Best, BestFilled, BestPct);
}
} // namespace detail

/** KennelArkMuster.assign: most posts, then highest summed odds; ties keep the earlier hound. False if > MaxHounds. */
inline bool Assign(const std::vector<FHound>& Hs, FRoster& Out)
{
	Out = FRoster();
	if (Hs.size() > static_cast<size_t>(MaxHounds)) { return false; }
	int Cur[NumPosts] = {-1, -1, -1, -1}, Best[NumPosts] = {-1, -1, -1, -1};
	int BestFilled = -1, BestPct = -1;
	std::vector<bool> Used(Hs.size(), false);
	detail::Search(Hs, 0, Cur, Used, 0, 0, Best, BestFilled, BestPct);
	for (int P = 0; P < NumPosts; ++P)
	{
		Out.Hound[P] = Best[P];
		if (Best[P] < 0) { continue; }
		Out.Pct[P] = SuccessPct(Hs[static_cast<size_t>(Best[P])].Bond, PostCommand(P));
		++Out.Filled; Out.TotalPct += Out.Pct[P];
	}
	return true;
}

/** The ark lifts at LaunchNeed or more holds; a roster under LaunchNeed posts cannot muster at all. */
inline bool Launches(int Holds) { return Holds >= LaunchNeed; }
inline bool CanMuster(const FRoster& R) { return R.Filled >= LaunchNeed; }

/** 64-bit LCG used only to generate the parity crews (same arithmetic in the Java fixture). */
inline uint64_t NextLcg(uint64_t& X)
{
	X = X * 6364136223846793005ull + 1442695040888963407ull;
	return X >> 33;
}

}}} // namespace daedalus::kennel::muster
