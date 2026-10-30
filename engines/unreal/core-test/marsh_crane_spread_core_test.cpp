// SPDX-License-Identifier: MIT
// G200 Crane Spread C++ port (G583), checked without Unreal:
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public marsh_crane_spread_core_test.cpp
//   ./a.out marsh_crane_spread_parity.txt
// Replays the Java-written golden vectors (MarshCoresParityTest.java). The kernel, MGF and c* must match to 1e-9 relative,
// and the deterministic run's fronts (exact) and bird totals to 1e-9. Noisy runs go through log/cos/exp, so libm
// last-ulp differences could in principle flip a draw: fronts must match within one cell and totals within 1 %, and
// almost every sampled year must match exactly.
#include "DaedalusMarshCraneSpreadCore.h"
#include "marsh_parity.h"
#include <string>
using namespace daedalus::marsh;
using marsh_test::Check;
using marsh_test::Close;
using marsh_test::Num;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "marsh_crane_spread_parity.txt";
	const std::vector<std::string> Lines = marsh_test::ParityLines(Path);
	Check("golden file has 6 tunings x 3 lines", Lines.size() == 18);
	int Sampled = 0, Exact = 0;
	for (size_t L = 0; L + 2 < Lines.size(); L += 3)
	{
		const std::string& Head = Lines[L];
		SpreadSettings S;
		S.Lambda = Num(Head, "lambda");
		S.Dispersal = Num(Head, "dispersal");
		S.Cell = Num(Head, "cell");
		S.Capacity = Num(Head, "capacity");
		S.Years = static_cast<int>(marsh_test::Int(Head, "years"));
		const std::string Tag = "lambda=" + marsh_test::Field(Head, "lambda") + " b=" + marsh_test::Field(Head, "dispersal");
		Check(Tag + " valid", S.Valid());
		const CraneSpread M(S);
		Check(Tag + " mgf", Close(M.Mgf(0.3 / S.Dispersal), Num(Head, "mgf"), 1e-9));
		Check(Tag + " c*", Close(M.SpreadingSpeed(), Num(Head, "cstar"), 1e-9));
		for (int Noisy = 0; Noisy < 2; ++Noisy)
		{
			const std::string& Row = Lines[L + 1 + Noisy];
			const SpreadReport R = Noisy ? M.Run(marsh_test::Int(Row, "seed")) : M.Run();
			const std::string T2 = Tag + (Noisy ? " noisy" : " det");
			Check(T2 + " has every year", R.Years.size() == static_cast<size_t>(S.Years) + 1);
			bool AllOk = true;
			for (int Y = 0; Y <= S.Years; Y += 5)
			{
				const double F = Num(Row, "front" + std::to_string(Y)), B = Num(Row, "birds" + std::to_string(Y));
				const SpreadYear& Got = R.Years[Y];
				if (Noisy)
				{
					++Sampled;
					Exact += Got.Front == F && Close(Got.Birds, B, 1e-9);
					AllOk = AllOk && std::fabs(Got.Front - F) <= S.Cell + 1e-12 && Close(Got.Birds, B, 1e-2);
				}
				else
					AllOk = AllOk && Got.Front == F && Close(Got.Birds, B, 1e-9);
			}
			Check(T2 + " sampled years", AllOk);
			Check(T2 + " speed", Noisy ? std::fabs(R.Speed - Num(Row, "speed")) <= 2 * S.Cell / (S.Years / 2) + 1e-12
				: Close(R.Speed, Num(Row, "speed"), 1e-9));
			const long long Reach = marsh_test::Int(Row, "reach5");
			Check(T2 + " year reached 5 km", Noisy ? (R.YearReached(5.0) == -1) == (Reach == -1)
				&& std::llabs(R.YearReached(5.0) - Reach) <= 1 : R.YearReached(5.0) == Reach);
		}
	}
	Check("noisy sampled years identical on at least 95 %", Sampled > 0 && Exact * 20 >= Sampled * 19);

	// Engine-free property checks mirroring CraneSpreadTest.
	const CraneSpread Def{ SpreadSettings() };
	Check("default settings valid", SpreadSettings().Valid());
	Check("kernel is a distribution: M(0) = 1", Close(Def.Mgf(0), 1, 1e-12));
	const double CLaplace = [] { // continuous Laplace kernel: M(s) = 1 / (1 - b^2 s^2), b = 1
		double Best = 1e300;
		for (int I = 1; I < 100000; ++I) { const double Sv = I * 1e-5; Best = std::fmin(Best, std::log(1.5 / (1 - Sv * Sv)) / Sv); }
		return Best; }();
	Check("c* near the continuous Laplace value", std::fabs(Def.SpreadingSpeed() - CLaplace) < 0.05 * CLaplace);
	SpreadSettings Short; Short.Years = 60;
	const SpreadReport Det = CraneSpread(Short).Run();
	Check("front speed approaches c* from below", Det.Speed > 0.7 * Def.SpreadingSpeed() && Det.Speed <= Def.SpreadingSpeed() * 1.02);
	bool Mono = true;
	for (size_t I = 1; I < Det.Years.size(); ++I) Mono = Mono && Det.Years[I].Front >= Det.Years[I - 1].Front;
	Check("deterministic front never retreats", Mono);
	SpreadSettings Shrink = Short; Shrink.Lambda = 0.9;
	const CraneSpread Sh(Shrink);
	Check("lambda below 1 does not spread", Sh.SpreadingSpeed() == 0 && Sh.Run().Years.back().Front < 2);
	const SpreadReport A = CraneSpread(Short).Run(42), B2 = CraneSpread(Short).Run(42), C = CraneSpread(Short).Run(43);
	bool Same = true, Differs = false;
	for (size_t I = 0; I < A.Years.size(); ++I) { Same = Same && A.Years[I].Birds == B2.Years[I].Birds; Differs = Differs || A.Years[I].Birds != C.Years[I].Birds; }
	Check("same seed same run, new seed new run", Same && Differs);
	Check("yearReached -1 when never reached", Det.YearReached(1e9) == -1 && Det.YearReached(0) == 0);
	SpreadSettings Bad1; Bad1.Cell = 5; SpreadSettings Bad2; Bad2.Years = 0; SpreadSettings Bad3; Bad3.Lambda = 0;
	SpreadSettings Bad4; Bad4.Cell = 0.001;
	Check("bad settings rejected", !Bad1.Valid() && !Bad2.Valid() && !Bad3.Valid() && !Bad4.Valid());
	return marsh_test::Summary("marsh crane spread core");
}
