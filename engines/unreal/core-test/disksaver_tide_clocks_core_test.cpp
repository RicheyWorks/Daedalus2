// SPDX-License-Identifier: MIT
// G166 port check: DaedalusDiskSaverTideClocksCore.h replays disksaver_tide_clocks_parity.txt
// (written from tide_clocks.py by tools/streaming/disksaver_cpp_parity.py, recorded draws included) line for line.
#include <algorithm>
#include "DaedalusDiskSaverTideClocksCore.h"
#include "disksaver_parity.h"

namespace TC = DaedalusDiskSaver::TideClocks;
using namespace DiskSaverParity;

// Signed decimal lists for the recorded tapes: optional '-', then up to 18 strict digits, no leading zeros.
static bool ToLong(const std::string& S, long long& Out) {
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
static std::vector<long long> Longs(const std::string& S, bool& Ok) {
    std::vector<long long> Out;
    for (const std::string& T : Split(S, ',')) {
        long long V = 0;
        Ok = ToLong(T, V) && Ok;
        Out.push_back(V);
    }
    return Out;
}
static std::string JoinL(const std::vector<long long>& V) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I]);
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    TC::Config C;
    C.Islands = 2;
    C.Saves = 1;
    C.Steps = TC::MaxSteps + 1;
    C.EditPermille = 500;
    Check(TC::Run(C, TC::Clock::Vector, {}).Err == TC::Error::Capped, "steps over the cap refused");
    C.Steps = 3;
    Check(TC::Run(C, TC::Clock::Vector, {0, 0, 5}).Err == TC::Error::Tape, "short tape refused");
    Check(TC::Run(C, TC::Clock::Vector, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}).Err == TC::Error::Tape, "unused draws refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    long long G86 = 0, Kpi = 0;
    TC::Config Base;
    std::vector<long long> Draws;
    std::vector<std::string> BaseTokens;
    bool SeenLayout = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_tide_clocks_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "B") {
            BaseTokens.assign(T.begin() + 1, T.end());
            SeenLayout = false;
        } else if (T[0] == "L" && !SeenLayout) {
            SeenLayout = true;
            Check(BaseTokens.size() + 1 >= T.size() && std::equal(T.begin() + 1, T.end(), BaseTokens.begin()),
                  Line + " first layout must be the B base config");
        }
        bool Ok = true;
        if (T[0] == "K" && T.size() == 3) {
            Check(ToLong(T[1], G86) && ToLong(T[2], Kpi), Line + " limits");
        } else if ((T[0] == "B" || T[0] == "L") && T.size() == 6) {
            TC::Config X;
            Ok = ToLong(T[1], X.Islands) && ToLong(T[2], X.Saves) && ToLong(T[3], X.Steps) && ToLong(T[4], X.EditPermille) &&
                 ToLong(T[5], X.MaxSkewTicks);
            Check(Ok, Line + " config");
            (T[0] == "B" ? Base : C) = X;
        } else if (T[0] == "V" && T.size() == 4) {
            TC::Config X = Base;
            long long V = 0;
            Check(ToLong(T[2], V), Line + " value");
            if (T[1] == "islands") X.Islands = V;
            else if (T[1] == "saves") X.Saves = V;
            else if (T[1] == "steps") X.Steps = V;
            else if (T[1] == "edit_permille") X.EditPermille = V;
            else if (T[1] == "max_skew") X.MaxSkewTicks = V;
            else Check(false, Line + " field");
            Check((TC::ValidConfig(X, G86, Kpi) ? "ok" : "err") == T[3], Line + " validate");
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "R" && T.size() == 2) {
            Draws = Longs(T[1], Ok);
            Check(Ok, Line + " tape");
        } else if (T[0] == "T" && T.size() == 10) {
            ++Trials;
            const TC::Clock K = T[1] == "wall" ? TC::Clock::Wall : T[1] == "lamport" ? TC::Clock::Lamport : TC::Clock::Vector;
            const TC::Result R = TC::Run(C, K, Draws);
            std::vector<long long> Lost(R.LostVids.begin(), R.LostVids.end());
            const std::string Got = std::string(R.Won ? "won" : "failed") + " " + std::to_string(R.Edits) + " " + std::to_string(R.Lost) +
                                    " " + std::to_string(R.Detected) + " " + std::to_string(R.Oracle) + " " +
                                    std::to_string(R.Inversions) + " " + std::to_string(R.Survivors) + " " + JoinL(Lost);
            const std::string Want = T[2] + " " + T[3] + " " + T[4] + " " + T[5] + " " + T[6] + " " + T[7] + " " + T[8] + " " + T[9];
            Check(R.Err == TC::Error::None && Got == Want, Line + " " + T[1] + " got " + TC::ErrorName(R.Err) + " " + Got);
            if (K == TC::Clock::Vector) Check(R.Detected == R.Oracle, Line + " vector clocks detect the oracle's conflicts");
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    Check(!BaseTokens.empty() && SeenLayout, "base config and layouts present");
    return Finish("tide_clocks", Cases, Trials);
}
