// SPDX-License-Identifier: MIT
// G519 port check: DaedalusDiskSaverMemoryFootprintCore.h replays disksaver_memory_footprint_parity.txt
// (written from memory_footprint.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverMemoryFootprintCore.h"
#include "DaedalusDiskSaverCensusPlanCore.h"
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

namespace MF = DaedalusDiskSaver::MemoryFootprint;
namespace CP = DaedalusDiskSaver::CensusPlan;

struct Case {
    std::string Name;
    bool Open = false, Ok = true, Census = false, Raw = false, HasP = false;
    DaedalusCensusBudget::Budget B;
    std::vector<CP::InWorld> Worlds;
    MF::Report Report;
    long long Top = 0, Wins = 0;
    std::vector<std::string> Want;
};

static int Plays = 0;
static std::string L(long long V) { return std::to_string(V); }

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && K.HasP && K.Census != K.Raw, K.Name + ": input lines");
    if (!K.Ok || !K.HasP || K.Census == K.Raw) return;
    MF::Report Rep = K.Report;
    if (K.Census) {
        CP::Report R;
        const CP::Error E = CP::Plan(K.Worlds, K.B, R);
        Check(E == CP::Error::None, K.Name + ": census refused " + CP::ErrorName(E));
        if (E != CP::Error::None) return;
        Rep = MF::FromCensus(R);
    }
    MF::Result R;
    const MF::Error E = MF::Build(Rep, K.Top, K.Wins, R);
    std::vector<std::string> Got;
    if (E != MF::Error::None) {
        Got.push_back(std::string("refused ") + MF::ErrorName(E));
    } else {
        for (const MF::WorldRow& W : R.Worlds) {
            std::string Top;
            for (const MF::TopIsland& I : W.Top) Top += (Top.empty() ? "" : ",") + L(I.Slot) + ":" + L(I.RamKiB) + ":" + L(I.DiskKiB) + ":" + L(I.SharePermille);
            Got.push_back("w " + Hex(W.Id) + " " + L(W.RamKiB) + " " + L(W.DiskKiB) + " " + L(W.RamPermille) + " " + L(W.DiskPermille) + " " +
                          (W.Over ? "1" : "0") + " " + std::to_string(W.Islands) + " " + (Top.empty() ? "-" : Top));
        }
        Got.push_back("t " + std::to_string(R.Worlds.size()) + " " + std::to_string(R.IslandCount) + " " + L(R.RamKiB) + " " + L(R.DiskKiB) + " " + L(R.Peak));
        for (const MF::Consumer& C : R.TopConsumers) Got.push_back("c " + Hex(C.World) + " " + L(C.Slot) + " " + L(C.RamKiB) + " " + L(C.DiskKiB));
        for (std::size_t I = 0; I < R.Wins.size(); ++I) {
            const MF::Win& W = R.Wins[I];
            Got.push_back("n " + std::to_string(I + 1) + " " + Hex(W.World) + " " + L(W.Slot) + " " + (W.Trim ? "trim" : "unload") + " " + L(W.RamFree) + " " +
                          L(W.DiskFree) + " " + (W.WorldOver ? "1" : "0") + " " + (W.Clears ? "1" : "0"));
            // a win only "clears" an over-budget world, and then that world fits after the move
            Check(!W.Clears || W.WorldOver, K.Name + ": clears implies world_over");
        }
        Got.push_back(std::string("v ") + MF::VerdictName(R.Verdict));
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_memory_footprint_parity.txt")) {
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
        } else if (T[0] == "U") {
            K.Census = true;
            K.Ok = ParseBudget(T, 1, K.B) && K.Ok;
        } else if (T[0] == "W") {
            CensusRow R;
            K.Census = true;
            K.Ok = ParseWorld(T, 1, R) && K.Ok;
            K.Worlds.push_back(R.W);
        } else if (T[0] == "Q" && T.size() == 4) {
            K.Raw = true;
            K.Ok = ToLong(T[1], K.Report.RamBudget) && ToLong(T[2], K.Report.DiskBudget) && ToLong(T[3], K.Report.Warn) && K.Ok;
        } else if (T[0] == "R" && T.size() == 3) {
            MF::ReportWorld W;
            K.Raw = true;
            K.Ok = Unhex(T[1], W.Id) && K.Ok;
            for (const std::string& P : Split(T[2], ',')) {
                const std::vector<std::string> F = Split(P, ':');
                MF::Island I;
                K.Ok = F.size() == 4 && ToLong(F[0], I.Slot) && ToLong(F[1], I.RamKiB) && ToLong(F[2], I.DiskKiB) && ToLong(F[3], I.Assets) && K.Ok;
                W.Islands.push_back(I);
            }
            K.Report.Worlds.push_back(W);
        } else if (T[0] == "P" && T.size() == 3) {
            K.HasP = true;
            K.Ok = ToLong(T[1], K.Top) && ToLong(T[2], K.Wins) && K.Ok;
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    return Finish("memory_footprint", Cases, Plays);
}
