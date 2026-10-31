// SPDX-License-Identifier: MIT
// G142 AlleeRelease "Sky-Crane Return" C++ port (G616), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_allee_release_core_test.cpp
//   ./a.out marsh_allee_release_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). The core uses only + - * /, min/max and ceil
// in Java's order, so every value (growth doubles included) is compared exactly on every case.
#include "DaedalusMarshAlleeReleaseCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Int;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_allee_release_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 24 cases", Lines.size() == 24);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		AlleeReleaseSettings S;
		S.Budget = static_cast<int>(Int(L, "budget"));
		S.Years = static_cast<int>(Int(L, "years"));
		S.Survival = Num(L, "survival");
		S.MateHalf = Num(L, "mateHalf");
		S.Fledge = Num(L, "fledge");
		S.Capacity = Num(L, "capacity");
		S.Goal = static_cast<int>(Int(L, "goal"));
		AlleeRelease M(S, Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" oks="));
		const int B = S.Budget, Q = S.Budget / 4;
		const std::vector<std::vector<int>> Plans = {{0, B}, {0, Q, 1, Q, 2, Q, 3, Q}, {0, B / 2, S.Years, 1, 0, B + 1, 1, 0}};
		const std::vector<int>& Plan = Plans[static_cast<size_t>(Int(L, "plan"))];
		std::string Oks;
		for (size_t K = 0; K + 1 < Plan.size(); K += 2)
			Oks += std::string(Oks.empty() ? "" : ",") + (M.Release(Plan[K], Plan[K + 1]) ? "1" : "0");
		Check(Tag + " releases accepted as in Java", S.Valid() && Oks == marsh_test::Field(L, "oks") && M.Left() == Int(L, "left"));
		Check(Tag + " threshold and growth", M.Threshold() == Int(L, "threshold") && M.Growth(10) == Num(L, "g10")
			&& M.Growth(40) == Num(L, "g40"));
		const AlleeReport R = M.Run();
		Check(Tag + " ran", R.Ok && static_cast<int>(R.Years.size()) == S.Years);
		if (!R.Ok) continue;
		long long Weighted = 0;
		for (const AlleeYear& Y : R.Years)
			Weighted += (static_cast<long long>(Y.Flock) * 10000 + Y.Released * 1000 + Y.Nests * 10 + Y.Fledged) * (Y.Index + 1);
		const bool Same = marsh_test::Field(L, "outcome") == AlleeOutcomeName(R.Outcome) && R.Flock == Int(L, "flock")
			&& R.Peak == Int(L, "peak") && (marsh_test::Field(L, "band") == "WETLAND") == R.Wetland()
			&& R.Years.back().Nests == Int(L, "lastNests") && Weighted == Int(L, "weighted");
		Check(Tag + " replays exactly", Same);
		Exact += Same ? 1 : 0;
	}
	std::printf("exact replays: %d/24\n", Exact);

	// Engine-free unit checks mirroring AlleeReleaseTest.
	const AlleeReleaseSettings D;
	AlleeRelease M(D, 2);
	Check("Allee: small flocks shrink, mid flocks grow", M.Growth(5) < 1 && M.Growth(40) > 1 && M.Growth(0) == 0);
	Check("threshold is the first whole flock with growth >= 1", M.Threshold() > 1 && M.Growth(M.Threshold()) >= 1
		&& M.Growth(M.Threshold() - 1) < 1);
	Check("release refuses bad input", !M.Release(-1, 1) && !M.Release(D.Years, 1) && !M.Release(0, 0)
		&& !M.Release(0, D.Budget + 1) && M.Release(0, 30) && M.Left() == 10 && !M.Release(1, 11) && M.Release(0, 10) && M.Left() == 0);
	Check("seeded replay", M.Run().Flock == M.Run().Flock);
	Check("no releases: extinct", AlleeRelease(D, 2).Run().Outcome == AlleeOutcome::Extinct);
	AlleeReleaseSettings Bad; Bad.Capacity = 0;
	AlleeReleaseSettings Bad2; Bad2.Survival = 1.5;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && D.Valid() && !AlleeRelease(Bad, 1).Run().Ok);
	return marsh_test::Summary("marsh allee release core");
}
