// SPDX-License-Identifier: MIT
// Emberkiln cabinet: tongs, coals, restart, difficulty, options, save round trip, and Python parity from seed alone by
// walking the tongs to each fixture cell with real input and setting the coal.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
using daedalus::emberkiln::Cell;
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
void Press(EmberkilnGame& G, const std::string& Act) {
    G.Step(Key(Act));
    G.Step({});
}
/** Walks the tongs to `Target` one press at a time, then sets the coal: the fixture replayed through real input. */
void CoalAt(EmberkilnGame& G, Cell Target) {
    while(G.TongsCell().R < Target.R) Press(G, "s");
    while(G.TongsCell().R > Target.R) Press(G, "n");
    while(G.TongsCell().C < Target.C) Press(G, "e");
    while(G.TongsCell().C > Target.C) Press(G, "w");
    Press(G, "coal");
}
std::string Field(const std::string& Line, const std::string& Key) {
    const std::string N = " " + Key + "=";
    const size_t P = Line.find(N);
    if(P == std::string::npos) return "";
    const size_t S = P + N.size(), E = Line.find(' ', S);
    return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
Cell ParseCell(const std::string& Text) {
    const size_t Comma = Text.find(',');
    return {std::stoi(Text.substr(0, Comma)), std::stoi(Text.substr(Comma + 1))};
}
std::string State(const EmberkilnGame& G) {
    const auto& C = G.CoreState();
    std::ostringstream O;
    O << " heat=" << C.HeatString() << " floor=" << C.FloorString() << " coals=" << C.Coals << " glazed=" << C.GlazedCount << " cracked=" << C.CrackedCount
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
    EmberkilnGame G;
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
            O << "game s=" << Seed << " d=" << Diff << " size=" << C.Size() << " coals=" << C.Coals << " floor=" << C.FloorString();
            if(O.str() != Line) {
                std::cerr << "  want " << Line << "\n  got  " << O.str() << '\n';
                Check(false, "fixture floor regenerates through the cabinet");
                Skip = true;
            }
        } else if(Line.rfind("move ", 0) == 0) {
            if(Skip) continue;
            const std::string Act = Field(Line, "act");
            CoalAt(G, ParseCell(Act));
            ++Turn;
            const std::string Got = "move t=" + std::to_string(Turn) + " act=" + Act + State(G) + " res=" + G.LastResultText();
            if(Got != Line) {
                std::cerr << "  want " << Line << "\n  got  " << Got << '\n';
                Check(false, "fixture coal replays through the cabinet (" + Diff + " s=" + std::to_string(Seed) + ")");
                Skip = true;
            }
        } else if(Line.rfind("end  ", 0) == 0) {
            if(Skip) continue;
            const auto& C = G.CoreState();
            const std::string Got = "end  score=" + std::to_string(C.Score) + " won=" + (C.Won ? "1" : "0") + " glazed=" + std::to_string(C.GlazedCount)
                                    + " cracked=" + std::to_string(C.CrackedCount) + " coals=" + std::to_string(C.Coals);
            Check(Got == Line && C.Over, "fixture floor ends identically (" + Diff + " s=" + std::to_string(Seed) + ")");
        }
    }
    Check(Games == 30, "fixture holds 30 floors");
}
int CountRects(const Frame& F, Color Tint, double Height = -1) {
    int N = 0;
    for(const auto& Cmd : F.Commands)
        if(Cmd.Kind == Shape::Rectangle && Cmd.Tint.R == Tint.R && Cmd.Tint.G == Tint.G && Cmd.Tint.B == Tint.B && (Height < 0 || Cmd.B.Y == Height)) ++N;
    return N;
}
}

int main(int Argc, char** Argv) {
    EmberkilnGame G;
    G.Reset(730);
    const auto& C = G.CoreState();
    Check(C.Size() == 6 && C.Coals == 27 && C.Raw() == 30 && G.TongsCell() == Cell{0, 0} && !C.Over && G.GetStatus().Lives == 1, "a fresh normal floor is 6x6 with 27 coals and 30 clay tiles");
    Press(G, "e");
    Check(G.TongsCell() == Cell{0, 1} && C.Coals == 27, "right moves the tongs without spending a coal");
    Input Hold = Key("s");
    G.Step(Hold);
    G.Step(Hold);
    Check(G.TongsCell() == Cell{1, 1}, "held down moves once per edge");
    G.Step({});
    Press(G, "coal");
    Check(C.Coals == 26 && C.HeatAt({1, 1}) >= 0 && G.LastResultText().rfind("1,1: ", 0) == 0, "A sets a coal under the tongs and spends one");
    Check(G.SourceControllerButton(0) && C.Coals == 25, "pad A sets a coal");
    {
        EmberkilnGame Edge;
        Edge.Reset(730);
        Press(Edge, "n");
        Press(Edge, "w");
        Check(Edge.TongsCell() == Cell{0, 0}, "the tongs stop at the floor's edge");
    }

    EmberkilnGame D;
    D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Size() == 5 && D.CoreState().Coals == 19, "easy is a 5x5 floor with nineteen coals");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Size() == 7 && D.CoreState().Coals == 36, "hard is a 7x7 floor with thirty-six coals");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Size() == 7, "unknown difficulty is refused");
    Check(!D.SetOption(2, 730) && D.SetOption(1, 730) && D.GetOption() == 1 && D.HintLine().find("Practice") != std::string::npos, "guide practice is option 1");
    {
        Frame GF;
        D.Render(GF);
        Check(CountRects(GF, {120, 225, 255, 255}) == 1, "guide marks exactly one cell");
    }
    Check(D.HintLine().find("stoker's pick") != std::string::npos, "guide v2 describes the stoker's move");
    Check(D.SetOption(0, 730) && D.GetOption() == 0, "option 0 returns to the floor");
    {
        // Tutorial rows on the first coal only; red rims equal the tiles a coal under the tongs would crack
        EmberkilnGame T;
        T.Reset(5);
        T.SetCabinetDifficulty("easy");
        const auto Rows = [](const Frame& F) {
            int N = 0;
            for(const auto& Cmd : F.Commands) if(Cmd.Kind == Shape::Text && Cmd.Label.rfind("TONGS arrows", 0) == 0) ++N;
            return N;
        };
        Frame F1;
        T.Render(F1);
        Check(Rows(F1) == 1, "a fresh floor shows the tutorial rows");
        Check(CountRects(F1, {255, 120, 60, 255}, 3) == 0, "a cold floor has no crack warnings");
        Press(T, "coal");
        Frame F2;
        T.Render(F2);
        Check(Rows(F2) == 0, "the tutorial leaves after the first coal");
        int Warned = 0;
        for(int N = 0; N < 30 && Warned == 0 && !T.GetStatus().Over; ++N) {
            CoalAt(T, T.CoreState().DemoAction());
            daedalus::emberkiln::Outcome O;
            T.CoreState().Preview(T.TongsCell(), O);
            Frame F3;
            T.Render(F3);
            Check(CountRects(F3, {255, 120, 60, 255}, 3) == O.Cracks, "red rims equal the tiles the tongs would crack");
            Warned = O.Cracks;
        }
        Check(Warned > 0, "the stoker's trail passes a cell where a second coal would crack");
    }

    EmberkilnGame X;
    X.Reset(730);
    X.SetCabinetDifficulty("easy");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) Press(X, "coal");
    Check(X.GetStatus().Over && !X.GetStatus().Won, "piling every coal on one corner spoils the firing");
    Check(!X.SetCoal() && !X.Nudge(0, 1) && X.ContrastMark() == "MARK WAIT" && X.ActionCue() == "CUE Retry", "a finished floor refuses coals and tongs");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Coals == 19, "R lays a new floor");
    for(int N = 0; N < 40 && !X.GetStatus().Over; ++N) Press(X, "coal");
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over, "pad Start restarts a finished firing");
    Check(!X.SourceControllerButton(1), "pad Start is not consumed mid-game");

    EmberkilnGame W;
    W.Reset(3);
    W.SetCabinetDifficulty("easy");
    for(int N = 0; N < 40 && !W.GetStatus().Over; ++N) CoalAt(W, W.CoreState().DemoAction());
    Check(W.GetStatus().Over && W.CoreState().GlazedCount + W.CoreState().CrackedCount + W.CoreState().Raw() == 21, "following the stoker ends the firing with every tile accounted for");

    EmberkilnGame S;
    S.Reset(4242);
    S.SetCabinetDifficulty("hard");
    for(int N = 0; N < 8 && !S.GetStatus().Over; ++N) CoalAt(S, S.CoreState().DemoAction());
    const std::string Saved = S.SaveState();
    const auto Before = S.GetStatus();
    EmberkilnGame R;
    R.Reset(1);
    Check(R.RestoreState(Saved, 1) && R.CabinetDifficulty() == "hard" && R.SeedAfterRestore(1) == 4242, "save text restores difficulty and seed");
    Check(R.GetStatus().Score == Before.Score && R.GetStatus().Note == Before.Note && R.TongsCell() == S.TongsCell()
          && R.CoreState().FloorString() == S.CoreState().FloorString() && R.CoreState().HeatString() == S.CoreState().HeatString(), "restored floor, heat, tongs, score and note match");
    for(int N = 0; N < 60 && !S.GetStatus().Over; ++N) {
        const Cell Act = S.CoreState().DemoAction();
        CoalAt(S, Act);
        CoalAt(R, Act);
    }
    Check(S.GetStatus().Over == R.GetStatus().Over && S.GetStatus().Score == R.GetStatus().Score && S.CoreState().GlazedCount == R.CoreState().GlazedCount, "restored floor fires on identically");
    {
        daedalus::emberkiln::Game Fresh;
        Fresh.Start(4242, "hard");
        const std::string Floor = Fresh.FloorString(), Cold = std::string(7, '0');
        std::string Heat = Cold;
        for(int N = 1; N < 7; ++N) Heat += ";" + Cold;
        const std::string Head = "emberkiln v1 d=hard seed=4242 coals=36 glazed=0 cracked=0 score=0 over=0 won=0 tongs=0,0";
        Check(R.RestoreState(Head + " floor=" + Floor + " heat=" + Heat, 1), "a cold floor laid by the seed restores");
        std::string Reshaped = Floor;
        for(char& Ch : Reshaped) if(Ch == '3') { Ch = '4'; break; }
        Check(!R.RestoreState(Head + " floor=" + Reshaped + " heat=" + Heat, 1), "a reshaped floor is refused");
        std::string Hot = Heat;
        for(size_t I = 0; I < Floor.size(); ++I) if(Floor[I] == '2') { Hot[I] = '2'; break; }
        Check(!R.RestoreState(Head + " floor=" + Floor + " heat=" + Hot, 1), "a raw tile at its target is refused");
        Check(!R.RestoreState("emberkiln v1 d=hard seed=4242 coals=36 glazed=0 cracked=0 score=0 over=0 won=0 tongs=9,0 floor=" + Floor + " heat=" + Heat, 1), "tongs off the floor are refused");
        Check(!R.RestoreState("roostcall v1", 1) && !R.RestoreState("", 1), "foreign save text is refused");
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
    Check(CountRects(F, {255, 236, 180, 255}, 3) >= 2, "the tongs frame is drawn in gold");

    if(Argc > 1) Parity(Argv[1]);
    std::cout << "emberkiln cabinet: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed ? 1 : 0;
}
