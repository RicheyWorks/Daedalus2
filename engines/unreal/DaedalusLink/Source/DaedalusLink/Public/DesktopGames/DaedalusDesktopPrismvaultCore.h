// SPDX-License-Identifier: MIT
// Prismvault Weigh (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusPrismvaultCore.h, a port of
// tools/minigames/prismvault.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("prismvault", seed) hides the same hollow shard as prismvault.start(seed, difficulty).
//
//   Left/Right or stick   pick a shard
//   pad A / J             cycle it: none -> left pan -> right pan -> none
//   pad X / Space         weigh the pans (equal, non-empty)
//   pad Y / Shift         name the cursor shard
//   pad B / K             clear both pans
//   R / pad Start         restart a finished vault
//   option 0 Weigh; option 1 Guide practice highlights the pans demo_action would load
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusPrismvaultCore.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class PrismvaultGame final : public Game {
    enum PanSide : int { NoPan = 0, LeftPan = 1, RightPan = 2 };

    prismvault::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    std::vector<int> PanOfShard;   // PanSide per shard index
    char LastResult = '?';         // '<', '>', '=' after a weighing; '?' until then
    int LastGained = 0;
    EdgeLatch PrevEdge, NextEdge;

    static constexpr int MaxScore = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Cursor = 0;
        PanOfShard.assign(static_cast<size_t>(Core.Shards()), NoPan);
        LastResult = '?';
        LastGained = 0;
        PrevEdge.Clear();
        NextEdge.Clear();
    }
    static bool GoPrev(const Input& I) { return I.Left || I.Up || I.PadLeft || I.PadUp || I.AxisX < -0.4 || I.AxisY < -0.4; }
    static bool GoNext(const Input& I) { return I.Right || I.Down || I.PadRight || I.PadDown || I.AxisX > 0.4 || I.AxisY > 0.4; }
    void Move(int Direction) {
        const int N = Core.Shards();
        if(N <= 0) return;
        Cursor = ((Cursor + Direction) % N + N) % N;
    }
    std::vector<int> ShardsOn(PanSide Which) const {
        std::vector<int> Shards;
        for(int I = 0; I < static_cast<int>(PanOfShard.size()); ++I) {
            if(PanOfShard[static_cast<size_t>(I)] == Which) Shards.push_back(I);
        }
        return Shards;
    }
    static bool Contains(const std::vector<int>& List, int Value) {
        for(int X : List) if(X == Value) return true;
        return false;
    }
    /** Replays one saved "left:right:result" row against a fresh core; false when it does not reproduce. */
    static bool ReplayRow(prismvault::Game& Fresh, const std::string& Row) {
        const std::vector<std::string> Parts = SplitText(Row, ':');
        if(Parts.size() != 3 || Parts[2].size() != 1) return false;
        std::vector<int> Left, Right;
        for(const std::string& Token : SplitText(Parts[0], ',')) {
            long long Value = 0;
            if(!ParseInteger(Token, Value)) return false;
            Left.push_back(static_cast<int>(Value));
        }
        for(const std::string& Token : SplitText(Parts[1], ',')) {
            long long Value = 0;
            if(!ParseInteger(Token, Value)) return false;
            Right.push_back(static_cast<int>(Value));
        }
        char Result = '?';
        return Fresh.Weigh(Left, Right, Result) == prismvault::Game::Act::Ok && Result == Parts[2][0];
    }

public:
    const prismvault::Game& CoreState() const { return Core; }
    int CursorShard() const { return Cursor; }
    int PanOf(int Shard) const {
        const bool InRange = Shard >= 0 && Shard < static_cast<int>(PanOfShard.size());
        return InRange ? PanOfShard[static_cast<size_t>(Shard)] : NoPan;
    }
    char LastWeighResult() const { return LastResult; }
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

    void CyclePan() {
        if(Core.Over) return;
        int& Pan = PanOfShard[static_cast<size_t>(Cursor)];
        Pan = (Pan + 1) % 3;
    }
    void ClearPans() {
        for(int& Pan : PanOfShard) Pan = NoPan;
    }
    bool WeighPans() {
        if(Core.Over) return false;
        char Result = '?';
        if(Core.Weigh(ShardsOn(LeftPan), ShardsOn(RightPan), Result) != prismvault::Game::Act::Ok) return false;
        LastResult = Result;
        ClearPans();
        return true;
    }
    bool NameCursor() {
        if(Core.Over) return false;
        int Gained = 0;
        if(Core.Name(Cursor, Gained) != prismvault::Game::Act::Ok) return false;
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
            case SourceKey::Up:
            case SourceKey::Left:  Move(-1); break;
            case SourceKey::Down:
            case SourceKey::Right: Move(1); break;
            case SourceKey::A:
            case SourceKey::Enter: CyclePan(); break;
            case SourceKey::B:     ClearPans(); break;
            case SourceKey::Space: WeighPans(); break;
            default: break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            CyclePan();
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
        if(I.FirePressed) CyclePan();
        else if(I.JumpPressed) ClearPans();
        else if(I.ActionPressed) WeighPans();
        else if(I.DashPressed) NameCursor();
    }

    std::string SaveState() const override {
        std::string Log;
        for(size_t I = 0; I < Core.Log.size(); ++I) {
            if(I) Log.push_back(';');
            Log += prismvault::Game::ListString(Core.Log[I].Left) + ':' + prismvault::Game::ListString(Core.Log[I].Right) + ':' + Core.Log[I].Result;
        }
        return SaveWriter(prismvault::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("weighings", Core.Weighings)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .Field("candidates", Core.Candidates.empty() ? std::string("-") : Core.CandidatesString())
            .Field("log", Log)
            .Text();
    }
    // The hollow shard is regenerated from the seed and the saved weighing log is replayed against it, so the
    // candidate list is derived rather than trusted.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, prismvault::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const prismvault::Difficulty* Diff = prismvault::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Weighings = 0, Score = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("weighings", 0, Diff->Weighings, Weighings)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.Int("cursor", 0, Diff->Shards - 1, SavedCursor)) return false;

        prismvault::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        const std::string Log = Fields.Str("log");
        if(!Log.empty()) {
            for(const std::string& Row : SplitText(Log, ';')) {
                if(!ReplayRow(Fresh, Row)) return false;
            }
        }
        if(Fresh.Weighings != Weighings) return false;
        const std::string SavedCandidates = Fields.Str("candidates");
        if((SavedCandidates == "-" ? std::string() : SavedCandidates) != Fresh.CandidatesString()) return false;

        Fresh.Score = Score;
        Fresh.Over = Over;
        Fresh.Won = Won;
        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        ResetTable();
        Cursor = SavedCursor;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT You found the hollow shard. Pad A or R seals a new vault."
                            : "HINT Wrong shard. Pad A or R seals a new vault.";
        }
        if(Option == 1) return "HINT Practice: the blue pans show a balanced split.";
        return "HINT Split the suspects in three; the lighter pan holds the hollow one.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        if(Core.Candidates.size() == 1) return "CUE Name it";
        if(Core.Weighings == 0) return "CUE Name a shard";
        return "CUE Load the pans";
    }
    std::string HowToLine() const override {
        return "HOW Weigh equal groups of shards on the balance to find the hollow one, then name it before the weighings run out.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a shard; A pans it, X weighs, Y names."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Ice{226, 236, 255, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255};
        const Color Amber{255, 180, 90, 255}, Azure{90, 180, 255, 255}, Suspect{200, 200, 220, 255}, Cleared{50, 50, 64, 255};

        F.Clear(800, 600, {14, 16, 24, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "PRISMVAULT GUIDE  [" : "PRISMVAULT WEIGH  [") + CabinetDifficulty() + "]", Ice, 26);
        F.AddText(28, 56, "SCORE: " + std::to_string(Core.Score) + "   WEIGHINGS LEFT: " + std::to_string(Core.Weighings) + "   SUSPECTS: " + std::to_string(Core.Candidates.size()), White, 18);
        const int N = Core.Shards();
        if(N <= 0) return;

        std::vector<int> GuideLeft, GuideRight;
        if(Option == 1 && !Core.Over) {
            const prismvault::Game::Demo Demo = Core.DemoAction();
            if(Demo.IsName) GuideLeft.push_back(Demo.Shard);
            else {
                GuideLeft = Demo.Left;
                GuideRight = Demo.Right;
            }
        }

        // Shard grid: pan colour first, then suspect/cleared; a guide ring sits behind a guided shard
        const int Columns = N <= 12 ? N : 9;
        const double Cell = N <= 12 ? 48 : 40, GridLeft = 60, GridTop = 110;
        for(int I = 0; I < N; ++I) {
            const double X = GridLeft + (I % Columns) * Cell;
            const double Y = GridTop + (I / Columns) * Cell;
            const double CX = X + Cell / 2, CY = Y + Cell / 2;
            const int Pan = PanOfShard[static_cast<size_t>(I)];
            Color Fill = Contains(Core.Candidates, I) ? Suspect : Cleared;
            if(Pan == LeftPan) Fill = Amber;
            else if(Pan == RightPan) Fill = Azure;
            F.AddCircle(CX, CY, Cell * 0.36, Fill);
            if(Contains(GuideLeft, I) || Contains(GuideRight, I)) F.AddCircle(CX, CY, Cell * 0.44, Sky);
            if(I == Cursor && !Core.Over) F.AddRect(X + 4, Y + Cell - 6, Cell - 8, 4, Gold);
            F.AddText(CX - 6, CY - 8, std::to_string(I), Black, 12);
        }

        // Weighing log and the last balance reading
        F.AddText(520, 120, "LOG", Ice, 16);
        for(size_t I = 0; I < Core.Log.size() && I < 3; ++I) {
            const prismvault::Weighing& W = Core.Log[I];
            F.AddText(520, 146 + static_cast<double>(I) * 22, prismvault::Game::ListString(W.Left) + " " + std::string(1, W.Result) + " " + prismvault::Game::ListString(W.Right), White, 14);
        }
        if(LastResult != '?' && !Core.Over) {
            const char* Reading = LastResult == '<' ? "left is lighter" : LastResult == '>' ? "right is lighter" : "balanced";
            F.AddText(520, 240, std::string("BALANCE: ") + Reading, Gold, 16);
        }
        if(LastGained > 0 && !Core.Over) F.AddText(520, 270, "+" + std::to_string(LastGained), Gold, 24);
        if(Core.Over) {
            const std::string Hollow = std::to_string(Core.Hollow);
            F.AddText(60, 400, Core.Won ? "WON: SHARD " + Hollow + " WAS HOLLOW" : "LOST: SHARD " + Hollow + " WAS THE HOLLOW ONE", Gold, 22);
        }

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(600, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The hollow shard was found; " : "Wrong shard; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R seals a new vault; weighings left " + std::to_string(Core.Weighings)};
        }
        return {Core.Score, 1, false, false, "Weighings " + std::to_string(Core.Weighings) + "; suspects " + std::to_string(Core.Candidates.size())};
    }
};

}} // daedalus::desktop
