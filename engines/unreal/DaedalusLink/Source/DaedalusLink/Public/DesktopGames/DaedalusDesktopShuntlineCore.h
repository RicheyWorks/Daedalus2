// SPDX-License-Identifier: MIT
// Shuntline (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusShuntlineCore.h, a port of
// tools/minigames/shuntline.py (the rules authority). CPython-compatible seeding, so StartGame("shuntline", seed)
// makes up the same train as shuntline.start(seed, difficulty).
//
//   Up / Down / d-pad / stick    pick a siding
//   Right                        send the front carriage out to the outbound track (one move)
//   pad A / J / Space            shunt the front carriage onto the picked siding (one move)
//   pad B / K                    pull the picked siding's top carriage out (one move)
//   R / pad Start                restart a finished shift
//   option 0 Shuntline; option 1 Guide practice marks the move the yardmaster's exact line takes next
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusShuntlineCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class ShuntlineGame final : public Game {
    shuntline::Game Core;
    int Pick = 0;             // the picked siding
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last move; empty until the first
    std::string History;      // the moves of this shift as text ("out,s0,p1"), kept for the save
    EdgeLatch UpEdge, DownEdge, OutEdge, ShuntEdge, PullEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Pick = 0;
        LastResult.clear();
        History.clear();
        UpEdge.Clear();
        DownEdge.Clear();
        OutEdge.Clear();
        ShuntEdge.Clear();
        PullEdge.Clear();
    }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool GoOut(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool ShuntPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed; }
    static bool PullPressed(const Input& I) { return I.DashPressed; }

    /** Replays a move list on a fresh yard; false when any move is refused. */
    static bool Replay(shuntline::Game& G, const std::vector<shuntline::Action>& Moves) {
        std::string Text;
        for(const shuntline::Action& A : Moves) if(G.Step(A, Text) != shuntline::Game::Act::Ok) return false;
        return true;
    }

public:
    const shuntline::Game& CoreState() const { return Core; }
    int PickedSiding() const { return Pick; }
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

    /** Moves the pick along the sidings; false at either end or once the shift is over. */
    bool Nudge(int Delta) {
        if(Core.Over) return false;
        const int Next = Pick + Delta;
        if(Next < 0 || Next >= Core.Diff->Sidings) return false;
        Pick = Next;
        return true;
    }
    /** One move. False when the rules refuse it or the shift is over. */
    bool Take(const shuntline::Action& A) {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(A, Result) != shuntline::Game::Act::Ok) return false;
        LastResult = Result;
        if(!History.empty()) History.push_back(',');
        History += shuntline::ActionText(A);
        return true;
    }
    bool SendOut() { return Take(shuntline::OutAction); }
    bool Shunt() { return Take({shuntline::Kind::Shunt, Pick}); }
    bool Pull() { return Take({shuntline::Kind::Pull, Pick}); }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:    Nudge(-1); break;
            case SourceKey::Down:  Nudge(1); break;
            case SourceKey::Right: SendOut(); break;
            case SourceKey::B:     Pull(); break;
            default:
                if(SourceKey::IsConfirm(Key)) Shunt();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Shunt();
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
            if(ShuntPressed(I) || PullPressed(I)) Deal();
            return;
        }
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        const bool O = OutEdge.Rose(GoOut(I));
        const bool S = ShuntEdge.Rose(ShuntPressed(I));
        const bool P = PullEdge.Rose(PullPressed(I));
        if(U) Nudge(-1);
        else if(D) Nudge(1);
        else if(O) SendOut();
        else if(S) Shunt();
        else if(P) Pull();
    }

    /** The moves so far as text (replayed on restore): "out,s0,p1,...". */
    std::string MovesText() const { return History.empty() ? "-" : History; }

    std::string SaveState() const override {
        return SaveWriter(shuntline::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("moves", MovesText())
            .Field("pick", Pick)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The shift is rebuilt by replaying the saved
    // move list on the seeded train; the saved score and flags must match the replay, so a save cannot claim a
    // train it never made up.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, shuntline::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const shuntline::Difficulty* Diff = shuntline::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int PickIndex = 0, Score = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("pick", 0, Diff->Sidings - 1, PickIndex)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        std::vector<shuntline::Action> Moves;
        const std::string MoveText = Fields.Str("moves");
        if(MoveText != "-") {
            for(const std::string& Token : SplitText(MoveText, ',')) {
                shuntline::Action A;
                if(!shuntline::ActionFromText(Token, A) || (A.K != shuntline::Kind::Out && A.Siding >= Diff->Sidings)) return false;
                Moves.push_back(A);
            }
        }
        if(static_cast<int>(Moves.size()) > Diff->Moves) return false;

        shuntline::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        if(!Replay(Fresh, Moves)) return false;
        if(Fresh.Score != Score || Fresh.Over != Over || Fresh.Won != Won) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        ResetTable();
        History = MoveText == "-" ? "" : MoveText;
        Pick = PickIndex;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            if(Core.Won) return "HINT The train is made up. Pad A or R brings in a new train.";
            return Core.Moves() <= 0 ? "HINT The shift ended. Pad A or R brings in a new train." : "HINT The yard blocked. Pad A or R brings in a new train.";
        }
        if(Option == 1) {
            const shuntline::Action D = Core.DemoAction();
            const std::string What = D.K == shuntline::Kind::Out ? "sends the front carriage out (Right)" : D.K == shuntline::Kind::Shunt ? "shunts it onto siding " + std::to_string(D.Siding) + " (A)" : "pulls siding " + std::to_string(D.Siding) + " out (B)";
            return "HINT Practice: the yardmaster's line " + What + "; blue marks it.";
        }
        const int Front = Core.Front();
        if(Front > 0 && Front < Core.OutLast()) return "HINT A " + std::to_string(Front) + " cannot leave after a " + std::to_string(Core.OutLast()) + "; park it (A) and pull it later.";
        if(Core.Remaining() > Core.Moves()) return "HINT More carriages than moves left; every one must leave in one move now.";
        return "HINT Lower tags out first. Park higher tags on a siding, highest at the bottom, and pull them in order.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Moves() - Core.Remaining() <= 2 ? "CUE Moves are tight" : "CUE Shunt or send";
    }
    std::string HowToLine() const override {
        return "HOW Right sends the front carriage to the outbound track; A shunts it onto the picked siding; B pulls that siding's top carriage out. The outbound order may never go down. Clear the inbound track within the moves.";
    }
    std::string KeyHint() const override { return "KEYS Up/Down pick a siding; Right sends out; A shunts; B pulls."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Rail{90, 90, 100, 255}, CarTint{200, 140, 80, 255}, OutTint{110, 170, 140, 255};
        const int Sidings = Core.Diff ? Core.Diff->Sidings : 0;

        F.Clear(800, 600, {18, 20, 26, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SHUNTLINE GUIDE  [" : "SHUNTLINE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "MOVES " + std::to_string(Core.Moves()) + "   OUT " + std::to_string(Core.Outbound.size()) + "/" + std::to_string(Core.Cars()) + "   LAST " + std::to_string(Core.OutLast()) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(Sidings <= 0) return;

        const bool HasGuide = Option == 1 && !Core.Over;
        const shuntline::Action Guide = HasGuide ? Core.DemoAction() : shuntline::OutAction;
        const double Box = 34, Left = 60;
        // Inbound track: front carriage nearest the switch (right side)
        F.AddText(Left, 100, "INBOUND  (front at the switch ->)", Mist, 12);
        F.AddRect(Left, 150, 420, 4, Rail);
        const int Inbound = Core.Cars() - Core.Index();
        for(int I = 0; I < Inbound && I < 11; ++I) {
            const int Tag = Core.Train[static_cast<size_t>(Core.Index() + I)];
            const double X = Left + 420 - (I + 1) * (Box + 4);
            F.AddRect(X, 118, Box, 28, I == 0 ? Gold : CarTint);
            F.AddText(X + 12, 124, std::to_string(Tag), White, 13);
        }
        if(HasGuide && Guide.K == shuntline::Kind::Out) F.AddRect(Left + 420 - Box - 4, 156, Box, 4, Sky);
        // Sidings: stacks growing rightward from the stop block, picked one framed in gold
        for(int S = 0; S < Sidings; ++S) {
            const double Y = 200 + S * 70;
            const shuntline::Siding& Sd = Core.SidingAt(S);
            F.AddText(Left, Y - 18, "SIDING " + std::to_string(S), Mist, 12);
            F.AddRect(Left, Y + 32, 4 + Core.Diff->Length * (Box + 4), 4, Rail);
            for(int I = 0; I < Sd.N; ++I) {
                F.AddRect(Left + 4 + I * (Box + 4), Y, Box, 28, CarTint);
                F.AddText(Left + 16 + I * (Box + 4), Y + 6, std::to_string(Sd.Tag[static_cast<size_t>(I)]), White, 13);
            }
            if(!Core.Over && S == Pick) {
                const double W = 8 + Core.Diff->Length * (Box + 4);
                F.AddRect(Left - 4, Y - 4, W, 3, Gold);
                F.AddRect(Left - 4, Y + 37, W, 3, Gold);
                F.AddRect(Left - 4, Y - 4, 3, 44, Gold);
                F.AddRect(Left - 4 + W - 3, Y - 4, 3, 44, Gold);
            }
            if(HasGuide && Guide.K != shuntline::Kind::Out && Guide.Siding == S) F.AddRect(Left + 4 + Core.Diff->Length * (Box + 4) + 10, Y + 12, 22, 4, Sky);
        }
        // Outbound track
        const double OutY = 200 + Sidings * 70 + 20;
        F.AddText(Left, OutY - 18, "OUTBOUND  (must not go down)", Mist, 12);
        F.AddRect(Left, OutY + 32, 420, 4, Rail);
        for(size_t I = 0; I < Core.Outbound.size() && I < 11; ++I) {
            F.AddRect(Left + 4 + static_cast<double>(I) * (Box + 4), OutY, Box, 28, OutTint);
            F.AddText(Left + 16 + static_cast<double>(I) * (Box + 4), OutY + 6, std::to_string(Core.Outbound[I]), White, 13);
        }

        if(Core.FreshYard()) {
            F.AddText(600, 360, "OUT   Right sends the front carriage out", Mist, 11);
            F.AddText(600, 378, "SIDE  A parks it on the picked siding; B pulls back out", Mist, 11);
            F.AddText(600, 396, "ORDER outbound tags never go down; " + std::to_string(Core.Diff->Moves) + " moves", Mist, 11);
        }
        F.AddText(600, 110, "LEFT IN YARD " + std::to_string(Core.Remaining()), Mist, 14);
        F.AddText(600, 132, "FRONT " + (Core.Front() > 0 ? std::to_string(Core.Front()) : std::string("-")), Mist, 14);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: THE TRAIN IS MADE UP" : (Core.Moves() <= 0 ? "LOST: THE SHIFT ENDS" : "LOST: THE YARD IS BLOCKED"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "out " + std::to_string(Core.Outbound.size()) + "/" + std::to_string(Core.Cars()) + ", moves " + std::to_string(Core.Moves());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The train is made up; " : (Core.Moves() <= 0 ? "The shift ended; " : "The yard blocked; ");
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R brings in a new train; " + Tally};
        }
        return {Core.Score, 1, false, false, Tally};
    }
};

}} // daedalus::desktop
