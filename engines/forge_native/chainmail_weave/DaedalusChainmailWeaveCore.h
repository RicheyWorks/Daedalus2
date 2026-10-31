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
inline constexpr int kSlack = 3;
inline constexpr int kInf = 1000000;

enum Ring : std::uint8_t { kEmpty = 0, kRust = 1, kLink = 2 };

/** Round state; stable values. */
enum class State : std::uint8_t { Playing = 0, Won = 1, Lost = 2 };

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

/** Earliest (row-major) empty ring on a cheapest crossing, or -1 when none: the demo move. */
constexpr int DemoCell(const Grid& g) {
    int a[kCells] = {};
    int b[kCells] = {};
    DistFrom(g, 0, a);
    DistFrom(g, kN - 1, b);
    const int best = Crossing(g);
    if (best >= kInf) {
        return -1;
    }
    for (int i = 0; i < kCells; ++i) {
        if (g.ring[i] == kEmpty && a[i] + b[i] - CostOf(g, i) == best) {
            return i;
        }
    }
    return -1;
}

/** One round. Copyable; carries its own PyRandom stream. */
class Game {
public:
    explicit Game(const std::string& seed) : rng_(std::string("chainmail|") + seed) {
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
        budget_ = Crossing(grid_) + kSlack;
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
        if (budget_ <= 0 || need >= kInf || need > budget_) {
            state_ = State::Lost;
        }
        return Status::Ok;
    }

    int Demo() const { return DemoCell(grid_); }
    int Score() const { return state_ == State::Won ? 10 + 10 * budget_ : 0; }
    int Budget() const { return budget_; }
    int Placed() const { return placed_; }
    State GetState() const { return state_; }
    const Grid& GetGrid() const { return grid_; }

private:
    daedalus::pyrandom::PyRandom rng_;
    Grid grid_{};
    int budget_ = 0;
    int placed_ = 0;
    State state_ = State::Playing;
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
}  // namespace detail

static_assert(detail::EmptyGridCosts(), "an empty grid needs one full row of links");
static_assert(detail::RustWallBlocks(), "a full rust column blocks every crossing");

}  // namespace chainmail
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_CHAINMAIL_WEAVE_CORE_H
