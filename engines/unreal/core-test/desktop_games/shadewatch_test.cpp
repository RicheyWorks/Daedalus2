// SPDX-License-Identifier: MIT
// Shadewatch Vigil cabinet: lane cursor, flare/kindle/nova, restart, difficulty, options, save round trip, and
// Python parity from seed alone by pressing each fixture action with real input.
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
Input Press(bool Fire, bool Jump, bool Action) {
    Input I;
    I.FirePressed = Fire;
    I.JumpPressed = Jump;
    I.ActionPressed = Action;
    return I;
}
Input Flare() { return Press(true, false, false); }
Input Kindle() { return Press(false, true, false); }
Input Nova() { return Press(false, false, true); }
Input Right() {
    Input I;
    I.Right = true;
    return I;
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
void Steer(ShadewatchGame& G, int Lane) {
    for(int Guard = 0; G.CursorLane() != Lane && Guard < 8; ++Guard) {
        G.Step(Right());
        G.Step({});
    }
}
std::string Flags(const ShadewatchGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " score=" << C.Score << " hearts=" << C.Hearts << " light=" << C.Light << " burned=" << C.Burned << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0) << " lanes=" << C.LanesString();
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    ShadewatchGame G;
    std::uint32_t Seed = 0;
    int Turn = 0, Games = 0;
    bool Skip = false;
    while(std::getline(In, Line)) {
        if(Line.empty() || Line[0] == '#') continue;
        if(Line.rfind("game ", 0) == 0) {
            Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
            Diff = Field(Line, "d");
            Turn = 0;
            Skip = false;
            ++Games;
            G.SetCabinetDifficulty(Diff);
            G.Reset(Seed);
            const auto& C = G.CoreState();
            std::ostringstream O;
            O << "game s=" << Seed << " d=" << Diff << " hearts=" << C.Hearts << " light=" << C.Light << " lanes=" << C.LanesString();
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture vigil regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string Act = Field(Line, "act");
            if(Act.rfind("flare:", 0) == 0) {
                Steer(G, std::stoi(Act.substr(6)));
                G.Step(Flare());
            } else if(Act == "nova") {
                G.Step(Nova());
            } else {
                G.Step(Kindle());
            }
            G.Step({});
            ++Turn;
            std::ostringstream O;
            O << "move t=" << Turn << " act=" << Act << Flags(G) << " res=" << G.LastResultText();
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture move replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + " t=" + std::to_string(Turn) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            std::ostringstream O;
            O << "end  score=" << C.Score << " won=" << (C.Won ? 1 : 0);
            Check(O.str() == Line && C.Over, "fixture game ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 games");
}
}

int main(int Argc, char** Argv) {
    ShadewatchGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Lanes.size() == 3 && C.Hearts == 3 && C.Light == 1 && C.TurnNo == 0 && !C.Over && G.GetStatus().Lives == 3, "a fresh normal vigil has three lanes, three hearts, one light");
    Check(G.CursorLane() == 0, "cursor starts on the first lane");
    G.Step(Right());
    Check(G.CursorLane() == 1, "one right press moves the cursor");
    G.Step(Right());
    Check(G.CursorLane() == 1, "held right does not move again");
    G.Step({});
    G.Step(Right());
    G.Step({});
    G.Step(Right());
    G.Step({});
    Check(G.CursorLane() == 0, "right wraps around the lanes");
    G.Step(Kindle());
    G.Step({});
    Check(C.Light == 2 && C.TurnNo == 1 && C.Score >= 1 && G.LastResultText().rfind("burned 0", 0) == 0, "B kindles one light and ends the turn");
    Check(!G.Nova() && C.Light == 2, "a nova without three light is refused");
    G.Step(Kindle());
    G.Step({});
    Check(G.Nova() && C.Light == 0 && C.TurnNo == 3, "X novas once three light are stored");
    Check(G.SourceControllerButton(0) && C.TurnNo == 4, "pad A flares the cursor lane");

    ShadewatchGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Lanes.size() == 2 && D.CoreState().Diff->Turns == 20, "easy has two lanes and twenty turns");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Lanes.size() == 4 && D.CoreState().Diff->Turns == 28, "hard has four lanes and twenty-eight turns");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Lanes.size() == 4, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        int Marks = 0;
        for(const auto& Cmd : GF.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == 120 && Cmd.Tint.G == 225 && Cmd.Tint.B == 255) ++Marks;
        Check(Marks >= 1, "guide draws at least one counsel mark");
    }
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to vigil");

    ShadewatchGame X;
    X.Reset(730);
    for(int N = 0; N < 100 && !X.GetStatus().Over; ++N) {
        X.Step(Kindle());
        X.Step({});
    }
    Check(X.GetStatus().Over, "doing nothing but kindling ends the vigil one way or the other");
    Check(!X.Flare() && !X.Kindle() && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished vigil refuses more actions");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().TurnNo == 0, "R lights a new vigil");
    for(int N = 0; N < 100 && !X.GetStatus().Over; ++N) {
        X.Step(Kindle());
        X.Step({});
    }
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished vigil");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    ShadewatchGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 5; ++N) {
        const auto Demo = S.CoreState().DemoAction();
        if(Demo.K == daedalus::shadewatch::Kind::Flare) {
            Steer(S, Demo.Lane);
            S.Step(Flare());
        } else if(Demo.K == daedalus::shadewatch::Kind::Nova) {
            S.Step(Nova());
        } else {
            S.Step(Kindle());
        }
        S.Step({});
    }
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    ShadewatchGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.CoreState().LanesString() == S.CoreState().LanesString() && R.CursorLane() == S.CursorLane(), "restored lanes, score, note and cursor match");
    for(int N = 0; N < 30 && !S.GetStatus().Over; ++N) {
        S.Step(Kindle());
        S.Step({});
        R.Step(Kindle());
        R.Step({});
    }
    Check(S.CoreState().LanesString() == R.CoreState().LanesString() && S.GetStatus().Score == R.GetStatus().Score, "restored stream spawns the same shades afterwards");
    Check(!R.RestoreState("shadewatch v1 d=hard seed=1 drawn=8 turn=0 hearts=3 light=1 burned=0 score=0 over=0 won=0 cursor=0 lanes=3,2||| ", 1), "a lane out of order is refused");
    Check(!R.RestoreState("shadewatch v1 d=hard seed=1 drawn=8 turn=0 hearts=3 light=1 burned=0 score=0 over=0 won=0 cursor=0 lanes=5|| ", 1), "the wrong lane count is refused");
    Check(!R.RestoreState("shardfall v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");

    Frame F;
    G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size() <= Frame::MaxCommands, "render stays bounded");
    if(Argc > 1) Parity(Argv[1]);
    std::cout << "shadewatch cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
