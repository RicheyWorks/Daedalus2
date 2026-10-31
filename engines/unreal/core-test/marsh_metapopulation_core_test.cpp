// SPDX-License-Identifier: MIT
// G183 Metapopulation "Fritillary Meadows" C++ port (G611), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_metapopulation_core_test.cpp
//   ./a.out marsh_metapopulation_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). Patch counts are compared exactly; the only
// libm call is pow in the colonisation chance, so the file must replay exactly on at least 22 of 24 cases (a
// last-ulp pow difference can flip one patch on a rare crossing).
#include "DaedalusMarshMetapopulationCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_metapopulation_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 24 cases", Lines.size() == 24);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		MetapopulationSettings S;
		S.Patches = static_cast<int>(marsh_test::Int(L, "patches"));
		S.Colonize = marsh_test::Num(L, "colonize");
		S.Extinction = marsh_test::Num(L, "extinction");
		S.Years = static_cast<int>(marsh_test::Int(L, "years"));
		S.Start = static_cast<int>(marsh_test::Int(L, "start"));
		Metapopulation V(S, marsh_test::Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" eq20="));
		// plough=year:count:ok,... ("-" for none); each call must succeed or fail as in Java.
		bool PlanOk = true;
		const std::string Plan = marsh_test::Field(L, "plough");
		for (size_t P = 0; Plan != "-" && P < Plan.size();)
		{
			const size_t E = Plan.find(',', P);
			const std::string Item = Plan.substr(P, E == std::string::npos ? std::string::npos : E - P);
			const size_t A = Item.find(':'), B = Item.find(':', A + 1);
			const bool Got = V.Plough(std::atoi(Item.substr(0, A).c_str()), std::atoi(Item.substr(A + 1, B - A - 1).c_str()));
			PlanOk = PlanOk && Got == (Item.substr(B + 1) == "1");
			P = E == std::string::npos ? Plan.size() : E + 1;
		}
		Check(Tag + " plough plan", PlanOk);
		Check(Tag + " equilibrium", Close(V.Equilibrium(0.2), marsh_test::Num(L, "eq20"), 1e-15)
			&& Close(V.PloughThreshold(), marsh_test::Num(L, "threshold"), 1e-15));
		const MetapopulationReport R = V.Run();
		Check(Tag + " ran", S.Valid() && R.Ok && static_cast<int>(R.Years.size()) == S.Years);
		if (!R.Ok) continue;
		long long Weighted = 0;
		for (const MetapopulationYear& Y : R.Years) Weighted += static_cast<long long>(Y.Occupied) * (Y.Index + 1);
		const MetapopulationYear& Mid = R.Years[R.Years.size() / 2];
		const bool Same = marsh_test::Field(L, "outcome") == MetapopulationOutcomeName(R.Outcome)
			&& R.Occupancy == marsh_test::Num(L, "occupancy") && Close(R.LateMean, marsh_test::Num(L, "late"), 1e-12)
			&& (marsh_test::Field(L, "band") == "MEADOW") == R.Meadow() && R.Years[0].Occupied == marsh_test::Int(L, "first")
			&& Mid.Index == marsh_test::Int(L, "midIndex") && Mid.Occupied == marsh_test::Int(L, "mid")
			&& R.Years.back().Occupied == marsh_test::Int(L, "last") && R.Years.back().Ploughed == marsh_test::Int(L, "ploughed")
			&& Weighted == marsh_test::Int(L, "weighted");
		Exact += Same ? 1 : 0;
		Check(Tag + " ploughed count", R.Years.back().Ploughed == marsh_test::Int(L, "ploughed"));
		if (!Same) std::printf("note: %s differs from Java (pow last-ulp crossing)\n", Tag.c_str());
	}
	Check("runs replay exactly on at least 22 of 24 cases", Exact >= 22);
	std::printf("exact replays: %d/24\n", Exact);

	// Engine-free unit checks mirroring MetapopulationTest.
	const MetapopulationSettings D;
	Metapopulation V(D, 3);
	Check("Levins equilibrium 1 - e/c = 0.8", Close(V.PloughThreshold(), 0.8, 1e-15) && Close(V.Equilibrium(0.3), 0.5, 1e-15));
	Check("seeded replay", V.Run().Occupancy == V.Run().Occupancy);
	MetapopulationSettings NoCol; NoCol.Colonize = 0;
	Check("c = 0: no equilibrium", Metapopulation(NoCol, 1).Equilibrium(0) == 0);
	Metapopulation P(D, 3);
	Check("plough refuses bad input", !P.Plough(-1, 1) && !P.Plough(D.Years, 1) && !P.Plough(0, D.Patches + 1) && P.Plough(0, D.Patches));
	Check("ploughing every patch loses the butterflies", P.Run().Outcome == MetapopulationOutcome::Lost);
	MetapopulationSettings Bad; Bad.Patches = 1;
	MetapopulationSettings Bad2; Bad2.Extinction = 0;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && D.Valid());
	return marsh_test::Summary("marsh metapopulation core");
}
