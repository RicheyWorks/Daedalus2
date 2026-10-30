// SPDX-License-Identifier: MIT
// Ear rule + creature-call designer, plain C++17 for the Unreal binding: a line-for-line port of the Java reference
// com.daedalus.world.audio.EarRule and CallSynth (design, earSafe, designEarSafe, peakHz, earSafePeak,
// designEarSafePeak) and the CallSpec PCS 1 line. No Unreal types, no engine includes, no heap allocation: specs
// are PODs, genomes live in a fixed buffer and ToLine writes into a caller buffer.
// Checked by engines/unreal/core-test/ear_rule_core_test.cpp against ear_rule_parity.txt, which the Java
// EarRuleParityTest writes (300 seeds x every species).
//
// Floating point: build with -ffp-contract=off (MSVC: /fp:precise, the default) so no fused multiply-add changes
// a rounding; the expressions below keep Java's evaluation order. Rounding mirrors Java's Math.round (half up,
// toward +infinity), not std::round (half away from zero), which differs for negative glides.
// The PCM renderer (CallSynth.render) is not ported here; the ear-rule decisions do not depend on it.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>

namespace daedalus { namespace earrule {

/** Highest fundamental any game sound may emit, Hz (EarRule.MAX_FUNDAMENTAL_HZ). */
constexpr double MaxFundamentalHz = 800.0;

/** EarRule.ok: a positive fundamental under the ceiling. */
inline bool Ok(double Hz) { return Hz > 0 && Hz < MaxFundamentalHz; }

/** Species, in Java enum order, with their call ranges in Hz (Species.java). */
enum class Species : std::uint8_t { Songbird, Goat, Bovine, Swine, Fowl, Amphibian, Canid };
constexpr int SpeciesCount = 7;
inline double LowHz(Species S)
{
	static constexpr double L[SpeciesCount] = { 1800, 260, 70, 140, 500, 150, 300 };
	return L[static_cast<int>(S)];
}
inline double HighHz(Species S)
{
	static constexpr double H[SpeciesCount] = { 5200, 700, 220, 480, 1600, 900, 1200 };
	return H[static_cast<int>(S)];
}
inline const char* SpeciesName(Species S)
{
	static const char* const N[SpeciesCount] = { "SONGBIRD", "GOAT", "BOVINE", "SWINE", "FOWL", "AMPHIBIAN", "CANID" };
	return N[static_cast<int>(S)];
}
inline bool SpeciesFromName(const char* Name, Species& Out)
{
	for (int I = 0; I < SpeciesCount; ++I)
	{
		const char* A = SpeciesName(static_cast<Species>(I));
		const char* B = Name;
		while (*A && *A == *B) { ++A; ++B; }
		if (*A == 0 && *B == 0) { Out = static_cast<Species>(I); return true; }
	}
	return false;
}

/** Java Math.round(double) for finite values: floor(x + 0.5) computed without double rounding. */
inline double JavaRound(double X)
{
	const double F = std::floor(X);
	return (X - F) >= 0.5 ? F + 1.0 : F;
}
inline double Round3(double V) { return JavaRound(V * 1000.0) / 1000.0; }

/** Immutable genome bytes (Genome.java): up to MaxBytes, genes read as 0..1 and wrap. */
struct Genome
{
	static constexpr int MaxBytes = 64;
	std::uint8_t Bytes[MaxBytes] = {};
	int Length = 0;

	/** Genome.ofHex: non-empty even-length hex, optional 0x prefix, surrounding spaces; false on bad input. */
	static bool FromHex(const char* Hex, Genome& Out)
	{
		if (!Hex) return false;
		while (*Hex == ' ' || *Hex == '\t' || *Hex == '\n' || *Hex == '\r') ++Hex;
		if (Hex[0] == '0' && (Hex[1] == 'x' || Hex[1] == 'X')) Hex += 2;
		int N = 0;
		while (Hex[N] && Hex[N] != ' ' && Hex[N] != '\t' && Hex[N] != '\n' && Hex[N] != '\r') ++N;
		for (int I = N; Hex[I]; ++I)
			if (Hex[I] != ' ' && Hex[I] != '\t' && Hex[I] != '\n' && Hex[I] != '\r') return false;
		if (N == 0 || N % 2 != 0 || N / 2 > MaxBytes) return false;
		Genome G;
		for (int I = 0; I < N / 2; ++I)
		{
			const int Hi = Digit(Hex[2 * I]), Lo = Digit(Hex[2 * I + 1]);
			if (Hi < 0 || Lo < 0) return false;
			G.Bytes[I] = static_cast<std::uint8_t>(Hi << 4 | Lo);
		}
		G.Length = N / 2;
		Out = G;
		return true;
	}
	double Gene(int I) const
	{
		const int M = ((I % Length) + Length) % Length;
		return Bytes[M] / 255.0;
	}

private:
	static int Digit(char C)
	{
		if (C >= '0' && C <= '9') return C - '0';
		if (C >= 'a' && C <= 'f') return C - 'a' + 10;
		if (C >= 'A' && C <= 'F') return C - 'A' + 10;
		return -1;
	}
};

/** CallSpec: one creature call (the PCS 1 fields). */
struct CallSpec
{
	double BaseHz = 0, Sweep = 0;
	int Harmonics = 1;
	double Brightness = 0;
	int Pulses = 1, PulseMs = 1, GapMs = 0;
	double VibratoHz = 0, VibratoDepth = 0, Breath = 0;

	/** CallSpec's constructor check. */
	bool Valid() const { return BaseHz > 0 && Harmonics >= 1 && Pulses >= 1 && PulseMs >= 1 && GapMs >= 0; }
	int DurationMs() const { return Pulses * PulseMs + (Pulses - 1) * GapMs; }

	/** CallSpec.toLine into Out (needs about 160 bytes); returns snprintf's count. */
	int ToLine(char* Out, int Size) const
	{
		return std::snprintf(Out, static_cast<std::size_t>(Size),
			"PCS 1 hz=%.3f sweep=%.3f harm=%d bright=%.3f pulses=%d pulse_ms=%d gap_ms=%d vib_hz=%.3f vib_st=%.3f breath=%.3f",
			BaseHz, Sweep, Harmonics, Brightness, Pulses, PulseMs, GapMs, VibratoHz, VibratoDepth, Breath);
	}
};

/** Gene slots (CallSynth.G_*). */
enum : int { GPitch = 0, GSweep = 1, GHarm = 2, GBright = 3, GPulses = 4, GPulseLen = 5, GGap = 6, GVib = 7, GBreath = 8 };

/** CallSynth.design: genome -> call inside the species range (log-scale pitch). Same order of operations as Java. */
inline CallSpec Design(Species S, const Genome& G)
{
	const bool Bird = S == Species::Songbird;
	const double Hz = LowHz(S) * std::pow(HighHz(S) / LowHz(S), G.Gene(GPitch));
	CallSpec C;
	C.Sweep = Round3((G.Gene(GSweep) - 0.5) * (Bird ? 2.0 : 0.8));
	C.Harmonics = 1 + static_cast<int>(std::floor(G.Gene(GHarm) * 7.999));
	C.Brightness = Round3(G.Gene(GBright));
	C.Pulses = 1 + static_cast<int>(std::floor(G.Gene(GPulses) * (Bird ? 7.999 : 3.999)));
	const double Big = 1.0 - std::log(Hz / 60.0) / std::log(6000.0 / 60.0);
	C.PulseMs = static_cast<int>(JavaRound(60 + 500 * Big * (0.5 + G.Gene(GPulseLen))));
	C.GapMs = C.Pulses == 1 ? 0 : static_cast<int>(JavaRound(30 + 200 * G.Gene(GGap)));
	const double Vib = G.Gene(GVib);
	const double Breath = G.Gene(GBreath) * (Bird ? 0.3 : 0.8);
	C.Breath = Round3(Breath < 1.0 ? Breath : 1.0);
	C.BaseHz = Round3(Hz);
	C.VibratoHz = Round3(3 + 9 * Vib);
	C.VibratoDepth = Round3(Vib * 0.8);
	return C;
}

/** CallSynth.earSafe: drop the fundamental by whole octaves until EarRule.ok; other fields kept. Needs Valid(). */
inline CallSpec EarSafe(const CallSpec& C)
{
	CallSpec Out = C;
	if (!(C.BaseHz > 0)) return Out;  // Java's CallSpec cannot hold this; refuse rather than loop
	double Hz = C.BaseHz;
	while (!Ok(Hz)) Hz = Round3(Hz / 2);
	Out.BaseHz = Hz;
	return Out;
}
inline CallSpec DesignEarSafe(Species S, const Genome& G) { return EarSafe(Design(S, G)); }

/** CallSynth.peakHz: base x largest upward glide x vibrato crest, the parameters render uses. */
inline double PeakHz(const CallSpec& C)
{
	return C.BaseHz * std::pow(2.0, (C.Sweep > 0 ? C.Sweep : 0.0) + C.VibratoDepth / 12.0);
}

/** CallSynth.earSafePeak: earSafe, then keep dropping whole octaves until the audible peak is under the rule. */
inline CallSpec EarSafePeak(const CallSpec& C)
{
	CallSpec Out = EarSafe(C);
	if (!(Out.BaseHz > 0)) return Out;
	while (!Ok(PeakHz(Out))) Out.BaseHz = Round3(Out.BaseHz / 2);
	return Out;
}
inline CallSpec DesignEarSafePeak(Species S, const Genome& G) { return EarSafePeak(Design(S, G)); }

/** Whole octaves between two bases (Java: Math.round(log(from/to)/log(2))). */
inline int OctaveDrops(const CallSpec& From, const CallSpec& To)
{
	return static_cast<int>(JavaRound(std::log(From.BaseHz / To.BaseHz) / std::log(2.0)));
}

}} // namespace daedalus::earrule
