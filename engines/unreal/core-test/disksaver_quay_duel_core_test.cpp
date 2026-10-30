// SPDX-License-Identifier: MIT
// G550 port check: DaedalusDiskSaverQuayDuelCore.h replays disksaver_quay_duel_parity.txt
// (written from quay_duel.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverQuayDuelCore.h"
#include "disksaver_parity.h"

namespace QD = DaedalusDiskSaver::QuayDuel;
using namespace DiskSaverParity;

static bool ToSigned(const std::string& S, std::int64_t& Out) {
    const bool Neg = !S.empty() && S[0] == '-';
    const std::string D = Neg ? S.substr(1) : S;
    if (D.empty() || D.size() > 15 || (D.size() > 1 && D[0] == '0') || (Neg && D == "0")) return false;
    std::int64_t V = 0;
    for (char C : D) {
        if (C < '0' || C > '9') return false;
        V = V * 10 + (C - '0');
    }
    Out = Neg ? -V : V;
    return true;
}

int main(int argc, char** argv) {
    std::vector<std::int64_t> V(QD::MaxCrates + 1, 1);
    Check(QD::Duel(V, false, {}, true, false).Err == QD::Error::BadQuay, "quay over the cap refused");
    V.assign(QD::MaxCrates, QD::MaxValue);
    const QD::Result Big = QD::Duel(V, false, {}, true, false);
    Check(Big.Err == QD::Error::None && Big.O == QD::Outcome::Tied && Big.You == QD::MaxValue * QD::MaxCrates / 2, "full quay of heavy crates ties");
    Check(QD::Duel({1}, true, {"L"}, true, false).Err == QD::Error::Mode, "moves with auto is a mode error");

    std::string Case;
    int Cases = 0, Trials = 0;
    std::int64_t Par = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_quay_duel_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            V.clear();
            for (const std::string& X : Split(T[1], ',')) {
                std::int64_t Y = -1;
                Check(ToSigned(X, Y), Line + " value " + X);
                V.push_back(Y);
            }
            Check(QD::ValidQuay(V), Line + " quay");
        } else if (T[0] == "P" && T.size() == 2) {
            Check(ToSigned(T[1], Par) && QD::ValidQuay(V) && QD::Margins(V).At(0, static_cast<int>(V.size()) - 1) == Par, Line + " margin");
        } else if (T[0] == "T" && (T.size() == 5 || T.size() == 10)) {
            ++Trials;
            int Second = -1;
            Check(ToInt(T[1], Second) && Second <= 1, Line + " side");
            const bool Auto = T[2] == "auto" || T[2] == "both";
            const bool HasMoves = T[2] != "auto";
            const std::vector<std::string> Moves = HasMoves && T[2] != "both" ? Split(T[2], ',') : std::vector<std::string>{};
            std::vector<std::string> Mine = Moves;
            if (T[2] == "both") {  // the generator passes the perfect line's own moves with --auto
                const QD::Result A = QD::Duel(V, false, {}, true, Second == 1);
                Mine.clear();
                for (std::size_t I = Second == 1 ? 1 : 0; I < A.Moves.size(); I += 2) Mine.push_back(std::string(1, A.Moves[I]));
            }
            const QD::Result R = QD::Duel(V, HasMoves, Mine, Auto, Second == 1);
            if (T[3] == "err") {
                Check(T.size() == 5 && R.Err != QD::Error::None && T[4] == QD::ErrorName(R.Err), Line + " want err " + T[4] + " got " + QD::ErrorName(R.Err));
            } else {
                Check(R.Err == QD::Error::None && T.size() == 10 && T[3] == "ok" && std::to_string(R.You) == T[4] &&
                          std::to_string(R.Casimir) == T[5] && std::to_string(R.BestForYou) == T[6] && std::to_string(R.GaveAway) == T[7] &&
                          R.Moves == T[8] && T[9] == QD::OutcomeName(R.O),
                      Line + " got " + std::to_string(R.You) + " " + std::to_string(R.Casimir) + " " + R.Moves + " " + QD::OutcomeName(R.O));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("quay_duel", Cases, Trials);
}
