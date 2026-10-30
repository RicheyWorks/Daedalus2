// SPDX-License-Identifier: MIT
// G517 Budget Trend Ledger (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/budget_ledger.py: make_record (the timestamp `at` is an input),
// dumps_line (compact sorted JSON through DaedalusDiskSaverPyJsonCore.h), diff (deltas,
// appeared/dropped/newly_over/back_under/beacon findings, worse/steady) and trend (last N
// runs, growing/shrinking/flat, rising/ebbing/steady). A census priced with the G206 port
// (DaedalusDiskSaverCensusPlanCore.h) or a parsed G206 report can be the input.
// Left in Python: reading and appending the ledger file (read_ledger/append, duplicate
// runs in the file), --from/--to picking, JSON loading, budget values that are not ints
// or null, text output and the CLI. No Unreal includes, no exceptions, no RTTI.
#pragma once

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
namespace BudgetLedger {

constexpr std::size_t MaxWorlds = 100000;
constexpr std::size_t MaxIslands = 1000000;
constexpr long long MaxKiB = 1000000000000000LL;  // per world total; deltas stay in 64 bits
constexpr long long MaxSlot = 1000000000000000LL;
constexpr std::size_t MaxRuns = 100000;
constexpr std::size_t MaxText = 65536;

enum class Error { None, Run, At, WorldId, Negative, BeaconSlot, Fits, Last, Empty, Capacity };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::Run: return "run";
        case Error::At: return "at";
        case Error::WorldId: return "world_id";
        case Error::Negative: return "negative";
        case Error::BeaconSlot: return "beacon_slot";
        case Error::Fits: return "fits";
        case Error::Last: return "last";
        case Error::Empty: return "empty";
        case Error::Capacity: return "capacity";
    }
    return "?";
}

// Optional int budget field: absent and null both write null.
struct MaybeInt {
    bool Has = false;
    long long V = 0;
    std::string Json() const { return Has ? PyJson::Int(V) : PyJson::Null(); }
};

struct RIsland {
    long long Slot = 0;
    std::string Beacon;
};

struct RWorld {
    std::string Id;
    int Fits = 1;  // 1 true, 0 false, else not a bool
    long long RamKiB = 0, DiskKiB = 0;
    std::vector<RIsland> Islands;
};

struct Report {
    MaybeInt Budget[3];  // ram_budget_kib, disk_budget_kib, warn_permille
    std::vector<RWorld> Worlds;
};

inline Report FromCensus(const CensusPlan::Report& R) {
    Report Out;
    Out.Budget[0] = MaybeInt{true, static_cast<long long>(R.B.RamKiB)};
    Out.Budget[1] = MaybeInt{true, static_cast<long long>(R.B.DiskKiB)};
    Out.Budget[2] = MaybeInt{true, static_cast<long long>(R.B.WarnPermille)};
    for (const CensusPlan::World& W : R.Worlds) {
        RWorld O;
        O.Id = W.Id;
        O.Fits = W.V.FitsAllResident ? 1 : 0;
        O.RamKiB = static_cast<long long>(W.V.TotalRamKiB);
        O.DiskKiB = static_cast<long long>(W.V.TotalDiskKiB);
        for (const CensusPlan::Island& I : W.Islands) O.Islands.push_back(RIsland{static_cast<long long>(I.Slot), CensusPlan::CB::BeaconName(I.V.Colour)});
        Out.Worlds.push_back(O);
    }
    return Out;
}

struct WorldRec {
    long long RamKiB = 0, DiskKiB = 0;
    bool Fits = true, Over = false;
    std::map<std::string, std::string> Beacons;  // str(slot) -> beacon, sorted like sort_keys
};

struct Record {
    std::string Run;
    bool HasAt = false;
    std::string At;
    MaybeInt Budget[3];
    std::map<std::string, WorldRec> Worlds;
};

inline int Rank(const std::string& B) { return B == "green" ? 0 : B == "amber" ? 1 : B == "red" ? 2 : -1; }

// RunKind/AtKind: 0 null (at only), 1 string, 2 not a string.
inline Error MakeRecord(const Report& R, int RunKind, const std::string& Run, int AtKind, const std::string& At, Record& Out) {
    Out = Record{};
    if (RunKind != 1 || Run.empty() || CensusPlan::Blank(Run)) return Error::Run;
    if (AtKind == 2) return Error::At;
    if (Run.size() > MaxText || At.size() > MaxText || R.Worlds.size() > MaxWorlds) return Error::Capacity;
    Out.Run = Run;
    Out.HasAt = AtKind == 1;
    Out.At = Out.HasAt ? At : std::string();
    for (int K = 0; K < 3; ++K) Out.Budget[K] = R.Budget[K];
    std::size_t Count = 0;
    for (const RWorld& W : R.Worlds) {
        if (W.Id.size() > CensusPlan::MaxIdBytes) return Error::Capacity;
        if (W.Id.empty() || CensusPlan::Blank(W.Id) || Out.Worlds.count(W.Id)) return Error::WorldId;
        Count += W.Islands.size();
        if (Count > MaxIslands) return Error::Capacity;
        WorldRec Rec;
        bool Red = false;
        for (const RIsland& I : W.Islands) {
            if (I.Slot < 0) return Error::Negative;
            if (I.Slot > MaxSlot) return Error::Capacity;
            const std::string Key = std::to_string(I.Slot);
            if (Rank(I.Beacon) < 0 || Rec.Beacons.count(Key)) return Error::BeaconSlot;
            Rec.Beacons[Key] = I.Beacon;
            Red = Red || I.Beacon == "red";
        }
        if (W.Fits != 0 && W.Fits != 1) return Error::Fits;
        if (W.RamKiB < 0 || W.DiskKiB < 0) return Error::Negative;
        if (W.RamKiB > MaxKiB || W.DiskKiB > MaxKiB) return Error::Capacity;
        Rec.RamKiB = W.RamKiB;
        Rec.DiskKiB = W.DiskKiB;
        Rec.Fits = W.Fits == 1;
        Rec.Over = !Rec.Fits || Red;
        Out.Worlds[W.Id] = Rec;
    }
    return Error::None;
}

// dumps_line() without the newline: json.dumps(rec, sort_keys=True, separators=(",", ":")).
inline std::string DumpsLine(const Record& R) {
    PyJson::Object Budget;
    Budget.Add("ram_budget_kib", R.Budget[0].Json()).Add("disk_budget_kib", R.Budget[1].Json()).Add("warn_permille", R.Budget[2].Json());
    PyJson::Object Worlds;
    for (const auto& KV : R.Worlds) {
        PyJson::Object B;
        for (const auto& S : KV.second.Beacons) B.Add(S.first, PyJson::Str(S.second));
        PyJson::Object W;
        W.Add("ram_kib", PyJson::Int(KV.second.RamKiB)).Add("disk_kib", PyJson::Int(KV.second.DiskKiB))
            .Add("fits_all_resident", PyJson::Bool(KV.second.Fits)).Add("beacons", B.Dump(true)).Add("over", PyJson::Bool(KV.second.Over));
        Worlds.Add(KV.first, W.Dump(true));
    }
    PyJson::Object O;
    O.Add("format", PyJson::Str("daedalus-budget-ledger")).Add("version", PyJson::Int(1)).Add("run", PyJson::Str(R.Run))
        .Add("at", R.HasAt ? PyJson::Str(R.At) : PyJson::Null()).Add("budget", Budget.Dump(true)).Add("worlds", Worlds.Dump(true));
    return O.Dump(true);
}

struct Delta {
    std::string World;
    long long Ram = 0, Disk = 0;
};

struct DiffFinding {
    std::string World, Kind;
    bool HasSlot = false;
    long long Slot = 0;
    std::string Before, After;
};

struct DiffResult {
    std::string From, To;
    std::vector<Delta> Worlds;
    std::vector<DiffFinding> Findings;
    bool Worse = false;
};

inline bool HasBeacon(const WorldRec& W, const char* B) {
    for (const auto& KV : W.Beacons)
        if (KV.second == B) return true;
    return false;
}

inline DiffResult Diff(const Record& A, const Record& B) {
    DiffResult D;
    D.From = A.Run;
    D.To = B.Run;
    std::set<std::string> Ids;
    for (const auto& KV : A.Worlds) Ids.insert(KV.first);
    for (const auto& KV : B.Worlds) Ids.insert(KV.first);
    for (const std::string& Id : Ids) {
        const auto X = A.Worlds.find(Id), Y = B.Worlds.find(Id);
        if (X == A.Worlds.end()) {
            const bool Hot = Y->second.Over || HasBeacon(Y->second, "amber");
            D.Findings.push_back(DiffFinding{Id, Hot ? "appeared_hot" : "appeared", false, 0, "", ""});
            continue;
        }
        if (Y == B.Worlds.end()) {
            D.Findings.push_back(DiffFinding{Id, "dropped", false, 0, "", ""});
            continue;
        }
        D.Worlds.push_back(Delta{Id, Y->second.RamKiB - X->second.RamKiB, Y->second.DiskKiB - X->second.DiskKiB});
        if (Y->second.Over && !X->second.Over) D.Findings.push_back(DiffFinding{Id, "newly_over", false, 0, "", ""});
        if (X->second.Over && !Y->second.Over) D.Findings.push_back(DiffFinding{Id, "back_under", false, 0, "", ""});
        std::set<long long> Slots;  // sorted(..., key=int); keys are str() of nonnegative ints
        auto Num = [](const std::string& K) {
            long long V = 0;
            for (char C : K) V = V * 10 + (C - '0');
            return V;
        };
        for (const auto& KV : X->second.Beacons) Slots.insert(Num(KV.first));
        for (const auto& KV : Y->second.Beacons) Slots.insert(Num(KV.first));
        for (long long S : Slots) {
            const std::string K = std::to_string(S);
            const auto P = X->second.Beacons.find(K), Q = Y->second.Beacons.find(K);
            if (P == X->second.Beacons.end() || Q == Y->second.Beacons.end() || P->second == Q->second) continue;
            D.Findings.push_back(DiffFinding{Id, Rank(Q->second) > Rank(P->second) ? "beacon_worse" : "beacon_better", true, S, P->second, Q->second});
        }
    }
    for (const DiffFinding& F : D.Findings)
        D.Worse = D.Worse || F.Kind == "beacon_worse" || F.Kind == "newly_over" || F.Kind == "appeared_hot";
    return D;
}

struct TrendWorld {
    std::string World;
    std::vector<long long> Ram;
    long long Net = 0;
    int Trend = 0;  // 1 growing, -1 shrinking, 0 flat
};

struct TrendResult {
    std::vector<std::string> Runs;
    std::vector<TrendWorld> Worlds;
    int Tally = 0;  // 1 rising, -1 ebbing, 0 steady
};

inline Error Trend(const std::vector<Record>& Recs, long long Last, TrendResult& Out) {
    Out = TrendResult{};
    if (Last < 2) return Error::Last;
    if (Recs.empty()) return Error::Empty;
    if (Recs.size() > MaxRuns) return Error::Capacity;
    const std::size_t From = static_cast<std::uint64_t>(Last) >= Recs.size() ? 0 : Recs.size() - static_cast<std::size_t>(Last);
    std::set<std::string> Ids;
    for (std::size_t K = From; K < Recs.size(); ++K) {
        Out.Runs.push_back(Recs[K].Run);
        for (const auto& KV : Recs[K].Worlds) Ids.insert(KV.first);
    }
    bool Grow = false, Shrink = false;
    for (const std::string& Id : Ids) {
        TrendWorld W;
        W.World = Id;
        for (std::size_t K = From; K < Recs.size(); ++K) {
            const auto It = Recs[K].Worlds.find(Id);
            if (It != Recs[K].Worlds.end()) W.Ram.push_back(It->second.RamKiB);
        }
        W.Net = W.Ram.back() - W.Ram.front();
        W.Trend = W.Net > 0 ? 1 : W.Net < 0 ? -1 : 0;
        Grow = Grow || W.Trend > 0;
        Shrink = Shrink || W.Trend < 0;
        Out.Worlds.push_back(W);
    }
    Out.Tally = Grow ? 1 : Shrink ? -1 : 0;
    return Error::None;
}

}  // namespace BudgetLedger
}  // namespace DaedalusDiskSaver
