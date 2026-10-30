// SPDX-License-Identifier: MIT
// G562 port check: DaedalusDiskSaverBoomDefenceCore.h replays disksaver_boom_defence_parity.txt
// (written from boom_defence.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverBoomDefenceCore.h"
#include "disksaver_parity.h"

namespace BD = DaedalusDiskSaver::BoomDefence;
using namespace DiskSaverParity;

static std::vector<BD::Cell> Cells(const std::string& S) {
    std::vector<BD::Cell> Out;
    for (const std::string& T : Split(S, ',')) {
        const std::vector<int> P = Ints(T, '.');
        Check(P.size() == 2, "bad cell " + T);
        if (P.size() == 2) Out.emplace_back(P[0], P[1]);
    }
    return Out;
}

static std::string Letters(const std::vector<int>& V) {
    std::string S;
    for (int I : V) S += static_cast<char>('A' + I);
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    BD::ChartData C;
    Check(!BD::ValidChart(C), "empty chart refused");
    C.Path = {{3, 0}, {3, 1}};
    C.Hulls = {BD::MaxHull + 1};
    Check(!BD::ValidChart(C), "hull over the cap refused");
    C.Hulls = {1};
    C.Sites = {{2, 1}};
    std::vector<int> Chosen;
    Check(BD::ParsePosts(C, " a ,", Chosen) == BD::Error::None && Chosen == std::vector<int>{0}, "post text trims and upcases");
    Check(BD::ParsePosts(C, "B", Chosen) == BD::Error::Site, "letter past the sites refused");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_boom_defence_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 4) {
            C = BD::ChartData{};
            C.Path = Cells(T[1]);
            C.Sites = Cells(T[2]);
            C.Hulls = Ints(T[3], ',');
            Check(BD::ValidChart(C), Line + " chart");
        } else if (T[0] == "P" && T.size() == 5) {
            std::vector<int> Combo, Pick;
            Par = BD::Best(C, Combo);
            const int G = BD::Greedy(C, Pick);
            Check(std::to_string(Par) == T[1] && Letters(Combo) == T[2] && std::to_string(G) == T[3] &&
                      Letters(Pick) == T[4],
                  Line + " got " + std::to_string(Par) + " " + Letters(Combo) + " " + std::to_string(G) + " " +
                      Letters(Pick));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const BD::Result R = BD::Play(C, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != BD::Error::None && T[3] == BD::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == BD::Error::None && T.size() == 6 && T[2] == "ok" && std::to_string(R.Through) == T[3] &&
                          R.Fates == T[4] && T[5] == BD::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Through) + " " + R.Fates + " " + BD::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("boom_defence", Cases, Trials);
}
