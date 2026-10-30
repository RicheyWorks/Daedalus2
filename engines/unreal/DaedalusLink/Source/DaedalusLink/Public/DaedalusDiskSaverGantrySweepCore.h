// SPDX-License-Identifier: MIT
// G590 Gantry Sweep (DiskSaver Island, quest q_gantry_sweep): a gantry crane rides one quay rail like a disk
// head over cylinders. Seeded ships ask for it at a berth and an arrival tick; the crane moves one berth per
// tick, waits at a berth until its ship arrives, and serves it at once. The player orders the service; the
// score is the total ticks ships wait. The core lays out a seeded rail with DaedalusPyRandomCore.h (CPython
// random.Random(str) draws: randrange, sample, random, and shuffle built from its _randbelow), plays an
// order, and shows four yard habits (first come first served, nearest arrived ship, elevator sweep,
// one-way sweep) and the exact best order. A tide profile sets the arrival span: calm 24, rush 6, spread 60. Golden file: tools/streaming/gantry_sweep_parity.py.
// Header-only C++17; no Unreal includes, no exceptions, no RTTI; errors are return codes.
#pragma once
#include "DaedalusPyRandomCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace GantrySweep {

constexpr std::uint32_t Rail = 40;
enum class Profile { Calm, Rush, Spread };
inline int ArrivalSpan(Profile P) { return P == Profile::Rush ? 6 : P == Profile::Spread ? 60 : 24; }
inline const char* ProfileName(Profile P) { return P == Profile::Rush ? "rush" : P == Profile::Spread ? "spread" : "calm"; }
constexpr std::uint32_t MinShips = 5, MaxShips = 8;
constexpr std::int64_t MaxCoord = 1000000000;  // hand layouts: berths and arrivals; every time stays < 2^40
constexpr std::size_t MaxSeedBytes = 4096;
static const char* const Berths[12] = {"anchor", "bollard", "capstan", "davit", "eyebolt", "fairlead",
                                        "gunwale", "hawser", "jetty", "keel", "lanyard", "mooring"};

enum class Error { None, Short, Long, Range, Repeat, NoShips, TooManyShips, Coord, Seed };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::Short: return "short";
        case Error::Long: return "long";
        case Error::Range: return "range";
        case Error::Repeat: return "repeat";
        case Error::NoShips: return "no_ships";
        case Error::TooManyShips: return "too_many_ships";
        case Error::Coord: return "coord";
        case Error::Seed: return "seed";
    }
    return "?";
}

struct Ship {
    std::string Label;
    std::int64_t Pos = 0, Arrive = 0;
};

struct Layout {
    std::int64_t Start = 0;
    std::vector<Ship> Ships;
};

using Order = std::vector<std::size_t>;

// CPython shuffle: for i from len-1 down to 1, j = _randbelow(i + 1), swap.
template <typename T>
inline void Shuffle(daedalus::pyrandom::PyRandom& R, std::vector<T>& X) {
    for (std::size_t I = X.size() > 0 ? X.size() - 1 : 0; I > 0; --I) {
        const std::size_t J = R.Below(static_cast<std::uint32_t>(I + 1));
        std::swap(X[I], X[J]);
    }
}

// random.Random(Seed): start = randrange(40); n = 5 + randrange(4); pos = sample(range(40), n);
// arrive = int(random() * span) per ship (span from the tide profile); names = shuffle(BERTHS)[:n].
inline Error FromSeed(const std::string& Seed, Profile P, Layout& Out) {
    if (Seed.size() > MaxSeedBytes) return Error::Seed;
    daedalus::pyrandom::PyRandom R(Seed);
    Out = Layout{};
    Out.Start = R.RandRange(Rail);
    const std::size_t N = MinShips + R.RandRange(MaxShips - MinShips + 1);
    const std::vector<std::size_t> Pos = R.SampleIndices(Rail, N);
    std::vector<std::int64_t> Arrive(N);
    for (std::size_t I = 0; I < N; ++I) Arrive[I] = static_cast<std::int64_t>(R.RandomDouble() * ArrivalSpan(P));
    std::vector<std::string> Names(Berths, Berths + 12);
    Shuffle(R, Names);
    for (std::size_t I = 0; I < N; ++I) Out.Ships.push_back(Ship{Names[I], static_cast<std::int64_t>(Pos[I]), Arrive[I]});
    return Error::None;
}

// A hand-laid rail: 1..8 ships, berths and arrivals in 0..MaxCoord.
inline Error MakeHand(std::int64_t Start, const std::vector<std::pair<std::int64_t, std::int64_t>>& PosArrive, Layout& Out) {
    if (PosArrive.empty()) return Error::NoShips;
    if (PosArrive.size() > MaxShips) return Error::TooManyShips;
    if (Start < 0 || Start > MaxCoord) return Error::Coord;
    Out = Layout{};
    Out.Start = Start;
    for (std::size_t I = 0; I < PosArrive.size(); ++I) {
        const auto& P = PosArrive[I];
        if (P.first < 0 || P.first > MaxCoord || P.second < 0 || P.second > MaxCoord) return Error::Coord;
        Out.Ships.push_back(Ship{"berth" + std::to_string(I), P.first, P.second});
    }
    return Error::None;
}

inline std::int64_t Dist(std::int64_t A, std::int64_t B) { return A > B ? A - B : B - A; }

// (waits, travel) of a valid order.
inline void Run(const Layout& L, const Order& O, std::int64_t& Waits, std::int64_t& Travel) {
    std::int64_t T = 0, X = L.Start;
    Waits = 0;
    Travel = 0;
    for (std::size_t I : O) {
        const Ship& S = L.Ships[I];
        Travel += Dist(S.Pos, X);
        T += Dist(S.Pos, X);
        X = S.Pos;
        if (T < S.Arrive) T = S.Arrive;
        Waits += T - S.Arrive;
    }
}

inline Error CheckOrder(const Layout& L, const Order& O) {
    const std::size_t N = L.Ships.size();
    if (O.size() < N) return Error::Short;
    if (O.size() > N) return Error::Long;
    for (std::size_t I : O)
        if (I >= N) return Error::Range;
    std::vector<bool> Seen(N, false);
    for (std::size_t I : O) {
        if (Seen[I]) return Error::Repeat;
        Seen[I] = true;
    }
    return Error::None;
}

inline Order Fcfs(const Layout& L) {
    Order O(L.Ships.size());
    for (std::size_t I = 0; I < O.size(); ++I) O[I] = I;
    std::stable_sort(O.begin(), O.end(), [&](std::size_t A, std::size_t B) {
        const Ship &SA = L.Ships[A], &SB = L.Ships[B];
        if (SA.Arrive != SB.Arrive) return SA.Arrive < SB.Arrive;
        if (SA.Pos != SB.Pos) return SA.Pos < SB.Pos;
        return A < B;
    });
    return O;
}

// No ship has arrived: the earliest arrival, then the nearest, then the lowest index.
inline std::size_t Fallback(const Layout& L, const std::vector<bool>& Left, std::int64_t X) {
    std::size_t Best = L.Ships.size();
    for (std::size_t I = 0; I < L.Ships.size(); ++I) {
        if (!Left[I]) continue;
        if (Best == L.Ships.size()) {
            Best = I;
            continue;
        }
        const Ship &S = L.Ships[I], &B = L.Ships[Best];
        if (S.Arrive < B.Arrive || (S.Arrive == B.Arrive && Dist(S.Pos, X) < Dist(B.Pos, X))) Best = I;
    }
    return Best;
}

// Habit 2: the nearest ship that has arrived (then the lower berth, then the lower index).
inline Order Sstf(const Layout& L) {
    const std::size_t N = L.Ships.size();
    std::vector<bool> Left(N, true);
    std::int64_t T = 0, X = L.Start;
    Order O;
    for (std::size_t K = 0; K < N; ++K) {
        std::size_t Pick = N;
        for (std::size_t I = 0; I < N; ++I) {
            if (!Left[I] || L.Ships[I].Arrive > T) continue;
            if (Pick == N) {
                Pick = I;
                continue;
            }
            const Ship &S = L.Ships[I], &B = L.Ships[Pick];
            const std::int64_t DS = Dist(S.Pos, X), DB = Dist(B.Pos, X);
            if (DS < DB || (DS == DB && S.Pos < B.Pos)) Pick = I;
        }
        if (Pick == N) Pick = Fallback(L, Left, X);
        T = std::max(T + Dist(L.Ships[Pick].Pos, X), L.Ships[Pick].Arrive);
        X = L.Ships[Pick].Pos;
        Left[Pick] = false;
        O.push_back(Pick);
    }
    return O;
}

// Habit 3: the elevator sweep. Keep heading the same way (up first) to the nearest arrived ship ahead
// (the berth under the crane counts); turn round when none is ahead; idle, go to the next arrival.
inline Order Scan(const Layout& L) {
    const std::size_t N = L.Ships.size();
    std::vector<bool> Left(N, true);
    std::int64_t T = 0, X = L.Start, D = 1;
    Order O;
    for (std::size_t K = 0; K < N; ++K) {
        std::size_t Pick = N;
        bool Any = false;
        for (int Pass = 0; Pass < 2 && Pick == N; ++Pass) {
            for (std::size_t I = 0; I < N; ++I) {
                if (!Left[I] || L.Ships[I].Arrive > T) continue;
                Any = true;
                const std::int64_t Off = L.Ships[I].Pos - X;
                if (Pass == 0 && !((D > 0 && Off >= 0) || (D < 0 && Off <= 0))) continue;
                if (Pick == N || Dist(L.Ships[I].Pos, X) < Dist(L.Ships[Pick].Pos, X)) Pick = I;
            }
            if (Pick == N && Any && Pass == 0) D = -D;
            if (!Any) break;
        }
        if (Pick == N) {
            Pick = Fallback(L, Left, X);
            if (L.Ships[Pick].Pos != X) D = L.Ships[Pick].Pos > X ? 1 : -1;
        }
        T = std::max(T + Dist(L.Ships[Pick].Pos, X), L.Ships[Pick].Arrive);
        X = L.Ships[Pick].Pos;
        Left[Pick] = false;
        O.push_back(Pick);
    }
    return O;
}

// Habit 4: the one-way sweep (C-SCAN). Serve the nearest arrived ship at or above the crane (lower index on
// a shared berth); when none is above, run back to the lowest arrived ship and sweep up again; idle, go to
// the next arrival.
inline Order Cscan(const Layout& L) {
    const std::size_t N = L.Ships.size();
    std::vector<bool> Left(N, true);
    std::int64_t T = 0, X = L.Start;
    Order O;
    for (std::size_t K = 0; K < N; ++K) {
        std::size_t Up = N, Low = N;
        for (std::size_t I = 0; I < N; ++I) {
            if (!Left[I] || L.Ships[I].Arrive > T) continue;
            const std::int64_t P = L.Ships[I].Pos;
            if (Low == N || P < L.Ships[Low].Pos) Low = I;
            if (P >= X && (Up == N || P < L.Ships[Up].Pos)) Up = I;
        }
        const std::size_t Pick = Up != N ? Up : Low != N ? Low : Fallback(L, Left, X);
        T = std::max(T + Dist(L.Ships[Pick].Pos, X), L.Ships[Pick].Arrive);
        X = L.Ships[Pick].Pos;
        Left[Pick] = false;
        O.push_back(Pick);
    }
    return O;
}

// The exact best order: fewest waiting ticks, the first in lexicographic order among ties (n <= 8: 40320 orders).
inline Order Best(const Layout& L) {
    Order P(L.Ships.size()), Top;
    for (std::size_t I = 0; I < P.size(); ++I) P[I] = I;
    std::int64_t TopW = -1;
    do {
        std::int64_t W = 0, Tr = 0;
        Run(L, P, W, Tr);
        if (TopW < 0 || W < TopW) {
            TopW = W;
            Top = P;
        }
    } while (std::next_permutation(P.begin(), P.end()));
    return Top;
}

enum class Verdict { Sweet, Fair, Jammed };
inline const char* VerdictName(Verdict V) { return V == Verdict::Sweet ? "sweet" : V == Verdict::Fair ? "fair" : "jammed"; }

struct PlayResult {
    std::int64_t Waits = 0, Travel = 0;
    Verdict V = Verdict::Jammed;
};

// sweet = as few waiting ticks as the best order; fair = no worse than the best of the four habits.
inline Error Play(const Layout& L, const Order& O, PlayResult& R) {
    const Error E = CheckOrder(L, O);
    if (E != Error::None) return E;
    Run(L, O, R.Waits, R.Travel);
    std::int64_t Opt = 0, Habit = -1, W = 0, Tr = 0;
    Run(L, Best(L), Opt, Tr);
    for (const Order& H : {Fcfs(L), Sstf(L), Scan(L), Cscan(L)}) {
        Run(L, H, W, Tr);
        if (Habit < 0 || W < Habit) Habit = W;
    }
    R.V = R.Waits == Opt ? Verdict::Sweet : R.Waits <= Habit ? Verdict::Fair : Verdict::Jammed;
    return Error::None;
}

}  // namespace GantrySweep
}  // namespace DaedalusDiskSaver
