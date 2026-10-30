// SPDX-License-Identifier: MIT
// G598 Tidelinks Golf check: DaedalusDiskSaverTidelinksGolfCore.h replays disksaver_tidelinks_golf_parity.txt
// (written by tools/streaming/tidelinks_golf_parity.py from CPython's random.Random(str)): each case lays out
// a course from its seed string or hand line, then every expected layout, habit, best-card and play line must match.
#include "DaedalusDiskSaverTidelinksGolfCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

using namespace DiskSaverParity;
namespace TG = DaedalusDiskSaver::TidelinksGolf;

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

static std::string Join(const TG::Card& C) {
    if (C.empty()) return "none";
    std::string S;
    for (std::size_t I = 0; I < C.size(); ++I) {
        if (I) S += "/";
        if (C[I].empty()) S += "-";
        for (std::size_t K = 0; K < C[I].size(); ++K) {
            if (K) S += ",";
            S += TG::ClubCodes[C[I][K]];
        }
    }
    return S;
}

static std::string ToPar(std::int64_t N) { return N == 0 ? "E" : (N > 0 ? "+" : "") + std::to_string(N); }

static bool ToSigned(const std::string& S, std::int64_t& Out) {
    if (!S.empty() && S[0] == '-') {
        if (S == "-0" || !ToI64(S.substr(1), Out)) return false;
        Out = -Out;
        return true;
    }
    return ToI64(S, Out);
}

static std::vector<std::string> SplitKeep(const std::string& S, char Sep) {  // the shared Split reads "-" as empty
    std::vector<std::string> Out(1);
    for (char C : S) {
        if (C == Sep) Out.emplace_back();
        else Out.back() += C;
    }
    return Out;
}

struct Case {
    std::string Name;
    bool Open = false, Ok = true, Laid = false, Refused = false;
    std::vector<TG::Hole> Hs;
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
    const std::vector<TG::Hole>& Hs = K.Hs;
    K.Got.push_back("L " + std::to_string(Hs.size()) + " " + std::to_string(TG::CoursePar(Hs)));
    for (std::size_t I = 0; I < Hs.size(); ++I)
        K.Got.push_back("R " + std::to_string(I) + " " + Hs[I].Name + " " + std::to_string(Hs[I].Length) + " " +
                        std::to_string(TG::Par(Hs[I].Length)) + " " + std::to_string(Hs[I].Wind) + " " + std::to_string(Hs[I].Water));
    const char* Names[4] = {"safe", "bold", "layup", "best"};
    const TG::Card Cards[4] = {TG::HabitCard(Hs, TG::Habit::Safe), TG::HabitCard(Hs, TG::Habit::Bold),
                               TG::HabitCard(Hs, TG::Habit::Layup), TG::BestCard(Hs)};
    std::int64_t T[4];
    for (int P = 0; P < 4; ++P) {
        T[P] = TG::RawStrokes(Hs, Cards[P]);
        K.Got.push_back(std::string("P ") + Names[P] + " " + Join(Cards[P]) + " " + std::to_string(T[P]));
    }
    // Invariants that hold whatever the golden file says.
    for (int P = 0; P < 3; ++P) Check(T[P] >= T[3], K.Name + ": best is no worse than a habit");
    TG::PlayResult R;
    Check(TG::Play(Hs, Cards[3], R) == TG::Error::None && R.V == TG::Verdict::Masterful && R.Strokes == T[3],
          K.Name + ": the best card plays masterful");
    for (std::size_t I = 0; I < Hs.size(); ++I) {
        Check(!Cards[3][I].empty() && Cards[3][I].size() <= 10, K.Name + ": best hole length");
        for (int C = 0; C < TG::NumClubs; ++C)  // no first shot beats the best by holing in fewer strokes
            if (TG::Hit(Hs[I], 0, C).Holed) Check(Cards[3][I].size() == 1, K.Name + ": an ace is found");
    }
    K.Laid = true;
    ++Layouts;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case* K = new Case;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_tidelinks_golf_parity.txt")) {
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
            if (Unhex(T[1], Seed) && TG::FromSeed(Seed, K->Hs) == TG::Error::None) Lay(*K);
            else K->Ok = false;
        } else if (T[0] == "H" && T.size() == 2 && !K->Laid) {
            std::vector<TG::HandHole> HH;
            bool Ok = true;
            if (T[1] != "-") {
                for (const std::string& P : SplitKeep(T[1], ',')) {
                    const std::vector<std::string> F = SplitKeep(P, ':');
                    TG::HandHole V;
                    Ok = F.size() == 3 && ToI64(F[0], V.Length) && ToSigned(F[1], V.Wind) && ToI64(F[2], V.Water) && Ok;
                    if (HH.size() > 64) Ok = false;
                    HH.push_back(V);
                }
            }
            const TG::Error E = Ok ? TG::MakeHand(HH, K->Hs) : TG::Error::None;
            if (!Ok) K->Ok = false;
            else if (E == TG::Error::None) Lay(*K);
            else {  // a refused hand course: no layout, no plays
                K->Got.push_back(std::string("hand_refused ") + TG::ErrorName(E));
                K->Laid = true;
                K->Refused = true;
                ++Layouts;
            }
        } else if (T[0] == "M" && T.size() == 2 && K->Laid && !K->Refused) {
            TG::Card C;
            if (T[1] != "none") {
                for (const std::string& H : SplitKeep(T[1], '/')) {
                    TG::Clubs Cs;
                    if (H != "-")
                        for (const std::string& X : SplitKeep(H, ',')) {
                            if (X.size() != 1) K->Ok = false;
                            Cs.push_back(X.size() == 1 ? TG::ClubIndex(X[0]) : -1);
                        }
                    C.push_back(Cs);
                }
            }
            TG::PlayResult R;
            const TG::Error E = TG::Play(K->Hs, C, R);
            K->Got.push_back(E != TG::Error::None ? std::string("refused ") + TG::ErrorName(E) + " " + std::to_string(R.BadHole)
                                                  : "m " + std::to_string(R.Strokes) + " " + ToPar(R.ToPar) + " " + TG::VerdictName(R.V));
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
    return Finish("tidelinks_golf", Cases, Plays);
}
