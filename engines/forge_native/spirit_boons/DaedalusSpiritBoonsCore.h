// SPDX-License-Identifier: MIT
// Spirit Boons core (Prismheart Round 2 lane R2-9, hephaestus). Header-only, engine-free C++17.
// Rules authority: spirit_boons_ref.py. Spirits summoned in Wardens' Accord (its SpiritName order) and Shardring
// (hue i summons spirit i) are tallied; each spirit grants one small boon in another cabinet, as a delta to one of
// that cabinet's per-difficulty settings. DATA + EVALUATOR ONLY: every boon is PROPOSED and changes no game until its
// owner ACKs. The Hollow Moth boon also needs the Hollow Moth rival beaten. Refusals leave state unchanged.
#pragma once
#include <cstdint>
#include <cstring>

namespace Daedalus { namespace SpiritBoons {

constexpr int kSpirits = 7;
constexpr int kHollowMoth = 4;
constexpr int kShardringHues = 5;
constexpr int kGames = 11;
constexpr int kLevel2At = 5;
constexpr int32_t kMaxCount = 999999;

enum class Status : uint8_t { Ok, NullPointer, BadSpirit, BadCount, BadTally, Overflow, UnknownGame };

inline const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok: return "OK";
        case Status::NullPointer: return "NULL_POINTER";
        case Status::BadSpirit: return "BAD_SPIRIT";
        case Status::BadCount: return "BAD_COUNT";
        case Status::BadTally: return "BAD_TALLY";
        case Status::Overflow: return "OVERFLOW";
        case Status::UnknownGame: return "UNKNOWN_GAME";
    }
    return "?";
}

inline const char* SpiritName(int s) {
    static const char* const k[kSpirits] = {"Cinder Wisp", "Mere Sprite", "Thornkin", "Sky Lark Spirit",
                                            "Hollow Moth", "Glass Heron", "Lantern Newt"};
    return (s >= 0 && s < kSpirits) ? k[s] : nullptr;
}

// Prism Satchel game ids, sorted.
inline const char* GameId(int i) {
    static const char* const k[kGames] = {"facetlock", "glimmerloom", "glowmoss", "lumenpath", "prismcairn",
                                          "prismvault", "shadewatch", "shardfall", "shardring", "spiritkite",
                                          "wardens_accord"};
    return (i >= 0 && i < kGames) ? k[i] : nullptr;
}

struct Boon { const char* Game; const char* Key; int8_t DeltaPerLevel; };

// spirit -> boon. Keys are setting names in the target game's DIFFICULTY table.
inline const Boon& BoonOf(int s) {
    static const Boon k[kSpirits] = {
        {"glowmoss", "light", 1},  {"spiritkite", "wind", 2},     {"facetlock", "spare", 1},
        {"lumenpath", "moves", 1}, {"shardfall", "cracked", -1},  {"glimmerloom", "satchel", 2},
        {"shadewatch", "hearts", 1}};
    return k[(s >= 0 && s < kSpirits) ? s : 0];
}

struct Tally { int32_t Count[kSpirits] = {}; };

inline bool Valid(const Tally& t) {
    for (int s = 0; s < kSpirits; ++s)
        if (t.Count[s] < 0 || t.Count[s] > kMaxCount) return false;
    return true;
}

inline Status Add(Tally* t, int spirit, int32_t count) {
    if (!t) return Status::NullPointer;
    if (spirit < 0 || spirit >= kSpirits) return Status::BadSpirit;
    if (count < 1 || count > kMaxCount) return Status::BadCount;
    if (!Valid(*t)) return Status::BadTally;
    if (t->Count[spirit] > kMaxCount - count) return Status::Overflow;
    t->Count[spirit] += count;
    return Status::Ok;
}

// Shardring hue h (0 ember .. 4 umbra) summons spirit h.
inline Status AddShardringHue(Tally* t, int hue, int32_t count) {
    if (hue < 0 || hue >= kShardringHues) return Status::BadSpirit;
    return Add(t, hue, count);
}

inline int Level(const Tally& t, int spirit, bool mothFreed) {
    if (spirit < 0 || spirit >= kSpirits) return 0;
    if (spirit == kHollowMoth && !mothFreed) return 0;
    const int32_t c = t.Count[spirit];
    return c <= 0 ? 0 : (c >= kLevel2At ? 2 : 1);
}

inline bool KnownGame(const char* game) {
    if (!game) return false;
    for (int i = 0; i < kGames; ++i)
        if (std::strcmp(game, GameId(i)) == 0) return true;
    return false;
}

struct Granted { int8_t Spirit; const char* Key; int8_t Delta; };
struct BoonList { int Count = 0; Granted Items[kSpirits] = {}; };

// Boons active for one cabinet, in spirit order. On refusal *out is left unchanged.
inline Status BoonsFor(const Tally& t, const char* game, bool mothFreed, BoonList* out) {
    if (!out) return Status::NullPointer;
    if (!KnownGame(game)) return Status::UnknownGame;
    if (!Valid(t)) return Status::BadTally;
    BoonList r;
    for (int s = 0; s < kSpirits; ++s) {
        const Boon& b = BoonOf(s);
        const int lv = Level(t, s, mothFreed);
        if (lv && std::strcmp(b.Game, game) == 0)
            r.Items[r.Count++] = Granted{static_cast<int8_t>(s), b.Key, static_cast<int8_t>(b.DeltaPerLevel * lv)};
    }
    *out = r;
    return Status::Ok;
}

}}  // namespace Daedalus::SpiritBoons
