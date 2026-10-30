// SPDX-License-Identifier: MIT
// Lumenpath Refraction (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusLumenpathCore.h, a port of
// tools/minigames/lumenpath.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("lumenpath", seed) is the same lattice as lumenpath.start(seed, difficulty). Cabinet difficulty is the
// game difficulty (easy 5x5 / normal 6x6 / hard 7x7).
//
//   Arrows or stick       move the cursor
//   pad A / J / Space     toggle the mirror under it: empty -> / -> \ -> empty
//   R / pad Start         restart a finished lattice
//   option 0 Refraction; option 1 Guide practice frames the next solution mirror
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusLumenpathCore.h"
#include <set>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class LumenpathGame final : public Game {
    lumenpath::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int CursorR = 0, CursorC = 0;
    int LastGained = 0;
    EdgeLatch LeftEdge, RightEdge, UpEdge, DownEdge, ConfirmEdge;

    static constexpr int MaxMoves = 1000;
    static constexpr int MaxScore = 1000000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        CursorR = Core.SourceRow;   // the cursor starts where the beam enters
        CursorC = 0;
        LastGained = 0;
        LeftEdge.Clear();
        RightEdge.Clear();
        UpEdge.Clear();
        DownEdge.Clear();
        ConfirmEdge.Clear();
    }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }
    void Move(int DR, int DC) {
        const int N = Core.Size();
        if(N <= 0) return;
        CursorR = ((CursorR + DR) % N + N) % N;
        CursorC = ((CursorC + DC) % N + N) % N;
    }
    /** A saved grid must keep every crystal and stone where the seed put them; only mirror cells may differ. */
    static bool SameFixedCells(const std::vector<std::string>& Saved, const std::vector<std::string>& Generated, int Size) {
        if(static_cast<int>(Saved.size()) != Size) return false;
        for(int R = 0; R < Size; ++R) {
            const std::string& Row = Saved[static_cast<size_t>(R)];
            if(static_cast<int>(Row.size()) != Size) return false;
            for(int C = 0; C < Size; ++C) {
                const char Have = Row[static_cast<size_t>(C)];
                const char Want = Generated[static_cast<size_t>(R)][static_cast<size_t>(C)];
                const bool Fixed = Want == '*' || Want == '#';
                if(Fixed && Have != Want) return false;
                if(!Fixed && Have != '.' && Have != '/' && Have != '\\') return false;
            }
        }
        return true;
    }
    /** The first solution mirror not yet in place, or (-1,-1) when the lattice already matches. */
    lumenpath::Cell NextSolutionMirror() const {
        for(const lumenpath::Mirror& M : Core.Solution) {
            if(Core.Grid[static_cast<size_t>(M.R)][static_cast<size_t>(M.C)] != M.M) return {M.R, M.C};
        }
        return {-1, -1};
    }

public:
    const lumenpath::Game& CoreState() const { return Core; }
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

    bool Toggle() {
        if(Core.Over) return false;
        int Gained = 0;
        if(Core.Toggle(CursorR, CursorC, Gained) != lumenpath::Game::Act::Ok) return false;
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
            case SourceKey::Up:    Move(-1, 0); break;
            case SourceKey::Down:  Move(1, 0); break;
            case SourceKey::Left:  Move(0, -1); break;
            case SourceKey::Right: Move(0, 1); break;
            default:
                if(SourceKey::IsConfirm(Key)) Toggle();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Toggle();
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
            if(Confirm(I)) Deal();
            return;
        }
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        if(L) Move(0, -1);
        else if(R) Move(0, 1);
        else if(U) Move(-1, 0);
        else if(D) Move(1, 0);
        if(ConfirmEdge.Rose(Confirm(I))) Toggle();
    }

    std::string SaveState() const override {
        return SaveWriter(lumenpath::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("moves", Core.Moves)
            .Field("score", Core.Score)
            .Field("lit", Core.Lit)
            .Field("best", Core.Best)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cur", std::to_string(CursorR) + "," + std::to_string(CursorC))
            .Field("grid", Core.GridString())
            .Text();
    }
    // The lattice (crystals, stones, solution) is regenerated from the seed; only the saved mirrors are overlaid, and
    // the lit count must agree with a fresh trace.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, lumenpath::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const lumenpath::Difficulty* Diff = lumenpath::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Moves = 0, Score = 0, Lit = 0, Best = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("moves", 0, MaxMoves, Moves)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Int("lit", 0, Diff->Crystals, Lit) || !Fields.Int("best", 0, Diff->Crystals, Best)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;

        const std::vector<std::string> CursorParts = SplitText(Fields.Str("cur"), ',');
        long long SavedR = 0, SavedC = 0;
        if(CursorParts.size() != 2 || !ParseInteger(CursorParts[0], SavedR) || !ParseInteger(CursorParts[1], SavedC)) return false;
        if(SavedR < 0 || SavedR >= Diff->Size || SavedC < 0 || SavedC >= Diff->Size) return false;

        lumenpath::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        const std::vector<std::string> Rows = SplitText(Fields.Str("grid"), '|');
        if(!SameFixedCells(Rows, Fresh.Grid, Diff->Size)) return false;
        Fresh.Grid = Rows;
        if(Fresh.CountLit() != Lit || Lit > Best || Best > static_cast<int>(Fresh.Crystals.size())) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Moves = Moves;
        Core.Score = Score;
        Core.Lit = Lit;
        Core.Best = Best;
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
            return Core.Won ? "HINT Every crystal glows. Pad A or R lays a new lattice."
                            : "HINT The light faded. Pad A or R lays a new lattice.";
        }
        if(Option == 1) return "HINT Practice: the blue frame marks the next solution mirror.";
        return "HINT Mirrors cycle / then \\ then empty. Bend the beam through every crystal.";
    }
    std::string ActionCue() const { return Core.Over ? "CUE Retry" : "CUE Toggle mirror"; }
    std::string HowToLine() const override {
        return "HOW Toggle shard mirrors to bend the prism beam through every crystal before your moves run out.";
    }
    std::string KeyHint() const override { return "KEYS Arrows move the cursor; A toggles the mirror."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Ice{222, 236, 255, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Beam{255, 236, 140, 255}, Glass{200, 230, 255, 255};

        F.Clear(800, 600, {12, 14, 28, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "LUMENPATH GUIDE  [" : "LUMENPATH REFRACTION  [") + CabinetDifficulty() + "]", Ice, 26);
        F.AddText(28, 56, "SCORE: " + std::to_string(Core.Score) + "   LIT: " + std::to_string(Core.Lit) + "/" + std::to_string(Core.Crystals.size()) + "   MOVES: " + std::to_string(Core.Moves), White, 18);
        const int N = Core.Size();
        if(N <= 0) return;

        const double Cell = 360.0 / N, GridLeft = 180, GridTop = 110;
        const std::vector<lumenpath::Cell> Path = lumenpath::Trace(Core.Grid, Core.SourceRow);
        const std::set<lumenpath::Cell> OnPath(Path.begin(), Path.end());
        const lumenpath::Cell Guide = (Option == 1 && !Core.Over) ? NextSolutionMirror() : lumenpath::Cell{-1, -1};

        // Lattice frame and the beam's entry arrow
        F.AddRect(GridLeft - 8, GridTop - 8, N * Cell + 16, N * Cell + 16, {26, 30, 54, 255});
        const double SourceY = GridTop + Core.SourceRow * Cell;
        F.AddTriangle({GridLeft - 30, SourceY + Cell * 0.3}, {GridLeft - 30, SourceY + Cell * 0.7}, {GridLeft - 10, SourceY + Cell * 0.5}, Beam);

        // Cells: lit background, then stone / crystal / mirror, then guide frame and cursor bar
        for(int R = 0; R < N; ++R) {
            for(int C = 0; C < N; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const char Ch = Core.Grid[static_cast<size_t>(R)][static_cast<size_t>(C)];
                const bool Lit = OnPath.count({R, C}) != 0;
                F.AddRect(X + 2, Y + 2, Cell - 4, Cell - 4, Lit ? Color{70, 66, 40, 255} : Color{18, 20, 40, 255});
                if(Ch == '#') F.AddRect(X + 6, Y + 6, Cell - 12, Cell - 12, {90, 80, 84, 255});
                else if(Ch == '*') F.AddCircle(X + Cell / 2, Y + Cell / 2, Cell * 0.28, Lit ? Color{255, 230, 120, 255} : Color{110, 120, 170, 255});
                else if(Ch == '/') F.AddLine(X + Cell * 0.2, Y + Cell * 0.8, X + Cell * 0.8, Y + Cell * 0.2, Glass, 3);
                else if(Ch == '\\') F.AddLine(X + Cell * 0.2, Y + Cell * 0.2, X + Cell * 0.8, Y + Cell * 0.8, Glass, 3);
                if(Guide.first == R && Guide.second == C) F.AddRect(X + 4, Y + 4, Cell - 8, Cell - 8, Sky);
                if(R == CursorR && C == CursorC && !Core.Over) F.AddRect(X, Y, Cell, 4, Gold);
            }
        }
        // The beam itself, cell centre to cell centre
        for(size_t I = 1; I < Path.size(); ++I) {
            const double X0 = GridLeft + Path[I - 1].second * Cell + Cell / 2, Y0 = GridTop + Path[I - 1].first * Cell + Cell / 2;
            const double X1 = GridLeft + Path[I].second * Cell + Cell / 2, Y1 = GridTop + Path[I].first * Cell + Cell / 2;
            F.AddLine(X0, Y0, X1, Y1, Beam, 2);
        }
        if(LastGained > 0 && !Core.Over) F.AddText(600, 120, "+" + std::to_string(LastGained), Gold, 24);
        if(Core.Over) F.AddText(560, 160, Core.Won ? "WON: EVERY CRYSTAL GLOWS" : "LOST: THE LIGHT FADES", Gold, 18);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string LitText = std::to_string(Core.Lit) + "/" + std::to_string(Core.Crystals.size());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Every crystal glows; " : "The light faded; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R lays a new lattice; lit " + LitText};
        }
        return {Core.Score, 1, false, false, "Lit " + LitText + "; moves " + std::to_string(Core.Moves)};
    }
};

}} // daedalus::desktop
