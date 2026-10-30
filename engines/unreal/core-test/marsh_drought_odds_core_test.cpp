// SPDX-License-Identifier: MIT
// G202 Drought Odds C++ port (G570), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_drought_odds_core_test.cpp
//   ./a.out marsh_drought_odds_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java): analytic values to 1e-9 relative, Monte Carlo
// hit counts to within one hit (libm last-ulp differences in log/cos can only move a crossing by a hair).
#include "DaedalusMarshDroughtOddsCore.h"
#include "marsh_parity.h"
#include <cstdlib>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_drought_odds_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 48 cases", Lines.size() == 48);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		DroughtSettings S;
		S.Mu = marsh_test::Num(L, "mu");
		S.Sigma = marsh_test::Num(L, "sigma");
		S.Start = static_cast<int>(marsh_test::Int(L, "start"));
		S.Threshold = static_cast<int>(marsh_test::Int(L, "threshold"));
		const DroughtOdds O(S);
		const std::string Tag = L.substr(0, L.find(" within"));
		Check(Tag + " valid", S.Valid());
		Check(Tag + " within", Close(O.Within(marsh_test::Num(L, "T")), marsh_test::Num(L, "within"), 1e-9));
		Check(Tag + " ultimate", Close(O.Ultimate(), marsh_test::Num(L, "ultimate"), 1e-9));
		Check(Tag + " median", Close(O.MedianYears(), marsh_test::Num(L, "median"), 1e-7));
		const int Hits = O.SimulateHits(static_cast<int>(marsh_test::Int(L, "runs")), static_cast<int>(marsh_test::Int(L, "years")),
			static_cast<int>(marsh_test::Int(L, "substeps")), marsh_test::Int(L, "seed"));
		const long long Want = marsh_test::Int(L, "hits");
		Check(Tag + " hits", std::llabs(Hits - Want) <= 1);
		Exact += Hits == Want;
	}
	Check("Monte Carlo hits identical on at least 46 of 48 cases", Exact >= 46);

	// Engine-free unit checks mirroring DroughtOddsTest.
	Check("Phi(0) = 0.5", Close(Phi(0), 0.5, 1e-7));
	Check("Phi(1.96) table", Close(Phi(1.96), 0.9750021, 2e-7));
	DroughtSettings Flat; Flat.Mu = 0; Flat.Sigma = 0.2;
	const DroughtOdds F(Flat);
	Check("driftless walk: reflection principle", Close(F.Within(50), 2 * Phi(-std::log(4.0) / (0.2 * std::sqrt(50.0))), 1e-9));
	Check("mu <= 0 means certain ruin", F.Ultimate() == 1);
	DroughtSettings Up; Up.Mu = 0.03; Up.Sigma = 0.2;
	const DroughtOdds G(Up);
	Check("ultimate = exp(-2 mu d / sigma^2)", Close(G.Ultimate(), std::exp(-2 * 0.03 * std::log(4.0) / 0.04), 1e-12));
	bool Mono = true; double Prev = 0;
	for (int T = 1; T <= 400; T += 7) { const double W = G.Within(T); Mono = Mono && W >= Prev - 1e-12; Prev = W; }
	Check("G(T) never falls", Mono && Close(G.Within(1e6), G.Ultimate(), 1e-6));
	Check("median halves the hitters", Close(DroughtOdds({ -0.02, 0.15, 30, 10 }).Within(DroughtOdds({ -0.02, 0.15, 30, 10 }).MedianYears()), 0.5, 1e-9));
	Check("seeded replay", G.SimulateHits(500, 30, 4, 5) == G.SimulateHits(500, 30, 4, 5));
	DroughtSettings Bad; Bad.Sigma = 0;
	DroughtSettings Bad2; Bad2.Start = 10;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && DroughtSettings().Valid());
	Check("bad inputs rejected", G.Within(-1) < 0 && G.SimulateHits(0, 10, 1, 1) < 0);
	return marsh_test::Summary("marsh drought odds core");
}
