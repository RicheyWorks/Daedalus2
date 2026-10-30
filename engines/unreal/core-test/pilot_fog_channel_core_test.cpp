// SPDX-License-Identifier: MIT
// G586 Fog Channel Pilot C++ core, checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public pilot_fog_channel_core_test.cpp
//   ./a.out pilot_fog_channel_parity.txt
#include "DaedalusPilotFogChannelCore.h"
#include "stable_parity.h"
using namespace daedalus::pilot;
using stable_test::Check;
using stable_test::Join;

static std::string Rows(const std::vector<std::vector<int>>& A)
{
	std::string Out;
	for (const auto& Row : A) Out += (Out.empty() ? "" : "/") + Join(Row);
	return Out;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "pilot_fog_channel_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const FogHarbour H = FogSeed("fog-" + std::to_string(s));
		const FogTrack B = FogBest(H), G = FogLoudestEcho(H);
		Lines.push_back("seed=fog-" + std::to_string(s) + " open=" + Join(H.Open) + " drift=" + Rows(H.Drift) + " echo=" + Rows(H.Echo)
			+ " heard=" + Join(H.Heard) + " best=" + std::to_string(B.Cost) + ":" + Join(B.Lanes) + " loudest=" + std::to_string(G.Cost)
			+ ":" + Join(G.Lanes));
	}
	stable_test::CheckParity(Path, Lines);

	// Judge + explain parity (pilot_fog_channel_judge_parity.txt next to the main file, also written by Java).
	std::string JudgePath = Path;
	JudgePath.replace(JudgePath.rfind("_parity.txt"), 11, "_judge_parity.txt");
	std::vector<std::string> JudgeLines;
	for (int s = 1; s <= 40; ++s)
	{
		const FogHarbour H = FogSeed("fog-" + std::to_string(s));
		const FogJudgement J = FogJudge(H, FogLoudestEcho(H).Lanes);
		std::string Why;
		for (const std::string& L : FogExplainText(H)) Why += (Why.empty() ? "" : " | ") + L;
		JudgeLines.push_back("seed=fog-" + std::to_string(s) + " par=" + std::to_string(J.Par) + " loudest_stars=" + std::to_string(J.Stars)
			+ " why=" + Why);
	}
	stable_test::CheckParity(JudgePath.c_str(), JudgeLines);

	// Tier parity (pilot_fog_channel_tiers_parity.txt, written by Java): calm-/fog-/pea-soup- seeds 1..30.
	std::string TierPath = Path;
	TierPath.replace(TierPath.rfind("_parity.txt"), 11, "_tiers_parity.txt");
	std::vector<std::string> TierLines;
	for (EFogTier Tier : { EFogTier::Calm, EFogTier::Fog, EFogTier::PeaSoup })
		for (int s = 1; s <= 30; ++s)
		{
			const std::string Seed = FogTierOf(Tier).SeedPrefix + std::to_string(s);
			const FogHarbour H = FogSeedTier(Seed, Tier);
			const FogTrack B = FogBest(H), G = FogLoudestEcho(H);
			TierLines.push_back("seed=" + Seed + " open=" + Join(H.Open) + " drift=" + Rows(H.Drift) + " echo=" + Rows(H.Echo) + " heard="
				+ Join(H.Heard) + " best=" + std::to_string(B.Cost) + ":" + Join(B.Lanes) + " loudest=" + std::to_string(G.Cost) + ":"
				+ Join(G.Lanes) + " loudest_stars=" + std::to_string(FogJudge(H, G.Lanes).Stars));
		}
	stable_test::CheckParity(TierPath.c_str(), TierLines);
	const FogHarbour H = FogSeed("fog-7");
	Check("best reading wins the quest", FogQuestDone(H, FogBest(H).Lanes));
	Check("trusting each echo never beats best", FogLoudestEcho(H).Cost >= FogBest(H).Cost);
	Check("missing lane is invalid", FogCost(H, std::vector<int>(H.Heard.size(), 9)) == FogInvalid);
	Check("wrong length is invalid", FogCost(H, std::vector<int>(H.Heard.size() + 1, 0)) == FogInvalid);
	Check("best reading earns three stars", FogJudge(H, FogBest(H).Lanes).Stars == 3);
	Check("invalid reading earns no stars", FogJudge(H, { 9 }).Stars == 0 && !FogJudge(H, { 9 }).QuestDone);

	// Validation and edges, mirroring the Java Harbour constructor.
	const FogHarbour Good{ { 2, 0 }, { { 0, 3 }, { 3, 0 } }, { { 1, 2, 3 }, { 3, 2, 1 } }, {} };
	Check("no blasts: empty best at cost 0", FogValid(Good) && FogBest(Good).Cost == 0 && FogBest(Good).Lanes.empty());
	Check("no blasts: empty explanation", FogExplainText(Good).empty() && FogJudge(Good, {}).Stars == 3);
	const FogHarbour One{ { 4 }, { { 1 } }, { { 0, 5, 2 } }, { 1, 2, 0 } };
	Check("one lane: forced track", FogBest(One).Cost == 4 + 5 + 1 + 2 + 1 + 0 && FogBest(One).Lanes == std::vector<int>({ 0, 0, 0 }));
	auto Bad = [&Good](auto Edit) { FogHarbour B = Good; B.Heard = { 0 }; Edit(B); return !FogValid(B) && FogBest(B).Cost == FogInvalid
		&& FogLoudestEcho(B).Cost == FogInvalid && FogCost(B, { 0 }) == FogInvalid && FogExplain(B).empty(); };
	Check("refuses no lanes", Bad([](FogHarbour& B) { B.Open.clear(); B.Drift.clear(); B.Echo.clear(); }));
	Check("refuses too many lanes", Bad([](FogHarbour& B) { B.Open.assign(5, 0); B.Drift.assign(5, std::vector<int>(5, 0));
		B.Echo.assign(5, std::vector<int>(3, 0)); }));
	Check("refuses too many blasts", Bad([](FogHarbour& B) { B.Heard.assign(FogMaxBlasts + 1, 0); }));
	Check("refuses negative opening", Bad([](FogHarbour& B) { B.Open[0] = -1; }));
	Check("refuses negative drift", Bad([](FogHarbour& B) { B.Drift[0][1] = -1; }));
	Check("refuses ragged drift", Bad([](FogHarbour& B) { B.Drift[1].pop_back(); }));
	Check("refuses short echo row", Bad([](FogHarbour& B) { B.Echo[0].pop_back(); }));
	Check("refuses negative echo", Bad([](FogHarbour& B) { B.Echo[0][1] = -2; }));
	Check("refuses unknown echo", Bad([](FogHarbour& B) { B.Heard[0] = 4; }));
	// Missed echoes: free everywhere, and the dockhand holds course through the silence.
	const FogHarbour Quiet{ { 0, 3 }, { { 0, 4 }, { 4, 0 } }, { { 5, 0, 2 }, { 0, 5, 2 } }, { 1, FogMissed, 0, FogMissed } };
	Check("dockhand holds course on a missed echo", FogLoudestEcho(Quiet).Lanes == std::vector<int>({ 0, 0, 1, 1 }));
	Check("missed echoes cost nothing", FogCost(Quiet, { 0, 0, 0, 0 }) == 5 && FogBest(Quiet).Cost == 4);
	Check("silence is explained", FogExplainText(Quiet)[1] == "blast 2: heard silence, hold lane 0 (+0 stay, +0 echo)");
	const FogHarbour Soup = FogSeedTier("pea-soup-1", EFogTier::PeaSoup); // pinned from python3 in the Java test
	Check("pea-soup-1 seeded like CPython", Soup.Open == std::vector<int>({ 2, 1, 5 })
		&& Soup.Heard == std::vector<int>({ 0, 3, 1, 3, 0, 2, 3, 0, 3, 3, 2, 3, 2 }));
	return stable_test::Finish();
}
