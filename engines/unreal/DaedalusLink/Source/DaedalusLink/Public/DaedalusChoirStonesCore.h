// SPDX-License-Identifier: MIT
// G53 Choir Stones (YTM story ch. 4), plain C++17 for the Unreal binding. A port of daedalus-core
// world/brew/stones/{BridgeLedger,ChoirStones,MasonLines}.java plus the QuestProgress twin, on the G46 shelf
// (DaedalusRecordHuntCore.h). The caller owns the plot store: it says whether the record is restored (G33 chapter)
// and whether a blank stone / two ropes are in store, and takes them when the call succeeds.
// Byte parity with Java goes through engines/unreal/core-test/choir_stones_parity.txt (ChoirStonesParityTest).
#pragma once
#include "DaedalusRecordHuntCore.h"
#include <algorithm>
#include <cstdint>
#include <deque>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace daedalus { namespace stones {

constexpr int MaxStrength = 3, RopePerBridge = 2;
inline const char* QuestId() { return "q_choir_stones"; }
inline const char* Mason() { return "mason_hale"; }
inline const char* Rope() { return "rope"; }
inline const char* Stone() { return "choir_stone_blank"; }

using Bridge = std::pair<int, int>; // (min, max); std::map orders it like Java's Bridge.compareTo
inline Bridge BridgeOf(int X, int Y) { return { std::min(X, Y), std::max(X, Y) }; }

/** BridgeLedger: every bridge starts at strength 3; 0 = snapped. */
struct Ledger
{
	const hunt::FragmentMap* Map = nullptr; std::map<Bridge, int> Strength;
	explicit Ledger(const hunt::FragmentMap& M) : Map(&M)
	{
		for (int A = 0; A < M.Size(); ++A) for (int B : M.Links[A]) if (A < B) Strength[{ A, B }] = MaxStrength;
	}
	int StrengthOf(int X, int Y) const { const auto It = Strength.find(BridgeOf(X, Y)); return It == Strength.end() ? -1 : It->second; }
	bool Intact(int X, int Y) const { return StrengthOf(X, Y) > 0; }
	/** True when this fray snapped it. */
	bool Fray(const Bridge& B) { int& S = Strength[B]; if (S == 0) return false; --S; return S == 0; }
	/** The caller takes 2 rope when this returns true. */
	bool Restring(int X, int Y, bool HasRope)
	{
		const int S = StrengthOf(X, Y);
		if (S < 0 || S == MaxStrength || !HasRope) return false;
		Strength[BridgeOf(X, Y)] = MaxStrength;
		return true;
	}
	std::vector<int> CutOff() const
	{
		std::vector<bool> Seen(Map->Size(), false); Seen[hunt::Home] = true;
		std::deque<int> Q{ hunt::Home };
		while (!Q.empty()) { const int U = Q.front(); Q.pop_front(); for (int V : Map->Links[U]) if (!Seen[V] && Intact(U, V)) { Seen[V] = true; Q.push_back(V); } }
		std::vector<int> Out; for (int F = 0; F < Map->Size(); ++F) if (!Seen[F]) Out.push_back(F);
		return Out;
	}
	std::vector<Bridge> IntactBridges() const { std::vector<Bridge> O; for (const auto& P : Strength) if (P.second > 0) O.push_back(P.first); return O; }
};

enum class Outcome : int { Carved = 0, NotRestored, RecordUsed, FragmentTaken, NoStone, UnknownFragment, Duplicate, Ignored };
inline const char* OutcomeName(Outcome O)
{
	static const char* const N[] = { "CARVED", "NOT_RESTORED", "RECORD_USED", "FRAGMENT_TAKEN", "NO_STONE", "UNKNOWN_FRAGMENT", "DUPLICATE", "IGNORED" };
	return N[static_cast<int>(O)];
}
struct StoneRec { int Fragment; std::string Record; int Range; };
struct Night { bool Valid = false; int N = 0; std::vector<Bridge> Frayed, Snapped; std::vector<int> CutOff; bool Held = false; };

inline int Range(int Tier) { return std::max(1, std::min(4, Tier)) / 2 + 1; }
inline int FraysPerNight(int N) { return 1 + N / 4; }

struct Choir
{
	Ledger L; int64_t Seed; std::vector<StoneRec> Stones; std::set<std::string> CarvedRecords, Events; hunt::Quest Q;
	int LastNight = 0, HeldNights = 0; Night Last;

	Choir(const hunt::FragmentMap& M, int64_t S) : L(M), Seed(S)
	{
		Q.Steps = { { "carve", "choir_stone", 2 }, { "hold", "night", 3 }, { "talk", Mason(), 1 } };
	}
	const StoneRec* StoneAt(int F) const { for (const StoneRec& S : Stones) if (S.Fragment == F) return &S; return nullptr; }

	/** The caller takes one blank stone on CARVED. */
	Outcome Carve(const std::string& EventId, int Fragment, const std::string& Record, int Tier, bool Restored, bool HasStone)
	{
		if (hunt::BadEvent(EventId)) return Outcome::Ignored;
		if (Events.count(EventId)) return Outcome::Duplicate;
		if (Fragment < 0 || Fragment >= L.Map->Size()) return Outcome::UnknownFragment;
		if (!Restored) return Outcome::NotRestored;
		if (CarvedRecords.count(Record)) return Outcome::RecordUsed;
		if (StoneAt(Fragment)) return Outcome::FragmentTaken;
		if (!HasStone) return Outcome::NoStone;
		Events.insert(EventId); CarvedRecords.insert(Record);
		Stones.push_back({ Fragment, Record, Range(Tier) });
		Q.Apply(EventId, "carve", "choir_stone");
		return Outcome::Carved;
	}
	bool Humming(const Bridge& B) const
	{
		for (const StoneRec& S : Stones)
		{
			const int D = std::min(L.Map->Distance(S.Fragment, B.first), L.Map->Distance(S.Fragment, B.second));
			if (D < S.Range) return true;
		}
		return false;
	}
	/** Night n's seeded tremor; Valid=false for a night already shaken (Java returns null). */
	Night Shake(int N)
	{
		Night Out;
		if (N <= LastNight) return Out;
		LastNight = N;
		forge::SplitRng Rng(Seed * 1000003LL + N);
		const int K = FraysPerNight(L.Map->Size());
		for (int I = 0; I < K; ++I)
		{
			const std::vector<Bridge> Live = L.IntactBridges();
			if (Live.empty()) break;
			const Bridge B = Live[Rng.NextInt(static_cast<int32_t>(Live.size()))];
			if (Humming(B)) continue;
			Out.Frayed.push_back(B);
			if (L.Fray(B)) Out.Snapped.push_back(B);
		}
		Out.CutOff = L.CutOff();
		Out.Held = Out.CutOff.empty();
		if (Out.Held) { ++HeldNights; Q.Apply("night-" + std::to_string(N), "hold", "night"); }
		Out.Valid = true; Out.N = N; Last = Out;
		return Out;
	}
	std::string Talk(const std::string& EventId);
};

// MasonLines
inline const char* Greeting() { return "Feel that? The shelf shakes every night, and the ropes can't take it forever. Bring me a song you've mended and a blank stone, and I'll make it hum."; }
inline const char* OneStone() { return "One stone humming. One more and the ropes near it might just hold."; }
inline const char* Thanks() { return "Three nights and not one fragment lost. The stones remember what the arks sang. Take this chisel; it's yours now."; }
inline std::string Holding(int H) { return "The ropes held " + std::to_string(H) + " night" + (H == 1 ? "" : "s") + ". Keep the stones singing."; }

inline std::string MasonLine(const Choir& C)
{
	if (C.Stones.empty()) return Greeting();
	if (C.Last.Valid && !C.Last.Held)
	{
		const int K = static_cast<int>(C.Last.CutOff.size());
		return "Last night's shake cut off " + std::to_string(K) + " fragment" + (K == 1 ? "" : "s") + ". Re-string the snapped ropes, and put a stone where the shaking keeps winning.";
	}
	if (!C.Last.Valid) return C.Stones.size() == 1 ? std::string(OneStone()) : Holding(0);
	return Holding(C.HeldNights);
}

inline std::string Choir::Talk(const std::string& EventId)
{
	const hunt::Quest::Step* Due = Q.CurrentStep();
	if (Due && Due->Type == "talk") { Q.Apply(EventId, "talk", Mason()); return Thanks(); }
	return MasonLine(*this);
}

}} // namespace daedalus::stones