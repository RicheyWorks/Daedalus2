// SPDX-License-Identifier: MIT
// Shardscale (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusShardscaleCore.h, a port of
// tools/minigames/shardscale.py (the rules authority). CPython-compatible seeding, so StartGame("shardscale", seed)
// rolls the same line of shards as shardscale.start(seed, difficulty).
//
//   Up / Down / d-pad / stick    pick the shard in hand: the next on the cart, or a bench shard
//   Left / Right                 set the shard in hand on the left or right pan (one turn)
//   pad A / J / Space            hold the next shard on the bench (one turn)
//   R / pad Start                restart a finished weighing
//   option 0 Shardscale; option 1 Guide practice marks the pan (or the bench) the weigher's exact line takes next
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusShardscaleCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class ShardscaleGame final : public Game {
    shardscale::Game Core;
    int Hand = shardscale::Action::Next;   // Next = the cart's next shard, else a bench index
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;   // the rules' result text for the last turn; empty until the first
    EdgeLatch UpEdge, DownEdge, LeftEdge, RightEdge, HoldEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Hand = shardscale::Action::Next;
        LastResult.clear();
        UpEdge.Clear();
        DownEdge.Clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        HoldEdge.Clear();
    }
    static bool GoU(const Input& I) { return I.Up || I.PadUp || I.AxisY < -0.4; }
    static bool GoD(const Input& I) { return I.Down || I.PadDown || I.AxisY > 0.4; }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool HoldPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }

    /** The cart's next shard is in hand only while the cart still has one. */
    bool CartHasNext() const { return Core.Diff && Core.Index < Core.Diff->Shards; }
    /** Keeps the hand on something that exists: the cart's next shard, else the last bench shard. */
    void SettleHand() {
        if(Hand == shardscale::Action::Next && !CartHasNext()) Hand = Core.Held.N > 0 ? Core.Held.N - 1 : shardscale::Action::Next;
        if(Hand != shardscale::Action::Next && Hand >= Core.Held.N) Hand = CartHasNext() ? shardscale::Action::Next : std::max(0, Core.Held.N - 1);
    }

public:
    const shardscale::Game& CoreState() const { return Core; }
    int HandSource() const { return Hand; }
    const std::string& LastResultText() const { return LastResult; }
    /** The weight of the shard in hand, 0 with nothing left. */
    int HandWeight() const {
        if(Hand == shardscale::Action::Next) return CartHasNext() ? Core.Line[static_cast<size_t>(Core.Index)] : 0;
        return Hand < Core.Held.N ? Core.Held.W[static_cast<size_t>(Hand)] : 0;
    }

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

    /** Moves the hand: Up toward the cart's next shard, Down along the bench. False at the ends or once over. */
    bool Nudge(int Delta) {
        if(Core.Over) return false;
        // Order: Next (if the cart has one), then bench 0..N-1
        const int Slots = (CartHasNext() ? 1 : 0) + Core.Held.N;
        if(Slots <= 1) return false;
        const int Position = Hand == shardscale::Action::Next ? 0 : Hand + (CartHasNext() ? 1 : 0);
        const int Target = Position + Delta;
        if(Target < 0 || Target >= Slots) return false;
        Hand = (CartHasNext() && Target == 0) ? shardscale::Action::Next : Target - (CartHasNext() ? 1 : 0);
        return true;
    }
    /** One turn: the shard in hand onto a pan, or the next shard onto the bench. False when the rules refuse it. */
    bool Take(shardscale::Kind K) {
        if(Core.Over) return false;
        const shardscale::Action A{K, K == shardscale::Kind::Hold ? shardscale::Action::Next : Hand};
        std::string Result;
        if(Core.Step(A, Result) != shardscale::Game::Act::Ok) return false;
        LastResult = Result;
        SettleHand();
        return true;
    }
    bool SetLeft() { return Take(shardscale::Kind::Left); }
    bool SetRight() { return Take(shardscale::Kind::Right); }
    bool Hold() { return Take(shardscale::Kind::Hold); }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:    Nudge(-1); break;
            case SourceKey::Down:  Nudge(1); break;
            case SourceKey::Left:  SetLeft(); break;
            case SourceKey::Right: SetRight(); break;
            default:
                if(SourceKey::IsConfirm(Key)) Hold();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Hold();
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
            if(HoldPressed(I)) Deal();
            return;
        }
        const bool U = UpEdge.Rose(GoU(I));
        const bool D = DownEdge.Rose(GoD(I));
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool H = HoldEdge.Rose(HoldPressed(I));
        if(U) Nudge(-1);
        else if(D) Nudge(1);
        else if(L) SetLeft();
        else if(R) SetRight();
        else if(H) Hold();
    }

    std::string SaveState() const override {
        return SaveWriter(shardscale::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("index", Core.Index)
            .Field("left", Core.Left)
            .Field("right", Core.Right)
            .Field("held", Core.HeldString())
            .Field("used", Core.BenchUsed)
            .Field("hand", Hand)
            .Field("score", Core.Score)
            .Flag("tipped", Core.Tipped)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The line comes from the seed; the pans, the
    // bench and the index must account for exactly the shards taken off the cart, the bench must be sorted and within
    // its slots, the beam within the cap unless tipped, and the flags must follow the rules.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, shardscale::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const shardscale::Difficulty* Diff = shardscale::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Index = 0, Left = 0, Right = 0, Used = 0, HandSlot = 0, Score = 0;
        bool Tipped = false, Over = false, Won = false;
        std::vector<int> Held;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("index", 0, Diff->Shards, Index)) return false;
        if(!Fields.Int("left", 0, MaxScore, Left) || !Fields.Int("right", 0, MaxScore, Right)) return false;
        if(!Fields.IntList("held", shardscale::MinWeight, shardscale::MaxWeight, Held) || static_cast<int>(Held.size()) > Diff->Bench) return false;
        for(size_t I = 1; I < Held.size(); ++I) if(Held[I - 1] > Held[I]) return false;
        if(!Fields.Int("used", 0, Diff->Shards, Used) || Used < static_cast<int>(Held.size()) || Used > Index) return false;
        if(!Fields.Int("hand", -1, Diff->Bench - 1, HandSlot)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("tipped", Tipped) || !Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;

        shardscale::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        int Taken = 0;
        for(int I = 0; I < Index; ++I) Taken += Fresh.Line[static_cast<size_t>(I)];
        int Benched = 0;
        for(int W : Held) Benched += W;
        if(Left + Right + Benched != Taken) return false;
        const int Difference = Left - Right;
        const bool Done = Index == Diff->Shards && Held.empty();
        if(std::abs(Difference) > Diff->Cap && !Tipped) return false;
        if(Tipped && std::abs(Difference) <= Diff->Cap) return false;
        if(Over != (Tipped || Done)) return false;
        if(Won != (Over && !Tipped && std::abs(Difference) <= Diff->Tolerance)) return false;
        if(!Over) {
            const bool CartLeft = Index < Diff->Shards;
            if(HandSlot == -1 ? !CartLeft : HandSlot >= static_cast<int>(Held.size())) return false;
        }

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        Core.Index = Index;
        Core.Left = Left;
        Core.Right = Right;
        Core.Held = shardscale::Bench{};
        for(int W : Held) Core.Held.Add(W);
        Core.BenchUsed = Used;
        Core.Score = Score;
        Core.Tipped = Tipped;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Hand = HandSlot;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            if(Core.Won) return "HINT The beam rests level. Pad A or R rolls a new line.";
            return Core.Tipped ? "HINT The beam tipped. Pad A or R rolls a new line." : "HINT The beam settled askew. Pad A or R rolls a new line.";
        }
        if(Option == 1) {
            const shardscale::Action D = Core.DemoAction();
            const std::string Where = D.K == shardscale::Kind::Hold ? "the bench" : D.K == shardscale::Kind::Left ? "the left pan" : "the right pan";
            const std::string Which = D.Source == shardscale::Action::Next ? "the next shard" : "bench shard " + std::to_string(D.Source + 1);
            return "HINT Practice: the weigher's line puts " + Which + " on " + Where + " (blue mark).";
        }
        const int Weight = HandWeight(), Diff = Core.Difference();
        const bool LeftTips = std::abs(Diff + Weight) > Core.Diff->Cap, RightTips = std::abs(Diff - Weight) > Core.Diff->Cap;
        if(Weight > 0 && LeftTips && RightTips) return "HINT A " + std::to_string(Weight) + " tips the beam either way; bench it (A) and set it later.";
        if(Weight > 0 && (LeftTips || RightTips)) return std::string("HINT A ") + std::to_string(Weight) + " only fits the " + (LeftTips ? "right" : "left") + " pan now.";
        return "HINT Up/Down pick the shard in hand; Left/Right set it; A benches the next shard for later.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Remaining() <= 2 ? "CUE Last shards" : "CUE Set a shard";
    }
    std::string HowToLine() const override {
        return "HOW Set the next shard left or right, or hold it on the bench; set a held shard later. Never let the pans differ by more than the cap; end level within the tolerance.";
    }
    std::string KeyHint() const override { return "KEYS Up/Down pick the shard; Left/Right set it; A benches it."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Shard{180, 150, 255, 255}, Beam{150, 130, 110, 255}, Pan{90, 80, 70, 255}, BenchTint{70, 80, 95, 255};
        const int Cap = Core.Diff ? Core.Diff->Cap : 0;

        F.Clear(800, 600, {18, 16, 26, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SHARDSCALE GUIDE  [" : "SHARDSCALE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "LEFT " + std::to_string(Core.Left) + "   RIGHT " + std::to_string(Core.Right) + "   DIFF " + std::to_string(Core.Difference()) + "   CAP " + std::to_string(Cap) + "   TOL " + std::to_string(Core.Diff ? Core.Diff->Tolerance : 0) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(!Core.Diff) return;

        // The beam: a bar whose tilt follows the difference (clamped to the cap), pans at each end
        const double CX = 400, CY = 230, Half = 220;
        const double Tilt = Cap > 0 ? std::max(-1.0, std::min(1.0, static_cast<double>(Core.Difference()) / Cap)) : 0.0;
        const double Drop = 40 * Tilt;
        F.AddRect(CX - 6, CY - 10, 12, 120, Beam);
        for(int Seg = -10; Seg <= 10; ++Seg) {
            const double X = CX + Seg * Half / 10, Y = CY + Drop * Seg / 10;
            F.AddRect(X - 11, Y - 3, 22, 6, Beam);
        }
        F.AddRect(CX - Half - 40, CY + Drop + 20, 80, 10, Pan);
        F.AddRect(CX + Half - 40, CY - Drop + 20, 80, 10, Pan);
        F.AddText(CX - Half - 20, CY + Drop + 36, std::to_string(Core.Left), Gold, 16);
        F.AddText(CX + Half - 20, CY - Drop + 36, std::to_string(Core.Right), Gold, 16);
        if(!Core.Over) {
            F.AddText(CX - Half - 30, CY + Drop - 40, "<- LEFT", Mist, 12);
            F.AddText(CX + Half - 40, CY - Drop - 40, "RIGHT ->", Mist, 12);
        }

        // The cart: the next five shards, the one in hand framed in gold; the bench below it
        const bool HasGuide = Option == 1 && !Core.Over;
        const shardscale::Action Guide = HasGuide ? Core.DemoAction() : shardscale::Action{shardscale::Kind::Hold, -2};
        F.AddText(60, 360, "CART", Mist, 14);
        for(int I = 0; I < 5 && Core.Index + I < Core.Diff->Shards; ++I) {
            const double X = 60 + I * 46, Y = 380;
            F.AddRect(X, Y, 38, 38, Shard);
            F.AddText(X + 12, Y + 10, std::to_string(Core.Line[static_cast<size_t>(Core.Index + I)]), White, 16);
            if(I == 0 && !Core.Over && Hand == shardscale::Action::Next) {
                F.AddRect(X - 3, Y - 3, 44, 3, Gold);
                F.AddRect(X - 3, Y + 38, 44, 3, Gold);
                F.AddRect(X - 3, Y - 3, 3, 44, Gold);
                F.AddRect(X + 38, Y - 3, 3, 44, Gold);
            }
            if(I == 0 && HasGuide && Guide.Source == shardscale::Action::Next) F.AddRect(X + 8, Y + 42, 22, 4, Sky);
        }
        F.AddText(60, 436, "BENCH " + std::to_string(Core.Held.N) + "/" + std::to_string(Core.Diff->Bench) + "  (A benches the next shard)", Mist, 12);
        for(int H = 0; H < Core.Diff->Bench; ++H) {
            const double X = 60 + H * 46, Y = 456;
            F.AddRect(X, Y, 38, 30, BenchTint);
            if(H < Core.Held.N) {
                F.AddText(X + 12, Y + 6, std::to_string(Core.Held.W[static_cast<size_t>(H)]), White, 16);
                if(!Core.Over && Hand == H) {
                    F.AddRect(X - 3, Y - 3, 44, 3, Gold);
                    F.AddRect(X - 3, Y + 30, 44, 3, Gold);
                    F.AddRect(X - 3, Y - 3, 3, 36, Gold);
                    F.AddRect(X + 38, Y - 3, 3, 36, Gold);
                }
                if(HasGuide && Guide.Source == H) F.AddRect(X + 8, Y + 34, 22, 4, Sky);
            }
        }
        if(HasGuide) F.AddText(600, 240, std::string("GUIDE: ") + (Guide.K == shardscale::Kind::Hold ? "bench it" : Guide.K == shardscale::Kind::Left ? "left pan" : "right pan"), Sky, 13);

        if(Core.FreshLine()) {
            F.AddText(600, 360, "SET   Left/Right set the shard in hand on a pan", Mist, 11);
            F.AddText(600, 378, "CAP   pans more than " + std::to_string(Cap) + " apart tip the beam", Mist, 11);
            F.AddText(600, 396, "LEVEL place every shard; end within " + std::to_string(Core.Diff->Tolerance), Mist, 11);
        }
        F.AddText(600, 110, "LEFT TO PLACE " + std::to_string(Core.Remaining()), Mist, 14);
        F.AddText(600, 132, "HAND " + (HandWeight() > 0 ? std::to_string(HandWeight()) : std::string("-")), Mist, 14);
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: THE BEAM RESTS LEVEL" : (Core.Tipped ? "LOST: THE BEAM TIPS" : "LOST: THE BEAM SETTLES ASKEW"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "pans " + std::to_string(Core.Left) + "/" + std::to_string(Core.Right) + ", left to place " + std::to_string(Core.Remaining());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The beam rests level; " : (Core.Tipped ? "The beam tipped; " : "The beam settled askew; ");
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R rolls a new line; " + Tally};
        }
        return {Core.Score, 1, false, false, Tally};
    }
};

}} // daedalus::desktop
