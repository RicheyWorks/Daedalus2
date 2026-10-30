// SPDX-License-Identifier: MIT
// G597 Buddy Berths (DiskSaver Island, quest q_buddy_berths): the long quay is split buddy-style, like a buddy
// allocator handing out blocks. A ship of size 2^k may only moor on an aligned run of 2^k free berth units
// (offset % size == 0). Seeded ships arrive one by one; ship k sails just before arrival k + stay and frees its
// run. For each arrival the player names an offset or turns the ship away; the score is ships turned away.
// The core lays out a seeded quay with DaedalusPyRandomCore.h (CPython random.Random(str) draws: randrange,
// random, and shuffle built from its _randbelow), plays a plan, and shows three dock habits (lowest offset,
// tightest fit, highest offset) and the exact best plan (memoised search over every choice).
// Golden file: tools/streaming/buddy_berths_parity.py.
// Header-only C++17; no Unreal includes, no exceptions, no RTTI; errors are return codes.
#pragma once
#include "DaedalusPyRandomCore.h"

#include <cstddef>
#include <cstdint>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace BuddyBerths {

constexpr std::int64_t Quay = 16;
constexpr std::uint32_t MinShips = 7, SeedShipSpan = 4, MaxShips = 10;
constexpr std::int64_t MaxStay = 16;
constexpr std::int64_t HandMaxMoored = 4;  // hand quays: ships moored at once, which bounds the best-plan search
constexpr std::size_t MaxSeedBytes = 4096;
constexpr std::int64_t Turn = -1;  // a plan entry that turns the ship away
static const char* const Names[12] = {"albatross", "brigantine", "coracle", "dhow", "felucca", "galleon",
                                       "junk", "ketch", "lugger", "pinnace", "schooner", "yawl"};

enum class Error { None, Length, Align, Busy, NoShips, TooManyShips, Size, Stay, Overlap, Seed };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::Length: return "length";
        case Error::Align: return "align";
        case Error::Busy: return "busy";
        case Error::NoShips: return "no_ships";
        case Error::TooManyShips: return "too_many_ships";
        case Error::Size: return "size";
        case Error::Stay: return "stay";
        case Error::Overlap: return "overlap";
        case Error::Seed: return "seed";
    }
    return "?";
}

struct Ship {
    std::string Label;
    std::int64_t Size = 1, Stay = 1;
};

struct Layout {
    std::vector<Ship> Ships;
};

using Plan = std::vector<std::int64_t>;  // offsets, or Turn
using Cells = std::vector<std::int64_t>;  // per berth unit: the arrival before which its ship sails (0 = free)

// CPython shuffle: for i from len-1 down to 1, j = _randbelow(i + 1), swap.
template <typename T>
inline void Shuffle(daedalus::pyrandom::PyRandom& R, std::vector<T>& X) {
    for (std::size_t I = X.size() > 0 ? X.size() - 1 : 0; I > 0; --I) {
        const std::size_t J = R.Below(static_cast<std::uint32_t>(I + 1));
        std::swap(X[I], X[J]);
    }
}

// random.Random(Seed): n = 7 + randrange(4); per ship size = 1 << int(random() * 4), stay = 1 + randrange(5);
// names = shuffle(NAMES)[:n].
inline Error FromSeed(const std::string& Seed, Layout& Out) {
    if (Seed.size() > MaxSeedBytes) return Error::Seed;
    daedalus::pyrandom::PyRandom R(Seed);
    Out = Layout{};
    const std::size_t N = MinShips + R.RandRange(SeedShipSpan);
    std::vector<std::pair<std::int64_t, std::int64_t>> SS(N);
    for (std::size_t I = 0; I < N; ++I) {
        SS[I].first = std::int64_t{1} << static_cast<int>(R.RandomDouble() * 4);
        SS[I].second = 1 + static_cast<std::int64_t>(R.RandRange(5));
    }
    std::vector<std::string> Nm(Names, Names + 12);
    Shuffle(R, Nm);
    for (std::size_t I = 0; I < N; ++I) Out.Ships.push_back(Ship{Nm[I], SS[I].first, SS[I].second});
    return Error::None;
}

// A hand-laid quay: 1..10 ships, sizes powers of two up to the quay, stays 1..16, and at most 4 ships moored at
// once (ship k is moored for arrivals k .. k + stay - 1). The moored cap keeps the exact search small; seeded
// quays (stays 1..5) are not capped.
inline Error MakeHand(const std::vector<std::pair<std::int64_t, std::int64_t>>& SizeStay, Layout& Out) {
    if (SizeStay.empty()) return Error::NoShips;
    if (SizeStay.size() > MaxShips) return Error::TooManyShips;
    Out = Layout{};
    for (std::size_t I = 0; I < SizeStay.size(); ++I) {
        const std::int64_t S = SizeStay[I].first, T = SizeStay[I].second;
        if (S < 1 || S > Quay || (S & (S - 1)) != 0) return Error::Size;
        if (T < 1 || T > MaxStay) return Error::Stay;
        Out.Ships.push_back(Ship{"ship" + std::to_string(I), S, T});
    }
    for (std::size_t J = 0; J < Out.Ships.size(); ++J) {
        std::int64_t Moored = 0;
        for (std::size_t K = 0; K <= J; ++K)
            if (static_cast<std::int64_t>(K) + Out.Ships[K].Stay > static_cast<std::int64_t>(J)) ++Moored;
        if (Moored > HandMaxMoored) return Error::Overlap;
    }
    return Error::None;
}

inline bool FreeAt(const Cells& C, std::int64_t J, std::int64_t O, std::int64_t S) {
    if (O < 0 || O % S != 0 || O + S > Quay) return false;
    for (std::int64_t I = O; I < O + S; ++I)
        if (C[static_cast<std::size_t>(I)] > J) return false;
    return true;
}

inline std::vector<std::int64_t> Options(const Cells& C, std::int64_t J, std::int64_t S) {
    std::vector<std::int64_t> V;
    for (std::int64_t O = 0; O < Quay; O += S)
        if (FreeAt(C, J, O, S)) V.push_back(O);
    return V;
}

inline void Moor(Cells& C, std::int64_t O, std::int64_t S, std::int64_t Leave) {
    for (std::int64_t I = O; I < O + S; ++I) C[static_cast<std::size_t>(I)] = Leave;
}

// Turned-away count of a plan, or the first refusal.
inline Error Simulate(const Layout& L, const Plan& P, std::int64_t& Turned) {
    if (P.size() != L.Ships.size()) return Error::Length;
    Cells C(static_cast<std::size_t>(Quay), 0);
    Turned = 0;
    for (std::size_t J = 0; J < P.size(); ++J) {
        const std::int64_t S = L.Ships[J].Size, O = P[J], Now = static_cast<std::int64_t>(J);
        if (O == Turn) {
            ++Turned;
            continue;
        }
        if (O < 0 || O >= Quay || O % S != 0 || O + S > Quay) return Error::Align;
        if (!FreeAt(C, Now, O, S)) return Error::Busy;
        Moor(C, O, S, Now + L.Ships[J].Stay);
    }
    return Error::None;
}

// Largest aligned free run holding [O, O + S).
inline std::int64_t Room(const Cells& C, std::int64_t J, std::int64_t O, std::int64_t S) {
    while (S < Quay && FreeAt(C, J, O - O % (2 * S), 2 * S)) {
        O -= O % (2 * S);
        S *= 2;
    }
    return S;
}

enum class Habit { Lowest, Tightest, Highest };

inline Plan HabitPlan(const Layout& L, Habit H) {
    Cells C(static_cast<std::size_t>(Quay), 0);
    Plan P;
    for (std::size_t J = 0; J < L.Ships.size(); ++J) {
        const std::int64_t S = L.Ships[J].Size, Now = static_cast<std::int64_t>(J);
        const std::vector<std::int64_t> V = Options(C, Now, S);
        std::int64_t O = Turn;
        if (!V.empty()) {
            if (H == Habit::Lowest) O = V.front();
            else if (H == Habit::Highest) O = V.back();
            else {
                std::int64_t TopRoom = Quay + 1;
                for (std::int64_t X : V) {
                    const std::int64_t R = Room(C, Now, X, S);
                    if (R < TopRoom) {
                        TopRoom = R;
                        O = X;
                    }
                }
            }
        }
        P.push_back(O);
        if (O != Turn) Moor(C, O, S, Now + L.Ships[J].Stay);
    }
    return P;
}

// The exact best plan: fewest turned away; ties go to the first choice in offset order, Turn last.
// Memo key: the arrival index and, per unit, when it frees (0 once free), so equal futures merge.
class BestSearch {
public:
    explicit BestSearch(const Layout& L) : L_(L) {}

    std::size_t States() const { return Memo_.size(); }

    Plan Run() {
        Plan P;
        Cells C(static_cast<std::size_t>(Quay), 0);
        Go(0, C);
        for (std::size_t J = 0; J < L_.Ships.size(); ++J) {
            Cells K = Norm(J, C);
            const std::int64_t O = Memo_[Key(J, K)].second;
            P.push_back(O);
            if (O != Turn) Moor(K, O, L_.Ships[J].Size, static_cast<std::int64_t>(J) + L_.Ships[J].Stay);
            C = K;
        }
        return P;
    }

private:
    static Cells Norm(std::size_t J, const Cells& C) {
        Cells K = C;
        for (std::int64_t& D : K)
            if (D <= static_cast<std::int64_t>(J)) D = 0;
        return K;
    }
    static std::string Key(std::size_t J, const Cells& K) {
        std::string S(1, static_cast<char>(J));
        for (std::int64_t D : K) S.push_back(static_cast<char>(D));  // D <= MaxShips + MaxStay < 128
        return S;
    }
    std::int64_t Go(std::size_t J, const Cells& C) {
        if (J == L_.Ships.size()) return 0;
        const Cells K = Norm(J, C);
        const std::string Ky = Key(J, K);
        const auto It = Memo_.find(Ky);
        if (It != Memo_.end()) return It->second.first;
        const std::int64_t S = L_.Ships[J].Size, Now = static_cast<std::int64_t>(J);
        std::vector<std::int64_t> V = Options(K, Now, S);
        V.push_back(Turn);
        std::int64_t Top = -1, Pick = Turn;
        for (std::int64_t O : V) {
            Cells N = K;
            if (O != Turn) Moor(N, O, S, Now + L_.Ships[J].Stay);
            const std::int64_t R = Go(J + 1, N) + (O == Turn ? 1 : 0);
            if (Top < 0 || R < Top) {
                Top = R;
                Pick = O;
            }
        }
        Memo_[Ky] = {Top, Pick};
        return Top;
    }
    const Layout& L_;
    std::map<std::string, std::pair<std::int64_t, std::int64_t>> Memo_;
};

inline Plan Best(const Layout& L) { return BestSearch(L).Run(); }

enum class Verdict { Snug, Fair, Crowded };
inline const char* VerdictName(Verdict V) { return V == Verdict::Snug ? "snug" : V == Verdict::Fair ? "fair" : "crowded"; }

struct PlayResult {
    std::int64_t Turned = 0;
    Verdict V = Verdict::Crowded;
};

// snug = as few turned away as the best plan; fair = no worse than the best of the three habits.
// Opt and Hab: turned-away counts of the best plan and the best habit (see Scores), so a caller playing many
// plans on one quay searches once.
inline Error PlayScored(const Layout& L, const Plan& P, std::int64_t Opt, std::int64_t Hab, PlayResult& R) {
    const Error E = Simulate(L, P, R.Turned);
    if (E != Error::None) return E;
    R.V = R.Turned == Opt ? Verdict::Snug : R.Turned <= Hab ? Verdict::Fair : Verdict::Crowded;
    return Error::None;
}

inline void Scores(const Layout& L, std::int64_t& Opt, std::int64_t& Hab) {
    std::int64_t T = 0;
    Simulate(L, Best(L), Opt);
    Hab = -1;
    for (Habit H : {Habit::Lowest, Habit::Tightest, Habit::Highest}) {
        Simulate(L, HabitPlan(L, H), T);
        if (Hab < 0 || T < Hab) Hab = T;
    }
}

inline Error Play(const Layout& L, const Plan& P, PlayResult& R) {
    std::int64_t Opt = 0, Hab = 0;
    Scores(L, Opt, Hab);
    return PlayScored(L, P, Opt, Hab, R);
}

}  // namespace BuddyBerths
}  // namespace DaedalusDiskSaver
