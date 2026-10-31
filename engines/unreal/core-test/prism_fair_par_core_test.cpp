// SPDX-License-Identifier: MIT
// Prismheart Fair Par parity: DaedalusPrismFairParCore.h must replay the whole par table in prism_fair_par_parity.txt
// (written by tools/minigames/fair_par.py) exactly, by playing the casual bot and the demo through the C++ cores of
// every Prismheart game but Shardring (Oracle-fed, no PRNG port: its rows are checked for shape and tier order), and
// match the bot hash vectors bit for bit. G607: with a second argument (fair_par_guard.txt, hand-kept) it also
// fails and names every par that moved from the guard, so a rule change cannot shift a par by a fixture regen alone.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public prism_fair_par_core_test.cpp -o prism_fair_par_core_test && ./prism_fair_par_core_test prism_fair_par_parity.txt fair_par_guard.txt
#include "DaedalusPrismFairParCore.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

using namespace daedalus::prismpar;

namespace {
int Passed = 0, Total = 0;
void Check(const std::string& Name, bool Ok)
{
	++Total;
	Passed += Ok;
	if (!Ok) std::printf("FAIL %s\n", Name.c_str());
}
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = Key + "=";
	size_t P = Line.rfind(" " + Needle);
	P = (P == std::string::npos) ? (Line.rfind(Needle, 0) == 0 ? 0 : std::string::npos) : P + 1;
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
int Int(const std::string& Line, const std::string& Key) { return std::atoi(Field(Line, Key).c_str()); }
} // namespace

int main(int argc, char** argv)
{
	std::ifstream In(argc > 1 ? argv[1] : "prism_fair_par_parity.txt");
	std::vector<std::string> Rows, Hashes;
	for (std::string L; std::getline(In, L);)
	{
		if (!L.empty() && L.back() == '\r') L.pop_back();
		if (L.rfind("game=", 0) == 0) Rows.push_back(L);
		else if (L.rfind("hash ", 0) == 0) Hashes.push_back(L);
	}
	Check("fixture has one par row per game and difficulty, and 4 hash rows", Rows.size() == 3 * GameCount && Hashes.size() == 4);
	for (const std::string& H : Hashes)
	{
		const int Run = Int(H, "run");
		Check("hash run " + std::to_string(Run), Uniform(41, Run, 2, 3) == std::strtod(Field(H, "u").c_str(), nullptr)
			&& Pick(41, Run, 1, 0, 6) == Int(H, "pick"));
	}
	bool Ok = false;
	const std::vector<Row> Table = daedalus::prismpar::Table(Ok);
	Check("every bot and demo move was legal", Ok && Table.size() == 3 * ReplayCount);
	for (size_t I = 0; I < Table.size() && I < Rows.size(); ++I)
	{
		const Row& R = Table[I];
		const std::string& H = Rows[I];
		const std::string Tag = R.Game + " " + R.Difficulty;
		Check(Tag + " names", Field(H, "game") == R.Game && Field(H, "difficulty") == R.Difficulty && Int(H, "seeds") == Seeds);
		Check(Tag + " pars", Int(H, "bronze") == R.Bronze && Int(H, "silver") == R.Silver && Int(H, "gold") == R.Gold);
		Check(Tag + " hits", Int(H, "bronzeHit") == R.Hits[0] && Int(H, "silverHit") == R.Hits[1] && Int(H, "goldHit") == R.Hits[2]);
		Check(Tag + " medians and win rates", Int(H, "winMedian") == R.WinMedian && Int(H, "botWin") == R.BotWin
			&& Int(H, "demoWin") == R.DemoWin && Int(H, "demoMedian") == R.DemoMedian);
		Check(Tag + " separated", (Field(H, "separated") == "true") == R.Separated);
		Check(Tag + " tiers", TierOf(R, false, 999) == Tier::None && TierOf(R, true, R.Bronze) == Tier::Bronze
			&& (R.Gold == 0 || TierOf(R, true, R.Gold) == Tier::Gold) && (R.Silver == 0 || R.Silver == R.Gold || TierOf(R, true, R.Silver) == Tier::Silver));
	}
	for (size_t I = Table.size(); I < Rows.size(); ++I)
	{
		const std::string& H = Rows[I];
		Row R;
		R.Game = Field(H, "game"); R.Difficulty = Field(H, "difficulty");
		R.Bronze = Int(H, "bronze"); R.Silver = Int(H, "silver"); R.Gold = Int(H, "gold");
		const std::string Tag = R.Game + " " + R.Difficulty + " (fixture only)";
		Check(Tag + " names", R.Game == "shardring" && Int(H, "seeds") == Seeds);
		Check(Tag + " order", R.Bronze == 1 && R.Silver <= R.Gold && Int(H, "bronzeHit") >= Int(H, "silverHit")
			&& Int(H, "silverHit") >= Int(H, "goldHit") && Int(H, "botWin") == Int(H, "bronzeHit"));
		Check(Tag + " tiers", TierOf(R, false, 999) == Tier::None && TierOf(R, true, R.Bronze) == Tier::Bronze
			&& (R.Gold == 0 || TierOf(R, true, R.Gold) == Tier::Gold));
	}
	if (argc > 2)
	{
		std::ifstream G(argv[2]);
		std::vector<std::string> Guard;
		for (std::string L; std::getline(G, L);)
		{
			if (!L.empty() && L.back() == '\r') L.pop_back();
			if (L.rfind("prism=", 0) == 0) Guard.push_back(L);
		}
		Check("guard has one row per game and difficulty", Guard.size() == 3 * GameCount);
		for (size_t I = 0; I < Guard.size() && I < Rows.size(); ++I)
		{
			const std::string& W = Guard[I];
			const std::string& H = Rows[I];
			const std::string Tag = Field(W, "prism") + " " + Field(W, "difficulty");
			Check("par guard " + Tag + " row order", Field(W, "prism") == Field(H, "game") && Field(W, "difficulty") == Field(H, "difficulty"));
			// Replayed games are compared with the live C++ table; Shardring (fixture-only) with its fixture row.
			for (const char* K : { "bronze", "silver", "gold" })
			{
				const int Got = I < Table.size() ? (std::string(K) == "bronze" ? Table[I].Bronze : std::string(K) == "silver" ? Table[I].Silver : Table[I].Gold) : Int(H, K);
				if (Int(W, K) != Got) std::printf("PAR GUARD: %s: %s par moved %d -> %d\n", Tag.c_str(), K, Int(W, K), Got);
				Check("par guard " + Tag + " " + K, Int(W, K) == Got);
			}
		}
	}
	std::printf("%s prism fair par core: %d/%d checks passed\n", Passed == Total ? "OK" : "FAIL", Passed, Total);
	return Passed == Total ? 0 : 1;
}
