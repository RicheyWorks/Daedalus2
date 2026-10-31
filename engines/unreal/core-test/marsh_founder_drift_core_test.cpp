// SPDX-License-Identifier: MIT
// G163 FounderDrift "Studbook" C++ port (G614), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_founder_drift_core_test.cpp
//   ./a.out marsh_founder_drift_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). Allele draws are all integer, so plan
// acceptance, outcomes, allele counts and the generation checksum must match exactly on every case. Diversity sums
// p^2 in a different order than Java's HashMap, and survival calls exp, so those compare to 1e-12.
#include "DaedalusMarshFounderDriftCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Int;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_founder_drift_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 24 cases", Lines.size() == 24);
	for (const std::string& L : Lines)
	{
		FounderDriftSettings S;
		S.Founders = static_cast<int>(Int(L, "founders"));
		S.Capacity = static_cast<int>(Int(L, "capacity"));
		S.Generations = static_cast<int>(Int(L, "generations"));
		S.Loci = static_cast<int>(Int(L, "loci"));
		S.MigrantPool = static_cast<int>(Int(L, "migrantPool"));
		S.Lethal = Num(L, "lethal");
		FounderDrift D(S, Int(L, "seed"));
		const std::string Tag = L.substr(0, L.find(" breedOk="));
		const int Plan = static_cast<int>(Int(L, "plan"));
		const int Mid = (S.Generations + 1) / 2;
		const bool BreedOk = Plan == 0 || D.Breed(Mid, Plan == 1 ? 1 : 2, Plan == 1 ? 1 : 3);
		const bool MigOk = D.Migrants(Plan == 2 ? 2 : 0);
		const bool BadOk = D.Breed(S.Generations + 1, 1, 1) || D.Breed(1, 0, 1) || D.Migrants(-1);
		Check(Tag + " plan accepted as in Java", BreedOk == (Int(L, "breedOk") == 1) && MigOk == (Int(L, "migOk") == 1)
			&& BadOk == (Int(L, "badOk") == 1));
		Check(Tag + " effective size and harmonic mean", FounderDrift::EffectiveSize(3, 7) == Num(L, "ne")
			&& FounderDrift::HarmonicMean({20.0, 2.0, 20.0}) == Num(L, "hm"));
		const DriftReport R = D.Run();
		Check(Tag + " ran", S.Valid() && R.Ok && static_cast<int>(R.Generations.size()) == S.Generations);
		if (!R.Ok) continue;
		long long Weighted = 0;
		for (const DriftGeneration& G : R.Generations)
			Weighted += (static_cast<long long>(G.Alleles) * 1000 + G.Migrants * 100 + G.Males * 10 + G.Females) * G.Index;
		Check(Tag + " expected retained", R.Expected == Num(L, "expected"));
		Check(Tag + " outcome, alleles and checksum exact", marsh_test::Field(L, "outcome") == DriftOutcomeName(R.Outcome)
			&& R.Generations[0].Alleles == Int(L, "a1") && R.Generations.back().Alleles == Int(L, "al")
			&& Weighted == Int(L, "weighted"));
		Check(Tag + " diversity and survival", Close(R.FounderDiversity, Num(L, "h0"), 1e-12)
			&& Close(R.Retained, Num(L, "retained"), 1e-12) && Close(R.Survival(0.8), Num(L, "survival"), 1e-12)
			&& Close(R.Generations[0].Diversity, Num(L, "d1"), 1e-12) && Close(R.Generations.back().Diversity, Num(L, "dl"), 1e-12));
	}

	// Engine-free unit checks mirroring FounderDriftTest.
	const FounderDriftSettings Def;
	FounderDrift D(Def, 9);
	Check("Ne = 4mf/(m+f)", FounderDrift::EffectiveSize(10, 10) == 20 && FounderDrift::EffectiveSize(0, 5) == 0
		&& FounderDrift::EffectiveSize(-1, 2) < 0);
	Check("harmonic mean: one bottleneck dominates", Close(FounderDrift::HarmonicMean({100.0, 2.0}), 400.0 / 102, 1e-15)
		&& FounderDrift::HarmonicMean({}) == 0 && FounderDrift::HarmonicMean({3.0, 0.0}) == 0);
	Check("seeded replay", D.Run().Retained == D.Run().Retained);
	Check("founders all unique: H0 = 1 - 1/(2n)", Close(D.Run().FounderDiversity, 1 - 1.0 / 40, 1e-12));
	Check("breed and migrants refuse bad input", !D.Breed(0, 1, 1) && !D.Breed(1, 15, 6) && !D.Migrants(3) && D.Migrants(2));
	DriftReport Ri = D.Run();
	Check("survival = base exp(-lethal F)", Close(Ri.Survival(1), std::exp(-Def.Lethal * Ri.Inbreeding()), 1e-15));
	FounderDriftSettings Bad; Bad.Founders = 1;
	FounderDriftSettings Bad2; Bad2.Lethal = -1;
	Check("bad settings rejected", !Bad.Valid() && !Bad2.Valid() && Def.Valid());
	return marsh_test::Summary("marsh founder drift core");
}
