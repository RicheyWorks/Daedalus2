// SPDX-License-Identifier: MIT
// Prismcairn Duel (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusPrismcairnCore.h, a port of
// tools/minigames/prismcairn.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("prismcairn", seed) is the same duel as prismcairn.start(seed, difficulty).
//
//   Left/Right or stick   pick a cairn
//   pad A / J   take 1     pad B / K   take 2     pad X / Space   take 3     pad Y / Shift   take 4
//   (each take is capped at the difficulty's limit and the cairn's height)
//   R / pad Start         restart a finished duel
//   option 0 Duel; option 1 Guide practice marks the cairn and count best_move would take
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusPrismcairnCore.h"
#include <algorithm>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class PrismcairnGame final : public Game {
    prismcairn::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    int LastWardenCairn = -1, LastWardenTake = -1;   // the Warden's reply to the player's last take
    prismcairn::Game::Outcome LastOutcome = prismcairn::Game::Outcome::WardenTakes;
    EdgeLatch PrevEdge, NextEdge;

    static constexpr int MaxScore = 1000;
    static constexpr int MaxDrawn = 200000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Cursor = 0;
        LastWardenCairn = -1;
        LastWardenTake = -1;
        PrevEdge.Clear();
        NextEdge.Clear();
    }
    static bool GoPrev(const Input& I) { return I.Left || I.Up || I.PadLeft || I.PadUp || I.AxisX < -0.4 || I.AxisY < -0.4; }
    static bool GoNext(const Input& I) { return I.Right || I.Down || I.PadRight || I.PadDown || I.AxisX > 0.4 || I.AxisY > 0.4; }
    void Move(int Direction) {
        const int N = static_cast<int>(Core.Cairns.size());
        if(N <= 0) return;
        Cursor = ((Cursor + Direction) % N + N) % N;
    }
    int CursorHeight() const { return Core.Cairns.empty() ? 0 : Core.Cairns[static_cast<size_t>(Cursor)]; }

public:
    const prismcairn::Game& CoreState() const { return Core; }
    int CursorCairn() const { return Cursor; }
    int LastWardenCairnIndex() const { return LastWardenCairn; }
    int LastWardenTakeCount() const { return LastWardenTake; }

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

    /** Takes up to `Count` shards from the cursor cairn, capped at the limit and the cairn. False when nothing moved. */
    bool Take(int Count) {
        if(Core.Over || Core.Cairns.empty()) return false;
        const int Height = CursorHeight();
        if(Height <= 0) return false;
        const int Taken = std::min(Count, std::min(Core.Diff->TakeMax, Height));
        if(Taken < 1) return false;
        if(Core.Take(Cursor, Taken, LastOutcome, LastWardenCairn, LastWardenTake) != prismcairn::Game::Act::Ok) return false;
        if(!Core.Over && CursorHeight() == 0) Move(1);   // step off an emptied cairn
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Up:
            case SourceKey::Left:  Move(-1); break;
            case SourceKey::Down:
            case SourceKey::Right: Move(1); break;
            case SourceKey::A:
            case SourceKey::Enter: Take(1); break;
            case SourceKey::B:     Take(2); break;
            case SourceKey::Space: Take(3); break;
            default: break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Take(1);
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
        const bool Prev = PrevEdge.Rose(GoPrev(I));
        const bool Next = NextEdge.Rose(GoNext(I));
        if(Prev) Move(-1);
        else if(Next) Move(1);
        if(I.FirePressed) Take(1);
        else if(I.JumpPressed) Take(2);
        else if(I.ActionPressed) Take(3);
        else if(I.DashPressed) Take(4);
    }

    std::string SaveState() const override {
        return SaveWriter(prismcairn::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Core.Rng.Drawn()))
            .Field("round", Core.Round)
            .Field("wins", Core.Wins)
            .Field("losses", Core.Losses)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .Field("cairns", Core.CairnsString())
            .Text();
    }
    // The cairn heights are range-checked against the difficulty and the PRNG is re-seeded and fast-forwarded, so
    // the Warden's later slips and the next round's deal match an unbroken session.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, prismcairn::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const prismcairn::Difficulty* Diff = prismcairn::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0;
        int Round = 0, Wins = 0, Losses = 0, Score = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        std::vector<int> Cairns;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", 1LL, static_cast<long long>(MaxDrawn), Drawn)) return false;
        if(!Fields.Int("round", 1, Diff->Rounds, Round)) return false;
        if(!Fields.Int("wins", 0, Diff->Rounds, Wins) || !Fields.Int("losses", 0, Diff->Rounds, Losses)) return false;
        if(Wins + Losses >= Round) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.Int("cursor", 0, Diff->Cairns - 1, SavedCursor)) return false;
        if(!Fields.IntList("cairns", 0, Diff->MaxHeight, Cairns)) return false;
        if(static_cast<int>(Cairns.size()) != Diff->Cairns) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core.Diff = Diff;
        Core.Round = Round;
        Core.Wins = Wins;
        Core.Losses = Losses;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        Core.Cairns = Cairns;
        Core.Log.clear();
        Core.Rng.Seed(std::string(prismcairn::GameId()) + ":" + std::to_string(SessionSeed) + ":" + DifficultyName);
        Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        ResetTable();
        Cursor = SavedCursor;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The Warden yields. Pad A or R raises new cairns."
                            : "HINT The Warden keeps the cairns. Pad A or R raises new ones.";
        }
        if(Option == 1) return "HINT Practice: the blue mark shows the winning take.";
        return "HINT Lift the last shard. Leave the Warden a balanced field.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(LastWardenTake > 0) return "CUE Warden took " + std::to_string(LastWardenTake);
        return "CUE Take shards";
    }
    std::string HowToLine() const override {
        return "HOW Take one or more shards, up to the limit, from one cairn each turn; lift the last shard to win the round, best of three.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a cairn; A/B/X/Y take 1/2/3/4."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Lilac{236, 226, 255, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Ember{255, 150, 120, 255}, Stone{150, 130, 190, 255};
        const int Rounds = Core.Diff ? Core.Diff->Rounds : 0;
        const int TakeMax = Core.Diff ? Core.Diff->TakeMax : 0;

        F.Clear(800, 600, {18, 16, 22, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "PRISMCAIRN GUIDE  [" : "PRISMCAIRN DUEL  [") + CabinetDifficulty() + "]", Lilac, 26);
        F.AddText(28, 56, "ROUND " + std::to_string(Core.Round) + "/" + std::to_string(Rounds) + "   WINS: " + std::to_string(Core.Wins) + "   LOSSES: " + std::to_string(Core.Losses)
                          + "   SCORE: " + std::to_string(Core.Score) + "   TAKE 1-" + std::to_string(TakeMax), White, 18);
        const int N = static_cast<int>(Core.Cairns.size());
        if(N <= 0) return;

        // Cairns: stacked slabs on a floor line, cursor bar beneath, guide mark and the Warden's last take as labels
        const std::pair<int, int> Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : std::pair<int, int>{-1, 0};
        const double Floor = 430, GridLeft = 120, Gap = 560.0 / N;
        for(int I = 0; I < N; ++I) {
            const double X = GridLeft + I * Gap;
            const int Height = Core.Cairns[static_cast<size_t>(I)];
            for(int Slab = 0; Slab < Height; ++Slab) {
                const double Jitter = Slab % 2 ? 3 : 0;
                F.AddRect(X - 22 + Jitter, Floor - (Slab + 1) * 22, 44, 18, Stone);
            }
            if(I == Cursor && !Core.Over) F.AddRect(X - 28, Floor + 6, 56, 5, Gold);
            if(Guide.first == I) {
                F.AddRect(X - 28, Floor + 14, 56, 4, Sky);
                F.AddText(X - 10, Floor + 20, "-" + std::to_string(Guide.second), Sky, 14);
            }
            if(I == LastWardenCairn && !Core.Over) F.AddText(X - 30, Floor - Height * 22 - 30, "-" + std::to_string(LastWardenTake), Ember, 16);
            F.AddText(X - 6, Floor + 36, std::to_string(Height), White, 14);
        }
        if(Core.Over) F.AddText(240, 470, Core.Won ? "WON: THE WARDEN YIELDS" : "LOST: THE WARDEN KEEPS THE CAIRNS", Gold, 22);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(600, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Record = std::to_string(Core.Wins) + "-" + std::to_string(Core.Losses);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The Warden yields; " : "The Warden keeps the cairns; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R raises new cairns; rounds " + Record};
        }
        return {Core.Score, 1, false, false, "Round " + std::to_string(Core.Round) + "; rounds " + Record};
    }
};

}} // daedalus::desktop
