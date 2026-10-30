// SPDX-License-Identifier: MIT
// G563 Salvage Sale core, header-only C++17 port of tools/streaming/salvage_sale.py (G574 batch 2).
// Takes an already-valued sale (lot values and starting coin, as laid out by the Python tool) and
// ports the Broker's bid rule, the exact par search (same pass-first tie rule, so the bids match),
// the win-what-you-can greedy, bid parsing and validation, and the verdict. Engine-free: no Unreal
// includes, no exceptions, no RTTI; errors come back as codes. Values and coin are capped so no
// sum can overflow.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace SalvageSale {

constexpr int MaxLots = 8;        // Python sells 5..6
constexpr int MaxValue = 1000000;
constexpr int MaxCoin = 100000000;
constexpr int BidCap = 1000000000;  // larger typed bids saturate here (always more than any coin)
constexpr int Hunger = 3;
enum class Error { None, BadSale, Count, Coin };
enum class Verdict { Shrewd, Fair, Fleeced };

struct Sale {
    std::vector<int> Values;
    int Coin = 0;
};

inline bool ValidSale(const Sale& S) {
    if (S.Values.empty() || S.Values.size() > static_cast<std::size_t>(MaxLots)) return false;
    for (int V : S.Values)
        if (V < 0 || V > MaxValue) return false;
    return S.Coin >= 0 && S.Coin <= MaxCoin;
}

inline int BrokerBid(int Value, int Coin, int Lost) { return std::min(Coin, Value / 2 + Hunger * Lost); }

// best(i, mine, theirs, lost): pass first; bid Broker+1 only if it scores strictly more.
inline int BestFrom(const Sale& S, int I, int Mine, int Theirs, int Lost, std::vector<int>& Plan) {
    const int N = static_cast<int>(S.Values.size());
    if (I == N) {
        Plan.clear();
        return 0;
    }
    const int Rb = BrokerBid(S.Values[I], Theirs, Lost);
    std::vector<int> Pass;
    int Top = BestFrom(S, I + 1, Mine, Theirs - Rb, Lost, Pass);
    Plan.assign(1, 0);
    Plan.insert(Plan.end(), Pass.begin(), Pass.end());
    if (Rb + 1 <= Mine) {
        std::vector<int> Win;
        const int S2 = BestFrom(S, I + 1, Mine - Rb - 1, Theirs, Lost + 1, Win) + S.Values[I];
        if (S2 > Top) {
            Top = S2;
            Plan.assign(1, Rb + 1);
            Plan.insert(Plan.end(), Win.begin(), Win.end());
        }
    }
    return Top;
}

inline bool Solve(const Sale& S, int& Par, std::vector<int>& Plan) {
    if (!ValidSale(S)) return false;
    Par = BestFrom(S, 0, S.Coin, S.Coin, 0, Plan);
    return true;
}

inline int Greedy(const Sale& S) {
    int Mine = S.Coin, Theirs = S.Coin, Lost = 0, Score = 0;
    for (int V : S.Values) {
        const int Rb = BrokerBid(V, Theirs, Lost);
        if (Rb + 1 <= Mine) {
            Mine -= Rb + 1;
            Score += V;
            ++Lost;
        } else {
            Theirs -= Rb;
        }
    }
    return Score;
}

// The --bids text: exactly one comma-separated whole number per lot (spaces trimmed).
inline Error ParseBids(const Sale& S, const std::string& Text, std::vector<int>& Bids) {
    Bids.clear();
    std::size_t From = 0;
    for (;;) {
        std::size_t To = Text.find(',', From);
        const bool Last = To == std::string::npos;
        if (Last) To = Text.size();
        std::string T = Text.substr(From, To - From);
        while (!T.empty() && (T.back() == ' ' || T.back() == '\t')) T.pop_back();
        while (!T.empty() && (T.front() == ' ' || T.front() == '\t')) T.erase(T.begin());
        if (T.empty()) return Error::Count;
        long long V = 0;
        for (char C : T) {
            if (C < '0' || C > '9') return Error::Count;
            V = std::min<long long>(BidCap, V * 10 + (C - '0'));
        }
        Bids.push_back(static_cast<int>(V));
        if (Last) break;
        From = To + 1;
    }
    return Bids.size() == S.Values.size() ? Error::None : Error::Count;
}

struct Result {
    Error Err = Error::None;
    int Score = 0;
    std::string Winners;  // 'y' you, 'b' broker, per lot
    Verdict V = Verdict::Fleeced;
};

inline Result Play(const Sale& S, int Par, const std::string& BidsText) {
    Result R;
    if (!ValidSale(S)) { R.Err = Error::BadSale; return R; }
    std::vector<int> Bids;
    R.Err = ParseBids(S, BidsText, Bids);
    if (R.Err != Error::None) return R;
    int Mine = S.Coin, Theirs = S.Coin, Lost = 0;
    for (std::size_t i = 0; i < Bids.size(); ++i) {
        if (Bids[i] > Mine) { R.Err = Error::Coin; return R; }
        const int Rb = BrokerBid(S.Values[i], Theirs, Lost);
        if (Bids[i] > Rb) {
            Mine -= Bids[i];
            R.Score += S.Values[i];
            ++Lost;
            R.Winners += 'y';
        } else {
            Theirs -= Rb;
            R.Winners += 'b';
        }
    }
    R.V = R.Score >= Par ? Verdict::Shrewd : (2LL * R.Score >= Par ? Verdict::Fair : Verdict::Fleeced);
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Shrewd ? "shrewd" : V == Verdict::Fair ? "fair" : "fleeced";
}
inline const char* ErrorName(Error E) {
    return E == Error::Count ? "count" : E == Error::Coin ? "coin" : E == Error::BadSale ? "sale" : "none";
}

}  // namespace SalvageSale
}  // namespace DaedalusDiskSaver
