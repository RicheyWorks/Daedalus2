// SPDX-License-Identifier: MIT
// G46 Ark Record Hunt (YTM story ch. 3), plain C++17 for the Unreal binding. A port of daedalus-core
// world/brew/hunt/{FragmentMap,RecordHunt,ArchivistLines}.java plus the QuestProgress twin, with no Unreal types.
// A found record goes into the plot store by the caller (Step::Found). Byte parity with Java goes through
// engines/unreal/core-test/record_hunt_parity.txt (RecordHuntParityTest).
#pragma once
#include "DaedalusTemperForgeCore.h" // daedalus::forge::SplitRng (java.util.SplittableRandom)
#include <algorithm>
#include <cstdint>
#include <deque>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace daedalus { namespace hunt {

constexpr int MinFragments = 4, MaxFragments = 64, Home = 0, RecordsForQuest = 3, MaxEventId = 128;
inline const char* QuestId() { return "q_ark_record_hunt"; }
inline const char* Archivist() { return "archivist_tamsin"; }

/** The shattered shelf: fragments joined by rope bridges (sorted neighbour sets, like Java's TreeSet). */
struct FragmentMap
{
	std::vector<std::set<int>> Links; std::vector<std::vector<int>> Dist;

	int Size() const { return static_cast<int>(Links.size()); }
	bool Bridged(int A, int B) const { return A >= 0 && A < Size() && Links[A].count(B) > 0; }
	int Distance(int A, int B) const { return Dist[A][B]; }
	void Finish()
	{
		Dist.assign(Links.size(), std::vector<int>());
		for (int S = 0; S < Size(); ++S)
		{
			std::vector<int> D(Links.size(), -1); D[S] = 0;
			std::deque<int> Q{ S };
			while (!Q.empty()) { const int U = Q.front(); Q.pop_front(); for (int V : Links[U]) if (D[V] < 0) { D[V] = D[U] + 1; Q.push_back(V); } }
			Dist[S] = D;
		}
	}
	/** -1 when unreachable (Java throws). */
	int NextStep(int From, int To) const
	{
		if (From == To) return From;
		for (int V : Links[From]) if (Dist[V][To] == Dist[From][To] - 1) return V;
		return -1;
	}
};

/** FragmentMap.seeded; false where Java throws (n outside 4..64). */
inline bool SeededMap(int64_t Seed, int N, FragmentMap& Out)
{
	if (N < MinFragments || N > MaxFragments) return false;
	forge::SplitRng Rng(Seed);
	Out.Links.assign(N, std::set<int>());
	for (int I = 1; I < N; ++I) { const int J = Rng.NextInt(I); Out.Links[I].insert(J); Out.Links[J].insert(I); }
	for (int E = 0; E < N / 4; ++E)
	{
		const int A = Rng.NextInt(N); const int B = Rng.NextInt(N);
		if (A != B) { Out.Links[A].insert(B); Out.Links[B].insert(A); }
	}
	Out.Finish();
	return true;
}

/** FragmentMap.of; false for a bad bridge or a fragment the homestead cannot reach. */
inline bool MapOf(int N, const std::vector<std::pair<int, int>>& Bridges, FragmentMap& Out)
{
	if (N < 1 || N > MaxFragments) return false;
	Out.Links.assign(N, std::set<int>());
	for (const auto& B : Bridges)
	{
		if (B.first == B.second || B.first < 0 || B.second < 0 || B.first >= N || B.second >= N) return false;
		Out.Links[B.first].insert(B.second); Out.Links[B.second].insert(B.first);
	}
	Out.Finish();
	for (int D : Out.Dist[Home]) if (D < 0) return false;
	return true;
}

inline std::string FragmentName(int F)
{
	static const char* const N[] = { "Homestead", "Reed Shelf", "Goat Rock", "Keel Drift", "Bell Ledge", "Mist Step", "Lantern Isle", "Choir Stone",
		"Cloudfoot", "Needle Spur", "Summit Shard", "Ferry Knoll", "Willow Crumb", "Ash Tooth", "Kite Perch", "Hollow Bell" };
	const int L = 16;
	if (F < L) return N[F];
	const int K = F - L;
	return std::string(N[1 + K % (L - 1)]) + " " + std::to_string(2 + K / (L - 1));
}

/** QuestProgress twin (sequential steps, event ids seen once, 512 cap). */
struct Quest
{
	struct Step { std::string Type, Target; int Required; };
	std::vector<Step> Steps; std::set<std::string> Seen; int Current = 0, Count = 0;
	bool Complete() const { return Current == static_cast<int>(Steps.size()); }
	const Step* CurrentStep() const { return Complete() ? nullptr : &Steps[Current]; }
	void Apply(const std::string& EventId, const std::string& Type, const std::string& Target)
	{
		if (EventId.empty() || EventId.size() > static_cast<size_t>(MaxEventId) || Seen.count(EventId) || Complete()) return;
		if (Type != Steps[Current].Type || Target != Steps[Current].Target || Seen.size() >= 512) return;
		Seen.insert(EventId);
		if (++Count == Steps[Current].Required) { ++Current; Count = 0; }
	}
};

enum class Outcome : int { Walked = 0, Found, NothingHere, NoBridge, Tired, Rested, Duplicate, Ignored };
inline const char* OutcomeName(Outcome O)
{
	static const char* const N[] = { "WALKED", "FOUND", "NOTHING_HERE", "NO_BRIDGE", "TIRED", "RESTED", "DUPLICATE", "IGNORED" };
	return N[static_cast<int>(O)];
}
struct Step { Outcome Result; int At; int Stamina; std::vector<std::string> Found; };
struct Hint { bool Valid = false; std::string Record; int Distance = 0; int Toward = 0; };

inline bool BadEvent(const std::string& E) { return E.find_first_not_of(" \t\n\r\f\v") == std::string::npos || E.size() > static_cast<size_t>(MaxEventId); }

struct RecordHunt
{
	const FragmentMap* Map = nullptr; int StaminaPerDay = 0;
	std::vector<std::pair<std::string, int>> Where; // LinkedHashMap order
	std::set<std::string> FoundSet, Events; Quest Q; int At = Home, Stamina = 0, Day = 0;

	int WhereIs(const std::string& R) const { for (const auto& W : Where) if (W.first == R) return W.second; return -1; }
	int Remaining() const { return static_cast<int>(Where.size() - FoundSet.size()); }

	Step Walk(const std::string& EventId, int To)
	{
		if (BadEvent(EventId)) return { Outcome::Ignored, At, Stamina, {} };
		if (Events.count(EventId)) return { Outcome::Duplicate, At, Stamina, {} };
		if (!Map->Bridged(At, To)) return { Outcome::NoBridge, At, Stamina, {} };
		if (Stamina < 1) return { Outcome::Tired, At, Stamina, {} };
		Events.insert(EventId); --Stamina; At = To;
		if (At == Home && static_cast<int>(FoundSet.size()) >= RecordsForQuest) Q.Apply(EventId, "return", "homestead");
		return { Outcome::Walked, At, Stamina, {} };
	}
	/** The caller adds each Step::Found record x1 to the plot store. */
	Step Search(const std::string& EventId)
	{
		if (BadEvent(EventId)) return { Outcome::Ignored, At, Stamina, {} };
		if (Events.count(EventId)) return { Outcome::Duplicate, At, Stamina, {} };
		if (Stamina < 1) return { Outcome::Tired, At, Stamina, {} };
		Events.insert(EventId); --Stamina;
		std::vector<std::string> Here;
		for (const auto& W : Where) if (W.second == At && !FoundSet.count(W.first)) Here.push_back(W.first);
		for (size_t I = 0; I < Here.size(); ++I) { FoundSet.insert(Here[I]); Q.Apply(EventId + "#" + std::to_string(I), "find_record", "ark_record"); }
		return { Here.empty() ? Outcome::NothingHere : Outcome::Found, At, Stamina, Here };
	}
	Step Rest(int NewDay)
	{
		if (NewDay <= Day) return { Outcome::Duplicate, At, Stamina, {} };
		Day = NewDay; Stamina = StaminaPerDay;
		return { Outcome::Rested, At, Stamina, {} };
	}
	Hint GetHint() const
	{
		Hint Best;
		for (const auto& W : Where)
		{
			if (FoundSet.count(W.first)) continue;
			const int D = Map->Distance(At, W.second);
			if (!Best.Valid || D < Best.Distance) { Best.Valid = true; Best.Record = W.first; Best.Distance = D; Best.Toward = Map->NextStep(At, W.second); }
		}
		return Best;
	}
	std::string Talk(const std::string& EventId);
};

/** RecordHunt constructor; false where Java throws (no records, stamina < 1, duplicate record). Map must outlive the hunt. */
inline bool MakeHunt(const FragmentMap& Map, const std::vector<std::string>& Records, int64_t Seed, int StaminaPerDay, RecordHunt& Out)
{
	if (StaminaPerDay < 1 || Records.empty()) return false;
	Out = RecordHunt();
	Out.Map = &Map; Out.StaminaPerDay = StaminaPerDay; Out.Stamina = StaminaPerDay;
	Out.Q.Steps = { { "find_record", "ark_record", RecordsForQuest }, { "return", "homestead", 1 }, { "talk", Archivist(), 1 } };
	forge::SplitRng Rng(Seed);
	std::vector<int> Pool;
	for (const std::string& R : Records)
	{
		if (Pool.empty()) for (int F = 1; F < Map.Size(); ++F) Pool.push_back(F);
		if (Out.WhereIs(R) >= 0) return false;
		const int K = Rng.NextInt(static_cast<int32_t>(Pool.size()));
		Out.Where.emplace_back(R, Pool[K]);
		Pool.erase(Pool.begin() + K);
	}
	return true;
}

// ArchivistLines
inline const char* Underfoot() { return "It's right here. The needle-hum is under your feet. Search."; }
inline const char* EmptyLine() { return "The crates are empty. Every record is home."; }
inline const char* Thanks() { return "Three records home already. Take them to Keeper Oriel's bench and mend them. I'll keep listening for the rest."; }
inline const char* TiredLine() { return "You're spent. Sleep, and the bridges will still be there tomorrow."; }

inline std::string ArchivistLine(const RecordHunt& H)
{
	const Hint Ht = H.GetHint();
	if (!Ht.Valid) return EmptyLine();
	if (H.Stamina == 0) return TiredLine();
	if (Ht.Distance == 0) return Underfoot();
	const std::string To = FragmentName(Ht.Toward);
	if (Ht.Distance == 1) return "One bridge away. Cross to " + To + ".";
	if (Ht.Distance <= 3) return "Warmer. " + std::to_string(Ht.Distance) + " bridges off; start across to " + To + ".";
	return "Faint, far out on the shelf: " + std::to_string(Ht.Distance) + " bridges. Head for " + To + " and listen again.";
}

inline std::string RecordHunt::Talk(const std::string& EventId)
{
	if (At == Home)
	{
		const Quest::Step* Due = Q.CurrentStep();
		if (Due && Due->Type == "talk") { Q.Apply(EventId, "talk", Archivist()); return Thanks(); }
	}
	return ArchivistLine(*this);
}

}} // namespace daedalus::hunt