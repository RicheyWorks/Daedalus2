// SPDX-License-Identifier: MIT
// G587 Shardsong Crossing (DaedalusShardsongCore.h): golden vectors (300 seeds x 3 difficulties, compared line for
// line with shardsong_golden.txt) plus property tests over 3000 seeds: every crossing solvable, scores 0..100,
// the best choice scores 100 and beats every other, totals bounded, play is deterministic, every call is ear-safe.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off shardsong_core_test.cpp
// Run from the repo root, or pass the golden file path; --write PATH rewrites it.
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusShardsongCore.h"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

using namespace daedalus::shardsong;

static int Failures = 0, Checks = 0;
static void Check(bool Ok, const std::string& What)
{
	++Checks;
	if (!Ok && ++Failures <= 25) std::printf("FAIL %s\n", What.c_str());
}

static const char* DiffName(Difficulty D) { return D == Difficulty::Easy ? "easy" : (D == Difficulty::Normal ? "normal" : "hard"); }

static std::vector<std::string> GoldenLines()
{
	std::vector<std::string> Out;
	Out.push_back("# shardsong_golden v1: token seed difficulty round | strips habitat:m | best band form snr_tenths");
	for (std::uint64_t Token = 0; Token < 300; ++Token)
		for (int Di = 0; Di < 3; ++Di)
		{
			const Difficulty D = static_cast<Difficulty>(Di);
			const Game G = Game::Begin(TokenSeed(Token), D);
			for (int R = 0; R < Rounds; ++R)
			{
				const Crossing& C = G.Rounds_[R];
				std::string L = std::to_string(Token) + " " + DiffName(D) + " " + std::to_string(R) + " |";
				for (int I = 0; I < C.Count; ++I) L += std::string(" ") + HabitatName(C.Seg[I].H) + ":" + std::to_string(C.Seg[I].LengthM);
				const Choice B = Best(C);
				L += " | " + std::to_string(BandHz[B.Band]) + (B.F == Form::Tone ? " tone " : " trill ") + std::to_string(B.Snr);
				Out.push_back(L);
			}
		}
	return Out;
}

static void Properties()
{
	Check(TokenSeed(1) != TokenSeed(2) && TokenSeed(7) == TokenSeed(7), "token seeds mix and repeat");
	Rng A(42), B(42);
	Check(A.Next() == B.Next() && A.Next() == B.Next(), "rng deterministic");
	Rng Z(0);
	Check(Z.Next() == 0xE220A8397B1DCDAFULL, "SplitMix64 reference value for seed 0");
	for (int Band = 0; Band < Bands; ++Band)
		for (int F = 0; F < 2; ++F)
		{
			const auto S = CallFor(Band, static_cast<Form>(F));
			Check(daedalus::earrule::Ok(S.BaseHz) && daedalus::earrule::Ok(daedalus::earrule::PeakHz(S)) && S.BaseHz == BandHz[Band],
				"call band " + std::to_string(BandHz[Band]) + " is ear-safe and unchanged");
		}
	int Unsolvable = 0, MaxTotal = 0;
	for (std::uint64_t Token = 0; Token < 3000; ++Token)
		for (int Di = 0; Di < 3; ++Di)
		{
			const Difficulty D = static_cast<Difficulty>(Di);
			Game G = Game::Begin(TokenSeed(Token), D), Same = Game::Begin(TokenSeed(Token), D), Worst = G;
			const int Min = Di + 1;
			while (!G.Over())
			{
				const Crossing& C = G.Current();
				const Choice Bst = Best(C);
				bool Shape = C.Count >= Min && C.Count <= Min + 1 && C.TotalM() <= MaxTotalM && C.TotalM() >= 10 * C.Count;
				for (int I = 0; I < C.Count; ++I) Shape = Shape && C.Seg[I].LengthM >= 10 && C.Seg[I].LengthM <= 120 && C.Seg[I].LengthM % 10 == 0;
				Check(Shape, "crossing shape token " + std::to_string(Token));
				if (Bst.Snr < HeardSnr) ++Unsolvable;
				for (int Band = 0; Band < Bands; ++Band)
					for (int F = 0; F < 2; ++F)
					{
						const int S = Score(C, Band, static_cast<Form>(F));
						if (S < 0 || S > 100 || SnrTenths(C, Band, static_cast<Form>(F)) > Bst.Snr) Check(false, "score bounds / best is max");
					}
				Check(Score(C, Bst.Band, Bst.F) == 100, "best choice scores 100");
				Check(Same.Choose(Bst.Band, Bst.F) == 100, "replay matches");
				Worst.Choose(5, Form::Trill);
				G.Choose(Bst.Band, Bst.F);
			}
			Check(G.Total() == 100 * Rounds && Same.Total() == G.Total(), "perfect play totals 500");
			Check(Worst.Total() >= 0 && Worst.Total() <= 100 * Rounds, "any play bounded");
			Check(G.Choose(0, Form::Tone) == -1, "no play after the game is over");
			if (Worst.Total() > MaxTotal) MaxTotal = Worst.Total();
		}
	Check(Unsolvable == 0, "every crossing is solvable (" + std::to_string(Unsolvable) + " unsolvable)");
	Game G = Game::Begin(1, Difficulty::Easy);
	Check(G.Choose(6, Form::Tone) == -1 && G.Choose(-1, Form::Tone) == -1 && G.Index == 0, "invalid band refused");
	// Hand-checked case: 100 m of forest, listener in forest. Spread 400, so a tone at 200 Hz receives 900-400-20 = 480
	// tenths against forest noise 340 (SNR 14 dB); a trill pays 50 more for reverb smear. 250 Hz ties 315 Hz at 15 dB.
	Crossing C; C.Count = 1; C.Seg[0] = { Habitat::Forest, 100 };
	Check(ReceivedTenths(C, 0, Form::Tone) == 480 && SnrTenths(C, 0, Form::Tone) == 140 && SnrTenths(C, 0, Form::Trill) == 90, "forest hand case");
	const Choice FB = Best(C);
	Check(FB.Band == 1 && FB.F == Form::Tone && FB.Snr == 150, "forest favours a low-mid tone");
	Crossing O; O.Count = 1; O.Seg[0] = { Habitat::Grass, 100 };
	const Choice OB = Best(O);
	Check(OB.F == Form::Trill, "open grass favours a trill");
}

int main(int argc, char** argv)
{
	const std::vector<std::string> Want = GoldenLines();
	if (argc > 2 && std::strcmp(argv[1], "--write") == 0)
	{
		std::ofstream Out(argv[2], std::ios::binary);
		for (const auto& L : Want) Out << L << "\n";
		std::printf("wrote %zu lines\n", Want.size());
		return 0;
	}
	Properties();
	const char* Path = argc > 1 ? argv[1] : "engines/unreal/core-test/shardsong_golden.txt";
	std::ifstream In(Path);
	if (!In) { std::printf("FAIL cannot open %s\n", Path); return 1; }
	std::string Line;
	std::size_t N = 0, Same = 0;
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') Line.pop_back();
		if (N < Want.size() && Line == Want[N]) ++Same;
		else if (N < Want.size()) Check(false, "golden line " + std::to_string(N) + ": file [" + Line + "] c++ [" + Want[N] + "]");
		++N;
	}
	Check(N == Want.size(), "golden line count " + std::to_string(N) + " vs " + std::to_string(Want.size()));
	std::printf("shardsong_core: golden %zu/%zu lines identical; %d checks, %d failures\n", Same, Want.size(), Checks, Failures);
	return Failures == 0 ? 0 : 1;
}
