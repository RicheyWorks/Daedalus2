// SPDX-License-Identifier: MIT
// G608 Replay Notary (DiskSaver Island, quest q_replay_notary; Prismheart tournaments lane): a leaderboard entry
// is never a bare score. It is one text line naming the game, the seed and the player's own plan (a crane order,
// a quay plan or a golf card), plus the score the player claims. The notary lays the puzzle from the seed and
// replays the plan through the game's own core (G590 Gantry Sweep, G597 Buddy Berths, G598 Tidelinks Golf), so a
// score on the board is always the score the core gives, and a plan the core refuses keeps the core's own
// refusal code. A claim that does not match the replay is marked forged.
//
//   entry  = "notary1|" game "|" seed "|" plan "|" claim
//   game   = gantry-calm | gantry-rush | gantry-spread | gantry-storm | berths | golf
//   seed   = 1..256 printable ASCII bytes (0x20..0x7E), no '|'
//   plan   = gantry: ship indices "3,0,1,2,4"; berths: offsets or "-" (turn away) "0,8,-,4";
//            golf: holes split by '/', clubs by ',', "-" for an empty hole "D,9,P/W,P"; an empty plan is no moves
//   claim  = the claimed score (waits, turned away or strokes) in decimal, or "-" for none
//   number = 1..4 decimal digits, no leading zero (claims 1..9 digits)
//
// Result lines (FormatResult): "ok <game> <score fields> verdict=<v>", "forged <game> claim=<c> <score fields>
// verdict=<v>", "refused <game> <core code>[ hole=<k>]", "bad <reason>" with reasons long, fields, version, game,
// seed, claim, plan. Golden file: tools/streaming/replay_notary_parity.py.
// Header-only C++17; no Unreal includes, no exceptions, no RTTI; the three cores are used unchanged.
#pragma once
#include "DaedalusDiskSaverBuddyBerthsCore.h"
#include "DaedalusDiskSaverGantrySweepCore.h"
#include "DaedalusDiskSaverTidelinksGolfCore.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace ReplayNotary {

constexpr std::size_t MaxEntryBytes = 8192, MaxSeedBytes = 256, MaxNumberDigits = 4, MaxClaimDigits = 9;

enum class Status { Ok, Forged, Refused, Bad };
enum class Bad { None, Long, Fields, Version, Game, Seed, Claim, Plan };
enum class Game { GantryCalm, GantryRush, GantrySpread, GantryStorm, Berths, Golf };

inline const char* BadName(Bad B) {
    switch (B) {
        case Bad::None: return "none";
        case Bad::Long: return "long";
        case Bad::Fields: return "fields";
        case Bad::Version: return "version";
        case Bad::Game: return "game";
        case Bad::Seed: return "seed";
        case Bad::Claim: return "claim";
        case Bad::Plan: return "plan";
    }
    return "?";
}

static const char* const GameNames[6] = {"gantry-calm", "gantry-rush", "gantry-spread", "gantry-storm", "berths", "golf"};
inline const char* GameName(Game G) { return GameNames[static_cast<int>(G)]; }

struct Result {
    Status S = Status::Bad;
    Bad Why = Bad::Fields;
    Game G = Game::GantryCalm;
    std::string Refusal;  // the core's own refusal code (Status::Refused)
    std::size_t BadHole = 0;  // golf refusals
    std::int64_t Score = 0;  // waits, turned away or strokes
    std::int64_t Travel = 0, ToPar = 0;  // gantry travel; golf strokes against par
    std::int64_t Claim = -1;  // -1 = no claim
    std::string Verdict;
};

namespace Detail {

inline std::vector<std::string> Split(const std::string& S, char D) {
    std::vector<std::string> Out(1);
    for (char C : S) {
        if (C == D)
            Out.emplace_back();
        else
            Out.back() += C;
    }
    return Out;
}

// Decimal 0..10^Digits - 1: 1..Digits digits, no sign, no leading zero.
inline bool Number(const std::string& S, std::size_t Digits, std::int64_t& V) {
    if (S.empty() || S.size() > Digits || (S.size() > 1 && S[0] == '0')) return false;
    V = 0;
    for (char C : S) {
        if (C < '0' || C > '9') return false;
        V = V * 10 + (C - '0');
    }
    return true;
}

// Comma list of numbers ("-" allowed when Dash); an empty string is an empty list.
inline bool Numbers(const std::string& S, bool Dash, std::vector<std::int64_t>& Out) {
    Out.clear();
    if (S.empty()) return true;
    for (const std::string& T : Split(S, ',')) {
        std::int64_t V = 0;
        if (Dash && T == "-")
            Out.push_back(-1);
        else if (Number(T, MaxNumberDigits, V))
            Out.push_back(V);
        else
            return false;
    }
    return true;
}

inline bool GolfCard(const std::string& S, TidelinksGolf::Card& Out) {
    Out.clear();
    if (S.empty()) return true;
    for (const std::string& H : Split(S, '/')) {
        TidelinksGolf::Clubs Cs;
        if (H != "-") {
            for (const std::string& T : Split(H, ',')) {
                if (T.size() != 1) return false;
                Cs.push_back(TidelinksGolf::ClubIndex(T[0]));  // -1 for an unknown code: the core refuses it as club
            }
        }
        Out.push_back(Cs);
    }
    return true;
}

inline void Finish(Result& R) {
    R.S = R.Claim >= 0 && R.Claim != R.Score ? Status::Forged : Status::Ok;
    R.Why = Bad::None;
}

inline void Refuse(Result& R, const char* Code) {
    R.S = Status::Refused;
    R.Why = Bad::None;
    R.Refusal = Code;
}

}  // namespace Detail

inline Result Notarise(const std::string& Entry) {
    Result R;
    auto Fail = [&R](Bad B) {
        R.S = Status::Bad;
        R.Why = B;
        return R;
    };
    if (Entry.size() > MaxEntryBytes) return Fail(Bad::Long);
    const std::vector<std::string> F = Detail::Split(Entry, '|');
    if (F.size() != 5) return Fail(Bad::Fields);
    if (F[0] != "notary1") return Fail(Bad::Version);
    int Gi = -1;
    for (int I = 0; I < 6; ++I)
        if (F[1] == GameNames[I]) Gi = I;
    if (Gi < 0) return Fail(Bad::Game);
    R.G = static_cast<Game>(Gi);
    const std::string& Seed = F[2];
    if (Seed.empty() || Seed.size() > MaxSeedBytes) return Fail(Bad::Seed);
    for (char C : Seed)
        if (static_cast<unsigned char>(C) < 0x20 || static_cast<unsigned char>(C) > 0x7E) return Fail(Bad::Seed);
    if (F[4] != "-" && !Detail::Number(F[4], MaxClaimDigits, R.Claim)) return Fail(Bad::Claim);
    const std::string& P = F[3];
    if (R.G == Game::Golf) {
        TidelinksGolf::Card C;
        if (!Detail::GolfCard(P, C)) return Fail(Bad::Plan);
        std::vector<TidelinksGolf::Hole> Hs;
        TidelinksGolf::FromSeed(Seed, Hs);
        TidelinksGolf::PlayResult G;
        const TidelinksGolf::Error E = TidelinksGolf::Play(Hs, C, G);
        if (E != TidelinksGolf::Error::None) {
            Detail::Refuse(R, TidelinksGolf::ErrorName(E));
            R.BadHole = G.BadHole;
            return R;
        }
        R.Score = G.Strokes;
        R.ToPar = G.ToPar;
        R.Verdict = TidelinksGolf::VerdictName(G.V);
    } else if (R.G == Game::Berths) {
        std::vector<std::int64_t> V;
        if (!Detail::Numbers(P, true, V)) return Fail(Bad::Plan);
        BuddyBerths::Layout L;
        BuddyBerths::FromSeed(Seed, L);
        BuddyBerths::PlayResult B;
        const BuddyBerths::Error E = BuddyBerths::Play(L, V, B);
        if (E != BuddyBerths::Error::None) {
            Detail::Refuse(R, BuddyBerths::ErrorName(E));
            return R;
        }
        R.Score = B.Turned;
        R.Verdict = BuddyBerths::VerdictName(B.V);
    } else {
        std::vector<std::int64_t> V;
        if (!Detail::Numbers(P, false, V)) return Fail(Bad::Plan);
        static const GantrySweep::Profile Pr[4] = {GantrySweep::Profile::Calm, GantrySweep::Profile::Rush,
                                                   GantrySweep::Profile::Spread, GantrySweep::Profile::Storm};
        GantrySweep::Layout L;
        GantrySweep::FromSeed(Seed, Pr[Gi], L);
        GantrySweep::Order O(V.begin(), V.end());
        GantrySweep::PlayResult G;
        const GantrySweep::Error E = GantrySweep::Play(L, O, G);
        if (E != GantrySweep::Error::None) {
            Detail::Refuse(R, GantrySweep::ErrorName(E));
            return R;
        }
        R.Score = G.Waits;
        R.Travel = G.Travel;
        R.Verdict = GantrySweep::VerdictName(G.V);
    }
    Detail::Finish(R);
    return R;
}

inline std::string FormatResult(const Result& R) {
    if (R.S == Status::Bad) return std::string("bad ") + BadName(R.Why);
    std::string Out = R.S == Status::Ok ? "ok " : R.S == Status::Forged ? "forged " : "refused ";
    Out += GameName(R.G);
    if (R.S == Status::Refused) {
        Out += " " + R.Refusal;
        if (R.G == Game::Golf) Out += " hole=" + std::to_string(R.BadHole);
        return Out;
    }
    if (R.S == Status::Forged) Out += " claim=" + std::to_string(R.Claim);
    if (R.G == Game::Golf) {
        Out += " strokes=" + std::to_string(R.Score) + " topar=";
        Out += R.ToPar == 0 ? std::string("E") : (R.ToPar > 0 ? "+" : "") + std::to_string(R.ToPar);
    } else if (R.G == Game::Berths) {
        Out += " turned=" + std::to_string(R.Score);
    } else {
        Out += " waits=" + std::to_string(R.Score) + " travel=" + std::to_string(R.Travel);
    }
    return Out + " verdict=" + R.Verdict;
}

}  // namespace ReplayNotary
}  // namespace DaedalusDiskSaver
