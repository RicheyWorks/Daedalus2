// SPDX-License-Identifier: MIT
// G504 Reed Ceiling C++ port (G591), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_reed_ceiling_core_test.cpp
//   ./a.out marsh_reed_ceiling_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java) for 7 marshes (stable, cycling and no-hawks):
// the closed-form equilibrium, Hopf capacity, regime and trace (1e-12 relative), the RK4 run sampled every 5 years (1e-9) and the seeded noisy seasons
// (1e-7, because the yearly shock goes through exp/log/cos and libm may differ in the last ulp).
#include "DaedalusMarshReedCeilingCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Num;

static bool SameRun(const ReedRun& R, const std::string& Row, double Tol)
{
	bool Ok = R.Ok && static_cast<long long>(R.Points.size()) == marsh_test::Int(Row, "points")
		&& Close(R.MinCranes, Num(Row, "min"), Tol) && Close(R.MaxCranes, Num(Row, "max"), Tol)
		&& Close(R.FinalHawks, Num(Row, "finalHawks"), Tol);
	for (const ReedPoint& P : R.Points)
	{
		const long long Y = static_cast<long long>(std::floor(P.Year + 0.5));
		if (Y % 5 != 0) continue;
		Ok = Ok && Close(P.Cranes, Num(Row, "n" + std::to_string(Y)), Tol) && Close(P.Hawks, Num(Row, "p" + std::to_string(Y)), Tol);
	}
	return Ok;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_reed_ceiling_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 7 marshes x 3 lines", Lines.size() == 21);
	for (size_t L = 0; L + 2 < Lines.size(); L += 3)
	{
		const std::string& H = Lines[L];
		ReedSettings S;
		S.R = Num(H, "r"); S.ReedHectares = Num(H, "reed"); S.CranesPerHectare = Num(H, "perHa"); S.Attack = Num(H, "a");
		S.Handling = Num(H, "h"); S.Conversion = Num(H, "e"); S.Mortality = Num(H, "m");
		const std::string Tag = "marsh " + std::to_string(L / 3);
		Check(Tag + " valid", S.Valid());
		const ReedCeiling C(S);
		Check(Tag + " equilibrium", Close(C.CranesStar(), Num(H, "nstar"), 1e-12) && Close(C.HawksStar(), Num(H, "pstar"), 1e-12));
		Check(Tag + " Hopf capacity and hectares", Close(C.HopfCapacity(), Num(H, "kh"), 1e-12)
			&& Close(C.CycleHectares(), Num(H, "cycleHa"), 1e-12) && Close(C.HawkHectares(), Num(H, "hawkHa"), 1e-12));
		Check(Tag + " regime", static_cast<int>(C.Regime()) == marsh_test::Int(H, "regime"));
		Check(Tag + " trace", Close(C.Trace(), Num(H, "trace"), 1e-12));
		const double N0 = Num(H, "n0"), P0 = Num(H, "p0");
		const auto Rt = C.Rate(N0, P0);
		Check(Tag + " rate", Close(Rt[0], Num(H, "dn"), 1e-12) && Close(Rt[1], Num(H, "dp"), 1e-12));
		Check(Tag + " RK4 run", SameRun(C.Integrate(N0, P0, 60, 0.02), Lines[L + 1], 1e-9));
		const std::string& Nz = Lines[L + 2];
		Check(Tag + " noisy seasons", SameRun(C.Noisy(N0, P0, 40, marsh_test::Int(Nz, "seed")), Nz, 1e-7));
	}

	// Engine-free property checks mirroring ReedCeilingTest.
	const ReedCeiling D{ ReedSettings() };
	Check("default settings valid", ReedSettings().Valid());
	Check("default is stable with K_H about 128.6", D.Regime() == ReedRegime::Stable && Close(D.HopfCapacity(), 128.571428571, 1e-9));
	const auto Eq = D.Rate(D.CranesStar(), D.HawksStar());
	Check("equilibrium is a rest point", std::fabs(Eq[0]) < 1e-12 && std::fabs(Eq[1]) < 1e-12);
	Check("trace negative when stable, positive when cycling",
		D.Trace() < 0 && ReedCeiling(ReedSettings().WithReed(80)).Trace() > 0);
	const ReedCeiling Big(ReedSettings().WithReed(80));
	const ReedRun Cyc = Big.Integrate(50, 10, 400, 0.02), Calm = D.Integrate(50, 10, 400, 0.02);
	Check("paradox of enrichment: big reedbed swings, default settles", Big.Regime() == ReedRegime::Cycles
		&& Cyc.Amplitude() > 20 && Calm.Amplitude() < 1 && std::fabs(Calm.MaxCranes - D.CranesStar()) < 0.5);
	Check("small reedbed cannot feed hawks", ReedCeiling(ReedSettings().WithReed(5)).Regime() == ReedRegime::NoHawks
		&& ReedCeiling(ReedSettings().WithReed(5)).HawksStar() == 0);
	const ReedRun A = D.Noisy(40, 10, 30, 9), B = D.Noisy(40, 10, 30, 9), X = D.Noisy(40, 10, 30, 10);
	Check("same seed same seasons, new seed new seasons", A.Points.back().Cranes == B.Points.back().Cranes
		&& A.Points.back().Cranes != X.Points.back().Cranes);
	bool Grow = false;
	const ReedCeiling F = ReedCeiling::FromCohorts(CraneCohorts(CohortSettings()), ReedSettings(), Grow);
	CohortSettings Shrinking; Shrinking.AdultSurvival = 0.8;
	bool Shrink = true;
	(void)ReedCeiling::FromCohorts(CraneCohorts(Shrinking), ReedSettings(), Shrink);
	Check("fromCohorts takes r = ln lambda, needs a growing flock",
		Grow && Close(F.Settings().R, std::log(CraneCohorts(CohortSettings()).GetLambda()), 1e-15) && !Shrink);
	ReedSettings Bad1; Bad1.Conversion = 0.05;
	ReedSettings Bad2; Bad2.Attack = 0;
	Check("bad settings and runs rejected", !Bad1.Valid() && !Bad2.Valid() && !D.Integrate(1, 1, 10, 2).Ok
		&& !D.Integrate(-1, 1, 10, 0.1).Ok && !D.Noisy(1, 1, 0, 1).Ok);
	return marsh_test::Summary("marsh reed ceiling core");
}
