// SPDX-License-Identifier: MIT
// G551 Fleet Soundings core, header-only C++17 port of tools/streaming/fleet_soundings.py (G577 batch 5).
// Takes the puzzle as the Python tool generated it (grid size, fleet lengths longest first, row and
// column soundings, hints; the seeded mooring and hint draw stay in Python) and ports the ship
// placements, the exact backtracking solver (same placement order and pruning, so the solutions
// come out in the same order), and the grid check with Python's exact problem messages and verdict.
// Engine-free: no Unreal includes, no exceptions, no RTTI. Cells are bits of a uint64 (grids up to
// MaxSize x MaxSize); the solver stops after MaxNodes calls. Grid text is ASCII: Python measures
// rows in code points, this port in bytes, so they only differ on non-ASCII rows (refused by both).
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace FleetSoundings {

constexpr int MaxSize = 8;  // Python uses 6 and 7
constexpr int MaxShips = 16;
constexpr std::uint64_t MaxNodes = 50000000;
enum class Error { None, BadPuzzle, Capped };
enum class Verdict { Charted, Short, Reefed };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadPuzzle: return "puzzle";
        case Error::Capped: return "capped";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Charted: return "charted";
        case Verdict::Short: return "short";
        case Verdict::Reefed: return "reefed";
    }
    return "?";
}

struct Hint {
    int Row = 0, Col = 0;
    bool Hull = false;
};
struct Puzzle {
    int Size = 0;
    std::vector<int> Lengths;  // fleet order: longest first
    std::vector<int> Rows, Cols;
    std::vector<Hint> Hints;
};

inline std::uint64_t Bit(int Size, int R, int C) { return std::uint64_t{1} << (R * Size + C); }

inline bool ValidPuzzle(const Puzzle& P) {
    const int N = P.Size;
    if (N < 1 || N > MaxSize || P.Lengths.empty() || P.Lengths.size() > static_cast<std::size_t>(MaxShips)) return false;
    if (P.Rows.size() != static_cast<std::size_t>(N) || P.Cols.size() != static_cast<std::size_t>(N)) return false;
    for (std::size_t I = 0; I < P.Lengths.size(); ++I)
        if (P.Lengths[I] < 1 || P.Lengths[I] > N || (I && P.Lengths[I] > P.Lengths[I - 1])) return false;
    for (int I = 0; I < N; ++I)
        if (P.Rows[I] < 0 || P.Rows[I] > N || P.Cols[I] < 0 || P.Cols[I] > N) return false;
    for (std::size_t I = 0; I < P.Hints.size(); ++I) {
        const Hint& H = P.Hints[I];
        if (H.Row < 0 || H.Row >= N || H.Col < 0 || H.Col >= N) return false;
        for (std::size_t J = 0; J < I; ++J)
            if (P.Hints[J].Row == H.Row && P.Hints[J].Col == H.Col) return false;
    }
    return true;
}

struct Place {
    std::vector<int> R, C;  // cells in order
    std::uint64_t Mask = 0, Halo = 0;
};

// placements(): horizontal first (only horizontal for length 1), row-major.
inline std::vector<Place> Placements(int Size, int N) {
    std::vector<Place> Out;
    for (int V = 0; V < (N == 1 ? 1 : 2); ++V) {
        const bool Vert = V == 1;
        for (int R = 0; R < Size - (Vert ? N - 1 : 0); ++R)
            for (int C = 0; C < Size - (Vert ? 0 : N - 1); ++C) {
                Place P;
                for (int K = 0; K < N; ++K) {
                    const int Rr = Vert ? R + K : R, Cc = Vert ? C : C + K;
                    P.R.push_back(Rr);
                    P.C.push_back(Cc);
                    P.Mask |= Bit(Size, Rr, Cc);
                    for (int Dr = -1; Dr <= 1; ++Dr)
                        for (int Dc = -1; Dc <= 1; ++Dc) {
                            const int A = Rr + Dr, B = Cc + Dc;
                            if (A >= 0 && A < Size && B >= 0 && B < Size) P.Halo |= Bit(Size, A, B);
                        }
                }
                Out.push_back(P);
            }
    }
    return Out;
}

namespace Detail {
struct Solver {
    const Puzzle* P = nullptr;
    int Limit = 0;
    std::vector<std::vector<Place>> Places;  // by length
    std::vector<int> Rc, Cc, Blocked;
    std::uint64_t Occupied = 0, ShipHint = 0, Nodes = 0;
    std::vector<std::uint64_t> Sols;
    bool Capped = false;

    void Rec(std::size_t K, std::size_t Start) {
        if (Capped || ++Nodes > MaxNodes) {
            Capped = true;
            return;
        }
        if (Sols.size() >= static_cast<std::size_t>(Limit)) return;
        const int N = P->Size;
        if (K == P->Lengths.size()) {
            if (Rc == P->Rows && Cc == P->Cols && (ShipHint & ~Occupied) == 0) Sols.push_back(Occupied);
            return;
        }
        int Left = 0;
        for (std::size_t I = K; I < P->Lengths.size(); ++I) Left += P->Lengths[I];
        for (int I = 0; I < N; ++I)
            if (P->Rows[I] - Rc[I] > Left || P->Cols[I] - Cc[I] > Left) return;
        const int L = P->Lengths[K];
        const std::vector<Place>& Opts = Places[L];
        for (std::size_t Idx = (K && P->Lengths[K - 1] == L) ? Start : 0; Idx < Opts.size(); ++Idx) {
            const Place& Pl = Opts[Idx];
            bool Hit = false;
            for (int I = 0; I < L && !Hit; ++I) Hit = Blocked[Pl.R[I] * N + Pl.C[I]] > 0;
            if (Hit) continue;
            bool Over = false;
            for (int I = 0; I < L && !Over; ++I) Over = Rc[Pl.R[I]] + 1 > P->Rows[Pl.R[I]] || Cc[Pl.C[I]] + 1 > P->Cols[Pl.C[I]];
            if (Over) {
                bool Skip = false;
                for (int I = 0; I < L && !Skip; ++I) {
                    int InRow = 0, InCol = 0;
                    for (int J = 0; J < L; ++J) {
                        InRow += Pl.R[J] == Pl.R[I];
                        InCol += Pl.C[J] == Pl.C[I];
                    }
                    Skip = Rc[Pl.R[I]] + InRow > P->Rows[Pl.R[I]] || Cc[Pl.C[I]] + InCol > P->Cols[Pl.C[I]];
                }
                if (Skip) continue;
            }
            for (int I = 0; I < L; ++I) {
                ++Rc[Pl.R[I]];
                ++Cc[Pl.C[I]];
            }
            Occupied |= Pl.Mask;
            for (int Q = 0; Q < N * N; ++Q)
                if (Pl.Halo >> Q & 1) ++Blocked[Q];
            Rec(K + 1, Idx + 1);
            for (int Q = 0; Q < N * N; ++Q)
                if (Pl.Halo >> Q & 1) --Blocked[Q];
            for (int I = 0; I < L; ++I) {
                --Rc[Pl.R[I]];
                --Cc[Pl.C[I]];
            }
            Occupied &= ~Pl.Mask;
        }
    }
};
}  // namespace Detail

// solve(): up to Limit solutions (hull cell masks) in Python's discovery order.
inline Error Solve(const Puzzle& P, bool UseHints, int Limit, std::vector<std::uint64_t>& Sols) {
    if (!ValidPuzzle(P) || Limit < 0 || Limit > 1000) return Error::BadPuzzle;
    Detail::Solver S;
    S.P = &P;
    S.Limit = Limit;
    const int N = P.Size;
    std::uint64_t Water = 0;
    if (UseHints)
        for (const Hint& H : P.Hints) (H.Hull ? S.ShipHint : Water) |= Bit(N, H.Row, H.Col);
    S.Places.resize(N + 1);
    for (int L = 1; L <= N; ++L)
        for (const Place& Pl : Placements(N, L))
            if (!(Pl.Mask & Water)) S.Places[L].push_back(Pl);
    S.Rc.assign(N, 0);
    S.Cc.assign(N, 0);
    S.Blocked.assign(N * N, 0);
    S.Rec(0, 0);
    if (S.Capped) return Error::Capped;
    Sols = S.Sols;
    return Error::None;
}

inline std::vector<std::string> GridOf(int Size, std::uint64_t Mask) {
    std::vector<std::string> G(Size, std::string(Size, '.'));
    for (int R = 0; R < Size; ++R)
        for (int C = 0; C < Size; ++C)
            if (Mask & Bit(Size, R, C)) G[R][C] = '#';
    return G;
}

struct Result {
    Error Err = Error::None;
    Verdict V = Verdict::Reefed;
    std::vector<std::string> Problems;
};

// check(): the player's grid of '#' hull and '.' water rows.
inline Result Check(const Puzzle& P, const std::vector<std::string>& Grid) {
    Result R;
    if (!ValidPuzzle(P)) {
        R.Err = Error::BadPuzzle;
        return R;
    }
    const int N = P.Size;
    const std::string Sz = std::to_string(N);
    bool Shape = Grid.size() == static_cast<std::size_t>(N);
    for (const std::string& Row : Grid) Shape = Shape && Row.size() == static_cast<std::size_t>(N);
    if (!Shape) {
        R.Problems.push_back("grid must be " + Sz + " rows of " + Sz + " cells");
        return R;
    }
    for (const std::string& Row : Grid)
        for (char Ch : Row)
            if (Ch != '#' && Ch != '.') {
                R.Problems = {"use only # and ."};
                return R;
            }
    auto At = [&](int A, int B) { return A >= 0 && A < N && B >= 0 && B < N && Grid[A][B] == '#'; };
    std::vector<std::vector<std::pair<int, int>>> Groups;
    std::vector<bool> Seen(N * N, false);
    for (int Rr = 0; Rr < N; ++Rr)
        for (int Cc = 0; Cc < N; ++Cc) {
            if (!At(Rr, Cc) || Seen[Rr * N + Cc]) continue;
            std::vector<std::pair<int, int>> Stack{{Rr, Cc}}, G;
            Seen[Rr * N + Cc] = true;
            while (!Stack.empty()) {
                const auto Q = Stack.back();
                Stack.pop_back();
                G.push_back(Q);
                const int Dr[4] = {1, -1, 0, 0}, Dc[4] = {0, 0, 1, -1};
                for (int D = 0; D < 4; ++D) {
                    const int A = Q.first + Dr[D], B = Q.second + Dc[D];
                    if (At(A, B) && !Seen[A * N + B]) {
                        Seen[A * N + B] = true;
                        Stack.push_back({A, B});
                    }
                }
            }
            std::sort(G.begin(), G.end());
            Groups.push_back(G);
        }
    for (const auto& G : Groups) {
        bool RowsDiffer = false, ColsDiffer = false;
        for (const auto& Q : G) {
            RowsDiffer = RowsDiffer || Q.first != G[0].first;
            ColsDiffer = ColsDiffer || Q.second != G[0].second;
        }
        if (RowsDiffer && ColsDiffer)
            R.Problems.push_back("ship at row " + std::to_string(G[0].first) + " col " + std::to_string(G[0].second) + " is bent");
    }
    for (int Rr = 0; Rr < N; ++Rr)
        for (int Cc = 0; Cc < N; ++Cc) {
            if (!At(Rr, Cc)) continue;
            for (int Dc : {1, -1})
                if (At(Rr + 1, Cc + Dc) && !At(Rr + 1, Cc) && !At(Rr, Cc + Dc))
                    R.Problems.push_back("ships touch diagonally at row " + std::to_string(Rr) + " col " + std::to_string(Cc));
        }
    if (R.Problems.empty()) {
        std::vector<int> Got, Want = P.Lengths;
        for (const auto& G : Groups) Got.push_back(static_cast<int>(G.size()));
        std::sort(Got.begin(), Got.end());
        std::sort(Want.begin(), Want.end());
        if (Got != Want) R.Problems.push_back("the moored ships are not the fleet");
    }
    if (!R.Problems.empty()) return R;
    for (int I = 0; I < N; ++I) {
        int Row = 0, Col = 0;
        for (int J = 0; J < N; ++J) {
            Row += Grid[I][J] == '#';
            Col += Grid[J][I] == '#';
        }
        if (Row != P.Rows[I])
            R.Problems.push_back("row " + std::to_string(I) + " sounds " + std::to_string(Row) + ", clue " + std::to_string(P.Rows[I]));
        if (Col != P.Cols[I])
            R.Problems.push_back("col " + std::to_string(I) + " sounds " + std::to_string(Col) + ", clue " + std::to_string(P.Cols[I]));
    }
    for (const Hint& H : P.Hints)
        if ((Grid[H.Row][H.Col] == '#') != H.Hull)
            R.Problems.push_back("hint at row " + std::to_string(H.Row) + " col " + std::to_string(H.Col) + " not matched");
    R.V = R.Problems.empty() ? Verdict::Charted : Verdict::Short;
    return R;
}

}  // namespace FleetSoundings
}  // namespace DaedalusDiskSaver
