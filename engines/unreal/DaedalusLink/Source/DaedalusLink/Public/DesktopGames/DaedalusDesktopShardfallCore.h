// SPDX-License-Identifier: MIT
// Shardfall Gamble (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusShardfallCore.h, a port of
// tools/minigames/shardfall.py (prism-shard-dev, the rules authority). CPython-compatible seeding and shuffle, so
// StartGame("shardfall", seed) deals the same seam as shardfall.start(seed, difficulty).
//
//   pad A / J / Space   draw a shard
//   pad B / X / K / Shift   bank the pot
//   R / pad Start       restart a finished seam
//   option 0 Gamble; option 1 Guide practice shows whether demo_action would draw or bank
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusShardfallCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class ShardfallGame final : public Game {
    shardfall::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    std::string LastResult;     // "+3", "cracked", "collapse", "banked 7"; empty until the first action
    EdgeLatch DrawEdge, BankEdge;

    static constexpr int MaxPot = 35;        // every value shard in one seam
    static constexpr int MaxScore = 400;     // generous ceiling for a tampered save
    static constexpr int MaxDrawn = 200000;  // PRNG words a legitimate session can consume

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        LastResult.clear();
        DrawEdge.Clear();
        BankEdge.Clear();
    }
    static bool BankPressed(const Input& I) { return I.JumpPressed || I.ActionPressed || I.DashPressed; }

public:
    const shardfall::Game& CoreState() const { return Core; }
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

    bool DrawShard() {
        shardfall::Game::Draw Outcome = shardfall::Game::Draw::Value;
        int Value = 0;
        if(Core.DrawShard(Outcome, Value) != shardfall::Game::Act::Ok) return false;
        switch(Outcome) {
            case shardfall::Game::Draw::Collapse: LastResult = "collapse"; break;
            case shardfall::Game::Draw::Cracked:  LastResult = "cracked"; break;
            default:                              LastResult = "+" + std::to_string(Value); break;
        }
        return true;
    }
    bool BankPot() {
        int Banked = 0;
        if(Core.Bank(Banked) != shardfall::Game::Act::Ok) return false;
        LastResult = "banked " + std::to_string(Banked);
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        if(SourceKey::IsConfirm(Key)) DrawShard();
        else if(Key == SourceKey::B) BankPot();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            DrawShard();
            return true;
        }
        if(Button == PadButton::Start && Core.Over) {
            Deal();
            return true;
        }
        return false;
    }
    void Step(const Input& I) override {
        const bool Draw = DrawEdge.Rose(I.FirePressed);
        const bool Bank = BankEdge.Rose(BankPressed(I));
        if(Core.Over) {
            if(Draw || Bank) Deal();
        } else if(Draw) {
            DrawShard();
        } else if(Bank) {
            BankPot();
        }
    }

    std::string SaveState() const override {
        return SaveWriter(shardfall::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Core.Rng.Drawn()))
            .Field("round", Core.Round)
            .Field("pot", Core.Pot)
            .Field("cracks", Core.Cracks)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .List("bag", Core.Bag)
            .List("history", Core.History)
            .Text();
    }
    // The seam bag is not trusted blindly: it must be a subset of the difficulty's shard pool, the history length
    // must match the round, and the PRNG is re-seeded and fast-forwarded so later seams reshuffle identically.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, shardfall::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const shardfall::Difficulty* Diff = shardfall::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0;
        int Round = 0, Pot = 0, Cracks = 0, Score = 0;
        bool Over = false, Won = false;
        std::vector<int> Bag, History;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", 1LL, static_cast<long long>(MaxDrawn), Drawn)) return false;
        if(!Fields.Int("round", 1, Diff->Rounds, Round)) return false;
        if(!Fields.Int("pot", 0, MaxPot, Pot)) return false;
        if(!Fields.Int("cracks", 0, shardfall::BustAt - 1, Cracks)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.IntList("bag", 0, 5, Bag) || !Fields.IntList("history", 0, MaxPot, History)) return false;

        const int RoundsBanked = Over ? Round : Round - 1;
        if(static_cast<int>(History.size()) != RoundsBanked) return false;
        int CrackedInBag = 0;
        for(int Value : Bag) if(Value == 0) ++CrackedInBag;
        if(CrackedInBag + Cracks > Diff->Cracked) return false;
        if(static_cast<int>(Bag.size()) > shardfall::ValueCount + Diff->Cracked) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core.Diff = Diff;
        Core.Round = Round;
        Core.Pot = Pot;
        Core.Cracks = Cracks;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        Core.Bag = Bag;
        Core.History = History;
        Core.Rng.Seed(std::string(shardfall::GameId()) + ":" + std::to_string(SessionSeed) + ":" + DifficultyName);
        Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        LastResult.clear();
        DrawEdge.Clear();
        BankEdge.Clear();
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The seam's light is yours. Pad A or R opens a new seam."
                            : "HINT The seam closed. Pad A or R opens a new seam.";
        }
        if(Option == 1) return std::string("HINT Practice: the Wardens would ") + (Core.DemoBank() ? "BANK now." : "DRAW again.");
        if(Core.Cracks > 0) return "HINT One crack already. The next cracked shard collapses the seam.";
        return "HINT Draw to grow the pot; bank before the second crack.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(Core.Bag.empty()) return "CUE Bank";
        return Core.Cracks > 0 ? "CUE Draw or bank" : "CUE Draw";
    }
    std::string HowToLine() const override {
        return "HOW Draw shards to grow the pot or bank it; a second cracked shard collapses the seam and loses the pot; reach the target by the last round.";
    }
    std::string KeyHint() const override { return "KEYS A draws a shard; B or X banks the pot."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Cream{255, 232, 210, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Ember{255, 150, 120, 255};
        const int Rounds = Core.Diff ? Core.Diff->Rounds : 0;
        const int Target = Core.Diff ? Core.Diff->Target : 0;

        F.Clear(800, 600, {22, 14, 14, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SHARDFALL GUIDE  [" : "SHARDFALL GAMBLE  [") + CabinetDifficulty() + "]", Cream, 26);
        F.AddText(28, 56, "ROUND " + std::to_string(Core.Round) + "/" + std::to_string(Rounds) + "   SCORE: " + std::to_string(Core.Score) + "/" + std::to_string(Target), White, 18);

        // Pot panel
        F.AddRect(60, 120, 300, 180, {44, 28, 28, 255});
        F.AddText(80, 132, "POT", Cream, 16);
        F.AddText(80, 160, std::to_string(Core.Pot), Gold, 54);
        F.AddText(80, 240, "CRACKS " + std::to_string(Core.Cracks) + "/" + std::to_string(shardfall::BustAt), Core.Cracks ? Ember : White, 16);

        // Seam panel: one tile per shard still in the bag
        F.AddRect(400, 120, 340, 180, {36, 26, 36, 255});
        F.AddText(420, 132, "SEAM: " + std::to_string(Core.Bag.size()) + " shards, " + std::to_string(Core.CrackedLeft()) + " cracked", Cream, 16);
        for(size_t I = 0; I < Core.Bag.size(); ++I) {
            const double X = 420 + static_cast<double>(I % 8) * 38;
            const double Y = 160 + static_cast<double>(I / 8) * 38;
            F.AddRect(X, Y, 30, 30, {90, 72, 90, 255});
        }
        if(!LastResult.empty() && !Core.Over) F.AddText(420, 250, "LAST: " + LastResult, Gold, 20);
        if(Option == 1 && !Core.Over) F.AddRect(400, 304, 340, 6, Core.DemoBank() ? Sky : Gold);

        F.AddText(60, 330, "BANKED: " + Core.HistoryString(), White, 16);
        if(Core.Over) F.AddText(60, 380, Core.Won ? "WON: THE SEAM'S LIGHT IS YOURS" : "LOST: THE SEAM CLOSES", Gold, 22);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The seam's light is yours; " : "The seam closed; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R opens a new seam; rounds " + std::to_string(Core.Round)};
        }
        return {Core.Score, 1, false, false, "Round " + std::to_string(Core.Round) + "; pot " + std::to_string(Core.Pot) + "; cracks " + std::to_string(Core.Cracks)};
    }
};

}} // daedalus::desktop
