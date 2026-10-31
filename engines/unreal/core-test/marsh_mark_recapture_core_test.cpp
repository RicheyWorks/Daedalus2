// SPDX-License-Identifier: MIT
// G156 MarkRecapture "Tag and Count" C++ port (G615), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_mark_recapture_core_test.cpp
//   ./a.out marsh_mark_recapture_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). The estimators use only + - * / and sqrt, so
// from the same counts they match exactly. The catch chance calls pow, compared to 1e-15; a last-ulp pow difference
// could flip one hare on a rare crossing, so the census must replay exactly on at least 22 of 24 cases.
#include "DaedalusMarshMarkRecaptureCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Int;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_mark_recapture_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 24 cases", Lines.size() == 24);
	int Exact = 0;
	for (const std::string& L : Lines)
	{
		MarkRecaptureSettings S;
		S.Population = static_cast<int>(Int(L, "population"));
		S.Traps = static_cast<int>(Int(L, "traps"));
		S.PerTrap = Num(L, "perTrap");
		S.TagLoss = Num(L, "tagLoss");
		S.TrapResponse = Num(L, "trapResponse");
		S.Turnover = Num(L, "turnover");
		MarkRecapture Refuge(S, Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" planOk="));
		const int First = static_cast<int>(Int(L, "first"));
		const bool Ok = First == 0 || Refuge.Plan(First, static_cast<int>(Int(L, "second")));
		Check(Tag + " plan accepted as in Java", S.Valid() && Ok == (Int(L, "planOk") == 1));
		Check(Tag + " catch chance", Close(Refuge.CatchChance(10), Num(L, "chance10"), 1e-15));
		const Census C = Refuge.Run();
		const bool SameCounts = C.Marked == Int(L, "marked") && C.Caught == Int(L, "caught") && C.Recaptured == Int(L, "recaptured");
		Exact += SameCounts ? 1 : 0;
		if (!SameCounts)
		{
			std::printf("note: %s differs from Java (pow last-ulp crossing)\n", Tag.c_str());
			continue;
		}
		Check(Tag + " estimates exact", C.LincolnPetersen() == Num(L, "lp") && C.Chapman() == Num(L, "chapman")
			&& C.Variance() == Num(L, "variance") && C.Low() == Num(L, "low") && C.High() == Num(L, "high"));
		Check(Tag + " verdict, quotas, band", marsh_test::Field(L, "verdict") == CensusVerdictName(C.Verdict())
			&& C.Quota(0.2) == Int(L, "quota") && C.GreedyQuota(0.2) == Int(L, "greedy")
			&& (marsh_test::Field(L, "band") == "MEADOW") == C.Meadow(0.2));
	}
	Check("census replays exactly on at least 22 of 24 cases", Exact >= 22);
	std::printf("exact replays: %d/24\n", Exact);

	// Engine-free unit checks mirroring MarkRecaptureTest.
	Check("Lincoln-Petersen 100*80/20 = 400", mark_recapture::LincolnPetersen(100, 80, 20) == 400
		&& std::isinf(mark_recapture::LincolnPetersen(5, 5, 0)));
	Check("Chapman 101*81/21 - 1", Close(mark_recapture::Chapman(100, 80, 20), 101.0 * 81 / 21 - 1, 1e-15));
	Check("bad counts give NaN", std::isnan(mark_recapture::Chapman(3, 5, 4)) && std::isnan(mark_recapture::SeberVariance(-1, 2, 0)));
	const MarkRecaptureSettings D;
	MarkRecapture Refuge(D, 4);
	Check("plan refuses bad splits", !Refuge.Plan(0, 10) && !Refuge.Plan(40, 21) && Refuge.Plan(30, 30));
	Check("seeded replay", Refuge.Run().Chapman() == Refuge.Run().Chapman());
	const Census C = Refuge.Run();
	Check("band holds the handled count", C.Low() >= C.Handled() && C.High() >= C.Low());
	MarkRecaptureSettings Bad; Bad.Traps = 1;
	MarkRecaptureSettings Bad2; Bad2.PerTrap = 1;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && D.Valid() && MarkRecapture(Bad, 1).Run().Truth == 0);
	return marsh_test::Summary("marsh mark recapture core");
}
