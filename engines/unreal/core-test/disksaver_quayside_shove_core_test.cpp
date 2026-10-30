// SPDX-License-Identifier: MIT
// G558 port check: DaedalusDiskSaverQuaysideShoveCore.h replays disksaver_quayside_shove_parity.txt
// (written from quayside_shove.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverQuaysideShoveCore.h"
#include "disksaver_parity.h"

namespace QS = DaedalusDiskSaver::QuaysideShove;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    QS::Yard Y;
    Check(!QS::ParseYard({"#######", "#     #"}, Y), "short yard refused");
    Check(!QS::ParseYard({"#######", "#@$. ##", "#     #", "#     #", "#     #", "#      ", "#######"}, Y),
          "open border refused");
    Check(!QS::ParseYard({"#######", "#@$.  #", "#  $  #", "#     #", "#     #", "#     #", "#######"}, Y),
          "more crates than marks refused");
    Check(!QS::ParseYard({"#######", "#@$.? #", "#     #", "#     #", "#     #", "#     #", "#######"}, Y),
          "unknown cell refused");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_quayside_shove_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            Check(QS::ParseYard(Split(T[1], '/'), Y), Line + " yard");
        } else if (T[0] == "P" && T.size() == 3) {
            int Got = -1;
            std::string Plan;
            const bool Ok = QS::Solve(Y, Y.Player, Y.Crates, Got, Plan);
            Par = Ok ? Got : -1;
            Check((Ok ? std::to_string(Got) : "-1") == T[1] && (Ok && !Plan.empty() ? Plan : "-") == T[2],
                  Line + " got " + std::to_string(Par) + " " + Plan);
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 8)) {
            ++Trials;
            const QS::Result R = QS::Play(Y, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != QS::Error::None && T[3] == QS::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == QS::Error::None && T.size() == 8 && T[2] == "ok" && std::to_string(R.Steps) == T[3] &&
                          std::to_string(R.Pushes) == T[4] && std::to_string(R.OnMarks) == T[5] &&
                          T[6] == QS::VerdictName(R.V) && T[7] == (R.Deadlocked ? "1" : "0"),
                      Line + " got " + std::to_string(R.Steps) + " " + std::to_string(R.Pushes) + " " +
                          std::to_string(R.OnMarks) + " " + QS::VerdictName(R.V) + " " + (R.Deadlocked ? "1" : "0"));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("quayside_shove", Cases, Trials);
}
