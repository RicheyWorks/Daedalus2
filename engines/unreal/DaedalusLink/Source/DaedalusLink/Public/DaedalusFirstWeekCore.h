// SPDX-License-Identifier: MIT
// G62 The First Week Home (YTM story ch. 5), plain C++17 for the Unreal binding. A port of daedalus-core
// world/brew/week/{Larder,FirstWeek,WickLines}.java plus the QuestProgress twin, with no Unreal types. The caller owns
// the plot store: it says whether the water / meal / tonic is in store and takes it when the call succeeds.
// Byte parity with Java goes through engines/unreal/core-test/first_week_parity.txt (FirstWeekParityTest).
#pragma once
#include "DaedalusRecordHuntCore.h" // hunt::Quest, hunt::BadEvent; forge::SplitRng via TemperForgeCore
#include <algorithm>
#include <cstdint>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace daedalus { namespace week {

constexpr int Max = 100, Start = 80, Clean = 35, Raw = 20, Salt = -10, ThirstPerDay = 60, HungerPerDay = 45, SickExtra = 20, HealthHit = 40, Days = 7, Low = 25;
constexpr int BaseRestore = 25, MaxRestore = 45;
constexpr double SickChance = 0.25;
inline const char* CleanWater() { return "clean_water"; }
inline const char* DesertThirstTonic() { return "Item_YTM_Tonic_Found_desert_thirst"; }
inline const char* QuestId() { return "q_first_week"; }
inline const char* Wick() { return "old_wick"; }

/** java.util.SplittableRandom.nextDouble on the shared SplitRng state: (mix64(seed += gamma) >>> 11) * 2^-53. */
inline double NextDouble(forge::SplitRng& R)
{
	R.Seed += 0x9e3779b97f4a7c15ULL;
	uint64_t Z = R.Seed;
	Z = (Z ^ (Z >> 30)) * 0xbf58476d1ce4e5b9ULL;
	Z = (Z ^ (Z >> 27)) * 0x94d049bb133111ebULL;
	Z ^= Z >> 31;
	return static_cast<double>(Z >> 11) * (1.0 / 9007199254740992.0);
}

// ------------------------------------------------------------------ Larder
struct Recipe { const char* Name; std::vector<std::string> In; };
inline const std::vector<Recipe>& Recipes()
{
	static const std::vector<Recipe> R = {
		{ "Stew", { "Bacon", "Spudlet", "clean_water" } }, { "Omelet", { "Egg", "Egg", "Fasage" } }, { "Pie", { "Pumplet", "Groat", "Egg" } },
		{ "Porridge", { "Groat", "Milk" } }, { "Roast", { "Bacon", "Gloryroot" } }, { "Soup", { "Kelpweed", "Bitroot", "clean_water" } },
		{ "Salad", { "Clover", "Mimint", "Moonbean" } }, { "Bread", { "Groat", "Groat", "clean_water" } } };
	return R;
}
inline const Recipe* FindRecipe(const std::string& N) { for (const Recipe& R : Recipes()) if (N == R.Name) return &R; return nullptr; }
inline std::string Cooked(const std::string& Recipe) { return "Item_YTM_Food_" + Recipe + "_Cooked"; }

/** PitchTable.ISLAND_CANON.pitchOf(h).isPresent(): the twelve chromatic herbs, case-insensitive. */
inline bool NoteHerb(const std::string& H)
{
	static const char* const N[] = { "doleaf", "sharpcress", "rebell", "flatfern", "mimint", "fasage", "hushmoss", "solthorn", "gloryroot", "lavine", "dronebloom", "tisquill" };
	std::string L = H; for (char& C : L) if (C >= 'A' && C <= 'Z') C = static_cast<char>(C - 'A' + 'a');
	for (const char* K : N) if (L == K) return true;
	return false;
}
inline int RestoreOf(const std::string& Recipe)
{
	const struct Recipe* R = FindRecipe(Recipe);
	if (!R) return 0;
	bool Note = false; for (const std::string& I : R->In) Note = Note || NoteHerb(I);
	return std::min(MaxRestore, BaseRestore + 10 * std::max(0, static_cast<int>(R->In.size()) - 2) + (Note ? 10 : 0));
}
inline std::string RecipeOf(const std::string& CookedItem) { for (const Recipe& R : Recipes()) if (Cooked(R.Name) == CookedItem) return R.Name; return std::string(); }
/** Store items a cook takes, merged in first-seen order (clean_water is the plot's "water"). Empty for an unknown recipe. */
inline std::vector<std::pair<std::string, int>> Needs(const std::string& Recipe)
{
	std::vector<std::pair<std::string, int>> Out;
	const struct Recipe* R = FindRecipe(Recipe);
	if (!R) return Out;
	for (const std::string& I : R->In)
	{
		const std::string S = I == CleanWater() ? std::string("water") : I;
		bool Hit = false; for (auto& P : Out) if (P.first == S) { ++P.second; Hit = true; }
		if (!Hit) Out.emplace_back(S, 1);
	}
	return Out;
}

// ------------------------------------------------------------------ FirstWeek
enum class Water : int { Clean = 0, Raw, Salt };
enum class Outcome : int { Drank = 0, Ate, Tonic, NothingToUse, Over, Duplicate, Ignored };
inline const char* OutcomeName(Outcome O) { static const char* const N[] = { "DRANK", "ATE", "TONIC", "NOTHING_TO_USE", "OVER", "DUPLICATE", "IGNORED" }; return N[static_cast<int>(O)]; }
/** The store item a drink takes (nullptr for the sea). */
inline const char* WaterItem(Water K) { return K == Water::Clean ? "water" : K == Water::Raw ? "raw_water" : nullptr; }
struct Day { bool Valid = false; int N = 0, Thirst = 0, Hunger = 0, Health = 0; bool Sick = false, Tonic = false, Survived = false; };

struct FirstWeek
{
	forge::SplitRng Rng; std::set<std::string> Events; hunt::Quest Q;
	int Thirst = Start, Hunger = Start, Health = Max, DayN = 1; bool SickToday = false, TonicToday = false; Day Last;

	explicit FirstWeek(int64_t Seed) : Rng(Seed) { Q.Steps = { { "survive", "day", Days }, { "talk", Wick(), 1 } }; }
	bool Lost() const { return Health <= 0; }
	bool Over() const { return Lost() || DayN > Days; }
	bool Guard(const std::string& E, Outcome& O) const
	{
		if (hunt::BadEvent(E)) { O = Outcome::Ignored; return true; }
		if (Events.count(E)) { O = Outcome::Duplicate; return true; }
		if (Over()) { O = Outcome::Over; return true; }
		return false;
	}
	/** HasItem: the WaterItem is in store (ignored for the sea). The caller takes it on DRANK. */
	Outcome Drink(const std::string& EventId, Water K, bool HasItem)
	{
		Outcome G; if (Guard(EventId, G)) return G;
		if (WaterItem(K) && !HasItem) return Outcome::NothingToUse;
		Events.insert(EventId);
		const int Gain = K == Water::Clean ? Clean : K == Water::Raw ? Raw : Salt;
		Thirst = std::max(0, std::min(Max, Thirst + Gain));
		if (K == Water::Raw && NextDouble(Rng) < SickChance) SickToday = true;
		return Outcome::Drank;
	}
	/** HasItem: the cooked item is in store. The caller takes it on ATE. */
	Outcome Eat(const std::string& EventId, const std::string& CookedItem, bool HasItem)
	{
		Outcome G; if (Guard(EventId, G)) return G;
		const std::string R = RecipeOf(CookedItem);
		if (R.empty() || !HasItem) return Outcome::NothingToUse;
		Events.insert(EventId);
		Hunger = std::min(Max, Hunger + RestoreOf(R));
		return Outcome::Ate;
	}
	/** HasTonic: the desert_thirst tonic is in store. The caller takes it on TONIC. */
	Outcome TakeTonic(const std::string& EventId, bool HasTonic)
	{
		Outcome G; if (Guard(EventId, G)) return G;
		if (TonicToday || !HasTonic) return Outcome::NothingToUse;
		Events.insert(EventId); TonicToday = true;
		return Outcome::Tonic;
	}
	Day EndDay()
	{
		Day D;
		if (Over()) return D;
		int Drain = ThirstPerDay + (SickToday ? SickExtra : 0);
		if (TonicToday) Drain /= 2;
		Thirst = std::max(0, Thirst - Drain);
		Hunger = std::max(0, Hunger - HungerPerDay);
		if (Thirst == 0) Health -= HealthHit;
		if (Hunger == 0) Health -= HealthHit;
		Health = std::max(0, Health);
		D.Valid = true; D.N = DayN; D.Thirst = Thirst; D.Hunger = Hunger; D.Health = Health; D.Sick = SickToday; D.Tonic = TonicToday; D.Survived = Health > 0;
		Last = D;
		if (D.Survived) Q.Apply("first-week-day-" + std::to_string(DayN), "survive", "day");
		++DayN; SickToday = false; TonicToday = false;
		return D;
	}
	std::string Talk(const std::string& EventId);
};

// WickLines
inline const char* Greeting() { return "First week's the hard one. Drink clean when you can, cook what the plot gives you, and never drink the sea, whatever it looks like."; }
inline const char* Thirsty() { return "Your lips are cracking. Get to a clean spring before the sun goes down."; }
inline const char* Hungry() { return "You're running on nothing. Cook something, even porridge."; }
inline const char* SickLine() { return "That cloudy water got you. Boil it, filter it, or brew a cadence over it next time."; }
inline const char* LostLine() { return "Lie still. Someone will carry you home. The shelf will wait for you."; }
inline const char* Thanks() { return "Seven days. You're not a survivor any more, you're a neighbour. The ferry's yours when you want it."; }

inline std::string WickLine(const FirstWeek& W)
{
	if (W.Lost()) return LostLine();
	if (!W.Last.Valid && W.Thirst == Start && W.Hunger == Start) return Greeting();
	if (W.SickToday) return SickLine();
	if (W.Thirst < Low) return Thirsty();
	if (W.Hunger < Low) return Hungry();
	return "Day " + std::to_string(std::min(W.DayN, Days)) + ". You're holding up.";
}

inline std::string FirstWeek::Talk(const std::string& EventId)
{
	const hunt::Quest::Step* Due = Q.CurrentStep();
	if (Due && Due->Type == "talk") { Q.Apply(EventId, "talk", Wick()); return Thanks(); }
	return WickLine(*this);
}

}} // namespace daedalus::week