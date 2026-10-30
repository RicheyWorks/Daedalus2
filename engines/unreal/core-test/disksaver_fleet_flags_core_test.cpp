// SPDX-License-Identifier: MIT
// G533 port check: DaedalusDiskSaverFleetFlagsCore.h replays disksaver_fleet_flags_parity.txt
// (written from fleet_flags.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverFleetFlagsCore.h"
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

namespace FF = DaedalusDiskSaver::FleetFlags;
namespace CP = DaedalusDiskSaver::CensusPlan;

struct Case {
    std::string Name;
    bool Open = false, Ok = true, HasBudget = false, HasClaims = true, NoneLine = false;
    DaedalusCensusBudget::Budget B;
    std::vector<FF::World> Worlds;
    std::vector<FF::Claim> Claims;
    std::vector<std::string> Want;
};

static int Plays = 0;

static std::string U(std::uint64_t V) { return std::to_string(V); }
static std::string Rid(const FF::RealmKey& K) { return K.first ? Hex(K.second) : "-"; }

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && K.HasBudget && !(K.NoneLine && !K.Claims.empty()), K.Name + ": input lines");
    if (!K.Ok || !K.HasBudget) return;
    FF::Result R;
    CP::Error CE = CP::Error::None;
    const FF::Error E = FF::Muster(K.Worlds, K.B, !K.NoneLine, K.Claims, R, CE);
    std::vector<std::string> Got;
    if (E == FF::Error::Census) {
        Got.push_back(std::string("refused ") + CP::ErrorName(CE));
    } else if (E != FF::Error::None) {
        Got.push_back(E == FF::Error::Realm ? "refused realm" : "refused capacity");
    } else {
        std::uint64_t Worlds = 0;
        for (const FF::Realm& G : R.Realms) {
            Got.push_back("r " + Rid(G.Id) + " " + U(G.Worlds) + " " + U(G.Islands) + " " + U(G.Assets) + " " + U(G.RamKiB) + " " +
                          U(G.DiskKiB) + " " + U(G.Green) + " " + U(G.Amber) + " " + U(G.Red) + " " + U(G.Spilling) + " " +
                          Hex(G.Heaviest) + " " + FF::FlagName(G.Flag));
            Worlds += G.Worlds;
        }
        Check(Worlds == K.Worlds.size(), K.Name + ": every world lands in exactly one realm");
        for (const FF::Mismatch& M : R.Mismatches)
            Got.push_back("m " + Rid(M.Id) + " " + M.Field + " " + (M.HasClaimed ? std::to_string(M.Claimed) : std::string("-")) + " " +
                          std::to_string(M.Found));
        Got.push_back(std::string("v ") + FF::SignalName(R.Verdict));
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_fleet_flags_parity.txt")) {
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
            K.HasBudget = true;
            K.Ok = ParseBudget(T, 1, K.B) && K.Ok;
        } else if (T[0] == "W") {
            CensusRow R;
            K.Ok = ParseWorld(T, 1, R) && K.Ok;
            FF::World W;
            W.W = R.W;
            W.RealmKind = R.RealmKind;
            W.Realm = R.Realm;
            W.HasAssets = R.HasAssets;
            W.Assets = R.Assets;
            K.Worlds.push_back(W);
        } else if (T[0] == "M" && T.size() == 2 && T[1] == "none") {
            K.NoneLine = true;
        } else if (T[0] == "M" && T.size() == 5) {
            FF::Claim C;
            if (T[1] != "-") {
                C.Id.first = true;
                K.Ok = Unhex(T[1], C.Id.second) && K.Ok;
            }
            for (int F = 0; F < 3; ++F) {
                C.Has[F] = T[2 + F] != "?";
                if (C.Has[F]) K.Ok = ToLong(T[2 + F], C.Value[F]) && K.Ok;
            }
            K.Claims.push_back(C);
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    return Finish("fleet_flags", Cases, Plays);
}
