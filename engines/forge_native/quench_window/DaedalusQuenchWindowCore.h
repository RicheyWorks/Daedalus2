// SPDX-License-Identifier: MIT
//
// Quench Window (Prismheart Crafting + rewards lane): the ten-second skill check that finishes a crafted piece at the
// Hephaestus Island forge. The piece leaves the fire hot and cools each tick by a seeded amount; the player quenches
// it at one tick. In the temper band it is Tempered, within kPerfect of the band middle it is Perfect, above the band
// it stays Soft and below it it Cracks. Rules authority: quench_window_ref.py; quench_window_golden.txt pins this
// header to it.
//
// Header-only, engine-free C++17, integer only, no exceptions, RTTI or Unreal headers. Grading is constexpr and
// allocation-free. Only MakeCurve draws randomness, through DaedalusPyRandomCore.h seeded with "quench|<seed>", so a
// seed gives the same curve as CPython's random on every engine.
#ifndef DAEDALUS_QUENCH_WINDOW_CORE_H
#define DAEDALUS_QUENCH_WINDOW_CORE_H

#include <cstddef>
#include <cstdint>
#include <string>

#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPyRandomCore.h"

namespace daedalus {
namespace prism {
namespace quench {

inline constexpr int kTicks = 12;
inline constexpr int kHeat0Base = 900;
inline constexpr int kHeat0Span = 101;
inline constexpr int kCoolBase = 40;
inline constexpr int kCoolSpan = 41;
inline constexpr int kLoBase = 521;
inline constexpr int kLoSpan = 81;
inline constexpr int kBand = 90;
inline constexpr int kPerfect = 10;

// Every curve crosses the band and lands at least one tick inside it: start above the highest band top, end below
// the lowest band bottom, and the band is wider than the largest single-tick cooling.
static_assert(kHeat0Base > kLoBase + kLoSpan - 1 + kBand, "every curve starts above the band");
static_assert(kHeat0Base + kHeat0Span - 1 - kTicks * kCoolBase < kLoBase, "every curve ends below the band");
static_assert(kBand > kCoolBase + kCoolSpan - 1, "no tick can jump over the band");

/** Stop result; stable values. */
enum class Outcome : std::uint8_t { Soft = 0, Tempered = 1, Perfect = 2, Cracked = 3 };

/** Call result; stable values. */
enum class Status : std::uint8_t { Ok = 0, NullPointer = 1, BadTick = 2 };

constexpr const char* OutcomeName(Outcome o) {
    switch (o) {
        case Outcome::Soft:
            return "SOFT";
        case Outcome::Tempered:
            return "TEMPERED";
        case Outcome::Perfect:
            return "PERFECT";
        case Outcome::Cracked:
            return "CRACKED";
    }
    return "UNKNOWN";
}

/** One cooling curve: heat at ticks 0..kTicks and the temper band [lo, hi]. Plain data. */
struct QuenchCurve {
    int heat[kTicks + 1] = {};
    int lo = 0;
    int hi = 0;
};

/** Build the curve for a seed string (any bytes); draws in the same order as the Python reference. */
inline QuenchCurve MakeCurve(const std::string& seed) {
    daedalus::pyrandom::PyRandom r(std::string("quench|") + seed);
    QuenchCurve c;
    c.heat[0] = kHeat0Base + static_cast<int>(r.RandRange(kHeat0Span));
    for (int t = 1; t <= kTicks; ++t) {
        c.heat[t] = c.heat[t - 1] - (kCoolBase + static_cast<int>(r.RandRange(kCoolSpan)));
    }
    c.lo = kLoBase + static_cast<int>(r.RandRange(kLoSpan));
    c.hi = c.lo + kBand;
    return c;
}

/** Grade a quench at `tick` into *out. BadTick for a tick outside 0..kTicks (out untouched). */
constexpr Status Grade(const QuenchCurve& c, int tick, Outcome* out) {
    if (out == nullptr) {
        return Status::NullPointer;
    }
    if (tick < 0 || tick > kTicks) {
        return Status::BadTick;
    }
    const int h = c.heat[tick];
    if (h > c.hi) {
        *out = Outcome::Soft;
    } else if (h < c.lo) {
        *out = Outcome::Cracked;
    } else {
        const int mid = (c.lo + c.hi) / 2;
        const int d = h > mid ? h - mid : mid - h;
        *out = d <= kPerfect ? Outcome::Perfect : Outcome::Tempered;
    }
    return Status::Ok;
}

/** Earliest tick whose heat is closest to the band middle (the tick a perfect player picks). */
constexpr int BestTick(const QuenchCurve& c) {
    const int mid = (c.lo + c.hi) / 2;
    int best = 0;
    int best_d = c.heat[0] > mid ? c.heat[0] - mid : mid - c.heat[0];
    for (int t = 1; t <= kTicks; ++t) {
        const int d = c.heat[t] > mid ? c.heat[t] - mid : mid - c.heat[t];
        if (d < best_d) {
            best = t;
            best_d = d;
        }
    }
    return best;
}

}  // namespace quench
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_QUENCH_WINDOW_CORE_H
