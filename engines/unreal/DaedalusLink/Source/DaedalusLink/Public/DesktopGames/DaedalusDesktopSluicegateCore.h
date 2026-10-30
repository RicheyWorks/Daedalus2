// SPDX-License-Identifier: MIT
// Sluicegate (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusSluicegateCore.h, a port of
// tools/minigames/sluicegate.py (the rules authority). CPython-compatible seeding, so StartGame("sluicegate", seed)
// lays the same field as sluicegate.start(seed, difficulty).
//
//   Arrows / d-pad / stick   move the marker one cell (free)
//   pad A / J / Space        drop a gate under the marker (one push)
//   pad B / K                wait: let the water push without a gate
//   R / pad Start            restart a finished field
//   option 0 Sluicegate; option 1 Guide practice marks the gatekeeper's pick and says how its rollout ends
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusSluicegateCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class SluicegateGame final : public Game {
    sluicegate::Game Core;
    sluicegate::Cell Marker;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last push; empty until the first
    EdgeLatch UpEdge, DownEdge, LeftEdge, RightEdge, GateEdge, WaitEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Marker = Core.Head;
        LastResult.clear();
        UpEdge.Clear();
        DownEdge.Clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        GateEdge.Clear();
        WaitEdge.Clear();
    }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool GatePressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed; }
    static bool WaitPressed(const Input& I) { return I.DashPressed; }

    /** Parses "r,c;r,c" ("-" for none) into distinct cells inside the field. */
    static bool ParseCells(const std::string& Text, int Size, std::vector<sluicegate::Cell>& Out) {
        Out.clear();
        if(Text == "-") return true;
        for(const std::string& Token : SplitText(Text, ';')) {
            const std::vector<std::string> Parts = SplitText(Token, ',');
            long long R = 0, C = 0;
            if(Parts.size() != 2 || !ParseInteger(Parts[0], R) || !ParseInteger(Parts[1], C)) return false;
            if(R < 0 || R >= Size || C < 0 || C >= Size) return false;
            const sluicegate::Cell Cell{static_cast<int>(R), static_cast<int>(C)};
            for(const sluicegate::Cell& Seen : Out) if(Seen == Cell) return false;
            Out.push_back(Cell);
        }
        return true;
    }

public:
    const sluicegate::Game& CoreState() const { return Core; }
    sluicegate::Cell MarkerCell() const { return Marker; }
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

    /** Moves the marker one cell; false at the field's edge or once the field is over. */
    bool Nudge(int DR, int DC) {
        if(Core.Over) return false;
        const sluicegate::Cell Next{Marker.R + DR, Marker.C + DC};
        if(!Core.Inside(Next)) return false;
        Marker = Next;
        return true;
    }
    /** One push, with a gate under the marker or (NoCell) none. False when the rules refuse it. */
    bool Push(sluicegate::Cell Gate) {
        if(Core.Over) return false;
        int Reached = 0, Filled = 0;
        std::string Result;
        if(Core.Step(Gate, Reached, Filled, Result) != sluicegate::Game::Act::Ok) return false;
        LastResult = Result;
        return true;
    }
    bool DropGate() { return Push(Marker); }
    bool Wait() { return Push(sluicegate::NoCell); }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:    Nudge(-1, 0); break;
            case SourceKey::Down:  Nudge(1, 0); break;
            case SourceKey::Left:  Nudge(0, -1); break;
            case SourceKey::Right: Nudge(0, 1); break;
            case SourceKey::B:     Wait(); break;
            default:
                if(SourceKey::IsConfirm(Key)) DropGate();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            DropGate();
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
            if(GatePressed(I) || WaitPressed(I)) Deal();
            return;
        }
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool G = GateEdge.Rose(GatePressed(I));
        const bool W = WaitEdge.Rose(WaitPressed(I));
        if(U) Nudge(-1, 0);
        else if(D) Nudge(1, 0);
        else if(L) Nudge(0, -1);
        else if(R) Nudge(0, 1);
        else if(G) DropGate();
        else if(W) Wait();
    }

    std::string SaveState() const override {
        return SaveWriter(sluicegate::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("turns", Core.Turns)
            .Field("left", Core.GatesLeft)
            .Field("filled", Core.Filled)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("marker", std::to_string(Marker.R) + "," + std::to_string(Marker.C))
            .Field("wet", sluicegate::Game::CellsString(Core.Wet))
            .Field("gates", sluicegate::Game::CellsString(Core.Gates))
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The field, cisterns and mill come from the
    // seed; the wet list and gates are checked against it: every wet cell is an open channel starting with the
    // headgate, no gate is wet, a cistern, the mill or the headgate, the filled count is the wet cisterns, the gate
    // stock and turns add up, and the over/won flags follow the rules.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, sluicegate::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const sluicegate::Difficulty* Diff = sluicegate::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Turns = 0, Left = 0, Filled = 0, Score = 0;
        bool Over = false, Won = false;
        std::vector<sluicegate::Cell> MarkerCells, Wet, Gates;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("turns", 0, Diff->Turns, Turns)) return false;
        if(!Fields.Int("left", 0, Diff->Gates, Left)) return false;
        if(!Fields.Int("filled", 0, Diff->Cisterns, Filled)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!ParseCells(Fields.Str("marker"), Diff->Size, MarkerCells) || MarkerCells.size() != 1) return false;
        if(!ParseCells(Fields.Str("wet"), Diff->Size, Wet) || Wet.empty()) return false;
        if(!ParseCells(Fields.Str("gates"), Diff->Size, Gates)) return false;
        if(static_cast<int>(Gates.size()) != Diff->Gates - Left) return false;
        if(Diff->Turns - Turns < static_cast<int>(Gates.size())) return false;

        sluicegate::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        if(Wet[0] != Fresh.Head) return false;
        int WetCisterns = 0;
        bool MillWet = false;
        for(const sluicegate::Cell& W : Wet) {
            if(!Fresh.IsChannel(W)) return false;
            for(const sluicegate::Cell& G : Gates) if(G == W) return false;
            if(Fresh.IsCistern(W)) ++WetCisterns;
            if(W == Fresh.Mill) MillWet = true;
        }
        for(const sluicegate::Cell& G : Gates) {
            if(!Fresh.IsChannel(G) || Fresh.IsCistern(G) || G == Fresh.Mill || G == Fresh.Head) return false;
        }
        if(WetCisterns != Filled) return false;
        const bool AllFilled = Filled == static_cast<int>(Fresh.Cisterns.size());
        if(Won != (AllFilled && !MillWet)) return false;
        if(!Over && (MillWet || AllFilled || Turns == 0)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Wet = Wet;
        Core.Gates = Gates;
        Core.GatesLeft = Left;
        Core.Turns = Turns;
        Core.Filled = Filled;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Marker = MarkerCells[0];
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT Every cistern brims. Pad A or R opens a new field."
                            : "HINT The channel failed. Pad A or R opens a new field.";
        }
        if(Option == 1) {
            const sluicegate::Cell Pick = Core.DemoAction();
            const sluicegate::Ending E = Core.Rollout(Pick);
            const std::string How = E.Won ? "fills every cistern" : E.Flooded ? "still floods the mill" : "fills " + std::to_string(E.Filled) + " before the water stops";
            return std::string("HINT Practice: ") + (Pick == sluicegate::NoCell ? "the gatekeeper waits" : "the blue cell is the gatekeeper's gate") + "; left alone the water then " + How + ".";
        }
        if(Core.Mill != sluicegate::NoCell && !Core.IsWet(Core.Mill)) {
            sluicegate::DistanceMap Dist;
            Core.Distances(Core.GateMask(), Dist);
            const int D = Dist[static_cast<size_t>(Core.Mill.R)][static_cast<size_t>(Core.Mill.C)];
            if(D >= 0 && D <= 3) return "HINT The water is " + std::to_string(D) + " cells from the mill wheel. Gate its throat.";
        }
        if(Core.GatesLeft == 0) return "HINT No gates left; the water finds its own way now. Press B to let it run.";
        return "HINT Gates block a branch so the push goes elsewhere. Pale cells are the next push; B waits.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Turns <= 2 ? "CUE Headgate closing" : "CUE Steer the water";
    }
    std::string HowToLine() const override {
        return "HOW Each turn the headgate pushes a few cells of water into the nearest open channels. Drop a gate on a dry channel to block a branch, or wait. Fill every cistern before the headgate closes; keep the water off the mill wheel.";
    }
    std::string KeyHint() const override { return "KEYS Arrows move the marker; A drops a gate; B waits."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Water{70, 130, 210, 255}, NextWater{120, 170, 230, 255};
        const Color RockTint{60, 58, 56, 255}, ChannelTint{120, 112, 96, 255}, CisternDry{180, 150, 70, 255}, CisternFull{90, 190, 170, 255}, MillTint{200, 80, 60, 255}, GateTint{40, 30, 24, 255};
        const int S = Core.Size();
        const int Total = static_cast<int>(Core.Cisterns.size());

        F.Clear(800, 600, {16, 20, 26, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SLUICEGATE GUIDE  [" : "SLUICEGATE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "TURNS " + std::to_string(Core.Turns) + "   GATES " + std::to_string(Core.GatesLeft) + "   FILLED " + std::to_string(Core.Filled) + "/" + std::to_string(Total) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(S <= 0) return;

        // The field: rock dark, channels pale, water blue, the next push's cells lighter blue, cisterns amber (teal
        // when full), the mill red, gates as dark bars; the guide gate in blue; the marker a gold frame
        const double Cell = 380.0 / S, GridLeft = 200, GridTop = 100;
        const bool HasGuide = Option == 1 && !Core.Over;
        const sluicegate::Cell Guide = HasGuide ? Core.DemoAction() : sluicegate::NoCell;
        std::vector<sluicegate::Cell> NextPush;
        int NextFilled = 0;
        bool NextFlood = false;
        if(!Core.Over) Core.Preview(sluicegate::NoCell, NextPush, NextFilled, NextFlood);
        F.AddRect(GridLeft - 8, GridTop - 8, S * Cell + 16, S * Cell + 16, {36, 44, 54, 255});
        for(int R = 0; R < S; ++R) {
            for(int C = 0; C < S; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const sluicegate::Cell Here{R, C};
                Color Tint = Core.IsChannel(Here) ? ChannelTint : RockTint;
                if(Core.IsWet(Here)) Tint = Water;
                else if(sluicegate::Game::Has(NextPush, Here)) Tint = NextWater;
                F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Tint);
                if(Core.IsCistern(Here)) F.AddCircle(X + Cell / 2, Y + Cell / 2, Cell * 0.28, Core.IsWet(Here) ? CisternFull : CisternDry);
                if(Here == Core.Mill) F.AddCircle(X + Cell / 2, Y + Cell / 2, Cell * 0.3, MillTint);
                if(Core.IsGate(Here)) F.AddRect(X + Cell * 0.4, Y + 2, Cell * 0.2, Cell - 4, GateTint);
                if(Here == Core.Head) F.AddText(X + Cell * 0.3, Y + Cell * 0.25, "H", Gold, 13);
                if(Here == Guide) F.AddRect(X + Cell * 0.35, Y + Cell * 0.62, Cell * 0.3, Cell * 0.2, Sky);
            }
        }
        {
            const double X = GridLeft + Marker.C * Cell, Y = GridTop + Marker.R * Cell;
            F.AddRect(X, Y, Cell, 3, Gold);
            F.AddRect(X, Y + Cell - 3, Cell, 3, Gold);
            F.AddRect(X, Y, 3, Cell, Gold);
            F.AddRect(X + Cell - 3, Y, 3, Cell, Gold);
        }

        if(Core.FreshField()) {
            F.AddText(600, 360, "FLOW  the headgate pushes " + std::to_string(Core.Diff ? Core.Diff->Flow : 0) + " cells a turn, nearest first", Mist, 11);
            F.AddText(600, 378, "GATE  A drops a gate under the marker to block a branch", Mist, 11);
            F.AddText(600, 396, "GOAL  fill every cistern; keep the mill wheel dry", Mist, 11);
        }
        F.AddText(600, 110, "KEY", Mist, 14);
        F.AddCircle(609, 139, 8, CisternDry);
        F.AddText(624, 132, "cistern (dry)", Mist, 11);
        F.AddCircle(609, 163, 8, MillTint);
        F.AddText(624, 156, "mill wheel", Mist, 11);
        F.AddRect(600, 178, 18, 18, NextWater);
        F.AddText(624, 180, "next push", Mist, 11);
        F.AddRect(606, 202, 6, 18, GateTint);
        F.AddText(624, 204, "gate", Mist, 11);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: EVERY CISTERN BRIMS" : (Core.Mill != sluicegate::NoCell && Core.IsWet(Core.Mill) ? "LOST: THE MILL WHEEL FLOODS" : "LOST: THE WATER NEVER CAME"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "filled " + std::to_string(Core.Filled) + "/" + std::to_string(Core.Cisterns.size());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Every cistern brims; " : "The channel failed; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R opens a new field; " + Tally};
        }
        return {Core.Score, 1, false, false, "Turns " + std::to_string(Core.Turns) + ", gates " + std::to_string(Core.GatesLeft) + "; " + Tally};
    }
};

}} // daedalus::desktop
