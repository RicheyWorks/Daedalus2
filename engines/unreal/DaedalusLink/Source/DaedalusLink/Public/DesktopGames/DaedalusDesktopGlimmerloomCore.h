// SPDX-License-Identifier: MIT
// Glimmerloom Ledger (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusGlimmerloomCore.h, a port of
// tools/minigames/glimmerloom.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("glimmerloom", seed) opens the same market as glimmerloom.start(seed, difficulty).
//
//   Left/Right or stick   pick a hue
//   pad A / J             buy one shard of it
//   pad B / K             sell one shard of it
//   pad Y / Shift         buy as many as purse and satchel allow
//   pad X / Space         rest: close the day, prices drift, a new rumor arrives
//   R / pad Start         restart a finished ledger
//   option 0 Ledger; option 1 Guide practice marks what demo_action would do
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusGlimmerloomCore.h"
#include <algorithm>
#include <numeric>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class GlimmerloomGame final : public Game {
    glimmerloom::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    std::string LastResult;   // the rules' result text for the last action; empty until the first
    EdgeLatch PrevEdge, NextEdge;

    static constexpr int MaxPurse = 100000;
    static constexpr int MaxDrawn = 200000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Cursor = 0;
        LastResult.clear();
        PrevEdge.Clear();
        NextEdge.Clear();
    }
    static bool GoPrev(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoNext(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    int HueCount() const { return static_cast<int>(Core.Prices.size()); }
    void Move(int Direction) {
        const int N = HueCount();
        if(N <= 0) return;
        Cursor = ((Cursor + Direction) % N + N) % N;
    }
    bool Act(const glimmerloom::Action& Action) {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(Action, Result) != glimmerloom::Game::Act::Ok) return false;
        LastResult = Result;
        return true;
    }
    /** How many of the cursor hue the purse and satchel allow right now. */
    int Affordable() const {
        if(Core.Over || HueCount() <= 0) return 0;
        const int Price = Core.Prices[static_cast<size_t>(Cursor)];
        const int Room = Core.Diff->Satchel - Core.Held();
        return std::max(0, std::min(Price > 0 ? Core.Purse / Price : 0, Room));
    }
    static Color HueColor(int Hue) {
        switch(Hue) {
            case 0:  return {255, 132, 64, 255};
            case 1:  return {72, 160, 255, 255};
            case 2:  return {96, 214, 112, 255};
            case 3:  return {228, 228, 160, 255};
            case 4:  return {170, 110, 230, 255};
            default: return {60, 56, 70, 255};
        }
    }

public:
    const glimmerloom::Game& CoreState() const { return Core; }
    int CursorHue() const { return Cursor; }
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

    bool BuyOne() { return Act({glimmerloom::Kind::Buy, Cursor, 1}); }
    bool SellOne() { return Act({glimmerloom::Kind::Sell, Cursor, 1}); }
    bool BuyMax() {
        const int Count = Affordable();
        return Count > 0 && Act({glimmerloom::Kind::Buy, Cursor, Count});
    }
    bool Rest() { return Act({glimmerloom::Kind::Rest, 0, 0}); }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        switch(Key) {
            case SourceKey::Left:  Move(-1); break;
            case SourceKey::Right: Move(1); break;
            case SourceKey::A:
            case SourceKey::Enter: BuyOne(); break;
            case SourceKey::B:     SellOne(); break;
            case SourceKey::Space: Rest(); break;
            default: break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            BuyOne();
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
        if(I.FirePressed) BuyOne();
        else if(I.JumpPressed) SellOne();
        else if(I.DashPressed) BuyMax();
        else if(I.ActionPressed) Rest();
    }

    std::string SaveState() const override {
        return SaveWriter(glimmerloom::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Core.Rng.Drawn()))
            .Field("day", Core.Day)
            .Field("purse", Core.Purse)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .List("prices", Core.Prices)
            .List("satchel", Core.Satchel)
            .List("moves", Core.Moves)
            .Field("rumor", std::to_string(Core.RumorHue) + (Core.RumorRise ? ":rise" : ":fall"))
            .Text();
    }
    // Prices, satchel, tomorrow's moves and the rumor are range-checked against the difficulty; the PRNG is re-seeded
    // and fast-forwarded so the following days' tides match an unbroken session.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, glimmerloom::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const glimmerloom::Difficulty* Diff = glimmerloom::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0;
        int Day = 0, Purse = 0, Score = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        std::vector<int> Prices, Satchel, Moves;
        const long long MinDrawn = static_cast<long long>(Diff->Hues) * 2 + 3;   // first prices, first moves, rumor hue, truth roll
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", MinDrawn, static_cast<long long>(MaxDrawn), Drawn)) return false;
        if(!Fields.Int("day", 1, Diff->Days + 1, Day)) return false;
        if(!Fields.Int("purse", 0, MaxPurse, Purse) || !Fields.Int("score", 0, MaxPurse, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.Int("cursor", 0, Diff->Hues - 1, SavedCursor)) return false;
        if(!Fields.IntList("prices", glimmerloom::Low, glimmerloom::High, Prices) || static_cast<int>(Prices.size()) != Diff->Hues) return false;
        if(!Fields.IntList("satchel", 0, Diff->Satchel, Satchel) || static_cast<int>(Satchel.size()) != Diff->Hues) return false;
        if(std::accumulate(Satchel.begin(), Satchel.end(), 0) > Diff->Satchel) return false;
        if(!Fields.IntList("moves", -3, 3, Moves) || static_cast<int>(Moves.size()) != Diff->Hues) return false;

        const std::vector<std::string> Rumor = SplitText(Fields.Str("rumor"), ':');
        long long RumorHue = 0;
        if(Rumor.size() != 2 || !ParseInteger(Rumor[0], RumorHue) || RumorHue < 0 || RumorHue >= Diff->Hues) return false;
        if(Rumor[1] != "rise" && Rumor[1] != "fall") return false;
        if(Over != (Day > Diff->Days)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core.Diff = Diff;
        Core.Day = Day;
        Core.Purse = Purse;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        Core.Prices = Prices;
        Core.Satchel = Satchel;
        Core.Moves = Moves;
        Core.RumorHue = static_cast<int>(RumorHue);
        Core.RumorRise = Rumor[1] == "rise";
        Core.Rng.Seed(std::string(glimmerloom::GameId()) + ":" + std::to_string(SessionSeed) + ":" + DifficultyName);
        Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        ResetTable();
        Cursor = SavedCursor;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The ledger balances. Pad A or R opens a new market."
                            : "HINT The market closed short. Pad A or R opens a new market.";
        }
        if(Option == 1) {
            const glimmerloom::Action Demo = Core.DemoAction();
            if(Demo.K == glimmerloom::Kind::Buy) return "HINT Practice: the trader would buy " + std::to_string(Demo.Count) + " " + glimmerloom::HueName(Demo.Hue) + ".";
            if(Demo.K == glimmerloom::Kind::Sell) return "HINT Practice: the trader would sell " + std::to_string(Demo.Count) + " " + glimmerloom::HueName(Demo.Hue) + ".";
            return "HINT Practice: the trader would rest.";
        }
        return std::string("HINT Rumor: ") + glimmerloom::HueName(Core.RumorHue) + (Core.RumorRise ? " rises" : " falls") + " tomorrow. Rumors are usually true.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(Core.Day >= Core.Diff->Days) return "CUE Last day: rest to close";
        return Core.Held() > 0 ? "CUE Trade or rest" : "CUE Buy or rest";
    }
    std::string HowToLine() const override {
        return "HOW Buy and sell hued shards as market prices drift, heed the Warden's rumor, then rest; end the last day with a purse at or above the target.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a hue; A buys, B sells, Y buys all, X rests."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Parchment{240, 230, 200, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Dim{150, 140, 120, 255};
        const int Days = Core.Diff ? Core.Diff->Days : 0;
        const int Target = Core.Diff ? Core.Diff->Target : 0;
        const int SatchelMax = Core.Diff ? Core.Diff->Satchel : 0;

        F.Clear(800, 600, {20, 16, 12, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "GLIMMERLOOM GUIDE  [" : "GLIMMERLOOM LEDGER  [") + CabinetDifficulty() + "]", Parchment, 26);
        F.AddText(28, 56, "DAY " + std::to_string(std::min(Core.Day, Days)) + "/" + std::to_string(Days) + "   PURSE: " + std::to_string(Core.Purse) + "/" + std::to_string(Target)
                          + "   SATCHEL: " + std::to_string(Core.Held()) + "/" + std::to_string(SatchelMax), White, 18);
        const int N = HueCount();
        if(N <= 0) return;

        const glimmerloom::Action Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : glimmerloom::Action{glimmerloom::Kind::Rest, -1, 0};

        // Market stalls: one column per hue with price bar, price, held count; cursor bar beneath, guide bar below that
        const double StallLeft = 60, StallTop = 110, StallWidth = 110, Gap = 130, BarMax = 200;
        for(int I = 0; I < N; ++I) {
            const double X = StallLeft + I * Gap;
            const int Price = Core.Prices[static_cast<size_t>(I)];
            const double BarHeight = BarMax * (Price - glimmerloom::Low) / static_cast<double>(glimmerloom::High - glimmerloom::Low);
            F.AddRect(X, StallTop, StallWidth, BarMax + 60, {36, 30, 24, 255});
            F.AddRect(X + 10, StallTop + 10 + (BarMax - BarHeight), StallWidth - 20, BarHeight, HueColor(I));
            F.AddText(X + 10, StallTop + BarMax + 16, glimmerloom::HueName(I), Parchment, 14);
            F.AddText(X + 10, StallTop + BarMax + 36, std::to_string(Price) + " ea   x" + std::to_string(Core.Satchel[static_cast<size_t>(I)]), White, 14);
            if(I == Core.RumorHue && !Core.Over) F.AddText(X + 10, StallTop - 20, Core.RumorRise ? "rumor: rises" : "rumor: falls", Gold, 12);
            if(I == Cursor && !Core.Over) F.AddRect(X, StallTop + BarMax + 64, StallWidth, 5, Gold);
            if(Guide.Hue == I && Guide.K != glimmerloom::Kind::Rest) F.AddRect(X, StallTop + BarMax + 72, StallWidth, 4, Sky);
        }
        if(Option == 1 && !Core.Over && Guide.K == glimmerloom::Kind::Rest) F.AddRect(StallLeft, StallTop + BarMax + 72, Gap * N - (Gap - StallWidth), 4, Sky);
        if(!LastResult.empty() && !Core.Over) F.AddText(60, 420, "LAST: " + LastResult, Gold, 16);
        if(Core.Over) F.AddText(60, 450, Core.Won ? "WON: THE LEDGER BALANCES" : "LOST: THE MARKET CLOSED SHORT", Gold, 22);
        else F.AddText(60, 450, "Target " + std::to_string(Target) + " by the close of day " + std::to_string(Days), Dim, 14);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(600, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The ledger balances; " : "The market closed short; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R opens a new market; purse " + std::to_string(Core.Purse)};
        }
        return {Core.Score, 1, false, false, "Day " + std::to_string(Core.Day) + "; purse " + std::to_string(Core.Purse) + "; held " + std::to_string(Core.Held())};
    }
};

}} // daedalus::desktop
