// SPDX-License-Identifier: MIT
// G505 port check: DaedalusDiskSaverBeaconWatchCore.h replays disksaver_beacon_watch_parity.txt
// (written from beacon_watch.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverBeaconWatchCore.h"
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

namespace BW = DaedalusDiskSaver::BeaconWatch;
namespace CP = DaedalusDiskSaver::CensusPlan;

struct Side {
    bool Census = false, Raw = false;
    DaedalusCensusBudget::Budget B;
    std::vector<CP::InWorld> Worlds;
    std::vector<BW::RWorld> Report;
};

struct Case {
    std::string Name;
    bool Open = false, Ok = true;
    Side S[2];
    std::vector<std::string> Want;
};

static int Plays = 0;

static bool Resolve(const std::string& Name, const Side& S, std::vector<BW::RWorld>& Out) {
    Check(!(S.Census && S.Raw), Name + ": a side is either census or report lines");
    if (!S.Census) {
        Out = S.Report;
        return true;
    }
    CP::Report R;
    const CP::Error E = CP::Plan(S.Worlds, S.B, R);
    Check(E == CP::Error::None, Name + ": census refused " + CP::ErrorName(E));
    if (E != CP::Error::None) return false;
    Out = BW::FromCensus(R);
    return true;
}

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok, K.Name + ": input lines");
    std::vector<BW::RWorld> Base, Cur;
    if (!K.Ok || !Resolve(K.Name, K.S[0], Base) || !Resolve(K.Name, K.S[1], Cur)) return;
    BW::Verdict V;
    int Bad = -1;
    const BW::Error E = BW::Watch(Base, Cur, V, Bad);
    std::vector<std::string> Got;
    if (E != BW::Error::None) {
        Got.push_back(std::string("refused ") + (Bad == 0 ? "baseline_" : "current_") + BW::ErrorName(E));
    } else {
        for (const BW::Finding& F : V.Findings)
            Got.push_back("f " + Hex(F.World) + " " + (F.Slot < 0 ? std::string("-") : std::to_string(F.Slot)) + " " + F.Kind + " " +
                          F.Before + " " + F.After + " " + (F.Fails ? "1" : "0"));
        std::string Counts;
        for (const auto& KV : V.Counts) Counts += (Counts.empty() ? "" : ",") + KV.first + "=" + std::to_string(KV.second);
        Got.push_back(std::string("v ") + (V.Storm ? "storm" : "calm") + " " + std::to_string(V.Regressions) + " " +
                      (Counts.empty() ? "-" : Counts));
        // a report compared with itself is always calm with no findings
        BW::Verdict Self;
        int SB = -1;
        Check(BW::Watch(Cur, Cur, Self, SB) == BW::Error::None && Self.Findings.empty() && !Self.Storm, K.Name + ": self compare");
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

static int SideOf(const std::string& S) { return S == "b" ? 0 : S == "c" ? 1 : -1; }

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_beacon_watch_parity.txt")) {
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
        const int S = T.size() > 1 ? SideOf(T[1]) : -1;
        if (T[0] == "O") {
            K.Want.push_back(Rest(T, 1));
        } else if (T[0] == "U" && S >= 0) {
            K.S[S].Census = true;
            K.Ok = ParseBudget(T, 2, K.S[S].B) && K.Ok;
        } else if (T[0] == "W" && S >= 0) {
            CensusRow R;
            K.S[S].Census = true;
            K.Ok = ParseWorld(T, 2, R) && K.Ok;
            K.S[S].Worlds.push_back(R.W);
        } else if (T[0] == "R" && S >= 0 && T.size() == 6) {
            BW::RWorld W;
            K.S[S].Raw = true;
            K.Ok = Unhex(T[2], W.Id) && K.Ok;
            W.Fits = T[3] == "1" ? 1 : T[3] == "0" ? 0 : T[3] == "!" ? 2 : (K.Ok = false, 0);
            K.Ok = ToLong(T[4], W.MaxResident) && K.Ok;
            for (const std::string& P : Split(T[5], ',')) {
                const std::vector<std::string> SB = Split(P, ':');
                BW::RIsland I;
                K.Ok = SB.size() == 2 && ToU(SB[0], I.Slot) && K.Ok;
                if (SB.size() == 2) I.Beacon = SB[1];
                W.Islands.push_back(I);
            }
            K.S[S].Report.push_back(W);
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    return Finish("beacon_watch", Cases, Plays);
}
