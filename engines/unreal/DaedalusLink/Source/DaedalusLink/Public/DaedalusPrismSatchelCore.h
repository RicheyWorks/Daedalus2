// SPDX-License-Identifier: MIT
// Prism Satchel + Warden Trials: the cross-game shard wallet and mastery seals for the 11 Prismheart games.
// Header-only C++17 port of tools/minigames/prism_satchel.py (Python rules are the authority); parity is checked by
// engines/unreal/core-test/prism_satchel_core_test.cpp against prism_satchel_parity.txt. Integer only, no RNG, no I/O.
#pragma once

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace daedalus::prism_satchel {

constexpr int HueCount = 5;
inline const std::array<const char*, HueCount> Hues = {"ember", "tide", "verdant", "gale", "umbra"};
inline const std::array<const char*, 7> Seals = {"none", "ember", "tide", "verdant", "gale", "umbra", "heartglass"};
enum SealIndex : int { SealNone = 0, SealEmber, SealTide, SealVerdant, SealGale, SealUmbra, SealHeartglass };
constexpr int ScoreCap = 4;
constexpr int PerfectBonus = 2;
constexpr const char* SaveTag = "PRISMSATCHEL1";
constexpr size_t SaveMax = 4096;

struct Payout
{
	const char* Game;
	int Hue;       // index into Hues
	int Divisor;   // score // Divisor shards, capped at ScoreCap
	int UmbraPar;  // hard win at or above this earns Umbra
	int HeartPar;  // hard win at or above this earns Heartglass; -1 means "a perfect run"
};

// Sorted by game id (the save writes seals in this order). Pars: Fair Par hard silver/gold (prism_fair_par_parity.txt).
inline const std::array<Payout, 11> Payouts = {{
	{"facetlock", 3, 40, 130, 160},
	{"glimmerloom", 1, 50, 120, 135},
	{"glowmoss", 2, 12, 29, -1},
	{"lumenpath", 0, 50, 140, 180},
	{"prismcairn", 2, 35, 105, 105},
	{"prismvault", 4, 40, 100, 200},
	{"shadewatch", 4, 40, 148, 163},
	{"shardfall", 0, 12, 34, 38},
	{"shardring", 1, 60, 188, 215},
	{"spiritkite", 3, 8, 22, 25},
	{"wardens_accord", 1, 15, 60, 65},
}};

inline const Payout* FindPayout(const std::string& Game)
{
	for (const Payout& P : Payouts)
		if (Game == P.Game) return &P;
	return nullptr;
}

inline int DifficultyIndex(const std::string& D)
{
	return D == "easy" ? 0 : D == "normal" ? 1 : D == "hard" ? 2 : -1;
}

inline int HueIndex(const std::string& H)
{
	for (int I = 0; I < HueCount; ++I)
		if (H == Hues[I]) return I;
	return -1;
}

inline int SealFor(const Payout& P, int Difficulty, long long Score, bool Won, bool Perfect)
{
	if (!Won) return SealEmber;
	if (Difficulty != 2) return Difficulty == 1 ? SealVerdant : SealTide;
	const bool Heart = P.HeartPar < 0 ? Perfect : Score >= P.HeartPar;
	if (Heart) return SealHeartglass;
	return Score >= P.UmbraPar ? SealUmbra : SealGale;
}

struct RecordResult
{
	bool Ok = false;
	long long Pay = 0;
	int Hue = 0;
	int Seal = 0;
	int Gained = 0;
};

class Satchel
{
public:
	std::array<long long, HueCount> Shards{};
	long long Runs = 0;
	std::map<std::string, int> SealsByGame;  // game id -> best seal index (std::map keeps id order)

	RecordResult Record(const std::string& Game, const std::string& Difficulty, long long Score, bool Won, bool Perfect)
	{
		RecordResult R;
		const Payout* P = FindPayout(Game);
		const int D = DifficultyIndex(Difficulty);
		if (!P || D < 0 || Score < 0 || (Perfect && !Won)) return R;
		const long long Share = Score / P->Divisor;
		long long Pay = Won ? (D + 1) + (Share < ScoreCap ? Share : ScoreCap) : ((Share / 2) < ScoreCap / 2 ? Share / 2 : ScoreCap / 2);
		if (Perfect) Pay += PerfectBonus;
		const int Seal = SealFor(*P, D, Score, Won, Perfect);
		auto It = SealsByGame.find(Game);
		const int Prev = It == SealsByGame.end() ? 0 : It->second;
		const int Gained = Seal > Prev ? Seal - Prev : 0;
		Pay += Gained;
		if (Gained) SealsByGame[Game] = Seal;
		Shards[P->Hue] += Pay;
		++Runs;
		R.Ok = true;
		R.Pay = Pay;
		R.Hue = P->Hue;
		R.Seal = Seal;
		R.Gained = Gained;
		return R;
	}

	// Cost per hue (0 = not in the cost). False, and nothing taken, when the cost is empty, negative or short.
	bool Spend(const std::array<long long, HueCount>& Cost)
	{
		bool Any = false;
		for (int H = 0; H < HueCount; ++H)
		{
			if (Cost[H] < 0) return false;
			if (Cost[H] > Shards[H]) return false;
			Any = Any || Cost[H] > 0;
		}
		if (!Any) return false;
		for (int H = 0; H < HueCount; ++H) Shards[H] -= Cost[H];
		return true;
	}

	int Heartglass() const
	{
		int N = 0;
		for (const auto& KV : SealsByGame) N += KV.second == SealHeartglass;
		return N;
	}

	std::string ToText() const
	{
		std::string S = std::string(SaveTag) + ";";
		for (int H = 0; H < HueCount; ++H) S += (H ? "," : "") + std::to_string(Shards[H]);
		S += ";" + std::to_string(Runs) + ";";
		bool First = true;
		for (const auto& KV : SealsByGame)
		{
			S += (First ? "" : ",") + KV.first + ":" + std::to_string(KV.second);
			First = false;
		}
		return S;
	}

	// Strict parse of ToText(); nullopt on anything else (matches Satchel.from_text raising ValueError).
	static std::optional<Satchel> FromText(const std::string& Raw)
	{
		if (Raw.size() > SaveMax) return std::nullopt;
		const char* Ws = " \t\r\n\f\v";
		const size_t B = Raw.find_first_not_of(Ws);
		if (B == std::string::npos) return std::nullopt;
		const std::string Text = Raw.substr(B, Raw.find_last_not_of(Ws) - B + 1);
		const std::vector<std::string> Parts = Split(Text, ';');
		if (Parts.size() != 4 || Parts[0] != SaveTag) return std::nullopt;
		const std::vector<std::string> Counts = Split(Parts[1], ',');
		if (Counts.size() != HueCount) return std::nullopt;
		Satchel S;
		for (int H = 0; H < HueCount; ++H)
		{
			if (!Digits(Counts[H], 9)) return std::nullopt;
			S.Shards[H] = std::stoll(Counts[H]);
		}
		if (!Digits(Parts[2], 9)) return std::nullopt;
		S.Runs = std::stoll(Parts[2]);
		if (!Parts[3].empty())
		{
			for (const std::string& Item : Split(Parts[3], ','))
			{
				const size_t C = Item.find(':');
				const std::string Game = Item.substr(0, C), Seal = C == std::string::npos ? "" : Item.substr(C + 1);
				if (!FindPayout(Game) || S.SealsByGame.count(Game) || !Digits(Seal, 2)) return std::nullopt;
				const int K = std::stoi(Seal);
				if (K < 1 || K >= static_cast<int>(Seals.size())) return std::nullopt;
				S.SealsByGame[Game] = K;
			}
		}
		if (S.ToText() != Text) return std::nullopt;
		return S;
	}

private:
	static std::vector<std::string> Split(const std::string& S, char Sep)
	{
		std::vector<std::string> Out(1);
		for (char C : S)
		{
			if (C == Sep) Out.emplace_back();
			else Out.back() += C;
		}
		return Out;
	}

	// Non-empty, ASCII digits only, at most MaxLen characters (longer is rejected rather than parsed).
	static bool Digits(const std::string& S, size_t MaxLen)
	{
		if (S.empty()) return false;
		for (char C : S)
			if (C < '0' || C > '9') return false;
		return S.size() <= MaxLen;
	}
};

}  // namespace daedalus::prism_satchel
