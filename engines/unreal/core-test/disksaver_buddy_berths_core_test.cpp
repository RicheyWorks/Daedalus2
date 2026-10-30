// SPDX-License-Identifier: MIT
// G597 Buddy Berths check: DaedalusDiskSaverBuddyBerthsCore.h replays disksaver_buddy_berths_parity.txt
// (written by tools/streaming/buddy_berths_parity.py from CPython's random.Random(str)): each case lays out
// a quay from its seed string or hand line, then every expected layout, habit, best-plan and play line must match.
#include "DaedalusDiskSaverBuddyBerthsCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

using namespace DiskSaverParity;
namespace BB = DaedalusDiskSaver::BuddyBerths;

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

static std::string Join(const BB::Plan& P) {
    if (P.empty()) return "none";
    std::string S;
    for (std::size_t I = 0; I < P.size(); ++I) S += (I ? "," : "") + (P[I] == BB::Turn ? std::string("-") : std::to_string(P[I]));
    return S;
}

struct Case {
    std::string Name;
    bool Open = false, Ok = true, Laid = false;
    BB::Layout L;
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
    const BB::Layout& L = K.L;
    K.Got.push_back("L " + std::to_string(L.Ships.size()));
    for (std::size_t I = 0; I < L.Ships.size(); ++I)
        K.Got.push_back("R " + std::to_string(I) + " " + L.Ships[I].Label + " " + std::to_string(L.Ships[I].Size) + " " +
                        std::to_string(L.Ships[I].Stay));
    const char* Names[4] = {"lowest", "tightest", "highest", "best"};
    const BB::Plan Plans[4] = {BB::HabitPlan(L, BB::Habit::Lowest), BB::HabitPlan(L, BB::Habit::Tightest),
                               BB::HabitPlan(L, BB::Habit::Highest), BB::Best(L)};
    std::int64_t T[4] = {0, 0, 0, 0};
    for (int P = 0; P < 4; ++P) {
        Check(BB::Simulate(L, Plans[P], T[P]) == BB::Error::None, K.Name + ": habit plan is legal");
        K.Got.push_back(std::string("P ") + Names[P] + " " + Join(Plans[P]) + " " + std::to_string(T[P]));
    }
    for (int P = 0; P < 3; ++P) Check(T[P] >= T[3], K.Name + ": best is no worse than a habit");
    K.Laid = true;
    ++Layouts;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case* K = new Case;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_buddy_berths_parity.txt")) {
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
        if (T[0] == "S" && T.size() == 2 && !K->Laid) {
            std::string Seed;
            if (Unhex(T[1], Seed) && BB::FromSeed(Seed, K->L) == BB::Error::None) Lay(*K);
            else K->Ok = false;
        } else if (T[0] == "H" && T.size() == 2 && !K->Laid) {
            std::vector<std::pair<std::int64_t, std::int64_t>> SS;
            bool Ok = true;
            for (const std::string& P : Split(T[1], ',')) {
                const std::vector<std::string> F = Split(P, ':');
                std::pair<std::int64_t, std::int64_t> V{0, 0};
                Ok = F.size() == 2 && ToI64(F[0], V.first) && ToI64(F[1], V.second) && Ok;
                SS.push_back(V);
            }
            if (Ok && BB::MakeHand(SS, K->L) == BB::Error::None) Lay(*K);
            else K->Ok = false;
        } else if (T[0] == "M" && T.size() == 2 && K->Laid) {
            BB::Plan P;
            if (T[1] == "-") P.push_back(BB::Turn);  // the shared Split reads a lone "-" as empty
            else if (T[1] != "none") {
                for (const std::string& X : Split(T[1], ',')) {
                    std::int64_t V = BB::Turn;
                    if (X != "-" && (!ToI64(X, V) || V > 1000)) {
                        K->Ok = false;
                        V = 0;
                    }
                    P.push_back(V);
                }
            }
            BB::PlayResult R;
            const BB::Error E = BB::Play(K->L, P, R);
            K->Got.push_back(E != BB::Error::None ? std::string("refused ") + BB::ErrorName(E)
                                                  : "m " + std::to_string(R.Turned) + " " + BB::VerdictName(R.V));
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
    return Finish("buddy_berths", Cases, Plays);
}
