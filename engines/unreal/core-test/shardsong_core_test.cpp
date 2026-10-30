// SPDX-License-Identifier: MIT
// G587 Shardsong Crossing (DaedalusShardsongCore.h): golden vectors (300 seeds x 3 difficulties, compared line for
// line with shardsong_golden.txt) plus property tests over 3000 seeds: every crossing solvable, scores 0..100,
// the best choice scores 100 and beats every other, totals bounded, play is deterministic, every call is ear-safe.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off shardsong_core_test.cpp
// Run from the repo root, or pass the golden file path; --write PATH rewrites it.
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusShardsongCore.h"

#include <cstdio>
#include <cstdlib>
#include <new>
#include <type_traits>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

using namespace daedalus::shardsong;

// Counts heap allocations so the play path can be checked allocation-free.
static long long Allocs = 0;
void* operator new(std::size_t N) { ++Allocs; if (void* P = std::malloc(N ? N : 1)) return P; throw std::bad_alloc(); }
void operator delete(void* P) noexcept { std::free(P); }
void operator delete(void* P, std::size_t) noexcept { std::free(P); }

static_assert(std::is_trivially_copyable<Game>::value, "Game is plain data (no heap)");

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

// Iteration 1: no-cost feedback. The breakdown adds up, the shortfall is the score gap, and the named cause is the
// largest of the three ways the call lost ground against the best one.
static void FeedbackTests()
{
	Crossing C; C.Count = 1; C.Seg[0] = { Habitat::Forest, 100 };
	const Feedback F = Advise(C, 5, Form::Trill);  // 630 Hz trill through forest: foliage and echo
	Check(F.Main == Cause::Absorbed && F.PitchHint == -1 && F.SwitchForm && F.ShortTenths == 150 - SnrTenths(C, 5, Form::Trill),
		"forest 630 trill: absorbed, try lower, switch to tone");
	Check(Advise(C, 1, Form::Tone).Main == Cause::None && Advise(C, 1, Form::Tone).ShortTenths == 0, "best call has no cause");
	Crossing W; W.Count = 1; W.Seg[0] = { Habitat::Water, 50 };  // surf masks the low bands at a water listener
	Check(Advise(W, 0, Form::Trill).Main == Cause::Masked, "low call over water: masked by surf");
	Crossing G; G.Count = 1; G.Seg[0] = { Habitat::Forest, 120 };
	const Choice GB = Best(G);
	const Form Other = GB.F == Form::Tone ? Form::Trill : Form::Tone;
	Check(Advise(G, GB.Band, Other).Main == Cause::Smeared, "right pitch, wrong form: smeared");
	for (std::uint64_t Token = 0; Token < 1000; ++Token)
	{
		const Game Gm = Game::Begin(TokenSeed(Token), static_cast<Difficulty>(Token % 3));
		for (int R = 0; R < Rounds; ++R)
			for (int Band = 0; Band < Bands; ++Band)
				for (int Fm = 0; Fm < 2; ++Fm)
				{
					const Crossing& X = Gm.Rounds_[R];
					const Breakdown B = Explain(X, Band, static_cast<Form>(Fm));
					const Feedback A = Advise(X, Band, static_cast<Form>(Fm));
					const bool Ok = B.Snr == SnrTenths(X, Band, static_cast<Form>(Fm))
						&& SourceLevel - B.Spread - B.Absorbed - B.Smeared == ReceivedTenths(X, Band, static_cast<Form>(Fm))
						&& A.ShortTenths == Best(X).Snr - B.Snr && A.ShortTenths >= 0 && A.Heard == (B.Snr >= HeardSnr)
						&& (A.ShortTenths == 0) == (A.Main == Cause::None)
						&& (A.ShortTenths > 100 || Score(X, Band, static_cast<Form>(Fm)) == (A.Heard ? 100 - A.ShortTenths : 0));
					if (!Ok) Check(false, "feedback adds up, token " + std::to_string(Token));
				}
	}
	Check(std::string(CauseName(Cause::Masked)).find("noise") != std::string::npos, "cause names");
}

// Iteration 2: properties, boundaries and fuzz. Longer paths never help any call; the 10 m and 400 m extremes work;
// raw (non-token) seeds are always solvable and well formed; Below stays in range.
static void BoundaryAndFuzz()
{
	Rng R(0xC0FFEEULL);
	for (int Trial = 0; Trial < 20000; ++Trial)
	{
		Crossing C;
		C.Count = 1 + R.Below(MaxSegments);
		for (int I = 0; I < C.Count; ++I) { C.Seg[I].H = static_cast<Habitat>(R.Below(HabitatCount)); C.Seg[I].LengthM = 10 * (1 + R.Below(9)); }
		const int Grow = R.Below(C.Count);
		Crossing Longer = C; Longer.Seg[Grow].LengthM += 10;
		bool Mono = true;
		for (int Band = 0; Band < Bands; ++Band)
			for (int Fm = 0; Fm < 2; ++Fm)
				Mono = Mono && SnrTenths(Longer, Band, static_cast<Form>(Fm)) < SnrTenths(C, Band, static_cast<Form>(Fm));
		if (!Mono) Check(false, "10 m more path lowers every call's SNR");
		const int N = 1 + R.Below(1000);
		const int V = R.Below(N);
		if (V < 0 || V >= N) Check(false, "Below in range");
	}
	Crossing Short; Short.Count = 1; Short.Seg[0] = { Habitat::Water, 10 };
	Check(Best(Short).Snr >= HeardSnr && ReceivedTenths(Short, 0, Form::Trill) == SourceLevel - 200 - 1, "10 m edge");
	Crossing Far; Far.Count = 4;
	for (int I = 0; I < 4; ++I) Far.Seg[I] = { Habitat::Water, 100 };
	Check(Far.TotalM() == MaxTotalM && ReceivedTenths(Far, 0, Form::Trill) == SourceLevel - 520 - 40, "400 m edge");
	int Bad = 0;
	Rng S(7);
	for (int Trial = 0; Trial < 30000; ++Trial)
	{
		Rng G(S.Next());
		const Crossing C = Generate(G, static_cast<Difficulty>(Trial % 3));
		if (C.Count < 1 || C.Count > MaxSegments || C.TotalM() > MaxTotalM || Best(C).Snr < HeardSnr) ++Bad;
	}
	Check(Bad == 0, "raw seeds: generator always solvable and in shape (" + std::to_string(Bad) + " bad)");
	Game G = Game::Begin(3, Difficulty::Hard);
	Check(G.Choose(Bands, Form::Tone) == -1 && G.Choose(0, Form::Tone) >= 0, "boundary bands");
	for (int I = 1; I < Rounds; ++I) G.Choose(0, Form::Tone);
	Check(G.Over() && G.Choose(0, Form::Tone) == -1 && &G.Current() == &G.Rounds_[Rounds - 1], "over is sticky; Current stays valid");
}

// Iteration 3: ear rule and no-heap play. Every call stays under 800 Hz at base and peak, soft (2 harmonics, low
// brightness), and a whole game (begin, every advice, every choice, every call) makes no heap allocation.
static void EarAndHeap()
{
	using namespace daedalus::earrule;
	for (int Band = 0; Band < Bands; ++Band)
		for (int Fm = 0; Fm < 2; ++Fm)
		{
			const CallSpec S = CallFor(Band, static_cast<Form>(Fm));
			const bool Soft = S.Valid() && S.Harmonics <= 2 && S.Brightness <= 0.25 && S.Sweep == 0 && Ok(S.BaseHz) && Ok(PeakHz(S))
				&& PeakHz(S) < MaxFundamentalHz && S.DurationMs() <= 800;
			Check(Soft, "soft ear-safe call band " + std::to_string(Band));
			Check(OctaveDrops(S, EarSafePeak(S)) == 0, "CallFor needs no further ear-rule drop");
		}
	const long long Before = Allocs;
	long long Sink = 0;
	for (std::uint64_t Token = 0; Token < 500; ++Token)
	{
		Game G = Game::Begin(TokenSeed(Token), static_cast<Difficulty>(Token % 3));
		while (!G.Over())
		{
			const Crossing& C = G.Current();
			for (int Band = 0; Band < Bands; ++Band) Sink += Advise(C, Band, Form::Trill).ShortTenths + static_cast<long long>(CallFor(Band, Form::Tone).BaseHz);
			const Choice B = Best(C);
			Sink += G.Choose(B.Band, B.F);
		}
	}
	const long long Made = Allocs - Before;  // read before building any message string
	Check(Made == 0 && Sink != 0, "play path makes no heap allocation (" + std::to_string(Made) + ")");
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
	FeedbackTests();
	BoundaryAndFuzz();
	EarAndHeap();
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
