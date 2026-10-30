// SPDX-License-Identifier: MIT
// G565 port check: DaedalusDiskSaverBelfryChangesCore.h replays disksaver_belfry_changes_parity.txt
// (written from belfry_changes.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverBelfryChangesCore.h"
#include "disksaver_parity.h"

namespace BC = DaedalusDiskSaver::BelfryChanges;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    BC::Ring G;
    G.Start = {1, 1, 2};
    G.Islands = 1;
    G.Tenor = 1;
    Check(!BC::ValidRing(G), "repeated bell refused");
    G.Start.assign(BC::MaxBells + 1, 1);
    Check(!BC::ValidRing(G), "ring over the cap refused");
    Check(BC::AllChanges(4, false).size() == 4 && BC::AllChanges(4, true).size() == 3, "change counts for four bells");
    std::vector<BC::Change> C;
    Check(BC::ParseChanges(5, "1 + 3, ,-1", C) == BC::Error::Range, "negative place is out of range, not a crash");
    Check(BC::ParseChanges(5, "99999999999999", C) == BC::Error::Range, "huge place saturates");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    bool Solved = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_belfry_changes_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 4) {
            G = BC::Ring{};
            G.Start = Ints(T[1], ',');
            Check(ToInt(T[2], G.Islands) && ToInt(T[3], G.Tenor) && BC::ValidRing(G), Line + " ring");
        } else if (T[0] == "P" && T.size() == 4) {
            std::vector<BC::Change> Plan, SPlan;
            int SPar = -1;
            Solved = BC::Solve(G, false, Par, Plan) == BC::Error::None;
            const bool S2 = BC::Solve(G, true, SPar, SPlan) == BC::Error::None;
            Check(Solved && S2 && std::to_string(Par) == T[1] && BC::ChangeText(Plan) == T[2] && std::to_string(SPar) == T[3],
                  Line + " got " + std::to_string(Par) + " " + BC::ChangeText(Plan) + " " + std::to_string(SPar));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 7)) {
            ++Trials;
            Check(Solved, Line + " play on an unsolved ring");
            const BC::Result R = BC::Play(G, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != BC::Error::None && T[3] == BC::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == BC::Error::None && T.size() == 7 && T[2] == "ok" && std::to_string(R.Count) == T[3] &&
                          Join(R.Final, ',') == T[4] && Join(R.Led, ',') == T[5] && T[6] == BC::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Count) + " " + Join(R.Final, ',') + " " + Join(R.Led, ',') + " " +
                          BC::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("belfry_changes", Cases, Trials);
}
