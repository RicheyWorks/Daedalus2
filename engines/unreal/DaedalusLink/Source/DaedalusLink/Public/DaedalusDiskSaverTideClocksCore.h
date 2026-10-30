// SPDX-License-Identifier: MIT
// G166 Tide Clocks core, header-only C++17 port of tools/streaming/tide_clocks.py (G578 batch 6).
// The tool interleaves Python's random with its simulation, so the core never draws numbers: it
// replays the tool's recorded draws (a tape of randrange/randint/sample results in call order,
// carried in the golden file) through the ported simulation, checking every draw against its own
// bound. Ported: config range checks, island skews, edits (Lamport and vector clocks, causal
// history oracle), ferries and merges under wall/lamport LWW or vector siblings, lost edits,
// detected vs oracle conflicts, causal inversions and the status. Left in Python: the JSON config
// schema and npc lines, the G86 shoals file read and the CLI. Engine-free: no Unreal includes, no
// exceptions, no RTTI. Runs stop at MaxSteps steps and MaxIslands islands.
#pragma once

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <tuple>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace TideClocks {

constexpr int MaxIslands = 64;
constexpr int MaxSaves = 1000;
constexpr long long MaxSteps = 10000;
constexpr long long MaxSkew = 1000000000;
enum class Error { None, BadConfig, Capped, Tape };
enum class Clock { Wall, Lamport, Vector };

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
    long long Islands = 0, Saves = 0, Steps = 0, EditPermille = 0, MaxSkewTicks = 0;
};

// validate()'s numeric rules; G86Islands and KeysPerIsland come from the shoals data.
inline bool ValidConfig(const Config& C, long long G86Islands, long long KeysPerIsland) {
    if (C.Islands < 0 || C.Saves < 0 || C.Steps < 0 || C.EditPermille < 0 || C.MaxSkewTicks < 0) return false;
    if (C.EditPermille < 1 || C.EditPermille > 999) return false;
    if (C.Islands < 2 || C.Islands > G86Islands) return false;
    if (C.Saves < 1 || C.Saves > KeysPerIsland) return false;
    return C.Steps >= 1;
}

// Recorded draws: Next(Lo, Hi) returns the next value if it lies in [Lo, Hi], else flags the tape bad.
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

struct Result {
    Error Err = Error::None;
    bool Won = false;
    int Edits = 0, Lost = 0, Detected = 0, Oracle = 0, Inversions = 0, Survivors = 0;
    std::vector<int> LostVids;
};

namespace Detail {
struct Bits {
    std::vector<std::uint64_t> W;
    void Set(int I) {
        if (static_cast<std::size_t>(I / 64) >= W.size()) W.resize(I / 64 + 1, 0);
        W[I / 64] |= std::uint64_t{1} << (I % 64);
    }
    bool Has(int I) const { return static_cast<std::size_t>(I / 64) < W.size() && (W[I / 64] >> (I % 64) & 1); }
    void Or(const Bits& O) {
        if (O.W.size() > W.size()) W.resize(O.W.size(), 0);
        for (std::size_t K = 0; K < O.W.size(); ++K) W[K] |= O.W[K];
    }
};
struct Ver {
    int Vid = 0, Save = 0, Island = 0;
    long long Wall = 0, Lamport = 0;
    std::vector<long long> Vc;
    Bits History;
};
struct Island {
    long long Skew = 0, Lamport = 0;
    std::vector<long long> Vc;
    Bits Seen;
    std::map<int, std::vector<int>> Store;  // save -> vids, sorted by vid
};
inline bool VcLe(const std::vector<long long>& A, const std::vector<long long>& B) {
    for (std::size_t I = 0; I < A.size(); ++I)
        if (A[I] > B[I]) return false;
    return true;
}
inline bool VcLt(const std::vector<long long>& A, const std::vector<long long>& B) { return VcLe(A, B) && A != B; }

struct Sim {
    Clock K = Clock::Vector;
    std::vector<Ver> Vers;
    std::vector<Island> Isl;
    std::set<std::pair<int, int>> OraclePairs, DetectedPairs;
    std::set<int> LostSet;

    bool Hb(int A, int B) const { return Vers[B].History.Has(Vers[A].Vid); }

    void Merge(Island& Dst, int Save, const std::vector<int>& Incoming) {
        std::vector<int> Vs;
        auto It = Dst.Store.find(Save);
        if (It != Dst.Store.end()) Vs = It->second;
        for (int V : Incoming)
            if (std::find(Vs.begin(), Vs.end(), V) == Vs.end()) Vs.push_back(V);
        std::vector<int> Top;
        for (int A : Vs) {
            bool Below = false;
            for (int B : Vs) Below = Below || Hb(A, B);
            if (!Below) Top.push_back(A);
        }
        for (int A : Top)
            for (int B : Top)
                if (A < B) OraclePairs.insert({A, B});
        std::vector<int> Keep;
        if (K == Clock::Vector) {
            for (int V : Vs) {
                bool Dominated = false;
                for (int W : Vs) Dominated = Dominated || VcLt(Vers[V].Vc, Vers[W].Vc);
                if (!Dominated) Keep.push_back(V);
            }
            for (int A : Keep)
                for (int B : Keep)
                    if (A < B && !VcLe(Vers[A].Vc, Vers[B].Vc) && !VcLe(Vers[B].Vc, Vers[A].Vc)) DetectedPairs.insert({A, B});
        } else if (!Vs.empty()) {
            int Best = Vs[0];
            for (int V : Vs) {
                const Ver& X = Vers[V];
                const Ver& Y = Vers[Best];
                const long long Kx = K == Clock::Wall ? X.Wall : X.Lamport, Ky = K == Clock::Wall ? Y.Wall : Y.Lamport;
                if (std::make_tuple(Kx, X.Island, X.Vid) > std::make_tuple(Ky, Y.Island, Y.Vid)) Best = V;
            }
            Keep.push_back(Best);
        }
        for (int V : Vs) {
            if (std::find(Keep.begin(), Keep.end(), V) != Keep.end()) continue;
            bool Seen = false;
            for (int W : Keep) Seen = Seen || Hb(V, W);
            if (!Seen) LostSet.insert(V);
        }
        std::sort(Keep.begin(), Keep.end());
        Dst.Store[Save] = Keep;
    }

    void Absorb(Island& Dst, const std::vector<int>& Vs) {
        for (int V : Vs) {
            Dst.Seen.Or(Vers[V].History);
            Dst.Seen.Set(V);
            Dst.Lamport = std::max(Dst.Lamport, Vers[V].Lamport);
            for (std::size_t I = 0; I < Dst.Vc.size(); ++I) Dst.Vc[I] = std::max(Dst.Vc[I], Vers[V].Vc[I]);
        }
    }

    void Ferry(int Src, int Dst) {
        const std::map<int, std::vector<int>> Snapshot = Isl[Src].Store;
        for (const auto& KV : Snapshot) {
            Merge(Isl[Dst], KV.first, KV.second);
            Absorb(Isl[Dst], KV.second);
        }
    }
};
}  // namespace Detail

// run(config, clock) replayed from the tool's recorded draws.
inline Result Run(const Config& C, Clock K, const std::vector<long long>& Draws) {
    Result R;
    if (C.Islands < 2 || C.Islands > MaxIslands || C.Saves < 1 || C.Saves > MaxSaves || C.Steps < 1 || C.EditPermille < 0 ||
        C.EditPermille > 1000 || C.MaxSkewTicks < 0 || C.MaxSkewTicks > MaxSkew) {
        R.Err = Error::BadConfig;
        return R;
    }
    if (C.Steps > MaxSteps) {
        R.Err = Error::Capped;
        return R;
    }
    Tape T(Draws);
    const int N = static_cast<int>(C.Islands);
    Detail::Sim S;
    S.K = K;
    S.Isl.resize(N);
    for (int I = 0; I < N; ++I) {
        S.Isl[I].Skew = T.Next(-C.MaxSkewTicks, C.MaxSkewTicks);
        S.Isl[I].Vc.assign(N, 0);
    }
    for (long long Step = 1; Step <= C.Steps && !T.Failed(); ++Step) {
        if (T.Next(0, 999) < C.EditPermille) {
            const int I = static_cast<int>(T.Next(0, N - 1));
            const int Save = static_cast<int>(T.Next(0, C.Saves - 1));
            if (T.Failed()) break;
            Detail::Island& Me = S.Isl[I];
            ++Me.Lamport;
            ++Me.Vc[I];
            Detail::Ver V;
            V.Vid = static_cast<int>(S.Vers.size());
            V.Save = Save;
            V.Island = I;
            V.Wall = Step + Me.Skew;
            V.Lamport = Me.Lamport;
            V.Vc = Me.Vc;
            V.History = Me.Seen;
            S.Vers.push_back(V);
            Me.Seen.Set(V.Vid);
            Me.Store[Save] = {V.Vid};
        } else {
            const int I = static_cast<int>(T.Next(0, N - 1));
            const int J = static_cast<int>(T.Next(0, N - 1));
            if (T.Failed() || I == J) {
                R.Err = Error::Tape;
                return R;
            }
            S.Ferry(I, J);
        }
    }
    if (!T.Ok()) {
        R.Err = Error::Tape;
        return R;
    }
    for (int Round = 0; Round < 2; ++Round)
        for (int A = 0; A < N; ++A)
            for (int B = 0; B < N; ++B)
                if (A != B) S.Ferry(A, B);
    std::set<int> Surv;
    for (const auto& X : S.Isl)
        for (const auto& KV : X.Store) Surv.insert(KV.second.begin(), KV.second.end());
    const int V = static_cast<int>(S.Vers.size());
    for (int B = 0; B < V; ++B)
        for (int A = 0; A < V; ++A)
            if (S.Hb(A, B) && S.Vers[A].Save == S.Vers[B].Save && S.Vers[A].Wall >= S.Vers[B].Wall) ++R.Inversions;
    R.Edits = V;
    R.LostVids.assign(S.LostSet.begin(), S.LostSet.end());
    R.Lost = static_cast<int>(R.LostVids.size());
    R.Detected = static_cast<int>(S.DetectedPairs.size());
    R.Oracle = static_cast<int>(S.OraclePairs.size());
    R.Survivors = static_cast<int>(Surv.size());
    R.Won = R.LostVids.empty();
    return R;
}

}  // namespace TideClocks
}  // namespace DaedalusDiskSaver
