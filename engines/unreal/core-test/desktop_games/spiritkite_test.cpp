// SPDX-License-Identifier: MIT
// Spiritkite Weave cabinet: lane pick, flying, landing, restart, difficulty, options, save round trip, and Python parity
// from seed alone by steering the pick to each fixture lane with real input and flying (or landing).
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
    else if(Act == "land") I.DashPressed = true;
    else I.FirePressed = true;
    return I;
}
void Press(SpiritkiteGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** "fly:N" steers the pick to the lane for isle N with Left/Right and flies; "land" presses B. */
void Act(SpiritkiteGame& G, const std::string& Text) {
    if(Text == "land") {
        Press(G, "land");
        return;
    }
    const int To = std::stoi(Text.substr(4));
    for(int Guard = 0; Guard < 32 && G.PickedIsle() != To; ++Guard) Press(G, G.PickedIsle() < To ? "e" : "w");
    Press(G, "fly");
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
std::string ActString(const daedalus::spiritkite::Action& A) {
    return A.K == daedalus::spiritkite::Kind::Land ? "land" : "fly:" + std::to_string(A.Isle);
}
std::string State(const SpiritkiteGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " at=" << C.At << " wind=" << C.Wind << " score=" << C.Score << " gathered=" << Joined(C.Gathered) << " trail=" << Joined(C.Trail) << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    SpiritkiteGame G;
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
            if(std::to_string(C.Target) != Field(Line, "target") || Joined(C.Plan) != Field(Line, "plan") || Joined(C.Values) != Field(Line, "values")) {
                std::cerr << "  want " << Line << "\n  got target=" << C.Target << " plan=" << Joined(C.Plan) << " values=" << Joined(C.Values) << '\n';
                Check(false, "fixture sky regenerates through the cabinet");
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
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0");
            Check(Got == Line && C.Over, "fixture flight ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 skies");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    SpiritkiteGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    const std::vector<int> FirstLanes = G.Lanes();
    Check(C.Isles() == 8 && C.Wind == 28 && C.At == 0 && !FirstLanes.empty() && G.PickedIsle() == FirstLanes[0] && !C.Over && G.GetStatus().Lives == 1, "a fresh normal sky has eight isles, 28 wind, the pick on the first lane");
    Press(G, "w");
    Check(G.PickedIsle() == FirstLanes[0], "the pick stops at the first lane");
    if(FirstLanes.size() > 1) {
        Press(G, "e");
        Check(G.PickedIsle() == FirstLanes[1] && C.At == 0, "right moves the pick to the next lane without flying");
        Input Hold = Key("w");
        G.Step(Hold);
        G.Step(Hold);
        Check(G.PickedIsle() == FirstLanes[0], "held left moves once per edge");
        G.Step({});
    }
    Press(G, "fly");
    Check(C.At == FirstLanes[0] && C.Trail.size() == 2 && G.LastResultText().rfind("+", 0) == 0, "A flies the picked lane");
    {
        SpiritkiteGame Home;
        Home.Reset(730);
        Press(Home, "land");
        Check(!Home.CoreState().Over, "B before the first flight is refused (fly first)");
        Press(Home, "fly");
        Home.PickLaneTo(0);
        Press(Home, "fly");
        Press(Home, "land");
        Check(Home.CoreState().Over && !Home.CoreState().Won && Home.LastResultText().rfind("landed with", 0) == 0, "B lands at once on the anchor (short of the target)");
        Check(Home.HintLine().find("short of the target") != std::string::npos, "the hint names the short landing");
        SpiritkiteGame Away;
        Away.Reset(730);
        Press(Away, "fly");
        Press(Away, "land");
        Check(!Away.CoreState().Over, "landing away from the anchor is refused");
        Check(Away.SourceControllerButton(0) && Away.CoreState().Trail.size() == 3, "pad A flies");
    }

    SpiritkiteGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Isles() == 7 && D.CoreState().Wind == 30, "easy is seven isles with thirty wind");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Isles() == 10 && D.CoreState().Wind == 26, "hard is ten isles with twenty-six wind");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Isles() == 10, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        const bool Flies = D.CoreState().DemoAction().K == daedalus::spiritkite::Kind::Fly;
        Check(CountRects(GF, {120, 225, 255, 255}) == (Flies ? 1 : 0), "guide marks the planned isle, or nothing when it says land");
    }
    Check(D.HintLine().find("planned tour") != std::string::npos, "guide v2 describes the planned tour");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the sky");
    {
        SpiritkiteGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("FLY   Left/Right", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "the anchor at the start shows the tutorial rows");
        Press(T, "fly");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first lane");
    }

    SpiritkiteGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 60 && !X.GetStatus().Over; ++N) Press(X, "fly");
    Check(X.GetStatus().Over && !X.GetStatus().Won, "flying the first lane forever loses the kite");
    Check(!X.Fly() && !X.Land() && !X.Nudge(1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished flight refuses lanes, landing and picks");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().At == 0, "R strings a new sky");
    Press(X, "fly");
    X.PickLaneTo(0);
    Press(X, "fly");
    Press(X, "land");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished flight");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    SpiritkiteGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("easy");
    for(int N = 0; N < 60 && !W.GetStatus().Over; ++N) Act(W, ActString(W.CoreState().DemoAction()));
    Check(W.GetStatus().Over && W.GetStatus().Won, "following the planned tour wins");

    SpiritkiteGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 3 && !S.GetStatus().Over; ++N) Act(S, ActString(S.CoreState().DemoAction()));
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    SpiritkiteGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.PickedIsle() == S.PickedIsle() && R.CoreState().Trail == S.CoreState().Trail && R.CoreState().Wind == S.CoreState().Wind, "restored trail, wind, pick, score and note match");
    for(int N = 0; N < 60 && !S.GetStatus().Over; ++N) {
        const std::string A = ActString(S.CoreState().DemoAction());
        Act(S, A);
        Act(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Won == R.CoreState().Won, "restored flight plays on identically");
    {
        const std::string Fresh = "spiritkite v1 d=hard seed=4242 trail=0 landed=0 pick=0 wind=26 score=0 over=0 won=0";
        Check(R.RestoreState(Fresh, 1), "a fresh sky restores");
        Check(!R.RestoreState("spiritkite v1 d=hard seed=4242 trail=0 landed=0 pick=0 wind=26 score=9 over=0 won=0", 1), "a score the lanes never gave is refused");
        Check(!R.RestoreState("spiritkite v1 d=hard seed=4242 trail=0,9,0,9,0,9,0,9,0,9,0,9,0,9,0,9 landed=0 pick=0 wind=26 score=0 over=0 won=0", 1), "a trail the lanes cannot fly is refused");
        Check(!R.RestoreState("spiritkite v1 d=hard seed=4242 trail=3 landed=0 pick=0 wind=26 score=0 over=0 won=0", 1), "a trail that does not start at the anchor is refused");
        Check(!R.RestoreState("spiritkite v1 d=hard seed=4242 trail=0 landed=0 pick=0 wind=26 score=0 over=1 won=1", 1), "flags the replay does not reach are refused");
        Check(!R.RestoreState("glowmoss v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}) >= 5, "the current isle frame and the pick bar are drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "spiritkite cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
