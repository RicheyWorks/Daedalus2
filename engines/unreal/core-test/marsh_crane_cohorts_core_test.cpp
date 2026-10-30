// SPDX-License-Identifier: MIT
// G194 Crane Cohorts C++ port (G585), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_crane_cohorts_core_test.cpp
//   ./a.out marsh_crane_cohorts_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). Lambda, stable ages, reproductive values,
// elasticities and the matrix step must match to 1e-9 relative. Best release, adult equivalents and trend must match
// exactly. Projections use integer counts and the hash; only clutches above 40 chicks go through log/cos, so every
// projected year must match exactly on at least 95 % of years, and all within 2 % of the flock.
#include "DaedalusMarshCraneCohortsCore.h"
#include "marsh_parity.h"
#include <cstdlib>
#include <sstream>
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Num;

static CraneCohorts::Flock ParseFlock(const std::string& V)
{
	CraneCohorts::Flock F{};
	std::stringstream Ss(V);
	std::string Part;
	for (int I = 0; I < 4 && std::getline(Ss, Part, ','); ++I) F[I] = std::atoi(Part.c_str());
	return F;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_crane_cohorts_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 7 flocks x 2 lines", Lines.size() == 14);
	int Years = 0, Exact = 0;
	for (size_t L = 0; L + 1 < Lines.size(); L += 2)
	{
		const std::string& H = Lines[L];
		const std::string& P = Lines[L + 1];
		CohortSettings S;
		S.ChickSurvival = Num(H, "s0"); S.JuvenileSurvival = Num(H, "s1"); S.SubadultSurvival = Num(H, "s2");
		S.AdultSurvival = Num(H, "p"); S.SubadultFecundity = Num(H, "fs"); S.AdultFecundity = Num(H, "fa");
		S.Years = static_cast<int>(marsh_test::Int(H, "years"));
		const std::string Tag = "flock " + std::to_string(L / 2);
		Check(Tag + " valid", S.Valid());
		const CraneCohorts C(S);
		Check(Tag + " lambda", Close(C.GetLambda(), Num(H, "lambda"), 1e-9));
		Check(Tag + " trend", static_cast<int>(C.Trend()) == marsh_test::Int(H, "trend"));
		Check(Tag + " best release", C.BestRelease() == marsh_test::Int(H, "best"));
		bool Vecs = true, Elas = true;
		const CraneCohorts::Vec Stepped = C.Step({ 10, 20, 30, 40 });
		for (int I = 0; I < 4; ++I)
		{
			const std::string Si = std::to_string(I);
			Vecs = Vecs && Close(C.StableAges()[I], Num(H, "w" + Si), 1e-9) && Close(C.ReproductiveValue()[I], Num(H, "v" + Si), 1e-9)
				&& Close(Stepped[I], Num(H, "step" + Si), 1e-12);
			for (int J = 0; J < 4; ++J) Elas = Elas && Close(C.Elasticity(I, J), Num(H, "e" + Si + std::to_string(J)), 1e-9);
		}
		Check(Tag + " stable ages, reproductive value, step", Vecs);
		Check(Tag + " elasticities", Elas);
		const CraneCohorts::Flock Start = ParseFlock(marsh_test::Field(H, "start"));
		Check(Tag + " adult equivalents", C.AdultEquivalents(Start) == marsh_test::Int(H, "ae"));
		const CohortReport R = C.Project(Start, marsh_test::Int(P, "seed"));
		Check(Tag + " projection length", static_cast<long long>(R.Years.size()) == marsh_test::Int(P, "nyears"));
		Check(Tag + " outcome and flock", static_cast<int>(R.Outcome) == marsh_test::Int(P, "outcome")
			&& std::llabs(R.Flock - marsh_test::Int(P, "flock")) <= 0.02 * std::max<long long>(10, marsh_test::Int(P, "flock")));
		bool Near = true;
		for (const CohortYear& Y : R.Years)
		{
			const CraneCohorts::Flock W = ParseFlock(marsh_test::Field(P, "y" + std::to_string(Y.Index)));
			const int Want = W[0] + W[1] + W[2] + W[3];
			++Years;
			Exact += Y.Chicks == W[0] && Y.Juveniles == W[1] && Y.Subadults == W[2] && Y.Adults == W[3];
			Near = Near && std::abs(Y.Total() - Want) <= 0.02 * std::max(10, Want);
		}
		Check(Tag + " projected years near", Near);
	}
	Check("projected years identical on at least 95 %", Years > 0 && Exact * 20 >= Years * 19);

	// Engine-free property checks mirroring CraneCohortsTest.
	const CohortSettings D;
	const CraneCohorts Def(D);
	Check("default lambda 1.0290662633", Close(Def.GetLambda(), 1.0290662633, 1e-9));
	Check("drought adults: lambda 0.9605619165", Close(CraneCohorts(D.WithAdultSurvival(0.8)).GetLambda(), 0.9605619165, 1e-9));
	const double L = Def.GetLambda();
	const double EulerLotka = D.ChickSurvival * D.JuvenileSurvival * D.SubadultFecundity / (L * L * L)
		+ D.ChickSurvival * D.JuvenileSurvival * D.SubadultSurvival * D.AdultFecundity / (L * L * L * (L - D.AdultSurvival));
	Check("lambda solves Euler-Lotka", Close(EulerLotka, 1, 1e-9));
	CohortSettings Barren = D; Barren.SubadultFecundity = 0; Barren.AdultFecundity = 0;
	Check("no chicks: lambda is adult survival", Close(CraneCohorts(Barren).GetLambda(), 0.9, 1e-9));
	const CraneCohorts::Vec Aw = Def.Step(Def.StableAges());
	bool Eig = true;
	for (int I = 0; I < 4; ++I) Eig = Eig && Close(Aw[I], L * Def.StableAges()[I], 1e-10);
	Check("stable ages are the right eigenvector", Eig && Def.ReproductiveValue()[0] == 1);
	double ESum = 0;
	for (int I = 0; I < 4; ++I) for (int J = 0; J < 4; ++J) ESum += Def.Elasticity(I, J);
	Check("elasticities sum to 1", Close(ESum, 1, 1e-9));
	Check("best release is the adult", Def.BestRelease() == CraneCohorts::Adult);
	Check("adults are worth one adult each", Def.AdultEquivalents({ 0, 0, 0, 17 }) == 17);
	const CohortReport A = Def.Project({ 20, 10, 8, 30 }, 42), B = Def.Project({ 20, 10, 8, 30 }, 42);
	bool Same = A.Years.size() == B.Years.size();
	for (size_t I = 0; Same && I < A.Years.size(); ++I) Same = A.Years[I].Total() == B.Years[I].Total() && A.Years[I].Adults == B.Years[I].Adults;
	Check("same seed same flock", Same && A.Years.front().Total() == 68);
	Check("empty flock is extinct", Def.Project({ 0, 0, 0, 0 }, 1).Outcome == CohortOutcome::Extinct);
	CohortSettings Bad1 = D; Bad1.AdultSurvival = 1.2;
	CohortSettings Bad2 = D; Bad2.AdultSurvival = 0; Bad2.SubadultFecundity = 0; Bad2.AdultFecundity = 0;
	CohortSettings Bad3 = D; Bad3.Years = 0;
	Check("bad settings rejected", !Bad1.Valid() && !Bad2.Valid() && !Bad3.Valid() && D.Valid());
	Check("negative cohorts rejected", Def.AdultEquivalents({ -1, 0, 0, 0 }) == -1 && Def.Project({ 0, -2, 0, 0 }, 1).Years.empty());
	return marsh_test::Summary("marsh crane cohorts core");
}
