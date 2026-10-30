// SPDX-License-Identifier: MIT
// G505 Beacon Watch (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/beacon_watch.py: read_report's field checks on parsed reports, the
// findings (world_gone/new, spill/unspill, max_resident_drop, island worse/better/new/
// new_hot/gone) in Python's order, counts, regressions and the storm/calm verdict.
// Reports can come from a census priced with the G206 port (DaedalusDiskSaverCensusPlanCore.h).
// Left in Python: JSON loading, format/version checks, budget_changed/cost_model_changed
// (dict compares of JSON) and the CLI. No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusDiskSaverCensusPlanCore.h"

#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace BeaconWatch {

constexpr std::size_t MaxWorlds = 100000;
constexpr std::size_t MaxIslands = 1000000;  // per report
constexpr long long MaxResidentCap = 1000000000000LL;

enum class Error { None, WorldId, DuplicateWorld, Fits, MaxResident, Beacon, DuplicateSlot, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::WorldId: return "world_id";
        case Error::DuplicateWorld: return "duplicate_world";
        case Error::Fits: return "fits";
        case Error::MaxResident: return "max_resident";
        case Error::Beacon: return "beacon";
        case Error::DuplicateSlot: return "duplicate_slot";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

struct RIsland {
    std::uint64_t Slot = 0;
    std::string Beacon;  // checked against green/amber/red
};

struct RWorld {
    std::string Id;
    int Fits = 1;            // 1 true, 0 false, anything else = not a bool
    long long MaxResident = 0;
    std::vector<RIsland> Islands;
};

struct Finding {
    std::string World;
    long long Slot = -1;  // -1 = world level
    std::string Kind, Before, After;
    bool Fails = false;
};

struct Verdict {
    bool Storm = false;
    std::uint64_t Regressions = 0;
    std::map<std::string, std::uint64_t> Counts;
    std::vector<Finding> Findings;
};

inline int Rank(const std::string& B) { return B == "green" ? 0 : B == "amber" ? 1 : B == "red" ? 2 : -1; }

inline std::vector<RWorld> FromCensus(const CensusPlan::Report& R) {
    std::vector<RWorld> Out;
    for (const CensusPlan::World& W : R.Worlds) {
        RWorld O;
        O.Id = W.Id;
        O.Fits = W.V.FitsAllResident ? 1 : 0;
        O.MaxResident = static_cast<long long>(W.V.MaxResident);
        for (const CensusPlan::Island& I : W.Islands) O.Islands.push_back(RIsland{I.Slot, CensusPlan::CB::BeaconName(I.V.Colour)});
        Out.push_back(O);
    }
    return Out;
}

struct Parsed {
    bool Fits = false;
    long long MaxResident = 0;
    std::map<std::uint64_t, int> Slots;
};

// read_report(): checks in Python's order, worlds in file order.
inline Error Read(const std::vector<RWorld>& In, std::map<std::string, Parsed>& Out) {
    Out.clear();
    if (In.size() > MaxWorlds) return Error::Capacity;
    std::size_t Total = 0;
    for (const RWorld& W : In) {
        if (W.Id.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (W.Id.empty() || CensusPlan::Blank(W.Id)) return Error::WorldId;
        if (Out.count(W.Id)) return Error::DuplicateWorld;
        if (W.Fits != 0 && W.Fits != 1) return Error::Fits;
        if (W.MaxResident < 0 || W.MaxResident > MaxResidentCap) return Error::MaxResident;
        Total += W.Islands.size();
        if (Total > MaxIslands) return Error::Capacity;
        Parsed P;
        P.Fits = W.Fits == 1;
        P.MaxResident = W.MaxResident;
        for (const RIsland& I : W.Islands) {
            const int R = Rank(I.Beacon);
            if (R < 0) return Error::Beacon;
            if (P.Slots.count(I.Slot)) return Error::DuplicateSlot;
            P.Slots[I.Slot] = R;
        }
        Out[W.Id] = P;
    }
    return Error::None;
}

inline const char* RankName(int R) { return R == 0 ? "green" : R == 1 ? "amber" : "red"; }

inline bool IsWorse(const std::string& K) { return K == "worse" || K == "new_hot" || K == "spill" || K == "max_resident_drop"; }

// watch(): baseline is read before current; BadSide = 0 baseline, 1 current on error.
inline Error Watch(const std::vector<RWorld>& BaseIn, const std::vector<RWorld>& CurIn, Verdict& V, int& BadSide) {
    V = Verdict{};
    BadSide = 0;
    std::map<std::string, Parsed> Base, Cur;
    Error E = Read(BaseIn, Base);
    if (E != Error::None) return E;
    BadSide = 1;
    E = Read(CurIn, Cur);
    if (E != Error::None) return E;
    BadSide = -1;
    std::set<std::string> Ids;
    for (const auto& KV : Base) Ids.insert(KV.first);
    for (const auto& KV : Cur) Ids.insert(KV.first);
    auto Add = [&](const std::string& W, long long S, const char* K, const std::string& B, const std::string& A) {
        V.Findings.push_back(Finding{W, S, K, B, A, IsWorse(K)});
    };
    for (const std::string& Id : Ids) {
        const auto C = Cur.find(Id);
        if (C == Cur.end()) {
            Add(Id, -1, "world_gone", "present", "absent");
            continue;
        }
        const auto B = Base.find(Id);
        static const std::map<std::uint64_t, int> NoSlots;
        const std::map<std::uint64_t, int>* BSlots = &NoSlots;
        if (B == Base.end()) {
            Add(Id, -1, "world_new", "absent", "present");
        } else {
            BSlots = &B->second.Slots;
            if (B->second.Fits && !C->second.Fits) Add(Id, -1, "spill", "fits", "spills");
            else if (C->second.Fits && !B->second.Fits) Add(Id, -1, "unspill", "spills", "fits");
            if (C->second.MaxResident < B->second.MaxResident)
                Add(Id, -1, "max_resident_drop", std::to_string(B->second.MaxResident), std::to_string(C->second.MaxResident));
        }
        std::set<std::uint64_t> Slots;
        for (const auto& KV : *BSlots) Slots.insert(KV.first);
        for (const auto& KV : C->second.Slots) Slots.insert(KV.first);
        for (std::uint64_t S : Slots) {
            const auto Bi = BSlots->find(S);
            const auto Ci = C->second.Slots.find(S);
            const long long SS = static_cast<long long>(S);
            if (Ci == C->second.Slots.end()) Add(Id, SS, "gone", RankName(Bi->second), "absent");
            else if (Bi == BSlots->end()) Add(Id, SS, Ci->second ? "new_hot" : "new", "absent", RankName(Ci->second));
            else if (Ci->second > Bi->second) Add(Id, SS, "worse", RankName(Bi->second), RankName(Ci->second));
            else if (Ci->second < Bi->second) Add(Id, SS, "better", RankName(Bi->second), RankName(Ci->second));
        }
    }
    for (const Finding& F : V.Findings) {
        ++V.Counts[F.Kind];
        V.Regressions += F.Fails ? 1 : 0;
    }
    V.Storm = V.Regressions > 0;
    return Error::None;
}

}  // namespace BeaconWatch
}  // namespace DaedalusDiskSaver
