// SPDX-License-Identifier: MIT
// Shardring Resonance (Prismheart cabinet): the ADaedalusDesktopArcade host for the pure core in
// DaedalusShardringCore.h, a port of tools/minigames/prism_shard.py (prism-shard-dev, the rules authority).
// Draws come from a CPython-compatible stream seeded exactly like prism_shard.py, so seed + difficulty reproduce
// the Python and web games; tests may inject an Oracle to replay recorded fixtures instead. Cabinet difficulty is
// the game's difficulty (easy 12 facets / normal 10 / hard 8).
//
//   Left/Up or stick      previous empty facet     Right/Down   next empty facet
//   pad A / J / Space     set the current shard in the cursor facet
//   R / pad Start         restart a finished ring
//   option 0 Resonance; option 1 Guide practice rings the facet greedy_move would pick
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusPyRandomCore.h"
#include "DaedalusShardringCore.h"
#include <cmath>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class ShardringGame final : public Game {
    /** The CPython-compatible draw stream: random.Random(f"shardring:{seed}:{difficulty}"). */
    struct Stream final : shardring::Oracle {
        pyrandom::PyRandom Rng;
        int Hues = 4;
        void Seed(std::uint32_t Value, const std::string& Difficulty) {
            Rng.Seed("shardring:" + std::to_string(Value) + ":" + Difficulty);
        }
        shardring::Hue Draw() override { return static_cast<shardring::Hue>(Rng.ChoiceIndex(static_cast<std::size_t>(Hues))); }
        int SpiritPick(const std::vector<int>& Filled) override { return Filled[Rng.ChoiceIndex(Filled.size())]; }
    };

    Stream Draws;
    shardring::Oracle* External = nullptr;   // tests only; see UseOracle
    shardring::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    int LastGained = 0;
    EdgeLatch PrevEdge, NextEdge, ConfirmEdge;

    static constexpr long long MaxScore = 1000000000LL;
    static constexpr int MaxDrawn = 200000;

    shardring::Oracle& Source() { return External ? *External : Draws; }
    const shardring::Difficulty& Difficulty() const {
        const shardring::Difficulty* Found = shardring::FindDifficulty(CabinetDifficulty());
        return Found ? *Found : *shardring::FindDifficulty("normal");
    }
    void Deal() {
        const shardring::Difficulty& Diff = Difficulty();
        Draws.Hues = Diff.Hues;
        Draws.Seed(SessionSeed, Diff.Name);
        Core.Start(Diff.Name, Source());
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
    bool Empty(int Facet) const { return Core.Ring[static_cast<std::size_t>(Facet)] == shardring::Hue::None; }
    /** Moves the cursor to the next empty facet in `Direction`, wrapping; stays put when the ring is full. */
    void MoveCursor(int Direction) {
        const int N = Core.Facets();
        if(N <= 0) return;
        for(int Steps = 1; Steps <= N; ++Steps) {
            const int Facet = ((Cursor + Direction * Steps) % N + N) % N;
            if(Empty(Facet)) {
                Cursor = Facet;
                return;
            }
        }
    }
    /** After a placement the cursor may sit on a filled facet; slide it forward to an empty one. */
    void Settle() {
        if(Core.Facets() && !Empty(Cursor)) MoveCursor(1);
    }
    static Color HueColor(shardring::Hue Hue) {
        switch(Hue) {
            case shardring::Hue::Ember:   return {255, 132, 64, 255};
            case shardring::Hue::Tide:    return {72, 160, 255, 255};
            case shardring::Hue::Verdant: return {96, 214, 112, 255};
            case shardring::Hue::Gale:    return {228, 228, 160, 255};
            case shardring::Hue::Umbra:   return {170, 110, 230, 255};
            default:                      return {60, 56, 70, 255};
        }
    }
    static std::vector<int> HueValues(const std::vector<shardring::Hue>& Hues) {
        std::vector<int> Values;
        for(shardring::Hue Hue : Hues) Values.push_back(static_cast<int>(Hue));
        return Values;
    }

public:
    /** Tests only: route every draw and spirit pick through a fixture oracle instead of the seeded stream. */
    void UseOracle(shardring::Oracle* Oracle) { External = Oracle; }
    const shardring::Game& CoreState() const { return Core; }
    int CursorFacet() const { return Cursor; }
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

    bool Place() {
        if(Core.Over) return false;
        int Gained = 0;
        if(Core.SetShard(Cursor, Source(), Gained) != shardring::Game::Place::Ok) return false;
        LastGained = Gained;
        Settle();
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        if(Key == SourceKey::Up || Key == SourceKey::Left) MoveCursor(-1);
        else if(Key == SourceKey::Down || Key == SourceKey::Right) MoveCursor(1);
        else if(SourceKey::IsConfirm(Key)) Place();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Place();
            return true;
        }
        if(Button == PadButton::Start && Core.Over) {   // pad menu restarts only after the sphere settles
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
        if(Prev) MoveCursor(-1);
        else if(Next) MoveCursor(1);
        if(ConfirmEdge.Rose(Confirm(I))) Place();
    }

    std::string SaveState() const override {
        return SaveWriter(shardring::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("drawn", static_cast<unsigned long long>(Draws.Rng.Drawn()))
            .Field("pouch", Core.Pouch)
            .Field("score", Core.Score)
            .Field("chain", Core.Chain)
            .Field("cur", static_cast<int>(Core.Current))
            .Field("next", static_cast<int>(Core.Next))
            .Field("cursor", Cursor)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .List("ring", HueValues(Core.Ring))
            .List("res", std::vector<int>(Core.Resonance, Core.Resonance + shardring::HueCount))
            .List("spirits", HueValues(Core.Spirits))
            .Text();
    }
    // Ring, resonance and spirits are range-checked against the difficulty; the draw stream is re-seeded and
    // fast-forwarded by the saved word count so the next shards match an unbroken session.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, shardring::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const shardring::Difficulty* Diff = shardring::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        long long Drawn = 0, Score = 0;
        int Pouch = 0, Chain = 0, Current = 0, Next = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        std::vector<int> Ring, Resonance, Spirits;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("drawn", 2LL, static_cast<long long>(MaxDrawn), Drawn)) return false;   // Start() draws two
        if(!Fields.Int("pouch", 0, Diff->Shards, Pouch)) return false;
        if(!Fields.Int("score", 0LL, MaxScore, Score)) return false;
        if(!Fields.Int("chain", 0, Diff->Shards, Chain)) return false;
        if(!Fields.Int("cur", 0, Diff->Hues - 1, Current) || !Fields.Int("next", 0, Diff->Hues - 1, Next)) return false;
        if(!Fields.Int("cursor", 0, Diff->Facets - 1, SavedCursor)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.IntList("ring", -1, Diff->Hues - 1, Ring) || static_cast<int>(Ring.size()) != Diff->Facets) return false;
        if(!Fields.IntList("res", 0, Diff->Shards, Resonance) || static_cast<int>(Resonance.size()) != shardring::HueCount) return false;
        if(!Fields.IntList("spirits", 0, Diff->Hues - 1, Spirits)) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Draws.Hues = Diff->Hues;
        Draws.Seed(SessionSeed, Diff->Name);
        Draws.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        Core.Diff = Diff;
        Core.Ring.clear();
        for(int Value : Ring) Core.Ring.push_back(static_cast<shardring::Hue>(Value));
        Core.Pouch = Pouch;
        Core.Score = static_cast<int>(Score);
        Core.Chain = Chain;
        for(int Hue = 0; Hue < shardring::HueCount; ++Hue) Core.Resonance[Hue] = Resonance[static_cast<std::size_t>(Hue)];
        Core.Spirits.clear();
        for(int Value : Spirits) Core.Spirits.push_back(static_cast<shardring::Hue>(Value));
        Core.Current = static_cast<shardring::Hue>(Current);
        Core.Next = static_cast<shardring::Hue>(Next);
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Cursor = SavedCursor;
        Settle();
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT The sphere is whole. Pad A or R sets a new ring."
                            : "HINT The sphere shattered. Pad A or R sets a new ring.";
        }
        if(Core.Chain > 0) return "HINT Chain " + std::to_string(Core.Chain) + ": keep resonating for bigger clears.";
        if(Option == 1) return "HINT Practice: the blue ring marks a strong facet.";
        return "HINT Three of one hue in a row resonate and clear.";
    }
    std::string ActionCue() const { return Core.Over ? "CUE Retry" : "CUE Set shard"; }
    std::string HowToLine() const override { return "HOW Set each shard in an empty facet; three of one hue in a row resonate."; }
    std::string KeyHint() const override { return "KEYS Left or Right picks a facet; A sets the shard."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Lilac{236, 222, 255, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Dim{180, 170, 210, 255};

        F.Clear(800, 600, {14, 12, 26, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SHARDRING GUIDE  [" : "SHARDRING RESONANCE  [") + CabinetDifficulty() + "]", Lilac, 26);
        F.AddText(28, 56, "SCORE: " + std::to_string(Core.Score) + "   CHAIN: " + std::to_string(Core.Chain) + "   POUCH: " + std::to_string(Core.Pouch), White, 18);

        // The ring: facets on a circle starting at twelve o'clock, cursor ring outside, guide ring inside
        const double CX = 330, CY = 300, Radius = 165, Facet = 26;
        F.AddCircle(CX, CY, Radius + Facet + 10, {30, 26, 52, 255});
        F.AddCircle(CX, CY, Radius - Facet - 10, {14, 12, 26, 255});
        const int N = Core.Facets();
        const int Guide = (Option == 1 && !Core.Over) ? Core.GreedyMove() : -1;
        for(int I = 0; I < N; ++I) {
            const double Angle = -1.5707963267948966 + 6.283185307179586 * I / static_cast<double>(N);
            const double X = CX + Radius * std::cos(Angle), Y = CY + Radius * std::sin(Angle);
            const shardring::Hue Hue = Core.Ring[static_cast<std::size_t>(I)];
            if(I == Cursor && !Core.Over) F.AddCircle(X, Y, Facet + 6, Gold);
            if(I == Guide) F.AddCircle(X, Y, Facet + 3, Sky);
            F.AddCircle(X, Y, Facet, HueColor(Hue));
            F.AddText(X - 6, Y - 9, std::to_string(I), Hue == shardring::Hue::None ? Color{150, 150, 170, 255} : Black, 14);
        }

        // Current and next shard, then the summoned spirits
        F.AddRect(560, 110, 200, 150, {22, 20, 40, 255});
        F.AddText(572, 118, "SHARD", Lilac, 16);
        F.AddCircle(620, 190, 30, HueColor(Core.Current));
        F.AddText(586, 230, shardring::HueName(Core.Current), White, 14);
        F.AddText(680, 118, "NEXT", Dim, 14);
        F.AddCircle(710, 190, 18, HueColor(Core.Next));
        F.AddText(690, 230, shardring::HueName(Core.Next), Dim, 12);
        F.AddText(572, 280, "SPIRITS", Lilac, 16);
        for(std::size_t I = 0; I < Core.Spirits.size() && I < 8; ++I) {
            F.AddText(572, 302 + static_cast<double>(I) * 18, shardring::SpiritName(Core.Spirits[I]), HueColor(Core.Spirits[I]), 13);
        }
        if(LastGained > 0 && !Core.Over) F.AddText(CX - 40, CY - 10, "+" + std::to_string(LastGained), Gold, 24);
        if(Core.Over) F.AddText(CX - 120, CY - 14, Core.Won ? "WON: THE SPHERE IS WHOLE" : "LOST: THE SPHERE SHATTERED", Gold, 22);

        F.AddText(28, 528, HowToLine(), Gold, 14);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string SpiritCount = std::to_string(Core.Spirits.size());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "The sphere is whole; " : "The sphere shattered; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R sets a new ring; spirits " + SpiritCount};
        }
        return {Core.Score, 1, false, false, "Pouch " + std::to_string(Core.Pouch) + "; chain " + std::to_string(Core.Chain) + "; spirits " + SpiritCount};
    }
};

}} // daedalus::desktop
