// SPDX-License-Identifier: MIT
// G564 Rope Run core, header-only C++17 port of tools/streaming/rope_run.py (G575 batch 3).
// Takes an already-laid-out 5x6 quay (grip per open square, crates, start and dock, as laid out by
// the Python tool) and ports the exhaustive best-grip search over simple paths (same N/S/E/W depth
// first order and strict-improvement rule, so the route matches), the best-neighbour greedy, route
// validation and the verdict. Engine-free: no Unreal includes, no exceptions, no RTTI. The search
// counts the squares it visits and stops at MaxVisits (Error::Capped) instead of running away.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace RopeRun {

constexpr int Rows = 5, Cols = 6, Cells = Rows * Cols;
constexpr int MaxGrip = 9;
constexpr std::uint64_t MaxVisits = 200000000ULL;
enum class Error { None, BadQuay, Capped, Letter, Dock, Off, Cross };
enum class Verdict { Taut, Slack, Loose };

struct Quay {
    std::vector<int> Grip = std::vector<int>(Cells, 0);  // 0 = crate, 1..9 = grip
    int Start = -1, Dock = -1;
};

inline bool ValidQuay(const Quay& Q) {
    if (Q.Grip.size() != static_cast<std::size_t>(Cells)) return false;
    for (int G : Q.Grip)
        if (G < 0 || G > MaxGrip) return false;
    return Q.Start >= 0 && Q.Start < Cells && Q.Dock >= 0 && Q.Dock < Cells && Q.Grip[Q.Start] && Q.Grip[Q.Dock];
}

inline int DirOf(char D) { return D == 'N' ? 0 : D == 'S' ? 1 : D == 'E' ? 2 : D == 'W' ? 3 : -1; }
// neighbour cell in direction D, or -1 off the quay
inline int Step(int P, int D) {
    const int R = P / Cols, C = P % Cols;
    const int Nr = R + (D == 0 ? -1 : D == 1 ? 1 : 0), Nc = C + (D == 2 ? 1 : D == 3 ? -1 : 0);
    return (Nr < 0 || Nr >= Rows || Nc < 0 || Nc >= Cols) ? -1 : Nr * Cols + Nc;
}

struct Search {
    const Quay* Q = nullptr;
    std::vector<bool> Seen;
    std::string Route, BestRoute;
    int Best = -1;
    std::uint64_t Visits = 0;
    bool Capped = false;

    void Dfs(int Cell, int Score) {
        if (Capped || ++Visits > MaxVisits) {
            Capped = true;
            return;
        }
        if (Cell == Q->Dock) {
            if (Score > Best) {
                Best = Score;
                BestRoute = Route;
            }
            return;
        }
        for (int D = 0; D < 4; ++D) {
            const int N = Step(Cell, D);
            if (N < 0 || !Q->Grip[N] || Seen[N]) continue;
            Seen[N] = true;
            Route.push_back("NSEW"[D]);
            Dfs(N, Score + Q->Grip[N]);
            Route.pop_back();
            Seen[N] = false;
        }
    }
};

// solve(): None with Par/Route, or Capped/BadQuay; Par = -1 when no rope reaches the dock.
inline Error Solve(const Quay& Q, int& Par, std::string& Route) {
    if (!ValidQuay(Q)) return Error::BadQuay;
    Search S;
    S.Q = &Q;
    S.Seen.assign(Cells, false);
    S.Seen[Q.Start] = true;
    S.Dfs(Q.Start, Q.Grip[Q.Start]);
    if (S.Capped) return Error::Capped;
    Par = S.Best;
    Route = S.Best >= 0 ? S.BestRoute : std::string();
    return Error::None;
}

// greedy(): unvisited neighbour with the most grip (ties N, S, E, W); 0 if stranded.
inline int Greedy(const Quay& Q) {
    if (!ValidQuay(Q)) return 0;
    std::vector<bool> Seen(Cells, false);
    int Cell = Q.Start, Score = Q.Grip[Q.Start];
    Seen[Cell] = true;
    while (Cell != Q.Dock) {
        int Pick = -1;
        for (int D = 0; D < 4; ++D) {
            const int N = Step(Cell, D);
            if (N < 0 || !Q.Grip[N] || Seen[N]) continue;
            if (Pick < 0 || Q.Grip[N] > Q.Grip[Pick]) Pick = N;
        }
        if (Pick < 0) return 0;
        Cell = Pick;
        Seen[Cell] = true;
        Score += Q.Grip[Cell];
    }
    return Score;
}

struct Result {
    Error Err = Error::None;
    int Grip = 0;
    bool OnDock = false;
    Verdict V = Verdict::Loose;
};

inline Result Play(const Quay& Q, int Par, const std::string& Route) {
    Result R;
    if (!ValidQuay(Q)) { R.Err = Error::BadQuay; return R; }
    std::vector<bool> Seen(Cells, false);
    int Cell = Q.Start;
    Seen[Cell] = true;
    R.Grip = Q.Grip[Cell];
    for (char Ch : Route) {
        const int D = DirOf(Ch);
        if (D < 0) { R.Err = Error::Letter; return R; }
        if (Cell == Q.Dock) { R.Err = Error::Dock; return R; }
        const int N = Step(Cell, D);
        if (N < 0 || !Q.Grip[N]) { R.Err = Error::Off; return R; }
        if (Seen[N]) { R.Err = Error::Cross; return R; }
        Cell = N;
        Seen[N] = true;
        R.Grip += Q.Grip[N];
    }
    R.OnDock = Cell == Q.Dock;
    R.V = !R.OnDock ? Verdict::Loose : (R.Grip >= Par ? Verdict::Taut : Verdict::Slack);
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Taut ? "taut" : V == Verdict::Slack ? "slack" : "loose";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Letter: return "letter";
        case Error::Dock: return "dock";
        case Error::Off: return "off";
        case Error::Cross: return "cross";
        case Error::Capped: return "capped";
        case Error::BadQuay: return "quay";
        default: return "none";
    }
}

}  // namespace RopeRun
}  // namespace DaedalusDiskSaver
