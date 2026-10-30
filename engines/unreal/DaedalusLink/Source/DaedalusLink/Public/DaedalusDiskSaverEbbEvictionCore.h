// SPDX-License-Identifier: MIT
// G253 Ebb Tide Eviction (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/ebb_eviction.py: the exact (weight, count) 0/1 knapsack DP with Python's
// tie-break (most RAM freed, then the lexicographically smallest index set), the two greedy
// orders, the per-world tide and the summary. Reports can come from a census priced with
// the G206 port (DaedalusDiskSaverCensusPlanCore.h). JSON parsing, the config file and the
// CLI stay in Python. No Unreal includes, no exceptions, no RTTI; errors are codes.
#pragma once

#include "DaedalusDiskSaverCensusPlanCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace EbbEviction {

constexpr std::uint64_t MaxWeight = 1000;
constexpr std::size_t MaxIslands = 512;
constexpr std::size_t MaxWorlds = 100000;
constexpr std::uint64_t MaxRamKiB = 1000000000000000ULL;  // port cap: 512 islands still fit in 64 bits
constexpr std::uint64_t MaxDpWords = 8000000;              // DP table cap (cells x (1 + bitset words))
constexpr std::uint64_t MaxDpSteps = 400000000;            // items x cells x words

enum class Error { None, DuplicateWorld, DuplicateSlot, TooManyIslands, WeightRange, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::DuplicateWorld: return "duplicate_world";
        case Error::DuplicateSlot: return "duplicate_slot";
        case Error::TooManyIslands: return "too_many_islands";
        case Error::WeightRange: return "weight_range";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

struct Row {
    std::uint64_t Slot = 0;
    std::uint64_t RamKiB = 0;
};

struct ReportWorld {
    std::string Id;
    std::vector<Row> Islands;
};

struct Config {
    std::set<std::uint64_t> Pinned;
    std::uint64_t DefaultWeight = 1;
    std::map<std::pair<std::string, std::uint64_t>, std::uint64_t> Weights;
};

struct Item {
    std::uint64_t Slot = 0, RamKiB = 0, Weight = 0;
};

struct Choice {
    bool Has = false;
    std::uint64_t Weight = 0, Count = 0;
    std::vector<std::uint64_t> Slots;
};

enum class Tide { Slack, Ebb, Stranded };

inline const char* TideName(Tide T) { return T == Tide::Slack ? "slack" : T == Tide::Ebb ? "ebb" : "stranded"; }

struct WorldPlan {
    std::string Id;
    std::uint64_t TotalRamKiB = 0, NeedKiB = 0;
    std::vector<std::uint64_t> PinnedSlots;
    Tide T = Tide::Slack;
    Choice Optimal, GreedyHeaviest, GreedyWeight;
};

struct Summary {
    std::uint64_t Worlds = 0, OverBudget = 0, CannotFit = 0, Unloads = 0, GreedyHeaviestWorse = 0, GreedyWeightWorse = 0;
};

// The report from a census priced with G206 (what census_budget.py writes for ebb_eviction).
inline std::vector<ReportWorld> FromCensus(const CensusPlan::Report& R) {
    std::vector<ReportWorld> Out;
    for (const CensusPlan::World& W : R.Worlds) {
        ReportWorld O;
        O.Id = W.Id;
        for (const CensusPlan::Island& I : W.Islands) O.Islands.push_back(Row{I.Slot, I.V.Cost.RamKiB});
        Out.push_back(O);
    }
    return Out;
}

// solve(): need <= 0 -> empty plan; Need is total - budget (signed).
inline Error Solve(std::vector<Item> Items, long long Need, Choice& Out) {
    Out = Choice{};
    if (Need <= 0) {
        Out.Has = true;
        return Error::None;
    }
    std::uint64_t Sum = 0;
    for (const Item& It : Items) Sum += It.RamKiB;
    if (Sum < static_cast<std::uint64_t>(Need)) return Error::None;
    std::sort(Items.begin(), Items.end(), [](const Item& A, const Item& B) {
        return A.Slot != B.Slot ? A.Slot < B.Slot : A.RamKiB != B.RamKiB ? A.RamKiB < B.RamKiB : A.Weight < B.Weight;
    });
    const std::size_t N = Items.size();
    std::uint64_t WMax = 0;
    for (const Item& It : Items) WMax += It.Weight;
    const std::uint64_t Words = (N + 63) / 64;
    const std::uint64_t Cells = (WMax + 1) * (N + 1);
    if (Cells > MaxDpWords || Cells * (1 + Words) > MaxDpWords || N * Cells * (Words ? Words : 1) > MaxDpSteps)
        return Error::Capacity;
    const std::uint64_t None = ~std::uint64_t{0};
    std::vector<std::uint64_t> Freed(Cells, None), Bits(Cells * Words, 0);
    auto At = [&](std::uint64_t W, std::uint64_t C) { return W * (N + 1) + C; };
    Freed[At(0, 0)] = 0;
    // lexicographic order of two equal-length sorted index sets: the set holding the lowest differing index is smaller
    auto Less = [&](const std::uint64_t* A, const std::uint64_t* B) {
        for (std::uint64_t K = 0; K < Words; ++K) {
            if (A[K] == B[K]) continue;
            const std::uint64_t D = A[K] ^ B[K];
            const std::uint64_t Low = D & (~D + 1);
            return (A[K] & Low) != 0;
        }
        return false;
    };
    std::vector<std::uint64_t> Cand(Words ? Words : 1);
    for (std::size_t Idx = 0; Idx < N; ++Idx) {
        const std::uint64_t Wt = Items[Idx].Weight, Ram = Items[Idx].RamKiB;
        for (std::uint64_t W = WMax + 1; W-- > Wt;) {
            for (std::uint64_t C = N; C >= 1; --C) {
                const std::uint64_t P = At(W - Wt, C - 1);
                if (Freed[P] == None) continue;
                const std::uint64_t CandFreed = Freed[P] + Ram;
                for (std::uint64_t K = 0; K < Words; ++K) Cand[K] = Bits[P * Words + K];
                Cand[Idx / 64] |= std::uint64_t{1} << (Idx % 64);
                const std::uint64_t Q = At(W, C);
                if (Freed[Q] == None || CandFreed > Freed[Q] || (CandFreed == Freed[Q] && Less(Cand.data(), &Bits[Q * Words]))) {
                    Freed[Q] = CandFreed;
                    for (std::uint64_t K = 0; K < Words; ++K) Bits[Q * Words + K] = Cand[K];
                }
            }
        }
    }
    for (std::uint64_t W = 0; W <= WMax; ++W) {
        for (std::uint64_t C = 0; C <= N; ++C) {
            const std::uint64_t Q = At(W, C);
            if (Freed[Q] != None && Freed[Q] >= static_cast<std::uint64_t>(Need)) {
                Out.Has = true;
                Out.Weight = W;
                Out.Count = C;
                for (std::size_t I = 0; I < N; ++I)
                    if (Bits[Q * Words + I / 64] >> (I % 64) & 1) Out.Slots.push_back(Items[I].Slot);
                std::sort(Out.Slots.begin(), Out.Slots.end());
                return Error::None;
            }
        }
    }
    return Error::None;
}

enum class Order { HeaviestFirst, LowestWeightFirst };

// greedy(): unload in key order until enough RAM is freed.
inline Choice Greedy(std::vector<Item> Items, long long Need, Order O) {
    Choice Out;
    if (Need <= 0) {
        Out.Has = true;
        return Out;
    }
    std::sort(Items.begin(), Items.end(), [O](const Item& A, const Item& B) {
        if (O == Order::LowestWeightFirst && A.Weight != B.Weight) return A.Weight < B.Weight;
        if (A.RamKiB != B.RamKiB) return A.RamKiB > B.RamKiB;
        return A.Slot < B.Slot;
    });
    std::uint64_t Freed = 0;
    for (const Item& It : Items) {
        if (Freed >= static_cast<std::uint64_t>(Need)) break;
        Freed += It.RamKiB;
        Out.Weight += It.Weight;
        Out.Slots.push_back(It.Slot);
    }
    if (Freed < static_cast<std::uint64_t>(Need)) return Choice{};
    Out.Has = true;
    Out.Count = Out.Slots.size();
    std::sort(Out.Slots.begin(), Out.Slots.end());
    return Out;
}

inline bool Worse(const Choice& G, const Choice& Opt) {
    return G.Weight != Opt.Weight ? G.Weight > Opt.Weight : G.Count > Opt.Count;
}

// plan(): read_report's checks (worlds in file order), then load_config's weight range, then every world by id.
inline Error Plan(const std::vector<ReportWorld>& In, std::uint64_t RamBudget, const Config& Cfg, std::vector<WorldPlan>& Out,
                  Summary& S) {
    Out.clear();
    S = Summary{};
    if (In.size() > MaxWorlds || RamBudget > MaxRamKiB) return Error::Capacity;
    std::set<std::string> Seen;
    for (const ReportWorld& W : In) {
        if (W.Id.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (!Seen.insert(W.Id).second) return Error::DuplicateWorld;
        if (W.Islands.size() > MaxIslands) return Error::TooManyIslands;
        std::set<std::uint64_t> Slots;
        for (const Row& R : W.Islands) {
            if (!Slots.insert(R.Slot).second) return Error::DuplicateSlot;
            if (R.RamKiB > MaxRamKiB) return Error::Capacity;
        }
    }
    if (Cfg.DefaultWeight < 1 || Cfg.DefaultWeight > MaxWeight) return Error::WeightRange;
    for (const auto& KV : Cfg.Weights)
        if (KV.second < 1 || KV.second > MaxWeight) return Error::WeightRange;
    std::vector<const ReportWorld*> Sorted;
    for (const ReportWorld& W : In) Sorted.push_back(&W);
    std::sort(Sorted.begin(), Sorted.end(), [](const ReportWorld* A, const ReportWorld* B) { return A->Id < B->Id; });
    for (const ReportWorld* W : Sorted) {
        std::vector<Row> Rows = W->Islands;
        std::sort(Rows.begin(), Rows.end(), [](const Row& A, const Row& B) { return A.Slot < B.Slot; });
        WorldPlan P;
        P.Id = W->Id;
        std::vector<Item> Items;
        for (const Row& R : Rows) {
            P.TotalRamKiB += R.RamKiB;
            if (Cfg.Pinned.count(R.Slot)) {
                P.PinnedSlots.push_back(R.Slot);
                continue;
            }
            const auto It = Cfg.Weights.find(std::make_pair(W->Id, R.Slot));
            Items.push_back(Item{R.Slot, R.RamKiB, It == Cfg.Weights.end() ? Cfg.DefaultWeight : It->second});
        }
        const long long Need = static_cast<long long>(P.TotalRamKiB) - static_cast<long long>(RamBudget);
        P.NeedKiB = Need > 0 ? static_cast<std::uint64_t>(Need) : 0;
        const Error E = Solve(Items, Need, P.Optimal);
        if (E != Error::None) return E;
        P.GreedyHeaviest = Greedy(Items, Need, Order::HeaviestFirst);
        P.GreedyWeight = Greedy(Items, Need, Order::LowestWeightFirst);
        ++S.Worlds;
        S.OverBudget += Need > 0 ? 1 : 0;
        if (!P.Optimal.Has) {
            ++S.CannotFit;
        } else {
            S.Unloads += P.Optimal.Count;
            S.GreedyHeaviestWorse += Worse(P.GreedyHeaviest, P.Optimal) ? 1 : 0;
            S.GreedyWeightWorse += Worse(P.GreedyWeight, P.Optimal) ? 1 : 0;
        }
        P.T = Need <= 0 ? Tide::Slack : (P.Optimal.Has ? Tide::Ebb : Tide::Stranded);
        Out.push_back(P);
    }
    return Error::None;
}

}  // namespace EbbEviction
}  // namespace DaedalusDiskSaver
