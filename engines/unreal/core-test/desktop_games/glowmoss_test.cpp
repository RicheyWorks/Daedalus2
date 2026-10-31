// SPDX-License-Identifier: MIT
// Glowmoss Delve cabinet: picking a ledge, digging, climbing, restart, difficulty, options, save round trip, and Python
// parity from seed alone by steering the pick to each fixture column with real input and digging (or climbing).
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
Input Key(const std::string& Act) {
    Input I;
    if(Act == "w") I.Left = true;
    else if(Act == "e") I.Right = true;
    else if(Act == "climb") I.DashPressed = true;
    else I.FirePressed = true;
    return I;
}
void Press(GlowmossGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** "dig:N" steers the pick to column N and digs; "climb" presses B. */
void Act(GlowmossGame& G, const std::string& Text) {
    if(Text == "climb") {
        Press(G, "climb");
        return;
    }
    const int Col = std::stoi(Text.substr(4));
    while(G.PickedColumn() < Col) Press(G, "e");
    while(G.PickedColumn() > Col) Press(G, "w");
    Press(G, "dig");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string Joined(const std::vector<int>& V) {
    std::string Out;
    for(size_t I = 0; I < V.size(); ++I) {
        if(I) Out.push_back(',');
        Out += std::to_string(V[I]);
    }
    return Out;
}
std::string ActString(const daedalus::glowmoss::Action& A) {
    return A.K == daedalus::glowmoss::Kind::Climb ? "climb" : "dig:" + std::to_string(A.Col);
}
std::string State(const GlowmossGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " row=" << C.Row << " col=" << C.Col << " light=" << C.Light << " crystals=" << C.Crystals << " score=" << C.Score << " path=" << Joined(C.Path)
      << " hint=" << (C.Over ? std::string("-") : ActString(C.Hint())) << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    GlowmossGame G;
    std::uint32_t Seed = 0;
    int Turn = 0, Games = 0;
    bool Skip = false;
    while(std::getline(In, Line)) {
        if(Line.empty() || Line[0] == '#' || Line.rfind("probe ", 0) == 0) continue;
        if(Line.rfind("game ", 0) == 0) {
            Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
            Diff = Field(Line, "d");
            Turn = 0;
            Skip = false;
            ++Games;
            G.SetCabinetDifficulty(Diff);
            G.Reset(Seed);
            const auto& C = G.CoreState();
            if(std::to_string(C.Best) != Field(Line, "best") || std::to_string(C.Target) != Field(Line, "target")) {
                std::cerr << "  want " << Line << "\n  got best=" << C.Best << " target=" << C.Target << '\n';
                Check(false, "fixture shaft regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string ActText = Field(Line, "act");
            Act(G, ActText);
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
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " perfect=" + (C.Perfect ? "1" : "0");
            Check(Got == Line && C.Over, "fixture delve ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 shafts");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    GlowmossGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Diff->Rows == 10 && C.Diff->Cols == 4 && C.Row == daedalus::glowmoss::Surface && C.Col == 2 && C.Light == 11 && G.PickedColumn() == 2 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal shaft is 10x4, start on the surface at column 2 with 11 light");
    Press(G, "w");
    Check(G.PickedColumn() == 1 && C.Row == daedalus::glowmoss::Surface, "left picks the ledge one column over without digging");
    Press(G, "w");
    Check(G.PickedColumn() == 1, "the pick stops at the edge of reach");
    Input Hold = Key("e");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.PickedColumn() == 2, "held right moves once per edge");
    G.Step({});
    Press(G, "dig");
    Check(C.Row >= 0 && C.Col == 2 && C.Path.size() == 1 && G.LastResultText().rfind("+", 0) == 0, "A digs onto the picked ledge");
    Check(G.SourceControllerButton(0) && C.Path.size() == 2, "pad A digs");
    {
        GlowmossGame Out;
        Out.Reset(730);
        Press(Out, "climb");
        Check(!Out.CoreState().Over, "B before the first dig is refused (dig first)");
        Press(Out, "dig");
        Press(Out, "climb");
        Check(Out.CoreState().Over && !Out.CoreState().Won && Out.LastResultText().rfind("climbed out", 0) == 0, "B climbs out at once (short of the target)");
        Check(Out.HintLine().find("short of the target") != std::string::npos, "the hint names the short climb");
    }

    GlowmossGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Diff->Rows == 8 && D.CoreState().Light == 12, "easy is an eight-row shaft with twelve light");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Diff->Cols == 5 && D.CoreState().Light == 10, "hard is five columns wide with ten light");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Diff->Cols == 5, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        const bool Digs = D.CoreState().Hint().K == daedalus::glowmoss::Kind::Dig;
        Check(CountRects(GF, {120, 225, 255, 255}) == (Digs ? 1 : 0), "guide marks the best next ledge, or nothing when it says climb");
    }
    Check(D.HintLine().find("best delve") != std::string::npos, "guide v2 describes the best delve");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the shaft");
    {
        GlowmossGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("DIG   Left/Right", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "the surface shows the tutorial rows");
        Press(T, "dig");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first dig");
    }

    GlowmossGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 20 && X.CanDig(); ++N) Press(X, "dig");
    if(!X.GetStatus().Over) Press(X, "climb");
    Check(X.GetStatus().Over, "digging straight down then climbing ends the delve");
    Check(!X.Dig() && !X.Climb() && !X.Nudge(1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished delve refuses digs, climbs and picks");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Row == daedalus::glowmoss::Surface, "R opens a new shaft");
    Press(X, "dig");
    Press(X, "climb");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished delve");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");
    {
        GlowmossGame Floor;
        Floor.Reset(730);
        Floor.SetCabinetDifficulty("easy");
        for(int N = 0; N < 20 && Floor.CanDig(); ++N) Act(Floor, ActString(Floor.CoreState().DemoAction()));
        if(!Floor.GetStatus().Over) {
            Check(!Floor.CanDig() && Floor.ActionCue() == "CUE Climb out", "at the shaft floor only the climb is left");
        }
    }

    GlowmossGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("easy");
    for(int N = 0; N < 20 && !W.GetStatus().Over; ++N) Act(W, ActString(W.CoreState().DemoAction()));
    Check(W.GetStatus().Over && W.GetStatus().Won && W.CoreState().Perfect, "following the best plan is a perfect delve");

    GlowmossGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 3 && !S.GetStatus().Over; ++N) Act(S, ActString(S.CoreState().DemoAction()));
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    GlowmossGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.PickedColumn() == S.PickedColumn() && R.CoreState().Path == S.CoreState().Path && R.CoreState().Light == S.CoreState().Light, "restored path, light, pick, score and note match");
    for(int N = 0; N < 20 && !S.GetStatus().Over; ++N) {
        const std::string A = ActString(S.CoreState().DemoAction());
        Act(S, A);
        Act(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Perfect == R.CoreState().Perfect, "restored delve plays on identically");
    {
        const std::string Fresh = "glowmoss v1 d=hard seed=4242 path=- climbed=0 pick=2 light=10 crystals=0 score=0 over=0 won=0";
        Check(R.RestoreState(Fresh, 1), "a fresh shaft restores");
        Check(!R.RestoreState("glowmoss v1 d=hard seed=4242 path=- climbed=0 pick=2 light=10 crystals=9 score=0 over=0 won=0", 1), "crystals the shaft never gave are refused");
        Check(!R.RestoreState("glowmoss v1 d=hard seed=4242 path=0 climbed=0 pick=0 light=10 crystals=0 score=0 over=0 won=0", 1), "a dig out of reach is refused");
        Check(!R.RestoreState("glowmoss v1 d=hard seed=4242 path=- climbed=0 pick=4 light=10 crystals=0 score=0 over=0 won=0", 1), "a pick out of reach is refused");
        Check(!R.RestoreState("glowmoss v1 d=hard seed=4242 path=- climbed=0 pick=2 light=10 crystals=0 score=0 over=1 won=1", 1), "flags the replay does not reach are refused");
        Check(!R.RestoreState("sluicegate v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}) >= 4, "the pick frame is drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "glowmoss cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
