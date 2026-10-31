// SPDX-License-Identifier: MIT
// Prismheart streak jingle (DaedalusStreakJingleCore.h): golden vectors from the Python reference (20 cabinets x 10
// tokens x streaks 0-9, streak_jingle_golden.txt) plus properties: grows by exactly one note per day and keeps the
// earlier notes, caps at 8, no repeated neighbour in the ladder, every note in scale and ear-safe, Almanac hook.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off streak_jingle_core_test.cpp
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusStreakJingleCore.h"

#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

using namespace daedalus;
using namespace daedalus::streakjingle;

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

static bool SamePrefix(const Phrase& A, const Phrase& B, int N)
{
	for (int I = 0; I < N; ++I) if (A.N[I].Hz != B.N[I].Hz || A.N[I].Ms != B.N[I].Ms || A.N[I].GapMs != B.N[I].GapMs) return false;
	return true;
}

static void Properties()
{
	Check(JingleSeed("glowmoss", 3) == "jingle|glowmoss|3", "seed string");
	int Bad = 0;
	for (int G = 0; G < GameCount; ++G)
		for (std::uint64_t T = 0; T < 100; ++T)
		{
			const Kit K = cuekit::MakeKitV2(Games[G], T);
			const Ladder L = MakeLadder(Games[G], T);
			const Phrase& W = K.Cues[static_cast<int>(cuekit::Cue::Win)];
			bool Ok = true;
			for (int I = 0; I < cuekit::MaxStreakNotes; ++I)
				Ok = Ok && L.Degree[I] >= 0 && L.Degree[I] <= 4 && (I == 0 || L.Degree[I] != L.Degree[I - 1]);
			Phrase Prev = Jingle(K, L, 0);
			Ok = Ok && Prev.Count == W.Count && SamePrefix(Prev, W, W.Count);
			for (int D = 1; D <= 12; ++D)
			{
				const Phrase P = Jingle(K, L, D);
				const int Added = D > 8 ? 8 : D;
				Ok = Ok && P.Count == Added + W.Count && P.Count <= cuekit::MaxNotes && P.DurationMs() <= 2000;
				if (D <= 8) Ok = Ok && SamePrefix(P, Prev, D - 1);  // grows, never reshuffles
				Ok = Ok && P.N[P.Count - 1].Hz == 2 * K.Root;      // still ends on the octave
				for (int I = 0; I < P.Count; ++I)
				{
					const auto S = cuekit::NoteCall(P.N[I]);
					bool InScale = false;
					for (int Dg = 0; Dg < cuekit::Degrees; ++Dg) InScale = InScale || K.StepHz(Dg) == P.N[I].Hz;
					Ok = Ok && InScale && earrule::Ok(S.BaseHz) && earrule::Ok(earrule::PeakHz(S)) && S.Harmonics <= 2 && S.Sweep == 0;
				}
				Prev = P;
			}
			Ok = Ok && Jingle(K, L, -3).Count == W.Count;
			if (!Ok) ++Bad;
		}
	Check(Bad == 0, "2,000 jingles: grow one note a day keeping the earlier notes, cap 8, end on the octave, in scale, ear-safe (" + std::to_string(Bad) + " bad)");
	// Almanac hook: cleared days 10-13 -> streak 4 on day 13 and on day 14 (not yet cleared), 0 on day 15.
	const std::set<std::int64_t> Cleared = { 8, 10, 11, 12, 13 };
	const int WinCount = cuekit::MakeKitV2("glowmoss", 1).Cues[3].Count;
	Check(almanac::Streak(Cleared, 13) == 4 && JingleForAlmanac("glowmoss", 1, Cleared, 13).Count == 4 + WinCount
		&& JingleForAlmanac("glowmoss", 1, Cleared, 14).Count == 4 + WinCount
		&& JingleForAlmanac("glowmoss", 1, Cleared, 15).Count == WinCount
		&& Line(JingleForAlmanac("glowmoss", 1, Cleared, 13)) == Line(JingleV2("glowmoss", 1, 4)), "Almanac streak drives the jingle");
	std::set<std::int64_t> Long;
	for (std::int64_t D = 100; D < 130; ++D) Long.insert(D);
	Check(JingleForAlmanac("shardfall", 2, Long, 129).Count == 8 + cuekit::MakeKitV2("shardfall", 2).Cues[3].Count, "30-day streak caps at 8 added notes");
}

int main(int argc, char** argv)
{
	Properties();
	std::vector<std::string> Want;
	Want.push_back("# streak_jingle_golden v1 (PyRandom 'jingle|game|token' over cue kit V2): game token days | hz/ms/gap ...");
	for (int G = 0; G < GameCount; ++G)
		for (std::uint64_t T = 0; T < 10; ++T)
			for (int D = 0; D < 10; ++D)
				Want.push_back(std::string(Games[G]) + " " + std::to_string(T) + " " + std::to_string(D) + " |" + Line(JingleV2(Games[G], T, D)));
	const std::string Path = argc > 1 ? argv[1] : "engines/unreal/core-test/streak_jingle_golden.txt";
	std::ifstream In(Path);
	if (!In) { std::printf("FAIL cannot open %s\n", Path.c_str()); return 1; }
	std::string L;
	std::size_t N = 0, Same = 0;
	while (std::getline(In, L))
	{
		if (!L.empty() && L.back() == '\r') L.pop_back();
		if (N < Want.size() && L == Want[N]) ++Same;
		else if (N < Want.size()) Check(false, "golden line " + std::to_string(N) + ": file [" + L + "] c++ [" + Want[N] + "]");
		++N;
	}
	Check(N == Want.size(), "golden line count");
	std::printf("streak_jingle_core: golden (Python reference) %zu/%zu lines identical; %d checks, %d failures\n", Same, Want.size(), Checks, Failures);
	return Failures == 0 ? 0 : 1;
}
