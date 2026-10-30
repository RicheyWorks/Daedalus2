// SPDX-License-Identifier: MIT
//
// Padovan Plinths (G526) as a header-only C++17 core: a port of
// daedalus-core/src/main/java/com/daedalus/world/forge/PadovanPlinths.java.
//
// Triangular plinths spiral outward with sides from the Padovan sequence
// P(0) = P(1) = P(2) = 1, P(n) = P(n-2) + P(n-3): 1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, ...
//
// Plain functions over int64_t, no exceptions, no RTTI, no Unreal headers, no __int128.
// Every term up to kMaxIndex (the last one that fits in int64_t) is exact; overflow and bad
// arguments are reported through Status, never thrown. A thin Unreal wrapper can call these directly.
#ifndef DAEDALUS_FORGE_NATIVE_PADOVAN_PLINTHS_H
#define DAEDALUS_FORGE_NATIVE_PADOVAN_PLINTHS_H

#include <cstdint>
#include <limits>

namespace daedalus {
namespace forge {
namespace padovan {

/** Quest id for the Hephaestus Island forge hook (same as the Java QUEST_ID). */
inline constexpr const char* kQuestId = "q_padovan_plinths";

/** Result of an operation that can fail. */
enum class Status : std::uint8_t { Ok, BadArgument, Overflow };

/** Grade band (same names as the Java Grade). */
enum class Grade : std::uint8_t { Turned, Slipped };

/** Portable checked signed add: false (and *out untouched) when a + b would overflow int64_t. */
constexpr bool CheckedAdd(std::int64_t a, std::int64_t b, std::int64_t* out) {
    if (b > 0 && a > std::numeric_limits<std::int64_t>::max() - b) {
        return false;
    }
    if (b < 0 && a < std::numeric_limits<std::int64_t>::min() - b) {
        return false;
    }
    *out = a + b;
    return true;
}

namespace detail {

inline constexpr int kCapacity = 200;

struct Table {
    std::int64_t value[kCapacity] = {};
    int count = 0;
};

constexpr Table BuildTable() {
    Table t{};
    t.value[0] = 1;
    t.value[1] = 1;
    t.value[2] = 1;
    int n = 3;
    while (n < kCapacity) {
        std::int64_t next = 0;
        if (!CheckedAdd(t.value[n - 2], t.value[n - 3], &next)) {
            break;
        }
        t.value[n] = next;
        ++n;
    }
    t.count = n;
    return t;
}

inline constexpr Table kTable = BuildTable();

}  // namespace detail

/** Largest index whose term fits in int64_t (156). */
inline constexpr int kMaxIndex = detail::kTable.count - 1;

static_assert(kMaxIndex == 156, "Padovan int64 limit must match the Java MAX_INDEX");
static_assert(detail::kTable.count < detail::kCapacity, "table capacity must exceed the int64 limit");

/** P(n) into *out; BadArgument when n is outside 0..kMaxIndex. */
constexpr Status Padovan(int n, std::int64_t* out) {
    if (n < 0 || n > kMaxIndex) {
        return Status::BadArgument;
    }
    *out = detail::kTable.value[n];
    return Status::Ok;
}

/** Smallest n with P(n) == v, or -1 (binary search; terms are non-decreasing). */
constexpr int IndexOf(std::int64_t v) {
    int lo = 0;
    int hi = kMaxIndex;
    while (lo < hi) {
        const int mid = lo + (hi - lo) / 2;
        if (detail::kTable.value[mid] < v) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return detail::kTable.value[lo] == v ? lo : -1;
}

/** True when v is a Padovan side. */
constexpr bool IsPadovan(std::int64_t v) {
    return IndexOf(v) >= 0;
}

/** P(a) + ... + P(b) into *out; BadArgument for a bad run, Overflow when the sum leaves int64_t. */
constexpr Status RunSum(int a, int b, std::int64_t* out) {
    if (a < 0 || b < a || b > kMaxIndex) {
        return Status::BadArgument;
    }
    std::int64_t s = 0;
    for (int i = a; i <= b; ++i) {
        if (!CheckedAdd(s, detail::kTable.value[i], &s)) {
            return Status::Overflow;
        }
    }
    *out = s;
    return Status::Ok;
}

/** Grade a claimed side P(n); a bad index grades Slipped. */
constexpr Grade GradeClaim(int n, std::int64_t claimed) {
    std::int64_t v = 0;
    return (Padovan(n, &v) == Status::Ok && v == claimed) ? Grade::Turned : Grade::Slipped;
}

/** Forgemaster line for a grade (same text as the Java version). */
constexpr const char* ForgemasterLine(Grade g) {
    return g == Grade::Turned ? "Forgemaster: the plinth fits the spiral. Skip one, add the two before."
                              : "Forgemaster: the plinth slipped. Each side is the sum two and three back.";
}

}  // namespace padovan
}  // namespace forge
}  // namespace daedalus

#endif  // DAEDALUS_FORGE_NATIVE_PADOVAN_PLINTHS_H
