// SPDX-License-Identifier: MIT
// Fogbell Ferry cabinet: steering, waiting, restart, difficulty, options, save round trip, and Python parity from
// seed alone by pressing each fixture move with real input.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks = 0, Failed = 0;
void Check(bool Ok, const std::string& What) {
    ++Checks;
    if(!Ok) {
        ++Failed;
        std::cerr << "FAIL " << What << '\n';
    }
}
Input Dir(const std::string& Act) {
    Input I;
    if(Act == "n") I.Up = true;
    else if(Act == "s") I.Down = true;
    else if(Act == "w") I.Left = true;
    else if(Act == "e") I.Right = true;
    else I.FirePressed = true;
    return I;
}
void Press(FogbellGame& G, const std::string& Act) {
    G.Step(Dir(Act));
    G.Step({});
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string State(const FogbellGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " ferry=" << C.Ferry.R << "," << C.Ferry.C << " tide=" << C.Tide() << " aboard=" << C.Aboard << " passengers=" << daedalus::fogbell::Game::CellsString(C.Passengers)
      << " score=" << C.Score << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    FogbellGame G;
    std::uint32_t Seed = 0;
    int Games = 0;
    bool Skip = false;
    while(std::getline(In, Line)) {
        if(Line.empty() || Line[0] == '#') continue;
        if(Line.rfind("game ", 0) == 0) {
            Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
            Diff = Field(Line, "d");
            Skip = false;
            ++Games;
            G.SetCabinetDifficulty(Diff);
            G.Reset(Seed);
            const auto& C = G.CoreState();
            std::ostringstream O;
            O << "game s=" << Seed << " d=" << Diff << " size=" << C.Size() << " heights=" << C.HeightsString() << " ferry=" << C.Ferry.R << "," << C.Ferry.C
              << " harbour=" << C.Harbour.R << "," << C.Harbour.C << " passengers=" << daedalus::fogbell::Game::CellsString(C.Passengers);
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture flat regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string Act = Field(Line, "act");
            Press(G, Act);
            const std::string Got = "move t=" + std::to_string(G.CoreState().Turn) + " act=" + Act + State(G) + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture move replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " aboard=" + std::to_string(C.Aboard) + " turns=" + std::to_string(C.Turn);
            Check(Got == Line && C.Over, "fixture voyage ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 voyages");
}
}

int main(int Argc, char** Argv) {
    FogbellGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Size() == 8 && C.Passengers.size() == 4 && C.Turn == 0 && C.Ferry.R == 0 && C.Ferry.C == 0 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal voyage starts north-west with four lanterns waiting");
    Press(G, "e");
    Check(C.Ferry.C == 1 && C.Turn == 1 && G.LastResultText().rfind("e: ", 0) == 0, "right steers east one cell and spends a turn");
    Input Hold = Dir("s");
    G.Step(Hold);
    G.Step(Hold);
    Check(C.Ferry.R == 1 && C.Turn == 2, "held down steers once per edge");
    G.Step({});
    Press(G, "wait");
    Check(C.Turn == 3 && C.Ferry.R == 1 && C.Ferry.C == 1, "A waits a turn in place");
    Check(G.SourceControllerButton(0) && C.Turn == 4, "pad A waits");
    {
        FogbellGame Edge;
        Edge.Reset(730);
        Press(Edge, "n");
        Check(Edge.CoreState().Turn == 0, "steering off the flat is refused and costs nothing");
    }

    FogbellGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Size() == 7 && D.CoreState().Diff->Need == 2, "easy is a 7x7 flat needing two lanterns");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Size() == 9 && D.CoreState().Diff->Need == 4, "hard is a 9x9 flat needing four");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Size() == 9, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        int Marks = 0;
        for(const auto& Cmd : GF.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == 120 && Cmd.Tint.G == 225 && Cmd.Tint.B == 255) ++Marks;
        Check(Marks == 1, "guide marks exactly one cell");
    }
    Check(D.HintLine().find("watcher's pick") != std::string::npos, "guide v2 describes the watcher's move");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the ferry");
    {
        FogbellGame T;
        T.Reset(5);
        Frame F1;
        T.Render(F1);
        int Rows = 0;
        for(const auto& Cmd : F1.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("STEER arrows", 0) == 0) ++Rows;
        Check(Rows == 1, "a fresh voyage shows the tutorial rows");
        Press(T, "wait");
        Frame F2;
        T.Render(F2);
        Rows = 0;
        for(const auto& Cmd : F2.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("STEER arrows", 0) == 0) ++Rows;
        Check(Rows == 0, "the tutorial leaves after the first turn");
    }

    FogbellGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 60 && !X.GetStatus().Over; ++N) Press(X, "wait");
    Check(X.GetStatus().Over && !X.GetStatus().Won, "waiting forever on the start cell ends with the tide");
    Check(!X.Steer(daedalus::fogbell::Move::E) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished voyage refuses moves");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Turn == 0, "R sets out again");
    for(int N = 0; N < 60 && !X.GetStatus().Over; ++N) Press(X, "wait");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished voyage");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    FogbellGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 4 && !S.GetStatus().Over; ++N) Press(S, daedalus::fogbell::MoveName(S.CoreState().DemoAction()));
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    FogbellGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.CoreState().Ferry == S.CoreState().Ferry
          && daedalus::fogbell::Game::CellsString(R.CoreState().Passengers) == daedalus::fogbell::Game::CellsString(S.CoreState().Passengers), "restored ferry, lanterns, score and note match");
    for(int N = 0; N < 40 && !S.GetStatus().Over; ++N) {
        const std::string Act = daedalus::fogbell::MoveName(S.CoreState().DemoAction());
        Press(S, Act);
        Press(R, Act);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Ferry == R.CoreState().Ferry, "restored voyage plays on identically");
    {
        std::string Tampered = Saved;
        const size_t P = Tampered.find(" heights=") + 9;
        Tampered[P] = Tampered[P] == '9' ? '8' : '9';
        Check(!R.RestoreState(Tampered, 1), "a save that reshapes the flat is refused");
    }
    Check(!R.RestoreState("fogbell v1 d=hard seed=4242 turn=0 aboard=9 score=0 over=0 won=0 ferry=0,0 heights=" + S.CoreState().HeightsString() + " passengers=-", 1), "a save with impossible lantern counts is refused");
    Check(!R.RestoreState("prismchime v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");

    Frame F;
    G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size() <= Frame::MaxCommands, "render stays bounded");
    if(Argc > 1) Parity(Argv[1]);
    std::cout << "fogbell cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
