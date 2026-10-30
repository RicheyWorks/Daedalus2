// SPDX-License-Identifier: MIT
// G590 Gantry Sweep check: DaedalusDiskSaverGantrySweepCore.h replays disksaver_gantry_sweep_parity.txt
// (written by tools/streaming/gantry_sweep_parity.py from CPython's random.Random(str)): each case lays out
// a rail from its seed string or hand line, then every expected layout, habit, best-order and play line must match.
#include "DaedalusDiskSaverGantrySweepCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

using namespace DiskSaverParity;
namespace GS = DaedalusDiskSaver::GantrySweep;

static std::string Rest(const std::vector<std::string>& T, std::size_t From) {
    std::string S;
    for (std::size_t I = From; I < T.size(); ++I) S += (I > From ? " " : "") + T[I];
    return S;
}

static void Compare(const std::string& Case, const std::vector<std::string>& Got, const std::vector<std::string>& Want) {
    if (Got == Want) return;
    std::size_t I = 0;
    while (I < Got.size() && I < Want.size() && Got[I] == Want[I]) ++I;
    Check(false, Case + ": output line " + std::to_string(I) + " got '" + (I < Got.size() ? Got[I] : "<end>") + "' want '" +
                     (I < Want.size() ? Want[I] : "<end>") + "'");
}

static bool ToI64(const std::string& S, std::int64_t& Out) {
    if (S.empty() || S.size() > 18 || (S.size() > 1 && S[0] == '0')) return false;  // Python writes no leading zeros
    std::int64_t V = 0;
    for (char C : S) {
        if (C < '0' || C > '9') return false;
        V = V * 10 + (C - '0');
    }
    Out = V;
    return true;
}

static bool Unhex(const std::string& S, std::string& Out) {
    if (S.empty() || S[0] != 'x' || S.size() % 2 == 0) return false;
    Out.clear();
    for (std::size_t I = 1; I + 1 < S.size(); I += 2) {
        int V = 0;
        for (int K = 0; K < 2; ++K) {
            const char C = S[I + static_cast<std::size_t>(K)];
            const int D = C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1;
            if (D < 0) return false;
            V = V * 16 + D;
        }
        Out.push_back(static_cast<char>(V));
    }
    return true;
}

static std::string Join(const GS::Order& O) {
    if (O.empty()) return "-";
    std::string S;
    for (std::size_t I = 0; I < O.size(); ++I) S += (I ? "," : "") + std::to_string(O[I]);
    return S;
}

struct Case {
    std::string Name;
    bool Open = false, Ok = true, Laid = false;
    GS::Layout L;
    std::vector<std::string> Got, Want;
};

static int Plays = 0, Layouts = 0;

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && K.Laid, K.Name + ": input lines");
    if (!K.Ok || !K.Laid) return;
    Compare(K.Name, K.Got, K.Want);
}

static void Lay(Case& K) {
    const GS::Layout& L = K.L;
    K.Got.push_back("L " + std::to_string(L.Start) + " " + std::to_string(L.Ships.size()));
    for (std::size_t I = 0; I < L.Ships.size(); ++I)
        K.Got.push_back("R " + std::to_string(I) + " " + L.Ships[I].Label + " " + std::to_string(L.Ships[I].Pos) + " " +
                        std::to_string(L.Ships[I].Arrive));
    const char* Names[5] = {"fcfs", "sstf", "scan", "cscan", "best"};
    const GS::Order Orders[5] = {GS::Fcfs(L), GS::Sstf(L), GS::Scan(L), GS::Cscan(L), GS::Best(L)};
    std::int64_t BestW = 0;
    for (int P = 0; P < 5; ++P) {
        Check(GS::CheckOrder(L, Orders[P]) == GS::Error::None, K.Name + ": habit order is a permutation");
        std::int64_t W = 0, Tr = 0;
        GS::Run(L, Orders[P], W, Tr);
        if (P == 4) BestW = W;
        K.Got.push_back(std::string("P ") + Names[P] + " " + Join(Orders[P]) + " " + std::to_string(W) + " " + std::to_string(Tr));
    }
    for (int P = 0; P < 4; ++P) {  // no habit beats the exhaustive best
        std::int64_t W = 0, Tr = 0;
        GS::Run(L, Orders[P], W, Tr);
        Check(W >= BestW, K.Name + ": best is no worse than a habit");
    }
    // Invariants that hold whatever the golden file says.
    std::int64_t Lo = L.Start, Hi = L.Start;
    for (const GS::Ship& S : L.Ships) {
        Lo = S.Pos < Lo ? S.Pos : Lo;
        Hi = S.Pos > Hi ? S.Pos : Hi;
    }
    std::int64_t MinHabit = -1;
    for (int P = 0; P < 4; ++P) {
        std::int64_t W = 0, Tr = 0;
        GS::Run(L, Orders[P], W, Tr);
        if (MinHabit < 0 || W < MinHabit) MinHabit = W;
    }
    for (int P = 0; P < 5; ++P) {
        std::int64_t W = 0, Tr = 0;
        GS::Run(L, Orders[P], W, Tr);
        Check(W >= 0 && Tr >= Hi - Lo, K.Name + ": waits are non-negative and travel covers the rail span");
        GS::PlayResult R;
        Check(GS::Play(L, Orders[P], R) == GS::Error::None && R.Waits == W && R.Travel == Tr &&
                  (R.V == GS::Verdict::Sweet) == (W == BestW) && (W > MinHabit) == (R.V == GS::Verdict::Jammed),
              K.Name + ": playing a habit or the best order agrees with Run and its verdict");
    }
    const GS::Order& B = Orders[4];
    for (std::size_t I = 0; I + 1 < B.size(); ++I) {  // swapping two neighbours never beats the best
        GS::Order S = B;
        std::swap(S[I], S[I + 1]);
        std::int64_t W = 0, Tr = 0;
        GS::Run(L, S, W, Tr);
        Check(W >= BestW, K.Name + ": no neighbour swap beats the best");
    }
    K.Laid = true;
    ++Layouts;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case* K = new Case;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_gantry_sweep_parity.txt")) {
        if (T[0] == "C" && T.size() == 2) {
            Flush(*K);
            delete K;
            K = new Case;
            K->Name = T[1];
            K->Open = true;
            ++Cases;
            continue;
        }
        if (!K->Open) {
            Check(false, "line before the first case: " + T[0]);
            continue;
        }
        if (T[0] == "S" && T.size() == 3 && !K->Laid) {
            std::string Seed;
            GS::Profile P = GS::Profile::Calm;
            const bool Known = T[1] == "calm" || T[1] == "rush" || T[1] == "spread" || T[1] == "storm";
            if (T[1] == "rush") P = GS::Profile::Rush;
            if (T[1] == "spread") P = GS::Profile::Spread;
            if (T[1] == "storm") P = GS::Profile::Storm;
            if (Known && Unhex(T[2], Seed) && GS::FromSeed(Seed, P, K->L) == GS::Error::None) Lay(*K);
            else K->Ok = false;
        } else if (T[0] == "H" && T.size() == 3 && !K->Laid) {
            std::int64_t Start = 0;
            std::vector<std::pair<std::int64_t, std::int64_t>> PA;
            bool Ok = ToI64(T[1], Start);
            for (const std::string& P : Split(T[2], ',')) {
                const std::vector<std::string> F = Split(P, ':');
                std::pair<std::int64_t, std::int64_t> V{0, 0};
                Ok = F.size() == 2 && ToI64(F[0], V.first) && ToI64(F[1], V.second) && Ok;
                PA.push_back(V);
            }
            if (Ok && GS::MakeHand(Start, PA, K->L) == GS::Error::None) Lay(*K);
            else K->Ok = false;
        } else if (T[0] == "M" && T.size() == 2 && K->Laid) {
            GS::Order O;
            if (T[1] != "-") {
                for (const std::string& P : Split(T[1], ',')) {
                    std::int64_t V = 0;
                    if (!ToI64(P, V) || V > 1000) {
                        K->Ok = false;
                        V = 0;
                    }
                    O.push_back(static_cast<std::size_t>(V));
                }
            }
            GS::PlayResult R;
            const GS::Error E = GS::Play(K->L, O, R);
            K->Got.push_back(E != GS::Error::None ? std::string("refused ") + GS::ErrorName(E)
                                                  : "m " + std::to_string(R.Waits) + " " + std::to_string(R.Travel) + " " + GS::VerdictName(R.V));
            ++Plays;
        } else if (T[0] == "O") {
            K->Want.push_back(Rest(T, 1));
        } else {
            K->Ok = false;
            Check(false, K->Name + ": unknown line " + T[0]);
        }
    }
    Flush(*K);
    delete K;
    Check(Layouts == Cases, "every case laid out");
    return Finish("gantry_sweep", Cases, Plays);
}
