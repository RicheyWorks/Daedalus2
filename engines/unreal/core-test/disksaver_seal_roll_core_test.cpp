// SPDX-License-Identifier: MIT
// G560 port check: DaedalusDiskSaverSealRollCore.h replays disksaver_seal_roll_parity.txt
// (written from seal_roll.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverSealRollCore.h"
#include "disksaver_parity.h"

namespace SR = DaedalusDiskSaver::SealRoll;
using namespace DiskSaverParity;

static int CellOf(const std::string& S) {
    const std::vector<int> P = Ints(S, '.');
    Check(P.size() == 2, "bad cell " + S);
    return P.size() == 2 ? P[0] * SR::Size + P[1] : -1;
}

int main(int argc, char** argv) {
    SR::Quay Q;
    Check(!SR::ValidQuay(Q), "quay with no marks refused");
    Check(SR::TipSeal(SR::Up, 0) == SR::North && SR::TipSeal(SR::East, 1) == SR::East, "tip table");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_seal_roll_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 5) {
            Q = SR::Quay{};
            const std::vector<std::string> Rows = Split(T[1], '/');
            Check(Rows.size() == static_cast<std::size_t>(SR::Size), Line + " rows");
            for (std::size_t r = 0; r < Rows.size() && r < static_cast<std::size_t>(SR::Size); ++r) {
                Check(Rows[r].size() == static_cast<std::size_t>(SR::Size), Line + " row width");
                for (std::size_t c = 0; c < Rows[r].size() && c < static_cast<std::size_t>(SR::Size); ++c) {
                    Check(Rows[r][c] == '#' || Rows[r][c] == '_', Line + " cell");
                    Q.Walls[r * SR::Size + c] = Rows[r][c] == '#';
                }
            }
            for (const std::string& M : Split(T[2], ',')) Q.Marks.push_back(CellOf(M));
            Q.Dock = CellOf(T[3]);
            Q.Start = CellOf(T[4]);
            Check(SR::ValidQuay(Q), Line + " quay");
        } else if (T[0] == "P" && T.size() == 3) {
            int Got = -1;
            std::string Plan;
            const bool Ok = SR::Solve(Q, Got, Plan);
            Par = Ok ? Got : -1;
            Check((Ok ? std::to_string(Got) : "-1") == T[1] && (Ok && !Plan.empty() ? Plan : "-") == T[2],
                  Line + " got " + std::to_string(Par) + " " + Plan);
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 8)) {
            ++Trials;
            const SR::Result R = SR::Play(Q, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != SR::Error::None && T[3] == SR::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                std::string St;
                for (int i = 0; i < SR::MaxMarks; ++i)
                    if (R.Stamped >> i & 1u) St += static_cast<char>('a' + i);
                if (St.empty()) St = "-";
                Check(R.Err == SR::Error::None && T.size() == 8 && T[2] == "ok" && std::to_string(R.Count) == T[3] &&
                          St == T[4] && T[5] == SR::SideName(R.Seal) && T[6] == (R.OnDock ? "1" : "0") &&
                          T[7] == SR::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Count) + " " + St + " " + SR::SideName(R.Seal) + " " +
                          SR::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("seal_roll", Cases, Trials);
}
