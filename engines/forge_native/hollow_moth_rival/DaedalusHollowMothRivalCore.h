// SPDX-License-Identifier: MIT
// Hollow Moth rival core (Prismheart Round 2 lane R2-9, hephaestus). Header-only, engine-free C++17.
// Rules authority: hollow_moth_rival_ref.py. With 3+ Heartglass seals in the Prism Satchel the secret Hollow Moth
// rival appears and, each round, challenges you in a cabinet you have not Heartglass-sealed (any once all 11 are),
// drawn with PyRandom("hollow_moth|<seed>|<round>"). Its mark is that cabinet's Satchel Heartglass par + a seeded
// margin of 0..max(1, par/10) (perfect-par cabinets: a perfect hard win at or above Umbra par + margin). 3 tries per
// round; a hard win at or above the mark beats it and frees the Hollow Moth boon (Spirit Boons). Satchel is read-only.
// Refusals leave state unchanged.
#pragma once
#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismSatchelCore.h"
#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPyRandomCore.h"
#include <cstdint>
#include <string>

namespace Daedalus { namespace HollowMothRival {

namespace satchel = ::daedalus::prism_satchel;
constexpr int kGames = static_cast<int>(satchel::Payouts.size());
constexpr int kUnlockAt = 3;
constexpr int kTries = 3;
constexpr int kMaxRound = 9999;
constexpr int kHard = 2;
static_assert(kGames == 11, "Satchel game count changed: regenerate the golden");

enum class Status : uint8_t {
    Ok, Locked, AlreadyBeaten, BadMask, NoChallenge, WrongGame, BadDifficulty, BadScore, Beaten, FellShort, FlewOff,
    RoundLimit, NullPointer
};

inline const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok: return "OK";
        case Status::Locked: return "LOCKED";
        case Status::AlreadyBeaten: return "ALREADY_BEATEN";
        case Status::BadMask: return "BAD_MASK";
        case Status::NoChallenge: return "NO_CHALLENGE";
        case Status::WrongGame: return "WRONG_GAME";
        case Status::BadDifficulty: return "BAD_DIFFICULTY";
        case Status::BadScore: return "BAD_SCORE";
        case Status::Beaten: return "BEATEN";
        case Status::FellShort: return "FELL_SHORT";
        case Status::FlewOff: return "FLEW_OFF";
        case Status::RoundLimit: return "ROUND_LIMIT";
        case Status::NullPointer: return "NULL_POINTER";
    }
    return "?";
}

struct State {
    int Round = 0;
    int Tries = 0;
    bool Beaten = false;
    int Game = -1;        // index into satchel::Payouts (sorted ids), -1 = no open challenge
    int64_t Mark = 0;
    bool NeedPerfect = false;
};

inline int PopCount(uint32_t m) { int n = 0; for (; m; m &= m - 1) ++n; return n; }

// Unlock check straight from the Satchel's Heartglass() count.
inline bool Unlocked(int heartglass) { return heartglass >= kUnlockAt; }

// Draw the next challenge. heartMask bit i = Heartglass held in Payouts[i].
inline Status Begin(State* st, int64_t seed, int64_t heartMask) {
    if (!st) return Status::NullPointer;
    if (heartMask < 0 || heartMask >= (int64_t{1} << kGames)) return Status::BadMask;
    const uint32_t mask = static_cast<uint32_t>(heartMask);
    if (!Unlocked(PopCount(mask))) return Status::Locked;
    if (st->Beaten) return Status::AlreadyBeaten;
    if (st->Game >= 0 && st->Tries > 0) return Status::Ok;
    if (st->Round >= kMaxRound) return Status::RoundLimit;
    int cand[kGames]; int n = 0;
    for (int i = 0; i < kGames; ++i) if (!(mask >> i & 1u)) cand[n++] = i;
    if (n == 0) for (int i = 0; i < kGames; ++i) cand[n++] = i;
    State s = *st;
    s.Round += 1;
    ::daedalus::pyrandom::PyRandom r("hollow_moth|" + std::to_string(seed) + "|" + std::to_string(s.Round));
    s.Game = cand[r.RandRange(static_cast<uint32_t>(n))];
    const satchel::Payout& p = satchel::Payouts[static_cast<size_t>(s.Game)];
    s.NeedPerfect = p.HeartPar < 0;
    const int base = s.NeedPerfect ? p.UmbraPar : p.HeartPar;
    const int margin = base / 10 > 1 ? base / 10 : 1;
    s.Mark = base + static_cast<int64_t>(r.RandRange(static_cast<uint32_t>(margin + 1)));
    s.Tries = kTries;
    *st = s;
    return Status::Ok;
}

inline const char* ChallengeGame(const State& st) {
    return (st.Game >= 0 && st.Game < kGames) ? satchel::Payouts[static_cast<size_t>(st.Game)].Game : nullptr;
}

inline Status Attempt(State* st, int game, int difficulty, int64_t score, bool won, bool perfect) {
    if (!st) return Status::NullPointer;
    if (st->Beaten) return Status::AlreadyBeaten;
    if (st->Game < 0 || st->Tries == 0) return Status::NoChallenge;
    if (game != st->Game) return Status::WrongGame;
    if (difficulty < 0 || difficulty > kHard) return Status::BadDifficulty;
    if (score < 0) return Status::BadScore;
    if (difficulty == kHard && won && score >= st->Mark && (perfect || !st->NeedPerfect)) {
        st->Beaten = true; st->Tries = 0;
        return Status::Beaten;
    }
    if (--st->Tries == 0) { st->Game = -1; return Status::FlewOff; }
    return Status::FellShort;
}

// Feeds Spirit Boons' mothFreed flag.
inline bool MothFreed(const State& st) { return st.Beaten; }

}}  // namespace Daedalus::HollowMothRival
