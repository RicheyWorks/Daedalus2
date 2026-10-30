// SPDX-License-Identifier: MIT
// G564 port check: DaedalusDiskSaverRopeRunCore.h replays disksaver_rope_run_parity.txt
// (written from rope_run.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverRopeRunCore.h"
#include "disksaver_parity.h"

namespace RR = DaedalusDiskSaver::RopeRun;
using namespace DiskSaverParity;

static int CellOf(const std::string& S) {
    const std::vector<int> P = Ints(S, '.');
    Check(P.size() == 2 && P[0] < RR::Rows && P[1] < RR::Cols, "bad cell " + S);
    return P.size() == 2 ? P[0] * RR::Cols + P[1] : -1;
}

int main(int argc, char** argv) {
    RR::Quay Q;
    Check(!RR::ValidQuay(Q), "quay with no start refused");
    Q.Start = 0;
    Q.Dock = 1;
    Q.Grip[0] = Q.Grip[1] = 1;
    Q.Grip[2] = RR::MaxGrip + 1;
    Check(!RR::ValidQuay(Q), "grip over the cap refused");
    Q.Grip[2] = 0;
    int Par = -1;
    std::string Route;
    Check(RR::Solve(Q, Par, Route) == RR::Error::None && Par == 2 && Route == "E", "two-square quay");

    std::string Case;
    int Cases = 0, Trials = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_rope_run_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 4) {
            Q = RR::Quay{};
            const std::vector<std::string> Rows = Split(T[1], '/');
            Check(Rows.size() == static_cast<std::size_t>(RR::Rows), Line + " rows");
            for (std::size_t r = 0; r < Rows.size() && r < static_cast<std::size_t>(RR::Rows); ++r) {
                Check(Rows[r].size() == static_cast<std::size_t>(RR::Cols), Line + " row width");
                for (std::size_t c = 0; c < Rows[r].size() && c < static_cast<std::size_t>(RR::Cols); ++c) {
                    const char Ch = Rows[r][c];
                    Check(Ch == '#' || (Ch >= '1' && Ch <= '9'), Line + " cell");
                    Q.Grip[r * RR::Cols + c] = Ch == '#' ? 0 : Ch - '0';
                }
            }
            Q.Start = CellOf(T[2]);
            Q.Dock = CellOf(T[3]);
            Check(RR::ValidQuay(Q), Line + " quay");
        } else if (T[0] == "P" && T.size() == 4) {
            const RR::Error E = RR::Solve(Q, Par, Route);
            Check(E == RR::Error::None && std::to_string(Par) == T[1] && (Route.empty() ? "-" : Route) == T[2] &&
                      std::to_string(RR::Greedy(Q)) == T[3],
                  Line + " got " + std::to_string(Par) + " " + Route + " " + std::to_string(RR::Greedy(Q)));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const RR::Result R = RR::Play(Q, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != RR::Error::None && T[3] == RR::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == RR::Error::None && T.size() == 6 && T[2] == "ok" && std::to_string(R.Grip) == T[3] &&
                          T[4] == (R.OnDock ? "1" : "0") && T[5] == RR::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Grip) + " " + RR::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("rope_run", Cases, Trials);
}
