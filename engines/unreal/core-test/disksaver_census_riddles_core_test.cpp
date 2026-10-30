// SPDX-License-Identifier: MIT
// G546 port check: DaedalusDiskSaverCensusRiddlesCore.h replays disksaver_census_riddles_parity.txt
// (written from census_riddles.py by tools/streaming/disksaver_cpp_parity.py, riddles and answers
// included) line for line.
#include "DaedalusDiskSaverCensusRiddlesCore.h"
#include "disksaver_parity.h"

namespace CR = DaedalusDiskSaver::CensusRiddles;
using namespace DiskSaverParity;

static bool Unhex(const std::string& S, std::string& Out) {
    if (S.empty() || S[0] != 'x' || S.size() % 2 == 0) return false;
    Out.clear();
    auto Nib = [](char C) { return C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1; };
    for (std::size_t I = 1; I < S.size(); I += 2) {
        const int A = Nib(S[I]), B = Nib(S[I + 1]);
        if (A < 0 || B < 0) return false;
        Out += static_cast<char>(A * 16 + B);
    }
    return true;
}

int main(int argc, char** argv) {
    Check(CR::Norm(" 1,000 ") == "1000" && CR::Norm("-0") == "0" && CR::Norm("+007") == "7" && CR::Norm("Alpha ") == "alpha" &&
              CR::Norm("+") == "+" && CR::Norm("1 2") == "1 2" && CR::Norm("5 ,") == "5",
          "normalisation");
    Check(CR::Norm(std::string(300, '9')) == std::string(300, '9'), "long numbers do not overflow");
    std::vector<CR::Riddle> Q = {{"r2", "islands_total", "Q?", "1"}};
    Check(!CR::ValidQuiz(Q), "riddle ids must run r1..rN");
    Check(CR::GradeQuiz(Q, {}).Err == CR::Error::BadQuiz, "bad quiz refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_census_riddles_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "N" && T.size() == 3) {
            const bool Neg = !T[1].empty() && T[1][0] == '-';
            int N = -1;
            Check(ToInt(Neg ? T[1].substr(1) : T[1], N), Line + " count");
            Check((CR::ValidCount(Neg ? -N : N) ? "ok" : "count") == T[2], Line + " count check");
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 2) {
            Q.clear();
            for (const std::string& X : Split(T[1], ',')) {
                const auto F = Split(X, '.');
                CR::Riddle R;
                Check(F.size() == 4 && Unhex(F[2], R.Question) && Unhex(F[3], R.Answer), Line + " riddle " + X);
                if (F.size() == 4) {
                    R.Id = F[0];
                    R.Kind = F[1];
                }
                Q.push_back(R);
            }
            Check(CR::ValidQuiz(Q), Line + " quiz");
        } else if (T[0] == "T" && T.size() == 6) {
            ++Trials;
            std::vector<std::pair<std::string, std::string>> A;
            bool Ok = true;
            for (const std::string& X : Split(T[1], ',')) {
                const auto F = Split(X, '.');
                std::string K, V;
                Ok = Ok && F.size() == 2 && Unhex(F[0], K) && Unhex(F[1], V);
                A.push_back({K, V});
            }
            Check(Ok, Line + " answers");
            const CR::Grade G = CR::GradeQuiz(Q, A);
            std::string Flags;
            for (bool B : G.Correct) Flags += B ? '1' : '0';
            Check(G.Err == CR::Error::None && std::to_string(G.Score) == T[2] && std::to_string(G.OutOf) == T[3] && Flags == T[4] &&
                      T[5] == CR::VerdictName(G.V),
                  Line + " got " + std::to_string(G.Score) + " " + Flags + " " + CR::VerdictName(G.V));
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("census_riddles", Cases, Trials);
}
