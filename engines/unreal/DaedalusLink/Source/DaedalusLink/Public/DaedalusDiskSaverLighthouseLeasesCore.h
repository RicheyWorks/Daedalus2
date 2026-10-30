// SPDX-License-Identifier: MIT
// G171 Lighthouse Leases core, header-only C++17 port of tools/streaming/lighthouse_leases.py
// (G578 batch 6). The tool interleaves Python's random with its simulation, so the core replays
// the tool's recorded draws (randrange/randint results in call order, carried in the golden file)
// and checks each against its own bound. Ported: config range checks, local_elapsed, drift_bound,
// last_valid_elapsed, the epoch/keeper/write/pause schedule under none/naive/guard/fenced, the
// landing-order sort, fencing, the stale-write count (a running maximum, equal to the tool's
// brute-force oracle) and the status. Left in Python: the JSON config schema and npc lines, the G86
// shoals file read and the CLI. Engine-free: no Unreal includes, no exceptions, no RTTI. Runs stop
// at MaxWrites writes.
#pragma once

#include <algorithm>
#include <cstdint>
#include <tuple>
#include <vector>

namespace DaedalusDiskSaver {
namespace LighthouseLeases {

constexpr std::size_t MaxWrites = 2000000;
constexpr int MaxKeepers = 1000;
enum class Error { None, BadConfig, Capped, Tape };
enum class Mode { None, Naive, Guard, Fenced };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadConfig: return "config";
        case Error::Capped: return "capped";
        case Error::Tape: return "tape";
    }
    return "?";
}

struct Config {
    long long Keepers = 0, Lease = 0, Epochs = 0, WritePermille = 0, MaxDriftPermille = 0, PausePermille = 0, MaxPause = 0,
              NewsDelay = 0, Guard = 0;
};

// validate()'s numeric rules (two or more G86 keepers).
inline bool ValidConfig(const Config& C) {
    auto In = [](long long V, long long Lo, long long Hi) { return V >= Lo && V <= Hi; };
    return C.Keepers >= 2 && C.Keepers <= MaxKeepers && In(C.Lease, 2, 1000) && In(C.Epochs, 1, 10000) &&
           In(C.WritePermille, 1, 1000) && In(C.MaxDriftPermille, 0, 500) && In(C.PausePermille, 0, 1000) &&
           In(C.MaxPause, 0, 1000) && In(C.NewsDelay, 0, 1000) && In(C.Guard, 0, C.Lease - 1);
}

// Ticks a keeper's clock shows after TrueElapsed ticks at Drift per mille (Python floor division).
inline long long LocalElapsed(long long TrueElapsed, long long Drift) {
    const long long P = TrueElapsed * (1000 + Drift);
    return P >= 0 ? P / 1000 : -((-P + 999) / 1000);
}
inline long long DriftBound(long long Lease, long long Drift) { return Lease - LocalElapsed(Lease, -Drift); }

// Largest true elapsed tick at which the keeper still thinks its lease holds; -1 if out of range.
inline long long LastValidElapsed(long long Lease, long long Drift, long long Guard) {
    if (Lease < 0 || Lease > 1000000 || Drift < -1000000 || Drift > 999 || Guard < 0) return -1;
    long long E = 0;
    while (LocalElapsed(E + 1, -Drift) < Lease - Guard) ++E;  // 1000 - Drift >= 1, so this ends
    return E;
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

struct Write {
    long long Land = 0, Token = 0, Keeper = 0, Checked = 0;
};
struct Result {
    Error Err = Error::None;
    long long Writes = 0, Accepted = 0, Rejected = 0, Stale = 0, Outside = 0;
    bool Won = false;
};

inline Result Run(const Config& C, Mode M, const std::vector<long long>& Draws) {
    Result R;
    if (!ValidConfig(C)) {
        R.Err = Error::BadConfig;
        return R;
    }
    Tape T(Draws);
    const long long N = C.Keepers;
    std::vector<long long> Drift(N);
    for (auto& D : Drift) D = T.Next(-C.MaxDriftPermille, C.MaxDriftPermille);
    const long long Guard = (M == Mode::Guard || M == Mode::Fenced) ? C.Guard : 0;
    std::vector<long long> Starts{0};
    for (long long E = 0; E < C.Epochs; ++E) Starts.push_back(Starts.back() + C.Lease + T.Next(0, 1));
    std::vector<Write> W;
    long long Keeper = 0;
    for (long long E = 0; E < C.Epochs && !T.Failed(); ++E) {
        const long long S = Starts[E], Nxt = Starts[E + 1];
        Keeper = E ? (Keeper + 1 + T.Next(0, N - 2)) % N : T.Next(0, N - 1);
        const long long Stop = M == Mode::None ? Nxt + C.NewsDelay : Nxt + C.Lease * 2;
        for (long long Tk = S; Tk < Stop && !T.Failed(); ++Tk) {
            if (Tk > S && T.Next(0, 999) >= C.WritePermille) continue;
            if (M != Mode::None && LocalElapsed(Tk - S, Drift[Keeper]) >= C.Lease - Guard) break;
            long long Pause = 0;
            if (Tk > S && C.MaxPause && T.Next(0, 999) < C.PausePermille) Pause = T.Next(1, C.MaxPause);
            if (W.size() >= MaxWrites) {
                R.Err = Error::Capped;
                return R;
            }
            W.push_back({Tk + Pause, E + 1, Keeper, Tk});
            if (Tk + Pause >= S + C.Lease) ++R.Outside;
        }
    }
    if (!T.Ok()) {
        R.Err = Error::Tape;
        return R;
    }
    std::stable_sort(W.begin(), W.end(), [](const Write& A, const Write& B) {
        return std::tie(A.Land, A.Checked, A.Token) < std::tie(B.Land, B.Checked, B.Token);
    });
    long long Hi = 0, AccHi = 0;
    for (const Write& X : W) {
        const bool Ok = !(M == Mode::Fenced && X.Token < Hi);
        if (Ok) {
            Hi = std::max(Hi, X.Token);
            ++R.Accepted;
            if (M != Mode::Fenced && X.Token < AccHi) ++R.Stale;  // some earlier accepted write has a higher token
            AccHi = std::max(AccHi, X.Token);
        }
    }
    R.Writes = static_cast<long long>(W.size());
    R.Rejected = R.Writes - R.Accepted;
    R.Won = R.Stale == 0;
    return R;
}

}  // namespace LighthouseLeases
}  // namespace DaedalusDiskSaver
