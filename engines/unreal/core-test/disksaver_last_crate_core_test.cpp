// SPDX-License-Identifier: MIT
// G549 port check: DaedalusDiskSaverLastCrateCore.h replays disksaver_last_crate_parity.txt
// (written from last_crate.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverLastCrateCore.h"
#include "disksaver_parity.h"

namespace LC = DaedalusDiskSaver::LastCrate;
using namespace DiskSaverParity;

static std::string TurnsText(const std::vector<LC::Turn>& Turns) {
    std::string S;
    for (const LC::Turn& T : Turns)
        S += (S.empty() ? "" : ",") + T.A.Bust + ";" + T.A.Load + ";" + T.A.Sail + ";" + (T.A.AdviseLoad ? "load" : "sail") + ";" +
             (T.Load ? "load" : "sail");
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    Check(LC::FractionText(6, 4) == "3/2" && LC::FractionText(0, 7) == "0" && LC::FractionText(8, 4) == "2", "fraction text");
    std::vector<std::int64_t> D(LC::MaxCrates, LC::MaxWeight);
    Check(LC::Play(D, LC::MaxKib, false, {}, true).Err == LC::Error::None, "full stack of heavy crates plays without overflow");
    D.push_back(1);
    Check(LC::Play(D, 5, false, {}, true).Err == LC::Error::BadStack, "stack over the cap refused");
    Check(LC::Play({1}, 0, true, {"sail"}, false).Err == LC::Error::Hold, "zero hold refused first");

    std::string Case;
    int Cases = 0, Trials = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_last_crate_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            D.clear();
            for (int W : Ints(T[1], ',')) D.push_back(W);
        } else if (T[0] == "T" && (T.size() == 5 || T.size() == 8)) {
            ++Trials;
            int Hold = -1;
            Check(ToInt(T[1], Hold), Line + " hold");
            const bool Auto = T[2] == "auto" || T[2] == "both";
            const bool HasMoves = T[2] != "auto";
            const std::vector<std::string> Moves = T[2] == "both" ? std::vector<std::string>{"sail"} : HasMoves ? Split(T[2], ',') : std::vector<std::string>{};
            const LC::Result R = LC::Play(D, Hold, HasMoves, Moves, Auto);
            if (T[3] == "err") {
                Check(T.size() == 5 && R.Err != LC::Error::None && T[4] == LC::ErrorName(R.Err), Line + " want err " + T[4] + " got " + LC::ErrorName(R.Err));
            } else {
                Check(R.Err == LC::Error::None && T.size() == 8 && T[3] == "ok" && std::to_string(R.Carried) == T[4] &&
                          std::to_string(R.Best) == T[5] && T[6] == LC::OutcomeName(R.O) && TurnsText(R.Turns) == T[7],
                      Line + " got " + std::to_string(R.Carried) + " " + LC::OutcomeName(R.O) + " " + TurnsText(R.Turns));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("last_crate", Cases, Trials);
}
