// SPDX-License-Identifier: MIT
// G555 port check: DaedalusDiskSaverWatchfiresCore.h replays disksaver_watchfires_parity.txt
// (written from watchfires.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverWatchfiresCore.h"
#include "disksaver_parity.h"

namespace WF = DaedalusDiskSaver::Watchfires;
using namespace DiskSaverParity;

int main(int argc, char** argv) {
    WF::Chart G;
    G.Labels = {"a:0", "a:0"};
    Check(!WF::ValidChart(G), "repeated label refused");
    G.Labels = {"a:0", "a:1"};
    G.Edges = {{1, 0}};
    Check(!WF::ValidChart(G), "edge must be i < j");
    G.Edges = {{0, 1}, {0, 1}};
    Check(!WF::ValidChart(G), "repeated edge refused");
    G.Labels.assign(WF::MaxIslands + 1, "x");
    for (int I = 0; I <= WF::MaxIslands; ++I) G.Labels[I] = "x:" + std::to_string(I);
    G.Edges.clear();
    Check(!WF::ValidChart(G), "chart over the cap refused");
    G.Labels.resize(WF::MaxIslands);
    int K = -1;
    std::vector<int> B;
    Check(WF::Par(G, K, B) == WF::Error::None && K == WF::MaxIslands, "forty isolated islands need forty fires (bit 39 safe)");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    std::vector<int> Best;
    bool Solved = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_watchfires_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 3) {
            G = WF::Chart{};
            G.Labels = Split(T[1], ',');
            for (const std::string& E : Split(T[2], ',')) {
                const auto AB = Split(E, '-');
                int A = -1, Bv = -1;
                Check(AB.size() == 2 && ToInt(AB[0], A) && ToInt(AB[1], Bv), Line + " edge " + E);
                G.Edges.push_back({A, Bv});
            }
            Check(WF::ValidChart(G), Line + " chart");
        } else if (T[0] == "P" && T.size() == 4) {
            Solved = WF::Par(G, Par, Best) == WF::Error::None;
            const std::vector<int> Gr = WF::Greedy(G);
            Check(Solved && std::to_string(Par) == T[1] && Join(Best, ',') == T[2] && Join(Gr, ',') == T[3],
                  Line + " got " + std::to_string(Par) + " " + Join(Best, ',') + " " + Join(Gr, ','));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            Check(Solved, Line + " play on an unsolved chart");
            const bool Auto = T[1] == "auto";
            const WF::Result R = WF::Play(G, Par, Best, Auto, Auto ? std::vector<std::string>{} : Split(T[1], ','));
            if (T[2] == "err") {
                Check(R.Err != WF::Error::None && T[3] == WF::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == WF::Error::None && T.size() == 6 && T[2] == "ok" && Join(R.Fires, ',') == T[3] &&
                          Join(R.Unlit, ',') == T[4] && T[5] == WF::VerdictName(R.V),
                      Line + " got " + Join(R.Fires, ',') + " " + Join(R.Unlit, ',') + " " + WF::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("watchfires", Cases, Trials);
}
