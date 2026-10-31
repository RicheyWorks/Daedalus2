// SPDX-License-Identifier: MIT
// Glowmoss Delve (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusGlowmossCore.h, a port of
// tools/minigames/glowmoss.py (prism-shard-dev's rules, the authority). CPython-compatible seeding, so
// StartGame("glowmoss", seed) digs the same shaft as glowmoss.start(seed, difficulty).
//
//   Left / Right / d-pad / stick   pick the ledge to dig onto (one column left or right of where you stand)
//   pad A / J / Space              dig down onto the picked ledge
//   pad B / K                      climb out now
//   R / pad Start                  restart a finished delve
//   option 0 Glowmoss Delve; option 1 Guide practice marks the ledge the best delve from here would take
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusGlowmossCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class GlowmossGame final : public Game {
    glowmoss::Game Core;
    int Pick = 0;             // the column the next dig lands on
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    bool Climbed = false;     // the delve ended by climbing (true) or by the lamp guttering (false)
    std::string LastResult;   // the rules' result text for the last action; empty until the first
    EdgeLatch LeftEdge, RightEdge, DigEdge, ClimbEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Pick = Core.Col;
        Climbed = false;
        LastResult.clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        DigEdge.Clear();
        ClimbEdge.Clear();
    }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool DigPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed; }
    static bool ClimbPressed(const Input& I) { return I.DashPressed; }

    /** Replays `Path` (digs) and the optional climb on a fresh shaft; false if any step is refused. */
    static bool Replay(glowmoss::Game& G, const std::vector<int>& Path, bool Climb) {
        std::string Text;
        for(int C : Path) {
            if(G.Step({glowmoss::Kind::Dig, C}, Text) != glowmoss::Game::Act::Ok) return false;
        }
        if(Climb && G.Step({glowmoss::Kind::Climb, 0}, Text) != glowmoss::Game::Act::Ok) return false;
        return true;
    }

public:
    const glowmoss::Game& CoreState() const { return Core; }
    int PickedColumn() const { return Pick; }
    const std::string& LastResultText() const { return LastResult; }
    bool CanDig() const { return !Core.Over && Core.Row + 1 < Core.Diff->Rows; }

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

    /** Moves the pick one column within reach; false at the edge of reach or once the delve is over. */
    bool Nudge(int DC) {
        if(Core.Over) return false;
        const int Next = Pick + DC;
        if(Next < glowmoss::FirstDigCol(Core.Col) || Next > glowmoss::LastDigCol(Core.Col, Core.Diff->Cols)) return false;
        Pick = Next;
        return true;
    }
    /** Digs onto the picked ledge. False at the shaft floor or once the delve is over. */
    bool Dig() {
        if(!CanDig()) return false;
        std::string Result;
        if(Core.Step({glowmoss::Kind::Dig, Pick}, Result) != glowmoss::Game::Act::Ok) return false;
        LastResult = Result;
        Pick = std::min(std::max(Pick, glowmoss::FirstDigCol(Core.Col)), glowmoss::LastDigCol(Core.Col, Core.Diff->Cols));
        return true;
    }
    /** Climbs out, ending the delve. False once it is over. */
    bool Climb() {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step({glowmoss::Kind::Climb, 0}, Result) != glowmoss::Game::Act::Ok) return false;
        LastResult = Result;
        Climbed = true;
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
            case SourceKey::B:     Climb(); break;
            default:
                if(SourceKey::IsConfirm(Key)) Dig();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Dig();
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
            if(DigPressed(I) || ClimbPressed(I)) Deal();
            return;
        }
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool D = DigEdge.Rose(DigPressed(I));
        const bool C = ClimbEdge.Rose(ClimbPressed(I));
        if(L) Nudge(-1);
        else if(R) Nudge(1);
        else if(D) Dig();
        else if(C) Climb();
    }

    std::string SaveState() const override {
        return SaveWriter(glowmoss::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .List("path", Core.Path)
            .Flag("climbed", Climbed)
            .Field("pick", Pick)
            .Field("light", Core.Light)
            .Field("crystals", Core.Crystals)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The delve is rebuilt by replaying the saved
    // path (and the climb) on the seeded shaft; the saved light, crystals, score and flags must match the replay,
    // so a save cannot claim more than the shaft gives.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, glowmoss::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const glowmoss::Difficulty* Diff = glowmoss::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int PickCol = 0, Light = 0, Crystals = 0, Score = 0;
        bool WasClimbed = false, Over = false, Won = false;
        std::vector<int> Path;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.IntList("path", 0, Diff->Cols - 1, Path) || static_cast<int>(Path.size()) > Diff->Rows) return false;
        if(!Fields.Flag("climbed", WasClimbed)) return false;
        if(!Fields.Int("pick", 0, Diff->Cols - 1, PickCol)) return false;
        if(!Fields.Int("light", -Diff->Rows, Diff->Light, Light)) return false;
        if(!Fields.Int("crystals", 0, MaxScore, Crystals)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;

        glowmoss::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        if(!Replay(Fresh, Path, WasClimbed)) return false;
        if(Fresh.Light != Light || Fresh.Crystals != Crystals || Fresh.Score != Score || Fresh.Over != Over || Fresh.Won != Won) return false;
        if(!Over && (PickCol < glowmoss::FirstDigCol(Fresh.Col) || PickCol > glowmoss::LastDigCol(Fresh.Col, Diff->Cols))) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        ResetTable();
        Climbed = WasClimbed;
        Pick = PickCol;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            if(Core.Won) return Core.Perfect ? "HINT A perfect delve. Pad A or R opens a new shaft." : "HINT You climbed out with the crystals. Pad A or R opens a new shaft.";
            return Climbed ? "HINT Climbed out short of the target. Pad A or R opens a new shaft." : "HINT The lamp guttered out. Pad A or R opens a new shaft.";
        }
        if(Option == 1) {
            const glowmoss::Action H = Core.Hint();
            return H.K == glowmoss::Kind::Climb ? "HINT Practice: the best delve from here is to climb out now (B)."
                                                 : "HINT Practice: the blue ledge is where the best delve from here digs next.";
        }
        const int Cost = glowmoss::ClimbCost(Core.Row);
        if(Core.Crystals >= Core.Target) return "HINT You have the target. Climb out (B) for " + std::to_string(Cost) + " light, or dig for more if the lamp allows.";
        if(Core.Light - Cost <= 2) return "HINT The lamp is low: climbing out costs " + std::to_string(Cost) + ". Only dig onto glowmoss now.";
        return "HINT Each dig burns 1 plus the ledge's darkness; glowmoss refills the lamp; an unstable ledge drops you a row.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(!CanDig()) return "CUE Climb out";
        return Core.Light - glowmoss::ClimbCost(Core.Row) <= 2 ? "CUE Lamp low" : "CUE Dig or climb";
    }
    std::string HowToLine() const override {
        return "HOW Dig down the shaft one ledge at a time to gather crystals; glowmoss refills your lamp and unstable ledges drop you one row. Climb out before the light is too low to carry you back up.";
    }
    std::string KeyHint() const override { return "KEYS Left/Right pick the ledge; A digs; B climbs out."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Lamp{255, 200, 90, 255};
        const Color Ledge{86, 78, 70, 255}, DarkLedge{52, 46, 42, 255}, Dug{120, 108, 96, 255}, MossTint{110, 220, 140, 255}, Crack{200, 90, 70, 255}, Crystal{180, 150, 255, 255};
        const int Rows = Core.Diff ? Core.Diff->Rows : 0, Cols = Core.Diff ? Core.Diff->Cols : 0;

        F.Clear(800, 600, {12, 14, 22, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "GLOWMOSS DELVE GUIDE  [" : "GLOWMOSS DELVE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "LIGHT " + std::to_string(Core.Light) + "/" + std::to_string(Core.Diff ? Core.Diff->Light : 0) + "   CRYSTALS " + std::to_string(Core.Crystals) + "/" + std::to_string(Core.Target)
                  + "   CLIMB " + std::to_string(glowmoss::ClimbCost(Core.Row)) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(Rows <= 0 || Cols <= 0) return;

        // The lamp gauge
        {
            const int Capacity = Core.Diff->Light;
            const double Width = 540.0 * std::max(0, Core.Light) / Capacity;
            F.AddRect(28, 84, 540, 10, {40, 40, 50, 255});
            F.AddRect(28, 84, Width, 10, Lamp);
        }

        // The shaft: one row per ledge row, columns across; dug ledges lighter; darkness as a darker plate; glowmoss a
        // green dot, unstable a red notch, crystals as a count; the pick a gold frame; the guide ledge blue; you a disc
        const double Cell = std::min(380.0 / Rows, 480.0 / Cols), GridLeft = 60, GridTop = 110;
        const bool HasGuide = Option == 1 && !Core.Over;
        const glowmoss::Action Guide = HasGuide ? Core.Hint() : glowmoss::Action{glowmoss::Kind::Climb, 0};
        const bool Reachable = CanDig();
        for(int R = 0; R < Rows; ++R) {
            for(int C = 0; C < Cols; ++C) {
                const double X = GridLeft + C * Cell, Y = GridTop + R * Cell;
                const size_t SR = static_cast<size_t>(R), SC = static_cast<size_t>(C);
                const bool WasDug = R <= Core.Row && Core.Path.size() > SR && Core.Path[SR] == C;
                const Color Tint = WasDug ? Dug : Core.Cells.Dark[SR][SC] == 2 ? DarkLedge : Ledge;
                F.AddRect(X + 1, Y + 1, Cell - 2, Cell - 2, Tint);
                F.AddText(X + Cell * 0.12, Y + Cell * 0.2, std::to_string(Core.Cells.Gems[SR][SC]), Crystal, 12);
                if(Core.Cells.Moss[SR][SC]) F.AddCircle(X + Cell * 0.75, Y + Cell * 0.3, Cell * 0.1, MossTint);
                if(Core.Cells.Unstable[SR][SC]) F.AddRect(X + Cell * 0.2, Y + Cell - 5, Cell * 0.6, 3, Crack);
                if(HasGuide && Guide.K == glowmoss::Kind::Dig && R == Core.Row + 1 && C == Guide.Col) F.AddRect(X + Cell * 0.35, Y + Cell * 0.62, Cell * 0.3, Cell * 0.2, Sky);
                if(Reachable && R == Core.Row + 1 && C == Pick) {
                    F.AddRect(X, Y, Cell, 3, Gold);
                    F.AddRect(X, Y + Cell - 3, Cell, 3, Gold);
                    F.AddRect(X, Y, 3, Cell, Gold);
                    F.AddRect(X + Cell - 3, Y, 3, Cell, Gold);
                }
            }
        }
        {
            const double YouY = Core.Row < 0 ? GridTop - Cell * 0.5 : GridTop + Core.Row * Cell + Cell / 2;
            F.AddCircle(GridLeft + Core.Col * Cell + Cell / 2, YouY, Cell * 0.22, Gold);
        }

        if(Core.Row == glowmoss::Surface && !Core.Over) {
            F.AddText(600, 360, "DIG   Left/Right pick a ledge within one column; A digs", Mist, 11);
            F.AddText(600, 378, "LAMP  a dig burns 1 + darkness; green glowmoss refills", Mist, 11);
            F.AddText(600, 396, "OUT   B climbs out for (row + 2) / 2 light; reach the target", Mist, 11);
        }
        F.AddText(600, 110, "KEY", Mist, 14);
        F.AddCircle(609, 139, 6, MossTint);
        F.AddText(624, 132, "glowmoss refill", Mist, 11);
        F.AddRect(600, 158, 18, 3, Crack);
        F.AddText(624, 152, "unstable ledge", Mist, 11);
        F.AddRect(600, 178, 18, 18, DarkLedge);
        F.AddText(624, 180, "deep darkness", Mist, 11);
        F.AddText(600, 210, "TARGET " + std::to_string(Core.Target) + "  BEST " + std::to_string(Core.Best), Mist, 12);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? (Core.Perfect ? "WON: A PERFECT DELVE" : "WON: INTO THE LIGHT") : (Climbed ? "LOST: SHORT OF THE TARGET" : "LOST: THE LAMP GUTTERS OUT"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "crystals " + std::to_string(Core.Crystals) + "/" + std::to_string(Core.Target) + ", light " + std::to_string(Core.Light);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? (Core.Perfect ? "A perfect delve; " : "Out into the light; ") : (Climbed ? "Short of the target; " : "The lamp guttered out; ");
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R opens a new shaft; " + Tally};
        }
        return {Core.Score, 1, false, false, "Row " + std::to_string(Core.Row) + "; " + Tally};
    }
};

}} // daedalus::desktop
