// SPDX-License-Identifier: MIT
// Prismheart cue kits (DaedalusCueKitCore.h): golden vectors (20 cabinet ids x 30 tokens, every cue plus streak cues
// for 3 and 8 days, compared line for line with cue_kit_golden.txt) and property tests over 50,000 kits.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off cue_kit_core_test.cpp
// Run from the repo root, or pass the golden file path; --write PATH rewrites it.
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusCueKitCore.h"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <set>
#include <string>
#include <vector>

using namespace daedalus::cuekit;

static int Failures = 0, Checks = 0;
static void Check(bool Ok, const std::string& What)
{
	++Checks;
	if (!Ok && ++Failures <= 25) std::printf("FAIL %s\n", What.c_str());
}

static const char* const Games[] = { "shardsong_crossing", "shardfall", "prismcairn", "wardens_accord", "facetlock",
	"prismvault", "lumenpath", "shardring", "glowmoss", "glimmerloom", "shadewatch", "spiritkite", "prismchime",
	"gantry_sweep", "fog_channel_pilot", "crane_cohorts", "reed_ceiling", "padovan_plinths", "dock_calipers", "lucky_feather" };
constexpr int GameCount = static_cast<int>(sizeof(Games) / sizeof(Games[0]));

static std::string Line(const Phrase& P)
{
	std::string L;
	for (int I = 0; I < P.Count; ++I) L += " " + std::to_string(P.N[I].Hz) + "/" + std::to_string(P.N[I].Ms) + "/" + std::to_string(P.N[I].GapMs);
	return L;
}

static std::vector<std::string> GoldenLines(bool V2)
{
	std::vector<std::string> Out;
	Out.push_back(V2 ? "# cue_kit_golden v2 (PyRandom 'cuekit|game|token'): game token root | cue: hz/ms/gap ..."
		: "# cue_kit_golden v1: game token root | cue: hz/ms/gap ...");
	for (int G = 0; G < GameCount; ++G)
		for (std::uint64_t T = 0; T < 30; ++T)
		{
			const Kit K = V2 ? MakeKitV2(Games[G], T) : MakeKit(KitSeed(Games[G], T));
			std::string L = std::string(Games[G]) + " " + std::to_string(T) + " " + std::to_string(K.Root) + " |";
			for (int C = 0; C < CueCount - 1; ++C) L += std::string(" ") + CueName(static_cast<Cue>(C)) + ":" + Line(K.Cues[C]) + " |";
			L += " streak3:" + Line(CueOf(K, Cue::Streak, 3)) + " | streak8:" + Line(CueOf(K, Cue::Streak, 8));
			Out.push_back(L);
		}
	return Out;
}

static bool InScale(const Kit& K, int Hz)
{
	for (int D = 0; D < Degrees; ++D) if (K.StepHz(D) == Hz) return true;
	return false;
}

static void Properties()
{
	Check(HashId("") == 0xCBF29CE484222325ULL && HashId("a") == 0xAF63DC4C8601EC8CULL, "FNV-1a 64 reference values");
	Rng Z(0);
	Check(Z.Next() == 0xE220A8397B1DCDAFULL, "SplitMix64 reference value for seed 0");
	Check(KitSeed("shardfall", 1) != KitSeed("shardfall", 2) && KitSeed("shardfall", 1) != KitSeed("prismcairn", 1)
		&& KitSeed("glowmoss", 5) == KitSeed("glowmoss", 5), "kit seeds differ by game and token and repeat");
	int Bad = 0;
	Rng R(99);
	for (int Trial = 0; Trial < 50000; ++Trial)
	{
		const Kit K = MakeKit(R.Next());
		bool Ok = K.NoteMs >= 90 && K.NoteMs <= 150 && K.GapMs >= 20 && K.GapMs <= 40;
		for (int C = 0; C < CueCount; ++C)
			for (int Days = 0; Days <= (C == 4 ? 12 : 0); ++Days)
			{
				const Phrase P = CueOf(K, static_cast<Cue>(C), Days);
				Ok = Ok && P.Count >= 2 && P.Count <= MaxNotes && P.DurationMs() <= 2000;
				for (int I = 0; I < P.Count; ++I)
				{
					const auto S = NoteCall(P.N[I]);
					Ok = Ok && InScale(K, P.N[I].Hz) && P.N[I].Hz >= 165 && P.N[I].Hz < 800
						&& daedalus::earrule::Ok(S.BaseHz) && daedalus::earrule::Ok(daedalus::earrule::PeakHz(S))
						&& S.BaseHz == P.N[I].Hz && S.Harmonics <= 2 && S.Brightness <= 0.25 && S.Sweep == 0;
					if (I > 0) Ok = Ok && P.N[I].Hz * 1 <= P.N[I - 1].Hz * 2 && P.N[I - 1].Hz <= P.N[I].Hz * 2;  // no leap past an octave
				}
			}
		const Phrase& G = K.Cues[1];
		for (int I = 1; I < G.Count; ++I) Ok = Ok && G.N[I].Hz > G.N[I - 1].Hz;
		const Phrase& M = K.Cues[2];
		Ok = Ok && M.Count == 2 && M.N[1].Hz < M.N[0].Hz && M.N[0].Hz * 3 <= M.N[1].Hz * 5;  // gentle fall: at most a major sixth
		const Phrase& W = K.Cues[3];
		Ok = Ok && W.N[W.Count - 1].Hz == 2 * K.Root;
		const Phrase S8 = CueOf(K, Cue::Streak, 8), S3 = CueOf(K, Cue::Streak, 3), S0 = CueOf(K, Cue::Streak, 0), S99 = CueOf(K, Cue::Streak, 99);
		Ok = Ok && S3.Count == 3 + W.Count && S8.Count == 8 + W.Count && S0.Count == W.Count && S99.Count == S8.Count
			&& S8.N[S8.Count - 1].Hz == 2 * K.Root && CueOf(K, Cue::Streak, -4).Count == W.Count;
		if (!Ok && ++Bad <= 3) std::printf("bad kit root %d note %d gap %d: good%s miss%s win%s s8 %d ms\n", K.Root, K.NoteMs, K.GapMs,
			Line(G).c_str(), Line(M).c_str(), Line(W).c_str(), S8.DurationMs());
	}
	Check(Bad == 0, "50,000 kits: in scale, under 800 Hz, soft, good rises, miss falls gently, win ends on the octave, streak grows to 8 (" + std::to_string(Bad) + " bad)");
	std::set<std::string> Seen;
	for (int G = 0; G < GameCount; ++G)
	{
		const Kit K = MakeKit(KitSeed(Games[G], 0));
		std::string L;
		for (int C = 0; C < CueCount - 1; ++C) L += Line(K.Cues[C]) + "|";
		Seen.insert(L);
	}
	Check(static_cast<int>(Seen.size()) == GameCount, "every listed cabinet has its own kit on token 0");
	int Roots_[Roots] = {};
	for (std::uint64_t T = 0; T < 6000; ++T) for (int Ri = 0; Ri < Roots; ++Ri) if (MakeKit(KitSeed("prismchime", T)).Root == RootHz[Ri]) ++Roots_[Ri];
	bool Spread = true;
	for (int Ri = 0; Ri < Roots; ++Ri) Spread = Spread && Roots_[Ri] > 800;
	Check(Spread, "roots spread evenly across tokens");
	// V2 (PyRandom): same musical rules, so the same checks hold for every V2 kit; seeds differ by game and token.
	Check(KitSeedV2("glowmoss", 7) == "cuekit|glowmoss|7" && KitSeedV2(nullptr, 0) == "cuekit||0", "V2 seed string");
	int BadV2 = 0;
	std::set<std::string> SeenV2;
	for (int G = 0; G < GameCount; ++G)
		for (std::uint64_t T = 0; T < 200; ++T)
		{
			const Kit K = MakeKitV2(Games[G], T);
			bool Ok = K.Cues[2].N[1].Hz < K.Cues[2].N[0].Hz && K.Cues[3].N[K.Cues[3].Count - 1].Hz == 2 * K.Root;
			for (int I = 1; I < K.Cues[1].Count; ++I) Ok = Ok && K.Cues[1].N[I].Hz > K.Cues[1].N[I - 1].Hz;
			for (int C = 0; C < CueCount; ++C)
			{
				const Phrase P = CueOf(K, static_cast<Cue>(C), 8);
				for (int I = 0; I < P.Count; ++I) Ok = Ok && InScale(K, P.N[I].Hz) && daedalus::earrule::Ok(daedalus::earrule::PeakHz(NoteCall(P.N[I])));
			}
			if (!Ok) ++BadV2;
			if (T == 0) SeenV2.insert(Line(K.Cues[0]) + Line(K.Cues[1]) + Line(K.Cues[2]) + Line(K.Cues[3]));
		}
	Check(BadV2 == 0 && static_cast<int>(SeenV2.size()) == GameCount, "V2 kits keep every rule; each cabinet distinct (" + std::to_string(BadV2) + " bad)");
}

static std::size_t Compare(const std::string& Path, const std::vector<std::string>& Want)
{
	std::ifstream In(Path);
	if (!In) { Check(false, "cannot open " + Path); return 0; }
	std::string L;
	std::size_t N = 0, Same = 0;
	while (std::getline(In, L))
	{
		if (!L.empty() && L.back() == '\r') L.pop_back();
		if (N < Want.size() && L == Want[N]) ++Same;
		else if (N < Want.size()) Check(false, Path + " line " + std::to_string(N) + ": file [" + L + "] c++ [" + Want[N] + "]");
		++N;
	}
	Check(N == Want.size(), Path + " line count");
	return Same;
}

int main(int argc, char** argv)
{
	const std::vector<std::string> Want = GoldenLines(false), WantV2 = GoldenLines(true);
	if (argc > 2 && std::strcmp(argv[1], "--write") == 0)  // V1 only; V2 is written by tools/minigames/cue_kit.py
	{
		std::ofstream Out(argv[2], std::ios::binary);
		for (const auto& L : Want) Out << L << "\n";
		std::printf("wrote %zu lines\n", Want.size());
		return 0;
	}
	Properties();
	const std::string Path = argc > 1 ? argv[1] : "engines/unreal/core-test/cue_kit_golden.txt";
	const std::string PathV2 = Path.substr(0, Path.size() - 4) + "_v2.txt";
	const std::size_t Same = Compare(Path, Want), SameV2 = Compare(PathV2, WantV2);
	std::printf("cue_kit_core: golden v1 %zu/%zu, v2 (Python reference) %zu/%zu lines identical; %d checks, %d failures\n",
		Same, Want.size(), SameV2, WantV2.size(), Checks, Failures);
	return Failures == 0 ? 0 : 1;
}
