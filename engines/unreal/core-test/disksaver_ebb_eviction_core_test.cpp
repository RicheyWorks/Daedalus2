// SPDX-License-Identifier: MIT
// G253 port check: DaedalusDiskSaverEbbEvictionCore.h replays disksaver_ebb_eviction_parity.txt
// (written from ebb_eviction.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverEbbEvictionCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

using namespace DiskSaverParity;

// ---- golden-line helpers (same rules as batches 1-6): strict decimals, "x"+hex ids, "-" = empty list
[[maybe_unused]] static bool ToLong(const std::string& S, long long& Out) {
    const bool Neg = !S.empty() && S[0] == '-';
    const std::string D = Neg ? S.substr(1) : S;
    if (D.empty() || D.size() > 18 || (D.size() > 1 && D[0] == '0') || (Neg && D == "0")) return false;
    long long V = 0;
    for (char Ch : D) {
        if (Ch < '0' || Ch > '9') return false;
        V = V * 10 + (Ch - '0');
    }
    Out = Neg ? -V : V;
    return true;
}
[[maybe_unused]] static bool ToU(const std::string& S, std::uint64_t& Out) {
    long long V = 0;
    if (!ToLong(S, V) || V < 0) return false;
    Out = static_cast<std::uint64_t>(V);
    return true;
}
[[maybe_unused]] static bool Unhex(const std::string& S, std::string& Out) {
    if (S.empty() || S[0] != 'x' || S.size() % 2 == 0) return false;
    Out.clear();
    auto Nib = [](char C) { return C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1; };
    for (std::size_t I = 1; I < S.size(); I += 2) {
        const int A = Nib(S[I]), B = Nib(S[I + 1]);
        if (A < 0 || B < 0) return false;
        Out += static_cast<char>(A * 16 + B);
    }
    return true;
}
[[maybe_unused]] static std::string Hex(const std::string& S) {
    static const char* const D = "0123456789abcdef";
    std::string Out = "x";
    for (unsigned char C : S) {
        Out += D[C >> 4];
        Out += D[C & 15];
    }
    return Out;
}
[[maybe_unused]] static std::string JoinU(const std::vector<std::uint64_t>& V) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I]);
    return S.empty() ? "-" : S;
}
[[maybe_unused]] static std::string Rest(const std::vector<std::string>& T, std::size_t From) {
    std::string S;
    for (std::size_t I = From; I < T.size(); ++I) S += (I > From ? " " : "") + T[I];
    return S;
}
// "U ram disk warn" (side token first when Side is set)
[[maybe_unused]] static bool ParseBudget(const std::vector<std::string>& T, std::size_t At, DaedalusCensusBudget::Budget& B) {
    return T.size() == At + 3 && ToU(T[At], B.RamKiB) && ToU(T[At + 1], B.DiskKiB) && ToU(T[At + 2], B.WarnPermille);
}
// census world "id realm world_assets slot:n,..."; realm: "-" null, "!" not a string, else "x"+hex
struct CensusRow {
    DaedalusDiskSaver::CensusPlan::InWorld W;
    int RealmKind = 0;
    std::string Realm;
    bool HasAssets = false;
    long long Assets = 0;
};
[[maybe_unused]] static bool ParseWorld(const std::vector<std::string>& T, std::size_t At, CensusRow& R) {
    if (T.size() != At + 4 || !Unhex(T[At], R.W.Id)) return false;
    if (T[At + 1] == "-") R.RealmKind = 0;
    else if (T[At + 1] == "!") R.RealmKind = 2;
    else if (Unhex(T[At + 1], R.Realm)) R.RealmKind = 1;
    else return false;
    R.HasAssets = T[At + 2] != "-";
    if (R.HasAssets && !ToLong(T[At + 2], R.Assets)) return false;
    for (const std::string& P : Split(T[At + 3], ',')) {
        const std::vector<std::string> SN = Split(P, ':');
        DaedalusDiskSaver::CensusPlan::InIsland I;
        if (SN.size() != 2 || !ToU(SN[0], I.Slot) || !ToU(SN[1], I.Assets)) return false;
        R.W.Islands.push_back(I);
    }
    return true;
}
// One golden case: the C line, its input lines and its expected O lines.
[[maybe_unused]] static void Compare(const std::string& Case, const std::vector<std::string>& Got, const std::vector<std::string>& Want) {
    if (Got == Want) return;
    std::size_t I = 0;
    while (I < Got.size() && I < Want.size() && Got[I] == Want[I]) ++I;
    Check(false, Case + ": output line " + std::to_string(I) + " got '" + (I < Got.size() ? Got[I] : "<end>") + "' want '" +
                     (I < Want.size() ? Want[I] : "<end>") + "'");
}

namespace EE = DaedalusDiskSaver::EbbEviction;
namespace CP = DaedalusDiskSaver::CensusPlan;

static std::string View(const EE::Choice& C) {
    return C.Has ? std::to_string(C.Weight) + "/" + std::to_string(C.Count) + "/" + JoinU(C.Slots) : "-";
}

// Test-only brute force over every subset (n <= 16): (weight, count) of the cheapest set freeing >= need.
static bool Oracle(const std::vector<EE::Item>& Items, long long Need, std::uint64_t& W, std::uint64_t& C) {
    bool Any = false;
    const std::size_t N = Items.size();
    for (std::uint64_t M = 0; M < (std::uint64_t{1} << N); ++M) {
        std::uint64_t F = 0, Wt = 0, Cn = 0;
        for (std::size_t I = 0; I < N; ++I)
            if (M >> I & 1) {
                F += Items[I].RamKiB;
                Wt += Items[I].Weight;
                ++Cn;
            }
        if (static_cast<long long>(F) >= Need && (!Any || Wt < W || (Wt == W && Cn < C))) {
            Any = true;
            W = Wt;
            C = Cn;
        }
    }
    return Any;
}

struct Case {
    std::string Name;
    bool Open = false, FromCensus = false, Raw = false, Ok = true;
    EE::Config Cfg;
    DaedalusCensusBudget::Budget B;
    std::vector<CP::InWorld> Census;
    std::uint64_t RamBudget = 0;
    std::vector<EE::ReportWorld> Report;
    std::vector<std::string> Want;
};

static int Plays = 0, Oracles = 0;

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && (K.FromCensus != K.Raw), K.Name + ": input lines");
    if (!K.Ok || K.FromCensus == K.Raw) return;
    std::vector<EE::ReportWorld> Report = K.Report;
    std::uint64_t Budget = K.RamBudget;
    if (K.FromCensus) {
        CP::Report R;
        const CP::Error E = CP::Plan(K.Census, K.B, R);
        Check(E == CP::Error::None, K.Name + ": census refused " + CP::ErrorName(E));
        if (E != CP::Error::None) return;
        Report = EE::FromCensus(R);
        Budget = K.B.RamKiB;
    }
    std::vector<EE::WorldPlan> Plans;
    EE::Summary S;
    const EE::Error E = EE::Plan(Report, Budget, K.Cfg, Plans, S);
    std::vector<std::string> Got;
    if (E != EE::Error::None) {
        Got.push_back(std::string("refused ") + EE::ErrorName(E));
    } else {
        for (const EE::WorldPlan& P : Plans) {
            Got.push_back("w " + Hex(P.Id) + " " + std::to_string(P.TotalRamKiB) + " " + std::to_string(P.NeedKiB) + " " +
                          JoinU(P.PinnedSlots) + " " + EE::TideName(P.T) + " " + View(P.Optimal) + " " + View(P.GreedyHeaviest) +
                          " " + View(P.GreedyWeight));
            // the DP never loses to either greedy order, and matches brute force on small worlds
            if (P.Optimal.Has && P.GreedyHeaviest.Has)
                Check(!EE::Worse(P.Optimal, P.GreedyHeaviest), K.Name + ": DP worse than greedy");
        }
        Got.push_back("s " + std::to_string(S.Worlds) + " " + std::to_string(S.OverBudget) + " " + std::to_string(S.CannotFit) + " " +
                      std::to_string(S.Unloads) + " " + std::to_string(S.GreedyHeaviestWorse) + " " + std::to_string(S.GreedyWeightWorse));
        for (const EE::ReportWorld& W : Report) {
            std::vector<EE::Item> Items;
            std::uint64_t Total = 0;
            for (const EE::Row& R : W.Islands) {
                Total += R.RamKiB;
                if (K.Cfg.Pinned.count(R.Slot)) continue;
                const auto It = K.Cfg.Weights.find(std::make_pair(W.Id, R.Slot));
                Items.push_back(EE::Item{R.Slot, R.RamKiB, It == K.Cfg.Weights.end() ? K.Cfg.DefaultWeight : It->second});
            }
            if (Items.size() > 16) continue;
            const long long Need = static_cast<long long>(Total) - static_cast<long long>(Budget);
            EE::Choice C;
            Check(EE::Solve(Items, Need, C) == EE::Error::None, K.Name + ": solve");
            std::uint64_t OW = 0, OC = 0;
            const bool Any = Need <= 0 ? (OW = 0, OC = 0, true) : Oracle(Items, Need, OW, OC);
            Check(Any == C.Has && (!Any || (OW == C.Weight && OC == C.Count)), K.Name + ": DP disagrees with brute force");
            ++Oracles;
        }
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_ebb_eviction_parity.txt")) {
        if (T[0] == "C" && T.size() == 2) {
            Flush(K);
            K = Case{};
            K.Name = T[1];
            K.Open = true;
            ++Cases;
            continue;
        }
        if (!K.Open) {
            Check(false, "line before the first case: " + T[0]);
            continue;
        }
        if (T[0] == "O") {
            K.Want.push_back(Rest(T, 1));
        } else if (T[0] == "K" && T.size() == 3) {
            for (const std::string& P : Split(T[1], ',')) {
                std::uint64_t S = 0;
                K.Ok = ToU(P, S) && K.Ok;
                K.Cfg.Pinned.insert(S);
            }
            K.Ok = ToU(T[2], K.Cfg.DefaultWeight) && K.Ok;
        } else if (T[0] == "X" && T.size() == 4) {
            std::string Id;
            std::uint64_t S = 0, W = 0;
            K.Ok = Unhex(T[1], Id) && ToU(T[2], S) && ToU(T[3], W) && K.Ok;
            K.Cfg.Weights[std::make_pair(Id, S)] = W;
        } else if (T[0] == "U") {
            K.FromCensus = true;
            K.Ok = ParseBudget(T, 1, K.B) && K.Ok;
        } else if (T[0] == "W") {
            CensusRow R;
            K.Ok = ParseWorld(T, 1, R) && K.Ok;
            K.Census.push_back(R.W);
        } else if (T[0] == "Q" && T.size() == 2) {
            K.Raw = true;
            K.Ok = ToU(T[1], K.RamBudget) && K.Ok;
        } else if (T[0] == "R" && T.size() == 3) {
            EE::ReportWorld W;
            K.Ok = Unhex(T[1], W.Id) && K.Ok;
            for (const std::string& P : Split(T[2], ',')) {
                const std::vector<std::string> SR = Split(P, ':');
                EE::Row Rw;
                K.Ok = SR.size() == 2 && ToU(SR[0], Rw.Slot) && ToU(SR[1], Rw.RamKiB) && K.Ok;
                W.Islands.push_back(Rw);
            }
            K.Report.push_back(W);
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    Check(Oracles > 0, "brute-force oracle ran");
    return Finish("ebb_eviction", Cases, Plays);
}
