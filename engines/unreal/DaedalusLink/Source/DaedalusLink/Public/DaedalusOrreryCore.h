// SPDX-License-Identifier: MIT
#pragma once
// The Orrery Reach's rules in plain C++ (ADR-057): no Unreal types, so core-test can build and check them with
// ASan/UBSan on any compiler. UDaedalusOrrery (the Unreal subsystem) calls these; it only adds the world, the HUD
// and the hero.
//
// - 24 herbs, one per sky hour. Each of the 12 constellations has one day bloom (06:00..17:59) and one night bloom.
// - A starbloom can be picked only during its own hour.
// - Steeping uses the last two herbs in the satchel:
//     - two of one constellation make "<Constellation> Brew";
//     - a day bloom and a night bloom of different constellations make "Eclipse Brew: <name>";
//     - anything else makes "<last herb> Tea" from the last herb alone.
// - The Keeper's Logbook has 9 steps (0..8). It only moves forward one step at a time, and step 7 needs all 12 charts.

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace daedalus { namespace orrery {

struct Herb { const char* Name; int Hour; const char* Constellation; };

inline const std::array<Herb, 24>& Herbs()
{
	static const std::array<Herb, 24> H = {{
		{"Dawnthistle", 6, "Keeper"}, {"Midnightmint", 0, "Keeper"},
		{"Sunsprig", 8, "Lantern"}, {"Duskmallow", 18, "Lantern"},
		{"Orbitfern", 9, "Ark"}, {"Moonvetch", 21, "Ark"},
		{"Eclipsebell", 13, "Shard"}, {"Meteorsage", 1, "Shard"},
		{"Equinoxbalm", 10, "Wanderer"}, {"Cometcress", 3, "Wanderer"},
		{"Heartstonebloom", 7, "Hearth"}, {"Starsedge", 22, "Hearth"},
		{"Zenithclover", 11, "Spindle"}, {"Nebulawort", 23, "Spindle"},
		{"Noonspire", 12, "Crown"}, {"Polarisroot", 2, "Crown"},
		{"Driftfennel", 16, "Tide"}, {"Nadirmoss", 4, "Tide"},
		{"Quasarthyme", 14, "Forge"}, {"Twilightsorrel", 19, "Forge"},
		{"Solsticerue", 15, "Kite"}, {"Auroraleaf", 5, "Kite"},
		{"Lunarlily", 17, "Loom"}, {"Galaxygrass", 20, "Loom"},
	}};
	return H;
}

inline const std::array<const char*, 12>& Constellations()
{
	static const std::array<const char*, 12> C = {{"Keeper", "Lantern", "Ark", "Shard", "Wanderer", "Hearth",
		"Spindle", "Crown", "Tide", "Forge", "Kite", "Loom"}};
	return C;
}

constexpr int ChartCount = 12;
constexpr int LastStep = 8;

inline bool IsDay(int Hour) { return Hour >= 6 && Hour < 18; }

inline const Herb* FindHerb(const std::string& Name)
{
	for (const Herb& H : Herbs())
		if (Name == H.Name) return &H;
	return nullptr;
}

/** Whole sky hour (0..23) for any hour value, including negative or past 24. */
inline int WholeHour(double Hour)
{
	if (!(Hour == Hour)) return 0;   // NaN
	long long H = static_cast<long long>(Hour >= 0 ? Hour : Hour - 1.0);   // floor for the range we use
	H %= 24;
	if (H < 0) H += 24;
	return static_cast<int>(H);
}

/** A bloom opens only in its own hour. */
inline bool CanPick(const std::string& Species, double Hour)
{
	const Herb* H = FindHerb(Species);
	return H && WholeHour(Hour) == H->Hour;
}

/** "" when the two herbs make no brew. */
inline std::string BrewOf(const std::string& A, const std::string& B)
{
	const Herb* X = FindHerb(A);
	const Herb* Y = FindHerb(B);
	if (!X || !Y || A == B) return std::string();
	if (std::string(X->Constellation) == Y->Constellation) return std::string(X->Constellation) + " Brew";
	if (IsDay(X->Hour) != IsDay(Y->Hour))
	{
		static const char* Eclipses[] = {"Umbra", "Penumbra", "Corona", "Diamondring", "Baileybeads", "Totality",
			"Annular", "Hybrid"};
		return std::string("Eclipse Brew: ") + Eclipses[(X->Hour + Y->Hour) % 8];
	}
	return std::string();
}

enum class Kind { None, Tea, Brew, Eclipse };
enum class Refusal { None, GrittyWater, EmptySatchel, UnknownHerb };

struct SteepResult
{
	Refusal Failure = Refusal::None;
	Kind Made = Kind::None;
	std::string Name;
	std::size_t Used = 0;   // herbs taken off the end of the satchel
};

/** Decide a steep without changing anything; ApplySteep commits it. A refusal leaves everything as it was. */
inline SteepResult PlanSteep(bool CleanWater, const std::vector<std::string>& Satchel)
{
	SteepResult R;
	if (!CleanWater) { R.Failure = Refusal::GrittyWater; return R; }
	if (Satchel.empty()) { R.Failure = Refusal::EmptySatchel; return R; }
	if (!FindHerb(Satchel.back())) { R.Failure = Refusal::UnknownHerb; return R; }
	if (Satchel.size() >= 2)
	{
		R.Name = BrewOf(Satchel.back(), Satchel[Satchel.size() - 2]);
		if (!R.Name.empty())
		{
			R.Used = 2;
			R.Made = R.Name.compare(0, 7, "Eclipse") == 0 ? Kind::Eclipse : Kind::Brew;
			return R;
		}
	}
	R.Name = Satchel.back() + " Tea";
	R.Used = 1;
	R.Made = Kind::Tea;
	return R;
}

/** The Keeper's Logbook. */
struct Logbook
{
	int Step = 0;
	std::vector<std::string> Charts;

	/** Moves to ToStep only from the step right before it. Step 7 needs all 12 charts; reaching step 6 with all
	 * 12 already home goes straight on to 7. Returns true if it moved. */
	bool Advance(int ToStep)
	{
		if (ToStep != Step + 1 || ToStep > LastStep) return false;
		if (ToStep == 7 && static_cast<int>(Charts.size()) < ChartCount) return false;
		Step = ToStep;
		if (Step == 6 && static_cast<int>(Charts.size()) >= ChartCount) Step = 7;
		return true;
	}

	/** Adds a chart once; unknown constellations are refused. Returns true if it was new. */
	bool AddChart(const std::string& Constellation)
	{
		bool Known = false;
		for (const char* C : Constellations()) Known = Known || Constellation == C;
		if (!Known) return false;
		for (const std::string& Have : Charts)
			if (Have == Constellation) return false;
		Charts.push_back(Constellation);
		return true;
	}

	/** The logbook steps a steep earns: a tea is step 5, a brew counts as the first tea and step 6, an eclipse is 8. */
	void Credit(Kind Made)
	{
		if (Made == Kind::Tea) Advance(5);
		else if (Made == Kind::Brew) { Advance(5); Advance(6); }
		else if (Made == Kind::Eclipse) Advance(8);
	}
};

/** Commit a planned steep: herbs off the satchel, the brew into Brews, the logbook credited. */
inline void ApplySteep(const SteepResult& R, std::vector<std::string>& Satchel, std::vector<std::string>& Brews,
	Logbook& Book)
{
	if (R.Failure != Refusal::None || R.Used > Satchel.size()) return;
	Satchel.resize(Satchel.size() - R.Used);
	Brews.push_back(R.Name);
	Book.Credit(R.Made);
}

inline const char* StepText(int Step)
{
	static const char* Steps[] = {
		"Meet the Keeper at the ark dock",
		"Fix the clogged sand filter on the aqueduct",
		"Find the Lantern star chart in the herb rings",
		"Harvest a starbloom in its own hour",
		"Steep your first tea at a kettle",
		"Steep a constellation brew (two blooms of one constellation)",
		"Recover all twelve star charts around the rim",
		"Steep an eclipse brew (a day bloom and a night bloom)",
		"Point the great telescope at the new moon",
	};
	return Steps[Step < 0 ? 0 : (Step > LastStep ? LastStep : Step)];
}

}}  // namespace daedalus::orrery
