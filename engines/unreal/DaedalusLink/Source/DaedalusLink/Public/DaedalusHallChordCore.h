// SPDX-License-Identifier: MIT
// Prismheart hall chord (audio lane, idea PROM-3), plain C++17 for the Unreal binding. A slow ambient chord for the
// arcade hall, built from the low notes of the cabinets being played right now.
//
// Rules (built on cue kit V2, integer only):
// - Input: (cabinet id, token) pairs. Duplicates are removed and the pairs are sorted by (id, token), so input order
//   never matters. Only the 32 lowest keys are considered (fixed storage, no heap for the list).
// - Each cabinet gives one low note: kit = MakeKitV2(id, token); PyRandom seeded "hall|<id>|<token>" picks root, fifth
//   or third (degree 0, 3 or 2, RandRange(3)); the note is halved (integer) until it is at most 330 Hz.
// - In key order: a note equal to an existing voice adds weight to that voice; a note within about a semitone (under 6 %)
//   of another voice clashes and tries an octave down (if >= 82 Hz), then up (if < 700 Hz); else it is dropped.
//   At most 8 voices; later new notes count as over cap.
// - Gain (thousandths): 600 * weight / total weight, at most 200 per voice, so the sum is at most 600.
// - Swell: attack 3000 + 400 per voice ms, release 4000 ms, swell period 12000 ms. Empty hall: a quiet 110 Hz drone
//   (gain 120, attack 6000, swell 16000).
// Every voice goes through EarSafePeak (DaedalusEarRuleCore.h): under 800 Hz, two soft harmonics, low brightness, no sweep.
// Reference: tools/minigames/hall_chord.py writes hall_chord_golden.txt; checked by hall_chord_core_test.cpp.
#pragma once
#include "DaedalusCueKitCore.h"

#include <cstdint>
#include <cstring>
#include <string>

namespace daedalus { namespace hallchord {

constexpr int MaxVoices = 8;
constexpr int MaxCandidates = 32;
constexpr int GainBudget = 600, GainCap = 200;
constexpr int LowCeilHz = 330, LowFloorHz = 82, HighLimitHz = 700;
constexpr int DroneHz = 110, DroneGain = 120;
constexpr int ChordDegrees[3] = { 0, 3, 2 };
static_assert(HighLimitHz < 800, "octave moves must stay under the 800 Hz ear rule");

struct Cabinet { const char* Id = ""; std::uint64_t Token = 0; };
struct Voice { int Hz = 0, Gain = 0; };
struct Chord
{
	Voice V[MaxVoices] = {};
	int Count = 0;
	int AttackMs = 0, ReleaseMs = 0, SwellMs = 0;
	int Dropped = 0, OverCap = 0;
	bool Drone = false;
	int TotalGain() const { int S = 0; for (int I = 0; I < Count; ++I) S += V[I].Gain; return S; }
};

namespace detail {
inline int Cmp(const Cabinet& A, const Cabinet& B)
{
	const int C = std::strcmp(A.Id ? A.Id : "", B.Id ? B.Id : "");
	if (C != 0) return C;
	return A.Token < B.Token ? -1 : (A.Token > B.Token ? 1 : 0);
}
inline bool Clashes(int Hz, const int* Notes, int N)
{
	for (int I = 0; I < N; ++I)
	{
		const int D = Hz > Notes[I] ? Hz - Notes[I] : Notes[I] - Hz;
		const int Lo = Hz < Notes[I] ? Hz : Notes[I];
		if (D != 0 && 100 * D < 6 * Lo) return true;
	}
	return false;
}
}  // namespace detail

/** A cabinet's low chord note. */
inline int LowNote(const char* Id, std::uint64_t Token)
{
	const cuekit::Kit K = cuekit::MakeKitV2(Id, Token);
	pyrandom::PyRandom R(std::string("hall|") + (Id ? Id : "") + "|" + std::to_string(Token));
	int Hz = K.StepHz(ChordDegrees[R.Below(3)]);
	while (Hz > LowCeilHz) Hz /= 2;
	return Hz;
}

inline Chord MakeChord(const Cabinet* In, int N)
{
	Cabinet Keys[MaxCandidates];
	int K = 0;
	for (int I = 0; I < N; ++I)  // keep the lowest unique keys, sorted (insertion)
	{
		int P = 0;
		while (P < K && detail::Cmp(Keys[P], In[I]) < 0) ++P;
		if (P < K && detail::Cmp(Keys[P], In[I]) == 0) continue;
		if (P >= MaxCandidates) continue;
		const int Last = K < MaxCandidates ? K : MaxCandidates - 1;
		for (int J = Last; J > P; --J) Keys[J] = Keys[J - 1];
		Keys[P] = In[I];
		if (K < MaxCandidates) ++K;
	}
	Chord C;
	int Hz[MaxVoices] = {}, W[MaxVoices] = {}, Count = 0;
	for (int I = 0; I < K; ++I)
	{
		const int H = LowNote(Keys[I].Id, Keys[I].Token);
		const int Cand[3] = { H, H / 2 >= LowFloorHz ? H / 2 : 0, H * 2 < HighLimitHz ? H * 2 : 0 };
		bool Placed = false;
		for (int T = 0; T < 3 && !Placed; ++T)
		{
			if (!Cand[T]) continue;
			for (int J = 0; J < Count; ++J) if (Hz[J] == Cand[T]) { ++W[J]; Placed = true; break; }
			if (Placed) break;
			if (!detail::Clashes(Cand[T], Hz, Count))
			{
				if (Count >= MaxVoices) ++C.OverCap;
				else { Hz[Count] = Cand[T]; W[Count] = 1; ++Count; }
				Placed = true;
			}
		}
		if (!Placed) ++C.Dropped;
	}
	if (Count == 0)
	{
		C.V[0].Hz = DroneHz; C.V[0].Gain = DroneGain; C.Count = 1; C.Drone = true;
		C.AttackMs = 6000; C.ReleaseMs = 4000; C.SwellMs = 16000;
		return C;
	}
	int Total = 0;
	for (int I = 0; I < Count; ++I) Total += W[I];
	for (int I = 0; I < Count; ++I)
	{
		int G = GainBudget * W[I] / Total;
		Voice X; X.Hz = Hz[I]; X.Gain = G > GainCap ? GainCap : G;
		int P = C.Count;  // sorted by Hz (unique)
		while (P > 0 && C.V[P - 1].Hz > X.Hz) { C.V[P] = C.V[P - 1]; --P; }
		C.V[P] = X; ++C.Count;
	}
	C.AttackMs = 3000 + 400 * C.Count; C.ReleaseMs = 4000; C.SwellMs = 12000;
	return C;
}

/** The ear-safe call for one voice: two soft harmonics, low brightness, one long pulse, no sweep. */
inline earrule::CallSpec VoiceCall(const Voice& V, const Chord& C)
{
	cuekit::Note N; N.Hz = V.Hz; N.Ms = C.AttackMs + C.ReleaseMs;
	return earrule::EarSafePeak(cuekit::NoteCall(N));
}

}}  // namespace daedalus::hallchord
