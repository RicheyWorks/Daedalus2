// SPDX-License-Identifier: MIT
// G517 port check: DaedalusDiskSaverBudgetLedgerCore.h replays disksaver_budget_ledger_parity.txt
// (written from budget_ledger.py by tools/streaming/disksaver_cpp_parity.py) case by case: inputs, then the expected output lines.
#include "DaedalusDiskSaverBudgetLedgerCore.h"
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

namespace BL = DaedalusDiskSaver::BudgetLedger;
namespace CP = DaedalusDiskSaver::CensusPlan;

struct Run {
    int RunKind = 1, AtKind = 0;
    std::string RunId, At;
    bool Census = false, Raw = false;
    DaedalusCensusBudget::Budget B;
    std::vector<CP::InWorld> Worlds;
    BL::Report Report;
};

struct Case {
    std::string Name;
    bool Open = false, Ok = true;
    std::vector<Run> Runs;
    std::vector<long long> Lasts;
    std::vector<std::string> Want;
};

static int Plays = 0;
static std::string L(long long V) { return std::to_string(V); }

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok, K.Name + ": input lines");
    if (!K.Ok) return;
    std::vector<std::string> Got;
    std::vector<BL::Record> Recs;
    for (const Run& R : K.Runs) {
        Check(!(R.Census && R.Raw), K.Name + ": a run is census or report lines");
        BL::Report Rep = R.Report;
        if (R.Census) {
            CP::Report P;
            const CP::Error E = CP::Plan(R.Worlds, R.B, P);
            Check(E == CP::Error::None, K.Name + ": census refused " + CP::ErrorName(E));
            if (E != CP::Error::None) return;
            Rep = BL::FromCensus(P);
        }
        BL::Record Rec;
        const BL::Error E = BL::MakeRecord(Rep, R.RunKind, R.RunId, R.AtKind, R.At, Rec);
        if (E != BL::Error::None) {
            Got.push_back(std::string("refused ") + BL::ErrorName(E));
            continue;
        }
        Got.push_back("r " + Hex(BL::DumpsLine(Rec)));
        const BL::DiffResult Self = BL::Diff(Rec, Rec);
        Check(Self.Findings.empty() && !Self.Worse, K.Name + ": a record diffed with itself is steady");
        Recs.push_back(Rec);
    }
    for (std::size_t I = 1; I < Recs.size(); ++I) {
        const BL::DiffResult D = BL::Diff(Recs[I - 1], Recs[I]);
        Got.push_back("d " + Hex(D.From) + " " + Hex(D.To) + " " + (D.Worse ? "worse" : "steady"));
        for (const BL::Delta& W : D.Worlds) Got.push_back("dw " + Hex(W.World) + " " + L(W.Ram) + " " + L(W.Disk));
        for (const BL::DiffFinding& F : D.Findings)
            Got.push_back("df " + Hex(F.World) + " " + F.Kind + " " + (F.HasSlot ? L(F.Slot) : "-") + " " + (F.Before.empty() ? "-" : F.Before) + " " +
                          (F.After.empty() ? "-" : F.After));
    }
    for (long long Last : K.Lasts) {
        BL::TrendResult T;
        const BL::Error E = BL::Trend(Recs, Last, T);
        if (E != BL::Error::None) {
            Got.push_back(std::string("refused ") + BL::ErrorName(E));
            continue;
        }
        std::string Runs;
        for (const std::string& R : T.Runs) Runs += (Runs.empty() ? "" : ",") + Hex(R);
        Got.push_back("t " + (Runs.empty() ? std::string("-") : Runs) + " " + (T.Tally > 0 ? "rising" : T.Tally < 0 ? "ebbing" : "steady"));
        for (const BL::TrendWorld& W : T.Worlds) {
            std::string Ram;
            for (long long V : W.Ram) Ram += (Ram.empty() ? "" : ",") + L(V);
            Got.push_back("tw " + Hex(W.World) + " " + std::to_string(W.Ram.size()) + " " + Ram + " " + L(W.Net) + " " +
                          (W.Trend > 0 ? "growing" : W.Trend < 0 ? "shrinking" : "flat"));
        }
    }
    Compare(K.Name, Got, K.Want);
    ++Plays;
}

static bool MaybeInt(const std::string& T, BL::MaybeInt& M) {
    M = BL::MaybeInt{};
    if (T == "?" || T == "-") return true;
    M.Has = true;
    return ToLong(T, M.V);
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case K;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_budget_ledger_parity.txt")) {
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
        Run* R = K.Runs.empty() ? nullptr : &K.Runs.back();
        if (T[0] == "O") {
            K.Want.push_back(Rest(T, 1));
        } else if (T[0] == "N" && T.size() == 3) {
            Run N;
            N.RunKind = T[1] == "!" ? 2 : 1;
            if (N.RunKind == 1) K.Ok = Unhex(T[1], N.RunId) && K.Ok;
            N.AtKind = T[2] == "-" ? 0 : T[2] == "!" ? 2 : 1;
            if (N.AtKind == 1) K.Ok = Unhex(T[2], N.At) && K.Ok;
            K.Runs.push_back(N);
        } else if (T[0] == "L" && T.size() == 2) {
            long long V = 0;
            K.Ok = ToLong(T[1], V) && K.Ok;
            K.Lasts.push_back(V);
        } else if (R && T[0] == "U") {
            R->Census = true;
            K.Ok = ParseBudget(T, 1, R->B) && K.Ok;
        } else if (R && T[0] == "W") {
            CensusRow C;
            R->Census = true;
            K.Ok = ParseWorld(T, 1, C) && K.Ok;
            R->Worlds.push_back(C.W);
        } else if (R && T[0] == "B" && T.size() == 4) {
            R->Raw = true;
            for (int I = 0; I < 3; ++I) K.Ok = MaybeInt(T[1 + static_cast<std::size_t>(I)], R->Report.Budget[I]) && K.Ok;
        } else if (R && T[0] == "R" && T.size() == 6) {
            BL::RWorld W;
            R->Raw = true;
            K.Ok = Unhex(T[1], W.Id) && K.Ok;
            W.Fits = T[2] == "1" ? 1 : T[2] == "0" ? 0 : T[2] == "!" ? 2 : (K.Ok = false, 0);
            K.Ok = ToLong(T[3], W.RamKiB) && ToLong(T[4], W.DiskKiB) && K.Ok;
            for (const std::string& P : Split(T[5], ',')) {
                const std::vector<std::string> SB = Split(P, ':');
                BL::RIsland I;
                K.Ok = SB.size() == 2 && ToLong(SB[0], I.Slot) && K.Ok;
                if (SB.size() == 2) I.Beacon = SB[1];
                W.Islands.push_back(I);
            }
            R->Report.Worlds.push_back(W);
        } else {
            K.Ok = false;
            Check(false, K.Name + ": unknown line " + T[0]);
        }
    }
    Flush(K);
    return Finish("budget_ledger", Cases, Plays);
}
