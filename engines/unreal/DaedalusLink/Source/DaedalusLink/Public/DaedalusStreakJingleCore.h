// SPDX-License-Identifier: MIT
// Prismheart streak jingle (audio lane, idea PROM-2), plain C++17 for the Unreal binding. A cabinet's win jingle grows
// one note for every day of the player's daily streak (up to 8), so a long run is audible across the hall; a broken
// streak goes back to the plain win cue. The streak count comes from the Daily Almanac (almanac::Streak).
//
// Rules (opt-in, built on cue kit V2): the kit is MakeKitV2(game, token); the added notes are drawn from
// DaedalusPyRandomCore.h seeded "jingle|<game>|<token>": the first is a random scale degree 0-4, each next one a
// different degree 0-4. All 8 are drawn up front, so day N+1's jingle is day N's plus one note (it grows, never
// reshuffles). Added notes are short (half the kit note + 30 ms, half the gap), then the kit's V2 win cue plays.
// Every note goes through EarSafePeak (DaedalusEarRuleCore.h): under 800 Hz, soft, two harmonics, no sweep.
// Reference: tools/minigames/streak_jingle.py writes streak_jingle_golden.txt; checked by streak_jingle_core_test.cpp.
#pragma once
#include "DaedalusCueKitCore.h"
#include "DaedalusPrismAlmanacCore.h"

#include <cstdint>
#include <set>
#include <string>

namespace daedalus { namespace streakjingle {

using cuekit::Kit;
using cuekit::Phrase;

/** Seed string for the added notes. */
inline std::string JingleSeed(const char* GameId, std::uint64_t TokenId)
{
	return std::string("jingle|") + (GameId ? GameId : "") + "|" + std::to_string(TokenId);
}

/** The eight added-note scale degrees for a cabinet on a token (0-4, no degree repeats the one before). */
struct Ladder { int Degree[cuekit::MaxStreakNotes] = {}; };
inline Ladder MakeLadder(const char* GameId, std::uint64_t TokenId)
{
	pyrandom::PyRandom R(JingleSeed(GameId, TokenId));
	Ladder L;
	int Prev = static_cast<int>(R.Below(5));
	L.Degree[0] = Prev;
	for (int I = 1; I < cuekit::MaxStreakNotes; ++I)
	{
		Prev = (Prev + 1 + static_cast<int>(R.Below(4))) % 5;
		L.Degree[I] = Prev;
	}
	return L;
}

/** The jingle for a streak of StreakDays (clamped to 0..8): that many added notes, then the V2 win cue. */
inline Phrase Jingle(const Kit& K, const Ladder& L, int StreakDays)
{
	const int Days = StreakDays < 0 ? 0 : (StreakDays > cuekit::MaxStreakNotes ? cuekit::MaxStreakNotes : StreakDays);
	Phrase P;
	for (int I = 0; I < Days; ++I) cuekit::detail::Add(P, K.StepHz(L.Degree[I]), K.NoteMs / 2 + 30, K.GapMs / 2);
	const Phrase& W = K.Cues[static_cast<int>(cuekit::Cue::Win)];
	for (int I = 0; I < W.Count; ++I) cuekit::detail::Add(P, W.N[I].Hz, W.N[I].Ms, W.N[I].GapMs);
	return P;
}
inline Phrase JingleV2(const char* GameId, std::uint64_t TokenId, int StreakDays)
{
	return Jingle(cuekit::MakeKitV2(GameId, TokenId), MakeLadder(GameId, TokenId), StreakDays);
}
/** Hooked to the Daily Almanac: the streak is almanac::Streak(Cleared, Today). */
inline Phrase JingleForAlmanac(const char* GameId, std::uint64_t TokenId, const std::set<std::int64_t>& Cleared, std::int64_t Today)
{
	return JingleV2(GameId, TokenId, almanac::Streak(Cleared, Today));
}

}} // namespace daedalus::streakjingle
