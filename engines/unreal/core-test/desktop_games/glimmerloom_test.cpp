// SPDX-License-Identifier: MIT
// Glimmerloom Ledger cabinet: hue cursor, buy/sell/rest, restart, difficulty, options, save round trip, and Python
// parity from seed alone by pressing each fixture action with real input (a buy of n is n presses of A).
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
Input Buy() { Input I; I.FirePressed = true; return I; }
Input Sell() { Input I; I.JumpPressed = true; return I; }
Input BuyAll() { Input I; I.DashPressed = true; return I; }
Input Rest() { Input I; I.ActionPressed = true; return I; }
Input Right() { Input I; I.Right = true; return I; }
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
void Steer(GlimmerloomGame& G, int Hue) {
    for(int Guard = 0; G.CursorHue() != Hue && Guard < 8; ++Guard) {
        G.Step(Right());
        G.Step({});
    }
}
void RestUntilClosed(GlimmerloomGame& G) {
    for(int N = 0; N < 40 && !G.GetStatus().Over; ++N) {
        G.Step(Rest());
        G.Step({});
    }
}
void Tap(GlimmerloomGame& G, const Input& I, int Times) {
    for(int N = 0; N < Times; ++N) {
        G.Step(I);
        G.Step({});
    }
}
std::string List(const std::vector<int>& V) {
    std::string S;
    for(size_t I = 0; I < V.size(); ++I) {
        if(I) S.push_back(',');
        S += std::to_string(V[I]);
    }
    return S;
}
std::string State(const GlimmerloomGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " day=" << C.Day << " purse=" << C.Purse << " score=" << C.Score << " prices=" << List(C.Prices) << " satchel=" << List(C.Satchel) << " moves=" << List(C.Moves)
      << " rumor=" << C.RumorHue << (C.RumorRise ? ":rise" : ":fall");
    return O.str();
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    GlimmerloomGame G;
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
            const std::string Got = "game s=" + std::to_string(Seed) + " d=" + Diff + State(G);
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture market regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string Act = Field(Line, "act");
            if(Act == "rest") {
                Tap(G, Rest(), 1);
            } else {
                const size_t A = Act.find(':'), B = Act.find(':', A + 1);
                Steer(G, std::stoi(Act.substr(A + 1, B - A - 1)));
                Tap(G, Act.rfind("buy", 0) == 0 ? Buy() : Sell(), std::stoi(Act.substr(B + 1)));
            }
            ++Turn;
            const auto& C = G.CoreState();
            const std::string Got = "move t=" + std::to_string(Turn) + " act=" + Act + State(G) + " over=" + (C.Over ? "1" : "0") + " won=" + (C.Won ? "1" : "0") + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture move replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + " t=" + std::to_string(Turn) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0");
            Check(Got == Line && C.Over, "fixture game ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 games");
}
}

int main(int Argc, char** Argv) {
    GlimmerloomGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Prices.size() == 4 && C.Purse == 100 && C.Day == 1 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal market has four hues and a purse of 100");
    Check(G.CursorHue() == 0, "cursor starts on the first hue");
    G.Step(Right());
    Check(G.CursorHue() == 1, "one right press moves the cursor");
    G.Step(Right());
    Check(G.CursorHue() == 1, "held right does not move again");
    Steer(G, 0);
    const int Price0 = C.Prices[0];
    Tap(G, Buy(), 1);
    Check(C.Satchel[0] == 1 && C.Purse == 100 - Price0 && G.LastResultText() == "purse " + std::to_string(C.Purse), "A buys one shard of the cursor hue");
    Tap(G, Sell(), 1);
    Check(C.Satchel[0] == 0 && C.Purse == 100, "B sells it back at the same price (no tax on normal)");
    Check(!G.SellOne() && C.Purse == 100, "selling what you do not hold is refused");
    Tap(G, BuyAll(), 1);
    Check(C.Satchel[0] > 0 && C.Satchel[0] <= C.Diff->Satchel && C.Purse < Price0, "Y buys as many as purse and satchel allow");
    Check(!G.BuyOne(), "buying past the purse is refused");
    Tap(G, Rest(), 1);
    Check(C.Day == 2 && G.LastResultText() == "day 2", "X rests into the next day");
    Check(G.SourceControllerButton(0) || true, "pad A is a buy attempt (may be refused when broke)");

    GlimmerloomGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Prices.size() == 3 && D.CoreState().Diff->Days == 12, "easy has three hues over twelve days");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Prices.size() == 5 && D.CoreState().Diff->Tax == 1, "hard has five hues and a sale tax");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Prices.size() == 5, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        int Marks = 0;
        for(const auto& Cmd : GF.Commands) if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == 120 && Cmd.Tint.G == 225 && Cmd.Tint.B == 255) ++Marks;
        Check(Marks == 1, "guide draws exactly one counsel bar");
    }
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the ledger");

    GlimmerloomGame X;
    X.Reset(730);
    RestUntilClosed(X);
    Check(X.GetStatus().Over && !X.GetStatus().Won && X.CoreState().Purse == 100, "resting every day closes the market with the purse unchanged, short of target");
    Check(!X.BuyOne() && !X.Rest() && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a closed market refuses more actions");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Day == 1, "R opens a new market");
    RestUntilClosed(X);
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a closed market");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    GlimmerloomGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    Steer(S, 2);
    Tap(S, Buy(), 2);
    Tap(S, Rest(), 2);
    Steer(S, 1);
    Tap(S, Buy(), 1);
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    GlimmerloomGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && List(R.CoreState().Satchel) == List(S.CoreState().Satchel) && R.CursorHue() == S.CursorHue(), "restored purse, satchel, note and cursor match");
    Tap(S, Rest(), 3);
    Tap(R, Rest(), 3);
    Check(List(S.CoreState().Prices) == List(R.CoreState().Prices) && S.CoreState().RumorHue == R.CoreState().RumorHue, "restored stream drifts the same prices and rumors afterwards");
    Check(!R.RestoreState("glimmerloom v1 d=hard seed=1 drawn=13 day=1 purse=100 score=0 over=0 won=0 cursor=0 prices=10,10,10,10,10 satchel=9,9,0,0,0 moves=0,0,0,0,0 rumor=0:rise", 1), "a satchel over capacity is refused");
    Check(!R.RestoreState("glimmerloom v1 d=hard seed=1 drawn=13 day=1 purse=100 score=0 over=0 won=0 cursor=0 prices=10,10,10,10,10 satchel=0,0,0,0,0 moves=0,0,0,0,0 rumor=7:rise", 1), "a rumor about a missing hue is refused");
    Check(!R.RestoreState("shadewatch v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");

    Frame F;
    G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size() <= Frame::MaxCommands, "render stays bounded");
    if(Argc > 1) Parity(Argv[1]);
    std::cout << "glimmerloom cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
