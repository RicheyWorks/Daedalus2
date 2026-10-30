// SPDX-License-Identifier: MIT
// G557 port check: DaedalusDiskSaverTwinPilotsCore.h replays disksaver_twin_pilots_parity.txt
// (written from twin_pilots.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverTwinPilotsCore.h"
#include "disksaver_parity.h"

namespace TP = DaedalusDiskSaver::TwinPilots;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    TP::Chart C;
    Check(!TP::MakeChart(TP::MaxNodes + 1, {}, C), "oversized chart refused");
    Check(!TP::MakeChart(3, {{0, 3}}, C), "edge off the chart refused");
    Check(TP::MakeChart(1, {}, C), "harbour alone");
    int Par = -1;
    TP::Route Ra, Rb;
    Check(TP::Solve(C, Par, Ra, Rb) == TP::Error::None && Par == 0 && TP::SoloBells(C) == 0, "nothing to call");

    std::string Case;
    int Cases = 0, Trials = 0;
    bool Solved = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_twin_pilots_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "") + (T.size() > 2 ? " " + T[2] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 3) {
            int N = 0;
            Check(ToInt(T[1], N), Line + " n");
            std::vector<TP::Edge> E;
            for (const std::string& S : Split(T[2], ',')) {
                const std::vector<int> P = Ints(S, '-');
                if (P.size() == 2) E.emplace_back(P[0], P[1]);
            }
            Check(TP::MakeChart(N, E, C), Line + " chart");
        } else if (T[0] == "P") {
            const TP::Error E = TP::Solve(C, Par, Ra, Rb);
            Solved = E == TP::Error::None;
            if (T.size() == 3 && T[1] == "err") {
                Check(!Solved && T[2] == TP::ErrorName(E), Line + " want " + T[2]);
            } else {
                Check(Solved && T.size() == 5 && std::to_string(Par) == T[1] &&
                          std::to_string(TP::SoloBells(C)) == T[2] && Join(Ra, '.') == T[3] && Join(Rb, '.') == T[4],
                      Line + " got " + std::to_string(Par) + " " + std::to_string(TP::SoloBells(C)) + " " +
                          Join(Ra, '.') + " " + Join(Rb, '.'));
            }
        } else if (T[0] == "T" && (T.size() == 5 || T.size() == 8)) {
            ++Trials;
            Check(Solved, Line + " play on an unsolved chart");
            const TP::Grade G = TP::Play(C, Par, Ints(T[1], '.'), Ints(T[2], '.'));
            if (T[3] == "err") {
                Check(G.Err != TP::Error::None && T[4] == TP::ErrorName(G.Err), Line + " want err " + T[4]);
            } else {
                Check(G.Err == TP::Error::None && T.size() == 8 && T[3] == "ok" && std::to_string(G.Bells) == T[4] &&
                          std::to_string(G.Missed) == T[5] && T[6] == (G.Home ? "1" : "0") &&
                          T[7] == TP::VerdictName(G.V),
                      Line + " got " + std::to_string(G.Bells) + " " + std::to_string(G.Missed) + " " +
                          TP::VerdictName(G.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("twin_pilots", Cases, Trials);
}
