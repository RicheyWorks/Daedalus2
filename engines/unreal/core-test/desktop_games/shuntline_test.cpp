// SPDX-License-Identifier: MIT
// Shuntline cabinet: siding pick, send/shunt/pull, restart, difficulty, options, save round trip, and Python parity from
// seed alone by picking each fixture siding with real input and pressing the right verb.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
using daedalus::shuntline::Action;
using daedalus::shuntline::Kind;
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
    if(Act == "n") I.Up = true;
    else if(Act == "s") I.Down = true;
    else if(Act == "out") I.Right = true;
    else if(Act == "pull") I.DashPressed = true;
    else I.FirePressed = true;
    return I;
}
void Press(ShuntlineGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** Picks the siding with Up/Down, then presses the verb for `A`. */
void Do(ShuntlineGame& G, const Action& A) {
    if(A.K == Kind::Out) {
        Press(G, "out");
        return;
    }
    while(G.PickedSiding() < A.Siding) Press(G, "s");
    while(G.PickedSiding() > A.Siding) Press(G, "n");
    Press(G, A.K == Kind::Shunt ? "shunt" : "pull");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string State(const ShuntlineGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " index=" << C.Index() << " sidings=" << C.SidingsString() << " outbound=" << C.OutboundString() << " moves=" << C.Moves() << " score=" << C.Score << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    ShuntlineGame G;
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
            if(G.CoreState().TrainString() != Field(Line, "train")) {
                std::cerr << "  want " << Line << "\n  got train=" << G.CoreState().TrainString() << '\n';
                Check(false, "fixture train regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string ActText = Field(Line, "act");
            Action A;
            daedalus::shuntline::ActionFromText(ActText, A);
            Do(G, A);
            ++Turn;
            const std::string Got = "move t=" + std::to_string(Turn) + " act=" + ActText + State(G) + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture move replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " out=" + std::to_string(C.Outbound.size()) + " moves=" + std::to_string(C.Moves());
            Check(Got == Line && C.Over, "fixture shift ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 trains");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    ShuntlineGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Cars() == 9 && C.Diff->Sidings == 2 && C.Moves() == 20 && G.PickedSiding() == 0 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal yard has nine carriages, two sidings, twenty moves");
    Press(G, "n");
    Check(G.PickedSiding() == 0, "the pick stops at the first siding");
    Press(G, "s");
    Check(G.PickedSiding() == 1 && C.Index() == 0, "down picks the next siding without a move");
    Input Hold = Key("n");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.PickedSiding() == 0, "held up moves once per edge");
    G.Step({});
    {
        const int Front = C.Front();
        Press(G, "shunt");
        Check(C.SidingAt(0).N == 1 && C.SidingAt(0).Top() == Front && C.Index() == 1 && C.Moves() == 19 && G.LastResultText().rfind("s0:", 0) == 0, "A shunts the front carriage onto the picked siding");
        Check(G.SourceControllerButton(0) && C.SidingAt(0).N == 2, "pad A shunts");
    }
    {
        ShuntlineGame O;
        O.Reset(730);
        const int Front = O.CoreState().Front();
        Press(O, "out");
        Check(O.CoreState().Outbound.size() == 1 && O.CoreState().Outbound[0] == Front && O.LastResultText().rfind("out:", 0) == 0, "Right sends the front carriage out");
        ShuntlineGame P;
        P.Reset(730);
        Press(P, "pull");
        Check(P.CoreState().Moves() == 20, "pulling from an empty siding is refused and costs nothing");
        Press(P, "shunt");
        Press(P, "pull");
        Check(P.CoreState().Outbound.size() == 1 && P.CoreState().SidingAt(0).N == 0 && P.LastResultText().rfind("p0:", 0) == 0, "B pulls the picked siding's top carriage out");
    }

    ShuntlineGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Cars() == 7 && D.CoreState().Moves() == 16, "easy is seven carriages in sixteen moves");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Cars() == 11 && D.CoreState().Diff->Sidings == 3, "hard is eleven carriages with three sidings");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Cars() == 11, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        Check(CountRects(GF, {120, 225, 255, 255}) == 1, "guide marks exactly one move");
    }
    Check(D.HintLine().find("yardmaster's line") != std::string::npos, "guide v2 describes the yardmaster's line");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the yard");
    {
        ShuntlineGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("OUT   Right sends", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "a fresh yard shows the tutorial rows");
        Press(T, "shunt");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first move");
        // Iteration 9: red bars equal the carriages tagged below the last one out, through a yardmaster game
        ShuntlineGame P;
        P.Reset(9);
        P.SetCabinetDifficulty("hard");
        bool DeadOk = true;
        while(!P.GetStatus().Over && DeadOk) {
            const auto& PC = P.CoreState();
            int Expected = 0;
            for(int I = PC.Index(); I < PC.Cars() && I - PC.Index() < 11; ++I) if(PC.Train[static_cast<size_t>(I)] < PC.OutLast()) ++Expected;
            for(int S = 0; S < PC.Diff->Sidings; ++S) for(int I = 0; I < PC.SidingAt(S).N; ++I) if(PC.SidingAt(S).Tag[static_cast<size_t>(I)] < PC.OutLast()) ++Expected;
            Frame FP;
            P.Render(FP);
            DeadOk = CountRects(FP, {200, 70, 60, 255}) == Expected;
            Do(P, PC.DemoAction());
        }
        Check(DeadOk, "dead-carriage bars match the rule every turn");
    }

    ShuntlineGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) {
        if(!X.SendOut() && !X.Shunt()) { X.Nudge(1); if(!X.Shunt() && !X.Pull()) { X.Nudge(-1); X.Pull(); } }
    }
    Check(X.GetStatus().Over, "sending straight out whenever allowed ends the shift one way or another");
    Check(!X.SendOut() && !X.Shunt() && !X.Pull() && !X.Nudge(1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished shift refuses moves");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Index() == 0, "R brings in a new train");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) Do(X, X.CoreState().DemoAction());
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished shift");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    ShuntlineGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("hard");
    for(int N = 0; N < 40 && !W.GetStatus().Over; ++N) Do(W, W.CoreState().DemoAction());
    Check(W.GetStatus().Over && W.GetStatus().Won, "following the yardmaster makes up the train");

    ShuntlineGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 5 && !S.GetStatus().Over; ++N) Do(S, S.CoreState().DemoAction());
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    ShuntlineGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.PickedSiding() == S.PickedSiding() && R.CoreState().SidingsString() == S.CoreState().SidingsString()
          && R.CoreState().OutboundString() == S.CoreState().OutboundString() && R.CoreState().Index() == S.CoreState().Index(), "restored sidings, outbound, index, pick, score and note match");
    for(int N = 0; N < 40 && !S.GetStatus().Over; ++N) {
        const Action A = S.CoreState().DemoAction();
        Do(S, A);
        Do(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Won == R.CoreState().Won, "restored shift plays on identically");
    {
        const std::string Base = "shuntline v1 d=hard seed=4242 ";
        Check(R.RestoreState(Base + "moves=- pick=0 score=0 over=0 won=0", 1), "a fresh yard restores");
        Check(R.RestoreState(Base + "moves=s0 pick=0 score=0 over=0 won=0", 1), "one shunt restores");
        Check(!R.RestoreState(Base + "moves=p0 pick=0 score=0 over=0 won=0", 1), "a pull from an empty siding is refused");
        Check(!R.RestoreState(Base + "moves=s9 pick=0 score=0 over=0 won=0", 1), "a siding that does not exist is refused");
        Check(!R.RestoreState(Base + "moves=- pick=0 score=9 over=0 won=0", 1), "a score the replay does not reach is refused");
        Check(!R.RestoreState(Base + "moves=- pick=0 score=0 over=1 won=1", 1), "flags the replay does not reach are refused");
        Check(!R.RestoreState("stonecourse v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}) >= 4, "the picked siding frame is drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "shuntline cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
