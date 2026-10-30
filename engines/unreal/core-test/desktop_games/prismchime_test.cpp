// SPDX-License-Identifier: MIT
// Prismchime Ring cabinet: ring cursor, taps, restart, difficulty, options, save round trip, and Python parity from
// seed alone by steering to each fixture chime and tapping with real input.
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
Input TapIn() { Input I; I.FirePressed = true; return I; }
Input Right() { Input I; I.Right = true; return I; }
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
void Steer(PrismchimeGame& G, int Chime) {
    for(int Guard = 0; G.CursorChime() != Chime && Guard < 12; ++Guard) {
        G.Step(Right());
        G.Step({});
    }
}
void TapAt(PrismchimeGame& G, int Chime) {
    Steer(G, Chime);
    G.Step(TapIn());
    G.Step({});
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) {
        Check(false, std::string("fixture opens: ") + Path);
        return;
    }
    std::string Line, Diff;
    PrismchimeGame G;
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
            O << "game s=" << Seed << " d=" << Diff << " taps=" << C.Taps << " charge=" << C.ChargeString() << " facing=" << C.FacingString();
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture ring regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const int Chime = std::stoi(Field(Line, "tap"));
            TapAt(G, Chime);
            ++Turn;
            const auto& C = G.CoreState();
            std::ostringstream O;
            O << "move t=" << Turn << " tap=" << Chime << " pealed=" << G.LastPealCount() << " score=" << C.Score << " taps=" << C.Taps << " lit=" << C.LitString()
              << " charge=" << C.ChargeString() << " over=" << (C.Over ? 1 : 0) << " won=" << (C.Won ? 1 : 0);
            if(Line.rfind(O.str(), 0) != 0) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture tap replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + " t=" + std::to_string(Turn) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            std::ostringstream O;
            O << "end  score=" << C.Score << " won=" << (C.Won ? 1 : 0) << " peals=" << C.Peals;
            Check(O.str() == Line && C.Over, "fixture game ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 games");
}
}

int main(int Argc, char** Argv) {
    PrismchimeGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Chimes() == 8 && C.Taps == 8 && C.LitCount() == 0 && !C.Over && G.GetStatus().Lives == 1, "a fresh normal ring has eight dark chimes and eight taps");
    Check(G.CursorChime() == 0, "cursor starts on chime 1");
    G.Step(Right());
    Check(G.CursorChime() == 1, "one right press moves the cursor");
    G.Step(Right());
    Check(G.CursorChime() == 1, "held right does not move again");
    G.Step({});
    for(int N = 0; N < 7; ++N) { G.Step(Right()); G.Step({}); }
    Check(G.CursorChime() == 0, "right wraps around the ring");
    const int Charge0 = C.Charge[0];
    Input Hold = TapIn();
    G.Step(Hold);
    G.Step(Hold);
    Check(C.Taps == 7 && G.LastPealCount() >= 0, "held tap fires once per edge and spends one tap");
    Check(C.Charge[0] == Charge0 + 1 || C.Lit[0], "the rung chime resonates (or pealed)");
    Check(G.SourceControllerButton(0) && C.Taps == 6, "pad A taps");

    PrismchimeGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Chimes() == 6, "easy hangs six chimes");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Chimes() == 10, "hard hangs ten chimes");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Chimes() == 10, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        int Rings = 0;
        for(const auto& Cmd : GF.Commands) if(Cmd.Kind == Shape::Circle && Cmd.Tint.R == 120 && Cmd.Tint.G == 225 && Cmd.Tint.B == 255) ++Rings;
        Check(Rings == 1, "guide draws exactly one counsel ring");
    }
    Check(D.HintLine().find("would peal") != std::string::npos, "guide v2 previews the cursor chime's peals");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the ring");
    {
        PrismchimeGame T;
        T.Reset(5);
        Frame F1;
        T.Render(F1);
        int Rows = 0;
        for(const auto& Cmd : F1.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("TAP  a chime", 0) == 0) ++Rows;
        Check(Rows == 1, "a fresh ring shows the tutorial rows");
        TapAt(T, 0);
        Frame F2;
        T.Render(F2);
        Rows = 0;
        for(const auto& Cmd : F2.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("TAP  a chime", 0) == 0) ++Rows;
        Check(Rows == 0, "the tutorial leaves after the first tap");
    }

    PrismchimeGame X;
    X.Reset(730);
    for(int N = 0; N < 20 && !X.GetStatus().Over; ++N) TapAt(X, 0);
    Check(X.GetStatus().Over, "tapping the same chime until the taps run out ends the ring");
    Check(!X.Tap() && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished ring refuses more taps");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Taps == 8, "R hangs a new ring");
    for(int N = 0; N < 20 && !X.GetStatus().Over; ++N) TapAt(X, 0);
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished ring");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    PrismchimeGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    TapAt(S, 3);
    TapAt(S, 7);
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    PrismchimeGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.CoreState().ChargeString() == S.CoreState().ChargeString()
          && R.CoreState().LitString() == S.CoreState().LitString() && R.CursorChime() == S.CursorChime(), "restored ring, score, note and cursor match");
    for(int N = 0; N < 10 && !S.GetStatus().Over; ++N) {
        const int Chime = S.CoreState().DemoAction();
        TapAt(S, Chime);
        TapAt(R, Chime);
    }
    Check(S.CoreState().ChargeString() == R.CoreState().ChargeString() && S.GetStatus().Score == R.GetStatus().Score, "restored ring plays on identically");
    Check(!R.RestoreState("prismchime v1 d=hard seed=1 taps=5 peals=0 score=0 over=0 won=0 cursor=0 charge=4,0,0,0,0,0,0,0,0,0 facing=+1,+1,+1,+1,+1,+1,+1,+1,+1,+1 lit=0000000000", 1), "a charge at the peal threshold is refused");
    Check(!R.RestoreState("prismchime v1 d=hard seed=1 taps=5 peals=0 score=0 over=0 won=0 cursor=0 charge=1,0,0,0,0,0,0,0,0,0 facing=+1,+2,+1,+1,+1,+1,+1,+1,+1,+1 lit=0000000000", 1), "a bad facing is refused");
    Check(!R.RestoreState("glimmerloom v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");

    Frame F;
    G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size() <= Frame::MaxCommands, "render stays bounded");
    if(Argc > 1) Parity(Argv[1]);
    std::cout << "prismchime cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
