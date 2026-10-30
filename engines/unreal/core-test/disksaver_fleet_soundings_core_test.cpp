// SPDX-License-Identifier: MIT
// G551 port check: DaedalusDiskSaverFleetSoundingsCore.h replays disksaver_fleet_soundings_parity.txt
// (written from fleet_soundings.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverFleetSoundingsCore.h"
#include "disksaver_parity.h"

namespace FS = DaedalusDiskSaver::FleetSoundings;
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

static std::string Joined(const std::vector<std::string>& V, char Sep) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? std::string(1, Sep) : "") + V[I];
    return S;
}

int main(int argc, char** argv) {
    FS::Puzzle P;
    P.Size = FS::MaxSize + 1;
    P.Lengths = {1};
    P.Rows.assign(P.Size, 0);
    P.Cols.assign(P.Size, 0);
    Check(!FS::ValidPuzzle(P), "grid over the cap refused");
    P.Size = 3;
    P.Lengths = {1, 2};
    P.Rows = {1, 1, 1};
    P.Cols = {1, 1, 1};
    Check(!FS::ValidPuzzle(P), "fleet must be longest first");
    std::vector<std::uint64_t> Sols;
    P.Lengths = {2, 1};
    P.Rows = {2, 0, 1};
    P.Cols = {1, 1, 1};
    Check(FS::Solve(P, false, 5, Sols) == FS::Error::None && !Sols.empty(), "small fleet solves");
    Check(FS::Check(P, {"##", ".."}).Problems.size() == 1, "short grid is one problem, not a crash");

    std::string Case;
    int Cases = 0, Trials = 0;
    bool Valid = false;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_fleet_soundings_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 7) {
            P = FS::Puzzle{};
            Check(ToInt(T[1], P.Size), Line + " size");
            P.Lengths = Ints(T[2], ',');
            P.Rows = Ints(T[3], ',');
            P.Cols = Ints(T[4], ',');
            for (const std::string& H : Split(T[5], ',')) {
                const auto F = Split(H, '.');
                FS::Hint X;
                int Hull = -1;
                Check(F.size() == 3 && ToInt(F[0], X.Row) && ToInt(F[1], X.Col) && ToInt(F[2], Hull) && Hull <= 1, Line + " hint " + H);
                X.Hull = Hull == 1;
                P.Hints.push_back(X);
            }
            Valid = FS::ValidPuzzle(P);
            Check(Valid, Line + " puzzle");
            if (Valid) {
                const FS::Result R = FS::Check(P, Split(T[6], '/'));
                Check(R.V == FS::Verdict::Charted, Line + " the solution charts");
            }
        } else if (T[0] == "S" && T.size() == 5) {
            int Limit = -1, Hints = -1, Count = -1;
            Check(ToInt(T[1], Limit) && ToInt(T[2], Hints) && ToInt(T[3], Count), Line + " numbers");
            std::vector<std::string> Got;
            const FS::Error E = FS::Solve(P, Hints == 1, Limit, Sols);
            if (E == FS::Error::None)
                for (std::uint64_t M : Sols) Got.push_back(Joined(FS::GridOf(P.Size, M), '/'));
            const std::string G = Got.empty() ? "-" : Joined(Got, ';');
            Check(Valid && E == FS::Error::None && static_cast<int>(Sols.size()) == Count && G == T[4], Line + " got " + G);
        } else if (T[0] == "T" && T.size() == 4) {
            ++Trials;
            std::string Text, Want;
            Check(Valid && Unhex(T[1], Text) && Unhex(T[3], Want), Line + " hex");
            std::vector<std::string> Grid;
            std::string Cur;
            for (char C : Text) {
                if (C == '\n') {
                    Grid.push_back(Cur);
                    Cur.clear();
                } else {
                    Cur += C;
                }
            }
            if (!Text.empty()) Grid.push_back(Cur);
            const FS::Result R = FS::Check(P, Grid);
            const std::string Got = Joined(R.Problems, '\n');
            Check(R.Err == FS::Error::None && T[2] == FS::VerdictName(R.V) && Got == Want, Line + " got " + FS::VerdictName(R.V) + " " + Got);
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("fleet_soundings", Cases, Trials);
}
