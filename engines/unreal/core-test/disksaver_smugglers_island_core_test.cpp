// SPDX-License-Identifier: MIT
// G553 port check: DaedalusDiskSaverSmugglersIslandCore.h replays disksaver_smugglers_island_parity.txt
// (written from smugglers_island.py by tools/streaming/disksaver_cpp_parity.py, hidden island included)
// line for line.
#include "DaedalusDiskSaverSmugglersIslandCore.h"
#include "disksaver_parity.h"

namespace SI = DaedalusDiskSaver::SmugglersIsland;
using namespace DiskSaverParity;

static std::string LogText(const std::vector<SI::Asked>& L) {
    std::string S;
    for (const SI::Asked& A : L) S += (S.empty() ? "" : ",") + A.Id + "/" + (A.Yes ? "y" : "n") + "/" + std::to_string(A.Left);
    return S.empty() ? "-" : S;
}

int main(int argc, char** argv) {
    std::vector<SI::Suspect> S = {{"b:0", "b", "none", 0, 0}, {"a:0", "a", "none", 0, 0}};
    Check(!SI::ValidSuspects(S, 0), "unsorted suspects refused");
    S = {{"a:0", "a", "none", 0, 0}};
    Check(!SI::ValidSuspects(S, 1), "hidden index out of range refused");
    Check(SI::Play(S, 0, true, false, {}, true, "a:0").Err == SI::Error::Mode, "auto with an accusation is a mode error");
    Check(SI::Play(S, 0, false, true, {}, false, "").Err == SI::Error::Accuse, "asks without an accusation refused");
    S.clear();
    for (int I = 0; I < SI::MaxSuspects; ++I) S.push_back({"z:" + std::string(1, static_cast<char>('A' + I / 26)) + static_cast<char>('a' + I % 26), "z", "none", I, 0});
    const SI::Result Big = SI::Play(S, SI::MaxSuspects - 1, true, false, {}, false, "");
    Check(Big.Err == SI::Error::None && Big.Optimal == 6 && Big.V == SI::Verdict::Sharp, "forty suspects by slot halve in six questions");

    std::string Case;
    int Cases = 0, Trials = 0, Hidden = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_smugglers_island_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 3) {
            S.clear();
            Check(ToInt(T[1], Hidden), Line + " hidden");
            for (const std::string& X : Split(T[2], ',')) {
                const auto F = Split(X, '|');
                SI::Suspect P;
                Check(F.size() == 5 && ToInt(F[3], P.Slot) && ToInt(F[4], P.Cargo), Line + " suspect " + X);
                if (F.size() == 5) {
                    P.Label = F[0];
                    P.World = F[1];
                    P.Realm = F[2];
                }
                S.push_back(P);
            }
            Check(SI::ValidSuspects(S, Hidden), Line + " suspects");
        } else if (T[0] == "P" && T.size() == 3) {
            const std::vector<SI::Question> Qs = SI::Questions(S);
            std::string Ids;
            for (const SI::Question& Q : Qs) Ids += (Ids.empty() ? "" : ",") + Q.Id;
            SI::Solver Sv(Qs);
            const int D = Sv.Depth(S.size() >= 64 ? ~std::uint64_t{0} : SI::Bit(static_cast<int>(S.size())) - 1);
            Check(std::to_string(D) == T[1] && (Ids.empty() ? "-" : Ids) == T[2], Line + " got " + std::to_string(D) + " " + Ids);
        } else if (T[0] == "T" && T.size() >= 5) {
            ++Trials;
            const bool AutoLine = T[1] == "auto";
            const bool Mix = T[3] == "mix";
            const std::size_t K = Mix ? 4 : 3;
            const bool HasAccuse = !AutoLine && T[2] != "-";
            const SI::Result R = SI::Play(S, Hidden, AutoLine || Mix, !AutoLine, AutoLine ? std::vector<std::string>{} : Split(T[1], ','),
                                          HasAccuse, HasAccuse ? T[2] : "");
            if (T[K] == "err") {
                Check(T.size() == K + 2 && R.Err != SI::Error::None && T[K + 1] == SI::ErrorName(R.Err),
                      Line + " want err " + T[K + 1] + " got " + SI::ErrorName(R.Err));
            } else {
                std::vector<std::string> Still;
                for (int I : R.Still) Still.push_back(S[I].Label);
                std::string St;
                for (const std::string& X : Still) St += (St.empty() ? "" : ",") + X;
                Check(R.Err == SI::Error::None && T.size() == 8 && T[3] == "ok" && LogText(R.Log) == T[4] && R.Accused == T[5] &&
                          St == T[6] && T[7] == SI::VerdictName(R.V),
                      Line + " got " + SI::ErrorName(R.Err) + " " + LogText(R.Log) + " " + R.Accused + " " + St + " " + SI::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("smugglers_island", Cases, Trials);
}
