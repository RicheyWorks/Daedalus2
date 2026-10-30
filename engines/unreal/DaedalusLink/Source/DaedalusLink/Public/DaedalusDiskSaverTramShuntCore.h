// SPDX-License-Identifier: MIT
// G566 Tram Shunt core, header-only C++17 port of tools/streaming/tram_shunt.py (G575 batch 3).
// Takes an already-jumbled inbound train (wagon numbers front first, as laid out by the Python
// tool) and ports the move rule, the exact BFS par (same move order, so the plan matches), the
// yardman's-habit greedy, move parsing and validation, and the verdict. Engine-free: no Unreal
// includes, no exceptions, no RTTI. The search stops at MaxStates.
#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace DaedalusDiskSaver {
namespace TramShunt {

constexpr int MaxWagons = 8;  // Python marshals 6
constexpr std::size_t MaxStates = 4000000;
constexpr int GreedyCap = 200;
enum class Error { None, BadTrain, Capped, Unsolvable, Format, Out, Impossible };
enum class Verdict { Smart, Slow, Jammed };
enum Track { In = 0, A = 1, B = 2, OutT = 3 };

struct State {
    int Taken = 0;  // wagons gone from the inbound line
    std::vector<int> SA, SB;  // bottom first
    int Next = 1;
};

struct Move { int From, To; };
inline const char* MoveName(int I) {
    static const char* N[7] = {"inout", "Aout", "Bout", "inA", "inB", "AB", "BA"};
    return N[I];
}
inline Move MoveAt(int I) {
    static const Move M[7] = {{In, OutT}, {A, OutT}, {B, OutT}, {In, A}, {In, B}, {A, B}, {B, A}};
    return M[I];
}

inline bool ValidTrain(const std::vector<int>& Order) {
    const int N = static_cast<int>(Order.size());
    if (N < 1 || N > MaxWagons) return false;
    std::vector<bool> Seen(N + 1, false);
    for (int W : Order) {
        if (W < 1 || W > N || Seen[W]) return false;
        Seen[W] = true;
    }
    return true;
}

// MOVE_RE ^(in|A|B)(A|B|out)$ ; false if the text is not FROM+TO.
inline bool ParseMove(const std::string& T, Move& M) {
    std::size_t K = 0;
    if (T.compare(0, 2, "in") == 0) { M.From = In; K = 2; }
    else if (!T.empty() && T[0] == 'A') { M.From = A; K = 1; }
    else if (!T.empty() && T[0] == 'B') { M.From = B; K = 1; }
    else return false;
    const std::string Rest = T.substr(K);
    if (Rest == "A") M.To = A;
    else if (Rest == "B") M.To = B;
    else if (Rest == "out") M.To = OutT;
    else return false;
    return true;
}

// step(): false when the move is not possible.
inline bool StepState(const std::vector<int>& Order, State& S, const Move& M) {
    if (M.From == M.To) return false;
    int W = 0;
    if (M.From == In) {
        if (S.Taken >= static_cast<int>(Order.size())) return false;
        W = Order[S.Taken];
        if (M.To == OutT && W != S.Next) return false;
        ++S.Taken;
    } else {
        std::vector<int>& Src = M.From == A ? S.SA : S.SB;
        if (Src.empty()) return false;
        W = Src.back();
        if (M.To == OutT && W != S.Next) return false;
        Src.pop_back();
    }
    if (M.To == OutT) ++S.Next;
    else (M.To == A ? S.SA : S.SB).push_back(W);
    return true;
}

inline std::string Key(const State& S) {
    std::string K;
    K += static_cast<char>(S.Taken);
    K += static_cast<char>(S.Next);
    for (int W : S.SA) K += static_cast<char>(W);
    K += '|';
    for (int W : S.SB) K += static_cast<char>(W);
    return K;
}

inline Error Solve(const std::vector<int>& Order, int& Par, std::vector<int>& Plan) {
    if (!ValidTrain(Order)) return Error::BadTrain;
    const int N = static_cast<int>(Order.size());
    struct Node { State S; std::int64_t From; int Via; };
    std::vector<Node> Nodes{{State{}, -1, -1}};
    std::unordered_map<std::string, std::size_t> Index{{Key(Nodes[0].S), 0}};
    for (std::size_t Head = 0; Head < Nodes.size(); ++Head) {
        if (Nodes[Head].S.Next == N + 1) {
            Plan.clear();
            for (std::int64_t I = static_cast<std::int64_t>(Head); Nodes[I].From >= 0; I = Nodes[I].From)
                Plan.insert(Plan.begin(), Nodes[I].Via);
            Par = static_cast<int>(Plan.size());
            return Error::None;
        }
        for (int m = 0; m < 7; ++m) {
            State T = Nodes[Head].S;
            if (!StepState(Order, T, MoveAt(m))) continue;
            const std::string K = Key(T);
            if (Index.find(K) != Index.end()) continue;
            if (Nodes.size() >= MaxStates) return Error::Capped;
            Index[K] = Nodes.size();
            Nodes.push_back({T, static_cast<std::int64_t>(Head), m});
        }
    }
    return Error::Unsolvable;
}

// greedy(): the yardman's habit; -1 when it jams (or passes GreedyCap moves).
inline int Greedy(const std::vector<int>& Order) {
    if (!ValidTrain(Order)) return -1;
    const int N = static_cast<int>(Order.size());
    State S;
    int Count = 0;
    while (S.Next <= N) {
        bool Out = false;
        for (int m = 0; m < 3 && !Out; ++m)
            if (StepState(Order, S, MoveAt(m))) { ++Count; Out = true; }
        if (Out) continue;
        if (S.Taken >= N) return -1;
        const int W = Order[S.Taken];
        const int TopA = S.SA.empty() ? 0 : S.SA.back(), TopB = S.SB.empty() ? 0 : S.SB.back();
        const bool FitA = TopA > W, FitB = TopB > W;
        int To;
        if (FitA && FitB) To = TopA < TopB ? A : B;
        else if (FitA) To = A;
        else if (FitB) To = B;
        else if (S.SA.empty()) To = A;
        else if (S.SB.empty()) To = B;
        else To = A;
        StepState(Order, S, Move{In, To});
        if (++Count > GreedyCap) return -1;
    }
    return Count;
}

struct Result {
    Error Err = Error::None;
    int Count = 0, Out = 0;
    Verdict V = Verdict::Jammed;
};

// The --moves text: comma-separated FROM+TO, blanks skipped, checked one move at a time.
inline Result Play(const std::vector<int>& Order, int Par, const std::string& Text) {
    Result R;
    if (!ValidTrain(Order)) { R.Err = Error::BadTrain; return R; }
    const int N = static_cast<int>(Order.size());
    State S;
    std::size_t From = 0;
    while (From <= Text.size()) {
        std::size_t To = Text.find(',', From);
        if (To == std::string::npos) To = Text.size();
        std::string T = Text.substr(From, To - From);
        From = To + 1;
        while (!T.empty() && T.back() == ' ') T.pop_back();
        while (!T.empty() && T.front() == ' ') T.erase(T.begin());
        if (T.empty()) continue;
        Move M{};
        if (!ParseMove(T, M)) { R.Err = Error::Format; return R; }
        if (S.Next > N) { R.Err = Error::Out; return R; }
        if (!StepState(Order, S, M)) { R.Err = Error::Impossible; return R; }
        ++R.Count;
    }
    R.Out = S.Next - 1;
    R.V = S.Next > N ? (R.Count <= Par ? Verdict::Smart : Verdict::Slow) : Verdict::Jammed;
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Smart ? "smart" : V == Verdict::Slow ? "slow" : "jammed";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Format: return "format";
        case Error::Out: return "out";
        case Error::Impossible: return "impossible";
        case Error::Unsolvable: return "unsolvable";
        case Error::Capped: return "capped";
        case Error::BadTrain: return "train";
        default: return "none";
    }
}

}  // namespace TramShunt
}  // namespace DaedalusDiskSaver
