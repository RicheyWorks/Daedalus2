// SPDX-License-Identifier: MIT
// Fogbell Ferry (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusFogbellCore.h, a port of
// tools/minigames/fogbell.py (the rules authority). CPython-compatible seeding, so StartGame("fogbell", seed) lays
// the same tidal flat as fogbell.start(seed, difficulty).
//
//   Arrows / d-pad / stick   steer the ferry one cell (each press is one turn)
//   pad A / J / Space        wait a turn
//   R / pad Start            restart a finished voyage
//   option 0 Ferry; option 1 Guide practice marks the cell the watcher would steer to
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusFogbellCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class FogbellGame final : public Game {
    fogbell::Game Core;
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

    /** Parses "7744757|3566755|..." into a Size x Size height grid with every height in [1, Size]. */
    static bool ParseHeights(const std::string& Text, int Size, std::vector<std::vector<int>>& Out) {
        Out.clear();
        const std::vector<std::string> Rows = SplitText(Text, '|');
        if(static_cast<int>(Rows.size()) != Size) return false;
        for(const std::string& Row : Rows) {
            if(static_cast<int>(Row.size()) != Size) return false;
            std::vector<int> Heights;
            for(char Ch : Row) {
                if(Ch < '1' || Ch > '9' || Ch - '0' > Size) return false;
                Heights.push_back(Ch - '0');
            }
            Out.push_back(Heights);
        }
        return true;
    }
    /** Parses "r,c;r,c" ("-" for none) into cells inside the flat. */
    static bool ParseCells(const std::string& Text, int Size, std::vector<fogbell::Cell>& Out) {
        Out.clear();
        if(Text == "-") return true;
        for(const std::string& Token : SplitText(Text, ';')) {
            const std::vector<std::string> Parts = SplitText(Token, ',');
            long long R = 0, C = 0;
            if(Parts.size() != 2 || !ParseInteger(Parts[0], R) || !ParseInteger(Parts[1], C)) return false;
            if(R < 0 || R >= Size || C < 0 || C >= Size) return false;
            Out.push_back({static_cast<int>(R), static_cast<int>(C)});
        }
        return true;
    }

public:
    const fogbell::Game& CoreState() const { return Core; }
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

    /** One turn: steer (or wait). False when the rules refuse it (off the flat, under water, finished). */
    bool Steer(fogbell::Move M) {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(M, Result) != fogbell::Game::Act::Ok) return false;
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
            case SourceKey::Up:    Steer(fogbell::Move::N); break;
            case SourceKey::Down:  Steer(fogbell::Move::S); break;
            case SourceKey::Left:  Steer(fogbell::Move::W); break;
            case SourceKey::Right: Steer(fogbell::Move::E); break;
            default:
                if(SourceKey::IsConfirm(Key)) Steer(fogbell::Move::Wait);
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Steer(fogbell::Move::Wait);
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
        if(U) Steer(fogbell::Move::N);
        else if(D) Steer(fogbell::Move::S);
        else if(L) Steer(fogbell::Move::W);
        else if(R) Steer(fogbell::Move::E);
        else if(W) Steer(fogbell::Move::Wait);
    }

    std::string SaveState() const override {
        return SaveWriter(fogbell::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("turn", Core.Turn)
            .Field("aboard", Core.Aboard)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("ferry", std::to_string(Core.Ferry.R) + "," + std::to_string(Core.Ferry.C))
            .Field("heights", Core.HeightsString())
            .Field("passengers", fogbell::Game::CellsString(Core.Passengers))
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The flat is regenerated from the seed and the
    // saved heights must equal it (heights never change in play); ferry, docks and counts are range-checked.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, fogbell::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const fogbell::Difficulty* Diff = fogbell::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Turn = 0, Aboard = 0, Score = 0;
        bool Over = false, Won = false;
        std::vector<std::vector<int>> Heights;
        std::vector<fogbell::Cell> Passengers, FerryCell;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("turn", 0, fogbell::TideEvery * Diff->Size, Turn)) return false;
        if(!Fields.Int("aboard", 0, Diff->Passengers, Aboard)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!ParseCells(Fields.Str("ferry"), Diff->Size, FerryCell) || FerryCell.size() != 1) return false;
        if(!ParseHeights(Fields.Str("heights"), Diff->Size, Heights)) return false;
        if(!ParseCells(Fields.Str("passengers"), Diff->Size, Passengers)) return false;
        if(Aboard + static_cast<int>(Passengers.size()) != Diff->Passengers) return false;

        fogbell::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        if(Fresh.Heights != Heights) return false;   // the flat is fixed by the seed
        for(const fogbell::Cell& P : Passengers) if(Fresh.PassengerAt(P.R, P.C) < 0) return false;   // docks are fixed too
        Fresh.Turn = Turn;
        if(!Over && Fresh.Flooded(FerryCell[0].R, FerryCell[0].C)) return false;   // a live ferry is never under water

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Ferry = FerryCell[0];
        Core.Passengers = Passengers;
        Core.Aboard = Aboard;
        Core.Turn = Turn;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The bell rings clear. Pad A or R sets out again."
                            : "HINT The voyage is lost. Pad A or R sets out again.";
        }
        if(Option == 1) {
            bool Picks = false, Lands = false, Floods = false;
            const fogbell::Move Guide = Core.DemoAction();
            Core.Preview(Guide, Picks, Lands, Floods);
            std::string What = Picks ? "takes a lantern" : Lands ? "makes harbour" : Guide == fogbell::Move::Wait ? "waits" : "crosses open water";
            return "HINT Practice: the blue cell is the watcher's pick; it " + What + ". Red-edged cells flood at the next toll.";
        }
        const int Need = Core.Diff ? Core.Diff->Need : 0;
        if(Core.Aboard >= Need) return "HINT Enough lanterns aboard: make for the harbour before the tide cuts the way.";
        return "HINT Low ground floods first. Pick up lanterns on the way and keep a dry route home.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        const int Need = Core.Diff ? Core.Diff->Need : 0;
        return Core.Aboard >= Need ? "CUE Make harbour" : "CUE Steer to a lantern";
    }
    std::string HowToLine() const override {
        return "HOW Move the ferry one cell a turn across the tidal flat, pick up the lantern passengers from their docks and reach the harbour before the rising tide floods your cell.";
    }
    std::string KeyHint() const override { return "KEYS Arrows steer one cell; A waits a turn."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{220, 230, 240, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Water{30, 60, 110, 255}, Lantern{255, 200, 90, 255};
        const int S = Core.Size();
        const int Need = Core.Diff ? Core.Diff->Need : 0;

        F.Clear(800, 600, {12, 18, 28, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "FOGBELL GUIDE  [" : "FOGBELL FERRY  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "TURN " + std::to_string(Core.Turn) + "   TIDE " + std::to_string(Core.Tide()) + "   ABOARD " + std::to_string(Core.Aboard) + "/" + std::to_string(Need)
                          + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(S <= 0) return;

        // The flat: a cell per height, darker as it nears the tide, water once flooded; docks carry lanterns
        const double Cell = 380.0 / S, GridLeft = 200, GridTop = 100;
        const bool HasGuide = Option == 1 && !Core.Over;
        const fogbell::Move Guide = HasGuide ? Core.DemoAction() : fogbell::Move::Wait;
        F.AddRect(GridLeft - 8, GridTop - 8, S * Cell + 16, S * Cell + 16, {24, 34, 52, 255});
        for(int R = 0; R < S; ++R) {
            for(int C = 0; C < S; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const int H = Core.Heights[static_cast<size_t>(R)][static_cast<size_t>(C)];
                if(Core.Flooded(R, C)) {
                    F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Water);
                } else {
                    const std::uint8_t Shade = static_cast<std::uint8_t>(70 + (H - Core.Tide()) * 100 / S);
                    F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, {Shade, static_cast<std::uint8_t>(Shade - 10), static_cast<std::uint8_t>(Shade - 30), 255});
                    F.AddText(X + Cell / 2 - 4, Y + Cell / 2 - 7, std::to_string(H), {20, 20, 30, 255}, 11);
                }
                if(!Core.Flooded(R, C) && Core.Flooded(R, C, Core.Turn + 1) && !Core.Over) F.AddRect(X + 1, Y + Cell - 5, Cell - 2, 4, {220, 80, 70, 255});   // floods at the next toll
                if(Core.PassengerAt(R, C) >= 0) F.AddCircle(X + Cell / 2, Y + Cell / 2, Cell * 0.22, Lantern);
                if(fogbell::Cell{R, C} == Core.Harbour) F.AddRect(X + 4, Y + 4, Cell - 8, Cell - 8, {60, 160, 120, 255});
            }
        }
        if(HasGuide && Guide != fogbell::Move::Wait) {
            const int GR = Core.Ferry.R + fogbell::MoveDR(Guide), GC = Core.Ferry.C + fogbell::MoveDC(Guide);
            F.AddRect(GridLeft + GC * Cell + 3, GridTop + GR * Cell + 3, Cell - 6, Cell - 6, Sky);
        }
        // The ferry
        F.AddCircle(GridLeft + Core.Ferry.C * Cell + Cell / 2, GridTop + Core.Ferry.R * Cell + Cell / 2, Cell * 0.3, Gold);

        if(Core.FreshVoyage()) {
            F.AddText(600, 360, "STEER arrows move one cell a turn; A waits", Mist, 11);
            F.AddText(600, 378, "TIDE  the bell tolls every " + std::to_string(fogbell::TideEvery) + " turns; low cells flood", Mist, 11);
            F.AddText(600, 396, "LAND  board lanterns; reach the harbour with " + std::to_string(Need) + " aboard", Mist, 11);
        }
        F.AddText(600, 110, "TIDE", Mist, 14);
        for(int L = 1; L <= S; ++L) F.AddRect(600, 130 + (S - L) * 14, 70, 10, L <= Core.Tide() ? Water : Color{50, 60, 80, 255});
        F.AddText(600, 130 + S * 14 + 6, "bell every " + std::to_string(fogbell::TideEvery) + " turns", Mist, 11);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: THE BELL RINGS CLEAR" : "LOST: THE TIDE TAKES THE FERRY", Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Aboard = std::to_string(Core.Aboard) + "/" + std::to_string(Core.Diff ? Core.Diff->Need : 0);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The bell rings clear; " : "The voyage is lost; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R sets out again; aboard " + Aboard};
        }
        return {Core.Score, 1, false, false, "Turn " + std::to_string(Core.Turn) + "; tide " + std::to_string(Core.Tide()) + "; aboard " + Aboard};
    }
};

}} // daedalus::desktop
