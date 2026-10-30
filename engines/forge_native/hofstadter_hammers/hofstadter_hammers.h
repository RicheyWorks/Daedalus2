// SPDX-License-Identifier: MIT
//
// Hofstadter Hammers (G521) as a header-only C++17 core: a port of
// daedalus-core/src/main/java/com/daedalus/world/forge/HofstadterHammers.java.
//
// Q hammer:      Q(n) = Q(n - Q(n-1)) + Q(n - Q(n-2))   1, 1, 2, 3, 3, 4, 5, 5, 6, 6, ...
// Conway hammer: a(n) = a(a(n-1)) + a(n - a(n-1))      1, 1, 2, 2, 3, 4, 4, 4, 5, ...
// with Q(1) = Q(2) = a(1) = a(2) = 1, 1-indexed (slot 0 holds 0, unused), n up to kMaxN.
//
// Plain functions over int32_t and caller-owned buffers: no allocation, no exceptions, no RTTI,
// no Unreal headers. Failures come back as Status, never thrown, so a thin Unreal wrapper can call
// these directly (for example with a TArray<int32>'s GetData() and Num()).
#ifndef DAEDALUS_FORGE_NATIVE_HOFSTADTER_HAMMERS_H
#define DAEDALUS_FORGE_NATIVE_HOFSTADTER_HAMMERS_H

#include <cstddef>
#include <cstdint>

namespace daedalus {
namespace forge {
namespace hofstadter {

/** Quest id for the Hephaestus Island forge hook (same as the Java QUEST_ID). */
inline constexpr const char* kQuestId = "q_hofstadter_hammers";

/** Largest supported index (same as the Java MAX_N). */
inline constexpr std::int32_t kMaxN = 10000000;

/** Result of an operation that can fail. */
enum class Status : std::uint8_t {
    Ok,
    BadArgument,  // n out of range (the Java IllegalArgumentException)
    BufferTooSmall,  // the buffer holds fewer than n + 1 slots
    IndexFell  // a Q look-back fell below 1 (the Java IllegalStateException); never seen up to kMaxN
};

/** Which hammer (same names as the Java Hammer). */
enum class Hammer : std::uint8_t { Q, Conway };

/** Grade band (same names as the Java Grade). */
enum class Grade : std::uint8_t { Turned, Slipped };

/** Q(0..n) into buf[0..n] (buf[0] = 0); needs len >= n + 1 and 0 <= n <= kMaxN. */
constexpr Status QSequence(std::int32_t n, std::int32_t* buf, std::size_t len) {
    if (n < 0 || n > kMaxN) {
        return Status::BadArgument;
    }
    if (buf == nullptr || len < static_cast<std::size_t>(n) + 1) {
        return Status::BufferTooSmall;
    }
    buf[0] = 0;
    for (std::int32_t i = 1; i <= n; ++i) {
        if (i <= 2) {
            buf[i] = 1;
        } else {
            const std::int32_t x = i - buf[i - 1];
            const std::int32_t y = i - buf[i - 2];
            if (x < 1 || y < 1) {
                return Status::IndexFell;
            }
            buf[i] = buf[x] + buf[y];
        }
    }
    return Status::Ok;
}

/** a(0..n) into buf[0..n] (buf[0] = 0); needs len >= n + 1 and 0 <= n <= kMaxN. */
constexpr Status ConwaySequence(std::int32_t n, std::int32_t* buf, std::size_t len) {
    if (n < 0 || n > kMaxN) {
        return Status::BadArgument;
    }
    if (buf == nullptr || len < static_cast<std::size_t>(n) + 1) {
        return Status::BufferTooSmall;
    }
    buf[0] = 0;
    for (std::int32_t i = 1; i <= n; ++i) {
        buf[i] = i <= 2 ? 1 : buf[buf[i - 1]] + buf[i - buf[i - 1]];
    }
    return Status::Ok;
}

/** The strike of hammer h at n (1 <= n <= kMaxN) into *out, using scratch[0..n] as work space. */
constexpr Status Strike(Hammer h, std::int32_t n, std::int32_t* scratch, std::size_t len, std::int32_t* out) {
    if (n < 1 || n > kMaxN || out == nullptr) {
        return Status::BadArgument;
    }
    const Status st = h == Hammer::Q ? QSequence(n, scratch, len) : ConwaySequence(n, scratch, len);
    if (st == Status::Ok) {
        *out = scratch[n];
    }
    return st;
}

/** Q(n) (the Java q), see Strike. */
constexpr Status Q(std::int32_t n, std::int32_t* scratch, std::size_t len, std::int32_t* out) {
    return Strike(Hammer::Q, n, scratch, len, out);
}

/** a(n) (the Java conway), see Strike. */
constexpr Status Conway(std::int32_t n, std::int32_t* scratch, std::size_t len, std::int32_t* out) {
    return Strike(Hammer::Conway, n, scratch, len, out);
}

/** Grade a claimed strike; any failure grades Slipped. */
constexpr Grade GradeClaim(Hammer h, std::int32_t n, std::int32_t claimed, std::int32_t* scratch, std::size_t len) {
    std::int32_t v = 0;
    return (Strike(h, n, scratch, len, &v) == Status::Ok && v == claimed) ? Grade::Turned : Grade::Slipped;
}

/** Forgemaster line for a grade (same text as the Java version). */
constexpr const char* ForgemasterLine(Grade g) {
    return g == Grade::Turned ? "Forgemaster: the hammer rang true. It only ever listens to its own echoes."
                              : "Forgemaster: the hammer slipped. Look back by the last strikes and add.";
}

}  // namespace hofstadter
}  // namespace forge
}  // namespace daedalus

#endif  // DAEDALUS_FORGE_NATIVE_HOFSTADTER_HAMMERS_H