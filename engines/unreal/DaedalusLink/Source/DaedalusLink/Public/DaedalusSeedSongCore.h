// SPDX-License-Identifier: MIT
// G33 Seed-Song Spring (YTM story ch. 2), plain C++17 for the Unreal binding. A port of daedalus-core
// world/brew/story/{SeedSongSpring,ScratchedRecord,SpringChain,KeeperLines}.java plus the QuestProgress twin, with no
// Unreal types. The bench brew itself stays in ADaedalusBrewBench (#285 parity): the caller passes its outcome in.
// Byte parity with Java goes through engines/unreal/core-test/seed_song_parity.txt (SeedSongParityTest).
#pragma once
#include "DaedalusTemperForgeCore.h" // daedalus::forge::SplitRng (java.util.SplittableRandom)
#include <cstdint>
#include <cstdio>
#include <set>
#include <string>
#include <vector>

namespace daedalus { namespace seedsong {

constexpr int MinHerbs = 3, RecordsForQuest = 3, MaxSprings = 32, MaxEventId = 128;
inline const char* QuestId() { return "q_seed_song_spring"; }
inline const char* Keeper() { return "keeper_oriel"; }
inline const char* Water() { return "water"; }
inline const char* RawWater() { return "raw_water"; }

/** One row of engines/unreal/ytm-island/found_tunes.csv (the columns the chapter reads). */
struct Tune { std::string Name, SeedSong; std::vector<std::string> Herbs; std::vector<int> Notes; std::string LearnedFrom; };

inline std::vector<std::string> Split(const std::string& S, char D)
{
	std::vector<std::string> Out; std::string Cur;
	for (char C : S) { if (C == D) { Out.push_back(Cur); Cur.clear(); } else Cur += C; }
	Out.push_back(Cur);
	return Out;
}

/** FoundTune.parseCsv: header line, then 9 columns; returns false on a malformed row. */
inline bool ParseTunes(const std::string& Text, std::vector<Tune>& Out)
{
	Out.clear();
	std::string T; for (char C : Text) if (C != '\r') T += C;
	const std::vector<std::string> Lines = Split(T, '\n');
	for (size_t I = 1; I < Lines.size(); ++I)
	{
		if (Lines[I].find_first_not_of(" \t") == std::string::npos) continue;
		const std::vector<std::string> C = Split(Lines[I], ',');
		if (C.size() != 9) return false;
		Tune U; U.Name = C[0]; U.SeedSong = C[1]; U.Herbs = Split(C[2], '|'); U.LearnedFrom = C[8];
		for (const std::string& N : Split(C[3], '|')) U.Notes.push_back(std::stoi(N));
		Out.push_back(U);
	}
	return true;
}

/** java.lang.String.hashCode for the ASCII tune names. */
inline int32_t JavaHash(const std::string& S)
{
	uint32_t H = 0;
	for (unsigned char C : S) H = 31u * H + C;
	return static_cast<int32_t>(H);
}

inline std::string Lower(std::string S) { for (char& C : S) if (C >= 'A' && C <= 'Z') C = static_cast<char>(C - 'A' + 'a'); return S; }

/** ScratchedRecord: the scratch eats the last {@code Missing} notes (1..2, leaving 2+). */
struct Record
{
	const Tune* T = nullptr; int Missing = 0;
	const std::string& Item() const { return T->LearnedFrom; }
	std::vector<std::string> Heard() const { return std::vector<std::string>(T->Herbs.begin(), T->Herbs.end() - Missing); }
	bool ComesHome() const { return T->Notes.front() == T->Notes.back(); }
	bool RestoredBy(const std::vector<std::string>& Herbs) const
	{
		if (Herbs.size() != T->Herbs.size()) return false;
		for (size_t I = 0; I < Herbs.size(); ++I) if (Lower(Herbs[I]) != Lower(T->Herbs[I])) return false;
		return true;
	}
};

/** ScratchedRecord.of; false where Java throws (fewer than 3 herbs). */
inline bool MakeRecord(const Tune& T, int64_t Seed, Record& Out)
{
	const int N = static_cast<int>(T.Herbs.size());
	if (N < MinHerbs) return false;
	const int Max = N - 2 < 2 ? N - 2 : 2;
	forge::SplitRng Rng(Seed ^ static_cast<int64_t>(JavaHash(T.Name)));
	Out.T = &T; Out.Missing = 1 + Rng.NextInt(Max);
	return true;
}

struct Spring { std::string Id, Name; int Yield; };
enum class DrawOutcome : int { Clean = 0, Cloudy, Duplicate, UnknownSpring, Ignored };
inline const char* DrawName(DrawOutcome O) { static const char* const N[] = { "CLEAN", "CLOUDY", "DUPLICATE", "UNKNOWN_SPRING", "IGNORED" }; return N[static_cast<int>(O)]; }
struct Draw { DrawOutcome Outcome; std::string Item; int Amount; };

inline bool BadEvent(const std::string& E) { return E.find_first_not_of(" \t\n\r\f\v") == std::string::npos || E.size() > static_cast<size_t>(MaxEventId); }

/** SpringChain: restored tunes purify the springs in order; a draw yields clean or raw water. */
struct Chain
{
	std::vector<Spring> Springs; std::vector<std::string> PurifiedBy; std::set<std::string> Events;
	static Chain Island()
	{
		static const char* const Names[] = { "Homestead Well", "Reed Seep", "Ferry Steps", "Goat Ledge", "Old Ark Keel", "Bell Hollow",
			"Mist Stair", "Lantern Pool", "Broken Choir", "Cloudfoot", "Needle Falls", "Summit Basin" };
		Chain C;
		for (int I = 0; I < 12; ++I) C.Springs.push_back({ "spring_" + std::to_string(I + 1), Names[I], 4 + I / 3 });
		C.PurifiedBy.assign(C.Springs.size(), std::string());
		return C;
	}
	int Index(const std::string& Id) const { for (size_t I = 0; I < Springs.size(); ++I) if (Springs[I].Id == Id) return static_cast<int>(I); return -1; }
	bool Clean(const std::string& Id) const { const int I = Index(Id); return I >= 0 && !PurifiedBy[I].empty(); }
	int CleanCount() const { int N = 0; for (const std::string& P : PurifiedBy) N += !P.empty(); return N; }
	const Spring* NextCloudy() const { for (size_t I = 0; I < Springs.size(); ++I) if (PurifiedBy[I].empty()) return &Springs[I]; return nullptr; }
	const Spring* PurifyNext(const std::string& TuneName)
	{
		const Spring* S = NextCloudy();
		if (S) PurifiedBy[Index(S->Id)] = TuneName;
		return S;
	}
	/** The caller adds Item x Amount to the plot store on CLEAN or CLOUDY. */
	Draw DrawAt(const std::string& EventId, const std::string& SpringId)
	{
		if (BadEvent(EventId)) return { DrawOutcome::Ignored, "", 0 };
		const int I = Index(SpringId);
		if (I < 0) return { DrawOutcome::UnknownSpring, "", 0 };
		if (!Events.insert(EventId).second) return { DrawOutcome::Duplicate, "", 0 };
		const bool C = !PurifiedBy[I].empty();
		return { C ? DrawOutcome::Clean : DrawOutcome::Cloudy, C ? Water() : RawWater(), Springs[I].Yield };
	}
};

/** QuestProgress twin for the chapter's three steps: restore 3 records, draw clean once, talk to Keeper Oriel. */
struct Quest
{
	struct Step { const char* Type; const char* Target; int Required; };
	Step Steps[3] = { { "restore", "seed_song_record", RecordsForQuest }, { "draw_clean", "spring", 1 }, { "talk", "keeper_oriel", 1 } };
	std::set<std::string> Seen; int Current = 0, Count = 0;
	bool Complete() const { return Current == 3; }
	const Step* CurrentStep() const { return Complete() ? nullptr : &Steps[Current]; }
	void Apply(const std::string& EventId, const std::string& Type, const std::string& Target)
	{
		if (EventId.empty() || EventId.size() > static_cast<size_t>(MaxEventId) || Seen.count(EventId) || Complete()) return;
		if (Type != Steps[Current].Type || Target != Steps[Current].Target || Seen.size() >= 512) return;
		Seen.insert(EventId);
		if (++Count == Steps[Current].Required) { ++Current; Count = 0; }
	}
};

/** What ADaedalusBrewBench reported for the restoration brew (BrewBench.Outcome). */
enum class BrewOutcome : int { Brewed = 0, Duplicate, MissingHerbs, Ignored };
enum class Outcome : int { Restored = 0, NeedleSkips, NoRecord, AlreadyRestored, UnknownRecord, MissingHerbs, Duplicate, Ignored };
inline const char* OutcomeName(Outcome O)
{
	static const char* const N[] = { "RESTORED", "NEEDLE_SKIPS", "NO_RECORD", "ALREADY_RESTORED", "UNKNOWN_RECORD", "MISSING_HERBS", "DUPLICATE", "IGNORED" };
	return N[static_cast<int>(O)];
}
struct Restore { Outcome Result; const Record* Rec; const Spring* Purified; };
struct Tally { int Restored, Skipped, SpringsPurified, CleanDraws; };

/** SeedSongSpring: one chapter on one homestead. Tunes must outlive the chapter. */
struct Chapter
{
	std::vector<Record> Records; Chain Springs; Quest Q; std::set<std::string> RestoredItems, Events; int Skipped = 0, CleanDraws = 0;

	Chapter(const std::vector<Tune>& Tunes, Chain C, int64_t Seed) : Springs(std::move(C))
	{
		for (const Tune& T : Tunes)
		{
			Record R; if (!MakeRecord(T, Seed, R)) continue;
			bool Replaced = false; // LinkedHashMap.put keeps the first slot, takes the new value
			for (Record& E : Records) if (E.Item() == R.Item()) { E = R; Replaced = true; }
			if (!Replaced) Records.push_back(R);
		}
	}
	const Record* Find(const std::string& Item) const { for (const Record& R : Records) if (R.Item() == Item) return &R; return nullptr; }
	bool IsRestored(const std::string& Item) const { return RestoredItems.count(Item) > 0; }
	Tally GetTally() const { return { static_cast<int>(RestoredItems.size()), Skipped, Springs.CleanCount(), CleanDraws }; }

	/** Before the bench: Java returns early (no brew) for these. Ignored here means "go ahead and brew". */
	Outcome PreCheck(const std::string& EventId, const std::string& Item, bool HasRecord) const
	{
		if (BadEvent(EventId)) return Outcome::Ignored;
		if (Events.count(EventId)) return Outcome::Duplicate;
		if (!Find(Item)) return Outcome::UnknownRecord;
		if (IsRestored(Item)) return Outcome::AlreadyRestored;
		if (!HasRecord) return Outcome::NoRecord;
		return Outcome::Restored; // = may brew
	}

	/** restore(): call PreCheck first; brew on the bench only when it says Restored, then pass the bench outcome here.
	 *  On Restored the caller plays the record on the jukebox (BrewBench.playRecord). */
	Restore Apply(const std::string& EventId, const std::string& Item, const std::vector<std::string>& Herbs, bool HasRecord, BrewOutcome Brew)
	{
		const Outcome Pre = PreCheck(EventId, Item, HasRecord);
		const Record* R = Find(Item);
		if (Pre != Outcome::Restored) return { Pre, Pre == Outcome::AlreadyRestored || Pre == Outcome::NoRecord ? R : nullptr, nullptr };
		if (Brew == BrewOutcome::MissingHerbs) return { Outcome::MissingHerbs, R, nullptr };
		if (Brew == BrewOutcome::Duplicate) return { Outcome::Duplicate, R, nullptr };
		if (Brew == BrewOutcome::Ignored) return { Outcome::Ignored, R, nullptr };
		Events.insert(EventId);
		if (!R->RestoredBy(Herbs)) { ++Skipped; return { Outcome::NeedleSkips, R, nullptr }; }
		RestoredItems.insert(Item);
		const Spring* S = Springs.PurifyNext(R->T->Name);
		Q.Apply(EventId, "restore", "seed_song_record");
		return { Outcome::Restored, R, S };
	}

	Draw DrawAt(const std::string& EventId, const std::string& SpringId)
	{
		Draw D = Springs.DrawAt(EventId, SpringId);
		if (D.Outcome == DrawOutcome::Clean) { ++CleanDraws; Q.Apply(EventId, "draw_clean", "spring"); }
		return D;
	}

	std::string Talk(const std::string& EventId);
};

// KeeperLines
inline const char* Greeting() { return "The arks sang these records into the seed vaults. The shattering scratched every one. Bring me a record and brew what it can't sing."; }
inline const char* DrinkLine() { return "Three songs mended. Go and drink from a clean spring, then come tell me."; }
inline const char* Thanks() { return "You hear that? The springs are humming the old tunes back. The arks would be proud. Keep the choir: every record you mend wakes another spring."; }
inline const char* AllClean() { return "Every spring on the island runs clean. The choir is whole."; }

inline std::string KeeperLine(const Chapter& C)
{
	const Tally T = C.GetTally();
	if (T.Restored == 0) return Greeting();
	if (!C.Springs.NextCloudy()) return AllClean();
	const Quest::Step* S = C.Q.CurrentStep();
	if (S && std::string(S->Type) == "draw_clean") return DrinkLine();
	std::string Last;
	for (const Spring& Sp : C.Springs.Springs) if (C.Springs.Clean(Sp.Id)) Last = Sp.Name;
	return "The water at " + Last + " runs clear again. " + std::to_string(T.Restored) + " of " + std::to_string(C.Records.size()) + " records sing whole.";
}

inline std::string Chapter::Talk(const std::string& EventId)
{
	const Quest::Step* Due = Q.CurrentStep();
	if (Due && std::string(Due->Type) == "talk") { Q.Apply(EventId, "talk", Keeper()); return Thanks(); }
	return KeeperLine(*this);
}

inline std::string Hint(const Record& R)
{
	std::string Heard;
	for (const std::string& H : R.Heard()) Heard += (Heard.empty() ? "" : ", ") + H;
	return "This is " + R.T->SeedSong + ". I hear " + Heard + ", then the scratch eats " + std::to_string(R.Missing) + " note" + (R.Missing == 1 ? "" : "s") + "." +
		(R.ComesHome() ? " It wants to come home: it ends on the note it began with." : " It does not come home; it ends somewhere new.");
}

}} // namespace daedalus::seedsong
