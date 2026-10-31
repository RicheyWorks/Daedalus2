// SPDX-License-Identifier: MIT
// Stonecourse (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusStonecourseCore.h, a port of
// tools/minigames/stonecourse.py (the rules authority). CPython-compatible seeding, so StartGame("stonecourse", seed)
// draws the same supply as stonecourse.start(seed, difficulty).
//
//   Left / Right / d-pad / stick   move the marker along the wall (the stone's left edge)
//   pad A / J / Space              set the next stone at the marker (one turn)
//   pad B / K                      skip the next stone to the rubble (one turn)
//   R / pad Start                  restart a finished build
//   option 0 Stonecourse; option 1 Guide practice marks the column (or the skip) the mason's search takes next
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusStonecourseCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class StonecourseGame final : public Game {
    stonecourse::Game Core;
    int Marker = 0;           // the column the next stone's left edge is over
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last turn; empty until the first
    EdgeLatch LeftEdge, RightEdge, SetEdge, SkipEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Marker = 0;
        LastResult.clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        SetEdge.Clear();
        SkipEdge.Clear();
    }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool SetPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed; }
    static bool SkipPressed(const Input& I) { return I.DashPressed; }

    /** The furthest column the next stone's left edge may sit at and stay on the wall. */
    int LastColumn() const { return std::max(0, Core.Width() - std::max(1, Core.NextStone())); }

public:
    const stonecourse::Game& CoreState() const { return Core; }
    int MarkerColumn() const { return Marker; }
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

    /** Moves the marker one column; false at the wall's ends or once the build is over. */
    bool Nudge(int Delta) {
        if(Core.Over) return false;
        const int Next = Marker + Delta;
        if(Next < 0 || Next > LastColumn()) return false;
        Marker = Next;
        return true;
    }
    /** One turn: the next stone at the marker. False when it does not rest there or the build is over. */
    bool SetStone() {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(Marker, Result) != stonecourse::Game::Act::Ok) return false;
        LastResult = Result;
        Marker = std::min(Marker, LastColumn());
        return true;
    }
    /** One turn: the next stone to the rubble. False with no skips left or once the build is over. */
    bool SkipStone() {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(stonecourse::Skip, Result) != stonecourse::Game::Act::Ok) return false;
        LastResult = Result;
        Marker = std::min(Marker, LastColumn());
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Left:  Nudge(-1); break;
            case SourceKey::Right: Nudge(1); break;
            case SourceKey::B:     SkipStone(); break;
            default:
                if(SourceKey::IsConfirm(Key)) SetStone();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            SetStone();
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
            if(SetPressed(I) || SkipPressed(I)) Deal();
            return;
        }
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool S = SetEdge.Rose(SetPressed(I));
        const bool K = SkipEdge.Rose(SkipPressed(I));
        if(L) Nudge(-1);
        else if(R) Nudge(1);
        else if(S) SetStone();
        else if(K) SkipStone();
    }

    std::string SaveState() const override {
        return SaveWriter(stonecourse::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("index", Core.Index)
            .Field("wall", Core.WallString())
            .Field("locked", Core.Locked)
            .Field("skips", Core.SkipsLeft)
            .Field("marker", Marker)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The supply comes from the seed; the wall
    // must be fully supported course by course, hold no more stone than the supply taken so far, the locked count
    // must be the full courses, the skips must fit the stones taken, and the flags must follow the rules.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, stonecourse::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const stonecourse::Difficulty* Diff = stonecourse::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Index = 0, Locked = 0, Skips = 0, MarkerCol = 0, Score = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("index", 0, Diff->Supply, Index)) return false;
        if(!Fields.Int("locked", 0, Diff->Courses, Locked)) return false;
        if(!Fields.Int("skips", 0, Diff->Skips, Skips)) return false;
        if(!Fields.Int("marker", 0, Diff->Width - 1, MarkerCol)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        const std::vector<std::string> Rows = SplitText(Fields.Str("wall"), ';');
        if(static_cast<int>(Rows.size()) != Diff->Courses) return false;
        stonecourse::Wall Cells;
        for(const std::string& Row : Rows) {
            if(static_cast<int>(Row.size()) != Diff->Width) return false;
            for(char Ch : Row) if(Ch != '0' && Ch != '1') return false;
            Cells += Row;
        }
        int Stone = 0, Full = 0;
        for(int K = 0; K < Diff->Courses; ++K) {
            bool AllFull = true;
            for(int C = 0; C < Diff->Width; ++C) {
                const bool Here = Cells[static_cast<size_t>(K * Diff->Width + C)] == '1';
                if(Here) ++Stone; else AllFull = false;
                if(Here && K > 0 && Cells[static_cast<size_t>((K - 1) * Diff->Width + C)] != '1') return false;
            }
            if(AllFull) ++Full;
        }
        if(Full != Locked) return false;
        if(Diff->Skips - Skips > Index) return false;

        stonecourse::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        int Taken = 0;
        for(int I = 0; I < Index; ++I) Taken += Fresh.Stones[static_cast<size_t>(I)];
        if(Stone > Taken) return false;
        if(Won != (Locked == Diff->Courses)) return false;
        if(!Over && (Won || Index >= Diff->Supply)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Cells = Cells;
        Core.Index = Index;
        Core.Locked = Locked;
        Core.SkipsLeft = Skips;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Marker = std::min(MarkerCol, LastColumn());
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            if(Core.Won) return "HINT The wall stands. Pad A or R draws a new supply.";
            return Core.Index >= Core.Supply() ? "HINT The supply ran out. Pad A or R draws a new supply." : "HINT The stone fit nowhere. Pad A or R draws a new supply.";
        }
        if(Option == 1) {
            const int Pick = Core.DemoAction();
            return Pick == stonecourse::Skip ? "HINT Practice: the mason's line skips this stone (B)."
                                              : "HINT Practice: the blue column is where the mason's line sets this stone.";
        }
        int Course = -1;
        bool Locks = false;
        if(Core.Preview(Marker, Course, Locks)) return Locks ? "HINT A " + std::to_string(Core.NextStone()) + "-stone here locks course " + std::to_string(Course) + "." : "HINT A " + std::to_string(Core.NextStone()) + "-stone here rests on course " + std::to_string(Course) + ". Mind the gaps you leave.";
        std::array<int, stonecourse::MaxWallWidth> Cols{};
        if(Core.Placements(Cols) == 0) return Core.SkipsLeft > 0 ? "HINT This stone fits nowhere; skip it (B)." : "HINT This stone fits nowhere and no skips are left.";
        return "HINT No rest here: every cell under a stone must be filled. Move the marker.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Supply() - Core.Index <= 3 ? "CUE Last stones" : "CUE Set a stone";
    }
    std::string HowToLine() const override {
        return "HOW Set the next stone at a column (it lands on the lowest course that supports it fully) or skip it. Lock every course with no gaps before the supply runs out.";
    }
    std::string KeyHint() const override { return "KEYS Left/Right move the marker; A sets the stone; B skips it."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Stone{150, 140, 125, 255}, LockedTint{110, 170, 140, 255}, Empty{40, 44, 50, 255}, Ghost{90, 85, 80, 255};
        const int W = Core.Width(), H = Core.Courses();

        F.Clear(800, 600, {16, 18, 24, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "STONECOURSE GUIDE  [" : "STONECOURSE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "LOCKED " + std::to_string(Core.Locked) + "/" + std::to_string(H) + "   SUPPLY " + std::to_string(Core.Supply() - Core.Index) + "   SKIPS " + std::to_string(Core.SkipsLeft) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(W <= 0 || H <= 0) return;

        // The wall from the footing up; the next stone as a ghost where it would land (or hovering red if it does not rest)
        const double Cell = std::min(440.0 / W, 300.0 / H), GridLeft = 60, GridBottom = 440;
        const bool HasGuide = Option == 1 && !Core.Over;
        const int Guide = HasGuide ? Core.DemoAction() : -2;
        int Land = -1;
        bool Locks = false;
        const bool Rests = !Core.Over && Core.Preview(Marker, Land, Locks);
        for(int K = 0; K < H; ++K) {
            const bool Full = Core.CourseFull(K);
            for(int C = 0; C < W; ++C) {
                const double X = GridLeft + C * Cell, Y = GridBottom - (K + 1) * Cell;
                F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Core.Filled(K, C) ? (Full ? LockedTint : Stone) : Empty);
            }
        }
        if(!Core.Over && Core.NextStone() > 0) {
            const int Size = Core.NextStone();
            const double Y = Rests ? GridBottom - (Land + 1) * Cell : GridBottom - (H + 1) * Cell - 8;
            F.AddRect(GridLeft + Marker * Cell + 3, Y + 3, Size * Cell - 6, Cell - 6, Rests ? Ghost : Color{160, 70, 60, 255});
            F.AddRect(GridLeft + Marker * Cell, GridBottom + 6, Size * Cell, 4, Gold);
        }
        if(HasGuide && Guide >= 0) F.AddRect(GridLeft + Guide * Cell + Cell * 0.3, GridBottom + 14, Cell * 0.4, 4, Sky);
        if(HasGuide && Guide == stonecourse::Skip) F.AddText(600, 240, "GUIDE: skip this stone", Sky, 13);

        // The supply: the next six stones
        F.AddText(600, 110, "SUPPLY", Mist, 14);
        for(int I = 0; I < 6 && Core.Index + I < Core.Supply(); ++I) {
            const int Size = Core.Stones[static_cast<size_t>(Core.Index + I)];
            F.AddRect(600, 132 + 22 * static_cast<double>(I), 18.0 * Size, 16, I == 0 ? Gold : Stone);
            F.AddText(670, 132 + 22 * static_cast<double>(I), std::to_string(Size) + (I == 0 ? "  next" : ""), Mist, 11);
        }
        if(Core.FreshWall()) {
            F.AddText(600, 360, "SET   Left/Right move the marker; A sets the stone", Mist, 11);
            F.AddText(600, 378, "REST  every cell under a stone must be filled", Mist, 11);
            F.AddText(600, 396, "LOCK  a gapless course locks; " + std::to_string(H) + " courses finish the wall", Mist, 11);
        }
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: THE WALL STANDS" : (Core.Index >= Core.Supply() ? "LOST: THE SUPPLY RUNS OUT" : "LOST: THE STONE FITS NOWHERE"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "locked " + std::to_string(Core.Locked) + "/" + std::to_string(Core.Courses()) + ", supply " + std::to_string(Core.Supply() - Core.Index);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The wall stands; " : (Core.Index >= Core.Supply() ? "The supply ran out; " : "The stone fit nowhere; ");
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R draws a new supply; " + Tally};
        }
        return {Core.Score, 1, false, false, Tally};
    }
};

}} // daedalus::desktop
