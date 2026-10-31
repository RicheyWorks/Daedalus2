// SPDX-License-Identifier: MIT
// G176 ShoalHarvest "Net Quota" C++ port (G612), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_shoal_harvest_core_test.cpp
//   ./a.out marsh_shoal_harvest_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). The core uses only + - * / and min/max in
// Java's order, so every double is compared exactly (Java prints the shortest round-trip form; strtod reads it back).
#include "DaedalusMarshShoalHarvestCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_shoal_harvest_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 32 cases", Lines.size() == 32);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		ShoalHarvestSettings S;
		S.Capacity = Num(L, "capacity");
		S.Growth = Num(L, "growth");
		S.Noise = Num(L, "noise");
		S.Years = static_cast<int>(marsh_test::Int(L, "years"));
		S.Collapse = Num(L, "collapse");
		const ShoalHarvest H(S, marsh_test::Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" msy="));
		Check(Tag + " msy", H.Msy() == Num(L, "msy") && H.MsyEffort() == Num(L, "msyEffort"));
		const ShoalRule Rule = marsh_test::Field(L, "rule") == "QUOTA" ? ShoalRule::Quota : ShoalRule::Effort;
		const ShoalReport R = H.Run(Rule, Num(L, "level"));
		Check(Tag + " ran", S.Valid() && R.Ok && static_cast<int>(R.Years.size()) == S.Years);
		if (!R.Ok) continue;
		double Weighted = 0;
		for (const ShoalYear& Y : R.Years) Weighted += (Y.Shoal + Y.Catch) * (Y.Index + 1);
		const ShoalYear& Mid = R.Years[R.Years.size() / 2];
		const ShoalYear& Last = R.Years.back();
		const bool Same = marsh_test::Field(L, "outcome") == ShoalOutcomeName(R.Outcome) && R.Shoal == Num(L, "shoal")
			&& R.Total == Num(L, "total") && R.MeanCatch() == Num(L, "mean")
			&& (marsh_test::Field(L, "band") == "WETLAND") == R.Kelp() && R.Years[0].Shoal == Num(L, "b0")
			&& R.Years[0].Catch == Num(L, "c0") && Mid.Index == marsh_test::Int(L, "midIndex") && Mid.Shoal == Num(L, "bm")
			&& Mid.Catch == Num(L, "cm") && Last.Shoal == Num(L, "bl") && Last.Catch == Num(L, "cl")
			&& Weighted == Num(L, "weighted");
		Check(Tag + " replays exactly", Same);
		Exact += Same ? 1 : 0;
	}
	std::printf("exact replays: %d/32\n", Exact);

	// Engine-free unit checks mirroring ShoalHarvestTest.
	const ShoalHarvestSettings D;
	const ShoalHarvest H(D, 7);
	Check("MSY rK/4 = 150 and effort (r/2)/(1+r/2)", H.Msy() == 150 && marsh_test::Close(H.MsyEffort(), 0.3 / 1.3, 1e-15));
	Check("seeded replay", H.Run(ShoalRule::Effort, 0.2).Total == H.Run(ShoalRule::Effort, 0.2).Total);
	Check("no fishing: nothing landed", H.Run(ShoalRule::Quota, 0).Total == 0 && H.Run(ShoalRule::Effort, 0).Outcome == ShoalOutcome::Thriving);
	Check("taking everything collapses the shoal", H.Run(ShoalRule::Effort, 1).Outcome == ShoalOutcome::Collapsed);
	Check("bad rule rejected", !H.Run(ShoalRule::Effort, 1.5).Ok && !H.Run(ShoalRule::Quota, -1).Ok
		&& !H.Run(ShoalRule::Quota, INFINITY).Ok && !H.Run(ShoalRule::Quota, NAN).Ok);
	ShoalHarvestSettings Bad; Bad.Growth = 0;
	ShoalHarvestSettings Bad2; Bad2.Noise = 1;
	ShoalHarvestSettings Bad3; Bad3.Years = 0;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && !Bad3.Valid() && D.Valid());
	return marsh_test::Summary("marsh shoal harvest core");
}
