// SPDX-License-Identifier: MIT
// G550 Quay Duel core, header-only C++17 port of tools/streaming/quay_duel.py (G577 batch 5).
// Takes the crate values in quay order as the Python tool lined them up (the seeded shuffle stays
// in Python) and ports the exact interval DP of forceable margins, the perfect rival Casimir (ties
// go to L, as in Python), move validation, the given-away margin and the outcome. Engine-free: no
// Unreal includes, no exceptions, no RTTI. At most MaxCrates crates of at most MaxValue KiB, so
// every sum fits in int64.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace QuayDuel {

constexpr int MaxCrates = 400;  // same cap as Python's MAX_CRATES
constexpr std::int64_t MaxValue = 1000000000000LL;
constexpr std::size_t MaxMoves = 4096;
enum class Error { None, BadQuay, Mode, Short, Move, Long };
enum class Outcome { Won, Tied, Lost };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadQuay: return "quay";
        case Error::Mode: return "mode";
        case Error::Short: return "short";
        case Error::Move: return "move";
        case Error::Long: return "long";
    }
    return "?";
}
inline const char* OutcomeName(Outcome O) {
    switch (O) {
        case Outcome::Won: return "won";
        case Outcome::Tied: return "tied";
        case Outcome::Lost: return "lost";
    }
    return "?";
}

inline bool ValidQuay(const std::vector<std::int64_t>& V) {
    if (V.empty() || V.size() > static_cast<std::size_t>(MaxCrates)) return false;
    for (std::int64_t X : V)
        if (X < 0 || X > MaxValue) return false;
    return true;
}

// margins(): F(i, j) = best mover-minus-other margin on values[i..j]; 0 when i > j.
class Margins {
public:
    explicit Margins(const std::vector<std::int64_t>& V) : N(static_cast<int>(V.size())), F((V.size() + 1) * (V.size() + 1), 0) {
        for (int Len = 1; Len <= N; ++Len)
            for (int I = 0; I + Len - 1 < N; ++I) {
                const int J = I + Len - 1;
                const std::int64_t L = V[I] - At(I + 1, J), R = V[J] - At(I, J - 1);
                F[Idx(I, J)] = std::max(L, R);
            }
    }
    std::int64_t At(int I, int J) const { return I <= J ? F[Idx(I, J)] : 0; }

private:
    std::size_t Idx(int I, int J) const { return static_cast<std::size_t>(I) * (N + 1) + static_cast<std::size_t>(J); }
    int N;
    std::vector<std::int64_t> F;
};

struct Result {
    Error Err = Error::None;
    std::int64_t You = 0, Casimir = 0, BestForYou = 0, GaveAway = 0;
    std::string Moves;  // every turn's L/R, both captains
    Outcome O = Outcome::Lost;
};

// duel(): HasMoves with Moves is --moves (your turns only), Auto plays you perfectly too.
inline Result Duel(const std::vector<std::int64_t>& V, bool HasMoves, const std::vector<std::string>& Moves, bool Auto, bool Second) {
    Result R;
    if (HasMoves == Auto) {
        R.Err = Error::Mode;
        return R;
    }
    if (!ValidQuay(V) || Moves.size() > MaxMoves) {
        R.Err = Error::BadQuay;
        return R;
    }
    const Margins F(V);
    int I = 0, J = static_cast<int>(V.size()) - 1;
    std::size_t Next = 0;
    bool YouMove = !Second;
    while (I <= J) {
        const std::int64_t Left = V[I] - F.At(I + 1, J), Right = V[J] - F.At(I, J - 1);
        const char Best = Left >= Right ? 'L' : 'R';
        const std::int64_t BestMargin = Left >= Right ? Left : Right;
        char Move = Best;
        if (YouMove && HasMoves) {
            if (Next == Moves.size()) {
                R.Err = Error::Short;
                return R;
            }
            const std::string& M = Moves[Next++];
            if (M != "L" && M != "R") {
                R.Err = Error::Move;
                return R;
            }
            Move = M[0];
        }
        const int Idx = Move == 'L' ? I : J;
        const std::int64_t Got = Move == 'L' ? Left : Right;
        if (YouMove) {
            R.You += V[Idx];
            R.GaveAway += BestMargin - Got;
        } else {
            R.Casimir += V[Idx];
        }
        R.Moves += Move;
        if (Move == 'L') ++I;
        else --J;
        YouMove = !YouMove;
    }
    if (Next < Moves.size()) {
        R.Err = Error::Long;
        return R;
    }
    const std::int64_t Opener = F.At(0, static_cast<int>(V.size()) - 1);
    R.BestForYou = Second ? -Opener : Opener;
    R.O = R.You > R.Casimir ? Outcome::Won : R.You == R.Casimir ? Outcome::Tied : Outcome::Lost;
    return R;
}

}  // namespace QuayDuel
}  // namespace DaedalusDiskSaver
