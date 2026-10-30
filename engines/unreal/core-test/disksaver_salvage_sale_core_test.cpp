// SPDX-License-Identifier: MIT
// G563 port check: DaedalusDiskSaverSalvageSaleCore.h replays disksaver_salvage_sale_parity.txt
// (written from salvage_sale.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverSalvageSaleCore.h"
#include "disksaver_parity.h"

namespace SS = DaedalusDiskSaver::SalvageSale;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    SS::Sale S;
    Check(!SS::ValidSale(S), "empty sale refused");
    S.Values = {SS::MaxValue + 1};
    Check(!SS::ValidSale(S), "value over the cap refused");
    S.Values = {4, 6};
    S.Coin = 3;
    Check(SS::Play(S, 0, "99999999999999999999,0").Err == SS::Error::Coin, "huge bid saturates, then is over the coin");
    Check(SS::Play(S, 0, "1,,").Err == SS::Error::Count && SS::Play(S, 0, "1,+1").Err == SS::Error::Count,
          "bid text needs one whole number per lot");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_salvage_sale_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 3) {
            S = SS::Sale{};
            S.Values = Ints(T[1], ',');
            Check(ToInt(T[2], S.Coin) && SS::ValidSale(S), Line + " sale");
        } else if (T[0] == "P" && T.size() == 4) {
            std::vector<int> Plan;
            Check(SS::Solve(S, Par, Plan), Line + " solve");
            Check(std::to_string(Par) == T[1] && Join(Plan, ',') == T[2] && std::to_string(SS::Greedy(S)) == T[3],
                  Line + " got " + std::to_string(Par) + " " + Join(Plan, ',') + " " + std::to_string(SS::Greedy(S)));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const SS::Result R = SS::Play(S, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != SS::Error::None && T[3] == SS::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == SS::Error::None && T.size() == 6 && T[2] == "ok" && std::to_string(R.Score) == T[3] &&
                          R.Winners == T[4] && T[5] == SS::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Score) + " " + R.Winners + " " + SS::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("salvage_sale", Cases, Trials);
}
