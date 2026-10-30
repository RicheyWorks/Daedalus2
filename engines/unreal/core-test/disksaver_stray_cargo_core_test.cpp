// SPDX-License-Identifier: MIT
// G531 port check: DaedalusDiskSaverStrayCargoCore.h replays disksaver_stray_cargo_parity.txt
// (written from stray_cargo.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverStrayCargoCore.h"
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

namespace SG = DaedalusDiskSaver::StrayCargo;

static bool ParseValue(const std::string& T, SG::Value& V) {
    V = SG::Value{};
    if (T == "-") return true;
    if (T == "t" || T == "f") {
        V.K = SG::Value::Bool;
        V.B = T == "t";
        return true;
    }
    if (T.size() >= 2 && T[0] == 'i') {
        V.K = SG::Value::Int;
        return ToLong(T.substr(1), V.I);
    }
    if (!T.empty() && T[0] == 's') {
        V.K = SG::Value::Str;
        return Unhex("x" + T.substr(1), V.S);
    }
    return false;
}

struct Case {
    std::string Name;
    bool Open = false, Ok = true;
    std::vector<SG::World> Worlds;
    std::vector<std::string> Want;
};

static int Plays = 0;

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok, K.Name + ": input lines");
    if (!K.Ok) return;
    SG::Result R;
    const SG::Error E = SG::Survey(K.Worlds, R);
    std::vector<std::string> Got;
    if (E != SG::Error::None) {
        Got.push_back(std::string("refused ") + SG::ErrorName(E));
    } else {
        for (const SG::Finding& F : R.Findings) Got.push_back("f " + Hex(F.Json));
        std::string C = "k";
        std::uint64_t Sum = 0;
        for (int I = 0; I < SG::KindCount; ++I) {
            C += " " + std::to_string(R.Counts[I]);
            Sum += R.Counts[I];
        }
        Check(Sum == R.Findings.size(), K.Name + ": counts add up to the findings");
        Got.push_back(C);
        Got.push_back(std::string("v ") + SG::VerdictName(R.Verdict) + " " + std::to_string(R.HiddenRam) + " " + std::to_string(R.HiddenDisk) +
                      " " + std::to_string(R.EmptyHullRam) + " " + std::to_string(R.SharedDisk));
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_stray_cargo_parity.txt")) {
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
        } else if (T[0] == "W" && T.size() == 5) {
            SG::World W;
            K.Ok = Unhex(T[1], W.Id) && (T[2] == "-" || T[2] == "r") && K.Ok;
            W.HasRealm = T[2] == "r";
            W.HasClaimed = T[3] != "-";
            if (W.HasClaimed) K.Ok = ToLong(T[3], W.Claimed) && K.Ok;
            for (const std::string& P : Split(T[4], ',')) {
                const std::vector<std::string> SA = Split(P, ':');
                SG::Island I;
                if (SA.size() != 2) {
                    K.Ok = false;
                    continue;
                }
                I.SlotIsInt = SA[0] != "!";
                if (I.SlotIsInt) K.Ok = ToLong(SA[0], I.Slot) && K.Ok;
                I.HasAssets = SA[1] != "-";
                if (I.HasAssets) K.Ok = ToLong(SA[1], I.Assets) && K.Ok;
                W.Islands.push_back(I);
            }
            K.Worlds.push_back(W);
        } else if (T[0] == "A" && T.size() == 4 && !K.Worlds.empty()) {
            SG::Asset A;
            A.NameIsStr = T[1] != "!";
            if (A.NameIsStr) K.Ok = Unhex(T[1], A.Name) && K.Ok;
            K.Ok = ParseValue(T[2], A.Slot) && ParseValue(T[3], A.File) && K.Ok;
            K.Worlds.back().Assets.push_back(A);
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    return Finish("stray_cargo", Cases, Plays);
}
