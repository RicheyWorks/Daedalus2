// SPDX-License-Identifier: MIT
// Emberkiln (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusEmberkilnCore.h, a port of
// tools/minigames/emberkiln.py (the rules authority). CPython-compatible seeding, so StartGame("emberkiln", seed)
// lays the same floor as emberkiln.start(seed, difficulty).
//
//   Arrows / d-pad / stick   move the tongs (cursor) one cell
//   pad A / J / Space        set a coal under the tongs (one turn)
//   R / pad Start            restart a finished firing
//   option 0 Emberkiln; option 1 Guide practice marks the cell the stoker would coal and says what it does
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusEmberkilnCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class EmberkilnGame final : public Game {
    emberkiln::Game Core;
    emberkiln::Cell Tongs;    // the cursor
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last coal; empty until the first
    EdgeLatch UpEdge, DownEdge, LeftEdge, RightEdge, CoalEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Tongs = {0, 0};
        LastResult.clear();
        UpEdge.Clear();
        DownEdge.Clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        CoalEdge.Clear();
    }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool CoalPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }

    /** Parses one digit per cell, rows joined by ';', into a Size x Size grid; every digit must pass `Allowed`. */
    template <class Allowed>
    static bool ParseGrid(const std::string& Text, int Size, emberkiln::Game::Grid& Out, Allowed Ok) {
        const std::vector<std::string> Rows = SplitText(Text, ';');
        if(static_cast<int>(Rows.size()) != Size) return false;
        for(auto& Row : Out) Row.fill(0);
        for(int R = 0; R < Size; ++R) {
            if(static_cast<int>(Rows[static_cast<size_t>(R)].size()) != Size) return false;
            for(int C = 0; C < Size; ++C) {
                const char Digit = Rows[static_cast<size_t>(R)][static_cast<size_t>(C)];
                if(Digit < '0' || Digit > '9' || !Ok(Digit - '0')) return false;
                Out[static_cast<size_t>(R)][static_cast<size_t>(C)] = Digit - '0';
            }
        }
        return true;
    }

public:
    const emberkiln::Game& CoreState() const { return Core; }
    emberkiln::Cell TongsCell() const { return Tongs; }
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

    /** Moves the tongs one cell; false at the edge of the floor or once the firing is over. */
    bool Nudge(int DR, int DC) {
        if(Core.Over) return false;
        const emberkiln::Cell Next{Tongs.R + DR, Tongs.C + DC};
        if(!Core.Inside(Next)) return false;
        Tongs = Next;
        return true;
    }
    /** One turn: a coal under the tongs. False once the firing is over. */
    bool SetCoal() {
        if(Core.Over) return false;
        emberkiln::Outcome Did;
        std::string Result;
        if(Core.Step(Tongs, Did, Result) != emberkiln::Game::Act::Ok) return false;
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
            case SourceKey::Up:    Nudge(-1, 0); break;
            case SourceKey::Down:  Nudge(1, 0); break;
            case SourceKey::Left:  Nudge(0, -1); break;
            case SourceKey::Right: Nudge(0, 1); break;
            default:
                if(SourceKey::IsConfirm(Key)) SetCoal();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            SetCoal();
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
            if(CoalPressed(I)) Deal();
            return;
        }
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool Coal = CoalEdge.Rose(CoalPressed(I));
        if(U) Nudge(-1, 0);
        else if(D) Nudge(1, 0);
        else if(L) Nudge(0, -1);
        else if(R) Nudge(0, 1);
        else if(Coal) SetCoal();
    }

    std::string SaveState() const override {
        return SaveWriter(emberkiln::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("coals", Core.Coals)
            .Field("glazed", Core.GlazedCount)
            .Field("cracked", Core.CrackedCount)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("tongs", std::to_string(Tongs.R) + "," + std::to_string(Tongs.C))
            .Field("floor", Core.FloorString())
            .Field("heat", Core.HeatString())
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The floor is checked cell by cell against the
    // one the seed lays: stone stays stone and cold, a raw tile keeps its target with heat below it, a glazed tile had
    // a target and sits exactly on it, a cracked tile sits past it; the counts must add up to the saved tallies.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, emberkiln::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const emberkiln::Difficulty* Diff = emberkiln::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Coals = 0, Glazed = 0, Cracked = 0, Score = 0;
        bool Over = false, Won = false;
        const int Clay = Diff->Size * Diff->Size - Diff->Stone;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("coals", 0, Diff->Coals, Coals)) return false;
        if(!Fields.Int("glazed", 0, Clay, Glazed)) return false;
        if(!Fields.Int("cracked", 0, Clay, Cracked)) return false;
        if(!Fields.Int("score", -MaxScore, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        const std::vector<std::string> TongsParts = SplitText(Fields.Str("tongs"), ',');
        long long TongsR = 0, TongsC = 0;
        if(TongsParts.size() != 2 || !ParseInteger(TongsParts[0], TongsR) || !ParseInteger(TongsParts[1], TongsC)) return false;
        if(TongsR < 0 || TongsR >= Diff->Size || TongsC < 0 || TongsC >= Diff->Size) return false;

        emberkiln::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        emberkiln::Game::Grid Floor{}, Heat{};
        if(!ParseGrid(Fields.Str("floor"), Diff->Size, Floor, [](int V) { return V == 0 || (V >= 2 && V <= 4) || V == 8 || V == 9; })) return false;
        if(!ParseGrid(Fields.Str("heat"), Diff->Size, Heat, [](int V) { return V <= 6; })) return false;
        int SeenGlazed = 0, SeenCracked = 0, Raw = 0;
        for(int R = 0; R < Diff->Size; ++R) {
            for(int C = 0; C < Diff->Size; ++C) {
                const int Laid = Fresh.TargetAt({R, C});
                int& Saved = Floor[static_cast<size_t>(R)][static_cast<size_t>(C)];
                const int H = Heat[static_cast<size_t>(R)][static_cast<size_t>(C)];
                if(Laid == emberkiln::Stone) {
                    if(Saved != 0 || H != 0) return false;
                } else if(Saved == 9) {
                    if(H != Laid) return false;
                    Saved = emberkiln::Glazed;
                    ++SeenGlazed;
                } else if(Saved == 8) {
                    if(H <= Laid) return false;
                    Saved = emberkiln::Cracked;
                    ++SeenCracked;
                } else {
                    if(Saved != Laid || H >= Laid) return false;
                    ++Raw;
                }
            }
        }
        if(SeenGlazed != Glazed || SeenCracked != Cracked) return false;
        if(Over != (Raw == 0 || Coals == 0) || Won != (Raw == 0 && Cracked == 0)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Target = Floor;
        Core.Heat = Heat;
        Core.Coals = Coals;
        Core.GlazedCount = Glazed;
        Core.CrackedCount = Cracked;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Tongs = {static_cast<int>(TongsR), static_cast<int>(TongsC)};
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The whole floor shines. Pad A or R lays a new floor."
                            : "HINT The firing is spoiled. Pad A or R lays a new floor.";
        }
        if(Option == 1) {
            emberkiln::Outcome O;
            Core.Preview(Core.DemoAction(), O);
            const std::string What = O.Glazes == 0 ? "warms " + std::to_string(O.Raised) + " tiles" : O.Glazes == 1 ? "glazes one tile" : "glazes " + std::to_string(O.Glazes) + " tiles";
            return "HINT Practice: the blue cell is the stoker's pick; it " + What + ". Red-rimmed tiles would crack under the tongs.";
        }
        emberkiln::Outcome Here;
        Core.Preview(Tongs, Here);
        if(Here.Cracks > 0) return "HINT A coal here cracks " + std::to_string(Here.Cracks) + ". Heat a tile one short from a neighbour, stone or a glazed tile.";
        return "HINT A coal adds 2 under the tongs and 1 around it. Glaze at the exact target; never past it.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Coals <= 3 ? "CUE Last coals" : "CUE Set a coal";
    }
    std::string HowToLine() const override {
        return "HOW Set a coal: the clay under it gains 2 heat and its neighbours gain 1 (stone and finished tiles only warm neighbours). A tile glazes at exactly its target and cracks past it. Glaze every tile before the coals run out.";
    }
    std::string KeyHint() const override { return "KEYS Arrows move the tongs; A sets a coal."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Ash{220, 210, 200, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Ember{255, 120, 60, 255}, Crack{120, 40, 40, 255};
        const Color StoneTint{70, 70, 76, 255}, GlazeTint{90, 190, 170, 255}, RawTint{110, 70, 50, 255};
        const int S = Core.Size();

        F.Clear(800, 600, {24, 14, 10, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "EMBERKILN GUIDE  [" : "EMBERKILN  [") + CabinetDifficulty() + "]", Ash, 26);
        F.AddText(28, 56, "COALS " + std::to_string(Core.Coals) + "   GLAZED " + std::to_string(Core.GlazedCount) + "   CRACKED " + std::to_string(Core.CrackedCount) + "   RAW " + std::to_string(Core.Raw()) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(S <= 0) return;

        // The floor: stone grey, raw clay brown with heat/target, glazed teal, cracked dark red; tiles a coal under
        // the tongs would crack are rimmed red; the guide cell is blue; the tongs are a gold frame
        const double Cell = 380.0 / S, GridLeft = 200, GridTop = 100;
        const bool HasGuide = Option == 1 && !Core.Over;
        const emberkiln::Cell Guide = HasGuide ? Core.DemoAction() : emberkiln::Cell{-1, -1};
        F.AddRect(GridLeft - 8, GridTop - 8, S * Cell + 16, S * Cell + 16, {50, 32, 24, 255});
        for(int R = 0; R < S; ++R) {
            for(int C = 0; C < S; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const emberkiln::Cell Here{R, C};
                const int T = Core.TargetAt(Here);
                const Color Tint = T == emberkiln::Stone ? StoneTint : T == emberkiln::Glazed ? GlazeTint : T == emberkiln::Cracked ? Crack : RawTint;
                F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Tint);
                if(T > 0) {
                    F.AddText(X + Cell * 0.18, Y + Cell * 0.3, std::to_string(Core.HeatAt(Here)) + "/" + std::to_string(T), Gold, 13);
                    if(!Core.Over && WouldCrack(Here)) F.AddRect(X + 1, Y + 1, Cell - 2, 3, Ember);
                }
                if(Here == Guide) F.AddRect(X + Cell * 0.35, Y + Cell * 0.62, Cell * 0.3, Cell * 0.2, Sky);
            }
        }
        {
            const double X = GridLeft + Tongs.C * Cell, Y = GridTop + Tongs.R * Cell;
            F.AddRect(X, Y, Cell, 3, Gold);
            F.AddRect(X, Y + Cell - 3, Cell, 3, Gold);
            F.AddRect(X, Y, 3, Cell, Gold);
            F.AddRect(X + Cell - 3, Y, 3, Cell, Gold);
        }

        if(Core.FreshFloor()) {
            F.AddText(600, 360, "TONGS arrows move; A sets a coal", Ash, 11);
            F.AddText(600, 378, "HEAT  +2 under the coal, +1 on each neighbour", Ash, 11);
            F.AddText(600, 396, "GLAZE reach the target exactly; past it cracks", Ash, 11);
        }
        F.AddText(600, 110, "KEY", Ash, 14);
        F.AddRect(600, 130, 18, 18, RawTint);
        F.AddText(624, 132, "raw  heat/target", Ash, 11);
        F.AddRect(600, 154, 18, 18, GlazeTint);
        F.AddText(624, 156, "glazed", Ash, 11);
        F.AddRect(600, 178, 18, 18, Crack);
        F.AddText(624, 180, "cracked", Ash, 11);
        F.AddRect(600, 202, 18, 18, StoneTint);
        F.AddText(624, 204, "stone", Ash, 11);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: THE WHOLE FLOOR SHINES" : "LOST: THE FIRING IS SPOILED", Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "glazed " + std::to_string(Core.GlazedCount) + ", cracked " + std::to_string(Core.CrackedCount);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The whole floor shines; " : "The firing is spoiled; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R lays a new floor; " + Tally};
        }
        return {Core.Score, 1, false, false, "Coals " + std::to_string(Core.Coals) + "; " + Tally};
    }

private:
    /** True when a coal under the tongs would crack the tile at `Here` (so the screen can rim it red). */
    bool WouldCrack(emberkiln::Cell Here) const {
        if(!Core.IsRaw(Here)) return false;
        int Gain = 0;
        if(Here == Tongs) Gain = emberkiln::CoalHeat;
        else if((Here.R == Tongs.R && (Here.C == Tongs.C - 1 || Here.C == Tongs.C + 1)) || (Here.C == Tongs.C && (Here.R == Tongs.R - 1 || Here.R == Tongs.R + 1))) Gain = emberkiln::SpreadHeat;
        return Gain > 0 && Core.HeatAt(Here) + Gain > Core.TargetAt(Here);
    }
};

}} // daedalus::desktop
