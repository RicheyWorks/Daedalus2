// SPDX-License-Identifier: MIT
//
// Hallmark Tiers (Prismheart Crafting + rewards lane): the stamp a finished piece earns at the Hephaestus Island
// forge. COSMETIC ONLY: a hallmark picks a stamp tier and a finish for display and never changes counts, values,
// marks or any gameplay number. Rules authority: hallmark_tiers_ref.py; hallmark_tiers_golden.txt pins this header.
//
// Inputs are the landed systems' own numbers, taken as plain ints so this header stays free of their code:
//   seal   = Prism Satchel's best Warden seal for the game (daedalus::prism_satchel::SealIndex, 0 none .. 6 heartglass)
//   par    = Fair Par's tier for the run (daedalus::prismpar::Tier, 0 none .. 3 gold; see prismpar::TierOf)
//   quench = the Quench Window outcome (daedalus::prism::quench::Outcome, 0 soft .. 3 cracked)
// hallmark_tiers_test.cpp includes all three real headers and static_asserts these values match.
//
// Header-only, engine-free C++17: integer only, constexpr, no allocation, exceptions, RTTI, I/O, randomness or
// Unreal headers.
#ifndef DAEDALUS_HALLMARK_TIERS_CORE_H
#define DAEDALUS_HALLMARK_TIERS_CORE_H

#include <cstdint>

namespace daedalus {
namespace prism {
namespace hallmark {

inline constexpr int kSeals = 7;    // prism_satchel::Seals
inline constexpr int kPars = 4;     // prismpar::Tier
inline constexpr int kQuench = 4;   // quench::Outcome
inline constexpr int kSealHeartglass = 6;
inline constexpr int kParGold = 3;
inline constexpr int kQuenchSoft = 0;
inline constexpr int kQuenchTempered = 1;
inline constexpr int kQuenchPerfect = 2;
inline constexpr int kQuenchCracked = 3;

/** Stamp tier; stable values. None means no stamp (a cracked piece). */
enum class Tier : std::uint8_t { None = 0, Plain = 1, Bronze = 2, Silver = 3, Gold = 4, Prism = 5 };

enum class Status : std::uint8_t { Ok = 0, NullPointer = 1, BadSeal = 2, BadPar = 3, BadQuench = 4 };

/** A hallmark: display data only. */
struct Hallmark {
    Tier tier = Tier::None;
    int finish = 0;  // seal index; the stamp is tinted with that seal's hue
};

inline constexpr const char* kSealNames[kSeals] = {"none", "ember", "tide", "verdant", "gale", "umbra", "heartglass"};

constexpr const char* TierName(Tier t) {
    switch (t) {
        case Tier::None:
            return "NONE";
        case Tier::Plain:
            return "PLAIN";
        case Tier::Bronze:
            return "BRONZE";
        case Tier::Silver:
            return "SILVER";
        case Tier::Gold:
            return "GOLD";
        case Tier::Prism:
            return "PRISM";
    }
    return "UNKNOWN";
}

constexpr const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok:
            return "OK";
        case Status::NullPointer:
            return "NULL_POINTER";
        case Status::BadSeal:
            return "BAD_SEAL";
        case Status::BadPar:
            return "BAD_PAR";
        case Status::BadQuench:
            return "BAD_QUENCH";
    }
    return "UNKNOWN";
}

constexpr const char* FinishName(int finish) { return finish >= 0 && finish < kSeals ? kSealNames[finish] : "unknown"; }

/**
 * Stamp for a finished piece. Cracked takes no stamp. Otherwise the par tier gives PLAIN..GOLD, capped at BRONZE for a
 * soft quench and SILVER for a tempered one; GOLD with a perfect quench and a heartglass seal becomes PRISM. The
 * finish is the seal. Refusals leave *out unchanged.
 */
constexpr Status Stamp(int seal, int par, int quench, Hallmark* out) {
    if (out == nullptr) {
        return Status::NullPointer;
    }
    if (seal < 0 || seal >= kSeals) {
        return Status::BadSeal;
    }
    if (par < 0 || par >= kPars) {
        return Status::BadPar;
    }
    if (quench < 0 || quench >= kQuench) {
        return Status::BadQuench;
    }
    Hallmark h;
    h.finish = seal;
    if (quench != kQuenchCracked) {
        int t = 1 + par;
        const int cap = quench == kQuenchSoft ? 2 : quench == kQuenchTempered ? 3 : 4;
        t = t < cap ? t : cap;
        if (t == 4 && quench == kQuenchPerfect && seal == kSealHeartglass) {
            t = 5;
        }
        h.tier = static_cast<Tier>(t);
    }
    *out = h;
    return Status::Ok;
}

namespace detail {

constexpr Tier TierAt(int seal, int par, int quench) {
    Hallmark h;
    Stamp(seal, par, quench, &h);
    return h.tier;
}

// A better input never gives a worse stamp (monotone in par, seal and quench quality soft < tempered < perfect).
constexpr bool Monotone() {
    constexpr int kOrder[3] = {kQuenchSoft, kQuenchTempered, kQuenchPerfect};
    for (int s = 0; s < kSeals; ++s) {
        for (int p = 0; p < kPars; ++p) {
            for (int q = 0; q < 3; ++q) {
                const Tier t = TierAt(s, p, kOrder[q]);
                if ((p + 1 < kPars && TierAt(s, p + 1, kOrder[q]) < t) || (s + 1 < kSeals && TierAt(s + 1, p, kOrder[q]) < t) ||
                    (q + 1 < 3 && TierAt(s, p, kOrder[q + 1]) < t)) {
                    return false;
                }
            }
        }
    }
    return true;
}

}  // namespace detail

static_assert(detail::Monotone(), "better play never stamps a worse hallmark");
static_assert(detail::TierAt(kSealHeartglass, kParGold, kQuenchPerfect) == Tier::Prism, "the top stamp is reachable");
static_assert(detail::TierAt(kSealHeartglass, kParGold, kQuenchCracked) == Tier::None, "a cracked piece takes no stamp");

}  // namespace hallmark
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_HALLMARK_TIERS_CORE_H
