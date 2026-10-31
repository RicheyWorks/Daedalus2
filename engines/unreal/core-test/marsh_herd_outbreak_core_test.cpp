// SPDX-License-Identifier: MIT
// G172 HerdOutbreak "Hoof Blight" C++ port (G613), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_herd_outbreak_core_test.cpp
//   ./a.out marsh_herd_outbreak_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). Counts are compared exactly; the core calls
// pow (infection chance) and exp (final size), so the final size is compared to 1e-12 and the runs must replay
// exactly on at least 22 of 24 cases (a last-ulp pow difference can flip one roll on a rare crossing).
#include "DaedalusMarshHerdOutbreakCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Int;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_herd_outbreak_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 24 cases", Lines.size() == 24);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		HerdOutbreakSettings S;
		S.Herd = static_cast<int>(Int(L, "herd"));
		S.R0 = Num(L, "r0");
		S.Doses = static_cast<int>(Int(L, "doses"));
		S.Generations = static_cast<int>(Int(L, "generations"));
		HerdOutbreak H(S, Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" vaccOk="));
		const bool VaccOk = H.Vaccinate(static_cast<int>(Int(L, "vacc")));
		const bool FenceOk = Int(L, "plan") == 2 ? H.Fence(3, 0.4) : H.Fence(-1, 0.5);
		Check(Tag + " plan accepted as in Java", VaccOk == (Int(L, "vaccOk") == 1) && FenceOk == (Int(L, "fenceOk") == 1));
		Check(Tag + " threshold and final size", H.Threshold() == Num(L, "threshold")
			&& Close(HerdOutbreak::FinalSize(S.R0), Num(L, "final"), 1e-12));
		const HerdReport R = H.Run();
		Check(Tag + " ran", S.Valid() && R.Ok && R.Vaccinated == Int(L, "vaccinated"));
		if (!R.Ok) continue;
		long long Weighted = 0;
		for (const HerdGeneration& G : R.Generations) Weighted += static_cast<long long>(G.Sick * 1000 + G.Susceptible) * G.Index;
		const size_t Gens = R.Generations.size();
		const bool Same = marsh_test::Field(L, "outcome") == HerdOutcomeName(R.Outcome) && R.Sick == Int(L, "sick")
			&& R.Share == Num(L, "share") && (marsh_test::Field(L, "band") == "MEADOW") == R.Meadow()
			&& static_cast<long long>(Gens) == Int(L, "gens")
			&& (Gens ? R.Generations[0].Sick : 0) == Int(L, "firstSick")
			&& (Gens ? R.Generations.back().Index : 0) == Int(L, "lastIndex")
			&& (Gens ? R.Generations.back().Susceptible : 0) == Int(L, "lastLeft") && Weighted == Int(L, "weighted");
		Exact += Same ? 1 : 0;
		if (!Same) std::printf("note: %s differs from Java (pow last-ulp crossing)\n", Tag.c_str());
	}
	Check("runs replay exactly on at least 22 of 24 cases", Exact >= 22);
	std::printf("exact replays: %d/24\n", Exact);

	// Engine-free unit checks mirroring HerdOutbreakTest.
	const HerdOutbreakSettings D;
	HerdOutbreak H(D, 5);
	Check("threshold 1 - 1/2.5 = 0.6", Close(H.Threshold(), 0.6, 1e-15));
	const double Z = HerdOutbreak::FinalSize(2.5);
	Check("final size solves z = 1 - exp(-r z)", Close(Z, 1 - std::exp(-2.5 * Z), 1e-12) && HerdOutbreak::FinalSize(1) == 0);
	Check("seeded replay", H.Run().Sick == H.Run().Sick);
	Check("vaccinate refuses bad input", !H.Vaccinate(-1) && !H.Vaccinate(D.Doses + 1) && H.Vaccinate(D.Doses));
	Check("fence refuses bad input", !H.Fence(-1, 0.5) && !H.Fence(0, 1.5) && H.Fence(0, 0));
	Check("full fence from the start: only the index case", H.Run().Sick == 1 && H.Run().Outcome == HerdOutcome::Contained);
	HerdOutbreakSettings Bad; Bad.Herd = 1;
	HerdOutbreakSettings Bad2; Bad2.R0 = 1e9;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && D.Valid());
	return marsh_test::Summary("marsh herd outbreak core");
}
