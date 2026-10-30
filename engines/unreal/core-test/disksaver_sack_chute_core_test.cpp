// SPDX-License-Identifier: MIT
// G559 port check: DaedalusDiskSaverSackChuteCore.h replays disksaver_sack_chute_parity.txt
// (written from sack_chute.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverSackChuteCore.h"
#include "disksaver_parity.h"

namespace SC = DaedalusDiskSaver::SackChute;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    Check(!SC::ValidChute({}), "empty chute refused");
    Check(!SC::ValidChute({SC::MaxSacks, 1}), "too many sacks refused");
    Check(SC::Play({1, -1}, 0, {}).Err == SC::Error::BadChute, "negative bin refused");
    SC::Bins B{9, 0};
    Check(SC::Sow(B, 0) == 3 && B == SC::Bins{3, 3}, "sow laps the loop and banks each pass");

    SC::Bins Start;
    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    std::vector<int> Plan;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_sack_chute_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            Start = Ints(T[1], ',');
            Check(SC::ValidChute(Start), Line + " chute");
        } else if (T[0] == "P" && T.size() == 4) {
            Check(SC::Solve(Start, Par, Plan), Line + " solve");
            std::vector<int> One;
            for (int I : Plan) One.push_back(I + 1);
            Check(std::to_string(Par) == T[1] && std::to_string(SC::Greedy(Start)) == T[2] && Join(One, ',') == T[3],
                  Line + " got " + std::to_string(Par) + " " + std::to_string(SC::Greedy(Start)) + " " + Join(One, ','));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const SC::Result R = SC::Play(Start, Par, Ints(T[1], ','));
            if (T[2] == "err") {
                Check(R.Err != SC::Error::None && T[3] == SC::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == SC::Error::None && T.size() == 6 && T[2] == "ok" && std::to_string(R.InHold) == T[3] &&
                          Join(R.Left, ',') == T[4] && T[5] == SC::VerdictName(R.V),
                      Line + " got " + std::to_string(R.InHold) + " " + Join(R.Left, ',') + " " + SC::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("sack_chute", Cases, Trials);
}
