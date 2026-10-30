// SPDX-License-Identifier: MIT
// Shadewatch Vigil (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusShadewatchCore.h, a port of
// tools/minigames/shadewatch.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("shadewatch", seed) spawns the same shades as shadewatch.start(seed, difficulty).
//
//   Left/Right or stick   pick a lane
//   pad A / J             flare the lane (burns its front shade)
//   pad B / K             kindle one light (up to 5)
//   pad X / Space         nova: spend 3 light to burn every shade within 2 steps of the heart
//   R / pad Start         restart a finished vigil
//   option 0 Vigil; option 1 Guide practice marks what demo_action would do
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusShadewatchCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class ShadewatchGame final : public Game {
    shadewatch::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    std::string LastResult;   // the rules' result text for the last turn; empty until the first
    EdgeLatch PrevEdge, NextEdge;

    static constexpr int MaxScore = 10000;
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
    int LaneCount() const { return static_cast<int>(Core.Lanes.size()); }
    void Move(int Direction) {
        const int N = LaneCount();
        if(N <= 0) return;
        Cursor = ((Cursor + Direction) % N + N) % N;
    }
    bool Act(const shadewatch::Action& Action) {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step(Action, Result) != shadewatch::Game::Act::Ok) return false;
        LastResult = Result;
        return true;
    }
    /** Parses "a,b|c|" into lanes: each lane strictly ascending within [0, Length). */
    static bool ParseLanes(const std::string& Text, int LaneCount, int Length, std::vector<std::vector<int>>& Out) {
        Out.clear();
        const std::vector<std::string> LaneTexts = SplitText(Text, '|');
        if(static_cast<int>(LaneTexts.size()) != LaneCount) return false;
        for(const std::string& LaneText : LaneTexts) {
            std::vector<int> Lane;
            for(const std::string& Token : SplitText(LaneText, ',')) {
                long long Value = 0;
                if(!ParseInteger(Token, Value) || Value < 0 || Value >= Length) return false;
                if(!Lane.empty() && Value <= Lane.back()) return false;
                Lane.push_back(static_cast<int>(Value));
            }
            Out.push_back(Lane);
        }
        return true;
    }

public:
    const shadewatch::Game& CoreState() const { return Core; }
    int CursorLane() const { return Cursor; }
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

    bool Flare() { return Act({shadewatch::Kind::Flare, Cursor}); }
    bool Kindle() { return Act({shadewatch::Kind::Kindle, 0}); }
    bool Nova() { return Act({shadewatch::Kind::Nova, 0}); }

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
            case SourceKey::Enter: Flare(); break;
            case SourceKey::B:     Kindle(); break;
            case SourceKey::Space: Nova(); break;
            default: break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Flare();
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
        if(I.FirePressed) Flare();
        else if(I.JumpPressed) Kindle();
        else if(I.ActionPressed) Nova();
    }

    std::string SaveState() const override {
        return SaveWriter(shadewatch::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Core.Rng.Drawn()))
            .Field("turn", Core.TurnNo)
            .Field("hearts", Core.Hearts)
            .Field("light", Core.Light)
            .Field("burned", Core.Burned)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .Field("lanes", Core.LanesString())
            .Text();
    }
    // Lanes are range-checked and must be strictly ascending; the PRNG is re-seeded and fast-forwarded so the next
    // spawns match an unbroken session.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, shadewatch::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const shadewatch::Difficulty* Diff = shadewatch::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0;
        int Turn = 0, Hearts = 0, Light = 0, Burned = 0, Score = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        std::vector<std::vector<int>> Lanes;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", static_cast<long long>(2 * Diff->Lanes), static_cast<long long>(MaxDrawn), Drawn)) return false;
        if(!Fields.Int("turn", 0, Diff->Turns, Turn)) return false;
        if(!Fields.Int("hearts", 0, Diff->Hearts, Hearts)) return false;
        if(!Fields.Int("light", 0, shadewatch::LightMax, Light)) return false;
        if(!Fields.Int("burned", 0, Diff->Turns * Diff->Lanes * Diff->Length, Burned)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.Int("cursor", 0, Diff->Lanes - 1, SavedCursor)) return false;
        if(!ParseLanes(Fields.Str("lanes"), Diff->Lanes, Diff->Length, Lanes)) return false;
        if(!Over && Hearts <= 0) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core.Diff = Diff;
        Core.Lanes = Lanes;
        Core.TurnNo = Turn;
        Core.Hearts = Hearts;
        Core.Light = Light;
        Core.Burned = Burned;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        Core.Rng.Seed(std::string(shadewatch::GameId()) + ":" + std::to_string(SessionSeed) + ":" + DifficultyName);
        Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        ResetTable();
        Cursor = SavedCursor;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT Dawn: the vigil held. Pad A or R lights a new vigil."
                            : "HINT The heart dimmed. Pad A or R lights a new vigil.";
        }
        if(Option == 1) {
            const shadewatch::Action Demo = Core.DemoAction();
            if(Demo.K == shadewatch::Kind::Nova) return "HINT Practice: the watcher would NOVA now.";
            if(Demo.K == shadewatch::Kind::Flare) return "HINT Practice: the watcher would flare lane " + std::to_string(Demo.Lane + 1) + ".";
            return "HINT Practice: the watcher would kindle.";
        }
        if(Core.Light >= shadewatch::NovaCost) return "HINT Nova is ready: it burns every shade within two steps.";
        return "HINT Flare the nearest shade; kindle when the lanes are quiet.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        for(const std::vector<int>& Lane : Core.Lanes) if(!Lane.empty() && Lane.front() == 0) return "CUE Shade at the heart";
        return Core.Light >= shadewatch::NovaCost ? "CUE Flare or nova" : "CUE Flare or kindle";
    }
    std::string HowToLine() const override {
        return "HOW Each turn flare one lane, kindle light or spend 3 light on a nova; keep the creeping shades from reaching the heart until the vigil ends.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a lane; A flares, B kindles, X novas."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{220, 226, 240, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Ember{255, 150, 120, 255}, Shade{90, 70, 120, 255};
        const int Turns = Core.Diff ? Core.Diff->Turns : 0;
        const int Length = Core.Diff ? Core.Diff->Length : 1;

        F.Clear(800, 600, {10, 10, 20, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SHADEWATCH GUIDE  [" : "SHADEWATCH VIGIL  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "TURN " + std::to_string(Core.TurnNo) + "/" + std::to_string(Turns) + "   HEARTS: " + std::to_string(Core.Hearts) + "   LIGHT: " + std::to_string(Core.Light) + "/" + std::to_string(shadewatch::LightMax)
                          + "   SCORE: " + std::to_string(Core.Score), White, 18);
        const int N = LaneCount();
        if(N <= 0) return;

        const shadewatch::Action Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : shadewatch::Action{shadewatch::Kind::Kindle, -1};
        const bool GuideNova = Option == 1 && !Core.Over && Guide.K == shadewatch::Kind::Nova;

        // Lanes run left (heart) to right (far end); shades are circles at their step; the cursor underlines a lane
        const double HeartX = 120, FarX = 640, Top = 120, Gap = 300.0 / N, Step = (FarX - HeartX) / (Length - 1);
        F.AddCircle(HeartX - 40, Top + Gap * (N - 1) / 2 + Gap / 2, 26, Core.Hearts > 0 ? Ember : Shade);
        for(int I = 0; I < N; ++I) {
            const double Y = Top + I * Gap + Gap / 2;
            F.AddLine(HeartX, Y, FarX, Y, {40, 40, 64, 255}, 3);
            if(GuideNova) F.AddRect(HeartX - 6, Y - 3, Step * shadewatch::NovaReach + 12, 6, Sky);
            for(int P : Core.Lanes[static_cast<size_t>(I)]) F.AddCircle(HeartX + P * Step, Y, 11, Shade);
            if(I == Cursor && !Core.Over) F.AddRect(HeartX - 10, Y + 18, FarX - HeartX + 20, 4, Gold);
            if(Option == 1 && !Core.Over && Guide.K == shadewatch::Kind::Flare && Guide.Lane == I) F.AddRect(HeartX - 10, Y + 24, FarX - HeartX + 20, 4, Sky);
            F.AddText(FarX + 20, Y - 8, std::to_string(I + 1), White, 14);
        }
        // Light meter
        F.AddText(680, 120, "LIGHT", Mist, 14);
        for(int L = 0; L < shadewatch::LightMax; ++L) F.AddRect(680, 150 + L * 22, 60, 16, L < Core.Light ? Gold : Color{40, 40, 64, 255});
        if(Option == 1 && !Core.Over && Guide.K == shadewatch::Kind::Kindle) F.AddRect(680, 150 + shadewatch::LightMax * 22 + 4, 60, 4, Sky);
        if(!LastResult.empty() && !Core.Over) F.AddText(120, 440, "LAST: " + LastResult, Gold, 16);
        if(Core.Over) F.AddText(120, 470, Core.Won ? "WON: DAWN, THE VIGIL HOLDS" : "LOST: THE HEART DIMS", Gold, 22);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(600, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Dawn, the vigil held; " : "The heart dimmed; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R lights a new vigil; turns " + std::to_string(Core.TurnNo)};
        }
        return {Core.Score, Core.Hearts, false, false, "Turn " + std::to_string(Core.TurnNo) + "; light " + std::to_string(Core.Light) + "; burned " + std::to_string(Core.Burned)};
    }
};

}} // daedalus::desktop
