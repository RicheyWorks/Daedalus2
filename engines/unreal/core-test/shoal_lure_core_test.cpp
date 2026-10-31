// SPDX-License-Identifier: MIT
// Shoal Lure parity: DaedalusShoalLureCore.h must regenerate every grid in shoal_lure_parity.txt (currents, fish,
// eels, the exact best trip's target and plan, probe trips) from seed + difficulty alone (CPython-compatible seeding)
// and replay every demo move and hint byte for byte.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public shoal_lure_core_test.cpp -o shoal_lure_core_test && ./shoal_lure_core_test shoal_lure_parity.txt
#include "DaedalusShoalLureCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::shoallure;

namespace {

std::string Ints(const std::vector<int>& Xs)
{
	std::string S;
	for (size_t I = 0; I < Xs.size(); ++I) S += (I ? "," : "") + std::to_string(Xs[I]);
	return S;
}

std::string ActString(const Action& A)
{
	if (A.K == Kind::Net) return "net";
	if (A.K == Kind::Dock) return "dock";
	return A.Dir >= 0 ? std::string(1, DirLetters()[A.Dir]) : "?";
}

std::string StateString(const Game& G)
{
	std::ostringstream O;
	O << "at=" << G.At << " stamina=" << G.Stamina << " score=" << G.Score << " netted=" << Ints(G.Netted) << " shoal=" << Ints(G.Shoal) << " moves=" << G.Moves;
	return O.str();
}

std::string Opening(std::uint32_t Seed, const std::string& Diff, const Game& G)
{
	std::string Cur, FishText;
	for (size_t R = 0; R < G.Current.size(); ++R)
	{
		if (R) Cur += "/";
		for (int X : G.Current[R]) Cur += std::to_string(X);
	}
	for (size_t I = 0; I < G.FishList.size(); ++I)
		FishText += (I ? "," : "") + std::to_string(G.FishList[I].Cell) + ":" + std::to_string(G.FishList[I].Hue);
	return "game s=" + std::to_string(Seed) + " d=" + Diff + " current=" + Cur + " fish=" + FishText + " eels=" + Ints(G.Eels)
		+ " best=" + std::to_string(G.Best) + " target=" + std::to_string(G.Target) + " plan=" + Ints(G.Plan) + " " + StateString(G);
}

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

int UnitChecks()
{
	int Fails = 0;
	if (ChainValue({}) != 0 || ChainValue({ 1, 1, 1 }) != 6 || ChainValue({ 1, 2, 1 }) != 3 || ChainValue({ 2, 2, 1, 1 }) != 6)
	{
		std::printf("FAIL chain value\n"); ++Fails;
	}
	const Grid East(3, std::vector<int>(3, 1));
	const Grid D = Distances(3, East, { 1 });
	if (D[0][2] != 4 || D[0][1] < Inf) { std::printf("FAIL distances around an eel\n"); ++Fails; }
	// Same case as test_shoal_lure.test_best_trip_and_best_score: biggest shoal 4, best-score order skips the far fish.
	const Grid Open = Distances(3, East, {});
	const std::vector<Fish> Pool = { { 0, 1 }, { 3, 1 }, { 8, 2 } };
	const Trip Big = BestTrip(Open, Pool, 1, 1, 12, {}), Top = BestTrip(Open, Pool, 1, 1, 12, {}, 3);
	std::vector<int> TopSorted = Top.Order;
	std::sort(TopSorted.begin(), TopSorted.end());
	if (Big.Best != 4 || Top.Best != 4 || TopSorted != std::vector<int>{ 0, 1 }) { std::printf("FAIL best trip\n"); ++Fails; }
	Game G; std::string Res;
	if (G.Start(0, "mythic")) { std::printf("FAIL unknown difficulty accepted\n"); ++Fails; }
	if (!G.Start(1, "normal")) { std::printf("FAIL normal start\n"); ++Fails; return Fails; }
	if (G.Step({ Kind::Dock, 0 }, Res) != Game::Act::SwimFirst || G.Step({ Kind::Net, 0 }, Res) != Game::Act::NoFish
		|| G.Step({ Kind::Move, 0 }, Res) != Game::Act::OffGrid || G.Step({ Kind::Move, 7 }, Res) != Game::Act::BadAction)
	{
		std::printf("FAIL refusals\n"); ++Fails;
	}
	// Eel scatter, as test_shoal_lure.test_eel_scatters_the_shoal.
	G.FishList[0] = { G.Home() + 1, 1 }; G.Eels[0] = G.Home() + 2; G.Restore();
	G.Step({ Kind::Move, 1 }, Res); G.Step({ Kind::Net, 0 }, Res);
	const int Before = G.Score;
	G.Step({ Kind::Move, 1 }, Res);
	if (Before != 1 || !G.Shoal.empty() || G.Score != 0) { std::printf("FAIL eel scatter\n"); ++Fails; }
	return Fails;
}

}  // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: shoal_lure_core_test shoal_lure_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks(), Games = 0, Turn = 0;
	Game G;
	std::string Line;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		if (Line.rfind("game ", 0) == 0)
		{
			const std::uint32_t Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
			const std::string Diff = Field(Line, "d");
			++Games; Turn = 0;
			if (!G.Start(Seed, Diff) || Opening(Seed, Diff, G) != Line)
			{
				std::printf("FAIL opening\n  want %s\n  got  %s\n", Line.c_str(), Opening(Seed, Diff, G).c_str()); ++Fails;
			}
		}
		else if (Line.rfind("probe ", 0) == 0)
		{
			const int K = std::stoi(Field(Line, "k"));
			const Trip T = BestTrip(G.Dist, G.FishList, G.Home(), G.Home(), K, {});
			const std::string Got = "probe k=" + std::to_string(K) + " best=" + std::to_string(T.Best) + " order=" + Ints(T.Order);
			if (Got != Line) { std::printf("FAIL %s\n  got %s\n", Line.c_str(), Got.c_str()); ++Fails; }
		}
		else if (Line.rfind("move ", 0) == 0)
		{
			const Action A = G.DemoAction();
			std::string Res;
			const Game::Act R = G.Step(A, Res);
			for (char& Ch : Res) if (Ch == ' ') Ch = '_';
			std::ostringstream O;
			O << "move t=" << ++Turn << " act=" << ActString(A) << " " << StateString(G) << " hint=" << (G.Over ? "-" : ActString(G.Hint()))
			  << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0) << " res=" << Res;
			if (R != Game::Act::Ok || O.str() != Line) { std::printf("FAIL move\n  want %s\n  got  %s\n", Line.c_str(), O.str().c_str()); ++Fails; }
		}
		else if (Line.rfind("end ", 0) == 0)
		{
			const std::string Got = "end  score=" + std::to_string(G.Score) + " won=" + (G.Won ? "1" : "0");
			if (Got != Line) { std::printf("FAIL %s\n  got %s\n", Line.c_str(), Got.c_str()); ++Fails; }
		}
		if (Fails > 20) break;
	}
	if (Fails) { std::printf("FAILED shoal_lure: %d failures over %d games\n", Fails, Games); return 1; }
	std::printf("OK shoal_lure: %d grids regenerated from seed, every demo move and hint matched, 0 failures\n", Games);
	return 0;
}
