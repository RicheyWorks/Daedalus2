// SPDX-License-Identifier: MIT
// G179 port check: DaedalusDiskSaverBottleCensusCore.h replays disksaver_bottle_census_parity.txt
// (written from bottle_census.py by tools/streaming/disksaver_cpp_parity.py, recorded draws included) line for line.
#include <algorithm>
#include "DaedalusDiskSaverBottleCensusCore.h"
#include "disksaver_parity.h"

namespace BC = DaedalusDiskSaver::BottleCensus;
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

static bool ParseConfig(const std::vector<std::string>& T, BC::Config& X) {
    bool Ok = T.size() == 10;
    if (!Ok) return false;
    X.Weights = Longs(T[1], Ok);
    return Ok && ToLong(T[2], X.CreditsPerWeight) && ToLong(T[3], X.Ticks) && ToLong(T[4], X.SendPermille) &&
           ToLong(T[5], X.MaxAmount) && ToLong(T[6], X.MaxDelay) && ToLong(T[7], X.Start) && ToLong(T[8], X.MaxSkew) &&
           ToLong(T[9], X.Initiator);
}

int main(int argc, char** argv) {
    BC::Config C;
    Check(BC::Run(C, BC::Mode::Marker, true, {}).Err == BC::Error::BadConfig, "empty config refused");
    C.Weights = {1, 1};
    C.CreditsPerWeight = 1;
    C.Ticks = 2;
    C.SendPermille = 0;
    C.MaxAmount = 1;
    C.MaxDelay = 1;
    C.Start = 0;
    C.MaxSkew = 0;
    Check(BC::Run(C, BC::Mode::Sync, true, {0, 0, 7}).Err == BC::Error::Tape, "unused draws refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    BC::Config Base;
    std::vector<std::string> BaseTokens;
    bool SeenLayout = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_bottle_census_parity.txt")) {
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
        if (T[0] == "B" || T[0] == "L") {
            BC::Config X;
            Check(ParseConfig(T, X), Line + " config");
            (T[0] == "B" ? Base : C) = X;
        } else if (T[0] == "V" && T.size() == 4) {
            BC::Config X = Base;
            long long V = 0;
            Check(ToLong(T[2], V), Line + " value");
            const std::string& F = T[1];
            if (F == "ticks") X.Ticks = V;
            else if (F == "credits_per_weight") X.CreditsPerWeight = V;
            else if (F == "send_permille") X.SendPermille = V;
            else if (F == "max_amount") X.MaxAmount = V;
            else if (F == "max_delay") X.MaxDelay = V;
            else if (F == "start") X.Start = V;
            else if (F == "max_skew") X.MaxSkew = V;
            else if (F == "initiator") X.Initiator = V;
            else Check(false, Line + " field");
            Check((BC::ValidConfig(X) ? "ok" : "err") == T[3], Line + " validate");
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "T" && T.size() == 14) {
            ++Trials;
            const BC::Mode M = T[1] == "local" ? BC::Mode::Local : T[1] == "sync" ? BC::Mode::Sync : BC::Mode::Marker;
            const bool Fifo = T[2] == "1";
            const std::vector<long long> Draws = Longs(T[3], Ok);
            Check(Ok, Line + " tape");
            const BC::Result R = BC::Run(C, M, Fifo, Draws);
            const std::string Got = std::to_string(R.TrueTotal) + " " + std::to_string(R.Census) + " " + std::to_string(R.Counted) + " " +
                                    std::to_string(R.AtSea) + " " + std::to_string(R.Bottles) + " " + (R.Consistent ? "1" : "0") + " " +
                                    (R.Won ? "won" : "failed") + " " + BC::ReasonName(R.Why) + " " + JoinL(R.Cut) + " " + JoinL(R.Lane);
            std::string Want;
            for (std::size_t I = 4; I < 14; ++I) Want += (I > 4 ? " " : "") + T[I];
            Check(R.Err == BC::Error::None && Got == Want, Line + " " + T[1] + " got " + BC::ErrorName(R.Err) + " " + Got);
            if (R.Err == BC::Error::None && M == BC::Mode::Marker && Fifo)
                Check(R.Lane == R.InTransitOracle && R.Won, Line + " marker lanes equal the in-transit oracle");
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    Check(!BaseTokens.empty() && SeenLayout, "base config and layouts present");
    return Finish("bottle_census", Cases, Trials);
}
