// SPDX-License-Identifier: MIT
// Prism Almanac Daily (Prismheart Daily Almanac lane, 2hot2trot), plain C++17, header-only, no Unreal types.
// Every calendar day deals the same three Prismheart cabinets, difficulties and 32-bit game seeds to every player,
// plus a weathervane modifier that nudges the day's silver and gold pars. The draw is CPython
// random.Random("prism-almanac:YYYY-MM-DD") through daedalus::pyrandom::PyRandom, the same as the Java reference
// com.daedalus.world.almanac.PrismAlmanac, which writes almanac_daily_parity.txt (replayed by almanac_daily_core_test.cpp).
// Pars are read, never computed: hosts feed the Fair Par fixture lines (prism_fair_par_parity.txt, Pythagoras' lane).
// Daedalus placement: the Almanac board in the Prismheart hall shows today's three cabinets, weather and pars; each
// cabinet starts its own core with the dealt seed and difficulty; streak and the 7-day ribbon drive the calendar.
#pragma once
#include "DaedalusPyRandomCore.h"
#include <cstdint>
#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace daedalus { namespace almanac {

constexpr int GameCount = 11;
constexpr const char* Games[GameCount] = { "glowmoss", "spiritkite", "glimmerloom", "lumenpath", "wardens_accord", "facetlock",
	"prismvault", "shardfall", "prismcairn", "shadewatch", "shardring" }; // Fair Par order
constexpr const char* Difficulties[3] = { "easy", "normal", "hard" };
constexpr int CabinetsPerDay = 3;
constexpr int RibbonDays = 7;
constexpr const char* SeedPrefix = "prism-almanac:";

enum class EWeather : int { ClearSkies, Calm, Fog, Gale };
struct WeatherSpec { const char* Name; int ParPercent; bool Hints; };
constexpr WeatherSpec Weathers[4] = { { "CLEAR_SKIES", 90, true }, { "CALM", 100, true }, { "FOG", 100, false }, { "GALE", 110, true } };
constexpr const WeatherSpec& WeatherOf(EWeather W) noexcept { return Weathers[static_cast<int>(W)]; }

struct Date { int Year = 1970, Month = 1, Day = 1; };

// Days since 1970-01-01 (proleptic Gregorian), same as Java LocalDate.toEpochDay.
constexpr std::int64_t EpochDay(Date D) noexcept
{
	const std::int64_t Y = D.Year - (D.Month <= 2 ? 1 : 0);
	const std::int64_t Era = (Y >= 0 ? Y : Y - 399) / 400;
	const std::int64_t Yoe = Y - Era * 400;
	const std::int64_t Doy = (153 * (D.Month + (D.Month > 2 ? -3 : 9)) + 2) / 5 + D.Day - 1;
	const std::int64_t Doe = Yoe * 365 + Yoe / 4 - Yoe / 100 + Doy;
	return Era * 146097 + Doe - 719468;
}

// Inverse of EpochDay.
constexpr Date FromEpochDay(std::int64_t Z) noexcept
{
	Z += 719468;
	const std::int64_t Era = (Z >= 0 ? Z : Z - 146096) / 146097;
	const std::int64_t Doe = Z - Era * 146097;
	const std::int64_t Yoe = (Doe - Doe / 1460 + Doe / 36524 - Doe / 146096) / 365;
	const std::int64_t Doy = Doe - (365 * Yoe + Yoe / 4 - Yoe / 100);
	const std::int64_t Mp = (5 * Doy + 2) / 153;
	const int M = static_cast<int>(Mp < 10 ? Mp + 3 : Mp - 9);
	return { static_cast<int>(Yoe + Era * 400 + (M <= 2 ? 1 : 0)), M, static_cast<int>(Doy - (153 * Mp + 2) / 5 + 1) };
}

constexpr bool ValidDate(Date D) noexcept
{
	if (D.Year < 1 || D.Year > 9999 || D.Month < 1 || D.Month > 12 || D.Day < 1) return false;
	const Date Back = FromEpochDay(EpochDay(D));
	return Back.Year == D.Year && Back.Month == D.Month && Back.Day == D.Day;
}

// ISO date text, e.g. 2026-10-30 (Java LocalDate.toString for years 1..9999).
inline std::string Iso(Date D)
{
	char Buf[16];
	std::snprintf(Buf, sizeof(Buf), "%04d-%02d-%02d", D.Year, D.Month, D.Day);
	return Buf;
}

struct Pick { int Game = 0; int Difficulty = 0; std::uint32_t Seed = 0; };
struct Day { Date When; EWeather Weather = EWeather::Calm; Pick Picks[CabinetsPerDay]; };

// Deals a day: weather, then per cabinet the game (from those not yet dealt), its difficulty and its game seed.
inline Day Deal(Date When)
{
	pyrandom::PyRandom Rng(SeedPrefix + Iso(When));
	Day D;
	D.When = When;
	D.Weather = static_cast<EWeather>(Rng.Below(4));
	std::vector<int> Pool;
	for (int g = 0; g < GameCount; ++g) Pool.push_back(g);
	for (Pick& P : D.Picks)
	{
		const std::size_t I = Rng.Below(static_cast<std::uint32_t>(Pool.size()));
		P.Game = Pool[I];
		Pool.erase(Pool.begin() + static_cast<std::ptrdiff_t>(I));
		P.Difficulty = static_cast<int>(Rng.Below(3));
		P.Seed = Rng.U32();
	}
	return D;
}

struct Par
{
	int Bronze = 0, Silver = 0, Gold = 0;
	// False when Fair Par's bot never won (silver and gold 0): no fair par to post.
	constexpr bool Calibrated() const noexcept { return Silver > 0 && Gold >= Silver; }
};
using ParTable = std::map<std::string, Par>; // key "game/difficulty"

// Reads Fair Par fixture lines ("game=.. difficulty=.. bronze=.. silver=.. gold=.."); other lines are skipped.
inline ParTable ParsFrom(const std::vector<std::string>& Lines)
{
	ParTable Out;
	for (const std::string& L : Lines)
	{
		if (L.rfind("game=", 0) != 0) continue;
		std::map<std::string, std::string> Kv;
		std::size_t I = 0;
		while (I < L.size())
		{
			std::size_t J = L.find(' ', I);
			if (J == std::string::npos) J = L.size();
			const std::string Tok = L.substr(I, J - I);
			const std::size_t Eq = Tok.find('=');
			if (Eq != std::string::npos && Eq > 0) Kv[Tok.substr(0, Eq)] = Tok.substr(Eq + 1);
			I = J + 1;
		}
		if (Kv.count("difficulty") && Kv.count("bronze") && Kv.count("silver") && Kv.count("gold"))
			Out[Kv["game"] + "/" + Kv["difficulty"]] = { std::stoi(Kv["bronze"]), std::stoi(Kv["silver"]), std::stoi(Kv["gold"]) };
	}
	return Out;
}

// The day's par: silver and gold scaled by the weather (integer floor), bronze kept.
constexpr Par ParFor(Par Base, EWeather W) noexcept
{
	return { Base.Bronze, Base.Silver * WeatherOf(W).ParPercent / 100, Base.Gold * WeatherOf(W).ParPercent / 100 };
}

struct Posted { Pick Dealt; int Difficulty = 0; Par DayPar; };

// Posts a dealt day against the par table: an uncalibrated difficulty is played one easier (until calibrated); the
// seed never changes. Ok is false when a cabinet has no calibrated par at all.
inline std::vector<Posted> Post(const Day& D, const ParTable& Pars, bool& Ok)
{
	Ok = true;
	std::vector<Posted> Out;
	for (const Pick& P : D.Picks)
	{
		int Diff = P.Difficulty;
		auto Find = [&](int Df) { auto It = Pars.find(std::string(Games[P.Game]) + "/" + Difficulties[Df]); return It == Pars.end() ? Par{} : It->second; };
		Par Base = Find(Diff);
		while (Diff > 0 && !Base.Calibrated()) Base = Find(--Diff);
		if (!Base.Calibrated()) Ok = false;
		Out.push_back({ P, Diff, ParFor(Base, D.Weather) });
	}
	return Out;
}

// Current streak: consecutive cleared days ending today, or yesterday when today is not cleared yet.
inline int Streak(const std::set<std::int64_t>& Cleared, std::int64_t Today)
{
	std::int64_t D = Cleared.count(Today) ? Today : Today - 1;
	int N = 0;
	while (Cleared.count(D)) { ++N; --D; }
	return N;
}

// Seven-day ribbon: bit i set when day Today - 6 + i is cleared.
inline int Ribbon(const std::set<std::int64_t>& Cleared, std::int64_t Today)
{
	int Mask = 0;
	for (int i = 0; i < RibbonDays; ++i)
		if (Cleared.count(Today - (RibbonDays - 1) + i)) Mask |= 1 << i;
	return Mask;
}

} } // namespace daedalus::almanac
