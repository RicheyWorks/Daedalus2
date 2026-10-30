// SPDX-License-Identifier: MIT
// G598 Tidelinks Golf (DiskSaver Island, quest q_tidelinks_golf): a seeded links course of a few holes on a
// straight line. Each hole has a length (a multiple of 10 m), a par (3 up to 220 m, 4 up to 400 m, else 5), a
// wind and an optional 20 m water band. Each shot picks a club; the ball flies the club's carry plus 10 m per
// wind step (at least 10 m) toward the pin, possibly past it. Water, or more than 50 m beyond either end of
// the hole, costs a penalty stroke and the ball stays put. Landing on the pin holes the ball; the putter
// holes out from 10 m or less and otherwise rolls 10 m toward the pin. A hole is capped at 10 strokes,
// penalties included. The core lays out a course with DaedalusPyRandomCore.h (CPython random.Random(str):
// randrange, random, and shuffle built from its _randbelow), plays a card, and shows three caddie habits
// (safe, bold, lay-up) and the exact best card. Golden file: tools/streaming/tidelinks_golf_parity.py.
// Header-only C++17; no Unreal includes, no exceptions, no RTTI; errors are return codes.
#pragma once
#include "DaedalusPyRandomCore.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace TidelinksGolf {

constexpr int NumClubs = 8;
static const char ClubCodes[NumClubs] = {'D', 'W', '5', '7', '9', 'S', 'C', 'P'};
static const std::int64_t ClubCarry[NumClubs] = {220, 190, 160, 130, 100, 60, 20, 0};
constexpr int Putter = 7;
constexpr std::int64_t Cap = 10, Oob = 50, WaterWidth = 20;
constexpr std::size_t HandMaxHoles = 9, MaxSeedBytes = 4096;
static const char* const Names[12] = {"Anchor_Reach", "Bellbuoy", "Capstan_Rise", "Dunes", "Eelgrass", "Foghorn",
                                       "Gullwing", "Harbour_Mouth", "Inkwell", "Jetty_End", "Kelp_Bed", "Lantern_Point"};

enum class Error { None, Holes, Club, CapHit, Short, Extra, NoHoles, TooManyHoles, Length, Wind, Water, Seed };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::Holes: return "holes";
        case Error::Club: return "club";
        case Error::CapHit: return "cap";
        case Error::Short: return "short";
        case Error::Extra: return "extra";
        case Error::NoHoles: return "no_holes";
        case Error::TooManyHoles: return "too_many_holes";
        case Error::Length: return "length";
        case Error::Wind: return "wind";
        case Error::Water: return "water";
        case Error::Seed: return "seed";
    }
    return "?";
}

struct Hole {
    std::string Name;
    std::int64_t Length = 0, Wind = 0, Water = 0;  // Water 0 = none, else the band [Water, Water + 20)
};

using Clubs = std::vector<int>;    // club indices into ClubCodes
using Card = std::vector<Clubs>;  // one club list per hole

inline std::int64_t Par(std::int64_t Length) { return Length <= 220 ? 3 : Length <= 400 ? 4 : 5; }

inline int ClubIndex(char C) {
    for (int I = 0; I < NumClubs; ++I)
        if (ClubCodes[I] == C) return I;
    return -1;
}

// CPython shuffle: for i from len-1 down to 1, j = _randbelow(i + 1), swap.
template <typename T>
inline void Shuffle(daedalus::pyrandom::PyRandom& R, std::vector<T>& X) {
    for (std::size_t I = X.size() > 0 ? X.size() - 1 : 0; I > 0; --I) {
        const std::size_t J = R.Below(static_cast<std::uint32_t>(I + 1));
        std::swap(X[I], X[J]);
    }
}

// random.Random(Seed): n = 4 + randrange(3); per hole length = 100 + 10 * randrange(41), wind = randrange(7) - 3,
// wet = random() < 0.7, spot = 30 + 10 * randrange((length - 70) / 10); names = shuffle(NAMES)[:n].
inline Error FromSeed(const std::string& Seed, std::vector<Hole>& Out) {
    if (Seed.size() > MaxSeedBytes) return Error::Seed;
    daedalus::pyrandom::PyRandom R(Seed);
    Out.clear();
    const std::size_t N = 4 + R.RandRange(3);
    for (std::size_t I = 0; I < N; ++I) {
        Hole H;
        H.Length = 100 + 10 * static_cast<std::int64_t>(R.RandRange(41));
        H.Wind = static_cast<std::int64_t>(R.RandRange(7)) - 3;
        const bool Wet = R.RandomDouble() < 0.7;
        const std::int64_t Spot = 30 + 10 * static_cast<std::int64_t>(R.RandRange(static_cast<std::uint32_t>((H.Length - 70) / 10)));
        H.Water = Wet ? Spot : 0;
        Out.push_back(H);
    }
    std::vector<std::string> Nm(Names, Names + 12);
    Shuffle(R, Nm);
    for (std::size_t I = 0; I < N; ++I) Out[I].Name = Nm[I];
    return Error::None;
}

struct HandHole {
    std::int64_t Length = 0, Wind = 0, Water = 0;
};

// A hand course: 1..9 holes, lengths 30..600 in tens, wind -5..5, water 0 or a multiple of 10 in 10..length-30.
inline Error MakeHand(const std::vector<HandHole>& Hs, std::vector<Hole>& Out) {
    if (Hs.empty()) return Error::NoHoles;
    if (Hs.size() > HandMaxHoles) return Error::TooManyHoles;
    Out.clear();
    for (std::size_t I = 0; I < Hs.size(); ++I) {
        const HandHole& H = Hs[I];
        if (H.Length < 30 || H.Length > 600 || H.Length % 10 != 0) return Error::Length;
        if (H.Wind < -5 || H.Wind > 5) return Error::Wind;
        if (H.Water != 0 && (H.Water % 10 != 0 || H.Water < 10 || H.Water > H.Length - 30)) return Error::Water;
        Out.push_back(Hole{"Hand_" + std::to_string(I), H.Length, H.Wind, H.Water});
    }
    return Error::None;
}

struct Shot {
    std::int64_t To = 0;
    bool Penalty = false, Holed = false;
};

inline Shot Hit(const Hole& H, std::int64_t P, int Club) {
    const std::int64_t D = H.Length - P;
    const std::int64_t Abs = D < 0 ? -D : D;
    if (Club == Putter) {
        if (Abs <= 10) return Shot{H.Length, false, true};
        return Shot{P + (D > 0 ? 10 : -10), false, false};
    }
    std::int64_t Carry = ClubCarry[Club] + 10 * H.Wind;
    if (Carry < 10) Carry = 10;
    const std::int64_t Q = P + (D > 0 ? Carry : -Carry);
    if (Q == H.Length) return Shot{Q, false, true};
    if (Q < -Oob || Q > H.Length + Oob || (H.Water != 0 && H.Water <= Q && Q < H.Water + WaterWidth)) return Shot{P, true, false};
    return Shot{Q, false, false};
}

// Strokes of one hole's clubs, or the first refusal.
inline Error PlayHole(const Hole& H, const Clubs& Cs, std::int64_t& Strokes) {
    std::int64_t P = 0;
    Strokes = 0;
    for (std::size_t K = 0; K < Cs.size(); ++K) {
        if (Cs[K] < 0 || Cs[K] >= NumClubs) return Error::Club;
        const Shot S = Hit(H, P, Cs[K]);
        Strokes += 1 + (S.Penalty ? 1 : 0);
        if (Strokes > Cap) return Error::CapHit;
        P = S.To;
        if (S.Holed) return K + 1 == Cs.size() ? Error::None : Error::Extra;
    }
    return Error::Short;
}

// Strokes of a card that holes out on every hole, ignoring the cap (habits may go over it).
inline std::int64_t RawStrokes(const std::vector<Hole>& Hs, const Card& C) {
    std::int64_t T = 0;
    for (std::size_t I = 0; I < Hs.size() && I < C.size(); ++I) {
        std::int64_t P = 0;
        for (int Cl : C[I]) {
            const Shot S = Hit(Hs[I], P, Cl);
            P = S.To;
            T += 1 + (S.Penalty ? 1 : 0);
        }
    }
    return T;
}

// The exact best clubs for a hole: fewest strokes from the tee; shot by shot, the first club in club order
// that keeps the minimum. Positions are multiples of 10 from -50 to length + 50; penalties never help.
inline Clubs BestHole(const Hole& H) {
    const std::int64_t Lo = -Oob, N = (H.Length + 2 * Oob) / 10 + 1;
    const std::int64_t Inf = 1000000000;
    std::vector<std::int64_t> G(static_cast<std::size_t>(N), Inf);
    auto Idx = [&](std::int64_t P) { return static_cast<std::size_t>((P - Lo) / 10); };
    for (bool Changed = true; Changed;) {
        Changed = false;
        for (std::int64_t K = 0; K < N; ++K) {
            const std::int64_t P = Lo + 10 * K;
            for (int C = 0; C < NumClubs; ++C) {
                const Shot S = Hit(H, P, C);
                if (S.Penalty) continue;
                const std::int64_t V = S.Holed ? 1 : 1 + G[Idx(S.To)];
                if (V < G[static_cast<std::size_t>(K)]) {
                    G[static_cast<std::size_t>(K)] = V;
                    Changed = true;
                }
            }
        }
    }
    Clubs Plan;
    std::int64_t P = 0;
    for (;;) {
        int Pick = Putter;
        Shot Sp;
        for (int C = 0; C < NumClubs; ++C) {
            const Shot S = Hit(H, P, C);
            if (!S.Penalty && (S.Holed ? 1 : 1 + G[Idx(S.To)]) == G[Idx(P)]) {
                Pick = C;
                Sp = S;
                break;
            }
        }
        Plan.push_back(Pick);
        if (Sp.Holed) return Plan;
        P = Sp.To;
    }
}

enum class Habit { Safe, Bold, Layup };

// Caddie habits: on the green (10 m or less) putt; otherwise the longest club that lands no more than 10 m
// past the pin (lay-up: not past it at all) and, for safe and lay-up, out of the water. Bold ignores the
// water until it has found it once on the hole, then plays safe. No club fits: putt.
inline Clubs HabitHole(const Hole& H, Habit Kind) {
    Clubs Plan;
    std::int64_t P = 0;
    bool Wet = false;
    for (;;) {
        const std::int64_t D = H.Length > P ? H.Length - P : P - H.Length;
        int Pick = Putter;
        if (D > 10) {
            for (int C = 0; C < Putter; ++C) {
                std::int64_t Carry = ClubCarry[C] + 10 * H.Wind;
                if (Carry < 10) Carry = 10;
                if (Carry > (Kind == Habit::Layup ? D : D + 10)) continue;
                const std::int64_t Q = P + (H.Length > P ? Carry : -Carry);
                if ((Kind != Habit::Bold || Wet) && H.Water != 0 && H.Water <= Q && Q < H.Water + WaterWidth) continue;
                Pick = C;
                break;
            }
        }
        const Shot S = Hit(H, P, Pick);
        Plan.push_back(Pick);
        Wet = Wet || S.Penalty;
        P = S.To;
        if (S.Holed) return Plan;
    }
}

inline Card HabitCard(const std::vector<Hole>& Hs, Habit Kind) {
    Card C;
    for (const Hole& H : Hs) C.push_back(HabitHole(H, Kind));
    return C;
}

inline Card BestCard(const std::vector<Hole>& Hs) {
    Card C;
    for (const Hole& H : Hs) C.push_back(BestHole(H));
    return C;
}

inline std::int64_t CoursePar(const std::vector<Hole>& Hs) {
    std::int64_t T = 0;
    for (const Hole& H : Hs) T += Par(H.Length);
    return T;
}

enum class Verdict { Masterful, Steady, Rough };
inline const char* VerdictName(Verdict V) { return V == Verdict::Masterful ? "masterful" : V == Verdict::Steady ? "steady" : "rough"; }

struct PlayResult {
    std::int64_t Strokes = 0, ToPar = 0;
    Verdict V = Verdict::Rough;
    std::size_t BadHole = 0;  // the hole of a refusal
};

// masterful = as few strokes as the best card; steady = no worse than the best of the three habits.
inline Error Play(const std::vector<Hole>& Hs, const Card& C, PlayResult& R) {
    R = PlayResult{};
    if (C.size() != Hs.size()) return Error::Holes;
    for (std::size_t I = 0; I < Hs.size(); ++I) {
        std::int64_t S = 0;
        const Error E = PlayHole(Hs[I], C[I], S);
        if (E != Error::None) {
            R.BadHole = I;
            return E;
        }
        R.Strokes += S;
    }
    R.ToPar = R.Strokes - CoursePar(Hs);
    const std::int64_t Opt = RawStrokes(Hs, BestCard(Hs));
    std::int64_t Hab = -1;
    for (Habit K : {Habit::Safe, Habit::Bold, Habit::Layup}) {
        const std::int64_t T = RawStrokes(Hs, HabitCard(Hs, K));
        if (Hab < 0 || T < Hab) Hab = T;
    }
    R.V = R.Strokes == Opt ? Verdict::Masterful : R.Strokes <= Hab ? Verdict::Steady : Verdict::Rough;
    return Error::None;
}

}  // namespace TidelinksGolf
}  // namespace DaedalusDiskSaver
