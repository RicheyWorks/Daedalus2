// SPDX-License-Identifier: MIT
// Wardens' Accord (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusWardensAccordCore.h, a port of
// tools/minigames/wardens_accord.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("wardens_accord", seed) is the same altar as wardens_accord.start(seed, difficulty).
//
// One cursor runs over the three altar shards (slots 0..2) and then the spirits (slots 3..).
//   Left/Up           previous slot        Right/Down   next slot
//   pad A / J / Space take the shard or summon the spirit under the cursor
//   R / pad Start     restart a finished altar
//   option 0 Accord; option 1 Guide practice marks what demo_action would do
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusWardensAccordCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class WardensAccordGame final : public Game {
    static constexpr int AltarSlots = 3;   // slots 0..2 are the offered shards; spirits follow

    wardens::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    int LastGained = 0;
    EdgeLatch PrevEdge, NextEdge, ConfirmEdge;

    static constexpr int MaxScore = 100000;
    static constexpr int MaxDrawn = 200000;
    static constexpr int MaxPouch = 100;

    int Slots() const { return AltarSlots + static_cast<int>(Core.Spirits.size()); }
    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Cursor = 0;
        LastGained = 0;
        PrevEdge.Clear();
        NextEdge.Clear();
        ConfirmEdge.Clear();
    }
    static bool GoPrev(const Input& I) { return I.Left || I.Up || I.PadLeft || I.PadUp || I.AxisX < -0.4 || I.AxisY < -0.4; }
    static bool GoNext(const Input& I) { return I.Right || I.Down || I.PadRight || I.PadDown || I.AxisX > 0.4 || I.AxisY > 0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }
    void Move(int Direction) {
        const int N = Slots();
        Cursor = ((Cursor + Direction) % N + N) % N;
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

    /** Serialises spirits as "name:hue=count+hue=count:value;..." (the save format, not SpiritsString()). */
    static std::string SpiritsField(const std::vector<wardens::Spirit>& Spirits) {
        std::string Out;
        for(size_t I = 0; I < Spirits.size(); ++I) {
            const wardens::Spirit& S = Spirits[I];
            if(I) Out.push_back(';');
            Out += std::to_string(S.Name) + ':';
            for(size_t J = 0; J < S.Cost.size(); ++J) {
                if(J) Out.push_back('+');
                Out += std::to_string(S.Cost[J].first) + '=' + std::to_string(S.Cost[J].second);
            }
            Out += ':' + std::to_string(S.Value);
        }
        return Out;
    }
    /** Parses one "name:cost:value" spirit and checks it against the rules' own cost/value relation. */
    static bool ParseSpirit(const std::string& Text, int Hues, wardens::Spirit& Out) {
        const std::vector<std::string> Parts = SplitText(Text, ':');
        if(Parts.size() != 3) return false;
        long long Name = 0, Value = 0;
        if(!ParseInteger(Parts[0], Name) || Name < 0 || Name >= wardens::NameCount) return false;
        if(!ParseInteger(Parts[2], Value) || Value < 10 || Value > 25) return false;
        Out = wardens::Spirit{};
        Out.Name = static_cast<int>(Name);
        Out.Value = static_cast<int>(Value);
        int Total = 0;
        for(const std::string& Term : SplitText(Parts[1], '+')) {
            const size_t Eq = Term.find('=');
            long long Hue = 0, Count = 0;
            if(Eq == std::string::npos) return false;
            if(!ParseInteger(Term.substr(0, Eq), Hue) || Hue < 0 || Hue >= Hues) return false;
            if(!ParseInteger(Term.substr(Eq + 1), Count) || Count < 0 || Count > 4) return false;
            Out.Cost.push_back({static_cast<int>(Hue), static_cast<int>(Count)});
            Total += static_cast<int>(Count);
        }
        if(Out.Cost.empty() || Out.Cost.size() > 2 || Total < 2 || Total > 4) return false;
        const int ExpectedValue = Total * 5 + (Out.Cost.size() == 2 ? 5 : 0);
        return Out.Value == ExpectedValue;
    }

public:
    const wardens::Game& CoreState() const { return Core; }
    int CursorSlot() const { return Cursor; }
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

    /** Takes the altar shard or summons the spirit under the cursor. False when nothing happened. */
    bool Act() {
        if(Core.Over) return false;
        int Gained = 0;
        const bool OnAltar = Cursor < AltarSlots;
        const wardens::Game::Act Result = OnAltar ? Core.Take(Cursor, Gained) : Core.Summon(Cursor - AltarSlots, Gained);
        if(Result != wardens::Game::Act::Ok) return false;
        LastGained = Gained;
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        if(Key == SourceKey::Up || Key == SourceKey::Left) Move(-1);
        else if(Key == SourceKey::Down || Key == SourceKey::Right) Move(1);
        else if(SourceKey::IsConfirm(Key)) Act();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Act();
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
        const bool Prev = PrevEdge.Rose(GoPrev(I));
        const bool Next = NextEdge.Rose(GoNext(I));
        if(Prev) Move(-1);
        else if(Next) Move(1);
        if(ConfirmEdge.Rose(Confirm(I))) Act();
    }

    std::string SaveState() const override {
        return SaveWriter(wardens::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Core.Rng.Drawn()))
            .Field("rounds", Core.Rounds)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .Field("pouch", Core.PouchString())
            .Field("offer", JoinIntegers(Core.Offer))
            .Field("summoned", Core.Summoned.empty() ? std::string() : JoinIntegers(Core.Summoned))
            .Field("spirits", SpiritsField(Core.Spirits))
            .Text();
    }
    // Pouch, offer, summoned list and spirits are each range-checked against the difficulty; spirits must also obey
    // the rules' cost/value relation. The PRNG is re-seeded and fast-forwarded so later offers match an unbroken session.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, wardens::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const wardens::Difficulty* Diff = wardens::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0, SavedCursor = 0;
        int Rounds = 0, Score = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", 1LL, static_cast<long long>(MaxDrawn), Drawn)) return false;
        if(!Fields.Int("rounds", 0, Diff->Rounds, Rounds)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!ParseInteger(Fields.Str("cursor"), SavedCursor)) return false;

        wardens::Game Fresh;
        Fresh.Diff = Diff;
        Fresh.Rounds = Rounds;
        Fresh.Score = Score;
        Fresh.Over = Over;
        Fresh.Won = Won;

        std::vector<int> Pouch, Offer, Summoned;
        if(!Fields.IntList("pouch", 0, MaxPouch, Pouch) || static_cast<int>(Pouch.size()) != Diff->Hues) return false;
        for(int Hue = 0; Hue < Diff->Hues; ++Hue) Fresh.Pouch[Hue] = Pouch[static_cast<size_t>(Hue)];
        if(!Fields.IntList("offer", 0, Diff->Hues - 1, Offer) || Offer.size() != 3) return false;
        Fresh.Offer = Offer;
        if(!Fields.Str("summoned").empty()) {
            if(!Fields.IntList("summoned", 0, wardens::NameCount - 1, Summoned)) return false;
        }
        Fresh.Summoned = Summoned;

        const std::vector<std::string> SpiritTexts = SplitText(Fields.Str("spirits"), ';');
        if(static_cast<int>(SpiritTexts.size()) != Diff->Spirits) return false;
        for(const std::string& SpiritText : SpiritTexts) {
            wardens::Spirit Spirit;
            if(!ParseSpirit(SpiritText, Diff->Hues, Spirit)) return false;
            Fresh.Spirits.push_back(Spirit);
        }
        if(SavedCursor < 0 || SavedCursor >= AltarSlots + static_cast<long long>(Fresh.Spirits.size())) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Fresh.Rng.Seed(std::string(wardens::GameId()) + ":" + std::to_string(SessionSeed) + ":" + DifficultyName);
        Fresh.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        Core = Fresh;
        ResetTable();
        Cursor = static_cast<int>(SavedCursor);
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The Wardens answered. Pad A or R lights the altar again."
                            : "HINT The altar went dark. Pad A or R lights it again.";
        }
        if(Option == 1) return "HINT Practice: the blue mark shows the Wardens' counsel.";
        return "HINT Take a shard each round; spend matching shards to summon.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(Cursor < AltarSlots) return "CUE Take shard";
        return Core.Affordable(Cursor - AltarSlots) ? "CUE Summon" : "CUE Need shards";
    }
    std::string HowToLine() const override {
        return "HOW Take one of three altar shards each round, then spend matching shards to summon spirits before the rounds end.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a shard or spirit; A takes or summons."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Rose{255, 228, 236, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255};
        const int Target = Core.Diff ? Core.Diff->Target : 0;

        F.Clear(800, 600, {20, 12, 26, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "WARDENS' GUIDE  [" : "WARDENS' ACCORD  [") + CabinetDifficulty() + "]", Rose, 26);
        F.AddText(28, 56, "SCORE: " + std::to_string(Core.Score) + "/" + std::to_string(Target) + "   ROUNDS: " + std::to_string(Core.Rounds), White, 18);

        // Guide: demo_action is (summon?, index); map it onto the cursor's slot numbering
        const std::pair<bool, int> Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : std::pair<bool, int>{false, -1};
        const int GuideSlot = Guide.second < 0 ? -1 : (Guide.first ? AltarSlots + Guide.second : Guide.second);

        // Altar: the three offered shards, cursor ring outside, guide ring inside
        F.AddText(28, 100, "ALTAR", Rose, 16);
        for(int I = 0; I < AltarSlots && I < static_cast<int>(Core.Offer.size()); ++I) {
            const double X = 60 + I * 90, Y = 160;
            const int Hue = Core.Offer[static_cast<size_t>(I)];
            if(Cursor == I && !Core.Over) F.AddCircle(X, Y, 36, Gold);
            if(GuideSlot == I) F.AddCircle(X, Y, 33, Sky);
            F.AddCircle(X, Y, 28, HueColor(Hue));
            F.AddText(X - 26, Y + 36, wardens::HueName(Hue), White, 12);
        }

        // Pouch: one counter per hue
        F.AddText(28, 230, "POUCH", Rose, 16);
        for(int Hue = 0; Hue < Core.Hues(); ++Hue) {
            const double X = 60 + Hue * 60;
            F.AddCircle(X, 270, 14, HueColor(Hue));
            F.AddText(X - 6, 290, std::to_string(Core.Pouch[Hue]), White, 14);
        }

        // Spirits: a card each, lit when affordable, cost shown as hue dots
        F.AddText(400, 100, "SPIRITS", Rose, 16);
        for(int I = 0; I < static_cast<int>(Core.Spirits.size()); ++I) {
            const wardens::Spirit& S = Core.Spirits[static_cast<size_t>(I)];
            const double Y = 130 + I * 70;
            const bool Affordable = Core.Affordable(I);
            F.AddRect(400, Y, 360, 60, Affordable ? Color{44, 36, 60, 255} : Color{30, 24, 40, 255});
            if(Cursor == AltarSlots + I && !Core.Over) F.AddRect(400, Y, 360, 4, Gold);
            if(GuideSlot == AltarSlots + I) F.AddRect(400, Y + 56, 360, 4, Sky);
            F.AddText(410, Y + 6, wardens::SpiritName(S.Name), Affordable ? Gold : White, 16);
            double DotX = 410;
            for(const auto& Cost : S.Cost) {
                for(int K = 0; K < Cost.second; ++K) {
                    F.AddCircle(DotX + 8, Y + 42, 7, HueColor(Cost.first));
                    DotX += 18;
                }
                DotX += 8;
            }
            F.AddText(700, Y + 20, "+" + std::to_string(S.Value), Sky, 18);
        }
        if(LastGained > 0 && !Core.Over) F.AddText(300, 160, "+" + std::to_string(LastGained), Gold, 24);
        if(Core.Over) F.AddText(60, 330, Core.Won ? "WON: THE WARDENS ANSWER" : "LOST: THE ALTAR GOES DARK", Gold, 22);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Summoned = std::to_string(Core.Summoned.size());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The Wardens answered; " : "The altar went dark; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R lights it again; summoned " + Summoned};
        }
        return {Core.Score, 1, false, false, "Rounds " + std::to_string(Core.Rounds) + "; summoned " + Summoned};
    }
};

}} // daedalus::desktop
