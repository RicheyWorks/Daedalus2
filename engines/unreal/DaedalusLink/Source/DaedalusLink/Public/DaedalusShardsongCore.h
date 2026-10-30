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
static_assert(BandHz[Bands - 1] < 800, "every call band must stay under the 800 Hz ear rule");

enum class Habitat : std::uint8_t { Forest, Grass, Water, Scrub, Marsh, Rock };
enum class Form : std::uint8_t { Tone, Trill };
enum class Difficulty : std::uint8_t { Easy, Normal, Hard };
/** Ruleset V1 is the frozen launch game (four habitats, still air; shardsong_golden.txt). V2 adds reed marsh and bare
 *  rock, per-round wind, a gentle first round and a difficulty ramp (shardsong_golden_v2.txt). V1 stays the default. */
enum class Ruleset : std::uint8_t { V1, V2 };
enum class Wind : std::uint8_t { Calm, Breeze, Gusty };
constexpr int HabitatCount = 6, V1HabitatCount = 4, WindCount = 3;

inline const char* HabitatName(Habitat H)
{
	static const char* const N[HabitatCount] = { "forest", "grass", "water", "scrub", "marsh", "rock" };
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
	{ 3, 4, 6, 9, 12, 15 }, // marsh (V2): dense reed stems scatter the upper bands hardest
	{ 1, 1, 1, 2, 2, 2 },   // rock (V2): bare and open
};
/** Ambient noise at the listener's fragment, tenths of dB, by habitat and band (illustrative). */
constexpr int NoiseTenths[HabitatCount][Bands] = {
	{ 340, 320, 310, 330, 360, 400 },  // forest: wind roar low, insects high
	{ 360, 340, 310, 320, 350, 380 },  // grass: wind low, crickets high
	{ 420, 390, 350, 320, 300, 290 },  // water: surf in the low bands
	{ 350, 330, 310, 320, 330, 350 },  // scrub
	{ 330, 350, 390, 410, 370, 340 },  // marsh (V2): frog chorus in the middle bands
	{ 300, 300, 300, 310, 320, 330 },  // rock (V2): quiet, a little wind hiss up high
};
/** Wind noise added at the mate, tenths of dB by band (wind roar is low-pitched); halved for a mate in forest shelter.
 *  Calm in V1 always. */
constexpr int WindNoiseTenths[WindCount][Bands] = {
	{ 0, 0, 0, 0, 0, 0 },
	{ 40, 30, 20, 10, 0, 0 },
	{ 80, 60, 40, 20, 10, 0 },
};
inline const char* WindName(Wind W)
{
	static const char* const N[WindCount] = { "calm", "breeze", "gusty" };
	return N[static_cast<int>(W)];
}
/** Trills smear in forest reverberation (and off rock faces in V2); steady tones blur in wind over open ground, twice as
 *  much when gusty. Tenths of dB per 10 m. */
constexpr int ChorusTenths = 80;
constexpr int TrillInForestTenths = 5, TrillOffRockTenths = 3, ToneInOpenTenths = 2;

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
	Wind Air = Wind::Calm;
	/** V2: band where another flock is singing at the mate's fragment (-1: none). Adds ChorusTenths there and half on
	 *  the neighbouring bands, so a call has to find a free band (the acoustic niche idea, illustrative). */
	int Chorus = -1;
	Habitat Listener() const { return Seg[Count - 1].H; }
	int TotalM() const { int T = 0; for (int I = 0; I < Count; ++I) T += Seg[I].LengthM; return T; }
};

/** Smearing of one strip for a form, tenths of dB per 10 m. */
inline int SmearPerStep(Habitat H, Form F, Wind W)
{
	if (F == Form::Trill) return H == Habitat::Forest ? TrillInForestTenths : (H == Habitat::Rock ? TrillOffRockTenths : 0);
	return (H == Habitat::Grass || H == Habitat::Water) ? ToneInOpenTenths * (W == Wind::Gusty ? 2 : 1) : 0;
}
/** Received level at the mate, tenths of dB. */
inline int ReceivedTenths(const Crossing& C, int Band, Form F)
{
	int L = SourceLevel - SpreadTenths[C.TotalM() / 10 - 1];
	for (int I = 0; I < C.Count; ++I)
	{
		const Segment& S = C.Seg[I];
		const int Steps = S.LengthM / 10;
		L -= (ExcessTenths[static_cast<int>(S.H)][Band] + SmearPerStep(S.H, F, C.Air)) * Steps;
	}
	return L;
}
/** Noise at the mate: habitat noise plus wind (halved in forest shelter), tenths of dB. */
inline int NoiseAt(const Crossing& C, int Band)
{
	const int W = WindNoiseTenths[static_cast<int>(C.Air)][Band];
	const int Gap = C.Chorus < 0 ? 9 : (Band > C.Chorus ? Band - C.Chorus : C.Chorus - Band);
	const int Flock = Gap == 0 ? ChorusTenths : (Gap == 1 ? ChorusTenths / 2 : 0);
	return NoiseTenths[static_cast<int>(C.Listener())][Band] + (C.Listener() == Habitat::Forest ? W / 2 : W) + Flock;
}
/** Signal-to-noise ratio at the mate, tenths of dB. */
inline int SnrTenths(const Crossing& C, int Band, Form F)
{
	return ReceivedTenths(C, Band, F) - NoiseAt(C, Band);
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

/** Where a call's level goes, tenths of dB: Received = SourceLevel - Spread - Absorbed - Smeared; Snr = Received - Noise. */
struct Breakdown { int Spread = 0, Absorbed = 0, Smeared = 0, Noise = 0, Snr = 0; };
inline Breakdown Explain(const Crossing& C, int Band, Form F)
{
	Breakdown B;
	B.Spread = SpreadTenths[C.TotalM() / 10 - 1];
	for (int I = 0; I < C.Count; ++I)
	{
		const Segment& S = C.Seg[I];
		const int Steps = S.LengthM / 10;
		B.Absorbed += ExcessTenths[static_cast<int>(S.H)][Band] * Steps;
		B.Smeared += SmearPerStep(S.H, F, C.Air) * Steps;
	}
	B.Noise = NoiseAt(C, Band);
	B.Snr = SourceLevel - B.Spread - B.Absorbed - B.Smeared - B.Noise;
	return B;
}

/** The main reason a call fell short of the best one (no cost to ask): soaked up by the habitats on the path, smeared
 *  (a trill in forest echo, a tone in open wind), or masked by noise where the mate sits. */
enum class Cause : std::uint8_t { None, Absorbed, Smeared, Masked };
inline const char* CauseName(Cause C)
{
	static const char* const N[4] = { "best call", "soaked up by the habitats on the way", "smeared on the way", "masked by noise at the mate" };
	return N[static_cast<int>(C)];
}
struct Feedback
{
	Cause Main = Cause::None;
	int ShortTenths = 0;  // best SNR minus this call's SNR (>= 0)
	bool Heard = false;
	int PitchHint = 0;    // -1: try lower, +1: try higher, 0: pitch is right
	bool SwitchForm = false;
};
inline Feedback Advise(const Crossing& C, int Band, Form F)
{
	Feedback Out;
	const Choice B = Best(C);
	const Breakdown Mine = Explain(C, Band, F), Top = Explain(C, B.Band, B.F);
	Out.ShortTenths = Top.Snr - Mine.Snr;
	Out.Heard = Mine.Snr >= HeardSnr;
	Out.PitchHint = B.Band < Band ? -1 : (B.Band > Band ? 1 : 0);
	Out.SwitchForm = B.F != F;
	if (Out.ShortTenths <= 0) return Out;
	const int DA = Mine.Absorbed - Top.Absorbed, DS = Mine.Smeared - Top.Smeared, DN = Mine.Noise - Top.Noise;
	Out.Main = DA >= DS && DA >= DN ? Cause::Absorbed : (DS >= DN ? Cause::Smeared : Cause::Masked);
	return Out;
}

/** Best tone only (ties keep the lowest band). */
inline Choice BestTone(const Crossing& C)
{
	Choice B; B.Snr = SnrTenths(C, 0, Form::Tone);
	for (int Band = 1; Band < Bands; ++Band)
	{
		const int S = SnrTenths(C, Band, Form::Tone);
		if (S > B.Snr) { B.Band = Band; B.Snr = S; }
	}
	return B;
}

/** V1 crossing: 1-2 (easy), 2-3 (normal) or 3-4 (hard) strips of 10-120 m in four habitats, still air, at most 400 m,
 *  shortened (longest strip first) until the best call is heard, so every crossing is solvable. Frozen. */
inline Crossing Generate(Rng& R, Difficulty D)
{
	const int Min = D == Difficulty::Easy ? 1 : (D == Difficulty::Normal ? 2 : 3);
	Crossing C;
	C.Count = Min + R.Below(2);
	for (int I = 0; I < C.Count; ++I)
	{
		C.Seg[I].H = static_cast<Habitat>(R.Below(V1HabitatCount));
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

/** V2 crossing for round Round (0-based). Round 0 is gentle at every difficulty: one strip of 20-60 m in still air.
 *  Later rounds ramp: rounds 1-2 use the difficulty's base strip count, rounds 3-4 one more, and the longest strip
 *  allowed grows by 20 m a round (60 m up to 120 m). Six habitats; wind drawn per round (calm 2/4, breeze, gusty).
 *  Shortened like V1 until both the best call and the best tone are heard (so tone-only play is always solvable). */
inline Crossing GenerateV2(Rng& R, Difficulty D, int Round)
{
	Crossing C;
	if (Round == 0)
	{
		C.Count = 1;
		C.Seg[0].H = static_cast<Habitat>(R.Below(HabitatCount));
		C.Seg[0].LengthM = 10 * (2 + R.Below(5));
		return C;
	}
	const int Base = D == Difficulty::Easy ? 1 : (D == Difficulty::Normal ? 2 : 3);
	C.Count = Base + (Round >= 3 ? 1 : 0);
	const int MaxSteps = 4 + 2 * Round;  // 6, 8, 10, 12 steps of 10 m
	for (int I = 0; I < C.Count; ++I)
	{
		C.Seg[I].H = static_cast<Habitat>(R.Below(HabitatCount));
		C.Seg[I].LengthM = 10 * (1 + R.Below(MaxSteps));
	}
	const int W = R.Below(4);
	C.Air = W < 2 ? Wind::Calm : static_cast<Wind>(W - 1);
	C.Chorus = R.Below(Bands + 1) - 1;  // none 1/7, else one band
	for (int Guard = 0; Guard < 64 && (C.TotalM() > MaxTotalM || Best(C).Snr < HeardSnr || BestTone(C).Snr < HeardSnr); ++Guard)
	{
		int L = 0;
		for (int I = 1; I < C.Count; ++I) if (C.Seg[I].LengthM > C.Seg[L].LengthM) L = I;
		if (C.Seg[L].LengthM <= 10) break;
		C.Seg[L].LengthM -= 10;
	}
	return C;
}

/** V2 score, 0..100 in partial-credit tiers by how far the call falls short of the best (the best tone in tone-only
 *  play): best 100, within 1 dB 90, within 3 dB 75, within 6 dB 50, heard 25, not heard 0. Coarse steps reward a
 *  near miss clearly instead of V1's point-per-0.1-dB slope. */
inline int ScoreV2(const Crossing& C, int Band, Form F, bool ToneOnly = false)
{
	if (Band < 0 || Band >= Bands || (ToneOnly && F == Form::Trill)) return 0;
	const int S = SnrTenths(C, Band, F);
	if (S < HeardSnr) return 0;
	const int Short = (ToneOnly ? BestTone(C) : Best(C)).Snr - S;
	return Short <= 0 ? 100 : (Short <= 10 ? 90 : (Short <= 30 ? 75 : (Short <= 60 ? 50 : 25)));
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
	Ruleset Rules = Ruleset::V1;
	/** Accessibility: tone-only play for listeners who find fast trills hard to hear or tell apart. Trills are refused
	 *  and rounds are scored against the best tone. Needs V2 (every V2 crossing is tone-solvable), so it selects V2. */
	bool ToneOnly = false;
	Crossing Rounds_[Rounds];
	int Scores[Rounds] = {};
	int Index = 0;

	static Game Begin(std::uint64_t Seed, Difficulty Level, Ruleset Rs = Ruleset::V1, bool TonesOnly = false)
	{
		Game G;
		G.D = Level;
		G.ToneOnly = TonesOnly;
		if (TonesOnly) Rs = Ruleset::V2;
		G.Rules = Rs;
		Rng R(Seed);
		for (int I = 0; I < Rounds; ++I) G.Rounds_[I] = Rs == Ruleset::V1 ? Generate(R, Level) : GenerateV2(R, Level, I);
		return G;
	}
	bool Over() const { return Index >= Rounds; }
	const Crossing& Current() const { return Rounds_[Index < Rounds ? Index : Rounds - 1]; }
	/** Plays the current round; returns its score, or -1 if the game is over, the band is invalid, or a trill is
	 *  played in tone-only mode. */
	int Choose(int Band, Form F)
	{
		if (Over() || Band < 0 || Band >= Bands || (ToneOnly && F == Form::Trill)) return -1;
		const int S = Rules == Ruleset::V1 ? Score(Rounds_[Index], Band, F) : ScoreV2(Rounds_[Index], Band, F, ToneOnly);
		Scores[Index++] = S;
		return S;
	}
	int Total() const { int T = 0; for (int I = 0; I < Index; ++I) T += Scores[I]; return T; }
};

}} // namespace daedalus::shardsong
