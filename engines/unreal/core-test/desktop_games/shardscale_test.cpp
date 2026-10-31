// SPDX-License-Identifier: MIT
// Shardscale cabinet: the hand, setting, benching, restart, difficulty, options, save round trip, and Python parity from
// seed alone by moving the hand to each fixture shard with real input and setting or benching it.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
using daedalus::shardscale::Action;
using daedalus::shardscale::Kind;
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
    else I.FirePressed = true;
    return I;
}
void Press(ShardscaleGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** Moves the hand to `Source` (Next or a bench index) with Up/Down, then sets or benches. */
void Do(ShardscaleGame& G, const Action& A) {
    if(A.K == Kind::Hold) {
        Press(G, "hold");
        return;
    }
    for(int Guard = 0; Guard < 8 && G.HandSource() != A.Source; ++Guard) {
        const bool Up = A.Source == Action::Next || (G.HandSource() != Action::Next && G.HandSource() > A.Source);
        Press(G, Up ? "n" : "s");
    }
    Press(G, A.K == Kind::Left ? "w" : "e");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
std::string State(const ShardscaleGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " index=" << C.Index << " left=" << C.Left << " right=" << C.Right << " held=" << C.HeldString() << " used=" << C.BenchUsed << " score=" << C.Score << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    ShardscaleGame G;
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
            if(G.CoreState().LineString() != Field(Line, "line")) {
                std::cerr << "  want " << Line << "\n  got line=" << G.CoreState().LineString() << '\n';
                Check(false, "fixture line regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string ActText = Field(Line, "act");
            Action A;
            daedalus::shardscale::ActionFromText(ActText, A);
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
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " left=" + std::to_string(C.Left) + " right=" + std::to_string(C.Right);
            Check(Got == Line && C.Over, "fixture weighing ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 lines");
}
int CountRects(const Frame& F, Color Tint) {
    int N = 0;
    for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    ShardscaleGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Line.size() == 10 && C.Diff->Cap == 5 && C.Diff->Bench == 2 && G.HandSource() == Action::Next && G.HandWeight() == C.Line[0] && !C.Over && G.GetStatus().Lives == 1, "a fresh normal line has ten shards, cap 5, two bench slots, the next shard in hand");
    Press(G, "s");
    Check(G.HandSource() == Action::Next, "with an empty bench the hand stays on the cart");
    Press(G, "hold");
    Check(C.Held.N == 1 && C.Index == 1 && G.HandSource() == Action::Next && G.LastResultText().rfind("hold ", 0) == 0, "A benches the next shard and the hand stays on the cart");
    Press(G, "s");
    Check(G.HandSource() == 0 && G.HandWeight() == C.Held.W[0], "down moves the hand onto the bench shard");
    Input Hold = Key("n");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.HandSource() == Action::Next, "held up moves once per edge back to the cart");
    G.Step({});
    {
        // Set the next shard on whichever pan the rules allow; a shard heavier than the cap goes to the bench instead
        const int Next = C.Line[static_cast<size_t>(C.Index)];
        if(Next <= C.Diff->Cap) {
            Press(G, "w");
            Check(C.Left == Next && C.Index == 2 && G.LastResultText().rfind("left ", 0) == 0, "left sets the shard in hand on the left pan");
            Check(G.SourceControllerButton(0) && C.Held.N == 2 && C.Index == 3, "pad A benches");
        } else {
            Check(G.SourceControllerButton(0) && C.Held.N == 2 && C.Index == 2, "pad A benches a shard too heavy for either pan");
        }
        const int BeforeIndex = C.Index;
        Press(G, "hold");
        Check(C.Held.N == 2 && C.Index == BeforeIndex, "a full bench refuses a third hold");
    }

    ShardscaleGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Line.size() == 8 && D.CoreState().Diff->Cap == 6, "easy is eight shards with cap 6");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Line.size() == 12 && D.CoreState().Diff->Tolerance == 0 && D.CoreState().Diff->Bench == 3, "hard is twelve shards, tolerance 0, three bench slots");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Line.size() == 12, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        Check(CountRects(GF, {120, 225, 255, 255}) == 1, "guide marks exactly one shard");
    }
    Check(D.HintLine().find("weigher's line") != std::string::npos, "guide v2 describes the weigher's line");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the beam");
    {
        ShardscaleGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("SET   Left/Right", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "a fresh line shows the tutorial rows");
        Press(T, "w");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first shard");
        // Iteration 9: the FITS line follows the preview through a whole weigher game
        ShardscaleGame P;
        P.Reset(9);
        P.SetCabinetDifficulty("hard");
        bool FitsOk = true;
        while(!P.GetStatus().Over && FitsOk) {
            int After = 0;
            bool TipsL = false, TipsR = false, Ends = false;
            P.CoreState().Preview({Kind::Left, P.HandSource()}, After, TipsL, Ends);
            P.CoreState().Preview({Kind::Right, P.HandSource()}, After, TipsR, Ends);
            const std::string Want = std::string("FITS ") + (!TipsL && !TipsR ? "left and right" : !TipsL ? "left" : !TipsR ? "right" : "neither pan (bench it)");
            Frame FP;
            P.Render(FP);
            bool Found = false;
            for(const auto& Cmd : FP.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label == Want) Found = true;
            FitsOk = Found;
            Do(P, P.CoreState().DemoAction());
        }
        Check(FitsOk, "the FITS line matches the preview every turn");
    }

    ShardscaleGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 20 && !X.GetStatus().Over; ++N) Press(X, "w");
    Check(X.GetStatus().Over && !X.GetStatus().Won && X.CoreState().Tipped, "piling every shard on the left tips the beam");
    Check(!X.SetLeft() && !X.Hold() && !X.Nudge(1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished weighing refuses actions");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Index == 0, "R rolls a new line");
    for(int N = 0; N < 20 && !X.GetStatus().Over; ++N) Press(X, "w");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished weighing");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    ShardscaleGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("hard");
    for(int N = 0; N < 30 && !W.GetStatus().Over; ++N) Do(W, W.CoreState().DemoAction());
    Check(W.GetStatus().Over && W.GetStatus().Won, "following the weigher levels the beam");

    ShardscaleGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 5 && !S.GetStatus().Over; ++N) Do(S, S.CoreState().DemoAction());
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    ShardscaleGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.HandSource() == S.HandSource() && R.CoreState().HeldString() == S.CoreState().HeldString()
          && R.CoreState().Left == S.CoreState().Left && R.CoreState().Right == S.CoreState().Right && R.CoreState().Index == S.CoreState().Index, "restored pans, bench, index, hand, score and note match");
    for(int N = 0; N < 30 && !S.GetStatus().Over; ++N) {
        const Action A = S.CoreState().DemoAction();
        Do(S, A);
        Do(R, A);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().Won == R.CoreState().Won, "restored weighing plays on identically");
    {
        daedalus::shardscale::Game Fresh;
        Fresh.Start(4242, "hard");
        const int W0 = Fresh.Line[0];
        const std::string Base = "shardscale v1 d=hard seed=4242 ";
        Check(R.RestoreState(Base + "index=0 left=0 right=0 held=- used=0 hand=-1 score=0 tipped=0 over=0 won=0", 1), "a fresh line restores");
        Check(R.RestoreState(Base + "index=1 left=" + std::to_string(W0) + " right=0 held=- used=0 hand=-1 score=0 tipped=0 over=0 won=0", 1), "one shard on the left restores");
        Check(!R.RestoreState(Base + "index=1 left=" + std::to_string(W0 + 1) + " right=0 held=- used=0 hand=-1 score=0 tipped=0 over=0 won=0", 1), "weight the cart never gave is refused");
        Check(!R.RestoreState(Base + "index=1 left=0 right=0 held=" + std::to_string(W0) + " used=0 hand=-1 score=0 tipped=0 over=0 won=0", 1), "a bench shard with no bench use is refused");
        Check(!R.RestoreState(Base + "index=0 left=0 right=0 held=- used=0 hand=0 score=0 tipped=0 over=0 won=0", 1), "a hand on an empty bench is refused");
        Check(!R.RestoreState(Base + "index=0 left=0 right=0 held=- used=0 hand=-1 score=0 tipped=0 over=1 won=1", 1), "flags the line does not support are refused");
        Check(!R.RestoreState("spiritkite v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}) >= 4, "the hand frame is drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "shardscale cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
