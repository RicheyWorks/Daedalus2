// SPDX-License-Identifier: MIT
// G66 The Record Exchange (YTM story ch. 6), plain C++17 for the Unreal binding. A port of daedalus-core
// world/brew/exchange/{Trader,RecordExchange,TraderLines}.java plus the QuestProgress twin, on the G33 tune rows
// (DaedalusSeedSongCore.h). The caller owns the plot store: it says whether the record is restored and whether a
// pressed copy is in store, adds the copy on PRESSED and takes the copy / adds the goods on TRADED.
// Byte parity with Java goes through engines/unreal/core-test/record_exchange_parity.txt (RecordExchangeParityTest).
#pragma once
#include "DaedalusSeedSongCore.h"
#include "DaedalusRecordHuntCore.h" // hunt::Quest, hunt::BadEvent
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace daedalus { namespace exchange {

inline const char* QuestId() { return "q_record_exchange"; }
inline std::string CopyOf(const std::string& Record) { return "Item_YTM_RecordCopy_" + Record; }

struct Trader { std::string Id, Name, Good; int Wants; };
inline std::vector<Trader> Island()
{
	return { { "pell", "Pell the rope-maker", "rope", 2 }, { "ida", "Quarry Ida", "choir_stone_blank", 1 }, { "mora", "Hen-wife Mora", "Egg", 2 }, { "dov", "Fisher Dov", "fish", 2 } };
}

enum class Outcome : int { Pressed = 0, Traded, NotRestored, PressedToday, NoCopy, UnknownTrader, UnknownTune, Refused, Duplicate, Ignored };
inline const char* OutcomeName(Outcome O)
{
	static const char* const N[] = { "PRESSED", "TRADED", "NOT_RESTORED", "PRESSED_TODAY", "NO_COPY", "UNKNOWN_TRADER", "UNKNOWN_TUNE", "REFUSED", "DUPLICATE", "IGNORED" };
	return N[static_cast<int>(O)];
}
struct Trade { Outcome Result; std::string Good; int Amount; bool Wanted; };

struct Exchange
{
	std::vector<std::pair<std::string, const seedsong::Tune*>> TunesByRecord; // LinkedHashMap order
	std::vector<Trader> Traders; int64_t Seed; std::map<std::string, int> Held; std::set<std::string> PressedToday, Events; hunt::Quest Q; int Day = 1;

	/** Tunes must outlive the exchange. */
	Exchange(const std::vector<seedsong::Tune>& Tunes, std::vector<Trader> T, int64_t S) : Seed(S)
	{
		for (const seedsong::Tune& U : Tunes)
		{
			bool Hit = false; for (auto& P : TunesByRecord) if (P.first == U.LearnedFrom) { P.second = &U; Hit = true; }
			if (!Hit) TunesByRecord.emplace_back(U.LearnedFrom, &U);
		}
		for (const Trader& X : T) { bool Hit = false; for (Trader& Y : Traders) if (Y.Id == X.Id) { Y = X; Hit = true; } if (!Hit) Traders.push_back(X); }
		Q.Steps = { { "trade", "neighbour", 4 }, { "trade_wanted", "neighbour", 2 }, { "talk", "pell", 1 } };
	}
	const Trader* FindTrader(const std::string& Id) const { for (const Trader& T : Traders) if (T.Id == Id) return &T; return nullptr; }
	const seedsong::Tune* FindTune(const std::string& R) const { for (const auto& P : TunesByRecord) if (P.first == R) return P.second; return nullptr; }
	void NextDay() { ++Day; PressedToday.clear(); }

	std::vector<std::string> WantsToday(const std::string& TraderId) const
	{
		const Trader* T = FindTrader(TraderId);
		if (!T) return {};
		std::vector<std::string> Pool; for (const auto& P : TunesByRecord) Pool.push_back(P.first);
		// Java long arithmetic wraps; do it unsigned.
		const uint64_t S = static_cast<uint64_t>(Seed) * 7919ULL + static_cast<uint64_t>(static_cast<int64_t>(Day)) * 104729ULL + static_cast<uint64_t>(static_cast<int64_t>(seedsong::JavaHash(TraderId)));
		forge::SplitRng Rng(static_cast<int64_t>(S));
		std::vector<std::string> Out;
		for (int I = 0; I < T->Wants && !Pool.empty(); ++I)
		{
			const int K = Rng.NextInt(static_cast<int32_t>(Pool.size()));
			Out.push_back(Pool[K]); Pool.erase(Pool.begin() + K);
		}
		return Out;
	}
	static bool Contains(const std::vector<std::string>& V, const std::string& S) { for (const std::string& X : V) if (X == S) return true; return false; }
	int Price(const std::string& TraderId, const std::string& Record) const
	{
		const seedsong::Tune* U = FindTune(Record);
		if (!U || !FindTrader(TraderId)) return 0;
		int P = static_cast<int>(U->Notes.size()) + (U->Notes.front() == U->Notes.back() ? 1 : 0);
		if (Contains(WantsToday(TraderId), Record)) P *= 2;
		const auto It = Held.find(TraderId + "|" + Record);
		return P >> ((It == Held.end() ? 0 : It->second) & 31); // Java int shift masks the count
	}
	/** The caller adds one CopyOf(record) on PRESSED. */
	Outcome Press(const std::string& EventId, const std::string& Record, bool Restored)
	{
		if (hunt::BadEvent(EventId)) return Outcome::Ignored;
		if (Events.count(EventId)) return Outcome::Duplicate;
		if (!FindTune(Record)) return Outcome::UnknownTune;
		if (!Restored) return Outcome::NotRestored;
		if (PressedToday.count(Record)) return Outcome::PressedToday;
		Events.insert(EventId); PressedToday.insert(Record);
		return Outcome::Pressed;
	}
	/** HasCopy: a CopyOf(record) is in store. On TRADED the caller takes the copy and adds Good x Amount. */
	Trade TradeWith(const std::string& EventId, const std::string& TraderId, const std::string& Record, bool HasCopy)
	{
		if (hunt::BadEvent(EventId)) return { Outcome::Ignored, "", 0, false };
		if (Events.count(EventId)) return { Outcome::Duplicate, "", 0, false };
		const Trader* T = FindTrader(TraderId);
		if (!T) return { Outcome::UnknownTrader, "", 0, false };
		if (!FindTune(Record)) return { Outcome::UnknownTune, "", 0, false };
		if (!HasCopy) return { Outcome::NoCopy, "", 0, false };
		const int P = Price(TraderId, Record);
		const bool Wanted = Contains(WantsToday(TraderId), Record);
		if (P <= 0) return { Outcome::Refused, T->Good, 0, Wanted };
		Events.insert(EventId);
		++Held[TraderId + "|" + Record];
		Q.Apply(EventId, "trade", "neighbour");
		if (Wanted) Q.Apply(EventId + "#w", "trade_wanted", "neighbour");
		return { Outcome::Traded, T->Good, P, Wanted };
	}
	std::string Talk(const std::string& EventId);
};

// TraderLines
inline const char* Greeting() { return "No one's played us a tune since the sky fell. Bring a pressed copy and we'll pay in rope, stone, eggs or fish."; }
inline const char* Thanks() { return "Music on every fragment again. Take the good rope; you'll need it for those bridges."; }
inline const char* DoneLine() { return "Come back tomorrow. We'll be humming something new."; }
inline const char* RefusedLine() { return "We've heard that one plenty, thanks."; }

inline std::string TraderLine(const Exchange& X)
{
	const hunt::Quest::Step* S = X.Q.CurrentStep();
	if (!S) return DoneLine();
	const int Idx = X.Q.Current, Count = X.Q.Count;
	if (Idx == 0) return Count == 0 ? std::string(Greeting()) : std::to_string(Count) + " trade" + (Count == 1 ? "" : "s") + " so far. Ask what we're humming for today; we pay double for that.";
	return "Now bring us the tunes we asked for. " + std::to_string(S->Required - Count) + " more of those.";
}

inline std::string Exchange::Talk(const std::string& EventId)
{
	const hunt::Quest::Step* Due = Q.CurrentStep();
	if (Due && Due->Type == "talk") { Q.Apply(EventId, "talk", "pell"); return Thanks(); }
	return TraderLine(*this);
}

}} // namespace daedalus::exchange