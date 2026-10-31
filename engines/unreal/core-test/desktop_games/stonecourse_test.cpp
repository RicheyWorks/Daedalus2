// SPDX-License-Identifier: MIT
// Stonecourse cabinet: marker, setting, skipping, restart, difficulty, options, save round trip, and Python parity from
// seed alone by walking the marker to each fixture column with real input and setting (or skipping) the stone.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
using daedalus::stonecourse::Skip;
namespace {
int Checks = 0, Failed = 0;
void Check(bool Ok, const std::string& What) {
    ++Checks;
    if(!Ok) {
        ++Failed;
        std::cerr << "FAIL " << What << '\n';
    }
}
Input Key(const std::string& Act) {
    Input I;
    if(Act == "w") I.Left = true;
    else if(Act == "e") I.Right = true;
    else if(Act == "skip") I.DashPressed = true;
    else I.FirePressed = true;
    return I;
}
void Press(StonecourseGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** Walks the marker to `Action` and sets the stone, or presses skip. */
void Do(StonecourseGame& G, int Action) {
    if(Action == Skip) {
        Press(G, "skip");
        return;
    }
    while(G.MarkerColumn() < Action) Press(G, "e");
    while(G.MarkerColumn() > Action) Press(G, "w");
    Press(G, "set");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string State(const StonecourseGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " index=" << C.Index << " wall=" << C.WallString() << " locked=" << C.Locked << " skips=" << C.SkipsLeft << " score=" << C.Score << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    StonecourseGame G;
    std::uint32_t Seed = 0;
    int Turn = 0, Games = 0;
    bool Skipping = false;
    while(std::getline(In, Line)) {
        if(Line.empty() || Line[0] == '#') continue;
        if(Line.rfind("game ", 0) == 0) {
            Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
            Diff = Field(Line, "d");
            Turn = 0;
            Skipping = false;
            ++Games;
            G.SetCabinetDifficulty(Diff);
            G.Reset(Seed);
            if(G.CoreState().StonesString() != Field(Line, "stones")) {
                std::cerr << "  want " << Line << "\n  got stones=" << G.CoreState().StonesString() << '\n';
                Check(false, "fixture supply regenerates through the cabinet");
                Skipping = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skipping) continue;
            const std::string ActText = Field(Line, "act");
            int A = 0;
            daedalus::stonecourse::ActionFromText(ActText, A);
            Do(G, A);
            ++Turn;
            const std::string Got = "move t=" + std::to_string(Turn) + " act=" + ActText + State(G) + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture move replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + ")");
                Skipping = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skipping) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " locked=" + std::to_string(C.Locked) + " index=" + std::to_string(C.Index);
            Check(Got == Line && C.Over, "fixture build ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 walls");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    StonecourseGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Width() == 8 && C.Courses() == 5 && C.Supply() == 26 && C.SkipsLeft == 3 && G.MarkerColumn() == 0 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal wall is 8 wide, 5 courses, 26 stones, 3 skips");
    Press(G, "w");
    Check(G.MarkerColumn() == 0, "the marker stops at the left end");
    Press(G, "e");
    Check(G.MarkerColumn() == 1 && C.Index == 0, "right moves the marker without setting");
    Input Hold = Key("e");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.MarkerColumn() == 2, "held right moves once per edge");
    G.Step({});
    {
        const int Size = C.NextStone();
        Press(G, "set");
        Check(C.Index == 1 && C.Filled(0, 2) && C.Filled(0, 2 + Size - 1) && G.LastResultText().rfind("2: ", 0) == 0, "A sets the stone at the marker on the footing");
    }
    Check(G.SourceControllerButton(0) && C.Index == 2, "pad A sets");
    {
        StonecourseGame S;
        S.Reset(730);
        Press(S, "skip");
        Check(S.CoreState().Index == 1 && S.CoreState().SkipsLeft == 2 && S.LastResultText().rfind("skip:", 0) == 0, "B skips the stone to the rubble");
        StonecourseGame E;
        E.Reset(730);
        E.SetCabinetDifficulty("easy");
        for(int N = 0; N < 10; ++N) Press(E, "e");
        Check(E.MarkerColumn() == 7 - E.CoreState().NextStone(), "the marker stops where the stone still fits on the wall");
    }

    StonecourseGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Width() == 7 && D.CoreState().Courses() == 4, "easy is a 7-wide wall of four courses");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Width() == 9 && D.CoreState().Supply() == 34, "hard is 9 wide with thirty-four stones");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Width() == 9, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        const bool Sets = D.CoreState().DemoAction() != Skip;
        Check(CountRects(GF, {120, 225, 255, 255}) == (Sets ? 1 : 0), "guide marks the mason's column, or nothing when it skips");
    }
    Check(D.HintLine().find("mason's line") != std::string::npos, "guide v2 describes the mason's line");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the wall");
    {
        StonecourseGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("SET   Left/Right", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "a fresh wall shows the tutorial rows");
        Press(T, "set");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first stone");
        // The hint names the landing course and whether it locks, matching the preview
        int Course = -1;
        bool Locks = false;
        T.CoreState().Preview(T.MarkerColumn(), Course, Locks);
        Check(T.HintLine().find("course " + std::to_string(Course)) != std::string::npos, "the hint names the landing course");
    }

    StonecourseGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    const auto Leftmost = [](StonecourseGame& B) {
        std::array<int, daedalus::stonecourse::MaxWallWidth> Cols{};
        const int N = B.CoreState().Placements(Cols);
        Do(B, N > 0 ? Cols[0] : Skip);
    };
    for(int N = 0; N < 60 && !X.GetStatus().Over; ++N) Leftmost(X);
    Check(X.GetStatus().Over, "setting every stone leftmost ends the build one way or another");
    Check(!X.SetStone() && !X.SkipStone() && !X.Nudge(1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished build refuses actions");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Index == 0, "R draws a new supply");
    for(int N = 0; N < 60 && !X.GetStatus().Over; ++N) Leftmost(X);
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished build");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    StonecourseGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("hard");
    for(int N = 0; N < 60 && !W.GetStatus().Over; ++N) Do(W, W.CoreState().DemoAction());
    Check(W.GetStatus().Over && W.GetStatus().Won, "following the mason finishes the wall");

    StonecourseGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 6 && !S.GetStatus().Over; ++N) Do(S, S.CoreState().DemoAction());
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    StonecourseGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.MarkerColumn() == S.MarkerColumn() && R.CoreState().WallString() == S.CoreState().WallString() && R.CoreState().Index == S.CoreState().Index, "restored wall, index, marker, score and note match");
    for(int N = 0; N < 60 && !S.GetStatus().Over; ++N) {
        const int A = S.CoreState().DemoAction();
        Do(S, A);
        Do(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Won == R.CoreState().Won, "restored build plays on identically");
    {
        const std::string Empty = "000000000;000000000;000000000;000000000;000000000;000000000";
        const std::string Base = "stonecourse v1 d=hard seed=4242 ";
        Check(R.RestoreState(Base + "index=0 wall=" + Empty + " locked=0 skips=3 marker=0 score=0 over=0 won=0", 1), "a fresh wall restores");
        Check(!R.RestoreState(Base + "index=0 wall=111000000;000000000;000000000;000000000;000000000;000000000 locked=0 skips=3 marker=0 score=0 over=0 won=0", 1), "stone the supply never gave is refused");
        Check(!R.RestoreState(Base + "index=3 wall=000000000;111000000;000000000;000000000;000000000;000000000 locked=0 skips=3 marker=0 score=0 over=0 won=0", 1), "an unsupported stone is refused");
        Check(!R.RestoreState(Base + "index=0 wall=" + Empty + " locked=1 skips=3 marker=0 score=0 over=0 won=0", 1), "a locked count that is not the full courses is refused");
        Check(!R.RestoreState(Base + "index=0 wall=" + Empty + " locked=0 skips=1 marker=0 score=0 over=0 won=0", 1), "more skips than stones taken is refused");
        Check(!R.RestoreState(Base + "index=0 wall=" + Empty + " locked=0 skips=3 marker=0 score=0 over=1 won=1", 1), "flags the wall does not support are refused");
        Check(!R.RestoreState("shardscale v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
    }

    Frame F;
    G.Render(F);
    bool HasHow = false, HasHint = false, HasKeys = false;
    for(const auto& Cmd : F.Commands) {
        if(Cmd.Kind != Shape::Text) continue;
        if(Cmd.Label == G.HowToLine()) HasHow = true;
        if(Cmd.Label == G.HintLine()) HasHint = true;
        if(Cmd.Label == G.KeyHint()) HasKeys = true;
    }
    Check(HasHow && HasHint && HasKeys, "frame carries how-to, hint and key hint");
    Check(CountRects(F, {255, 236, 180, 255}) >= 2, "the marker bar and the next stone are drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "stonecourse cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
