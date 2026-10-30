// SPDX-License-Identifier: MIT
// G206 Census Budget Beacons cost model, header-only C++17 port (disk-saver).
// Mirrors tools/streaming/census_budget.py: RAM 16 MiB + 24 KiB and disk 4 MiB + 96 KiB per
// asset definition (ESTIMATE), beacon flags/colour against the resident-set budget
// (shipped: 40000 KiB RAM, 32768 KiB disk, warn 900 permille) and the lightest-first
// max-resident count. Engine-free: no Unreal includes, no exceptions, no RTTI, no allocation
// in the per-island path. Replayed against census_budget_parity.txt (written by Python).
#pragma once

#include <algorithm>
#include <cstdint>
#include <vector>

namespace DaedalusCensusBudget {

constexpr std::uint64_t BaseRamKiB = 16384;
constexpr std::uint64_t PerAssetRamKiB = 24;
constexpr std::uint64_t BaseDiskKiB = 4096;
constexpr std::uint64_t PerAssetDiskKiB = 96;
constexpr std::uint64_t MaxKiB = 100000000;
constexpr std::uint64_t DefaultRamBudgetKiB = 40000;
constexpr std::uint64_t DefaultDiskBudgetKiB = 32768;
constexpr std::uint64_t DefaultWarnPermille = 900;
// Python ints are unbounded; the port refuses counts above this so every product fits in 64 bits.
constexpr std::uint64_t MaxAssetDefinitions = 1000000000000ULL;

enum Flag : unsigned { RamOver = 1u, DiskOver = 2u, RamNear = 4u, DiskNear = 8u };
enum class Beacon { Green, Amber, Red };

struct Budget {
    std::uint64_t RamKiB = DefaultRamBudgetKiB;
    std::uint64_t DiskKiB = DefaultDiskBudgetKiB;
    std::uint64_t WarnPermille = DefaultWarnPermille;
};

struct IslandCost {
    std::uint64_t RamKiB = 0;
    std::uint64_t DiskKiB = 0;
};

struct IslandVerdict {
    IslandCost Cost;
    unsigned Flags = 0;
    Beacon Colour = Beacon::Green;
};

struct WorldVerdict {
    std::uint64_t TotalRamKiB = 0;
    std::uint64_t TotalDiskKiB = 0;
    bool FitsAllResident = true;
    std::uint64_t MaxResident = 0;
    std::uint64_t Green = 0, Amber = 0, Red = 0;
};

// load_budget's range checks; false = the Python tool would refuse the config.
inline bool ValidBudget(const Budget& B) {
    return B.RamKiB >= 1 && B.RamKiB <= MaxKiB && B.DiskKiB >= 1 && B.DiskKiB <= MaxKiB &&
           B.WarnPermille >= 1 && B.WarnPermille <= 1000;
}

// island_cost; false = count out of the port's range.
inline bool CostOf(std::uint64_t AssetDefinitions, IslandCost& Out) {
    if (AssetDefinitions > MaxAssetDefinitions) return false;
    Out.RamKiB = BaseRamKiB + AssetDefinitions * PerAssetRamKiB;
    Out.DiskKiB = BaseDiskKiB + AssetDefinitions * PerAssetDiskKiB;
    return true;
}

// beacon(): over flags first; near flags only when nothing is over.
inline IslandVerdict Judge(const IslandCost& C, const Budget& B) {
    IslandVerdict V;
    V.Cost = C;
    if (C.RamKiB > B.RamKiB) V.Flags |= RamOver;
    if (C.DiskKiB > B.DiskKiB) V.Flags |= DiskOver;
    if (V.Flags == 0) {
        if (C.RamKiB * 1000 > B.RamKiB * B.WarnPermille) V.Flags |= RamNear;
        if (C.DiskKiB * 1000 > B.DiskKiB * B.WarnPermille) V.Flags |= DiskNear;
    }
    V.Colour = (V.Flags & (RamOver | DiskOver)) ? Beacon::Red : (V.Flags ? Beacon::Amber : Beacon::Green);
    return V;
}

// max_resident: lightest first is optimal for a count.
inline std::uint64_t MaxResident(std::vector<std::uint64_t> Rams, std::uint64_t RamBudget) {
    std::sort(Rams.begin(), Rams.end());
    std::uint64_t Total = 0, Count = 0;
    for (std::uint64_t R : Rams) {
        if (Total + R > RamBudget) break;
        Total += R;
        ++Count;
    }
    return Count;
}

// One world of plan(); Islands receives one verdict per count, in the given (slot) order.
inline bool PlanWorld(const std::vector<std::uint64_t>& AssetCounts, const Budget& B, WorldVerdict& Out,
                      std::vector<IslandVerdict>& Islands) {
    if (!ValidBudget(B)) return false;
    Out = WorldVerdict{};
    Islands.clear();
    std::vector<std::uint64_t> Rams;
    Rams.reserve(AssetCounts.size());
    for (std::uint64_t N : AssetCounts) {
        IslandCost C;
        if (!CostOf(N, C)) return false;
        const IslandVerdict V = Judge(C, B);
        Islands.push_back(V);
        Rams.push_back(C.RamKiB);
        Out.TotalRamKiB += C.RamKiB;
        Out.TotalDiskKiB += C.DiskKiB;
        (V.Colour == Beacon::Red ? Out.Red : V.Colour == Beacon::Amber ? Out.Amber : Out.Green) += 1;
    }
    Out.FitsAllResident = Out.TotalRamKiB <= B.RamKiB && Out.TotalDiskKiB <= B.DiskKiB;
    Out.MaxResident = MaxResident(Rams, B.RamKiB);
    return true;
}

inline const char* BeaconName(Beacon C) {
    return C == Beacon::Red ? "red" : C == Beacon::Amber ? "amber" : "green";
}

}  // namespace DaedalusCensusBudget
