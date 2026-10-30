// SPDX-License-Identifier: MIT
// G565 Belfry Changes core, header-only C++17 port of tools/streaming/belfry_changes.py (G575 batch 3).
// Takes an already-jumbled ring (row of bells, island bell count, tenor, as laid out by the Python
// tool) and ports the change generator (same sorted order), the exact BFS par over (row, bells led,
// tenor resting) and the single-swap par, change parsing and validation, and the verdict.
// Engine-free: no Unreal includes, no exceptions, no RTTI. The search stops at MaxStates.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace DaedalusDiskSaver {
namespace BelfryChanges {

constexpr int MaxBells = 7;  // Python rings 5..6; 7 keeps the packed key in 32 bits
constexpr std::size_t MaxStates = 4000000;
enum class Error { None, BadRing, Capped, NoWay, Format, Range, Overlap, Rest };
enum class Verdict { Rung, Clattered, Unfinished };
using Row = std::vector<int>;
using Change = std::vector<int>;  // 0-based pair starts

struct Ring {
    Row Start;
    int Islands = 0;  // bells 1..Islands are island bells
    int Tenor = 0;
};

inline bool ValidRing(const Ring& R) {
    const int N = static_cast<int>(R.Start.size());
    if (N < 2 || N > MaxBells || R.Islands < 1 || R.Islands > N || R.Tenor < 1 || R.Tenor > N) return false;
    std::vector<bool> Seen(N + 1, false);
    for (int B : R.Start) {
        if (B < 1 || B > N || Seen[B]) return false;
        Seen[B] = true;
    }
    return true;
}

// all_changes(): every non-empty set of non-overlapping pair starts, sorted as Python sorts tuples.
inline std::vector<Change> AllChanges(int N, bool Single) {
    std::vector<Change> Out;
    Change Cur;
    struct Rec {
        static void Go(int I, int N, bool Single, Change& Cur, std::vector<Change>& Out) {
            if (I >= N - 1) {
                if (!Cur.empty()) Out.push_back(Cur);
                return;
            }
            Go(I + 1, N, Single, Cur, Out);
            if (!Single || Cur.empty()) {
                Cur.push_back(I);
                Go(I + 2, N, Single, Cur, Out);
                Cur.pop_back();
            }
        }
    };
    Rec::Go(0, N, Single, Cur, Out);
    std::sort(Out.begin(), Out.end());
    return Out;
}

inline void Apply(Row& R, const Change& C) {
    for (int P : C) std::swap(R[P], R[P + 1]);
}
inline bool TenorMoves(const Row& R, int Tenor, const Change& C) {
    const int Ti = static_cast<int>(std::find(R.begin(), R.end(), Tenor) - R.begin());
    for (int P : C)
        if (P == Ti || P + 1 == Ti) return true;
    return false;
}
inline unsigned LedBit(const Ring& G, int Bell) { return Bell <= G.Islands ? 1u << (Bell - 1) : 0u; }

inline std::uint32_t Pack(const Row& R, unsigned Led, bool Rest) {
    std::uint32_t K = 0;
    for (int B : R) K = (K << 3) | static_cast<std::uint32_t>(B - 1);
    return (K << 8) | (Led << 1) | (Rest ? 1u : 0u);
}

inline Error Solve(const Ring& G, bool Single, int& Par, std::vector<Change>& Plan) {
    if (!ValidRing(G)) return Error::BadRing;
    const int N = static_cast<int>(G.Start.size());
    const std::vector<Change> Changes = AllChanges(N, Single);
    const unsigned Full = (1u << G.Islands) - 1u;
    struct Node { Row R; unsigned Led; bool Rest; std::int64_t From; int Via; };
    std::vector<Node> Nodes;
    std::unordered_map<std::uint32_t, std::size_t> Index;
    Nodes.push_back({G.Start, LedBit(G, G.Start[0]), false, -1, -1});
    Index[Pack(G.Start, Nodes[0].Led, false)] = 0;
    for (std::size_t Head = 0; Head < Nodes.size(); ++Head) {
        const Node Cur = Nodes[Head];
        bool Rounds = true;
        for (int i = 0; i < N; ++i) Rounds = Rounds && Cur.R[i] == i + 1;
        if (Rounds && Cur.Led == Full) {
            Plan.clear();
            for (std::int64_t I = static_cast<std::int64_t>(Head); Nodes[I].From >= 0; I = Nodes[I].From)
                Plan.insert(Plan.begin(), Changes[Nodes[I].Via]);
            Par = static_cast<int>(Plan.size());
            return Error::None;
        }
        for (std::size_t c = 0; c < Changes.size(); ++c) {
            const bool Moves = TenorMoves(Cur.R, G.Tenor, Changes[c]);
            if (Cur.Rest && Moves) continue;
            Row Nr = Cur.R;
            Apply(Nr, Changes[c]);
            const unsigned Nl = Cur.Led | LedBit(G, Nr[0]);
            const std::uint32_t K = Pack(Nr, Nl, Moves);
            if (Index.find(K) != Index.end()) continue;
            if (Nodes.size() >= MaxStates) return Error::Capped;
            Index[K] = Nodes.size();
            Nodes.push_back({Nr, Nl, Moves, static_cast<std::int64_t>(Head), static_cast<int>(c)});
        }
    }
    return Error::NoWay;
}

// parse_changes(): "1+3,2" -> 0-based changes; blanks skipped; all parsed before any is rung.
inline Error ParseChanges(int N, const std::string& Text, std::vector<Change>& Out) {
    Out.clear();
    std::size_t From = 0;
    while (From <= Text.size()) {
        std::size_t To = Text.find(',', From);
        if (To == std::string::npos) To = Text.size();
        std::string Tok = Text.substr(From, To - From);
        From = To + 1;
        while (!Tok.empty() && Tok.back() == ' ') Tok.pop_back();
        while (!Tok.empty() && Tok.front() == ' ') Tok.erase(Tok.begin());
        if (Tok.empty()) continue;
        std::vector<long long> Places;
        std::size_t P0 = 0;
        for (;;) {
            std::size_t P1 = Tok.find('+', P0);
            const bool Last = P1 == std::string::npos;
            if (Last) P1 = Tok.size();
            std::string Part = Tok.substr(P0, P1 - P0);
            while (!Part.empty() && Part.back() == ' ') Part.pop_back();
            while (!Part.empty() && Part.front() == ' ') Part.erase(Part.begin());
            bool Neg = false;
            if (!Part.empty() && Part[0] == '-') { Neg = true; Part.erase(Part.begin()); }
            if (Part.empty()) return Error::Format;
            long long V = 0;
            for (char C : Part) {
                if (C < '0' || C > '9') return Error::Format;
                V = std::min(1000000000LL, V * 10 + (C - '0'));
            }
            Places.push_back(Neg ? -V : V);
            if (Last) break;
            P0 = P1 + 1;
        }
        std::sort(Places.begin(), Places.end());
        for (long long P : Places)
            if (P < 1 || P > N - 1) return Error::Range;
        for (std::size_t i = 1; i < Places.size(); ++i)
            if (Places[i] - Places[i - 1] < 2) return Error::Overlap;
        Change C;
        for (long long P : Places) C.push_back(static_cast<int>(P - 1));
        Out.push_back(C);
    }
    return Error::None;
}

struct Result {
    Error Err = Error::None;
    int Count = 0;
    Row Final;
    std::vector<int> Led;
    Verdict V = Verdict::Unfinished;
};

inline Result Play(const Ring& G, int Par, const std::string& Text) {
    Result R;
    if (!ValidRing(G)) { R.Err = Error::BadRing; return R; }
    std::vector<Change> Changes;
    R.Err = ParseChanges(static_cast<int>(G.Start.size()), Text, Changes);
    if (R.Err != Error::None) return R;
    Row Cur = G.Start;
    unsigned Led = LedBit(G, Cur[0]);
    bool Rest = false;
    for (const Change& C : Changes) {
        const bool Moves = TenorMoves(Cur, G.Tenor, C);
        if (Rest && Moves) { R.Err = Error::Rest; return R; }
        Apply(Cur, C);
        Rest = Moves;
        Led |= LedBit(G, Cur[0]);
    }
    R.Count = static_cast<int>(Changes.size());
    R.Final = Cur;
    for (int B = 1; B <= G.Islands; ++B)
        if (Led >> (B - 1) & 1u) R.Led.push_back(B);
    bool Rounds = true;
    for (std::size_t i = 0; i < Cur.size(); ++i) Rounds = Rounds && Cur[i] == static_cast<int>(i) + 1;
    const bool Done = Rounds && Led == (1u << G.Islands) - 1u;
    R.V = Done ? (R.Count <= Par ? Verdict::Rung : Verdict::Clattered) : Verdict::Unfinished;
    return R;
}

inline std::string ChangeText(const std::vector<Change>& V) {
    std::string S;
    for (std::size_t i = 0; i < V.size(); ++i) {
        if (i) S += ',';
        for (std::size_t j = 0; j < V[i].size(); ++j) S += (j ? "+" : "") + std::to_string(V[i][j] + 1);
    }
    return S.empty() ? "-" : S;
}
inline const char* VerdictName(Verdict V) {
    return V == Verdict::Rung ? "rung" : V == Verdict::Clattered ? "clattered" : "unfinished";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Format: return "format";
        case Error::Range: return "range";
        case Error::Overlap: return "overlap";
        case Error::Rest: return "rest";
        case Error::NoWay: return "noway";
        case Error::Capped: return "capped";
        case Error::BadRing: return "ring";
        default: return "none";
    }
}

}  // namespace BelfryChanges
}  // namespace DaedalusDiskSaver
