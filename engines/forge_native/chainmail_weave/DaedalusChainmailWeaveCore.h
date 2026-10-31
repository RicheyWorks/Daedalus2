// SPDX-License-Identifier: MIT
//
// Chainmail Weave (original Prismheart minigame, hephaestus): a link puzzle in the Hephaestus Island armory. A seeded
// 7x7 mail grid has rusted rings. Place links one at a time and join the left edge to the right edge with
// orthogonally adjacent links before the link budget runs out. After every placement that does not win, rust spreads
// to one seeded empty ring. Rules authority: chainmail_weave_ref.py; chainmail_weave_golden.txt pins this header.
//
// Header-only, engine-free C++17, integer only, no exceptions, RTTI or Unreal headers. The grid logic is constexpr
// and allocation-free; randomness comes only from DaedalusPyRandomCore.h seeded "chainmail|<seed>", identical to
// CPython's random, so a seed gives the same weave everywhere.
#ifndef DAEDALUS_CHAINMAIL_WEAVE_CORE_H
#define DAEDALUS_CHAINMAIL_WEAVE_CORE_H

#include <cstdint>
#include <string>

#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPyRandomCore.h"

namespace daedalus {
namespace prism {
namespace chainmail {

inline constexpr int kN = 7;
inline constexpr int kCells = kN * kN;
inline constexpr int kRustDraws = 9;
inline constexpr int kMaxRolls = 20;
inline constexpr int kSlack = 3;  // normal

inline constexpr int kInf = 1000000;

/** Difficulty; stable values. Only the link budget changes: the grid and the rust stream are the same. */
enum class Difficulty : std::uint8_t { Easy = 0, Normal = 1, Hard = 2 };

/** Budget slack per difficulty: easy 4, normal 3, hard 2. */
constexpr int SlackFor(Difficulty d) { return d == Difficulty::Easy ? 4 : d == Difficulty::Hard ? 2 : kSlack; }

constexpr const char* DifficultyName(Difficulty d) {
    switch (d) {
        case Difficulty::Easy:
            return "easy";
        case Difficulty::Normal:
            return "normal";
        case Difficulty::Hard:
            return "hard";
    }
    return "unknown";
}

/** Parse "easy" / "normal" / "hard" into *out; false (out untouched) for anything else or a null pointer. */
constexpr bool ParseDifficulty(const char* text, Difficulty* out) {
    if (text == nullptr || out == nullptr) {
        return false;
    }
    for (int k = 0; k < 3; ++k) {
        const Difficulty d = static_cast<Difficulty>(k);
        const char* a = DifficultyName(d);
        const char* b = text;
        while (*a != '\0' && *a == *b) {
            ++a;
            ++b;
        }
        if (*a == '\0' && *b == '\0') {
            *out = d;
            return true;
        }
    }
    return false;
}

enum Ring : std::uint8_t { kEmpty = 0, kRust = 1, kLink = 2 };

/** Round state; stable values. */
enum class State : std::uint8_t { Playing = 0, Won = 1, Lost = 2 };

/** Why a round was lost; stable values. None while playing or after a win. */
enum class LossReason : std::uint8_t { None = 0, OutOfLinks = 1, Blocked = 2 };

constexpr const char* ReasonName(LossReason r) {
    switch (r) {
        case LossReason::None:
            return "NONE";
        case LossReason::OutOfLinks:
            return "OUT_OF_LINKS";  // a crossing exists but costs more links than are left
        case LossReason::Blocked:
            return "BLOCKED";  // rust has cut every crossing
    }
    return "UNKNOWN";
}

/** Place result; stable values. Only OK takes a turn. */
enum class Status : std::uint8_t { Ok = 0, BadCell = 1, Occupied = 2, GameOver = 3 };

constexpr const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok:
            return "OK";
        case Status::BadCell:
            return "BAD_CELL";
        case Status::Occupied:
            return "OCCUPIED";
        case Status::GameOver:
            return "GAME_OVER";
    }
    return "UNKNOWN";
}

constexpr const char* StateName(State s) {
    switch (s) {
        case State::Playing:
            return "PLAYING";
        case State::Won:
            return "WON";
        case State::Lost:
            return "LOST";
    }
    return "UNKNOWN";
}

/** The mail grid, row-major. Plain data. */
struct Grid {
    std::uint8_t ring[kCells] = {};
};

constexpr int CostOf(const Grid& g, int i) { return g.ring[i] == kRust ? kInf : (g.ring[i] == kLink ? 0 : 1); }

/** Cheapest cost from edge column `col` to each cell (empty rings still to link, counting the cell itself). */
constexpr void DistFrom(const Grid& g, int col, int (&d)[kCells]) {
    for (int i = 0; i < kCells; ++i) {
        d[i] = kInf;
    }
    for (int r = 0; r < kN; ++r) {
        d[r * kN + col] = CostOf(g, r * kN + col);
    }
    bool changed = true;
    while (changed) {
        changed = false;
        for (int i = 0; i < kCells; ++i) {
            if (g.ring[i] == kRust) {
                continue;
            }
            const int r = i / kN;
            const int c = i % kN;
            const int nb[4] = {r > 0 ? i - kN : -1, r < kN - 1 ? i + kN : -1, c > 0 ? i - 1 : -1, c < kN - 1 ? i + 1 : -1};
            for (int j : nb) {
                if (j >= 0 && d[j] < kInf && d[j] + CostOf(g, i) < d[i]) {
                    d[i] = d[j] + CostOf(g, i);
                    changed = true;
                }
            }
        }
    }
}

/** Fewest empty rings to link for a left-right crossing, or kInf when rust blocks every crossing. */
constexpr int Crossing(const Grid& g) {
    int d[kCells] = {};
    DistFrom(g, 0, d);
    int best = kInf;
    for (int r = 0; r < kN; ++r) {
        best = d[r * kN + kN - 1] < best ? d[r * kN + kN - 1] : best;
    }
    return best;
}

/** True when links alone already join the two edges. */
constexpr bool Joined(const Grid& g) {
    Grid only{};
    for (int i = 0; i < kCells; ++i) {
        only.ring[i] = g.ring[i] == kLink ? kLink : kRust;
    }
    return Crossing(only) < kInf;
}

/**
 * The hint and demo move: among empty rings on a cheapest crossing, the chokepoint (the ring whose rusting would
 * raise the cheapest crossing most; one whose loss blocks every crossing counts highest), earliest row-major on
 * ties. -1 when rust has cut every crossing.
 */
constexpr int DemoCell(const Grid& g) {
    int a[kCells] = {};
    int b[kCells] = {};
    DistFrom(g, 0, a);
    DistFrom(g, kN - 1, b);
    const int best = Crossing(g);
    if (best >= kInf) {
        return -1;
    }
    int pick = -1;
    int harm = -1;
    for (int i = 0; i < kCells; ++i) {
        if (g.ring[i] == kEmpty && a[i] + b[i] - CostOf(g, i) == best) {
            Grid h = g;
            h.ring[i] = kRust;
            const int hv = Crossing(h);
            if (hv > harm) {
                pick = i;
                harm = hv;
            }
        }
    }
    return pick;
}

/**
 * One cheapest crossing, left edge to right edge, written to out (cells in path order); returns its length, or 0
 * when rust has cut every crossing. For the hint glow. Deterministic smallest-cost-first search from the left edge
 * (lowest cell index on ties) that records each ring's predecessor; ends on the earliest cheapest right-edge ring.
 */
constexpr int PathCells(const Grid& g, int (&out)[kCells]) {
    int d[kCells] = {};
    int pred[kCells] = {};
    bool done[kCells] = {};
    for (int i = 0; i < kCells; ++i) {
        d[i] = kInf;
        pred[i] = -1;
    }
    for (int r = 0; r < kN; ++r) {
        d[r * kN] = CostOf(g, r * kN);
    }
    for (int step = 0; step < kCells; ++step) {
        int u = -1;
        for (int i = 0; i < kCells; ++i) {
            if (!done[i] && d[i] < kInf && (u < 0 || d[i] < d[u])) {
                u = i;
            }
        }
        if (u < 0) {
            break;
        }
        done[u] = true;
        const int r = u / kN;
        const int c = u % kN;
        const int nb[4] = {r > 0 ? u - kN : -1, r < kN - 1 ? u + kN : -1, c > 0 ? u - 1 : -1, c < kN - 1 ? u + 1 : -1};
        for (int j : nb) {
            if (j >= 0 && !done[j] && g.ring[j] != kRust && d[u] + CostOf(g, j) < d[j]) {
                d[j] = d[u] + CostOf(g, j);
                pred[j] = u;
            }
        }
    }
    int at = -1;
    for (int r = 0; r < kN; ++r) {
        const int i = r * kN + kN - 1;
        if (d[i] < kInf && (at < 0 || d[i] < d[at])) {
            at = i;
        }
    }
    if (at < 0) {
        return 0;
    }
    int rev[kCells] = {};
    int n = 0;
    while (at >= 0 && n < kCells) {
        rev[n++] = at;
        at = pred[at];
    }
    for (int k = 0; k < n; ++k) {
        out[k] = rev[n - 1 - k];
    }
    return n;
}

/** One round. Copyable; carries its own PyRandom stream. */
class Game {
public:
    explicit Game(const std::string& seed, Difficulty difficulty = Difficulty::Normal)
        : rng_(std::string("chainmail|") + seed), difficulty_(difficulty) {
        bool found = false;
        for (int roll = 0; roll < kMaxRolls && !found; ++roll) {
            Grid g{};
            for (int k = 0; k < kRustDraws; ++k) {
                g.ring[rng_.RandRange(kCells)] = kRust;
            }
            if (Crossing(g) < kInf) {
                grid_ = g;
                found = true;
            }
        }
        if (!found) {
            grid_ = Grid{};
        }
        budget_ = Crossing(grid_) + SlackFor(difficulty_);
    }

    Status Place(int cell) {
        if (state_ != State::Playing) {
            return Status::GameOver;
        }
        if (cell < 0 || cell >= kCells) {
            return Status::BadCell;
        }
        if (grid_.ring[cell] != kEmpty) {
            return Status::Occupied;
        }
        grid_.ring[cell] = kLink;
        --budget_;
        ++placed_;
        if (Joined(grid_)) {
            state_ = State::Won;
            return Status::Ok;
        }
        int empties[kCells] = {};
        int n = 0;
        for (int k = 0; k < kCells; ++k) {
            if (grid_.ring[k] == kEmpty) {
                empties[n++] = k;
            }
        }
        if (n > 0) {
            grid_.ring[empties[rng_.RandRange(static_cast<std::uint32_t>(n))]] = kRust;
        }
        const int need = Crossing(grid_);
        if (need >= kInf) {
            state_ = State::Lost;
            reason_ = LossReason::Blocked;
        } else if (budget_ <= 0 || need > budget_) {
            state_ = State::Lost;
            reason_ = LossReason::OutOfLinks;
        }
        return Status::Ok;
    }

    int Demo() const { return DemoCell(grid_); }
    int Score() const { return state_ == State::Won ? 10 + 10 * budget_ : 0; }
    int Budget() const { return budget_; }
    int Placed() const { return placed_; }
    State GetState() const { return state_; }
    LossReason Reason() const { return reason_; }
    Difficulty GetDifficulty() const { return difficulty_; }
    const Grid& GetGrid() const { return grid_; }

private:
    daedalus::pyrandom::PyRandom rng_;
    Difficulty difficulty_ = Difficulty::Normal;
    Grid grid_{};
    int budget_ = 0;
    int placed_ = 0;
    State state_ = State::Playing;
    LossReason reason_ = LossReason::None;
};

namespace detail {
constexpr bool EmptyGridCosts() {
    Grid g{};
    return Crossing(g) == kN && DemoCell(g) == 0 && !Joined(g);
}
constexpr bool RustWallBlocks() {
    Grid g{};
    for (int r = 0; r < kN; ++r) {
        g.ring[r * kN + 3] = kRust;
    }
    return Crossing(g) == kInf && DemoCell(g) == -1;
}
// One gap in a rust wall at row 3, column 3. The old earliest-ring rule picked cell 21, whose loss costs nothing;
// the hint now picks cell 23, the first ring whose loss blocks every crossing (it walls off the gap).
constexpr bool HintTakesChokepoint() {
    Grid g{};
    for (int r = 0; r < kN; ++r) {
        g.ring[r * kN + 3] = r == 3 ? kEmpty : kRust;
    }
    Grid lost = g;
    lost.ring[3 * kN + 2] = kRust;
    int path[kCells] = {};
    return Crossing(g) == kN && DemoCell(g) == 3 * kN + 2 && Crossing(lost) == kInf && PathCells(g, path) == kN &&
           path[3] == 3 * kN + 3;
}
}  // namespace detail

static_assert(SlackFor(Difficulty::Easy) == 4 && SlackFor(Difficulty::Normal) == 3 && SlackFor(Difficulty::Hard) == 2,
              "easy gets the most slack");
static_assert(detail::HintTakesChokepoint(), "the hint links the chokepoint first");
static_assert(detail::EmptyGridCosts(), "an empty grid needs one full row of links");
static_assert(detail::RustWallBlocks(), "a full rust column blocks every crossing");

}  // namespace chainmail
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_CHAINMAIL_WEAVE_CORE_H
