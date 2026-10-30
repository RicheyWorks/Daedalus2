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

// Ruleset V2 fixture: also records wind, the singing flock's band, and the best tone (for tone-only play).
static std::vector<std::string> GoldenLinesV2()
{
	std::vector<std::string> Out;
	Out.push_back("# shardsong_golden v2: token difficulty round | wind chorus_hz | strips habitat:m | best band form snr_tenths | best tone band snr_tenths");
	for (std::uint64_t Token = 0; Token < 300; ++Token)
		for (int Di = 0; Di < 3; ++Di)
		{
			const Difficulty D = static_cast<Difficulty>(Di);
			const Game G = Game::Begin(TokenSeed(Token), D, Ruleset::V2);
			for (int R = 0; R < Rounds; ++R)
			{
				const Crossing& C = G.Rounds_[R];
				std::string L = std::to_string(Token) + " " + DiffName(D) + " " + std::to_string(R) + " | " + WindName(C.Air) + " "
					+ (C.Chorus < 0 ? std::string("none") : std::to_string(BandHz[C.Chorus])) + " |";
				for (int I = 0; I < C.Count; ++I) L += std::string(" ") + HabitatName(C.Seg[I].H) + ":" + std::to_string(C.Seg[I].LengthM);
				const Choice B = Best(C), T = BestTone(C);
				L += " | " + std::to_string(BandHz[B.Band]) + (B.F == Form::Tone ? " tone " : " trill ") + std::to_string(B.Snr);
				L += " | " + std::to_string(BandHz[T.Band]) + " " + std::to_string(T.Snr);
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

// Iterations 4-6 (Ruleset V2): marsh and rock strips, wind and a singing flock per round, a gentle first round and a
// rising difficulty curve. V1 stays the default and is untouched (its golden file still matches line for line).
static void RulesetV2()
{
	Check(Game::Begin(5, Difficulty::Normal).Rules == Ruleset::V1, "V1 is the default ruleset");
	int Count[Bands][2] = {}, ToneBand[Bands] = {}, Total = 0, Bad = 0, HabSeen[HabitatCount] = {}, WindSeen[WindCount] = {};
	for (std::uint64_t Token = 0; Token < 3000; ++Token)
		for (int Di = 0; Di < 3; ++Di)
		{
			const Difficulty D = static_cast<Difficulty>(Di);
			Game G = Game::Begin(TokenSeed(Token), D, Ruleset::V2);
			const Game V1 = Game::Begin(TokenSeed(Token), D);
			bool AllCalmV1 = true;
			for (int R = 0; R < Rounds; ++R) AllCalmV1 = AllCalmV1 && V1.Rounds_[R].Air == Wind::Calm && V1.Rounds_[R].Chorus == -1
				&& static_cast<int>(V1.Rounds_[R].Listener()) < V1HabitatCount;
			if (!AllCalmV1) ++Bad;
			for (int R = 0; R < Rounds; ++R)
			{
				const Crossing& C = G.Rounds_[R];
				const Choice B = Best(C), T = BestTone(C);
				const int Base = Di + 1, MaxLen = R == 0 ? 60 : 10 * (4 + 2 * R);
				bool Ok = B.Snr >= HeardSnr && T.Snr >= HeardSnr && C.TotalM() <= MaxTotalM && T.Snr <= B.Snr;
				Ok = Ok && (R == 0 ? (C.Count == 1 && C.Air == Wind::Calm && C.Chorus == -1 && C.Seg[0].LengthM >= 20)
					: C.Count == Base + (R >= 3 ? 1 : 0)) && C.Chorus >= -1 && C.Chorus < Bands;
				for (int I = 0; I < C.Count; ++I)
				{
					Ok = Ok && C.Seg[I].LengthM >= 10 && C.Seg[I].LengthM <= MaxLen;
					++HabSeen[static_cast<int>(C.Seg[I].H)];
				}
				++WindSeen[static_cast<int>(C.Air)];
				if (!Ok) ++Bad;
				++Count[B.Band][static_cast<int>(B.F)]; ++ToneBand[T.Band]; ++Total;
				if (G.Choose(B.Band, B.F) != 100) ++Bad;
			}
		}
	Check(Bad == 0, "V2 crossings solvable (best and tone), gentle round 0, ramp shape, V1 still calm (" + std::to_string(Bad) + " bad)");
	bool AllSeen = true;
	for (int H = 0; H < HabitatCount; ++H) AllSeen = AllSeen && HabSeen[H] > 0;
	for (int W = 0; W < WindCount; ++W) AllSeen = AllSeen && WindSeen[W] > 0;
	Check(AllSeen, "V2 draws every habitat and wind");
	// Balance: no single answer dominates and every pitch band is the best answer sometimes.
	int MaxChoice = 0, Trills = 0;
	for (int Band = 0; Band < Bands; ++Band)
	{
		const int BandTotal = Count[Band][0] + Count[Band][1];
		Check(BandTotal * 100 >= 5 * Total, "V2 band " + std::to_string(BandHz[Band]) + " is the answer >= 5%");
		Check(ToneBand[Band] * 100 >= 5 * Total, "V2 tone-only band " + std::to_string(BandHz[Band]) + " >= 5%");
		for (int F = 0; F < 2; ++F) if (Count[Band][F] > MaxChoice) MaxChoice = Count[Band][F];
		Trills += Count[Band][1];
	}
	Check(MaxChoice * 100 <= 25 * Total, "V2 no answer above 25% (" + std::to_string(MaxChoice * 100 / Total) + "%)");
	Check(Trills * 100 >= 25 * Total && Trills * 100 <= 75 * Total, "V2 tone and trill both common");
	// Hand cases: wind adds low noise (halved in forest), the flock masks its band and half its neighbours, rock and marsh.
	Crossing W; W.Count = 1; W.Seg[0] = { Habitat::Grass, 100 };
	const int Calm = SnrTenths(W, 0, Form::Trill);
	W.Air = Wind::Gusty;
	Check(SnrTenths(W, 0, Form::Trill) == Calm - 80 && SnrTenths(W, 5, Form::Trill) == SnrTenths(Crossing(W), 5, Form::Trill)
		&& ReceivedTenths(W, 2, Form::Tone) == ReceivedTenths(W, 2, Form::Trill) - 40 + 0, "gusty: +8 dB at 200 Hz, tone blur doubled");
	Crossing F; F.Count = 1; F.Seg[0] = { Habitat::Forest, 50 }; F.Air = Wind::Gusty;
	Check(NoiseAt(F, 0) == 340 + 40, "forest shelter halves wind");
	Crossing K; K.Count = 1; K.Seg[0] = { Habitat::Rock, 50 }; K.Chorus = 2;
	Check(NoiseAt(K, 2) == 300 + 80 && NoiseAt(K, 1) == 300 + 40 && NoiseAt(K, 3) == 310 + 40 && NoiseAt(K, 0) == 300, "flock masks its band");
	Check(ReceivedTenths(K, 0, Form::Tone) - ReceivedTenths(K, 0, Form::Trill) == 15, "trill smears off rock (3 per 10 m)");
	Crossing M; M.Count = 1; M.Seg[0] = { Habitat::Marsh, 100 };
	Check(Best(M).Band <= 1 || Best(M).Band == 5, "marsh: frog chorus pushes calls out of the middle bands");
}

static std::size_t Compare(const std::string& Path, const std::vector<std::string>& Want)
{
	std::ifstream In(Path);
	if (!In) { Check(false, "cannot open " + Path); return 0; }
	std::string Line;
	std::size_t N = 0, Same = 0;
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') Line.pop_back();
		if (N < Want.size() && Line == Want[N]) ++Same;
		else if (N < Want.size()) Check(false, Path + " line " + std::to_string(N) + ": file [" + Line + "] c++ [" + Want[N] + "]");
		++N;
	}
	Check(N == Want.size(), Path + " line count " + std::to_string(N) + " vs " + std::to_string(Want.size()));
	return Same;
}

int main(int argc, char** argv)
{
	const std::vector<std::string> Want = GoldenLines(), WantV2 = GoldenLinesV2();
	if (argc > 3 && std::strcmp(argv[1], "--write") == 0)  // --write V1PATH V2PATH
	{
		std::ofstream Out(argv[2], std::ios::binary), Out2(argv[3], std::ios::binary);
		for (const auto& L : Want) Out << L << "\n";
		for (const auto& L : WantV2) Out2 << L << "\n";
		std::printf("wrote %zu + %zu lines\n", Want.size(), WantV2.size());
		return 0;
	}
	Properties();
	FeedbackTests();
	BoundaryAndFuzz();
	EarAndHeap();
	RulesetV2();
	const std::string Path = argc > 1 ? argv[1] : "engines/unreal/core-test/shardsong_golden.txt";
	const std::string PathV2 = Path.substr(0, Path.size() - 4) + "_v2.txt";  // shardsong_golden_v2.txt beside it
	const std::size_t Same = Compare(Path, Want), SameV2 = Compare(PathV2, WantV2);
	std::printf("shardsong_core: golden v1 %zu/%zu, v2 %zu/%zu lines identical; %d checks, %d failures\n", Same, Want.size(),
		SameV2, WantV2.size(), Checks, Failures);
	return Failures == 0 ? 0 : 1;
}
