// SPDX-License-Identifier: MIT
// G552 port check: DaedalusDiskSaverHarbourCryptogramCore.h replays disksaver_harbour_cryptogram_parity.txt
// (written from harbour_cryptogram.py by tools/streaming/disksaver_cpp_parity.py, cipher, key and
// plain text included) line for line.
#include "DaedalusDiskSaverHarbourCryptogramCore.h"
#include "disksaver_parity.h"

namespace HC = DaedalusDiskSaver::HarbourCryptogram;
using namespace DiskSaverParity;

// "x" + lowercase hex of the UTF-8 bytes; false on anything else.
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

static std::string Spaced(const std::string& S, char From, char To) {
    std::string O = S;
    std::replace(O.begin(), O.end(), From, To);
    return O;
}

static bool Letters(const std::string& S, std::array<char, 26>& Out) {
    Out = {};
    for (const std::string& P : Split(S, ',')) {
        if (P.size() != 3 || P[1] != '=' || !HC::IsAlpha(P[0]) || !HC::IsAlpha(P[2]) || Out[P[0] - 'A']) return false;
        Out[P[0] - 'A'] = P[2];
    }
    return true;
}

int main(int argc, char** argv) {
    std::string W;
    Check(HC::NumberWords(-1, W) == HC::Error::Negative, "negative count refused");
    Check(HC::NumberWords(HC::MaxNumber + 1, W) == HC::Error::TooLong, "huge count refused");
    Check(HC::Clean("  sea,  stop!\ttea ") == "SEA STOP TEA", "clean collapses and trims");
    HC::Puzzle P;
    P.Plain = "AB";
    P.Cipher = "AC";
    P.Key['A' - 'A'] = 'A';
    P.Key['C' - 'A'] = 'B';
    Check(!HC::ValidPuzzle(P), "a letter standing for itself is refused");
    std::string Reads;
    Check(HC::ApplyMapping(P, std::vector<std::pair<std::string, std::string>>(HC::MaxPairs + 1), Reads) == HC::Error::TooLong,
          "over-long mapping refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    bool Valid = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_harbour_cryptogram_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "N" && T.size() == 3) {
            int N = -1;
            Check(ToInt(T[1], N) && HC::NumberWords(N, W) == HC::Error::None && Spaced(W, ' ', '_') == T[2], Line + " got " + W);
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 5) {
            P = HC::Puzzle{};
            P.Cipher = Spaced(T[1], '_', ' ');
            P.Plain = Spaced(T[2], '_', ' ');
            Valid = Letters(T[3], P.Key) && Letters(T[4], P.Given) && HC::ValidPuzzle(P);
            Check(Valid, Line + " puzzle");
        } else if (T[0] == "F" && T.size() == 3) {
            std::string F;
            for (const auto& KV : HC::Frequency(P.Cipher)) F += (F.empty() ? "" : ",") + std::string(1, KV.first) + ":" + std::to_string(KV.second);
            Check(F == T[1] && Spaced(HC::Board(P), ' ', '.') == T[2], Line + " got " + F + " " + HC::Board(P));
        } else if (T[0] == "T" && T[1] == "g" && T.size() == 6) {
            ++Trials;
            std::string G;
            Check(Valid && Unhex(T[2], G), Line + " guess");
            const HC::Grade R = HC::GradeGuess(P, G);
            Check(R.Err == HC::Error::None && std::to_string(R.Right) == T[3] && std::to_string(R.Letters) == T[4] &&
                      T[5] == HC::VerdictName(R.V),
                  Line + " got " + std::to_string(R.Right) + " " + std::to_string(R.Letters) + " " + HC::VerdictName(R.V));
        } else if (T[0] == "T" && T[1] == "m" && (T.size() == 5 || T.size() == 8)) {
            ++Trials;
            std::vector<std::pair<std::string, std::string>> M;
            bool Ok = Valid;
            for (const std::string& KV : Split(T[2], ',')) {
                const auto Two = Split(KV, '.');
                std::string K, V;
                Ok = Ok && Two.size() == 2 && Unhex(Two[0], K) && Unhex(Two[1], V);
                M.push_back({K, V});
            }
            Check(Ok, Line + " mapping");
            const HC::Error E = HC::ApplyMapping(P, M, Reads);
            if (T[3] == "err") {
                Check(T.size() == 5 && E != HC::Error::None && T[4] == HC::ErrorName(E), Line + " want err " + T[4]);
            } else {
                std::string Want;
                Check(E == HC::Error::None && T.size() == 8 && T[3] == "ok" && Unhex(T[4], Want) && Want == Reads, Line + " reads " + Reads);
                const HC::Grade R = HC::GradeGuess(P, Reads);
                Check(std::to_string(R.Right) == T[5] && std::to_string(R.Letters) == T[6] && T[7] == HC::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Right) + " " + HC::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("harbour_cryptogram", Cases, Trials);
}
