// SPDX-License-Identifier: MIT
// G554 Tide Lock core, header-only C++17 port of tools/streaming/tide_lock.py (G576 batch 4).
// Takes the boat queue as the Python tool laid it out (length KiB and arrival minute, queue
// order; the seeded shuffle and arrivals stay in Python), the chamber and the cycle, and ports the
// plan run (lock timing and waits), the exact memoised optimum (same split order and tuple tie
// rule, so the optimal plan matches), the fill-the-chamber greedy, the jam reasons and the
// verdict. Engine-free: no Unreal includes, no exceptions, no RTTI. The optimum stops at MaxStates
// memo entries and plans longer than MaxPlan groups are refused.
#pragma once

#include <algorithm>
#include <cstdint>
#include <map>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace TideLock {

constexpr int MaxBoats = 60;  // same cap as Python's MAX_BOATS
constexpr std::int64_t MaxKib = 100000000;  // census_budget.MAX_KIB
constexpr std::int64_t MaxMinute = 1000000000;
constexpr std::size_t MaxStates = 1000000;
constexpr std::size_t MaxPlan = 4096;
enum class Error { None, BadQueue, Param, Long, Capped, TooLong };
enum class Verdict { Smooth, Slow, Jammed };
enum class Jam { None, Plan, Group };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadQueue: return "queue";
        case Error::Param: return "param";
        case Error::Long: return "long";
        case Error::Capped: return "capped";
        case Error::TooLong: return "toolong";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Smooth: return "smooth";
        case Verdict::Slow: return "slow";
        case Verdict::Jammed: return "jammed";
    }
    return "?";
}

struct Boat {
    std::int64_t Length = 0, Arrives = 0;
};
struct Lock {
    std::int64_t Chamber = 0, Cycle = 0;
    std::vector<Boat> Queue;
};

// puzzle()'s checks in its order: chamber/cycle range, then the queue the tool would build.
inline Error Validate(const Lock& L) {
    if (L.Chamber < 1 || L.Chamber > MaxKib || L.Cycle < 1 || L.Cycle > MaxKib) return Error::Param;
    if (L.Queue.empty() || L.Queue.size() > static_cast<std::size_t>(MaxBoats)) return Error::BadQueue;
    for (const Boat& B : L.Queue)
        if (B.Length < 0 || B.Length > MaxKib || B.Arrives < 0 || B.Arrives > MaxMinute) return Error::BadQueue;
    return Error::None;
}

struct Run {
    Jam J = Jam::None;
    int Group = 0;  // 1-based group that overfills, for Jam::Group
    std::int64_t Wait = 0;
};

// run_plan(): total wait of a legal plan, or why it jams.
inline Run RunPlan(const Lock& L, const std::vector<std::int64_t>& Sizes) {
    Run R;
    const std::int64_t N = static_cast<std::int64_t>(L.Queue.size());
    std::int64_t Sum = 0;
    bool Bad = false;
    for (std::int64_t S : Sizes) {
        Sum += S;  // |S| <= 1e9 and at most MaxPlan entries: no overflow
        if (S < 1) Bad = true;
    }
    if (Sum != N || Bad) {
        R.J = Jam::Plan;
        return R;
    }
    std::int64_t Free = 0;
    std::size_t I = 0;
    for (std::size_t G = 0; G < Sizes.size(); ++G) {
        const std::size_t E = I + static_cast<std::size_t>(Sizes[G]);
        std::int64_t Load = 0;
        for (std::size_t K = I; K < E; ++K) Load += L.Queue[K].Length;
        if (Load > L.Chamber) {
            R.J = Jam::Group;
            R.Group = static_cast<int>(G) + 1;
            return R;
        }
        const std::int64_t Leave = std::max(Free, L.Queue[E - 1].Arrives);
        for (std::size_t K = I; K < E; ++K) R.Wait += Leave - L.Queue[K].Arrives;
        Free = Leave + L.Cycle;
        I = E;
    }
    return R;
}

namespace Detail {
struct Best {
    std::int64_t Cost = 0;
    std::vector<std::int64_t> Plan;
};
struct Search {
    const Lock* L = nullptr;
    std::map<std::pair<std::size_t, std::int64_t>, Best> Memo;
    bool Capped = false;

    const Best* Get(std::size_t I, std::int64_t Free) {
        const auto Key = std::make_pair(I, Free);
        auto It = Memo.find(Key);
        if (It != Memo.end()) return &It->second;
        if (Memo.size() >= MaxStates) {
            Capped = true;
            return nullptr;
        }
        Best Out;
        const std::size_t N = L->Queue.size();
        if (I < N) {
            bool Have = false;
            std::int64_t Load = 0;
            for (std::size_t J = I; J < N; ++J) {
                Load += L->Queue[J].Length;
                if (Load > L->Chamber) break;
                const std::int64_t Leave = std::max(Free, L->Queue[J].Arrives);
                std::int64_t Wait = 0;
                for (std::size_t K = I; K <= J; ++K) Wait += Leave - L->Queue[K].Arrives;
                const Best* Rest = Get(J + 1, Leave + L->Cycle);
                if (!Rest) return nullptr;
                Best Cand;
                Cand.Cost = Wait + Rest->Cost;
                Cand.Plan.push_back(static_cast<std::int64_t>(J - I + 1));
                Cand.Plan.insert(Cand.Plan.end(), Rest->Plan.begin(), Rest->Plan.end());
                // Python: cand < result on (cost, plan tuple); vector < is the same lexicographic rule.
                if (!Have || Cand.Cost < Out.Cost || (Cand.Cost == Out.Cost && Cand.Plan < Out.Plan)) {
                    Out = Cand;
                    Have = true;
                }
            }
        }
        return &Memo.emplace(Key, Out).first->second;
    }
};
}  // namespace Detail

// optimum(): least total wait and its plan sizes.
inline Error Optimum(const Lock& L, std::int64_t& Cost, std::vector<std::int64_t>& Plan) {
    const Error V = Validate(L);
    if (V != Error::None) return V;
    for (const Boat& B : L.Queue)
        if (B.Length > L.Chamber) return Error::Long;
    Detail::Search S;
    S.L = &L;
    const Detail::Best* B = S.Get(0, 0);
    if (!B || S.Capped) return Error::Capped;
    Cost = B->Cost;
    Plan = B->Plan;
    return Error::None;
}

inline std::vector<std::int64_t> Greedy(const Lock& L) {
    std::vector<std::int64_t> Sizes;
    std::int64_t Load = 0, Count = 0;
    for (const Boat& B : L.Queue) {
        if (Count && Load + B.Length > L.Chamber) {
            Sizes.push_back(Count);
            Load = 0;
            Count = 0;
        }
        Load += B.Length;
        ++Count;
    }
    Sizes.push_back(Count);
    return Sizes;
}

struct Result {
    Error Err = Error::None;
    Run R;
    Verdict V = Verdict::Jammed;
};

// puzzle(plan=...) after a successful Optimum: OptimalWait is its cost.
inline Result Play(const Lock& L, std::int64_t OptimalWait, const std::vector<std::int64_t>& Sizes) {
    Result Out;
    if (Validate(L) != Error::None) {
        Out.Err = Validate(L);
        return Out;
    }
    if (Sizes.size() > MaxPlan) {
        Out.Err = Error::TooLong;
        return Out;
    }
    for (std::int64_t S : Sizes)
        if (S < -MaxMinute || S > MaxMinute) {
            Out.Err = Error::TooLong;
            return Out;
        }
    Out.R = RunPlan(L, Sizes);
    Out.V = Out.R.J != Jam::None ? Verdict::Jammed : Out.R.Wait == OptimalWait ? Verdict::Smooth : Verdict::Slow;
    return Out;
}

}  // namespace TideLock
}  // namespace DaedalusDiskSaver
