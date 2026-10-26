// SPDX-License-Identifier: MIT
#pragma once
// Portable consumer of Astra's AUD 1 / canonical Java CallSynth contract.
// No network or engine work occurs here. A failed decode/render leaves the output unchanged.

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace daedalus { namespace audio {

constexpr std::size_t MaxBody = 4096;
constexpr std::size_t MaxLine = 512;
constexpr std::size_t MaxLayers = 16;
constexpr std::size_t MaxId = 64;
constexpr int SampleRate = 22050;
// 8 * (1000 * 22050 / 1000) + 7 * (230 * 22050 / 1000).
constexpr std::size_t MaxSamples = 211897;

// Single-owner/game-thread state: at most one HTTP request, no generation reuse after overflow.
class RequestFence
{
	std::uint64_t Generation;
	bool InFlight = false;
public:
	explicit RequestFence(std::uint64_t InitialGeneration = 0) : Generation(InitialGeneration) { }
	bool Begin(std::uint64_t& Out)
	{
		if (InFlight || Generation == std::numeric_limits<std::uint64_t>::max()) return false;
		Out = ++Generation; InFlight = true; return true;
	}
	bool IsCurrent(std::uint64_t Value) const { return InFlight && Value != 0 && Value == Generation; }
	bool Complete(std::uint64_t Value)
	{
		if (!IsCurrent(Value)) return false;
		InFlight = false; return true;
	}
	void Invalidate()
	{
		InFlight = false;
		if (Generation != std::numeric_limits<std::uint64_t>::max()) ++Generation;
	}
	bool Busy() const { return InFlight; }
	std::uint64_t Current() const { return Generation; }
};

// A response-stream delegate must feed chunks here rather than first buffering an unbounded body.
class BoundedBody
{
	std::string Data;
	bool Rejected = false;
public:
	bool Append(const char* Chunk, std::size_t Size)
	{
		if (Rejected) return false;
		if (Size > MaxBody - Data.size() || (Size != 0 && Chunk == nullptr)) { Rejected = true; return false; }
		if (Size != 0) Data.append(Chunk, Size);
		return true;
	}
	const std::string& Body() const { return Data; }
	bool Failed() const { return Rejected; }
	void Reset() { Data.clear(); Rejected = false; }
};

struct Layer
{
	std::string Id;
	double Gain = 0, LowpassHz = 3000, Density = 0;
};

struct CallSpec
{
	double BaseHz = 70, Sweep = 0;
	int Harmonics = 1;
	double Brightness = 0;
	int Pulses = 1, PulseMs = 1, GapMs = 0;
	double VibratoHz = 3, VibratoDepth = 0, Breath = 0;
};

struct Design
{
	std::string MusicCue;
	std::vector<Layer> Layers;
	CallSpec Call;
};

inline bool MusicCue(std::string_view Cue)
{
	constexpr std::string_view Cues[] = {"FIELD", "TOWN", "CASTLE", "CAVE", "BATTLE", "BOSS", "VICTORY", "DEFEAT", "INN"};
	for (std::string_view Value : Cues) if (Cue == Value) return true;
	return false;
}

// Complete only the matching active request. HTTP callback generations are fenced by the engine owner.
// Cue refreshes coalesce to one latest pending value, and never restart unchanged music.
class CueRoutePolicy
{
	std::string Flight, Pending, LastIssued;
public:
	bool Offer(std::string_view Cue, std::string& OutToSend)
	{
		if (!MusicCue(Cue)) return false;
		if (!Flight.empty())
		{
			if (Cue == Flight) Pending.clear();
			else Pending = std::string(Cue);
			return false;
		}
		if (Cue == LastIssued) return false;
		Flight = std::string(Cue);
		LastIssued = Flight;
		OutToSend = Flight;
		return true;
	}
	bool Complete(bool Success, std::string& OutNext)
	{
		if (Flight.empty()) return false;
		if (!Success) LastIssued.clear(); // Same-cue retries require a later explicit refresh.
		Flight.clear();
		if (Pending.empty()) return false;
		const std::string Latest = std::move(Pending);
		Pending.clear();
		return Offer(Latest, OutNext);
	}
	void Reset() { Flight.clear(); Pending.clear(); LastIssued.clear(); }
	bool Busy() const { return !Flight.empty(); }
	const std::string& InFlightCue() const { return Flight; }
	const std::string& PendingCue() const { return Pending; }
};

namespace detail {

inline bool Digit(char C) { return C >= '0' && C <= '9'; }

inline bool Identifier(std::string_view Value)
{
	if (Value.empty() || Value.size() > MaxId) return false;
	for (char C : Value)
		if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || Digit(C) || C == '_' || C == '-' || C == '.')) return false;
	return true;
}

// Canonical wire numbers have exactly three decimals; parse integers manually so locale cannot matter.
inline bool Fixed3(std::string_view Text, double& Out)
{
	bool Negative = false;
	std::size_t Start = 0;
	if (!Text.empty() && Text.front() == '-') { Negative = true; Start = 1; }
	const std::size_t Dot = Text.find('.', Start);
	if (Dot == std::string_view::npos || Dot == Start || Text.size() - Dot != 4) return false;
	if (Dot - Start > 1 && Text[Start] == '0') return false;
	int Whole = 0, Fraction = 0;
	for (std::size_t I = Start; I < Dot; ++I)
	{
		if (!Digit(Text[I]) || Whole > 100000) return false;
		Whole = Whole * 10 + Text[I] - '0';
	}
	for (std::size_t I = Dot + 1; I < Text.size(); ++I)
	{
		if (!Digit(Text[I])) return false;
		Fraction = Fraction * 10 + Text[I] - '0';
	}
	const double Value = static_cast<double>(Whole) + static_cast<double>(Fraction) / 1000.0;
	Out = Negative ? -Value : Value;
	return true;
}

inline bool Integer(std::string_view Text, int& Out)
{
	if (Text.empty() || (Text.size() > 1 && Text.front() == '0')) return false;
	int Value = 0;
	for (char C : Text)
	{
		if (!Digit(C) || Value > 10000) return false;
		Value = Value * 10 + C - '0';
	}
	Out = Value;
	return true;
}

inline bool Range(double Value, double Low, double High)
{
	return std::isfinite(Value) && Value >= Low && Value <= High;
}

inline bool Tokens(std::string_view Line, std::vector<std::string_view>& Out)
{
	std::size_t Start = 0;
	while (Start < Line.size())
	{
		const std::size_t Space = Line.find(' ', Start);
		const std::size_t End = Space == std::string_view::npos ? Line.size() : Space;
		if (Start == End || Out.size() >= 16) return false;
		Out.push_back(Line.substr(Start, End - Start));
		if (End == Line.size()) return true;
		Start = End + 1;
	}
	return false; // Empty line or trailing space.
}

inline bool Field(std::string_view Token, std::string_view Key, std::string_view& Value)
{
	if (Token.size() <= Key.size() + 1 || Token.substr(0, Key.size()) != Key || Token[Key.size()] != '=') return false;
	Value = Token.substr(Key.size() + 1);
	return true;
}

inline bool CallLine(const std::vector<std::string_view>& T, CallSpec& Call)
{
	if (T.size() != 12 || T[0] != "PCS" || T[1] != "1") return false;
	constexpr std::string_view Keys[] = {"hz", "sweep", "harm", "bright", "pulses", "pulse_ms", "gap_ms", "vib_hz", "vib_st", "breath"};
	std::string_view V[10];
	for (std::size_t I = 0; I < 10; ++I) if (!Field(T[I + 2], Keys[I], V[I])) return false;
	return Fixed3(V[0], Call.BaseHz) && Fixed3(V[1], Call.Sweep) && Integer(V[2], Call.Harmonics)
		&& Fixed3(V[3], Call.Brightness) && Integer(V[4], Call.Pulses) && Integer(V[5], Call.PulseMs)
		&& Integer(V[6], Call.GapMs) && Fixed3(V[7], Call.VibratoHz) && Fixed3(V[8], Call.VibratoDepth)
		&& Fixed3(V[9], Call.Breath);
}

inline int Hex(char C)
{
	if (C >= '0' && C <= '9') return C - '0';
	if (C >= 'a' && C <= 'f') return C - 'a' + 10;
	if (C >= 'A' && C <= 'F') return C - 'A' + 10;
	return -1;
}

} // namespace detail

inline bool ValidCall(const CallSpec& C)
{
	return detail::Range(C.BaseHz, 70, 5200) && detail::Range(C.Sweep, -1, 1)
		&& C.Harmonics >= 1 && C.Harmonics <= 8 && detail::Range(C.Brightness, 0, 1)
		&& C.Pulses >= 1 && C.Pulses <= 8 && C.PulseMs >= 1 && C.PulseMs <= 1000
		&& C.GapMs >= 0 && C.GapMs <= 230 && detail::Range(C.VibratoHz, 3, 12)
		&& detail::Range(C.VibratoDepth, 0, 0.8) && detail::Range(C.Breath, 0, 0.8);
}

inline bool DecodeAud1(std::string_view Wire, Design& Out, std::string& Error)
{
	if (Wire.empty() || Wire.size() > MaxBody) { Error = "AUD body size outside 1..4096 bytes"; return false; }
	for (unsigned char C : Wire)
		if (C != '\n' && (C < 32 || C > 126)) { Error = "AUD must be printable ASCII and LF"; return false; }
	Design Candidate;
	std::size_t Position = 0, LineNumber = 0;
	int Stage = 0; // header, jukebox, layers/PCS, end, terminal empty lines.
	auto Refuse = [&](const char* Reason)
	{
		Error = "line " + std::to_string(LineNumber) + ": " + Reason;
		return false;
	};
	while (Position < Wire.size())
	{
		const std::size_t LF = Wire.find('\n', Position);
		const std::size_t End = LF == std::string_view::npos ? Wire.size() : LF;
		const std::string_view Line = Wire.substr(Position, End - Position);
		Position = LF == std::string_view::npos ? Wire.size() : LF + 1;
		++LineNumber;
		if (Line.size() > MaxLine) return Refuse("line exceeds 512 bytes");
		if (Stage == 4) { if (!Line.empty()) return Refuse("data after end"); continue; }
		if (Stage == 0)
		{
			if (Line != "AUD 1") return Refuse("unsupported AUD header/version");
			Stage = 1; continue;
		}
		std::vector<std::string_view> T;
		if (!detail::Tokens(Line, T)) return Refuse("empty record or noncanonical spaces");
		if (Stage == 1)
		{
			if (T.size() != 2 || T[0] != "jukebox" || !MusicCue(T[1])) return Refuse("expected supported jukebox cue");
			Candidate.MusicCue = std::string(T[1]); Stage = 2; continue;
		}
		if (Stage == 2 && T[0] == "layer")
		{
			if (T.size() != 5 || !detail::Identifier(T[1]) || Candidate.Layers.size() >= MaxLayers)
				return Refuse("invalid or excessive layer");
			if (!Candidate.Layers.empty() && !(Candidate.Layers.back().Id < T[1])) return Refuse("layer ids must be distinct and sorted");
			Layer L;
			L.Id = std::string(T[1]);
			if (!detail::Fixed3(T[2], L.Gain) || !detail::Fixed3(T[3], L.LowpassHz) || !detail::Fixed3(T[4], L.Density)
				|| !detail::Range(L.Gain, 0, 1) || !detail::Range(L.LowpassHz, 3000, 18000) || !detail::Range(L.Density, 0, 1))
				return Refuse("layer number grammar or range");
			Candidate.Layers.push_back(std::move(L)); continue;
		}
		if (Stage == 2 && T[0] == "PCS")
		{
			if (!detail::CallLine(T, Candidate.Call) || !ValidCall(Candidate.Call)) return Refuse("PCS key grammar or range");
			Stage = 3; continue;
		}
		if (Stage == 3 && Line == "end") { Stage = 4; continue; }
		return Refuse("unknown or out-of-order record");
	}
	if (Stage != 4) { Error = "missing PCS or end record"; return false; }
	Out = std::move(Candidate);
	Error.clear();
	return true;
}

// Hash bytes, not ASCII hex characters. No prefixes/whitespace: this matches the HTTP request contract.
inline bool GenomeSeed(std::string_view GenomeHex, std::uint64_t& Out, std::string& Error)
{
	if (GenomeHex.size() < 2 || GenomeHex.size() > 128 || GenomeHex.size() % 2 != 0)
	{
		Error = "genome must contain 2..128 even ASCII hex digits"; return false;
	}
	std::uint64_t Hash = UINT64_C(0xcbf29ce484222325);
	for (std::size_t I = 0; I < GenomeHex.size(); I += 2)
	{
		const int High = detail::Hex(GenomeHex[I]), Low = detail::Hex(GenomeHex[I + 1]);
		if (High < 0 || Low < 0) { Error = "invalid genome hex digit"; return false; }
		Hash ^= static_cast<std::uint64_t>(High * 16 + Low);
		Hash *= UINT64_C(0x100000001b3);
	}
	Out = Hash; Error.clear(); return true;
}

class SplitMix64
{
	std::uint64_t State;
public:
	explicit SplitMix64(std::uint64_t Seed) : State(Seed) { }
	std::uint64_t NextLong()
	{
		std::uint64_t Z = State += UINT64_C(0x9e3779b97f4a7c15);
		Z = (Z ^ (Z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
		Z = (Z ^ (Z >> 27)) * UINT64_C(0x94d049bb133111eb);
		return Z ^ (Z >> 31);
	}
	double NextDouble() { return static_cast<double>(NextLong() >> 11) * 0x1.0p-53; }
};

inline bool RenderCall(const CallSpec& C, std::uint64_t NoiseSeed, std::vector<std::int16_t>& Out, std::string& Error)
{
	if (!ValidCall(C)) { Error = "invalid PCS bounds before render"; return false; }
	const std::size_t PulseN = static_cast<std::size_t>(C.PulseMs) * SampleRate / 1000;
	const std::size_t GapN = static_cast<std::size_t>(C.GapMs) * SampleRate / 1000;
	const std::size_t Total = static_cast<std::size_t>(C.Pulses) * PulseN + static_cast<std::size_t>(C.Pulses - 1) * GapN;
	if (PulseN == 0 || Total > MaxSamples) { Error = "PCM exceeds fixed render budget"; return false; }
	std::vector<std::int16_t> Candidate(Total, 0);
	SplitMix64 Rng(NoiseSeed);
	constexpr double Pi = 3.141592653589793238462643383279502884;
	constexpr double Nyquist = SampleRate / 2.0;
	std::size_t Position = 0;
	for (int Pulse = 0; Pulse < C.Pulses; ++Pulse)
	{
		double Phase = 0;
		for (std::size_t I = 0; I < PulseN; ++I)
		{
			const double T = static_cast<double>(I) / static_cast<double>(PulseN);
			const double Seconds = static_cast<double>(I) / SampleRate;
			const double Frequency = C.BaseHz * std::pow(2.0, C.Sweep * T)
				* std::pow(2.0, C.VibratoDepth / 12.0 * std::sin(2 * Pi * C.VibratoHz * Seconds));
			Phase += 2 * Pi * Frequency / SampleRate;
			double Tone = 0, Norm = 0;
			for (int Harmonic = 1; Harmonic <= C.Harmonics; ++Harmonic)
			{
				if (Frequency * Harmonic >= Nyquist) break;
				const double Amplitude = std::pow(0.15 + 0.8 * C.Brightness, Harmonic - 1);
				Tone += Amplitude * std::sin(Harmonic * Phase);
				Norm += Amplitude;
			}
			Tone = Norm == 0 ? 0 : Tone / Norm;
			const double Noise = Rng.NextDouble() * 2 - 1;
			const double Envelope = std::sin(Pi * T);
			const double Value = Envelope * ((1 - C.Breath) * Tone + C.Breath * Noise) * 0.8;
			const double Limited = std::max(-1.0, std::min(1.0, Value));
			// Java Math.round is floor(x + .5), including negative half ties.
			Candidate[Position + I] = static_cast<std::int16_t>(std::floor(Limited * 32767.0 + 0.5));
		}
		Position += PulseN + (Pulse < C.Pulses - 1 ? GapN : 0);
	}
	Out = std::move(Candidate); Error.clear(); return true;
}

}} // namespace daedalus::audio
