// SPDX-License-Identifier: MIT
// G529 port check: DaedalusDiskSaverBudgetFathomsCore.h replays disksaver_budget_fathoms_parity.txt
// (written from budget_fathoms.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverBudgetFathomsCore.h"
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

namespace BF = DaedalusDiskSaver::BudgetFathoms;
namespace CP = DaedalusDiskSaver::CensusPlan;
namespace CB = DaedalusCensusBudget;

struct Case {
    std::string Name;
    bool Open = false, Ok = true, HasBudget = false, HasSweep = false;
    CB::Budget B;
    std::vector<CP::InWorld> Census;
    BF::Sweep SR, SD;
    std::vector<std::string> Want;
};

static int Plays = 0, GreenChecks = 0;

static std::string U(std::uint64_t V) { return std::to_string(V); }

static std::string StateText(const BF::State& S) {
    return U(S.Green) + " " + U(S.Amber) + " " + U(S.Red) + " " + U(S.Spilling) + " " + BF::DepthName(S.Verdict);
}

// green_kib is the smallest RAM budget that keeps the island green (test-only check through the G206 beacon).
static void CheckGreen(std::uint64_t Cost, std::uint64_t Warn, std::uint64_t G) {
    auto Green = [&](std::uint64_t Budget) {
        CB::Budget B;
        B.RamKiB = Budget;
        B.DiskKiB = CB::MaxKiB;
        B.WarnPermille = Warn;
        CB::IslandCost C;
        C.RamKiB = Cost;
        C.DiskKiB = 0;
        return CB::Judge(C, B).Colour == CB::Beacon::Green;
    };
    Check(Green(G) && (G == 0 || !Green(G - 1)), "green_kib is the smallest green budget");
    ++GreenChecks;
}

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && K.HasBudget && K.HasSweep, K.Name + ": input lines");
    if (!K.Ok || !K.HasBudget || !K.HasSweep) return;
    BF::Result R;
    CP::Error CE = CP::Error::None;
    const BF::Error E = BF::Build(K.Census, K.B, K.SR, K.SD, R, CE);
    std::vector<std::string> Got;
    if (E == BF::Error::Census) {
        Got.push_back(std::string("refused ") + CP::ErrorName(CE));
    } else if (E == BF::Error::SweepRam || E == BF::Error::SweepDisk) {
        Got.push_back(E == BF::Error::SweepRam ? "refused sweep_ram" : "refused sweep_disk");
    } else if (E != BF::Error::None) {
        Got.push_back("refused capacity");
    } else {
        for (int Dim = 0; Dim < 2; ++Dim) {
            const BF::Need& N = Dim == 0 ? R.Ram : R.Disk;
            const long long* S = Dim == 0 ? R.RamSlack : R.DiskSlack;
            Got.push_back(std::string("n ") + (Dim == 0 ? "ram " : "disk ") + U(N.AllGreen) + " " + U(N.NoRed) + " " + U(N.AllFit) + " " +
                          U(N.Deep) + " " + std::to_string(S[0]) + " " + std::to_string(S[1]) + " " + std::to_string(S[2]) + " " +
                          std::to_string(S[3]));
        }
        for (const BF::WorldNeed& W : R.Worlds) {
            std::string Isl;
            for (const BF::IslandNeed& I : W.Islands) {
                Isl += (Isl.empty() ? "" : ",") + U(I.Slot) + ":" + U(I.RamGreen) + ":" + U(I.RamClear) + ":" + U(I.DiskGreen) + ":" +
                       U(I.DiskClear);
                if (GreenChecks < 2000) CheckGreen(I.RamClear, K.B.WarnPermille, I.RamGreen);
            }
            Got.push_back("w " + Hex(W.Id) + " " + U(W.RamFit) + " " + U(W.DiskFit) + " " + (Isl.empty() ? "-" : Isl));
        }
        for (const BF::SweepRow& S : R.Sweeps)
            Got.push_back(std::string("s ") + (S.Ram ? "ram " : "disk ") + U(S.BudgetKiB) + " " + StateText(S.S));
        Got.push_back("now " + StateText(R.Now));
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

static bool ParseSweep(const std::string& T, BF::Sweep& S) {
    S = BF::Sweep{};
    if (T == "n") return true;
    S.Given = true;
    return Unhex(T, S.Text);
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_budget_fathoms_parity.txt")) {
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
            K.Census.push_back(R.W);
        } else if (T[0] == "S" && T.size() == 3) {
            K.HasSweep = true;
            K.Ok = ParseSweep(T[1], K.SR) && ParseSweep(T[2], K.SD) && K.Ok;
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    Check(GreenChecks > 0, "green_kib checks ran");
    return Finish("budget_fathoms", Cases, Plays);
}
