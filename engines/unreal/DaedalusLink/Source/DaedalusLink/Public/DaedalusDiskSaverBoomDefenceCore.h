// SPDX-License-Identifier: MIT
// G562 Boom Defence core, header-only C++17 port of tools/streaming/boom_defence.py (G574 batch 2).
// Takes an already-charted channel (path cells, lettered post sites and skiff hulls, as laid out by
// the Python tool) and ports the tick simulator, the exhaustive par over every pair of sites (same
// combination order and tie rule), the most-reach greedy habit, post parsing and the verdict.
// Engine-free: no Unreal includes, no exceptions, no RTTI; errors come back as codes.
#pragma once

#include <algorithm>
#include <cstdlib>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace BoomDefence {

constexpr int Rows = 7, Cols = 9;
constexpr int MaxSkiffs = 6, MaxSites = 12, Posts = 2, Gap = 2;
constexpr int MaxPath = Rows * Cols;
constexpr int MaxHull = 1000;
enum class Error { None, BadChart, Site, Twice, Many };
enum class Verdict { Watertight, Leaky, Overrun };
using Cell = std::pair<int, int>;

struct ChartData {
    std::vector<Cell> Path, Sites;
    std::vector<int> Hulls;
};

inline bool ValidChart(const ChartData& C) {
    if (C.Path.empty() || C.Path.size() > static_cast<std::size_t>(MaxPath)) return false;
    if (C.Sites.size() > static_cast<std::size_t>(MaxSites)) return false;
    if (C.Hulls.empty() || C.Hulls.size() > static_cast<std::size_t>(MaxSkiffs)) return false;
    for (int H : C.Hulls)
        if (H < 1 || H > MaxHull) return false;
    for (const auto* V : {&C.Path, &C.Sites})
        for (const Cell& P : *V)
            if (P.first < 0 || P.first >= Rows || P.second < 0 || P.second >= Cols) return false;
    return true;
}

inline bool Reach(const Cell& Site, const Cell& P) {
    return std::max(std::abs(Site.first - P.first), std::abs(Site.second - P.second)) == 1;
}

// simulate(): number through; Fates gets 't' (through) or 's' (sunk) per skiff.
inline int Simulate(const ChartData& C, const std::vector<Cell>& PostCells, std::string& Fates) {
    const int N = static_cast<int>(C.Hulls.size());
    const int Len = static_cast<int>(C.Path.size());
    std::vector<int> Hp(C.Hulls), At(N, -1);
    Fates.assign(N, '?');
    int Open = N;
    // every skiff enters by tick Gap*(N-1) and leaves Len ticks later at the latest
    const int MaxTicks = Gap * N + Len + 2;
    for (int Tick = 0; Open > 0 && Tick <= MaxTicks; ++Tick) {
        for (int i = 0; i < N; ++i)
            if (Fates[i] == '?' && At[i] >= 0 && ++At[i] >= Len) {
                Fates[i] = 't';
                --Open;
            }
        if (Tick % Gap == 0 && Tick / Gap < N) At[Tick / Gap] = 0;
        for (const Cell& P : PostCells) {
            int J = -1;
            for (int i = 0; i < N; ++i) {
                if (Fates[i] != '?' || At[i] < 0 || !Reach(P, C.Path[At[i]])) continue;
                if (J < 0 || At[i] > At[J]) J = i;  // furthest along; ties keep the lower index
            }
            if (J >= 0 && --Hp[J] <= 0) {
                Fates[J] = 's';
                --Open;
            }
        }
    }
    int Through = 0;
    for (char F : Fates) Through += F == 't';
    return Through;
}

inline std::vector<Cell> CellsOf(const ChartData& C, const std::vector<int>& Idx) {
    std::vector<Cell> Out;
    for (int I : Idx) Out.push_back(C.Sites[I]);
    return Out;
}

// best(): every combination of min(2, sites) sites in itertools order; strict improvement only.
inline int Best(const ChartData& C, std::vector<int>& Combo) {
    const int S = static_cast<int>(C.Sites.size());
    const int K = std::min(Posts, S);
    std::string F;
    int Top = -1;
    Combo.clear();
    if (K == 0) return Simulate(C, {}, F);
    if (K == 1) {
        for (int a = 0; a < S; ++a) {
            const int N = Simulate(C, CellsOf(C, {a}), F);
            if (Top < 0 || N < Top) { Top = N; Combo = {a}; }
        }
        return Top;
    }
    for (int a = 0; a < S; ++a)
        for (int b = a + 1; b < S; ++b) {
            const int N = Simulate(C, CellsOf(C, {a, b}), F);
            if (Top < 0 || N < Top) { Top = N; Combo = {a, b}; }
        }
    return Top;
}

// greedy(): the sites that reach the most channel cells (ties to the lower letter).
inline int Greedy(const ChartData& C, std::vector<int>& Pick) {
    const int S = static_cast<int>(C.Sites.size());
    const int K = std::min(Posts, S);
    std::vector<int> Cover(S, 0), Order(S);
    for (int i = 0; i < S; ++i) {
        Order[i] = i;
        for (const Cell& P : C.Path) Cover[i] += Reach(C.Sites[i], P);
    }
    std::stable_sort(Order.begin(), Order.end(), [&Cover](int x, int y) { return Cover[x] > Cover[y]; });
    Pick.assign(Order.begin(), Order.begin() + K);
    std::sort(Pick.begin(), Pick.end());
    std::string F;
    return Simulate(C, CellsOf(C, Pick), F);
}

// The --posts text: comma-separated letters, case-insensitive, blanks skipped.
inline Error ParsePosts(const ChartData& C, const std::string& Text, std::vector<int>& Chosen) {
    Chosen.clear();
    const int S = static_cast<int>(C.Sites.size());
    std::size_t From = 0;
    while (From <= Text.size()) {
        std::size_t To = Text.find(',', From);
        if (To == std::string::npos) To = Text.size();
        std::string T = Text.substr(From, To - From);
        From = To + 1;
        while (!T.empty() && (T.back() == ' ' || T.back() == '\t')) T.pop_back();
        while (!T.empty() && (T.front() == ' ' || T.front() == '\t')) T.erase(T.begin());
        if (T.empty()) continue;
        if (T.size() != 1) return Error::Site;
        char Ch = T[0];
        if (Ch >= 'a' && Ch <= 'z') Ch = static_cast<char>(Ch - 'a' + 'A');
        const int I = Ch - 'A';
        if (I < 0 || I >= S) return Error::Site;
        if (std::find(Chosen.begin(), Chosen.end(), I) != Chosen.end()) return Error::Twice;
        Chosen.push_back(I);
    }
    if (static_cast<int>(Chosen.size()) > std::min(Posts, S)) return Error::Many;
    return Error::None;
}

struct Result {
    Error Err = Error::None;
    int Through = 0;
    std::string Fates;
    Verdict V = Verdict::Overrun;
};

inline Result Play(const ChartData& C, int Par, const std::string& PostsText) {
    Result R;
    if (!ValidChart(C)) { R.Err = Error::BadChart; return R; }
    std::vector<int> Chosen;
    R.Err = ParsePosts(C, PostsText, Chosen);
    if (R.Err != Error::None) return R;
    R.Through = Simulate(C, CellsOf(C, Chosen), R.Fates);
    const int N = static_cast<int>(C.Hulls.size());
    R.V = R.Through <= Par ? Verdict::Watertight : (R.Through < N ? Verdict::Leaky : Verdict::Overrun);
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Watertight ? "watertight" : V == Verdict::Leaky ? "leaky" : "overrun";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Site: return "site";
        case Error::Twice: return "twice";
        case Error::Many: return "many";
        case Error::BadChart: return "chart";
        default: return "none";
    }
}

}  // namespace BoomDefence
}  // namespace DaedalusDiskSaver
