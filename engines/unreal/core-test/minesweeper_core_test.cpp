// SPDX-License-Identifier: MIT
// Standalone runtime contract and extracted Java-source transcript parity; no Unreal or GUI.
// Build with the DaedalusLink Public directory on the include path. Pass minesweeper_parity.txt.
#include "DaedalusMinesweeperCore.h"
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::minesweeper;
static int Passed = 0, Total = 0;
static void Check(const std::string& Name, bool OK)
{
    ++Total; Passed += OK;
    std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name.c_str());
}
static const char* OutcomeName(Outcome O)
{
    return O == Outcome::Won ? "Won" : O == Outcome::Lost ? "Lost" : "Playing";
}
static std::string Cells(const Board& B)
{
    std::string Out;
    for (int R = 0; R < B.Rows(); ++R)
        for (int C = 0; C < B.Cols(); ++C)
        {
            const Cell* X = B.At(R, C);
            if (!X) return "missing";
            Out += X->Mine ? '1' : '0';
            Out += X->Revealed ? '1' : '0';
            Out += X->Flagged ? '1' : '0';
            Out += static_cast<char>('0' + X->Adjacent);
        }
    return Out;
}
static std::string Snapshot(const Board& B)
{
    std::ostringstream Out;
    Out << B.Rows() << ' ' << B.Cols() << ' ' << B.MineCount() << ' '
        << OutcomeName(B.Result()) << ' ' << B.Score() << ' '
        << B.RevealedCount() << ' ' << B.FlagCount() << ' ' << Cells(B);
    return Out.str();
}
static void SourceParity(const char* Path)
{
    std::ifstream Input(Path);
    Check("Java-source parity fixture is present", Input.good());
    if (!Input) return;
    Board B;
    std::string Line, CaseName;
    int Cases = 0, Actions = 0, States = 0;
    while (std::getline(Input, Line))
    {
        if (Line.empty() || Line[0] == '#') continue;
        std::istringstream In(Line);
        std::string Kind;
        In >> Kind;
        if (Kind == "case")
        {
            int Rows = 0, Cols = 0, Count = 0;
            In >> CaseName >> Rows >> Cols >> Count;
            std::vector<int> Mines;
            for (int I = 0, Index = 0; I < Count && In >> Index; ++I) Mines.push_back(Index);
            Check(CaseName + " fixture loads", static_cast<int>(Mines.size()) == Count && B.Load(Rows, Cols, Mines));
            ++Cases;
        }
        else if (Kind == "state" || Kind == "action")
        {
            bool Changed = false;
            int ExpectedChange = 0;
            if (Kind == "action")
            {
                std::string Verb;
                int Row = 0, Col = 0;
                std::int64_t Elapsed = 0;
                In >> Verb >> Row >> Col >> Elapsed >> ExpectedChange;
                if (Verb == "reveal") Changed = B.Reveal(Row, Col, Elapsed);
                else if (Verb == "flag") Changed = B.ToggleFlag(Row, Col, Elapsed);
                else { Check(CaseName + " known action", false); continue; }
                Check(CaseName + " action " + std::to_string(Actions) + " changed/no-op", Changed == (ExpectedChange != 0));
                ++Actions;
            }
            std::string ExpectedOutcome, ExpectedCells;
            int Score = -1, Revealed = -1, Flags = -1;
            In >> ExpectedOutcome >> Score >> Revealed >> Flags >> ExpectedCells;
            Check(CaseName + " Java-source state " + std::to_string(States),
                In && ExpectedOutcome == OutcomeName(B.Result()) && Score == B.Score()
                && Revealed == B.RevealedCount() && Flags == B.FlagCount() && ExpectedCells == Cells(B));
            ++States;
        }
        else Check("fixture line is recognized: " + Kind, false);
    }
    Check("parity covers at least ten layouts/scoring cases", Cases >= 10);
    Check("parity exercises at least thirty actions", Actions >= 30);
}
static bool ConsistentLayout(const Board& B)
{
    std::vector<int> Sorted = B.Layout();
    std::sort(Sorted.begin(), Sorted.end());
    if (static_cast<int>(Sorted.size()) != B.MineCount()
        || std::adjacent_find(Sorted.begin(), Sorted.end()) != Sorted.end()) return false;
    for (int R = 0; R < B.Rows(); ++R)
        for (int C = 0; C < B.Cols(); ++C)
        {
            const Cell* X = B.At(R, C);
            if (!X || X->Mine != std::binary_search(Sorted.begin(), Sorted.end(), R * B.Cols() + C)) return false;
        }
    return true;
}
int main(int argc, char** argv)
{
    SourceParity(argc > 1 ? argv[1] : "minesweeper_parity.txt");
    Board B;
    Check("fixed layout accepts unique in-range mine indices", B.Load(4, 4, {15}));
    Check("fixed layout retains exact mine count and cell identity", B.MineCount() == 1 && B.At(3, 3)->Mine && !B.At(0, 0)->Mine);
    Check("negative and past-edge coordinates are absent", !B.At(-1, 0) && !B.At(0, -1) && !B.At(4, 0) && !B.At(0, 4));
    const std::string BeforeInvalid = Snapshot(B);
    const std::vector<std::vector<int>> InvalidLayouts = {{}, {-1}, {16}, {0, 0}, {0, 1, 2, 3}};
    bool InvalidLoadPreserved = true;
    for (const auto& Mines : InvalidLayouts)
    {
        const int Side = Mines.size() == 4 ? 2 : 4;
        InvalidLoadPreserved &= !B.Load(Side, Side, Mines) && Snapshot(B) == BeforeInvalid;
    }
    InvalidLoadPreserved &= !B.Load(0, 4, {1}) && !B.Load(33, 4, {1}) && !B.Load(4, -1, {1})
        && Snapshot(B) == BeforeInvalid;
    Check("invalid layouts and dimensions preserve the live board", InvalidLoadPreserved);
    bool InvalidGeneratePreserved = true;
    struct Config { int Rows, Cols, Mines, SafeR, SafeC; };
    const Config Invalid[] = {{0, 8, 10, 0, 0}, {-1, 8, 10, 0, 0}, {33, 8, 10, 0, 0},
        {8, 33, 10, 0, 0}, {8, 8, 0, 0, 0}, {8, 8, 64, 0, 0}, {8, 8, 10, -1, 0},
        {8, 8, 10, 8, 0}, {8, 8, 10, 0, 8}, {std::numeric_limits<int>::max(), 8, 10, 0, 0}};
    for (const auto& X : Invalid)
        InvalidGeneratePreserved &= !B.Generate(X.Rows, X.Cols, X.Mines, 7, X.SafeR, X.SafeC)
            && Snapshot(B) == BeforeInvalid;
    Check("invalid generation inputs preserve the live board without overflow", InvalidGeneratePreserved);
    Check("invalid actions do not mutate a playing board", !B.Reveal(-1, 0, 0) && !B.ToggleFlag(4, 0, 0)
        && Snapshot(B) == BeforeInvalid);

    bool SafeZones = true, Stable = true, Different = false, Consistent = true;
    std::vector<int> First;
    for (std::uint32_t Seed = 0; Seed < 64; ++Seed)
    {
        Board A, Repeat;
        SafeZones &= A.Generate(8, 8, 10, Seed, 4, 4);
        Stable &= Repeat.Generate(8, 8, 10, Seed, 4, 4) && A.Layout() == Repeat.Layout()
            && Snapshot(A) == Snapshot(Repeat);
        Consistent &= ConsistentLayout(A) && A.RevealedCount() == 0 && A.FlagCount() == 0
            && A.Result() == Outcome::Playing && A.Score() == 0;
        for (int R = 3; R <= 5; ++R) for (int C = 3; C <= 5; ++C)
            SafeZones &= A.At(R, C) && !A.At(R, C)->Mine;
        if (Seed == 0) First = A.Layout();
        else Different |= First != A.Layout();
    }
    Check("64 generated layouts protect the configured 3x3 center zone", SafeZones);
    Check("64 seeds are reproducible under the new runtime RNG", Stable);
    Check("different seeds produce more than one layout", Different);
    Check("generated mine indices agree with fresh concealed board cells", Consistent);
    Check("dense-board fallback protects only the configured safe cell", B.Generate(2, 2, 3, 0, 1, 1)
        && !B.At(1, 1)->Mine && B.At(0, 0)->Mine && B.At(0, 1)->Mine && B.At(1, 0)->Mine);
    Check("a 1x2 dense board remains playable", B.Generate(1, 2, 1, 0, 0, 1) && B.Reveal(0, 1, 0)
        && B.Result() == Outcome::Won);
    Check("the 32x32 upper bound is supported", B.Generate(32, 32, 1023, 42, 31, 31)
        && ConsistentLayout(B) && !B.At(31, 31)->Mine);
    Check("generation does not reveal the safe cell before an action", B.RevealedCount() == 0);
    Check("a generated terminal board can start a fresh game", B.Reveal(31, 31, 0)
        && B.Result() == Outcome::Won && B.Generate(8, 8, 10, 99) && B.Result() == Outcome::Playing
        && B.Score() == 0 && B.RevealedCount() == 0 && B.FlagCount() == 0);
    Check("source-style pre-generation does not promise any arbitrary first click is safe", B.Load(2, 2, {0})
        && B.Reveal(0, 0, 0) && B.Result() == Outcome::Lost);
    Check("elapsed-time overflow is capped safely instead of wrapping the score", B.Load(2, 2, {0})
        && B.ToggleFlag(0, 0, std::numeric_limits<std::int64_t>::max()) && B.Score() == 0);
    std::printf("minesweeper: %d/%d checks passed\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
