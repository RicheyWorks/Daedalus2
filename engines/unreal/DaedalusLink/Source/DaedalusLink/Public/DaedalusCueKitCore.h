// SPDX-License-Identifier: MIT
// Prismheart cue kits (audio lane, first slice), plain C++17 for the Unreal binding. Every cabinet gets its own small,
// recognisable set of sound cues (start, good move, miss, win, and a streak cue that grows one note per streak day),
// generated from the game id and the island token, so the same cabinet sounds the same on every platform.
//
// Musical rules (integer only): a root of 165-262 Hz, a five-note scale in just ratios plus the octave (so the top note
// is at most 524 Hz), short soft notes. Good cues rise, miss cues fall gently, win and streak cues land on the root or
// its octave. Every note becomes an earrule::CallSpec through EarSafePeak (DaedalusEarRuleCore.h): base and peak under
// 800 Hz, two soft harmonics, low brightness, no sweeps. Generated, never sampled from existing tunes.
//
// Rulesets. V1 (frozen, cue_kit_golden.txt): FNV-1a 64 of the game id, SplitMix64 defined here, no heap.
// V2 (team standard, cue_kit_golden_v2.txt): the same musical rules drawn from DaedalusPyRandomCore.h (CPython
// random.Random) seeded with the string "cuekit|<game>|<token>", so tools/minigames/cue_kit.py (the rules reference)
// and the C++ core give identical kits. Seeding V2 allocates once; building a kit does not.
// Checked by engines/unreal/core-test/cue_kit_core_test.cpp.
#pragma once
#include "DaedalusEarRuleCore.h"
#include "DaedalusPyRandomCore.h"

#include <cstdint>
#include <string>

namespace daedalus { namespace cuekit {

constexpr int Roots = 6, Degrees = 6, MaxNotes = 12, MaxStreakNotes = 8, CueCount = 5;
/** Kit roots, Hz (low and warm). */
constexpr int RootHz[Roots] = { 165, 175, 196, 220, 247, 262 };
/** Major pentatonic in just ratios plus the octave: 1, 9/8, 5/4, 3/2, 5/3, 2. */
constexpr int DegNum[Degrees] = { 1, 9, 5, 3, 5, 2 }, DegDen[Degrees] = { 1, 8, 4, 2, 3, 1 };
static_assert(RootHz[Roots - 1] * 2 < 800, "top note must stay under the 800 Hz ear rule");

enum class Cue : std::uint8_t { Start, Good, Miss, Win, Streak };
inline const char* CueName(Cue C)
{
	static const char* const N[CueCount] = { "start", "good", "miss", "win", "streak" };
	return N[static_cast<int>(C)];
}

/** SplitMix64, integer only. */
struct Rng
{
	std::uint64_t State;
	explicit Rng(std::uint64_t Seed) : State(Seed) {}
	std::uint64_t Next()
	{
		std::uint64_t Z = (State += 0x9E3779B97F4A7C15ULL);
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		return Z ^ (Z >> 31);
	}
	int Below(int N) { return static_cast<int>(Next() % static_cast<std::uint64_t>(N)); }
};

/** FNV-1a 64 of a NUL-terminated game id. */
inline std::uint64_t HashId(const char* Id)
{
	std::uint64_t H = 0xCBF29CE484222325ULL;
	for (; Id && *Id; ++Id) { H ^= static_cast<unsigned char>(*Id); H *= 0x100000001B3ULL; }
	return H;
}
/** Kit seed for a cabinet on an island token. */
inline std::uint64_t KitSeed(const char* GameId, std::uint64_t TokenId)
{
	Rng R(HashId(GameId) ^ (TokenId * 0xD1B54A32D192ED03ULL) ^ 0x4355454B4954ULL);  // "CUEKIT"
	return R.Next();
}

struct Note { int Hz = 0, Ms = 0, GapMs = 0; };
struct Phrase
{
	Note N[MaxNotes];
	int Count = 0;
	int DurationMs() const { int T = 0; for (int I = 0; I < Count; ++I) T += N[I].Ms + (I + 1 < Count ? N[I].GapMs : 0); return T; }
};

struct Kit
{
	int Root = RootHz[0];
	int NoteMs = 120, GapMs = 30;
	Phrase Cues[CueCount - 1];  // start, good, miss, win; the streak cue is built on demand
	int StepHz(int Degree) const { return Root * DegNum[Degree] / DegDen[Degree]; }
};

namespace detail {
inline void Add(Phrase& P, int Hz, int Ms, int Gap) { if (P.Count < MaxNotes) { P.N[P.Count].Hz = Hz; P.N[P.Count].Ms = Ms; P.N[P.Count].GapMs = Gap; ++P.Count; } }
}

/** Builds a cabinet's kit. Start: three notes inside the scale. Good: two or three notes stepping up the scale. Miss: two
 *  gently falling notes (one to three scale steps down, held longer). Win: four notes ending on the octave. */
/** The musical rules, drawing every choice from Below(N) in [0, N); shared by V1 and V2. */
template <typename DrawT> Kit BuildKit(DrawT&& Below)
{
	Kit K;
	K.Root = RootHz[Below(Roots)];
	K.NoteMs = 90 + 10 * Below(7);  // 90-150 ms
	K.GapMs = 20 + 10 * Below(3);   // 20-40 ms
	Phrase& S = K.Cues[0];
	for (int I = 0; I < 3; ++I) detail::Add(S, K.StepHz(Below(Degrees - 1)), K.NoteMs, K.GapMs);
	Phrase& G = K.Cues[1];
	const int GN = 2 + Below(2);
	const int D0 = Below(Degrees - GN + 1);
	for (int I = 0; I < GN; ++I) detail::Add(G, K.StepHz(D0 + I), K.NoteMs, K.GapMs);  // stepwise up
	Phrase& M = K.Cues[2];
	const int Top = 2 + Below(3);           // degree 2-4
	const int Drop = 1 + Below(Top < 3 ? Top : 3);
	detail::Add(M, K.StepHz(Top), K.NoteMs + 40, K.GapMs);
	detail::Add(M, K.StepHz(Top - Drop), K.NoteMs + 120, 0);
	Phrase& W = K.Cues[3];
	int WD = Below(3);
	for (int I = 0; I < 3; ++I) { detail::Add(W, K.StepHz(WD), K.NoteMs, K.GapMs); WD += 1 + Below(2); if (WD > Degrees - 2) WD = Degrees - 2; }
	detail::Add(W, K.StepHz(Degrees - 1), K.NoteMs * 2, 0);
	return K;
}
/** V1 kit (frozen). */
inline Kit MakeKit(std::uint64_t Seed)
{
	Rng R(Seed);
	return BuildKit([&R](int N) { return R.Below(N); });
}
/** V2 seed string: "cuekit|<game>|<token>". */
inline std::string KitSeedV2(const char* GameId, std::uint64_t TokenId)
{
	return std::string("cuekit|") + (GameId ? GameId : "") + "|" + std::to_string(TokenId);
}
/** V2 kit: identical rules, draws from CPython-compatible random.Random(seed string).randrange. */
inline Kit MakeKitV2(const char* GameId, std::uint64_t TokenId)
{
	pyrandom::PyRandom P(KitSeedV2(GameId, TokenId));
	return BuildKit([&P](int N) { return static_cast<int>(P.Below(static_cast<std::uint32_t>(N))); });
}

/** A cue of a kit. Streak: the win cue preceded by one rising scale note per streak day (up to 8; days < 1 = win). */
inline Phrase CueOf(const Kit& K, Cue C, int StreakDays = 0)
{
	if (C != Cue::Streak) return K.Cues[static_cast<int>(C)];
	Phrase P;
	const int Days = StreakDays < 0 ? 0 : (StreakDays > MaxStreakNotes ? MaxStreakNotes : StreakDays);
	for (int I = 0; I < Days; ++I) detail::Add(P, K.StepHz(I % (Degrees - 1)), K.NoteMs / 2 + 30, K.GapMs / 2);
	const Phrase& W = K.Cues[3];
	for (int I = 0; I < W.Count && P.Count < MaxNotes; ++I) detail::Add(P, W.N[I].Hz, W.N[I].Ms, W.N[I].GapMs);
	return P;
}

/** The ear-safe call spec for one note (soft, two harmonics, no sweep or vibrato). */
inline earrule::CallSpec NoteCall(const Note& N)
{
	earrule::CallSpec S;
	S.BaseHz = N.Hz;
	S.Harmonics = 2;
	S.Brightness = 0.15;
	S.Pulses = 1;
	S.PulseMs = N.Ms;
	S.GapMs = 0;
	return earrule::EarSafePeak(S);
}

}} // namespace daedalus::cuekit
