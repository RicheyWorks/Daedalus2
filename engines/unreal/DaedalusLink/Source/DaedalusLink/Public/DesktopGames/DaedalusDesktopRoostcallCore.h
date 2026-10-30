// SPDX-License-Identifier: MIT
// Roostcall (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusRoostcallCore.h, a port of
// tools/minigames/roostcall.py (the rules authority). CPython-compatible seeding, so StartGame("roostcall", seed)
// scatters the same birds as roostcall.start(seed, difficulty).
//
//   Arrows / d-pad / stick   walk the whistler one cell (each press is one turn)
//   pad A / J / Space        wait a turn (the birds near you still fly)
//   R / pad Start            restart a finished yard
//   option 0 Roostcall; option 1 Guide practice marks the cell the watcher would walk to
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusRoostcallCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class RoostcallGame final : public Game {
    roostcall::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last turn; empty until the first
    EdgeLatch UpEdge, DownEdge, LeftEdge, RightEdge, WaitEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        LastResult.clear();
        UpEdge.Clear();
        DownEdge.Clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        WaitEdge.Clear();
    }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool WaitPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }

    /** Parses "r,c;r,c" ("-" for none) into distinct cells inside the yard. */
    static bool ParseCells(const std::string& Text, int Size, std::vector<roostcall::Cell>& Out) {
        Out.clear();
        if(Text == "-") return true;
        for(const std::string& Token : SplitText(Text, ';')) {
            const std::vector<std::string> Parts = SplitText(Token, ',');
            long long R = 0, C = 0;
            if(Parts.size() != 2 || !ParseInteger(Parts[0], R) || !ParseInteger(Parts[1], C)) return false;
            if(R < 0 || R >= Size || C < 0 || C >= Size) return false;
            const roostcall::Cell Cell{static_cast<int>(R), static_cast<int>(C)};
            for(const roostcall::Cell& Seen : Out) if(Seen == Cell) return false;
            Out.push_back(Cell);
        }
        return true;
    }

public:
    const roostcall::Game& CoreState() const { return Core; }
    const std::string& LastResultText() const { return LastResult; }

    void Reset(std::uint32_t Seed) override {
        SessionSeed = Seed;
        Deal();
    }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if(!Game::SetCabinetDifficulty(Name)) return false;
        Deal();
        return true;
    }
    bool SetOption(int Value, std::uint32_t Seed) override {
        if(Value < 0 || Value > 1) return false;
        Option = Value;
        SessionSeed = Seed;
        Deal();
        return true;
    }
    int GetOption() const override { return Option; }

    /** One turn: walk (or wait). False when the rules refuse it (off the yard, a bird there, finished). */
    bool Walk(roostcall::Move M) {
        if(Core.Over) return false;
        int Flew = 0, Perched = 0;
        std::string Result;
        if(Core.Step(M, Flew, Perched, Result) != roostcall::Game::Act::Ok) return false;
        LastResult = Result;
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:    Walk(roostcall::Move::N); break;
            case SourceKey::Down:  Walk(roostcall::Move::S); break;
            case SourceKey::Left:  Walk(roostcall::Move::W); break;
            case SourceKey::Right: Walk(roostcall::Move::E); break;
            default:
                if(SourceKey::IsConfirm(Key)) Walk(roostcall::Move::Wait);
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Walk(roostcall::Move::Wait);
            return true;
        }
        if(Button == PadButton::Start && Core.Over) {
            Deal();
            return true;
        }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) {
            if(WaitPressed(I)) Deal();
            return;
        }
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool W = WaitEdge.Rose(WaitPressed(I));
        if(U) Walk(roostcall::Move::N);
        else if(D) Walk(roostcall::Move::S);
        else if(L) Walk(roostcall::Move::W);
        else if(R) Walk(roostcall::Move::E);
        else if(W) Walk(roostcall::Move::Wait);
    }

    std::string SaveState() const override {
        return SaveWriter(roostcall::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("turns", Core.Turns)
            .Field("settled", Core.Settled)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("whistler", std::to_string(Core.Whistler.R) + "," + std::to_string(Core.Whistler.C))
            .Field("birds", roostcall::Game::CellsString(Core.Birds))
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The whistler, birds and counts are
    // range-checked: birds are distinct, outside the roost, never on the whistler, and settled + remaining is the total.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, roostcall::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const roostcall::Difficulty* Diff = roostcall::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Turns = 0, Settled = 0, Score = 0;
        bool Over = false, Won = false;
        std::vector<roostcall::Cell> WhistlerCell, Birds;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("turns", 0, Diff->Turns, Turns)) return false;
        if(!Fields.Int("settled", 0, Diff->Birds, Settled)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!ParseCells(Fields.Str("whistler"), Diff->Size, WhistlerCell) || WhistlerCell.size() != 1) return false;
        if(!ParseCells(Fields.Str("birds"), Diff->Size, Birds)) return false;
        if(Settled + static_cast<int>(Birds.size()) != Diff->Birds) return false;
        if(!Over && Turns == 0) return false;

        roostcall::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        for(const roostcall::Cell& B : Birds) {
            if(Fresh.InRoost(B) || B == WhistlerCell[0]) return false;
        }

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Whistler = WhistlerCell[0];
        Core.Birds = Birds;
        Core.Turns = Turns;
        Core.Settled = Settled;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT Every bird is home. Pad A or R scatters a new flock."
                            : "HINT Dusk fell. Pad A or R scatters a new flock.";
        }
        if(Option == 1) return "HINT Practice: the blue cell is where the watcher would stand next.";
        if(Core.Birds.size() == 1) return "HINT One left. Stand beside a cornered bird to send it along the edge.";
        return "HINT Birds fly to the open cell farthest from you. Walk up behind them, roost-side last.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Turns <= 3 ? "CUE Dusk is close" : "CUE Herd a bird";
    }
    std::string HowToLine() const override {
        return "HOW Walk up behind the glimmer-birds so they flee one step at a time; drive every bird into the roost corner before your turns run out.";
    }
    std::string KeyHint() const override { return "KEYS Arrows walk one cell; A waits a turn."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Moss{200, 230, 200, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Bird{255, 210, 120, 255}, RoostTint{60, 120, 90, 255};
        const int S = Core.Size();
        const int Total = Core.Diff ? Core.Diff->Birds : 0;

        F.Clear(800, 600, {14, 22, 16, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "ROOSTCALL GUIDE  [" : "ROOSTCALL  [") + CabinetDifficulty() + "]", Moss, 26);
        F.AddText(28, 56, "TURNS " + std::to_string(Core.Turns) + "   HOME " + std::to_string(Core.Settled) + "/" + std::to_string(Total) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(S <= 0) return;

        // The yard: cells, the roost corner tinted, birds as discs, the whistler as a gold disc; the guide cell in blue
        const double Cell = 380.0 / S, GridLeft = 200, GridTop = 100;
        const bool HasGuide = Option == 1 && !Core.Over;
        const roostcall::Move Guide = HasGuide ? Core.DemoAction() : roostcall::Move::Wait;
        F.AddRect(GridLeft - 8, GridTop - 8, S * Cell + 16, S * Cell + 16, {28, 44, 32, 255});
        for(int R = 0; R < S; ++R) {
            for(int C = 0; C < S; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const roostcall::Cell Here{R, C};
                F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Core.InRoost(Here) ? RoostTint : Color{40, 60, 44, 255});
                if(Core.BirdAt(Here) >= 0) F.AddCircle(X + Cell / 2, Y + Cell / 2, Cell * 0.26, Bird);
            }
        }
        // Scare range around the whistler: a faint frame two cells out
        {
            const double Reach = roostcall::ScareRange;
            const double X0 = GridLeft + (Core.Whistler.C - Reach) * Cell, Y0 = GridTop + (Core.Whistler.R - Reach) * Cell;
            F.AddRect(X0, Y0, (2 * Reach + 1) * Cell, 3, {90, 110, 90, 255});
            F.AddRect(X0, Y0 + (2 * Reach + 1) * Cell - 3, (2 * Reach + 1) * Cell, 3, {90, 110, 90, 255});
            F.AddRect(X0, Y0, 3, (2 * Reach + 1) * Cell, {90, 110, 90, 255});
            F.AddRect(X0 + (2 * Reach + 1) * Cell - 3, Y0, 3, (2 * Reach + 1) * Cell, {90, 110, 90, 255});
        }
        if(HasGuide && Guide != roostcall::Move::Wait) {
            const int GR = Core.Whistler.R + roostcall::MoveDR(Guide), GC = Core.Whistler.C + roostcall::MoveDC(Guide);
            F.AddRect(GridLeft + GC * Cell + 3, GridTop + GR * Cell + 3, Cell - 6, Cell - 6, Sky);
        }
        F.AddCircle(GridLeft + Core.Whistler.C * Cell + Cell / 2, GridTop + Core.Whistler.R * Cell + Cell / 2, Cell * 0.3, Gold);

        F.AddText(600, 110, "ROOST", Moss, 14);
        F.AddRect(600, 130, 70, 30, RoostTint);
        F.AddText(600, 170, "south-east corner", Moss, 11);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: EVERY BIRD IS HOME" : "LOST: DUSK FALLS", Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Home = std::to_string(Core.Settled) + "/" + std::to_string(Core.Diff ? Core.Diff->Birds : 0);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Every bird is home; " : "Dusk fell; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R scatters a new flock; home " + Home};
        }
        return {Core.Score, 1, false, false, "Turns " + std::to_string(Core.Turns) + "; home " + Home};
    }
};

}} // daedalus::desktop
