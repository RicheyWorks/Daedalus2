// SPDX-License-Identifier: MIT
// G188 Hawk-Dove "Rut on the Ridge" C++ port (G610), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_hawk_dove_core_test.cpp
//   ./a.out marsh_hawk_dove_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). The simulation is integer counting plus sums
// of exactly representable payoffs, so outcomes and hawk shares must match exactly; payoff means to 1e-12 relative.
#include "DaedalusMarshHawkDoveCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;

namespace {
bool Same(double A, const std::string& Want, double Rel)
{
	if (Want == "NaN") return std::isnan(A);
	return !std::isnan(A) && Close(A, std::strtod(Want.c_str(), nullptr), Rel);
}
} // namespace

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_hawk_dove_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 32 cases", Lines.size() == 32);
	for (const std::string& L : Lines)
	{
		HawkDoveSettings S;
		S.Herd = static_cast<int>(marsh_test::Int(L, "herd"));
		S.Value = marsh_test::Num(L, "value");
		S.Cost = marsh_test::Num(L, "cost");
		S.Base = marsh_test::Num(L, "base");
		S.Rounds = static_cast<int>(marsh_test::Int(L, "rounds"));
		S.Seasons = static_cast<int>(marsh_test::Int(L, "seasons"));
		const HawkDove Ridge(S, marsh_test::Int(L, "seed"));
		const HawkDoveReport R = Ridge.Run(static_cast<int>(marsh_test::Int(L, "start")));
		const std::string Tag = L.substr(0, L.find(" ess="));
		Check(Tag + " ran", S.Valid() && R.Ok && static_cast<int>(R.Seasons.size()) == S.Seasons);
		Check(Tag + " ess and expected payoffs", Close(Ridge.Ess(), marsh_test::Num(L, "ess"), 1e-15)
			&& Close(Ridge.ExpectedPayoff(true, 0.3), marsh_test::Num(L, "payHawk"), 1e-15)
			&& Close(Ridge.ExpectedPayoff(false, 0.3), marsh_test::Num(L, "payDove"), 1e-15));
		Check(Tag + " outcome", marsh_test::Field(L, "outcome") == HawkDoveOutcomeName(R.Outcome)
			&& R.Hawks == marsh_test::Num(L, "hawks") && Close(R.LateHawks, marsh_test::Num(L, "late"), 1e-12)
			&& (marsh_test::Field(L, "band") == "BARE") == R.Bare());
		for (int K = 0; K < 3 && R.Ok; ++K)
		{
			const std::string Ks = std::to_string(K);
			const int Idx = static_cast<int>(marsh_test::Int(L, "s" + Ks));
			const HawkDoveSeason& Q = R.Seasons[static_cast<size_t>(Idx - 1)];
			Check(Tag + " season " + std::to_string(Idx), Q.Index == Idx && Q.Hawks == marsh_test::Num(L, "h" + Ks)
				&& Same(Q.HawkPayoff, marsh_test::Field(L, "hp" + Ks), 1e-12) && Same(Q.DovePayoff, marsh_test::Field(L, "dp" + Ks), 1e-12));
		}
	}

	// Engine-free unit checks mirroring HawkDoveTest.
	const HawkDoveSettings D;
	const HawkDove Ridge(D, 7);
	Check("default ESS is V/C = 0.4", Close(Ridge.Ess(), 0.4, 1e-15));
	Check("at the ESS hawks and doves earn the same", Close(Ridge.ExpectedPayoff(true, 0.4), Ridge.ExpectedPayoff(false, 0.4), 1e-12));
	HawkDoveSettings Cheap; Cheap.Cost = 2;
	Check("cheap fights: hawks take over (ESS 1)", HawkDove(Cheap, 1).Ess() == 1);
	HawkDoveSettings Small; Small.Herd = 40; Small.Seasons = 40; Small.Rounds = 4;
	const HawkDove Sm(Small, 3);
	const HawkDoveReport A = Sm.Run(10), B = Sm.Run(10);
	Check("seeded replay", A.Ok && A.Hawks == B.Hawks && A.LateHawks == B.LateHawks);
	Check("all doves stay doves", Sm.Run(0).Outcome == HawkDoveOutcome::AllDove);
	Check("all hawks stay hawks", Sm.Run(40).Outcome == HawkDoveOutcome::AllHawk);
	Check("bad start refused", !Sm.Run(-1).Ok && !Sm.Run(41).Ok);
	HawkDoveSettings Bad; Bad.Herd = 1;
	HawkDoveSettings Bad2; Bad2.Value = 0;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && D.Valid());
	return marsh_test::Summary("marsh hawk dove core");
}
