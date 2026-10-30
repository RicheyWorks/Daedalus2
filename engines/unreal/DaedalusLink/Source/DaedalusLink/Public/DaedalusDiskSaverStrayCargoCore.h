// SPDX-License-Identifier: MIT
// G531 Stray Cargo (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/stray_cargo.py survey(): census assets the G206 pricing never sees
// (stray, dangling, duplicate names, count mismatches, empty hulls, shared files, worlds
// without a realm), sorted exactly like Python (kind order, world, then the finding's
// json.dumps text via DaedalusDiskSaverPyJsonCore.h), counts, hidden costs and verdict.
// Costs use the G206 constants in DaedalusCensusBudgetCore.h.
// Left in Python: JSON loading, format/version checks, values that are not null, ints,
// strings or bools (floats, lists), text output and the CLI. World ids are bytes; blank
// means ASCII whitespace only. No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusCensusBudgetCore.h"
#include "DaedalusDiskSaverCensusPlanCore.h"
#include "DaedalusDiskSaverPyJsonCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace StrayCargo {

namespace CB = ::DaedalusCensusBudget;

constexpr std::size_t MaxWorlds = 100000;
constexpr std::size_t MaxRows = 1000000;  // islands plus assets over the census
constexpr std::size_t MaxText = 65536;    // bytes per name or file

enum class Error { None, NoWorlds, WorldId, BadIsland, BadAsset, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::NoWorlds: return "no_worlds";
        case Error::WorldId: return "world_id";
        case Error::BadIsland: return "bad_island";
        case Error::BadAsset: return "bad_asset";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

// A JSON scalar from the census: null, int, str or bool.
struct Value {
    enum Kind { Null, Int, Str, Bool } K = Null;
    long long I = 0;
    std::string S;
    bool B = false;
    std::string Json() const {
        return K == Null ? PyJson::Null() : K == Int ? PyJson::Int(I) : K == Str ? PyJson::Str(S) : PyJson::Bool(B);
    }
};

struct Island {
    bool SlotIsInt = true;
    long long Slot = 0;
    bool HasAssets = false;  // asset_definitions present (an int)
    long long Assets = 0;
};

struct Asset {
    bool NameIsStr = true;
    std::string Name;
    Value Slot, File;
};

struct World {
    std::string Id;
    bool HasRealm = false;
    bool HasClaimed = false;
    long long Claimed = 0;
    std::vector<Island> Islands;
    std::vector<Asset> Assets;
};

// ERRORS then ADVISORIES, in Python's order.
enum Kind { Dangling, DuplicateName, CountMismatch, Stray, EmptyHull, SharedFile, NoRealm, KindCount };

inline const char* KindName(int K) {
    static const char* const N[KindCount] = {"dangling", "duplicate_name", "count_mismatch", "stray", "empty_hull", "shared_file", "no_realm"};
    return K >= 0 && K < KindCount ? N[K] : "?";
}

struct Finding {
    int K = 0;
    bool HasWorld = true;
    std::string World;
    std::string Json;  // json.dumps(finding, sort_keys=True)
};

struct Result {
    std::vector<Finding> Findings;
    std::uint64_t Counts[KindCount] = {0, 0, 0, 0, 0, 0, 0};
    std::uint64_t HiddenRam = 0, HiddenDisk = 0, EmptyHullRam = 0, SharedDisk = 0;
    int Verdict = 0;  // 0 tidy, 1 littered, 2 adrift
};

inline const char* VerdictName(int V) { return V == 2 ? "adrift" : V == 1 ? "littered" : "tidy"; }

inline Error Survey(const std::vector<World>& In, Result& Out) {
    Out = Result{};
    if (In.empty()) return Error::NoWorlds;
    if (In.size() > MaxWorlds) return Error::Capacity;
    std::size_t Rows = 0;
    std::set<std::string> Seen;
    std::map<std::string, std::set<std::string>> Files;
    std::vector<Finding> F;
    auto Add = [&](int K, const std::string& W, PyJson::Object O) {
        O.Add("kind", PyJson::Str(KindName(K))).Add("world", PyJson::Str(W));
        F.push_back(Finding{K, true, W, O.Dump()});
    };
    for (const World& W : In) {
        if (W.Id.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (W.Id.empty() || CensusPlan::Blank(W.Id) || !Seen.insert(W.Id).second) return Error::WorldId;
        Rows += W.Islands.size() + W.Assets.size();
        if (Rows > MaxRows) return Error::Capacity;
        std::map<long long, const Island*> Slots;  // later islands win, like the dict
        for (const Island& I : W.Islands) {
            if (!I.SlotIsInt) return Error::BadIsland;
            Slots[I.Slot] = &I;
        }
        if (!W.HasRealm) Add(NoRealm, W.Id, PyJson::Object{});
        for (const auto& KV : Slots)
            if (KV.second->HasAssets && KV.second->Assets == 0)
                Add(EmptyHull, W.Id, PyJson::Object{}
                                         .Add("slot", PyJson::Int(KV.first))
                                         .Add("ram_kib", PyJson::Int(static_cast<long long>(CB::BaseRamKiB)))
                                         .Add("disk_kib", PyJson::Int(static_cast<long long>(CB::BaseDiskKiB))));
        std::map<std::string, std::uint64_t> Names;
        std::uint64_t Strays = 0;
        for (const Asset& A : W.Assets) {
            if (!A.NameIsStr) return Error::BadAsset;
            if (A.Name.size() > MaxText || A.File.S.size() > MaxText || A.Slot.S.size() > MaxText) return Error::Capacity;
            ++Names[A.Name];
            if (A.File.K == Value::Str && !A.File.S.empty()) Files[A.File.S].insert(W.Id);
            if (A.Slot.K == Value::Null) {
                ++Strays;
                Add(Stray, W.Id, PyJson::Object{}
                                     .Add("asset", PyJson::Str(A.Name))
                                     .Add("file", A.File.Json())
                                     .Add("ram_kib", PyJson::Int(static_cast<long long>(CB::PerAssetRamKiB)))
                                     .Add("disk_kib", PyJson::Int(static_cast<long long>(CB::PerAssetDiskKiB))));
            } else if (A.Slot.K != Value::Int || !Slots.count(A.Slot.I)) {
                Add(Dangling, W.Id, PyJson::Object{}.Add("asset", PyJson::Str(A.Name)).Add("slot", A.Slot.Json()));
            }
        }
        for (const auto& KV : Names)
            if (KV.second > 1)
                Add(DuplicateName, W.Id, PyJson::Object{}.Add("asset", PyJson::Str(KV.first)).Add("count", PyJson::Int(static_cast<long long>(KV.second))));
        if (W.HasClaimed && (W.Claimed < 0 || static_cast<std::uint64_t>(W.Claimed) != Strays))
            Add(CountMismatch, W.Id, PyJson::Object{}.Add("claimed", PyJson::Int(W.Claimed)).Add("found", PyJson::Int(static_cast<long long>(Strays))));
    }
    for (const auto& KV : Files) {
        if (KV.second.size() < 2) continue;
        std::vector<std::string> Ws;
        for (const std::string& W : KV.second) Ws.push_back(PyJson::Str(W));
        const long long Disk = static_cast<long long>((KV.second.size() - 1) * CB::PerAssetDiskKiB);
        PyJson::Object O;
        O.Add("world", PyJson::Null()).Add("kind", PyJson::Str("shared_file")).Add("file", PyJson::Str(KV.first))
            .Add("worlds", PyJson::List(Ws)).Add("disk_kib", PyJson::Int(Disk));
        F.push_back(Finding{SharedFile, false, std::string(), O.Dump()});
        Out.SharedDisk += static_cast<std::uint64_t>(Disk);
    }
    std::stable_sort(F.begin(), F.end(), [](const Finding& A, const Finding& B) {
        if (A.K != B.K) return A.K < B.K;
        if (A.World != B.World) return A.World < B.World;  // a missing world sorts as ""
        return A.Json < B.Json;
    });
    for (const Finding& X : F) {
        ++Out.Counts[X.K];
        if (X.K == Stray) {
            Out.HiddenRam += CB::PerAssetRamKiB;
            Out.HiddenDisk += CB::PerAssetDiskKiB;
        } else if (X.K == EmptyHull) {
            Out.EmptyHullRam += CB::BaseRamKiB;
        }
    }
    Out.Verdict = (Out.Counts[Dangling] || Out.Counts[DuplicateName] || Out.Counts[CountMismatch]) ? 2 : F.empty() ? 0 : 1;
    Out.Findings = F;
    return Error::None;
}

}  // namespace StrayCargo
}  // namespace DaedalusDiskSaver
