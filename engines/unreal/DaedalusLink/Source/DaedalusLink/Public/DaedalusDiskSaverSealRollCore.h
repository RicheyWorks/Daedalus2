// SPDX-License-Identifier: MIT
// G560 Seal Roll core, header-only C++17 port of tools/streaming/seal_roll.py (G574 batch 2).
// Takes an already-laid-out 7x7 quay (walls, up to 4 chalk marks in order, dock, start, as laid out
// by the Python tool) and ports the tipping rule, the exact BFS par (same N/S/E/W expansion order,
// so the plan matches), tip validation and the verdict. Engine-free: no Unreal includes, no
// exceptions, no RTTI; errors come back as codes.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace SealRoll {

constexpr int Size = 7;
constexpr int Cells = Size * Size;
constexpr int MaxMarks = 4;
enum Side { Up, Down, North, South, East, West };
enum class Error { None, Letter, Wall };
enum class Verdict { True, Wobbly, OffMark };

struct Quay {
    std::vector<bool> Walls = std::vector<bool>(Cells, false);
    std::vector<int> Marks;  // cell per mark, in mark order (a, b, c, d)
    int Dock = -1, Start = -1;
};

inline int DirOf(char D) { return D == 'N' ? 0 : D == 'S' ? 1 : D == 'E' ? 2 : D == 'W' ? 3 : -1; }

// TIP table: where the seal goes when the cube tips in direction D.
inline int TipSeal(int Seal, int D) {
    static const int T[4][6] = {
        /* N */ {North, South, Down, Up, East, West},
        /* S */ {South, North, Up, Down, East, West},
        /* E */ {East, West, North, South, Down, Up},
        /* W */ {West, East, North, South, Up, Down},
    };
    return T[D][Seal];
}
inline int TipCell(int P, int D) {
    static const int Delta[4] = {-Size, Size, 1, -1};
    return P + Delta[D];
}
inline const char* SideName(int S) {
    static const char* N[6] = {"up", "down", "north", "south", "east", "west"};
    return N[S];
}

// Border must be walls (a tip can never leave the quay); marks, dock and start on the floor.
inline bool ValidQuay(const Quay& Q) {
    if (Q.Walls.size() != static_cast<std::size_t>(Cells)) return false;
    for (int I = 0; I < Size; ++I)
        for (int P : {I, (Size - 1) * Size + I, I * Size, I * Size + Size - 1})
            if (!Q.Walls[P]) return false;
    if (Q.Marks.empty() || Q.Marks.size() > static_cast<std::size_t>(MaxMarks)) return false;
    std::vector<int> All(Q.Marks);
    All.push_back(Q.Dock);
    All.push_back(Q.Start);
    for (int P : All)
        if (P < 0 || P >= Cells || Q.Walls[P]) return false;
    for (std::size_t i = 0; i < Q.Marks.size(); ++i)
        for (std::size_t j = i + 1; j < Q.Marks.size(); ++j)
            if (Q.Marks[i] == Q.Marks[j]) return false;
    return true;
}

inline int MarkIndex(const Quay& Q, int P) {
    for (std::size_t i = 0; i < Q.Marks.size(); ++i)
        if (Q.Marks[i] == P) return static_cast<int>(i);
    return -1;
}

// solve(): false when no tip sequence stamps every mark and ends on the dock.
inline bool Solve(const Quay& Q, int& Par, std::string& Plan) {
    if (!ValidQuay(Q)) return false;
    const unsigned Full = (1u << Q.Marks.size()) - 1u;
    const auto Key = [](int P, int S, unsigned M) { return (static_cast<std::size_t>(P) * 6 + S) * 16 + M; };
    std::vector<std::int64_t> Prev(static_cast<std::size_t>(Cells) * 6 * 16, -2);
    std::vector<char> How(Prev.size(), 0);
    const int M0i = MarkIndex(Q, Q.Start);
    const std::size_t S0 = Key(Q.Start, Up, M0i >= 0 ? 1u << M0i : 0u);
    Prev[S0] = -1;
    std::vector<std::size_t> Queue{S0};
    for (std::size_t Head = 0; Head < Queue.size(); ++Head) {
        std::size_t S = Queue[Head];
        const unsigned M = static_cast<unsigned>(S % 16);
        const int Seal = static_cast<int>((S / 16) % 6);
        const int P = static_cast<int>(S / 96);
        if (M == Full && P == Q.Dock) {
            Plan.clear();
            while (Prev[S] != -1) {
                Plan.insert(Plan.begin(), How[S]);
                S = static_cast<std::size_t>(Prev[S]);
            }
            Par = static_cast<int>(Plan.size());
            return true;
        }
        for (int D = 0; D < 4; ++D) {
            const int Np = TipCell(P, D);
            if (Q.Walls[Np]) continue;
            const int Ns = TipSeal(Seal, D);
            const int Mi = MarkIndex(Q, Np);
            const unsigned Nm = (Mi >= 0 && Ns == Up) ? (M | (1u << Mi)) : M;
            const std::size_t T = Key(Np, Ns, Nm);
            if (Prev[T] == -2) {
                Prev[T] = static_cast<std::int64_t>(Queue[Head]);
                How[T] = "NSEW"[D];
                Queue.push_back(T);
            }
        }
    }
    return false;
}

struct Result {
    Error Err = Error::None;
    int Count = 0;
    unsigned Stamped = 0;
    int Seal = Up;
    bool OnDock = false;
    Verdict V = Verdict::OffMark;
};

// Par < 0 means the quay has no solution.
inline Result Play(const Quay& Q, int Par, const std::string& Tips) {
    Result R;
    int P = Q.Start, Seal = Up;
    const int M0 = MarkIndex(Q, P);
    if (M0 >= 0) R.Stamped |= 1u << M0;
    for (char Ch : Tips) {
        const int D = DirOf(Ch);
        if (D < 0) { R.Err = Error::Letter; return R; }
        const int Np = TipCell(P, D);
        if (Np < 0 || Np >= Cells || Q.Walls[Np]) { R.Err = Error::Wall; return R; }
        P = Np;
        Seal = TipSeal(Seal, D);
        const int Mi = MarkIndex(Q, P);
        if (Mi >= 0 && Seal == Up) R.Stamped |= 1u << Mi;
    }
    R.Count = static_cast<int>(Tips.size());
    R.Seal = Seal;
    R.OnDock = P == Q.Dock;
    const bool Done = R.Stamped == (1u << Q.Marks.size()) - 1u && R.OnDock;
    R.V = Done ? ((Par >= 0 && R.Count <= Par) ? Verdict::True : Verdict::Wobbly) : Verdict::OffMark;
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::True ? "true" : V == Verdict::Wobbly ? "wobbly" : "off_mark";
}
inline const char* ErrorName(Error E) {
    return E == Error::Letter ? "letter" : E == Error::Wall ? "wall" : "none";
}

}  // namespace SealRoll
}  // namespace DaedalusDiskSaver
