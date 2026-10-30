// SPDX-License-Identifier: MIT
// G554 port check: DaedalusDiskSaverTideLockCore.h replays disksaver_tide_lock_parity.txt
// (written from tide_lock.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverTideLockCore.h"
#include "disksaver_parity.h"

namespace TL = DaedalusDiskSaver::TideLock;
using namespace DiskSaverParity;

// Plan sizes may be zero or negative in the golden file: optional '-' then ToInt's strict digits.
static bool ToSigned(const std::string& S, std::int64_t& Out) {
    int V = 0;
    if (!S.empty() && S[0] == '-') {
        if (!ToInt(S.substr(1), V) || V == 0) return false;
        Out = -static_cast<std::int64_t>(V);
        return true;
    }
    if (!ToInt(S, V)) return false;
    Out = V;
    return true;
}

static std::vector<std::int64_t> Sizes(const std::string& S, bool& Ok) {
    std::vector<std::int64_t> Out;
    for (const std::string& T : Split(S, ',')) {
        std::int64_t V = 0;
        Ok = ToSigned(T, V) && Ok;
        Out.push_back(V);
    }
    return Out;
}

static std::string JoinS(const std::vector<std::int64_t>& V) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I]);
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    TL::Lock G;
    G.Chamber = 10;
    G.Cycle = 0;
    G.Queue = {{1, 0}};
    Check(TL::Validate(G) == TL::Error::Param, "zero cycle refused");
    G.Cycle = 5;
    G.Queue.assign(TL::MaxBoats + 1, TL::Boat{1, 0});
    Check(TL::Validate(G) == TL::Error::BadQueue, "queue over the cap refused");
    G.Queue = {{1, 0}};
    Check(TL::Play(G, 0, std::vector<std::int64_t>(TL::MaxPlan + 1, 0)).Err == TL::Error::TooLong, "over-long plan refused");
    Check(TL::Play(G, 0, {1000000000, -999999999}).V == TL::Verdict::Jammed, "huge sizes jam without overflow");

    std::string Case;
    int Cases = 0, Trials = 0;
    std::int64_t Opt = -1;
    bool Solved = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_tide_lock_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
            Solved = false;
        } else if (T[0] == "L" && T.size() == 4) {
            G = TL::Lock{};
            int C = -1, Y = -1;
            Check(ToInt(T[1], C) && ToInt(T[2], Y), Line + " chamber/cycle");
            G.Chamber = C;
            G.Cycle = Y;
            for (const std::string& B : Split(T[3], ',')) {
                const auto LA = Split(B, ':');
                int Len = -1, Arr = -1;
                Check(LA.size() == 2 && ToInt(LA[0], Len) && ToInt(LA[1], Arr), Line + " boat " + B);
                G.Queue.push_back({Len, Arr});
            }
        } else if (T[0] == "P" && T.size() == 3 && T[1] == "err") {
            std::int64_t C = 0;
            std::vector<std::int64_t> P;
            const TL::Error E = TL::Optimum(G, C, P);
            Check(E != TL::Error::None && T[2] == TL::ErrorName(E), Line + " want refusal " + T[2] + " got " + TL::ErrorName(E));
        } else if (T[0] == "P" && T.size() == 5) {
            std::vector<std::int64_t> Plan;
            Solved = TL::Optimum(G, Opt, Plan) == TL::Error::None;
            const std::vector<std::int64_t> Gr = TL::Greedy(G);
            const TL::Result GR = TL::Play(G, Opt, Gr);
            Check(Solved && std::to_string(Opt) == T[1] && JoinS(Plan) == T[2] && JoinS(Gr) == T[3] &&
                      GR.R.J == TL::Jam::None && std::to_string(GR.R.Wait) == T[4],
                  Line + " got " + std::to_string(Opt) + " " + JoinS(Plan) + " " + JoinS(Gr) + " " + std::to_string(GR.R.Wait));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 5)) {
            ++Trials;
            Check(Solved, Line + " play on an unsolved lock");
            bool Ok = true;
            std::vector<std::int64_t> S;
            if (T[1] == "auto") {
                std::int64_t C = 0;
                TL::Optimum(G, C, S);
            } else {
                S = Sizes(T[1], Ok);
            }
            Check(Ok, Line + " plan parse");
            const TL::Result R = TL::Play(G, Opt, S);
            if (T[2] == "jam") {
                const std::string Kind = R.R.J == TL::Jam::Plan ? "plan" : R.R.J == TL::Jam::Group ? "group" + std::to_string(R.R.Group) : "none";
                Check(R.Err == TL::Error::None && T.size() == 4 && R.V == TL::Verdict::Jammed && Kind == T[3], Line + " got " + Kind);
            } else {
                Check(R.Err == TL::Error::None && T.size() == 5 && T[2] == "ok" && std::to_string(R.R.Wait) == T[3] &&
                          T[4] == TL::VerdictName(R.V),
                      Line + " got " + std::to_string(R.R.Wait) + " " + TL::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("tide_lock", Cases, Trials);
}
