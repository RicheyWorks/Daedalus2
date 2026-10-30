// SPDX-License-Identifier: MIT
// G566 port check: DaedalusDiskSaverTramShuntCore.h replays disksaver_tram_shunt_parity.txt
// (written from tram_shunt.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverTramShuntCore.h"
#include "disksaver_parity.h"

namespace TS = DaedalusDiskSaver::TramShunt;
using namespace DiskSaverParity;

static std::string PlanText(const std::vector<int>& P) {
    std::string S;
    for (std::size_t i = 0; i < P.size(); ++i) S += (i ? "," : "") + std::string(TS::MoveName(P[i]));
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    Check(!TS::ValidTrain({}), "empty train refused");
    Check(!TS::ValidTrain({1, 3}), "gap in the numbers refused");
    Check(!TS::ValidTrain(std::vector<int>(TS::MaxWagons + 1, 1)), "train over the cap refused");
    TS::Move M{};
    Check(TS::ParseMove("inout", M) && !TS::ParseMove("in", M) && !TS::ParseMove("outA", M) && TS::ParseMove("AA", M),
          "FROM+TO grammar (AA parses, then is impossible)");

    std::vector<int> Order;
    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_tram_shunt_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            Order = Ints(T[1], ',');
            Check(TS::ValidTrain(Order), Line + " train");
        } else if (T[0] == "P" && T.size() == 4) {
            std::vector<int> Plan;
            Check(TS::Solve(Order, Par, Plan) == TS::Error::None, Line + " solve");
            const int G = TS::Greedy(Order);
            Check(std::to_string(Par) == T[1] && PlanText(Plan) == T[2] && std::to_string(G) == T[3],
                  Line + " got " + std::to_string(Par) + " " + PlanText(Plan) + " " + std::to_string(G));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const TS::Result R = TS::Play(Order, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != TS::Error::None && T[3] == TS::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == TS::Error::None && T.size() == 6 && T[2] == "ok" && std::to_string(R.Count) == T[3] &&
                          std::to_string(R.Out) == T[4] && T[5] == TS::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Count) + " " + std::to_string(R.Out) + " " + TS::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("tram_shunt", Cases, Trials);
}
