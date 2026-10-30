// SPDX-License-Identifier: MIT
// Lucky Feather parity: DaedalusLuckyFeatherCore.h reproduces every case in luckyfeather_parity.txt (written by the
// Java core via tools/minigames/LuckyFeatherParity.java): seeded simulation counts and mean steps exactly, closed
// form / exact chain / mean steps to 1e-12 relative, and the quest's carriers-needed answers.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public luckyfeather_core_test.cpp -o luckyfeather_core_test && ./luckyfeather_core_test luckyfeather_parity.txt
#include "DaedalusLuckyFeatherCore.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

using namespace daedalus::luckyfeather;

namespace {
int Checks = 0;
int Fails = 0;
void Expect(bool Ok, const std::string& What)
{
	++Checks;
	if (!Ok) { std::printf("FAIL %s\n", What.c_str()); ++Fails; }
}
bool Close(double A, double B, double Rel) { return std::fabs(A - B) <= Rel * std::fmax(1.0, std::fabs(B)); }
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
Aviary Make(int N, double R, int I)
{
	Settings S; S.Flock = N; S.Fitness = R; S.Start = I;
	return Aviary(S);
}

void UnitChecks()
{
	// 1. Neutral allele fixes with probability i / N.
	bool Neutral = true;
	for (int N : { 2, 5, 20, 100 })
		for (int I = 0; I <= N; ++I)
			Neutral = Neutral && Close(Make(N, 1.0, 1).Fixation(I), static_cast<double>(I) / N, 1e-12);
	Expect(Neutral, "neutral fixation is i/N");

	// 2. Closed form matches the exact (Thomas) chain solve.
	bool Chain = true;
	for (int N = 2; N <= 30; ++N)
		for (double R : { 0.5, 0.9, 0.999999, 1.0, 1.1, 1.5, 3.0 })
		{
			const Aviary A = Make(N, R, 1);
			const std::vector<double> P = A.Exact();
			for (int I = 0; I <= N; ++I) Chain = Chain && std::fabs(P[static_cast<size_t>(I)] - A.Fixation(I)) < 1e-10;
		}
	Expect(Chain, "closed form = exact chain for N 2..30");

	// 3. Selection tilts the odds and fixation rises with fitness.
	Expect(Make(20, 1.2, 1).Fixation() > 1.0 / 20 && Make(20, 0.8, 1).Fixation() < 1.0 / 20, "selection tilts odds");
	bool Rising = true; double Prev = 0;
	for (double R = 0.5; R <= 3; R += 0.25) { const double F = Make(20, R, 1).Fixation(); Rising = Rising && F > Prev; Prev = F; }
	Expect(Rising, "fixation rises with fitness");

	// 4. Big flock limit 1 - 1/r.
	bool Limit = true;
	for (double R : { 1.5, 2.0, 4.0 }) Limit = Limit && std::fabs(Make(5000, R, 1).Fixation() - (1 - 1 / R)) < 1e-9;
	Expect(Limit, "large-N limit 1 - 1/r");

	// 5. Quest: carriers needed is the smallest count reaching the target.
	Settings Av; Av.Fitness = 1.1;
	const Aviary Q(Av);
	bool Minimal = Q.GetSettings().Flock == AviaryCap;
	for (double T : { 0.1, 0.5, 0.9, 0.99 })
	{
		const int K = Q.CarriersNeeded(T);
		Minimal = Minimal && Q.Fixation(K) >= T - 1e-12 && (K == 0 || Q.Fixation(K - 1) < T);
	}
	Expect(Minimal && Q.CarriersNeeded(0) == 0 && Q.CarriersNeeded(1) == AviaryCap, "carriers needed minimal");

	// 6. Seeded runs replay; another seed differs; step cap is reported.
	const Aviary Rp = Make(20, 1.3, 3);
	const Result A1 = Rp.Simulate(300, 5), A2 = Rp.Simulate(300, 5), B1 = Rp.Simulate(300, 6);
	Expect(A1.FixedRuns == A2.FixedRuns && A1.MeanSteps == A2.MeanSteps
		&& (A1.FixedRuns != B1.FixedRuns || A1.MeanSteps != B1.MeanSteps), "seeded replay");
	Settings Cap; Cap.Flock = 200; Cap.Fitness = 1.0; Cap.Start = 100; Cap.MaxSteps = 5;
	const Result C1 = Aviary(Cap).Simulate(50, 1);
	Expect(C1.Capped == 50 && C1.FixedRuns == 0, "step cap reported");

	// 7. Bad tuning and inputs are rejected.
	Settings Bad; Bad.Flock = 1;
	Settings Bad2; Bad2.Fitness = 0;
	Settings Bad3; Bad3.Flock = 10; Bad3.Start = 11;
	Settings Good;
	Expect(!Bad.Valid() && !Bad2.Valid() && !Bad3.Valid() && Good.Valid(), "settings validation");
	const Aviary G = Make(10, 1.2, 1);
	Expect(G.Fixation(11) < 0 && G.CarriersNeeded(1.5) == -1 && G.Simulate(0, 1).FixedRuns == 0, "bad inputs rejected");
}
} // namespace

int main(int Argc, char** Argv)
{
	UnitChecks();
	if (Argc < 2) { std::printf("usage: %s luckyfeather_parity.txt\n", Argv[0]); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 1; }
	std::string Line;
	int Cases = 0;
	while (std::getline(In, Line))
	{
		if (Line.rfind("case", 0) != 0) continue;
		++Cases;
		const int N = std::atoi(Field(Line, "N").c_str());
		const double R = std::strtod(Field(Line, "r").c_str(), nullptr);
		const int I = std::atoi(Field(Line, "i").c_str());
		const int Runs = std::atoi(Field(Line, "runs").c_str());
		const long long Seed = std::atoll(Field(Line, "seed").c_str());
		const Aviary A = Make(N, R, I);
		const Result Res = A.Simulate(Runs, Seed);
		const std::string Tag = "case N=" + std::to_string(N) + " r=" + Field(Line, "r");
		Expect(Close(A.Fixation(), std::strtod(Field(Line, "fix").c_str(), nullptr), 1e-12), Tag + " fix");
		Expect(Close(A.Exact()[static_cast<size_t>(I)], std::strtod(Field(Line, "exact").c_str(), nullptr), 1e-12), Tag + " exact");
		Expect(Close(A.MeanSteps(), std::strtod(Field(Line, "steps").c_str(), nullptr), 1e-12), Tag + " steps");
		Expect(Res.FixedRuns == std::atoi(Field(Line, "simfixed").c_str()), Tag + " simfixed");
		Expect(Res.MeanSteps == std::strtod(Field(Line, "simsteps").c_str(), nullptr), Tag + " simsteps");
		Expect(Res.Capped == std::atoi(Field(Line, "capped").c_str()), Tag + " capped");
		Expect(A.CarriersNeeded(0.5) == std::atoi(Field(Line, "need50").c_str())
			&& A.CarriersNeeded(0.9) == std::atoi(Field(Line, "need90").c_str()), Tag + " carriers needed");
	}
	Expect(Cases == 20, "fixture has 20 cases");
	std::printf("%s luckyfeather core: %d checks, %d failed, %d parity cases\n", Fails ? "FAIL" : "OK", Checks, Fails, Cases);
	return Fails ? 1 : 0;
}
