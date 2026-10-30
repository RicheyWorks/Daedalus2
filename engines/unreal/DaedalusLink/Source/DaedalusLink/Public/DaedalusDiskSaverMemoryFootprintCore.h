// SPDX-License-Identifier: MIT
// G519 Memory Footprint Report (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/memory_footprint.py build(): permille, per-world totals and top islands,
// fleet top consumers, the ranked unload/trim wins (with "clears"), and the
// light/laden/overladen verdict. A census priced with the G206 port
// (DaedalusDiskSaverCensusPlanCore.h) or a parsed G206 report can be the input.
// Left in Python: tool_footprint (reading the tools folder), JSON loading and schema checks,
// text output and the CLI. No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusDiskSaverCensusPlanCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace MemoryFootprint {

namespace CB = ::DaedalusCensusBudget;

constexpr std::size_t MaxWorlds = 100000;
constexpr std::size_t MaxIslands = 1000000;
constexpr long long MaxValue = 10000000000000LL;   // 10^13 KiB or assets per field
constexpr long long MaxTotal = 4000000000000000LL;  // every sum stays <= 4*10^15, so x1000 fits in 64 bits

enum class Error { None, TopWins, Negative, BudgetPositive, WorldId, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::TopWins: return "top_wins";
        case Error::Negative: return "negative";
        case Error::BudgetPositive: return "budget_positive";
        case Error::WorldId: return "world_id";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

struct Island {
    long long Slot = 0, RamKiB = 0, DiskKiB = 0, Assets = 0;
};

struct ReportWorld {
    std::string Id;
    std::vector<Island> Islands;
};

struct Report {
    long long RamBudget = 0, DiskBudget = 0, Warn = 0;
    std::vector<ReportWorld> Worlds;
};

inline Report FromCensus(const CensusPlan::Report& R) {
    Report Out;
    Out.RamBudget = static_cast<long long>(R.B.RamKiB);
    Out.DiskBudget = static_cast<long long>(R.B.DiskKiB);
    Out.Warn = static_cast<long long>(R.B.WarnPermille);
    for (const CensusPlan::World& W : R.Worlds) {
        ReportWorld O;
        O.Id = W.Id;
        for (const CensusPlan::Island& I : W.Islands)
            O.Islands.push_back(Island{static_cast<long long>(I.Slot), static_cast<long long>(I.V.Cost.RamKiB),
                                       static_cast<long long>(I.V.Cost.DiskKiB), static_cast<long long>(I.Assets)});
        Out.Worlds.push_back(O);
    }
    return Out;
}

inline long long Permille(long long X, long long Budget) { return X * 1000 / Budget; }

struct TopIsland {
    long long Slot = 0, RamKiB = 0, DiskKiB = 0, SharePermille = 0;
};

struct WorldRow {
    std::string Id;
    long long RamKiB = 0, DiskKiB = 0, RamPermille = 0, DiskPermille = 0;
    bool Over = false;
    std::size_t Islands = 0;
    std::vector<TopIsland> Top;
};

struct Consumer {
    std::string World;
    long long Slot = 0, RamKiB = 0, DiskKiB = 0;
};

struct Win {
    std::string World;
    long long Slot = 0;
    bool Trim = false;  // "trim" sorts before "unload"
    long long RamFree = 0, DiskFree = 0;
    bool WorldOver = false, Clears = false;
};

struct Result {
    std::vector<WorldRow> Worlds;
    std::size_t IslandCount = 0;
    long long RamKiB = 0, DiskKiB = 0, Peak = 0;
    std::vector<Consumer> TopConsumers;
    std::vector<Win> Wins;
    int Verdict = 0;  // 0 light, 1 laden, 2 overladen
};

inline const char* VerdictName(int V) { return V == 2 ? "overladen" : V == 1 ? "laden" : "light"; }

inline Error Build(const Report& R, long long Top, long long Wins, Result& Out) {
    Out = Result{};
    if (Top < 1 || Wins < 1) return Error::TopWins;
    if (R.RamBudget < 0 || R.DiskBudget < 0 || R.Warn < 0) return Error::Negative;
    if (R.RamBudget == 0 || R.DiskBudget == 0) return Error::BudgetPositive;
    if (R.RamBudget > MaxValue || R.DiskBudget > MaxValue || R.Worlds.size() > MaxWorlds) return Error::Capacity;
    std::set<std::string> Seen;
    std::vector<Consumer> Everyone;
    std::vector<Win> Cand;
    std::size_t Count = 0;
    long long AllRam = 0, AllDisk = 0;
    for (const ReportWorld& W : R.Worlds) {
        if (W.Id.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (W.Id.empty() || CensusPlan::Blank(W.Id) || !Seen.insert(W.Id).second) return Error::WorldId;
        Count += W.Islands.size();
        if (Count > MaxIslands) return Error::Capacity;
        long long Ram = 0, Disk = 0;
        for (const Island& I : W.Islands) {
            if (I.Slot < 0 || I.RamKiB < 0 || I.DiskKiB < 0 || I.Assets < 0) return Error::Negative;
            if (I.Slot > MaxValue || I.RamKiB > MaxValue || I.DiskKiB > MaxValue || I.Assets > MaxValue) return Error::Capacity;
            Ram += I.RamKiB;
            Disk += I.DiskKiB;
            AllRam += I.RamKiB;
            AllDisk += I.DiskKiB;
            if (AllRam > MaxTotal || AllDisk > MaxTotal || I.Assets * static_cast<long long>(CB::PerAssetDiskKiB) > MaxTotal)
                return Error::Capacity;
        }
        WorldRow Row;
        Row.Id = W.Id;
        Row.RamKiB = Ram;
        Row.DiskKiB = Disk;
        Row.RamPermille = Permille(Ram, R.RamBudget);
        Row.DiskPermille = Permille(Disk, R.DiskBudget);
        Row.Over = Row.RamPermille > 1000 || Row.DiskPermille > 1000;
        Row.Islands = W.Islands.size();
        std::vector<Island> Ranked = W.Islands;
        std::stable_sort(Ranked.begin(), Ranked.end(), [](const Island& A, const Island& B) {
            if (A.RamKiB != B.RamKiB) return A.RamKiB > B.RamKiB;
            if (A.DiskKiB != B.DiskKiB) return A.DiskKiB > B.DiskKiB;
            return A.Slot < B.Slot;
        });
        for (std::size_t K = 0; K < Ranked.size() && static_cast<long long>(K) < Top; ++K)
            Row.Top.push_back(TopIsland{Ranked[K].Slot, Ranked[K].RamKiB, Ranked[K].DiskKiB, Ram ? Permille(Ranked[K].RamKiB, Ram) : 0});
        for (const Island& I : W.Islands) {
            Everyone.push_back(Consumer{W.Id, I.Slot, I.RamKiB, I.DiskKiB});
            Win U{W.Id, I.Slot, false, I.RamKiB, I.DiskKiB, Row.Over, false};
            U.Clears = Row.Over && Ram - U.RamFree <= R.RamBudget && Disk - U.DiskFree <= R.DiskBudget;
            Cand.push_back(U);
            if (I.Assets) {
                Win T{W.Id, I.Slot, true, I.Assets * static_cast<long long>(CB::PerAssetRamKiB),
                      I.Assets * static_cast<long long>(CB::PerAssetDiskKiB), Row.Over, false};
                T.Clears = Row.Over && Ram - T.RamFree <= R.RamBudget && Disk - T.DiskFree <= R.DiskBudget;
                Cand.push_back(T);
            }
        }
        Out.Worlds.push_back(Row);
    }
    std::stable_sort(Cand.begin(), Cand.end(), [](const Win& A, const Win& B) {
        if (A.WorldOver != B.WorldOver) return A.WorldOver;
        if (A.Clears != B.Clears) return A.Clears;
        if (A.RamFree != B.RamFree) return A.RamFree > B.RamFree;
        if (A.DiskFree != B.DiskFree) return A.DiskFree > B.DiskFree;
        if (A.World != B.World) return A.World < B.World;
        if (A.Slot != B.Slot) return A.Slot < B.Slot;
        return A.Trim && !B.Trim;
    });
    auto Peak = [](const WorldRow& W) { return std::max(W.RamPermille, W.DiskPermille); };
    std::stable_sort(Out.Worlds.begin(), Out.Worlds.end(), [&](const WorldRow& A, const WorldRow& B) {
        if (Peak(A) != Peak(B)) return Peak(A) > Peak(B);
        return A.Id < B.Id;
    });
    bool AnyOver = false;
    for (const WorldRow& W : Out.Worlds) {
        Out.Peak = std::max(Out.Peak, Peak(W));
        AnyOver = AnyOver || W.Over;
        Out.RamKiB += W.RamKiB;
        Out.DiskKiB += W.DiskKiB;
    }
    Out.Verdict = AnyOver ? 2 : Out.Peak >= R.Warn ? 1 : 0;
    Out.IslandCount = Everyone.size();
    std::stable_sort(Everyone.begin(), Everyone.end(), [](const Consumer& A, const Consumer& B) {
        if (A.RamKiB != B.RamKiB) return A.RamKiB > B.RamKiB;
        if (A.DiskKiB != B.DiskKiB) return A.DiskKiB > B.DiskKiB;
        if (A.World != B.World) return A.World < B.World;
        return A.Slot < B.Slot;
    });
    for (std::size_t K = 0; K < Everyone.size() && static_cast<long long>(K) < Top; ++K) Out.TopConsumers.push_back(Everyone[K]);
    for (std::size_t K = 0; K < Cand.size() && static_cast<long long>(K) < Wins; ++K) Out.Wins.push_back(Cand[K]);
    return Error::None;
}

}  // namespace MemoryFootprint
}  // namespace DaedalusDiskSaver
