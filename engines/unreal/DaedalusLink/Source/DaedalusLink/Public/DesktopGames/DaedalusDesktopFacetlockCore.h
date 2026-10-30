// SPDX-License-Identifier: MIT
// Facetlock Lattice (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusFacetlockCore.h, a port of
// tools/minigames/facetlock.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("facetlock", seed) is the same scramble as facetlock.start(seed, difficulty).
//
//   Arrows or stick   move the cursor
//   pad A / J   slide the cursor's row right     pad B / K       slide it left
//   pad X / Space   slide the cursor's column down   pad Y / Shift   slide it up
//   R / pad Start     restart a finished lock
//   option 0 Lattice; option 1 Guide practice marks the row or column the solution slides next
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusFacetlockCore.h"
#include <cstring>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class FacetlockGame final : public Game {
    facetlock::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int CursorR = 0, CursorC = 0;
    int LastGained = 0;
    EdgeLatch LeftEdge, RightEdge, UpEdge, DownEdge;

    static constexpr int MaxScore = 1000;
    static constexpr size_t MaxSolution = 64;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        CursorR = 0;
        CursorC = 0;
        LastGained = 0;
        LeftEdge.Clear();
        RightEdge.Clear();
        UpEdge.Clear();
        DownEdge.Clear();
    }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    void MoveCursor(int DR, int DC) {
        const int N = Core.Size();
        if(N <= 0) return;
        CursorR = ((CursorR + DR) % N + N) % N;
        CursorC = ((CursorC + DC) % N + N) % N;
    }
    static Color MarkColor(char Mark) {
        switch(Mark) {
            case 'E': return {255, 132, 64, 255};
            case 'T': return {72, 160, 255, 255};
            case 'V': return {96, 214, 112, 255};
            case 'G': return {228, 228, 160, 255};
            case 'U': return {170, 110, 230, 255};
            default:  return {60, 56, 70, 255};
        }
    }
    /** A saved board is a Size x Size grid over the first Size hues, with exactly one row's worth of each hue. */
    static bool ValidBoard(const std::vector<std::string>& Rows, int Size) {
        if(static_cast<int>(Rows.size()) != Size) return false;
        int Counts[5] = {0, 0, 0, 0, 0};
        for(const std::string& Row : Rows) {
            if(static_cast<int>(Row.size()) != Size) return false;
            for(char Ch : Row) {
                const char* Found = std::strchr(facetlock::Marks(), Ch);
                if(!Found || Found - facetlock::Marks() >= Size) return false;
                ++Counts[Found - facetlock::Marks()];
            }
        }
        for(int Hue = 0; Hue < Size; ++Hue) if(Counts[Hue] != Size) return false;
        return true;
    }
    /** Parses "r,3,1;c,0,-1;..." into moves; false on any malformed part. */
    static bool ParseSolution(const std::string& Text, int Size, std::vector<facetlock::Move>& Out) {
        Out.clear();
        if(Text.empty()) return true;
        for(const std::string& Part : SplitText(Text, ';')) {
            const std::vector<std::string> Fields = SplitText(Part, ',');
            long long Index = 0, Dir = 0;
            if(Fields.size() != 3 || (Fields[0] != "r" && Fields[0] != "c")) return false;
            if(!ParseInteger(Fields[1], Index) || Index < 0 || Index >= Size) return false;
            if(!ParseInteger(Fields[2], Dir) || (Dir != 1 && Dir != -1)) return false;
            Out.push_back({Fields[0] == "r", static_cast<int>(Index), static_cast<int>(Dir)});
        }
        return Out.size() <= MaxSolution;
    }

public:
    const facetlock::Game& CoreState() const { return Core; }
    int CursorRow() const { return CursorR; }
    int CursorCol() const { return CursorC; }
    int LastGain() const { return LastGained; }

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

    /** Slides the cursor's row (Row=true) or column by Dir. False when nothing happened. */
    bool Slide(bool Row, int Dir) {
        if(Core.Over) return false;
        int Gained = 0;
        if(Core.Apply({Row, Row ? CursorR : CursorC, Dir}, Gained) != facetlock::Game::Act::Ok) return false;
        LastGained = Gained;
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:    MoveCursor(-1, 0); break;
            case SourceKey::Down:  MoveCursor(1, 0); break;
            case SourceKey::Left:  MoveCursor(0, -1); break;
            case SourceKey::Right: MoveCursor(0, 1); break;
            case SourceKey::A:
            case SourceKey::Enter: Slide(true, 1); break;
            case SourceKey::B:     Slide(true, -1); break;
            case SourceKey::Space: Slide(false, 1); break;
            default: break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Slide(true, 1);
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
            if(I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed) Deal();
            return;
        }
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        if(L) MoveCursor(0, -1);
        else if(R) MoveCursor(0, 1);
        else if(U) MoveCursor(-1, 0);
        else if(D) MoveCursor(1, 0);
        if(I.FirePressed) Slide(true, 1);
        else if(I.JumpPressed) Slide(true, -1);
        else if(I.ActionPressed) Slide(false, 1);
        else if(I.DashPressed) Slide(false, -1);
    }

    std::string SaveState() const override {
        return SaveWriter(facetlock::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("moves", Core.Moves)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cur", std::to_string(CursorR) + "," + std::to_string(CursorC))
            .Field("board", Core.BoardString())
            .Field("solution", Core.SolutionString())
            .Text();
    }
    // The board is validated as a true permutation of the hue rows and the solution is parsed move by move; the core is
    // regenerated from the seed first so the restored game shares its difficulty table and scramble metadata.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, facetlock::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const facetlock::Difficulty* Diff = facetlock::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Moves = 0, Score = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("moves", 0, Diff->Scramble + Diff->Spare, Moves)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;

        const std::vector<std::string> CursorParts = SplitText(Fields.Str("cur"), ',');
        long long SavedR = 0, SavedC = 0;
        if(CursorParts.size() != 2 || !ParseInteger(CursorParts[0], SavedR) || !ParseInteger(CursorParts[1], SavedC)) return false;
        if(SavedR < 0 || SavedR >= Diff->Size || SavedC < 0 || SavedC >= Diff->Size) return false;

        facetlock::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        const std::vector<std::string> Rows = SplitText(Fields.Str("board"), '|');
        if(!ValidBoard(Rows, Diff->Size)) return false;
        std::vector<facetlock::Move> Solution;
        if(!ParseSolution(Fields.Str("solution"), Diff->Size, Solution)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Board = Rows;
        Core.Solution = Solution;
        Core.Moves = Moves;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        CursorR = static_cast<int>(SavedR);
        CursorC = static_cast<int>(SavedC);
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The vault lock opened. Pad A or R scrambles a new lattice."
                            : "HINT The lock sealed. Pad A or R scrambles a new lattice.";
        }
        if(Option == 1) return "HINT Practice: the blue bar marks the next slide of the solution.";
        return "HINT Rows and columns wrap. Make every row one hue.";
    }
    std::string ActionCue() const { return Core.Over ? "CUE Retry" : "CUE Slide"; }
    std::string HowToLine() const override {
        return "HOW Slide lattice rows and columns, which wrap, until each row shows a single hue inside the move budget.";
    }
    std::string KeyHint() const override { return "KEYS Arrows move the cursor; A/B slide the row, X/Y the column."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Cream{255, 236, 220, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255};

        F.Clear(800, 600, {16, 10, 24, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "FACETLOCK GUIDE  [" : "FACETLOCK LATTICE  [") + CabinetDifficulty() + "]", Cream, 26);
        F.AddText(28, 56, "SCORE: " + std::to_string(Core.Score) + "   MOVES: " + std::to_string(Core.Moves), White, 18);
        const int N = Core.Size();
        if(N <= 0) return;

        // Lattice: coloured facets with the cursor as a bar across the top of its cell
        const double Cell = 340.0 / N, GridLeft = 200, GridTop = 120;
        F.AddRect(GridLeft - 10, GridTop - 10, N * Cell + 20, N * Cell + 20, {34, 24, 46, 255});
        for(int R = 0; R < N; ++R) {
            for(int C = 0; C < N; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                F.AddRect(X + 3, Y + 3, Cell - 6, Cell - 6, MarkColor(Core.Board[static_cast<size_t>(R)][static_cast<size_t>(C)]));
                if(R == CursorR && C == CursorC && !Core.Over) F.AddRect(X, Y, Cell, 5, Gold);
            }
        }
        // Guide: a blue bar along the row or column the solution slides next
        const facetlock::Move Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : facetlock::Move{true, -1, 0};
        if(Guide.Index >= 0) {
            if(Guide.Row) F.AddRect(GridLeft - 10, GridTop + Guide.Index * Cell + Cell - 4, N * Cell + 20, 4, Sky);
            else F.AddRect(GridLeft + Guide.Index * Cell + Cell - 4, GridTop - 10, 4, N * Cell + 20, Sky);
        }

        // Target swatches: one row per hue in the order the lock wants them
        F.AddText(580, 120, "TARGET", Cream, 16);
        for(int R = 0; R < N; ++R) F.AddRect(580, 150 + R * 22, 120, 16, MarkColor(facetlock::Marks()[R]));
        if(LastGained > 0 && !Core.Over) F.AddText(580, 320, "+" + std::to_string(LastGained), Gold, 24);
        if(Core.Over) F.AddText(560, 360, Core.Won ? "WON: THE VAULT LOCK OPENS" : "LOST: THE LOCK SEALS", Gold, 18);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The vault lock opened; " : "The lock sealed; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R scrambles a new lattice; moves left " + std::to_string(Core.Moves)};
        }
        return {Core.Score, 1, false, false, "Moves " + std::to_string(Core.Moves) + "; solution " + std::to_string(Core.Solution.size()) + " slides"};
    }
};

}} // daedalus::desktop
