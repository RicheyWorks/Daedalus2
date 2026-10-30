// SPDX-License-Identifier: MIT
// G533 Fleet Flags (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/fleet_flags.py: the G206 report (through DaedalusDiskSaverCensusPlanCore.h)
// rolled up by realm (unrealmed first, then realm ids in order), beacon counts, spilling
// worlds, heaviest world, the realm flag, the census realms[] tally check (including
// missing rows) and the fair/signal/distress verdict.
// Left in Python: JSON loading, the realms[] row shape checks, claimed values that are not
// integers, text output and the CLI. Realm ids are bytes; blank means ASCII whitespace only.
// No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusDiskSaverCensusPlanCore.h"

#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace FleetFlags {

namespace CB = ::DaedalusCensusBudget;

constexpr std::size_t MaxClaims = 100000;
constexpr long long MaxWorldAssets = 1000000000000LL;  // world-level asset_definitions (summed per realm)

enum class Error { None, Census, Realm, Capacity };

// A realm id: null (unrealmed) or a string; RealmKey orders null first, like _rkey.
using RealmKey = std::pair<bool, std::string>;

struct World {
    CensusPlan::InWorld W;
    int RealmKind = 0;  // 0 null/absent, 1 string, 2 not a string
    std::string Realm;
    bool HasAssets = false;
    long long Assets = 0;  // world-level asset_definitions
};

struct Claim {
    RealmKey Id;
    bool Has[3] = {false, false, false};  // worlds, islands, asset_definitions
    long long Value[3] = {0, 0, 0};
};

struct Realm {
    RealmKey Id;
    std::uint64_t Worlds = 0, Islands = 0, Assets = 0, RamKiB = 0, DiskKiB = 0, Green = 0, Amber = 0, Red = 0, Spilling = 0;
    std::string Heaviest;
    std::uint64_t HeavyRam = 0, HeavyDisk = 0;
    int Flag = 0;  // 0 green, 1 amber, 2 red
};

struct Mismatch {
    RealmKey Id;
    std::string Field;
    bool HasClaimed = false;
    long long Claimed = 0, Found = 0;
};

enum class Signal { Fair, Signal, Distress };

inline const char* SignalName(Signal S) { return S == Signal::Fair ? "fair" : S == Signal::Signal ? "signal" : "distress"; }
inline const char* FlagName(int F) { return F == 2 ? "red" : F == 1 ? "amber" : "green"; }

struct Result {
    std::vector<Realm> Realms;
    std::vector<Mismatch> Mismatches;
    Signal Verdict = Signal::Fair;
};

// muster(): price the census, check realm ids in file order, roll up, then check the claims (if any).
inline Error Muster(const std::vector<World>& In, const CB::Budget& B, bool HasClaims, const std::vector<Claim>& Claims,
                    Result& Out, CensusPlan::Error& CensusError) {
    Out = Result{};
    std::vector<CensusPlan::InWorld> Census;
    for (const World& W : In) Census.push_back(W.W);
    CensusPlan::Report Rep;
    CensusError = CensusPlan::Plan(Census, B, Rep);
    if (CensusError != CensusPlan::Error::None) return Error::Census;
    if (Claims.size() > MaxClaims || Claims.size() * In.size() > 100000000) return Error::Capacity;
    std::map<std::string, RealmKey> RealmOf;
    for (const World& W : In) {
        if (W.RealmKind == 2 || (W.RealmKind == 1 && CensusPlan::Blank(W.Realm))) return Error::Realm;
        if (W.Realm.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (W.HasAssets && (W.Assets < 0 || W.Assets > MaxWorldAssets)) return Error::Capacity;
        RealmOf[W.W.Id] = RealmKey{W.RealmKind == 1, W.RealmKind == 1 ? W.Realm : std::string()};
    }
    std::map<RealmKey, Realm> Realms;
    for (const CensusPlan::World& W : Rep.Worlds) {
        const RealmKey K = RealmOf[W.Id];
        Realm& G = Realms[K];
        G.Id = K;
        ++G.Worlds;
        G.Islands += W.Islands.size();
        for (const CensusPlan::Island& I : W.Islands) G.Assets += I.Assets;
        G.RamKiB += W.V.TotalRamKiB;
        G.DiskKiB += W.V.TotalDiskKiB;
        G.Green += W.V.Green;
        G.Amber += W.V.Amber;
        G.Red += W.V.Red;
        G.Spilling += W.V.FitsAllResident ? 0 : 1;
        // key (-ram, -disk, id): most RAM, then most disk, then the smallest id
        const bool Heavier = G.Worlds == 1 || W.V.TotalRamKiB > G.HeavyRam ||
                             (W.V.TotalRamKiB == G.HeavyRam &&
                              (W.V.TotalDiskKiB > G.HeavyDisk || (W.V.TotalDiskKiB == G.HeavyDisk && W.Id < G.Heaviest)));
        if (Heavier) {
            G.Heaviest = W.Id;
            G.HeavyRam = W.V.TotalRamKiB;
            G.HeavyDisk = W.V.TotalDiskKiB;
        }
    }
    int Worst = 0;
    for (auto& KV : Realms) {
        Realm& G = KV.second;
        G.Flag = (G.Red || G.Spilling) ? 2 : G.Amber ? 1 : 0;
        Worst = G.Flag > Worst ? G.Flag : Worst;
        Out.Realms.push_back(G);
    }
    if (HasClaims) {
        static const char* const Fields[3] = {"worlds", "islands", "asset_definitions"};
        std::set<RealmKey> Seen;
        for (const Claim& C : Claims) {
            Seen.insert(C.Id);
            const auto Mine = Realms.find(C.Id);
            for (int F = 0; F < 3; ++F) {
                if (!C.Has[F]) continue;
                long long Have = 0;
                if (F == 2) {
                    for (const World& W : In)
                        if (RealmOf[W.W.Id] == C.Id && W.HasAssets) Have += W.Assets;
                } else if (Mine != Realms.end()) {
                    Have = static_cast<long long>(F == 0 ? Mine->second.Worlds : Mine->second.Islands);
                }
                if (C.Value[F] != Have) Out.Mismatches.push_back(Mismatch{C.Id, Fields[F], true, C.Value[F], Have});
            }
        }
        for (const auto& KV : Realms)
            if (!Seen.count(KV.first))
                Out.Mismatches.push_back(Mismatch{KV.first, "missing_row", false, 0, static_cast<long long>(KV.second.Worlds)});
    }
    Out.Verdict = Worst == 2 ? Signal::Distress : Worst == 1 ? Signal::Signal : Signal::Fair;
    return Error::None;
}

}  // namespace FleetFlags
}  // namespace DaedalusDiskSaver
