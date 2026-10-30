// SPDX-License-Identifier: MIT
// Shared by the batch 7 DiskSaver cores (G253, G505, G529, G533): census_budget.plan()'s
// checks and ordering on an already-parsed census, priced with the G206/G571 port
// DaedalusCensusBudgetCore.h. The JSON schema checks (format, version, count_semantics,
// types) stay in Python. Header-only C++17; no Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusCensusBudgetCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace CensusPlan {

namespace CB = ::DaedalusCensusBudget;

constexpr std::size_t MaxWorlds = 100000;
constexpr std::size_t MaxIslands = 1000000;  // over the whole census
constexpr std::size_t MaxIdBytes = 4096;
// Python ints are unbounded; the port also caps the census's total asset definitions at
// CB::MaxAssetDefinitions (10^12), so every RAM/disk sum and the x1000 warn products fit in 64 bits.

enum class Error { None, BudgetRange, BudgetWarn, NoWorlds, WorldId, DuplicateWorld, DuplicateSlot, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BudgetRange: return "budget_range";
        case Error::BudgetWarn: return "budget_warn";
        case Error::NoWorlds: return "no_worlds";
        case Error::WorldId: return "world_id";
        case Error::DuplicateWorld: return "duplicate_world";
        case Error::DuplicateSlot: return "duplicate_slot";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

struct InIsland {
    std::uint64_t Slot = 0;
    std::uint64_t Assets = 0;
};

struct InWorld {
    std::string Id;
    std::vector<InIsland> Islands;
};

struct Island {
    std::uint64_t Slot = 0;
    std::uint64_t Assets = 0;
    CB::IslandVerdict V;
};

struct World {
    std::string Id;
    std::vector<Island> Islands;
    CB::WorldVerdict V;
};

struct Report {
    CB::Budget B;
    std::vector<World> Worlds;  // sorted by id
    std::uint64_t Islands = 0, Green = 0, Amber = 0, Red = 0, Spilling = 0;
};

// Python's str.isspace() on ASCII; ids are bytes here (non-ASCII whitespace is not stripped).
inline bool IsSpace(unsigned char C) { return C == ' ' || (C >= 9 && C <= 13) || (C >= 0x1c && C <= 0x1f); }

inline bool Blank(const std::string& S) {
    for (unsigned char C : S)
        if (!IsSpace(C)) return false;
    return true;
}

// load_budget's range checks, in Python's order.
inline Error CheckBudget(const CB::Budget& B) {
    if (B.RamKiB < 1 || B.RamKiB > CB::MaxKiB || B.DiskKiB < 1 || B.DiskKiB > CB::MaxKiB) return Error::BudgetRange;
    if (B.WarnPermille < 1 || B.WarnPermille > 1000) return Error::BudgetWarn;
    return Error::None;
}

// census_budget.plan(): budget, then read_census (worlds in file order), then price worlds by id.
inline Error Plan(const std::vector<InWorld>& In, const CB::Budget& B, Report& Out) {
    Out = Report{};
    Out.B = B;
    const Error BE = CheckBudget(B);
    if (BE != Error::None) return BE;
    if (In.empty()) return Error::NoWorlds;
    if (In.size() > MaxWorlds) return Error::Capacity;
    std::set<std::string> Seen;
    std::size_t Total = 0;
    std::uint64_t Assets = 0;
    for (const InWorld& W : In) {
        if (W.Id.size() > MaxIdBytes) return Error::Capacity;
        if (W.Id.empty() || Blank(W.Id)) return Error::WorldId;
        if (!Seen.insert(W.Id).second) return Error::DuplicateWorld;
        Total += W.Islands.size();
        if (W.Islands.size() > MaxIslands || Total > MaxIslands) return Error::Capacity;
        std::set<std::uint64_t> Slots;
        for (const InIsland& I : W.Islands) {
            if (I.Assets > CB::MaxAssetDefinitions - Assets) return Error::Capacity;  // census total stays <= 10^12
            Assets += I.Assets;
            if (!Slots.insert(I.Slot).second) return Error::DuplicateSlot;
        }
    }
    std::vector<const InWorld*> Order;
    for (const InWorld& W : In) Order.push_back(&W);
    std::sort(Order.begin(), Order.end(), [](const InWorld* A, const InWorld* Bw) { return A->Id < Bw->Id; });
    for (const InWorld* W : Order) {
        World O;
        O.Id = W->Id;
        std::vector<InIsland> Rows = W->Islands;
        std::sort(Rows.begin(), Rows.end(), [](const InIsland& A, const InIsland& Bi) { return A.Slot < Bi.Slot; });
        std::vector<std::uint64_t> Counts;
        for (const InIsland& I : Rows) Counts.push_back(I.Assets);
        std::vector<CB::IslandVerdict> Vs;
        if (!CB::PlanWorld(Counts, B, O.V, Vs)) return Error::Capacity;
        for (std::size_t K = 0; K < Rows.size(); ++K) O.Islands.push_back(Island{Rows[K].Slot, Rows[K].Assets, Vs[K]});
        Out.Islands += Rows.size();
        Out.Green += O.V.Green;
        Out.Amber += O.V.Amber;
        Out.Red += O.V.Red;
        Out.Spilling += O.V.FitsAllResident ? 0 : 1;
        Out.Worlds.push_back(O);
    }
    return Error::None;
}

}  // namespace CensusPlan
}  // namespace DaedalusDiskSaver
