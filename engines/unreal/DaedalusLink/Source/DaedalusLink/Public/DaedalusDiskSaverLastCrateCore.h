// SPDX-License-Identifier: MIT
// G549 Last Crate core, header-only C++17 port of tools/streaming/last_crate.py (G577 batch 5).
// Takes the face-down stack as the Python tool shuffled it (crate KiB top first; the seeded
// shuffle stays in Python) and the hold, and ports the exact advisor (bust chance, load and sail
// values as Python Fraction strings, including Python's "0.0" when no crate still fits), the best
// stopping point, the turn rules, move validation and the outcome. Engine-free: no Unreal
// includes, no exceptions, no RTTI. At most MaxCrates crates of at most MaxWeight KiB, so every
// product in the exact comparisons fits in int64.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace LastCrate {

constexpr std::int64_t MaxKib = 100000000;  // census_budget.MAX_KIB, the hold range
constexpr std::int64_t MaxWeight = 1000000000;
constexpr std::size_t MaxCrates = 4096;
constexpr std::size_t MaxMoves = 8192;
enum class Error { None, BadStack, Hold, Mode, Short, Move, Empty, Long };
enum class Outcome { Full, Light, Overboard };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadStack: return "stack";
        case Error::Hold: return "hold";
        case Error::Mode: return "mode";
        case Error::Short: return "short";
        case Error::Move: return "move";
        case Error::Empty: return "empty";
        case Error::Long: return "long";
    }
    return "?";
}
inline const char* OutcomeName(Outcome O) {
    switch (O) {
        case Outcome::Full: return "full";
        case Outcome::Light: return "light";
        case Outcome::Overboard: return "overboard";
    }
    return "?";
}

inline std::int64_t Gcd(std::int64_t A, std::int64_t B) {
    while (B) {
        const std::int64_t T = A % B;
        A = B;
        B = T;
    }
    return A < 0 ? -A : A;
}
// str(Fraction(Num, Den)) for Den > 0.
inline std::string FractionText(std::int64_t Num, std::int64_t Den) {
    const std::int64_t G = Gcd(Num, Den);
    if (G > 1) {
        Num /= G;
        Den /= G;
    }
    return Den == 1 ? std::to_string(Num) : std::to_string(Num) + "/" + std::to_string(Den);
}

struct Advice {
    std::string Bust, Load, Sail;
    bool AdviseLoad = false;
};

// advise(): Remaining is the unseen stack (order unknown to the advisor).
inline Advice Advise(std::int64_t Loaded, const std::vector<std::int64_t>& Remaining, std::size_t From, std::int64_t Hold) {
    Advice A;
    A.Sail = FractionText(Loaded, 1);
    const std::int64_t N = static_cast<std::int64_t>(Remaining.size() - From);
    if (N == 0) {
        A.Bust = "0";
        A.Load = A.Sail;
        return A;
    }
    std::int64_t Busts = 0, Sum = 0, Fits = 0;
    for (std::size_t I = From; I < Remaining.size(); ++I) {
        if (Loaded + Remaining[I] > Hold) {
            ++Busts;
        } else {
            Sum += Loaded + Remaining[I];
            ++Fits;
        }
    }
    A.Bust = FractionText(Busts, N);
    A.Load = Fits ? FractionText(Sum, N) : "0.0";  // Python: sum() of nothing is int 0, and 0 / n is a float
    A.AdviseLoad = Fits && Sum > Loaded * N;
    return A;
}

inline std::int64_t BestStop(const std::vector<std::int64_t>& Deck, std::int64_t Hold) {
    std::int64_t Best = 0, Total = 0;
    for (std::int64_t W : Deck) {
        Total += W;
        if (Total > Hold) break;
        Best = Total;
    }
    return Best;
}

struct Turn {
    Advice A;
    bool Load = false;
};
struct Result {
    Error Err = Error::None;
    std::vector<Turn> Turns;
    std::int64_t Carried = 0, Best = 0;
    Outcome O = Outcome::Overboard;
};

inline Result Play(const std::vector<std::int64_t>& Deck, std::int64_t Hold, bool HasMoves, const std::vector<std::string>& Moves, bool Auto) {
    Result R;
    if (Hold < 1 || Hold > MaxKib) {
        R.Err = Error::Hold;
        return R;
    }
    if (HasMoves == Auto) {
        R.Err = Error::Mode;
        return R;
    }
    bool Ok = !Deck.empty() && Deck.size() <= MaxCrates && Moves.size() <= MaxMoves;
    for (std::int64_t W : Deck) Ok = Ok && W >= 0 && W <= MaxWeight;
    if (!Ok) {
        R.Err = Error::BadStack;
        return R;
    }
    std::int64_t Total = 0;
    std::size_t I = 0, Next = 0;
    bool Over = false;
    while (true) {
        Turn T;
        T.A = Advise(Total, Deck, I, Hold);
        if (HasMoves) {
            if (Next == Moves.size()) {
                R.Err = Error::Short;
                return R;
            }
            const std::string& M = Moves[Next++];
            if (M != "load" && M != "sail") {
                R.Err = Error::Move;
                return R;
            }
            T.Load = M == "load";
        } else {
            T.Load = T.A.AdviseLoad;
        }
        if (T.Load) {
            if (I == Deck.size()) {
                R.Err = Error::Empty;
                return R;
            }
            Total += Deck[I++];
            R.Turns.push_back(T);
            if (Total > Hold) {
                Over = true;
                break;
            }
        } else {
            R.Turns.push_back(T);
            break;
        }
    }
    if (Next < Moves.size()) {
        R.Err = Error::Long;
        return R;
    }
    R.Best = BestStop(Deck, Hold);
    R.Carried = Over ? 0 : Total;
    R.O = Over ? Outcome::Overboard : R.Carried == R.Best ? Outcome::Full : Outcome::Light;
    return R;
}

}  // namespace LastCrate
}  // namespace DaedalusDiskSaver
