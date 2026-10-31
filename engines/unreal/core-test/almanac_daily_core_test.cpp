// SPDX-License-Identifier: MIT
// Prism Almanac Daily C++ core, checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public almanac_daily_core_test.cpp
//   ./a.out almanac_daily_parity.txt      (reads prism_fair_par_parity.txt from the same folder for pars)
#include "DaedalusPrismAlmanacCore.h"
#include "stable_parity.h"
using namespace daedalus::almanac;
using stable_test::Check;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "almanac_daily_parity.txt";
	std::string ParPath = Path;
	const std::size_t Slash = ParPath.find_last_of("/\\");
	ParPath = (Slash == std::string::npos ? std::string() : ParPath.substr(0, Slash + 1)) + "prism_fair_par_parity.txt";
	const ParTable Pars = ParsFrom(stable_test::ParityLines(ParPath.c_str()));
	Check("fair par table has every cabinet and difficulty", Pars.size() == static_cast<std::size_t>(GameCount * 3));

	std::vector<std::string> Lines;
	const std::int64_t First = EpochDay({ 2026, 1, 1 });
	bool AllOk = true;
	for (int i = 0; i < 365; ++i)
	{
		const Date When = FromEpochDay(First + i);
		const Day D = Deal(When);
		bool Ok = false;
		std::string L = "date=" + Iso(When) + " epoch=" + std::to_string(First + i) + " weather=" + WeatherOf(D.Weather).Name;
		for (const Posted& P : Post(D, Pars, Ok))
			L += std::string(" ") + Games[P.Dealt.Game] + "/" + Difficulties[P.Difficulty] + "/" + std::to_string(P.Dealt.Seed) + ":par="
				+ std::to_string(P.DayPar.Bronze) + "," + std::to_string(P.DayPar.Silver) + "," + std::to_string(P.DayPar.Gold);
		AllOk = AllOk && Ok;
		std::set<std::int64_t> Cleared;
		for (int k = 0; k < 10; ++k)
			if ((i + k * k) % 3 != 0) Cleared.insert(First + i - k);
		L += " streak=" + std::to_string(Streak(Cleared, First + i)) + " ribbon=" + std::to_string(Ribbon(Cleared, First + i));
		Lines.push_back(L);
	}
	stable_test::CheckParity(Path, Lines);
	Check("every dealt cabinet has a calibrated par", AllOk);

	const Day Today = Deal({ 2026, 10, 30 }); // pinned from python3 in PrismAlmanacTest
	Check("2026-10-30 dealt like CPython", Today.Weather == EWeather::Fog && Today.Picks[0].Game == 5 && Today.Picks[0].Seed == 590745773u
		&& Today.Picks[1].Game == 1 && Today.Picks[2].Game == 3 && Today.Picks[2].Difficulty == 1 && Today.Picks[2].Seed == 707004768u);
	static_assert(EpochDay({ 1970, 1, 1 }) == 0 && EpochDay({ 2026, 10, 30 }) == 20756 && EpochDay({ 2000, 3, 1 }) == 11017, "epoch day");
	static_assert(ValidDate({ 2024, 2, 29 }) && !ValidDate({ 2026, 2, 29 }) && !ValidDate({ 2026, 13, 1 }) && !ValidDate({ 2026, 4, 31 }), "dates");
	static_assert(ParFor({ 1, 31, 42 }, EWeather::ClearSkies).Silver == 27 && ParFor({ 1, 31, 42 }, EWeather::Gale).Gold == 46, "weather pars");
	const std::int64_t T = EpochDay({ 2026, 10, 30 });
	Check("streak alive from yesterday", Streak({ T - 1, T - 2, T - 3, T - 5 }, T) == 3 && Streak({ T - 2 }, T) == 0);
	Check("ribbon bits", Ribbon({ T - 1, T - 2, T - 3, T - 5 }, T) == 0x3A);
	Day Hard{};
	Hard.Picks[0] = { 8, 2, 7 };
	bool Ok = false;
	Check("uncalibrated prismcairn hard is posted as normal", Post(Hard, Pars, Ok)[0].Difficulty == 1 && Ok);
	Check("missing par is refused", (Post(Hard, ParTable{}, Ok), !Ok));
	return stable_test::Finish();
}
