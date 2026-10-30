// SPDX-License-Identifier: MIT
// G559 Sack Chute core, header-only C++17 port of tools/streaming/sack_chute.py (G573).
// Takes an already-filled chute (sacks per bin, as laid out by the Python tool) and ports the sowing
// rule, the exact BFS par (same bin order, so the plan matches), the nearest-the-hold greedy habit,
// move validation and the verdict. Engine-free: no Unreal includes, no exceptions, no RTTI.
#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>

namespace DaedalusDiskSaver {
namespace SackChute {

constexpr int MaxBins = 8;
constexpr int MaxSacks = 24;  // Python deals at most 12; the key packs 5 bits per bin
enum class Error { None, BadChute, Bin, Clear, Empty };
enum class Verdict { Stowed, Slow, Loose };
using Bins = std::vector<int>;

inline bool ValidChute(const Bins& B) {
    if (B.empty() || B.size() > static_cast<std::size_t>(MaxBins)) return false;
    int Total = 0;
    for (int K : B) {
        if (K < 0 || K > MaxSacks) return false;
        Total += K;
    }
    return Total <= MaxSacks;
}

inline bool AnySacks(const Bins& B) {
    for (int K : B)
        if (K) return true;
    return false;
}

// sow(): bin I (0-based, non-empty) round the loop; returns sacks banked in the hold.
inline int Sow(Bins& B, int I) {
    const int N = static_cast<int>(B.size());
    int K = B[I], Pos = I, Banked = 0;
    B[I] = 0;
    for (int s = 0; s < K; ++s) {
        Pos = (Pos + 1) % (N + 1);
        if (Pos == N) ++Banked;
        else ++B[Pos];
    }
    return Banked;
}

inline std::uint64_t Pack(const Bins& B) {
    std::uint64_t K = 0;
    for (int X : B) K = (K << 5) | static_cast<std::uint64_t>(X);
    return K;
}

// solve(): BFS to the empty chute; Plan is 0-based bins.
inline bool Solve(const Bins& Start, int& Par, std::vector<int>& Plan) {
    if (!ValidChute(Start)) return false;
    struct Back { std::uint64_t From; int Bin; };
    std::unordered_map<std::uint64_t, Back> Prev;
    std::unordered_map<std::uint64_t, Bins> State;
    std::vector<std::uint64_t> Queue{Pack(Start)};
    Prev[Queue[0]] = {~std::uint64_t{0}, -1};
    State[Queue[0]] = Start;
    for (std::size_t Head = 0; Head < Queue.size(); ++Head) {
        std::uint64_t S = Queue[Head];
        const Bins Cur = State[S];
        if (!AnySacks(Cur)) {
            Plan.clear();
            while (Prev[S].From != ~std::uint64_t{0}) {
                Plan.insert(Plan.begin(), Prev[S].Bin);
                S = Prev[S].From;
            }
            Par = static_cast<int>(Plan.size());
            return true;
        }
        for (int I = 0; I < static_cast<int>(Cur.size()); ++I) {
            if (!Cur[I]) continue;
            Bins Next = Cur;
            Sow(Next, I);
            const std::uint64_t T = Pack(Next);
            if (Prev.find(T) == Prev.end()) {
                Prev[T] = {S, I};
                State[T] = Next;
                Queue.push_back(T);
            }
        }
    }
    return false;
}

// greedy(): always sow the non-empty bin nearest the hold. -1 if the chute is invalid.
inline int Greedy(Bins B) {
    if (!ValidChute(B)) return -1;
    int Moves = 0;
    while (AnySacks(B)) {
        int I = static_cast<int>(B.size()) - 1;
        while (!B[I]) --I;
        Sow(B, I);
        if (++Moves > 100000) return -1;
    }
    return Moves;
}

struct Result {
    Error Err = Error::None;
    int InHold = 0;
    Bins Left;
    Verdict V = Verdict::Loose;
};

// Moves are 1-based bins, as typed by the player.
inline Result Play(const Bins& Start, int Par, const std::vector<int>& Moves) {
    Result R;
    if (!ValidChute(Start)) { R.Err = Error::BadChute; return R; }
    const int N = static_cast<int>(Start.size());
    for (int M : Moves)
        if (M < 1 || M > N) { R.Err = Error::Bin; return R; }
    Bins S = Start;
    for (int M : Moves) {
        if (!AnySacks(S)) { R.Err = Error::Clear; return R; }
        if (!S[M - 1]) { R.Err = Error::Empty; return R; }
        R.InHold += Sow(S, M - 1);
    }
    R.Left = S;
    R.V = AnySacks(S) ? Verdict::Loose
                      : (static_cast<int>(Moves.size()) <= Par ? Verdict::Stowed : Verdict::Slow);
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Stowed ? "stowed" : V == Verdict::Slow ? "slow" : "loose";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Bin: return "bin";
        case Error::Clear: return "clear";
        case Error::Empty: return "empty";
        case Error::BadChute: return "chute";
        default: return "none";
    }
}

}  // namespace SackChute
}  // namespace DaedalusDiskSaver
