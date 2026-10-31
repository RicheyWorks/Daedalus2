// SPDX-License-Identifier: MIT
// Sluicegate cabinet: marker, gates, waiting, restart, difficulty, options, save round trip, and Python parity from
// seed alone by walking the marker to each fixture gate with real input (or pressing wait).
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
using daedalus::sluicegate::Cell;
using daedalus::sluicegate::NoCell;
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
    else if(Act == "w") I.Left = true;
    else if(Act == "e") I.Right = true;
    else if(Act == "wait") I.DashPressed = true;
    else I.FirePressed = true;
    return I;
}
void Press(SluicegateGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** Walks the marker to `Target` and drops the gate, or presses wait for NoCell: the fixture replayed through input. */
void Act(SluicegateGame& G, Cell Target) {
    if(Target == NoCell) {
        Press(G, "wait");
        return;
    }
    while(G.MarkerCell().R < Target.R) Press(G, "s");
    while(G.MarkerCell().R > Target.R) Press(G, "n");
    while(G.MarkerCell().C < Target.C) Press(G, "e");
    while(G.MarkerCell().C > Target.C) Press(G, "w");
    Press(G, "gate");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
Cell ParseAct(const std::string& Text) {
    if(Text == "wait") return NoCell;
    const size_t Comma = Text.find(',');
    return {std::stoi(Text.substr(0, Comma)), std::stoi(Text.substr(Comma + 1))};
}
std::string State(const SluicegateGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " wet=" << daedalus::sluicegate::Game::CellsString(C.Wet) << " gates=" << daedalus::sluicegate::Game::CellsString(C.Gates) << " left=" << C.GatesLeft << " filled=" << C.Filled
      << " turns=" << C.Turns << " score=" << C.Score << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    SluicegateGame G;
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
            O << "game s=" << Seed << " d=" << Diff << " size=" << C.Size() << " turns=" << C.Turns << " gates=" << C.GatesLeft << " head=" << C.Head.R << "," << C.Head.C
              << " mill=" << (C.Mill == NoCell ? std::string("-") : std::to_string(C.Mill.R) + "," + std::to_string(C.Mill.C)) << " cisterns=" << daedalus::sluicegate::Game::CellsString(C.Cisterns) << " field=" << C.FieldString();
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture field regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string ActText = Field(Line, "act");
            Act(G, ParseAct(ActText));
            ++Turn;
            const std::string Got = "move t=" + std::to_string(Turn) + " act=" + ActText + State(G) + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture push replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " filled=" + std::to_string(C.Filled) + " turns=" + std::to_string(C.Turns);
            Check(Got == Line && C.Over, "fixture field ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 fields");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    SluicegateGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Size() == 8 && C.Turns == 12 && C.GatesLeft == 5 && C.Cisterns.size() == 4 && C.Wet.size() == 1 && G.MarkerCell() == C.Head && !C.Over && G.GetStatus().Lives == 1, "a fresh normal field is 8x8 with 12 turns, 5 gates and 4 cisterns");
    Press(G, "s");
    Check(G.MarkerCell() == Cell{1, 4} && C.Turns == 12, "down moves the marker without a push");
    Input Hold = Key("s");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.MarkerCell() == Cell{2, 4}, "held down moves once per edge");
    G.Step({});
    Press(G, "wait");
    Check(C.Turns == 11 && C.GatesLeft == 5 && C.Wet.size() == 3 && G.LastResultText().rfind("wait: ", 0) == 0, "B waits: a push with no gate");
    {
        SluicegateGame Edge;
        Edge.Reset(730);
        Press(Edge, "n");
        Check(Edge.MarkerCell() == Edge.CoreState().Head, "the marker stops at the field's edge");
        Press(Edge, "gate");
        Check(Edge.CoreState().GatesLeft == 5 && Edge.CoreState().Turns == 12, "a gate on the headgate is refused and costs nothing");
        // Walk to the gatekeeper's first pick and drop it there
        const Cell Pick = Edge.CoreState().DemoAction();
        if(Pick != NoCell) {
            Act(Edge, Pick);
            Check(Edge.CoreState().GatesLeft == 4 && Edge.CoreState().IsGate(Pick) && Edge.CoreState().Turns == 11, "A drops a gate under the marker and pushes");
            Check(Edge.SourceControllerButton(0) == true, "pad A is consumed mid-game");
        }
    }

    SluicegateGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Size() == 7 && D.CoreState().Turns == 9, "easy is a 7x7 field with nine turns");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Size() == 9 && D.CoreState().GatesLeft == 6, "hard is a 9x9 field with six gates");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Size() == 9, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        const int Marks = CountRects(GF, {120, 225, 255, 255});
        Check(Marks == (D.CoreState().DemoAction() == NoCell ? 0 : 1), "guide marks the gatekeeper's gate, or nothing when it waits");
    }
    Check(D.HintLine().find("gatekeeper") != std::string::npos, "guide v2 describes the gatekeeper's move");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the field");
    {
        // Tutorial rows on the first push only; next-push cells on screen equal the preview
        SluicegateGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("FLOW  the headgate", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "a fresh field shows the tutorial rows");
        std::vector<Cell> Next;
        int Filled = 0;
        bool Flood = false;
        T.CoreState().Preview(NoCell, Next, Filled, Flood);
        Check(CountRects(F1, {120, 170, 230, 255}) == static_cast<int>(Next.size()) + 1, "the next push is drawn in pale water (plus the key swatch)");
        Press(T, "wait");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first push");
    }

    SluicegateGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) Press(X, "wait");
    Check(X.GetStatus().Over, "waiting every turn ends the field one way or another");
    Check(!X.Wait() && !X.Nudge(1, 0) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished field refuses pushes and the marker");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Turns == 9, "R opens a new field");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) Press(X, "wait");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished field");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    SluicegateGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("easy");
    for(int N = 0; N < 40 && !W.GetStatus().Over; ++N) Act(W, W.CoreState().DemoAction());
    Check(W.GetStatus().Over && W.CoreState().Filled <= 3, "following the gatekeeper ends the field");

    SluicegateGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 4 && !S.GetStatus().Over; ++N) Act(S, S.CoreState().DemoAction());
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    SluicegateGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.MarkerCell() == S.MarkerCell()
          && daedalus::sluicegate::Game::CellsString(R.CoreState().Wet) == daedalus::sluicegate::Game::CellsString(S.CoreState().Wet)
          && daedalus::sluicegate::Game::CellsString(R.CoreState().Gates) == daedalus::sluicegate::Game::CellsString(S.CoreState().Gates), "restored water, gates, marker, score and note match");
    for(int N = 0; N < 40 && !S.GetStatus().Over; ++N) {
        const Cell A = S.CoreState().DemoAction();
        Act(S, A);
        Act(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Filled == R.CoreState().Filled, "restored field flows on identically");
    {
        daedalus::sluicegate::Game Fresh;
        Fresh.Start(4242, "hard");
        const std::string HeadText = std::to_string(Fresh.Head.R) + "," + std::to_string(Fresh.Head.C);
        const std::string Base = "sluicegate v1 d=hard seed=4242 turns=15 left=6 filled=0 score=0 over=0 won=0 marker=" + HeadText;
        Check(R.RestoreState(Base + " wet=" + HeadText + " gates=-", 1), "a fresh field restores");
        Check(!R.RestoreState(Base + " wet=8,8 gates=-", 1), "water that does not start at the headgate is refused");
        Check(!R.RestoreState(Base + " wet=" + HeadText + " gates=" + HeadText, 1), "a gate on the headgate is refused");
        Check(!R.RestoreState("sluicegate v1 d=hard seed=4242 turns=15 left=5 filled=0 score=0 over=0 won=0 marker=" + HeadText + " wet=" + HeadText + " gates=-", 1), "gate stock that does not match the gates is refused");
        Check(!R.RestoreState("sluicegate v1 d=hard seed=4242 turns=15 left=6 filled=1 score=0 over=0 won=0 marker=" + HeadText + " wet=" + HeadText + " gates=-", 1), "a filled count with no wet cistern is refused");
        Check(!R.RestoreState("emberkiln v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}) >= 4, "the marker frame is drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "sluicegate cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
