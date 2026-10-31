// SPDX-License-Identifier: MIT
// Prismheart Fair Par (G603, Prismheart balance lane, Pythagoras; G600/G602 did the marsh cabinets) in plain C++17:
// header-only, standard library only, no Unreal types. A port of tools/minigames/fair_par.py, which stays the
// authority. A seeded casual bot plays Glowmoss Delve, Spiritkite Weave and Glimmerloom Ledger on every difficulty
// through their own cores (read-only on their rules). BRONZE is any win; SILVER and GOLD are the scores reached by at
// least 40 % and 10 % of the bot's winning rounds. G604 adds Lumenpath, Wardens' Accord and Facetlock with a mixed
// casual bot (coin flip: the game's demo move or a random legal move) (integer rank rule). Table() replays the whole par table, which must
// equal engines/unreal/core-test/prism_fair_par_parity.txt exactly (prism_fair_par_core_test.cpp).
// Bot choices use the stateless SplitMix64 hash of (seed, run, pick, salt) from FairPar.java, never the game RNG.
// Daedalus hook: Tier(game, difficulty, won, score) for the cabinet result screen, Satchel tiers and Almanac pars.
#pragma once
#include "DaedalusGlimmerloomCore.h"
#include "DaedalusFacetlockCore.h"
#include "DaedalusGlowmossCore.h"
#include "DaedalusLumenpathCore.h"
#include "DaedalusPrismcairnCore.h"
#include "DaedalusPrismvaultCore.h"
#include "DaedalusShadewatchCore.h"
#include "DaedalusShardfallCore.h"
#include "DaedalusSpiritkiteCore.h"
#include "DaedalusWardensAccordCore.h"
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace daedalus { namespace prismpar {

constexpr int Seeds = 400;
constexpr std::int64_t BotSeed = 600;
constexpr int StepLimit = 500;
constexpr int WinPercent[2] = { 40, 10 };
constexpr int GameCount = 11; // G603: glowmoss, spiritkite, glimmerloom; G604: lumenpath, wardens_accord, facetlock;
                               // G605: prismvault, shardfall, prismcairn; G606: shadewatch, shardring
// Shardring (last) has no PRNG port: its core takes every random choice from an Oracle, so its pars are Python-only.
// Table() replays the first ReplayCount games; the test checks the shardring rows for shape and tier order only.
constexpr int ReplayCount = GameCount - 1;

enum class Tier { None, Bronze, Silver, Gold };

struct Row
{
	std::string Game, Difficulty;
	int Bronze = 1, Silver = 0, Gold = 0;
	int Hits[3] = { 0, 0, 0 }; // per mille of all rounds
	int WinMedian = 0, BotWin = 0, DemoWin = 0, DemoMedian = 0;
	bool Separated = false;
};

inline double Uniform(std::int64_t Seed, int Run, int Pick, int Salt)
{
	std::uint64_t Z = static_cast<std::uint64_t>(Seed) + 0x9E3779B97F4A7C15ULL * static_cast<std::uint64_t>(static_cast<std::int64_t>(Run) + 1)
		+ 0xBF58476D1CE4E5B9ULL * static_cast<std::uint64_t>(static_cast<std::int64_t>(Pick) + 1)
		+ 0x94D049BB133111EBULL * static_cast<std::uint64_t>(static_cast<std::int64_t>(Salt) + 1);
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
	Z ^= Z >> 31;
	return static_cast<double>(Z >> 11) * 0x1.0p-53;
}
inline int Pick(std::int64_t Seed, int Run, int K, int Salt, int Bound)
{
	return std::min(Bound, static_cast<int>(Uniform(Seed, Run, K, Salt) * (Bound + 1)));
}

// --- bots (same choices as fair_par.py) ---
inline glowmoss::Action GlowmossBot(const glowmoss::Game& G, int Run, int K)
{
	using namespace glowmoss;
	if (G.Crystals >= G.Target || G.Row + 1 >= G.Diff->Rows) return { Kind::Climb, 0 };
	std::vector<int> Safe;
	for (int C = FirstDigCol(G.Col); C <= LastDigCol(G.Col, G.Diff->Cols); ++C)
	{
		const Landing L = Land(*G.Diff, G.Cells, G.Row + 1, C, G.Light);
		if (L.Light >= ClimbCost(L.Row)) Safe.push_back(C);
	}
	if (Safe.empty()) return { Kind::Climb, 0 };
	return { Kind::Dig, Safe[static_cast<size_t>(Pick(BotSeed, Run, K, 0, static_cast<int>(Safe.size()) - 1))] };
}

inline spiritkite::Action SpiritkiteBot(const spiritkite::Game& G, int Run, int K)
{
	using namespace spiritkite;
	const bool Home = G.Lanterns() >= G.Target;
	std::vector<int> Safe;
	for (int J = 0; J < G.Isles(); ++J)
	{
		const int W = G.Adj[static_cast<size_t>(G.At)][static_cast<size_t>(J)];
		if (W != 0 && G.Dist[static_cast<size_t>(J)][0] <= G.Wind - W) Safe.push_back(J);
	}
	if (!Home && !Safe.empty()) return { Kind::Fly, Safe[static_cast<size_t>(Pick(BotSeed, Run, K, 1, static_cast<int>(Safe.size()) - 1))] };
	if (G.At == 0) return { Kind::Land, 0 };
	int Best = -1, BestKey = 0;
	for (int U = 0; U < G.Isles(); ++U)
	{
		const int W = G.Adj[static_cast<size_t>(G.At)][static_cast<size_t>(U)];
		if (W == 0) continue;
		const int Key = W + G.Dist[static_cast<size_t>(U)][0];
		if (Best < 0 || Key < BestKey) { Best = U; BestKey = Key; }
	}
	return { Kind::Fly, Best };
}

inline glimmerloom::Action GlimmerloomBot(const glimmerloom::Game& G, int Run, int K)
{
	using namespace glimmerloom;
	for (size_t J = 0; J < G.Satchel.size(); ++J)
		if (G.Satchel[J] && !(static_cast<int>(J) == G.RumorHue && G.RumorRise)) return { Kind::Sell, static_cast<int>(J), G.Satchel[J] };
	const size_t H = static_cast<size_t>(G.RumorHue);
	if (G.RumorRise && G.Day < G.Diff->Days && G.Satchel[H] == 0)
	{
		const int Most = std::min(G.Purse / G.Prices[H], G.Diff->Satchel - G.Held());
		const int Q = Pick(BotSeed, Run, K, 2, std::max(0, Most));
		if (Q > 0) return { Kind::Buy, G.RumorHue, Q };
	}
	return { Kind::Rest, 0, 0 };
}

// --- G604: mixed casual bot (coin flip, salt 9: the game's demo move, else a random legal move) ---
inline bool FollowDemo(int Run, int K) { return Uniform(BotSeed, Run, K, 9) < 0.5; }

inline int LumenpathRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	lumenpath::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		lumenpath::Cell C = G.DemoAction();
		if (!DemoOnly && !FollowDemo(Run, K))
		{
			std::vector<lumenpath::Cell> Cells;
			for (int R = 0; R < G.Size(); ++R)
				for (int Cc = 0; Cc < G.Size(); ++Cc)
				{
					const char Ch = G.Grid[static_cast<size_t>(R)][static_cast<size_t>(Cc)];
					if (Ch != '*' && Ch != '#') Cells.push_back({ R, Cc });
				}
			C = Cells[static_cast<size_t>(Pick(BotSeed, Run, K, 10, static_cast<int>(Cells.size()) - 1))];
		}
		int Gained = 0;
		if (G.Toggle(C.first, C.second, Gained) != lumenpath::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

inline int WardensRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	wardens::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		std::pair<bool, int> A = G.DemoAction();
		if (!DemoOnly && !FollowDemo(Run, K))
		{
			std::vector<std::pair<bool, int>> Options = { { false, 0 }, { false, 1 }, { false, 2 } };
			for (int I = 0; I < static_cast<int>(G.Spirits.size()); ++I) if (G.Affordable(I)) Options.push_back({ true, I });
			A = Options[static_cast<size_t>(Pick(BotSeed, Run, K, 11, static_cast<int>(Options.size()) - 1))];
		}
		int Gained = 0;
		if ((A.first ? G.Summon(A.second, Gained) : G.Take(A.second, Gained)) != wardens::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

inline int FacetlockRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	facetlock::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		facetlock::Move M = G.DemoAction();
		if (!DemoOnly && !FollowDemo(Run, K))
		{
			const int N = G.Size();
			const int V = Pick(BotSeed, Run, K, 12, 4 * N - 1);
			M = facetlock::Move{ V % 2 == 0, (V / 2) % N, V / (2 * N) == 0 ? 1 : -1 };
		}
		int Gained = 0;
		if (G.Apply(M, Gained) != facetlock::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

// --- G605: same mixed bot (salts 13, 14, 15) ---
inline int PrismvaultRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	prismvault::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		prismvault::Game::Demo A = G.DemoAction();
		if (!DemoOnly && !FollowDemo(Run, K))
		{
			const std::vector<int>& C = G.Candidates;
			A = { true, C[static_cast<size_t>(Pick(BotSeed, Run, K, 13, static_cast<int>(C.size()) - 1))], {}, {} };
		}
		int Gained = 0;
		char Res = '=';
		if ((A.IsName ? G.Name(A.Shard, Gained) : G.Weigh(A.Left, A.Right, Res)) != prismvault::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

inline int ShardfallRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	shardfall::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		bool BankIt = G.DemoBank();
		if (!DemoOnly && !FollowDemo(Run, K)) BankIt = G.Bag.empty() || Pick(BotSeed, Run, K, 14, 1) == 1;
		int V = 0;
		shardfall::Game::Draw D = shardfall::Game::Draw::Value;
		if ((BankIt ? G.Bank(V) : G.DrawShard(D, V)) != shardfall::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

inline int PrismcairnRound(std::uint32_t Seed, const char* Difficulty, bool DemoOnly)
{
	prismcairn::Game G;
	if (!G.Start(Seed, Difficulty)) return -1;
	const int Run = static_cast<int>(Seed);
	for (int K = 0; K < StepLimit && !G.Over; ++K)
	{
		std::pair<int, int> M = prismcairn::BestMove(G.Cairns, G.Diff->TakeMax);
		if (!DemoOnly && !FollowDemo(Run, K))
		{
			std::vector<std::pair<int, int>> Options;
			for (int I = 0; I < static_cast<int>(G.Cairns.size()); ++I)
				for (int T = 1; T <= std::min(G.Diff->TakeMax, G.Cairns[static_cast<size_t>(I)]); ++T) Options.push_back({ I, T });
			M = Options[static_cast<size_t>(Pick(BotSeed, Run, K, 15, static_cast<int>(Options.size()) - 1))];
		}
		prismcairn::Game::Outcome O = prismcairn::Game::Outcome::WardenTakes;
		int Wc = 0, Wt = 0;
		if (G.Take(M.first, M.second, O, Wc, Wt) != prismcairn::Game::Act::Ok) return -1;
	}
	return G.Won ? G.Score : 0;
}

// --- G606: Shadewatch (salt 16). Shardring is fixture-only (see ReplayCount). ---
inline shadewatch::Action ShadewatchBot(const shadewatch::Game& G, int Run, int K)
{
	if (FollowDemo(Run, K)) return G.DemoAction();
	std::vector<shadewatch::Action> Options;
	for (int I = 0; I < static_cast<int>(G.Lanes.size()); ++I) Options.push_back({ shadewatch::Kind::Flare, I });
	Options.push_back({ shadewatch::Kind::Kindle, 0 });
	if (G.Light >= shadewatch::NovaCost) Options.push_back({ shadewatch::Kind::Nova, 0 });
	return Options[static_cast<size_t>(Pick(BotSeed, Run, K, 16, static_cast<int>(Options.size()) - 1))];
}

// One round: final score if won, else 0. Demo = the game's own DemoAction(). Returns -1 on a refused move.
template <class GameT, class BotT>
int PlayRound(std::uint32_t Seed, const char* Difficulty, BotT Bot)
{
	GameT G;
	if (!G.Start(Seed, Difficulty)) return -1;
	std::string Result;
	for (int K = 0; K < StepLimit && !G.Over; ++K)
		if (G.Step(Bot(G, static_cast<int>(Seed), K), Result) != GameT::Act::Ok) return -1;
	return G.Won ? G.Score : 0;
}

inline Row Calibrate(const std::string& Game, const std::string& Difficulty, const std::vector<int>& Scores, const std::vector<int>& Demo)
{
	Row R;
	R.Game = Game; R.Difficulty = Difficulty;
	const int N = static_cast<int>(Scores.size());
	std::vector<int> Won;
	for (int V : Scores) if (V > 0) Won.push_back(V);
	std::sort(Won.begin(), Won.end());
	const int W = static_cast<int>(Won.size());
	int Pars[3] = { 1, 0, 0 };
	for (int T = 0; T < 2; ++T) Pars[T + 1] = W ? Won[static_cast<size_t>(W - std::max(1, (W * WinPercent[T] + 99) / 100))] : 0;
	R.Bronze = Pars[0]; R.Silver = Pars[1]; R.Gold = Pars[2];
	for (int T = 0; T < 3; ++T)
	{
		int C = 0;
		for (int V : Scores) C += (V >= Pars[T] && V > 0) ? 1 : 0;
		R.Hits[T] = C * 1000 / N;
	}
	R.WinMedian = W ? Won[static_cast<size_t>((W - 1) / 2)] : 0;
	R.BotWin = W * 1000 / N;
	std::vector<int> D = Demo;
	int DemoWins = 0;
	for (int V : D) DemoWins += V > 0 ? 1 : 0;
	std::sort(D.begin(), D.end());
	R.DemoWin = DemoWins * 1000 / static_cast<int>(D.size());
	R.DemoMedian = D[static_cast<size_t>((D.size() - 1) / 2)];
	R.Separated = W > 0 && 0 < Won.front() && Won.front() < R.Silver && R.Silver < R.Gold;
	return R;
}

// The replayable par table (ReplayCount games x easy/normal/hard), in fair_par.py order. Ok false if any round refused a move.
inline std::vector<Row> Table(bool& Ok, int SeedCount = Seeds)
{
	static const char* const Diffs[3] = { "easy", "normal", "hard" };
	static const char* const Names[ReplayCount] = { "glowmoss", "spiritkite", "glimmerloom", "lumenpath", "wardens_accord", "facetlock",
		"prismvault", "shardfall", "prismcairn", "shadewatch" };
	std::vector<Row> Out;
	Ok = true;
	for (int Gi = 0; Gi < ReplayCount; ++Gi)
		for (const char* D : Diffs)
		{
			std::vector<int> S, De;
			for (int Seed = 0; Seed < SeedCount; ++Seed)
			{
				const std::uint32_t U = static_cast<std::uint32_t>(Seed);
				auto Demo = [](const auto& G, int, int) { return G.DemoAction(); };
				int A = 0, B = 0;
				if (Gi == 0) { A = PlayRound<glowmoss::Game>(U, D, GlowmossBot); B = PlayRound<glowmoss::Game>(U, D, Demo); }
				else if (Gi == 1) { A = PlayRound<spiritkite::Game>(U, D, SpiritkiteBot); B = PlayRound<spiritkite::Game>(U, D, Demo); }
				else if (Gi == 2) { A = PlayRound<glimmerloom::Game>(U, D, GlimmerloomBot); B = PlayRound<glimmerloom::Game>(U, D, Demo); }
				else if (Gi == 3) { A = LumenpathRound(U, D, false); B = LumenpathRound(U, D, true); }
				else if (Gi == 4) { A = WardensRound(U, D, false); B = WardensRound(U, D, true); }
				else if (Gi == 5) { A = FacetlockRound(U, D, false); B = FacetlockRound(U, D, true); }
				else if (Gi == 6) { A = PrismvaultRound(U, D, false); B = PrismvaultRound(U, D, true); }
				else if (Gi == 7) { A = ShardfallRound(U, D, false); B = ShardfallRound(U, D, true); }
				else if (Gi == 8) { A = PrismcairnRound(U, D, false); B = PrismcairnRound(U, D, true); }
				else { A = PlayRound<shadewatch::Game>(U, D, ShadewatchBot); B = PlayRound<shadewatch::Game>(U, D, Demo); }
				Ok = Ok && A >= 0 && B >= 0;
				S.push_back(std::max(0, A)); De.push_back(std::max(0, B));
			}
			Out.push_back(Calibrate(Names[Gi], D, S, De));
		}
	return Out;
}

// Tier for a finished round, from a par row (a lost round is None).
inline Tier TierOf(const Row& R, bool Won, int Score)
{
	if (!Won || Score < R.Bronze) return Tier::None;
	if (R.Gold > 0 && Score >= R.Gold) return Tier::Gold;
	if (R.Silver > 0 && Score >= R.Silver) return Tier::Silver;
	return Tier::Bronze;
}

} } // namespace daedalus::prismpar
