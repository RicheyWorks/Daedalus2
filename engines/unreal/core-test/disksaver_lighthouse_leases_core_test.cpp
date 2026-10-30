// SPDX-License-Identifier: MIT
// G171 port check: DaedalusDiskSaverLighthouseLeasesCore.h replays disksaver_lighthouse_leases_parity.txt
// (written from lighthouse_leases.py by tools/streaming/disksaver_cpp_parity.py, recorded draws included) line for line.
#include <algorithm>
#include "DaedalusDiskSaverLighthouseLeasesCore.h"
#include "disksaver_parity.h"

namespace LL = DaedalusDiskSaver::LighthouseLeases;
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

static bool ParseConfig(const std::vector<std::string>& T, LL::Config& X) {
    return T.size() == 10 && ToLong(T[1], X.Keepers) && ToLong(T[2], X.Lease) && ToLong(T[3], X.Epochs) &&
           ToLong(T[4], X.WritePermille) && ToLong(T[5], X.MaxDriftPermille) && ToLong(T[6], X.PausePermille) &&
           ToLong(T[7], X.MaxPause) && ToLong(T[8], X.NewsDelay) && ToLong(T[9], X.Guard);
}

int main(int argc, char** argv) {
    Check(LL::LocalElapsed(7, -200) == 5 && LL::DriftBound(20, 150) == 3, "elapsed and drift bound");
    Check(LL::LastValidElapsed(10, 1000, 0) == -1, "a stopped clock is refused, not an endless scan");
    LL::Config C;
    Check(LL::Run(C, LL::Mode::Fenced, {}).Err == LL::Error::BadConfig, "empty config refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    LL::Config Base;
    std::vector<std::string> BaseTokens;
    bool SeenLayout = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_lighthouse_leases_parity.txt")) {
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
        if (T[0] == "D" && T.size() == 6) {
            long long L = 0, D = 0, G = 0, B = 0, E = 0;
            Check(ToLong(T[1], L) && ToLong(T[2], D) && ToLong(T[3], G) && ToLong(T[4], B) && ToLong(T[5], E) &&
                      LL::DriftBound(L, D) == B && LL::LastValidElapsed(L, D, G) == E,
                  Line + " drift");
        } else if (T[0] == "B" || T[0] == "L") {
            LL::Config X;
            Check(ParseConfig(T, X), Line + " config");
            (T[0] == "B" ? Base : C) = X;
        } else if (T[0] == "V" && T.size() == 4) {
            LL::Config X = Base;
            long long V = 0;
            Check(ToLong(T[2], V), Line + " value");
            if (T[1] == "lease") X.Lease = V;
            else if (T[1] == "epochs") X.Epochs = V;
            else if (T[1] == "write_permille") X.WritePermille = V;
            else if (T[1] == "max_drift_permille") X.MaxDriftPermille = V;
            else if (T[1] == "pause_permille") X.PausePermille = V;
            else if (T[1] == "max_pause") X.MaxPause = V;
            else if (T[1] == "news_delay") X.NewsDelay = V;
            else if (T[1] == "guard") X.Guard = V;
            else Check(false, Line + " field");
            Check((LL::ValidConfig(X) ? "ok" : "err") == T[3], Line + " validate");
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "T" && T.size() == 9) {
            ++Trials;
            const LL::Mode M = T[1] == "none" ? LL::Mode::None : T[1] == "naive" ? LL::Mode::Naive : T[1] == "guard" ? LL::Mode::Guard : LL::Mode::Fenced;
            const std::vector<long long> Draws = Longs(T[2], Ok);
            Check(Ok, Line + " tape");
            const LL::Result R = LL::Run(C, M, Draws);
            const std::string Got = std::to_string(R.Writes) + " " + std::to_string(R.Accepted) + " " + std::to_string(R.Rejected) + " " +
                                    std::to_string(R.Stale) + " " + std::to_string(R.Outside) + " " + (R.Won ? "won" : "failed");
            const std::string Want = T[3] + " " + T[4] + " " + T[5] + " " + T[6] + " " + T[7] + " " + T[8];
            Check(R.Err == LL::Error::None && Got == Want, Line + " " + T[1] + " got " + LL::ErrorName(R.Err) + " " + Got);
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    Check(!BaseTokens.empty() && SeenLayout, "base config and layouts present");
    return Finish("lighthouse_leases", Cases, Trials);
}
