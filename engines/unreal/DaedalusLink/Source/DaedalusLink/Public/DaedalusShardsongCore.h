// SPDX-License-Identifier: MIT
// G587 Shardsong Crossing, plain C++17 for the Unreal binding. When the planet shattered, songbird pairs were split
// across the drifting fragments that became the Daedalus islands. Each round a bird must reach its mate across a
// seeded path of habitat strips (forest, grass, open water, scrub) carried over from the old world. The player picks
// a call pitch band and a form (a steady tone or a fast trill); the mate hears it if the received level clears the
// noise at the mate's fragment. Score is how close the choice comes to the best possible signal-to-noise ratio.
//
// Ecology (illustrative, not a propagation model): sound spreads (20 log10 d), habitats add excess attenuation that
// rises with pitch in foliage, open ground adds a low-mid "ground dip", reverberation in forest smears fast trills,
// and wind over open ground blurs long steady tones. This follows the acoustic adaptation hypothesis (dense habitats
// favour lower, tonal songs; open habitats favour higher, modulated ones), which fits some bird groups and not
// others. Real songs are mostly well above 800 Hz; bands here are compressed under the ear rule (DaedalusEarRuleCore.h).
//
// Determinism: integer tables only (tenths of dB), a SplitMix64 generator defined here, no floating point in the
// rules, no heap. The same token seed gives the same game on g++, clang++ and MSVC. Checked by
// engines/unreal/core-test/shardsong_core_test.cpp against shardsong_golden.txt.
#pragma once
#include "DaedalusEarRuleCore.h"

#include <cstdint>

namespace daedalus { namespace shardsong {

constexpr int Bands = 6, Rounds = 5, MaxSegments = 4, MaxTotalM = 400, SourceLevel = 900, HeardSnr = 30;
/** Call pitch per band, Hz (all under the ear rule). */
constexpr int BandHz[Bands] = { 200, 250, 315, 400, 500, 630 };

enum class Habitat : std::uint8_t { Forest, Grass, Water, Scrub };
enum class Form : std::uint8_t { Tone, Trill };
enum class Difficulty : std::uint8_t { Easy, Normal, Hard };
constexpr int HabitatCount = 4;

inline const char* HabitatName(Habitat H)
{
	static const char* const N[HabitatCount] = { "forest", "grass", "water", "scrub" };
	return N[static_cast<int>(H)];
}

/** 20 log10(d) in tenths of dB for d = 10, 20, ..., 400 m (spherical spreading from 1 m). */
constexpr int SpreadTenths[MaxTotalM / 10] = { 200, 260, 295, 320, 340, 356, 369, 381, 391, 400, 408, 416, 423, 429,
	435, 441, 446, 451, 456, 460, 464, 468, 472, 476, 480, 483, 486, 489, 492, 495, 498, 501, 504, 506, 509, 511, 514,
	516, 518, 520 };
/** Excess attenuation, tenths of dB per 10 m, by habitat and band (illustrative). */
constexpr int ExcessTenths[HabitatCount][Bands] = {
	{ 2, 3, 4, 6, 8, 11 },  // forest: foliage scattering grows with pitch
	{ 9, 10, 7, 4, 3, 3 },  // grass: ground dip in the low bands
	{ 1, 1, 1, 1, 1, 2 },   // water: open and quiet
	{ 3, 4, 4, 5, 6, 7 },   // scrub: in between
};
/** Ambient noise at the listener's fragment, tenths of dB, by habitat and band (illustrative). */
constexpr int NoiseTenths[HabitatCount][Bands] = {
	{ 340, 320, 310, 330, 360, 400 },  // forest: wind roar low, insects high
	{ 360, 340, 310, 320, 350, 380 },  // grass: wind low, crickets high
	{ 420, 390, 350, 320, 300, 290 },  // water: surf in the low bands
	{ 350, 330, 310, 320, 330, 350 },  // scrub
};
/** Trills smear in forest reverberation; steady tones blur in wind over open ground. Tenths of dB per 10 m. */
constexpr int TrillInForestTenths = 5, ToneInOpenTenths = 2;

/** SplitMix64, integer only, so every compiler draws the same numbers. */
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

/** Seed for a fragment pair from a Daedalus token id (mixed so neighbouring ids give unrelated games). */
inline std::uint64_t TokenSeed(std::uint64_t TokenId)
{
	Rng R(TokenId ^ 0x5348415244534E47ULL);  // "SHARDSNG"
	return R.Next();
}

struct Segment { Habitat H = Habitat::Forest; int LengthM = 10; };

struct Crossing
{
	Segment Seg[MaxSegments];
	int Count = 0;
	Habitat Listener() const { return Seg[Count - 1].H; }
	int TotalM() const { int T = 0; for (int I = 0; I < Count; ++I) T += Seg[I].LengthM; return T; }
};

/** Received level at the mate, tenths of dB. */
inline int ReceivedTenths(const Crossing& C, int Band, Form F)
{
	int L = SourceLevel - SpreadTenths[C.TotalM() / 10 - 1];
	for (int I = 0; I < C.Count; ++I)
	{
		const Segment& S = C.Seg[I];
		const int Steps = S.LengthM / 10;
		L -= ExcessTenths[static_cast<int>(S.H)][Band] * Steps;
		if (F == Form::Trill && S.H == Habitat::Forest) L -= TrillInForestTenths * Steps;
		if (F == Form::Tone && (S.H == Habitat::Grass || S.H == Habitat::Water)) L -= ToneInOpenTenths * Steps;
	}
	return L;
}
/** Signal-to-noise ratio at the mate, tenths of dB. */
inline int SnrTenths(const Crossing& C, int Band, Form F)
{
	return ReceivedTenths(C, Band, F) - NoiseTenths[static_cast<int>(C.Listener())][Band];
}

struct Choice { int Band = 0; Form F = Form::Tone; int Snr = 0; };
/** Best choice; ties keep the lowest band, then the tone. */
inline Choice Best(const Crossing& C)
{
	Choice B; B.Snr = SnrTenths(C, 0, Form::Tone);
	for (int Band = 0; Band < Bands; ++Band)
		for (int F = 0; F < 2; ++F)
		{
			const int S = SnrTenths(C, Band, static_cast<Form>(F));
			if (S > B.Snr) { B.Band = Band; B.F = static_cast<Form>(F); B.Snr = S; }
		}
	return B;
}

/** 0..100: zero if the mate cannot hear it, otherwise 100 minus one point per 0.1 dB short of the best. */
inline int Score(const Crossing& C, int Band, Form F)
{
	if (Band < 0 || Band >= Bands) return 0;
	const int S = SnrTenths(C, Band, F);
	if (S < HeardSnr) return 0;
	const int P = 100 - (Best(C).Snr - S);
	return P < 0 ? 0 : (P > 100 ? 100 : P);
}

/** One crossing from the generator: 1-2 (easy), 2-3 (normal) or 3-4 (hard) strips of 10-120 m, at most 400 m,
 *  shortened (longest strip first) until the best call is heard, so every crossing is solvable. */
inline Crossing Generate(Rng& R, Difficulty D)
{
	const int Min = D == Difficulty::Easy ? 1 : (D == Difficulty::Normal ? 2 : 3);
	Crossing C;
	C.Count = Min + R.Below(2);
	for (int I = 0; I < C.Count; ++I)
	{
		C.Seg[I].H = static_cast<Habitat>(R.Below(HabitatCount));
		C.Seg[I].LengthM = 10 * (1 + R.Below(12));
	}
	for (int Guard = 0; Guard < 64 && (C.TotalM() > MaxTotalM || Best(C).Snr < HeardSnr); ++Guard)
	{
		int L = 0;
		for (int I = 1; I < C.Count; ++I) if (C.Seg[I].LengthM > C.Seg[L].LengthM) L = I;
		if (C.Seg[L].LengthM <= 10) break;
		C.Seg[L].LengthM -= 10;
	}
	return C;
}

/** The pitched call the bird plays for a choice, made ear-safe (base and peak under 800 Hz). */
inline earrule::CallSpec CallFor(int Band, Form F)
{
	earrule::CallSpec S;
	S.BaseHz = BandHz[Band];
	S.Harmonics = 2;
	S.Brightness = 0.2;
	S.Pulses = F == Form::Trill ? 8 : 1;
	S.PulseMs = F == Form::Trill ? 40 : 420;
	S.GapMs = F == Form::Trill ? 25 : 0;
	S.VibratoHz = 5;
	S.VibratoDepth = F == Form::Tone ? 0.3 : 0;
	return earrule::EarSafePeak(S);
}

/** Five crossings, one choice each. */
struct Game
{
	Difficulty D = Difficulty::Normal;
	Crossing Rounds_[Rounds];
	int Scores[Rounds] = {};
	int Index = 0;

	static Game Begin(std::uint64_t Seed, Difficulty Level)
	{
		Game G;
		G.D = Level;
		Rng R(Seed);
		for (int I = 0; I < Rounds; ++I) G.Rounds_[I] = Generate(R, Level);
		return G;
	}
	bool Over() const { return Index >= Rounds; }
	const Crossing& Current() const { return Rounds_[Index < Rounds ? Index : Rounds - 1]; }
	/** Plays the current round; returns its score, or -1 if the game is over or the band is invalid. */
	int Choose(int Band, Form F)
	{
		if (Over() || Band < 0 || Band >= Bands) return -1;
		const int S = Score(Rounds_[Index], Band, F);
		Scores[Index++] = S;
		return S;
	}
	int Total() const { int T = 0; for (int I = 0; I < Index; ++I) T += Scores[I]; return T; }
};

}} // namespace daedalus::shardsong
