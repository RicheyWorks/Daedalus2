// SPDX-License-Identifier: MIT
// Prism Feat ledger: replays prism_feat_parity.txt and walks every Satchel cabinet's result and save.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public prism_feat_core_test.cpp -o prism_feat_core_test && ./prism_feat_core_test prism_feat_parity.txt
#include "DaedalusPrismFeatCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using daedalus::prism_feat::CabinetFeat;
using daedalus::prism_feat::CrossFeat;
using daedalus::prism_feat::MakeRun;
using daedalus::prism_feat::Run;
using daedalus::prism_satchel::Payouts;
using daedalus::prism_satchel::Satchel;
using daedalus::prism_satchel::SealEmber;

namespace {
int Fails = 0;
void Expect(bool Ok, const std::string& What) {
	if (!Ok) { ++Fails; std::cerr << "FAIL " << What << '\n'; }
}
bool CrossName(const std::string& Name) {
	return Name == "one_mastered" || Name == "three_mastered" || Name == "one_heartglass";
}
}

int main(int Argc, char** Argv) {
	if (Argc < 2) { std::cerr << "usage: prism_feat_core_test prism_feat_parity.txt\n"; return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::cerr << "FAIL cannot read " << Argv[1] << '\n'; return 2; }

	Satchel Bag;
	Run Last;
	std::string Saved;
	std::string Line;
	int Feats = 0;
	while (std::getline(In, Line)) {
		if (Line.empty() || Line[0] == '#') continue;
		std::istringstream Row(Line);
		std::string Op;
		Row >> Op;
		if (Op == "RESET") { Bag = Satchel(); Last = Run(); Saved.clear(); continue; }
		if (Op == "RECORD") {
			std::string Game, Pace;
			long long Score = 0;
			int Won = 0, Perfect = 0;
			Row >> Game >> Pace >> Score >> Won >> Perfect;
			const auto Result = Bag.Record(Game, Pace, Score, Won != 0, Perfect != 0);
			Last = MakeRun(Game, Pace, Score, Won != 0, Perfect != 0, Result.Ok);
			continue;
		}
		if (Op == "SAVE") { Saved = Bag.ToText(); continue; }
		if (Op == "LOAD") {
			const auto Back = Satchel::FromText(Saved);
			Expect(static_cast<bool>(Back), "save reloaded");
			if (Back) {
				Expect(Back->ToText() == Saved, "save text is stable");
				Bag = *Back;
			}
			continue;
		}
		if (Op == "FEAT") {
			std::string Name;
			int Want = 0;
			Row >> Name >> Want;
			const bool Got = CrossName(Name) ? CrossFeat(Name, Bag) : CabinetFeat(Name, Last);
			Expect(Got == (Want != 0), "feat " + Name + " on " + Last.Game);
			++Feats;
			continue;
		}
		Expect(false, "unknown line " + Line);
	}
	Expect(Feats >= 16, "fixture checked the feat rows");

	Expect(Payouts.size() == 11, "eleven Prismheart cabinets");
	for (const auto& P : Payouts) {
		Satchel One;
		const auto Loss = One.Record(P.Game, "easy", 0, false, false);
		const Run LossRun = MakeRun(P.Game, "easy", 0, false, false, Loss.Ok);
		Expect(Loss.Ok && CabinetFeat("finish", LossRun) && !CabinetFeat("win", LossRun), std::string(P.Game) + " loss is a finish");
		const std::string Text = One.ToText();
		const auto Back = Satchel::FromText(Text);
		bool EmberSaved = false;
		if (Back) {
			const auto Found = Back->SealsByGame.find(P.Game);
			EmberSaved = Found != Back->SealsByGame.end() && Found->second == SealEmber;
		}
		Expect(static_cast<bool>(Back) && Back->ToText() == Text && EmberSaved, std::string(P.Game) + " save round trip");

		Satchel Hard;
		const long long Par = P.UmbraPar;
		const auto Win = Hard.Record(P.Game, "hard", Par, true, false);
		const Run WinRun = MakeRun(P.Game, "hard", Par, true, false, Win.Ok);
		Expect(Win.Ok && CabinetFeat("hard_win", WinRun) && CabinetFeat("par", WinRun) && !CabinetFeat("perfect", WinRun), std::string(P.Game) + " hard par");
	}

	Satchel Hearts;
	const auto Glass = Hearts.Record("glowmoss", "hard", 1, true, true);
	const Run GlassRun = MakeRun("glowmoss", "hard", 1, true, true, Glass.Ok);
	Expect(Glass.Ok && CabinetFeat("perfect", GlassRun) && CrossFeat("one_heartglass", Hearts), "glowmoss perfect is heartglass");

	if (Fails) std::cerr << Fails << " gap(s)\n";
	else std::cout << "prism feat: " << Feats << " fixture rows, " << Payouts.size() << " cabinets\n";
	return Fails == 0 ? 0 : 1;
}
