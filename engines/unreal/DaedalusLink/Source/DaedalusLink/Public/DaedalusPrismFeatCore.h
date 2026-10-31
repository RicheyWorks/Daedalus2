// SPDX-License-Identifier: MIT
// Prism Feat ledger. Header-only. Reads a finished run and the Prism Satchel.
// Five feats per cabinet, plus three that count seals across games. No RNG and no I/O.
#pragma once
#include "DaedalusPrismSatchelCore.h"
#include <string>

namespace daedalus::prism_feat {

struct Run {
	std::string Game;
	std::string Difficulty;
	long long Score = 0;
	bool Won = false;
	bool Perfect = false;
	bool Accepted = false;
};

inline Run MakeRun(const std::string& Game, const std::string& Difficulty, long long Score, bool Won, bool Perfect, bool Accepted) {
	Run R;
	R.Game = Game;
	R.Difficulty = Difficulty;
	R.Score = Score;
	R.Won = Won;
	R.Perfect = Perfect;
	R.Accepted = Accepted;
	return R;
}

inline bool CabinetFeat(const std::string& Name, const Run& R) {
	const prism_satchel::Payout* P = prism_satchel::FindPayout(R.Game);
	if (!R.Accepted || !P) return false;
	if (Name == "finish") return true;
	if (Name == "win") return R.Won;
	if (Name == "hard_win") return R.Won && R.Difficulty == "hard";
	if (Name == "par") return R.Won && R.Difficulty == "hard" && R.Score >= P->UmbraPar;
	if (Name == "perfect") return R.Won && R.Perfect;
	return false;
}

inline bool CrossFeat(const std::string& Name, const prism_satchel::Satchel& S) {
	if (Name == "one_mastered") return S.Mastered() >= 1;
	if (Name == "three_mastered") return S.Mastered() >= 3;
	if (Name == "one_heartglass") return S.Heartglass() >= 1;
	return false;
}

}  // namespace daedalus::prism_feat
