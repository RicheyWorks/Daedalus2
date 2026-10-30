// SPDX-License-Identifier: MIT
// G558 Quayside Shove core, header-only C++17 port of tools/streaming/quayside_shove.py (G573).
// Takes an already-laid-out 7x7 yard (the Python tool's draw() rows) and ports the push rule, the
// exact BFS par (same U/D/L/R expansion order, so the plan matches), move validation, the
// deadlock check and the verdict. Engine-free: no Unreal includes, no exceptions, no RTTI.
#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace DaedalusDiskSaver {
namespace QuaysideShove {

constexpr int Size = 7;
constexpr int Cells = Size * Size;  // 49 bits of crate mask, player above them
constexpr std::size_t MaxStates = 4000000;
enum class Error { None, BadYard, Letter, Clear, Blocked };
enum class Verdict { Tidy, Shuffled, Stuck };

struct Yard {
    std::uint64_t Walls = 0, Marks = 0, Crates = 0;
    int Player = -1;
};

inline std::uint64_t Bit(int P) { return std::uint64_t{1} << P; }
inline int Popcount(std::uint64_t M) {
    int N = 0;
    for (; M; M &= M - 1) ++N;
    return N;
}

// draw() rows: '#' wall, '@'/'+' player (off/on a mark), '$'/'*' crate (off/on), '.' mark, ' ' or '_' floor.
inline bool ParseYard(const std::vector<std::string>& Rows, Yard& Y) {
    Y = Yard{};
    if (Rows.size() != static_cast<std::size_t>(Size)) return false;
    for (int R = 0; R < Size; ++R) {
        if (Rows[R].size() > static_cast<std::size_t>(Size)) return false;
        for (int C = 0; C < Size; ++C) {
            const char Ch = C < static_cast<int>(Rows[R].size()) ? Rows[R][C] : ' ';
            const int P = R * Size + C;
            switch (Ch) {
                case '#': Y.Walls |= Bit(P); break;
                case '+': Y.Marks |= Bit(P); [[fallthrough]];
                case '@': if (Y.Player >= 0) return false; Y.Player = P; break;
                case '*': Y.Marks |= Bit(P); [[fallthrough]];
                case '$': Y.Crates |= Bit(P); break;
                case '.': Y.Marks |= Bit(P); break;
                case ' ': case '_': break;
                default: return false;
            }
        }
    }
    // the border must be walls so a step never leaves the yard
    for (int I = 0; I < Size; ++I)
        for (int P : {I, (Size - 1) * Size + I, I * Size, I * Size + Size - 1})
            if (!(Y.Walls & Bit(P))) return false;
    return Y.Player >= 0 && Popcount(Y.Crates) == Popcount(Y.Marks) && Popcount(Y.Crates) > 0;
}

inline int DirOf(char D) { return D == 'U' ? 0 : D == 'D' ? 1 : D == 'L' ? 2 : D == 'R' ? 3 : -1; }
inline int Step(int P, int D) {
    static const int Delta[4] = {-Size, Size, -1, 1};
    return P + Delta[D];
}

// move(): false when blocked.
inline bool Move(std::uint64_t Walls, int& Player, std::uint64_t& Crates, int D) {
    const int Next = Step(Player, D);
    if (Walls & Bit(Next)) return false;
    if (Crates & Bit(Next)) {
        const int Beyond = Step(Next, D);
        if ((Walls | Crates) & Bit(Beyond)) return false;
        Crates = (Crates & ~Bit(Next)) | Bit(Beyond);
    }
    Player = Next;
    return true;
}

// solve(): true with Par/Plan, false when the yard cannot be cleared (or the state cap is hit: Capped).
inline bool Solve(const Yard& Y, int Player, std::uint64_t Crates, int& Par, std::string& Plan, bool* Capped = nullptr) {
    if (Capped) *Capped = false;
    const auto Key = [](int P, std::uint64_t C) { return C | (static_cast<std::uint64_t>(P) << Cells); };
    struct Back { std::uint64_t From; char D; };
    std::unordered_map<std::uint64_t, Back> Prev;
    std::vector<std::uint64_t> Queue{Key(Player, Crates)};
    Prev[Queue[0]] = {~std::uint64_t{0}, 0};
    for (std::size_t Head = 0; Head < Queue.size(); ++Head) {
        std::uint64_t S = Queue[Head];
        const std::uint64_t C = S & (Bit(Cells) - 1);
        const int P = static_cast<int>(S >> Cells);
        if (C == Y.Marks) {
            Plan.clear();
            while (Prev[S].From != ~std::uint64_t{0}) {
                Plan.insert(Plan.begin(), Prev[S].D);
                S = Prev[S].From;
            }
            Par = static_cast<int>(Plan.size());
            return true;
        }
        for (int D = 0; D < 4; ++D) {
            int Np = P;
            std::uint64_t Nc = C;
            if (!Move(Y.Walls, Np, Nc, D)) continue;
            const std::uint64_t T = Key(Np, Nc);
            if (Prev.find(T) == Prev.end()) {
                if (Prev.size() >= MaxStates) {
                    if (Capped) *Capped = true;
                    return false;
                }
                Prev[T] = {S, "UDLR"[D]};
                Queue.push_back(T);
            }
        }
    }
    return false;
}

struct Result {
    Error Err = Error::None;
    int Steps = 0, Pushes = 0, OnMarks = 0;
    bool Deadlocked = false;
    Verdict V = Verdict::Stuck;
};

// Par < 0 means the yard has no solution.
inline Result Play(const Yard& Y, int Par, const std::string& Moves) {
    Result R;
    int P = Y.Player;
    std::uint64_t C = Y.Crates;
    for (char Ch : Moves) {
        const int D = DirOf(Ch);
        if (D < 0) { R.Err = Error::Letter; return R; }
        if (C == Y.Marks) { R.Err = Error::Clear; return R; }
        const std::uint64_t Before = C;
        if (!Move(Y.Walls, P, C, D)) { R.Err = Error::Blocked; return R; }
        R.Pushes += C != Before;
    }
    R.Steps = static_cast<int>(Moves.size());
    R.OnMarks = Popcount(C & Y.Marks);
    if (C == Y.Marks) {
        R.V = (Par >= 0 && R.Steps <= Par) ? Verdict::Tidy : Verdict::Shuffled;
    } else {
        int Ignored = 0;
        std::string Unused;
        R.Deadlocked = !Solve(Y, P, C, Ignored, Unused);
        R.V = Verdict::Stuck;
    }
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Tidy ? "tidy" : V == Verdict::Shuffled ? "shuffled" : "stuck";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Letter: return "letter";
        case Error::Clear: return "clear";
        case Error::Blocked: return "blocked";
        case Error::BadYard: return "yard";
        default: return "none";
    }
}

}  // namespace QuaysideShove
}  // namespace DaedalusDiskSaver
