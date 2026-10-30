// SPDX-License-Identifier: MIT
// G557 Twin Pilots core, header-only C++17 port of tools/streaming/twin_pilots.py (G573).
// Takes an already-charted harbour (node count, channels; node 0 is the harbour, as laid out by the
// Python tool) and ports the exact two-boat BFS par, the one-boat Held-Karp bells, route grading and
// the verdict. Engine-free: no Unreal includes, no exceptions, no RTTI; errors come back as codes.
#pragma once

#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace TwinPilots {

constexpr int MaxNodes = 12;  // Python caps a chart at 9 (harbour + 8 calls); 12 bounds the BFS table
enum class Error { None, BadChart, Disconnected, Berth, Channel };
enum class Verdict { InStep, Late, Adrift };
using Edge = std::pair<int, int>;
using Route = std::vector<int>;  // nodes after the start, one per bell

struct Chart {
    int N = 0;
    std::vector<std::vector<int>> Adj;  // sorted, includes the node itself (holding)
};

inline bool MakeChart(int N, const std::vector<Edge>& Edges, Chart& Out) {
    if (N < 1 || N > MaxNodes) return false;
    Out.N = N;
    Out.Adj.assign(N, {});
    for (int i = 0; i < N; ++i) Out.Adj[i].push_back(i);
    for (const Edge& E : Edges) {
        if (E.first < 0 || E.second < 0 || E.first >= N || E.second >= N || E.first == E.second) return false;
        Out.Adj[E.first].push_back(E.second);
        Out.Adj[E.second].push_back(E.first);
    }
    for (auto& A : Out.Adj) {
        std::sort(A.begin(), A.end());
        A.erase(std::unique(A.begin(), A.end()), A.end());
    }
    return true;
}

// solve(): BFS over (a, b, calls mask) in the same expansion order, so the routes match too.
inline Error Solve(const Chart& C, int& Par, Route& Ra, Route& Rb) {
    const int N = C.N;
    if (N < 1 || N > MaxNodes) return Error::BadChart;
    const std::uint32_t Full = (1u << N) - 2u;
    const std::size_t Size = static_cast<std::size_t>(N) * N << N;
    const auto Key = [N](int A, int B, std::uint32_t M) {
        return ((static_cast<std::size_t>(A) * N + B) << N) | M;
    };
    std::vector<std::int64_t> Prev(Size, -2);  // -2 unseen, -1 start
    std::vector<std::size_t> Queue;
    Queue.reserve(Size);
    const std::size_t Start = Key(0, 0, 0);
    Prev[Start] = -1;
    Queue.push_back(Start);
    for (std::size_t Head = 0; Head < Queue.size(); ++Head) {
        std::size_t S = Queue[Head];
        const std::uint32_t M = static_cast<std::uint32_t>(S & ((1u << N) - 1));
        const int Ab = static_cast<int>(S >> N);
        const int A = Ab / N, B = Ab % N;
        if (A == 0 && B == 0 && M == Full) {
            Ra.clear();
            Rb.clear();
            while (Prev[S] != -1) {
                const int X = static_cast<int>(S >> N);
                Ra.push_back(X / N);
                Rb.push_back(X % N);
                S = static_cast<std::size_t>(Prev[S]);
            }
            std::reverse(Ra.begin(), Ra.end());
            std::reverse(Rb.begin(), Rb.end());
            Par = static_cast<int>(Ra.size());
            return Error::None;
        }
        for (int X : C.Adj[A])
            for (int Y : C.Adj[B]) {
                const std::size_t T = Key(X, Y, (M | (1u << X) | (1u << Y)) & Full);
                if (Prev[T] == -2) {
                    Prev[T] = static_cast<std::int64_t>(Queue[Head]);
                    Queue.push_back(T);
                }
            }
    }
    return Error::Disconnected;
}

// solo_bells(): one boat makes every call (Held-Karp over Floyd-Warshall distances).
inline int SoloBells(const Chart& C) {
    const int N = C.N;
    if (N <= 1) return 0;
    std::vector<std::vector<int>> D(N, std::vector<int>(N, N * 9));
    for (int i = 0; i < N; ++i)
        for (int j : C.Adj[i]) D[i][j] = i == j ? 0 : 1;
    for (int k = 0; k < N; ++k)
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                if (D[i][k] + D[k][j] < D[i][j]) D[i][j] = D[i][k] + D[k][j];
    const int K = N - 1;
    const int Inf = 1 << 30;
    std::vector<std::vector<int>> Best(static_cast<std::size_t>(1) << K, std::vector<int>(K, Inf));
    for (int i = 0; i < K; ++i) Best[std::size_t{1} << i][i] = D[0][i + 1];
    for (std::size_t M = 1; M < (std::size_t{1} << K); ++M)
        for (int i = 0; i < K; ++i) {
            if (!((M >> i) & 1) || Best[M][i] == Inf) continue;
            for (int j = 0; j < K; ++j) {
                if ((M >> j) & 1) continue;
                const int V = Best[M][i] + D[i + 1][j + 1];
                if (V < Best[M | (std::size_t{1} << j)][j]) Best[M | (std::size_t{1} << j)][j] = V;
            }
        }
    int Out = Inf;
    for (int i = 0; i < K; ++i) Out = std::min(Out, Best[(std::size_t{1} << K) - 1][i] + D[i + 1][0]);
    return Out;
}

struct Grade {
    Error Err = Error::None;
    int Bells = 0;
    int Missed = 0;
    bool Home = true;
    Verdict V = Verdict::Adrift;
};

inline Grade Play(const Chart& C, int Par, const Route& A, const Route& B) {
    Grade G;
    const Route* Rs[2] = {&A, &B};
    for (const Route* R : Rs)
        for (int X : *R)
            if (X < 0 || X >= C.N) { G.Err = Error::Berth; return G; }
    std::vector<bool> Seen(C.N, false);
    Seen[0] = true;
    for (const Route* R : Rs) {
        int At = 0;
        for (int X : *R) {
            if (!std::binary_search(C.Adj[At].begin(), C.Adj[At].end(), X)) { G.Err = Error::Channel; return G; }
            At = X;
            Seen[X] = true;
        }
    }
    G.Bells = static_cast<int>(std::max(A.size(), B.size()));
    for (int i = 1; i < C.N; ++i) G.Missed += Seen[i] ? 0 : 1;
    G.Home = (A.empty() || A.back() == 0) && (B.empty() || B.back() == 0);
    G.V = (G.Missed || !G.Home) ? Verdict::Adrift : (G.Bells <= Par ? Verdict::InStep : Verdict::Late);
    return G;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::InStep ? "in_step" : V == Verdict::Late ? "late" : "adrift";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Berth: return "berth";
        case Error::Channel: return "channel";
        case Error::Disconnected: return "disconnected";
        case Error::BadChart: return "chart";
        default: return "none";
    }
}

}  // namespace TwinPilots
}  // namespace DaedalusDiskSaver
