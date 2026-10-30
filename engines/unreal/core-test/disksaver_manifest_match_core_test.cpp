// SPDX-License-Identifier: MIT
// G556 port check: DaedalusDiskSaverManifestMatchCore.h replays disksaver_manifest_match_parity.txt
// (written from manifest_match.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverManifestMatchCore.h"
#include "disksaver_parity.h"

namespace MM = DaedalusDiskSaver::ManifestMatch;
using namespace DiskSaverParity;

static std::vector<MM::Turn> Turns(const std::string& S) {
    std::vector<MM::Turn> Out;
    for (const std::string& T : Split(S, ',')) {
        const std::vector<int> P = Ints(T, '-');
        Check(P.size() == 2, "bad turn " + T);
        if (P.size() == 2) Out.emplace_back(P[0], P[1]);
    }
    return Out;
}

static std::string TurnText(const std::vector<MM::Turn>& V) {
    if (V.empty()) return "-";
    std::string S;
    for (std::size_t i = 0; i < V.size(); ++i)
        S += (i ? "," : "") + std::to_string(V[i].first + 1) + "-" + std::to_string(V[i].second + 1);
    return S;
}

int main(int argc, char** argv) {
    // direct edges
    Check(!MM::ValidTable({0, 0, 1}), "odd table refused");
    Check(!MM::ValidTable({0, 0, 0, 1}), "triple refused");
    Check(MM::Play({0, 1}, {}).Err == MM::Error::BadTable, "bad table is an error, not a crash");
    std::vector<MM::Turn> Best;
    Check(MM::PerfectTurns({0, 0}, Best) && Best.size() == 1, "one pair, one turn");

    std::vector<int> Ids;
    std::string Case;
    int Cases = 0, Trials = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_manifest_match_parity.txt")) {
        const std::string Line = Case + ":" + (T.empty() ? "" : T[0]) + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            Ids = Ints(T[1], ',');
            Check(MM::ValidTable(Ids), Line + " table");
        } else if (T[0] == "P" && T.size() == 3) {
            Check(MM::PerfectTurns(Ids, Best), Line + " par solver");
            Check(std::to_string(Best.size()) == T[1], Line + " par " + std::to_string(Best.size()));
            Check(TurnText(Best) == T[2], Line + " perfect plan " + TurnText(Best));
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 6)) {
            ++Trials;
            const MM::Result R = MM::Play(Ids, Turns(T[1]));
            if (T[2] == "err") {
                Check(R.Err != MM::Error::None && T[3] == MM::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                std::string Hits;
                for (bool H : R.Hits) Hits += H ? '1' : '0';
                if (Hits.empty()) Hits = "-";
                Check(R.Err == MM::Error::None && T.size() == 6 && T[2] == "ok" &&
                          std::to_string(R.MatchedPairs) == T[3] && Hits == T[4] && T[5] == MM::VerdictName(R.V),
                      Line + " got " + std::to_string(R.MatchedPairs) + " " + Hits + " " + MM::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("manifest_match", Cases, Trials);
}
