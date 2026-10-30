// SPDX-License-Identifier: MIT
// G179 Bottle Census core, header-only C++17 port of tools/streaming/bottle_census.py (G578 batch 6).
// The board lists disk-saver as this tool's owner; its first commit carries another bot's author
// name. This port is additive and edits nothing of the Python tool. The tool interleaves Python's
// random with its simulation, so the core replays the tool's recorded draws (randrange/randint
// results in call order, carried in the golden file), checking each against its own bound.
// Ported: config range checks, the FIFO or free lanes, the local/sync/marker (Chandy-Lamport)
// censuses, the drain of bottles still at sea, cut_consistent, in_transit_oracle and the status.
// Left in Python: the JSON config schema and npc lines, the G86 shoals file read and the CLI.
// Engine-free: no Unreal includes, no exceptions, no RTTI. Runs stop at MaxPosts posts.
#pragma once

#include <algorithm>
#include <cstdint>
#include <functional>
#include <map>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace BottleCensus {

constexpr std::size_t MaxPosts = 4000000;
constexpr int MaxIslands = 1000;
enum class Error { None, BadConfig, Capped, Tape };
enum class Mode { Local, Sync, Marker };
enum class Reason { None, TotalWrong, InconsistentCut };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadConfig: return "config";
        case Error::Capped: return "capped";
        case Error::Tape: return "tape";
    }
    return "?";
}
inline const char* ReasonName(Reason R) {
    switch (R) {
        case Reason::None: return "-";
        case Reason::TotalWrong: return "total_wrong";
        case Reason::InconsistentCut: return "inconsistent_cut";
    }
    return "?";
}

struct Config {
    std::vector<long long> Weights;
    long long CreditsPerWeight = 0, Ticks = 0, SendPermille = 0, MaxAmount = 0, MaxDelay = 0, Start = 0, MaxSkew = 0, Initiator = 0;
};

// validate()'s numeric rules (two or more G86 islands).
inline bool ValidConfig(const Config& C) {
    auto In = [](long long V, long long Lo, long long Hi) { return V >= Lo && V <= Hi; };
    const long long N = static_cast<long long>(C.Weights.size());
    if (N < 2 || N > MaxIslands) return false;
    for (long long W : C.Weights)
        if (W < 0 || W > 1000000) return false;
    return In(C.Ticks, 2, 100000) && In(C.CreditsPerWeight, 1, 1000000) && In(C.SendPermille, 0, 1000) &&
           In(C.MaxAmount, 1, 1000000) && In(C.MaxDelay, 1, 1000) && In(C.Start, 0, C.Ticks - 1) && In(C.MaxSkew, 0, 1000) &&
           In(C.Initiator, 0, N - 1);
}

class Tape {
public:
    explicit Tape(const std::vector<long long>& V) : Vals(V) {}
    long long Next(long long Lo, long long Hi) {
        if (Bad || Pos >= Vals.size() || Vals[Pos] < Lo || Vals[Pos] > Hi) {
            Bad = true;
            return Lo;
        }
        return Vals[Pos++];
    }
    bool Ok() const { return !Bad && Pos == Vals.size(); }
    bool Failed() const { return Bad; }

private:
    const std::vector<long long>& Vals;
    std::size_t Pos = 0;
    bool Bad = false;
};

struct Bottle {
    long long Seq = 0, Src = 0, Dst = 0, Amount = 0, Sent = 0, Arrive = 0, SendEv = 0, RecvEv = 0;
};

// cut_consistent(): nothing received inside the cut unless its send is inside the cut too.
inline bool CutConsistent(const std::vector<Bottle>& Log, const std::vector<long long>& Cut) {
    for (const Bottle& B : Log)
        if (B.RecvEv < Cut[B.Dst] && B.SendEv >= Cut[B.Src]) return false;
    return true;
}
// in_transit_oracle(): sent inside the cut, received outside it.
inline std::vector<long long> InTransit(const std::vector<Bottle>& Log, const std::vector<long long>& Cut) {
    std::vector<long long> Out;
    for (const Bottle& B : Log)
        if (B.SendEv < Cut[B.Src] && B.RecvEv >= Cut[B.Dst]) Out.push_back(B.Seq);
    std::sort(Out.begin(), Out.end());
    return Out;
}

struct Result {
    Error Err = Error::None;
    long long TrueTotal = 0, Census = 0, Counted = 0, AtSea = 0, Bottles = 0;
    bool Consistent = false, Won = false;
    Reason Why = Reason::None;
    std::vector<long long> Cut, Lane, InTransitOracle;
};

namespace Detail {
struct Post {
    long long Arrive, Seq;
    bool Marker;
    long long Src, Dst, Amount, Sent, SendEv;
    bool operator>(const Post& O) const { return std::tie(Arrive, Seq) > std::tie(O.Arrive, O.Seq); }
};
}  // namespace Detail

inline Result Run(const Config& C, Mode M, bool Fifo, const std::vector<long long>& Draws) {
    Result R;
    if (!ValidConfig(C)) {
        R.Err = Error::BadConfig;
        return R;
    }
    Tape T(Draws);
    const long long N = static_cast<long long>(C.Weights.size());
    std::vector<long long> Bal(N), Skew(N), Ev(N, 0), Counted(N, 0), Cut(N, -1);
    for (long long I = 0; I < N; ++I) {
        Bal[I] = C.Weights[I] * C.CreditsPerWeight;
        R.TrueTotal += Bal[I];
    }
    for (auto& S : Skew) S = T.Next(0, C.MaxSkew);
    std::map<std::pair<long long, long long>, long long> LaneLast;
    std::map<std::pair<long long, long long>, bool> Recording;
    std::priority_queue<Detail::Post, std::vector<Detail::Post>, std::greater<Detail::Post>> Sea;
    long long Seq = 0, Markers = 0, LaneAmt = 0;
    std::size_t Posts = 0;
    bool Cap = false;
    std::vector<Bottle> Done;
    auto PostOne = [&](long long Tk, bool Marker, long long Src, long long Dst, long long Amount) {
        if (++Posts > MaxPosts) {
            Cap = true;
            return;
        }
        long long Arrive = Tk + T.Next(1, C.MaxDelay);
        if (Fifo) {
            auto It = LaneLast.find({Src, Dst});
            Arrive = std::max(Arrive, It == LaneLast.end() ? 0 : It->second);
            LaneLast[{Src, Dst}] = Arrive;
        }
        Sea.push({Arrive, Seq, Marker, Src, Dst, Amount, Tk, Ev[Src]});
        if (!Marker) ++Ev[Src];
        else ++Markers;
        ++Seq;
    };
    auto Count = [&](long long I, long long Tk) {
        Cut[I] = Ev[I];
        Counted[I] = Bal[I];
        if (M == Mode::Marker) {
            for (long long J = 0; J < N; ++J)
                if (J != I) Recording[{J, I}] = true;
            for (long long J = 0; J < N; ++J)
                if (J != I) PostOne(Tk, true, I, J, 0);
        }
    };
    for (long long Tk = 0; (Tk < C.Ticks || (M == Mode::Marker && Markers > 0)) && !T.Failed() && !Cap; ++Tk) {
        if (M == Mode::Sync && Tk == C.Start)
            for (long long I = 0; I < N; ++I) Count(I, Tk);
        if (M == Mode::Local)
            for (long long I = 0; I < N; ++I)
                if (Cut[I] < 0 && Tk == C.Start + Skew[I]) Count(I, Tk);
        if (M == Mode::Marker && Tk == C.Start) Count(C.Initiator, Tk);
        while (!Sea.empty() && Sea.top().Arrive <= Tk) {
            const Detail::Post P = Sea.top();
            Sea.pop();
            if (P.Marker) {
                --Markers;
                if (Cut[P.Dst] < 0) Count(P.Dst, Tk);
                Recording[{P.Src, P.Dst}] = false;
                continue;
            }
            Bal[P.Dst] += P.Amount;
            Done.push_back({P.Seq, P.Src, P.Dst, P.Amount, P.Sent, P.Arrive, P.SendEv, Ev[P.Dst]});
            ++Ev[P.Dst];
            if (M == Mode::Marker && Cut[P.Dst] >= 0) {
                auto It = Recording.find({P.Src, P.Dst});
                if (It != Recording.end() && It->second) {
                    R.Lane.push_back(P.Seq);
                    LaneAmt += P.Amount;
                }
            }
        }
        if (Tk < C.Ticks)
            for (long long I = 0; I < N; ++I)
                if (Bal[I] && T.Next(0, 999) < C.SendPermille) {
                    const long long Amt = T.Next(1, std::min(C.MaxAmount, Bal[I]));
                    const long long J = (I + 1 + T.Next(0, N - 2)) % N;
                    Bal[I] -= Amt;
                    PostOne(Tk, false, I, J, Amt);
                }
    }
    if (Cap) {
        R.Err = Error::Capped;
        return R;
    }
    if (!T.Ok()) {
        R.Err = Error::Tape;
        return R;
    }
    while (!Sea.empty()) {
        const Detail::Post P = Sea.top();
        Sea.pop();
        if (P.Marker) continue;
        Bal[P.Dst] += P.Amount;
        Done.push_back({P.Seq, P.Src, P.Dst, P.Amount, P.Sent, P.Arrive, P.SendEv, Ev[P.Dst]});
        ++Ev[P.Dst];
    }
    for (long long I = 0; I < N; ++I) {
        R.Cut.push_back(Cut[I] >= 0 ? Cut[I] : Ev[I]);
        R.Counted += Counted[I];
    }
    std::sort(R.Lane.begin(), R.Lane.end());
    R.Consistent = CutConsistent(Done, R.Cut);
    R.InTransitOracle = InTransit(Done, R.Cut);
    R.AtSea = LaneAmt;
    R.Census = R.Counted + LaneAmt;
    R.Bottles = static_cast<long long>(Done.size());
    R.Why = R.Census != R.TrueTotal ? Reason::TotalWrong : !R.Consistent ? Reason::InconsistentCut : Reason::None;
    R.Won = R.Why == Reason::None;
    return R;
}

}  // namespace BottleCensus
}  // namespace DaedalusDiskSaver
