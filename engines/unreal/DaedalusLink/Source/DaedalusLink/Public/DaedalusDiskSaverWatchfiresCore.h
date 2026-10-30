// SPDX-License-Identifier: MIT
// G555 Watchfires core, header-only C++17 port of tools/streaming/watchfires.py (G576 batch 4).
// Takes the ferry chart as the Python tool laid it out (sorted island labels and sorted (i, j)
// routes with i < j; the seeded routes stay in Python) and ports the closed neighbourhoods, the
// exact branch-and-bound par (same island order, so the optimal set matches), the "light the most
// new islands" greedy, fire validation and the verdict. Engine-free: no Unreal includes, no
// exceptions, no RTTI. Islands are bits of a uint64 (Python caps the chart at 40); the search
// stops after MaxNodes calls.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace Watchfires {

constexpr int MaxIslands = 40;  // same cap as Python's MAX_ISLANDS
constexpr std::uint64_t MaxNodes = 50000000;
enum class Error { None, BadChart, Capped, Unknown };
enum class Verdict { Blazing, Smoky, Dark };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadChart: return "chart";
        case Error::Capped: return "capped";
        case Error::Unknown: return "unknown";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Blazing: return "blazing";
        case Verdict::Smoky: return "smoky";
        case Verdict::Dark: return "dark";
    }
    return "?";
}

struct Chart {
    std::vector<std::string> Labels;
    std::vector<std::pair<int, int>> Edges;
};

inline int Bits(std::uint64_t X) {
    int C = 0;
    while (X) {
        X &= X - 1;
        ++C;
    }
    return C;
}
inline std::uint64_t Bit(int I) { return std::uint64_t{1} << I; }
inline std::uint64_t Full(int N) { return N >= 64 ? ~std::uint64_t{0} : Bit(N) - 1; }

inline bool ValidChart(const Chart& C) {
    const int N = static_cast<int>(C.Labels.size());
    if (N < 1 || N > MaxIslands) return false;
    for (int I = 0; I < N; ++I)
        for (int J = I + 1; J < N; ++J)
            if (C.Labels[I] == C.Labels[J]) return false;
    for (std::size_t K = 0; K < C.Edges.size(); ++K) {
        const auto& E = C.Edges[K];
        if (E.first < 0 || E.first >= E.second || E.second >= N) return false;
        for (std::size_t L = 0; L < K; ++L)
            if (C.Edges[L] == E) return false;
    }
    return true;
}

inline std::vector<std::uint64_t> Closed(const Chart& C) {
    const int N = static_cast<int>(C.Labels.size());
    std::vector<std::uint64_t> Nb(N);
    for (int I = 0; I < N; ++I) Nb[I] = Bit(I);
    for (const auto& E : C.Edges) {
        Nb[E.first] |= Bit(E.second);
        Nb[E.second] |= Bit(E.first);
    }
    return Nb;
}

namespace Detail {
struct Search {
    std::vector<std::uint64_t> Nb;
    std::vector<int> Order;
    std::uint64_t FullMask = 0;
    int N = 0, BestK = 0;
    std::vector<int> Best, Chosen;
    std::uint64_t Nodes = 0;
    bool Capped = false;

    void Rec(std::uint64_t Lit) {
        if (Capped || ++Nodes > MaxNodes) {
            Capped = true;
            return;
        }
        if (Lit == FullMask) {
            if (static_cast<int>(Chosen.size()) < BestK) {
                BestK = static_cast<int>(Chosen.size());
                Best = Chosen;
                std::sort(Best.begin(), Best.end());
            }
            return;
        }
        if (static_cast<int>(Chosen.size()) + 1 >= BestK) return;
        int U = 0;
        while (Lit >> U & 1) ++U;
        for (int V : Order) {
            if (!(Nb[U] >> V & 1)) continue;
            Chosen.push_back(V);
            Rec(Lit | Nb[V]);
            Chosen.pop_back();
        }
    }
};
}  // namespace Detail

// par(): minimum number of fires and the first optimal set found (sorted indexes).
inline Error Par(const Chart& C, int& K, std::vector<int>& Best) {
    if (!ValidChart(C)) return Error::BadChart;
    Detail::Search S;
    S.N = static_cast<int>(C.Labels.size());
    S.Nb = Closed(C);
    S.FullMask = Full(S.N);
    S.BestK = S.N + 1;
    for (int I = 0; I < S.N; ++I) S.Order.push_back(I);
    std::stable_sort(S.Order.begin(), S.Order.end(), [&](int A, int B) { return Bits(S.Nb[A]) > Bits(S.Nb[B]); });
    S.Rec(0);
    if (S.Capped) return Error::Capped;
    K = S.BestK;
    Best = S.Best;
    return Error::None;
}

// Empty for an invalid chart.
inline std::vector<int> Greedy(const Chart& C) {
    if (!ValidChart(C)) return {};
    const int N = static_cast<int>(C.Labels.size());
    const std::vector<std::uint64_t> Nb = Closed(C);
    std::uint64_t Lit = 0;
    std::vector<int> Fires;
    while (Lit != Full(N)) {
        int Pick = 0, Gain = -1;
        for (int V = 0; V < N; ++V) {
            const int G = Bits(Nb[V] & ~Lit);
            if (G > Gain) {
                Gain = G;
                Pick = V;
            }
        }
        Fires.push_back(Pick);
        Lit |= Nb[Pick];
    }
    std::sort(Fires.begin(), Fires.end());
    return Fires;
}

struct Result {
    Error Err = Error::None;
    std::vector<int> Fires, Unlit;
    Verdict V = Verdict::Dark;
};

// game(fires=...) or game(auto=True): fires are island labels; repeats count once.
inline Result Play(const Chart& C, int Par, const std::vector<int>& Best, bool Auto, const std::vector<std::string>& Fires) {
    Result R;
    if (!ValidChart(C)) {
        R.Err = Error::BadChart;
        return R;
    }
    const int N = static_cast<int>(C.Labels.size());
    std::uint64_t Chosen = 0;
    if (Auto) {
        for (int V : Best) Chosen |= Bit(V);
    } else {
        for (const std::string& F : Fires) {
            int Hit = -1;
            for (int I = 0; I < N && Hit < 0; ++I)
                if (C.Labels[I] == F) Hit = I;
            if (Hit < 0) {
                R.Err = Error::Unknown;
                return R;
            }
            Chosen |= Bit(Hit);
        }
    }
    const std::vector<std::uint64_t> Nb = Closed(C);
    std::uint64_t Lit = 0;
    for (int I = 0; I < N; ++I)
        if (Chosen >> I & 1) {
            R.Fires.push_back(I);
            Lit |= Nb[I];
        }
    for (int I = 0; I < N; ++I)
        if (!(Lit >> I & 1)) R.Unlit.push_back(I);
    R.V = !R.Unlit.empty() ? Verdict::Dark : static_cast<int>(R.Fires.size()) <= Par ? Verdict::Blazing : Verdict::Smoky;
    return R;
}

}  // namespace Watchfires
}  // namespace DaedalusDiskSaver
