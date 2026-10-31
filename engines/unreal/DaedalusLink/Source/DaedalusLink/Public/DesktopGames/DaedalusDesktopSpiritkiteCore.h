// SPDX-License-Identifier: MIT
// Spiritkite Weave (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusSpiritkiteCore.h, a port of
// tools/minigames/spiritkite.py (prism-shard-dev's rules, the authority). CPython-compatible seeding, so
// StartGame("spiritkite", seed) strings the same sky isles as spiritkite.start(seed, difficulty).
//
//   Left / Right / d-pad / stick   pick a wind lane out of the isle you are on (by destination isle)
//   pad A / J / Space              fly the picked lane
//   pad B / K                      land (only on the anchor isle 0)
//   R / pad Start                  restart a finished flight
//   option 0 Spiritkite Weave; option 1 Guide practice marks the lane the planned tour would fly next
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusSpiritkiteCore.h"
#include <cmath>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class SpiritkiteGame final : public Game {
    spiritkite::Game Core;
    int Pick = 0;             // index into Lanes() of the current isle
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    bool Landed = false;      // the flight ended by landing (true) or by the kite being lost (false)
    std::string LastResult;   // the rules' result text for the last action; empty until the first
    EdgeLatch LeftEdge, RightEdge, FlyEdge, LandEdge;

    static constexpr int MaxScore = 1000;
    static constexpr double Pi = 3.14159265358979323846;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Pick = 0;
        Landed = false;
        LastResult.clear();
        LeftEdge.Clear();
        RightEdge.Clear();
        FlyEdge.Clear();
        LandEdge.Clear();
    }
    static bool GoL(const Input& I) { return I.Left || I.PadLeft || I.AxisX < -0.4; }
    static bool GoR(const Input& I) { return I.Right || I.PadRight || I.AxisX > 0.4; }
    static bool FlyPressed(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed; }
    static bool LandPressed(const Input& I) { return I.DashPressed; }

    /** Replays `Trail` (the isles after the anchor) and the optional landing on a fresh sky; false if refused. */
    static bool Replay(spiritkite::Game& G, const std::vector<int>& Trail, bool Land) {
        std::string Text;
        for(size_t I = 1; I < Trail.size(); ++I) {
            if(G.Step({spiritkite::Kind::Fly, Trail[I]}, Text) != spiritkite::Game::Act::Ok) return false;
        }
        if(Land && G.Step({spiritkite::Kind::Land, 0}, Text) != spiritkite::Game::Act::Ok) return false;
        return true;
    }

public:
    const spiritkite::Game& CoreState() const { return Core; }
    const std::string& LastResultText() const { return LastResult; }

    /** Wind lanes out of the current isle, by destination isle (the order Left/Right cycles). */
    std::vector<int> Lanes() const {
        std::vector<int> Out;
        for(int U = 0; U < Core.Isles(); ++U) if(Core.Adj[static_cast<size_t>(Core.At)][static_cast<size_t>(U)] != 0) Out.push_back(U);
        return Out;
    }
    /** The destination isle of the picked lane, or -1 with no lanes. */
    int PickedIsle() const {
        const std::vector<int> L = Lanes();
        if(L.empty()) return -1;
        return L[static_cast<size_t>(std::min(Pick, static_cast<int>(L.size()) - 1))];
    }
    /** Points the pick at the lane to `Isle`; false when no such lane leaves the current isle. */
    bool PickLaneTo(int Isle) {
        const std::vector<int> L = Lanes();
        for(size_t I = 0; I < L.size(); ++I) if(L[I] == Isle) { Pick = static_cast<int>(I); return true; }
        return false;
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

    /** Moves the pick along the lane list; false at either end or once the flight is over. */
    bool Nudge(int Delta) {
        if(Core.Over) return false;
        const int Count = static_cast<int>(Lanes().size());
        const int Next = Pick + Delta;
        if(Count == 0 || Next < 0 || Next >= Count) return false;
        Pick = Next;
        return true;
    }
    /** Flies the picked lane. False once the flight is over or with no lane. */
    bool Fly() {
        if(Core.Over) return false;
        const int To = PickedIsle();
        if(To < 0) return false;
        std::string Result;
        if(Core.Step({spiritkite::Kind::Fly, To}, Result) != spiritkite::Game::Act::Ok) return false;
        LastResult = Result;
        Pick = 0;
        return true;
    }
    /** Lands on the anchor, ending the flight. False away from the anchor or once it is over. */
    bool Land() {
        if(Core.Over) return false;
        std::string Result;
        if(Core.Step({spiritkite::Kind::Land, 0}, Result) != spiritkite::Game::Act::Ok) return false;
        LastResult = Result;
        Landed = true;
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
            case SourceKey::B:     Land(); break;
            default:
                if(SourceKey::IsConfirm(Key)) Fly();
                break;
        }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Fly();
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
            if(FlyPressed(I) || LandPressed(I)) Deal();
            return;
        }
        const bool L = LeftEdge.Rose(GoL(I));
        const bool R = RightEdge.Rose(GoR(I));
        const bool F = FlyEdge.Rose(FlyPressed(I));
        const bool D = LandEdge.Rose(LandPressed(I));
        if(L) Nudge(-1);
        else if(R) Nudge(1);
        else if(F) Fly();
        else if(D) Land();
    }

    std::string SaveState() const override {
        return SaveWriter(spiritkite::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .List("trail", Core.Trail)
            .Flag("landed", Landed)
            .Field("pick", Pick)
            .Field("wind", Core.Wind)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward. The flight is rebuilt by replaying the saved
    // trail (and the landing) on the seeded sky; the saved wind, score and flags must match the replay, so a save
    // cannot claim lanterns or wind the lanes never gave.
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, spiritkite::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const spiritkite::Difficulty* Diff = spiritkite::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int PickIndex = 0, Wind = 0, Score = 0;
        bool WasLanded = false, Over = false, Won = false;
        std::vector<int> Trail;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.IntList("trail", 0, Diff->Isles - 1, Trail) || Trail.empty() || Trail[0] != spiritkite::Anchor) return false;
        if(static_cast<int>(Trail.size()) > Diff->Wind + 1) return false;
        if(!Fields.Flag("landed", WasLanded)) return false;
        if(!Fields.Int("pick", 0, Diff->Isles - 1, PickIndex)) return false;
        if(!Fields.Int("wind", -Diff->Wind, Diff->Wind, Wind)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;

        spiritkite::Game Fresh;
        if(!Fresh.Start(Seed, DifficultyName)) return false;
        if(!Replay(Fresh, Trail, WasLanded)) return false;
        if(Fresh.Wind != Wind || Fresh.Score != Score || Fresh.Over != Over || Fresh.Won != Won) return false;

        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core = Fresh;
        ResetTable();
        Landed = WasLanded;
        const int Count = static_cast<int>(Lanes().size());
        if(!Over && PickIndex >= Count) return false;
        Pick = PickIndex;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            if(Core.Won) return "HINT The kite lands heavy with light. Pad A or R strings a new sky.";
            return Landed ? "HINT Landed short of the target. Pad A or R strings a new sky." : "HINT The kite drifted away. Pad A or R strings a new sky.";
        }
        if(Option == 1) {
            const spiritkite::Action D = Core.DemoAction();
            return D.K == spiritkite::Kind::Land ? "HINT Practice: the planned tour is done; land now (B)."
                                                  : "HINT Practice: the blue isle is where the planned tour flies next.";
        }
        const int Home = Core.Dist[static_cast<size_t>(Core.At)][spiritkite::Anchor];
        if(Core.At == spiritkite::Anchor && Core.Lanterns() >= Core.Target) return "HINT You hold the target on the anchor. Land (B) to bank the wind left, or fly for more.";
        if(Core.Wind - Home <= 3) return "HINT The anchor is " + std::to_string(Home) + " wind away and you have " + std::to_string(Core.Wind) + ". Head home.";
        return "HINT Each lane costs its wind; a lantern is gathered the first time you land on an isle. Keep enough wind to reach the anchor.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        const int Home = Core.Dist[static_cast<size_t>(Core.At)][spiritkite::Anchor];
        return Core.Wind - Home <= 3 ? "CUE Head home" : "CUE Fly a lane";
    }
    std::string HowToLine() const override {
        return "HOW Fly the kite along wind lanes between sky isles to gather lanterns, then land on the anchor isle before the wind runs out.";
    }
    std::string KeyHint() const override { return "KEYS Left/Right pick a lane; A flies; B lands on the anchor."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Mist{205, 215, 225, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Lantern{255, 190, 90, 255}, Taken{110, 100, 90, 255}, AnchorTint{90, 190, 170, 255};
        const int N = Core.Isles();

        F.Clear(800, 600, {14, 18, 34, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "SPIRITKITE WEAVE GUIDE  [" : "SPIRITKITE WEAVE  [") + CabinetDifficulty() + "]", Mist, 26);
        F.AddText(28, 56, "WIND " + std::to_string(Core.Wind) + "   LANTERNS " + std::to_string(Core.Lanterns()) + "/" + std::to_string(Core.Target) + "   ISLE " + std::to_string(Core.At) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        if(N <= 0) return;

        // The sky: isles on a ring (index order), the anchor teal, lanterns amber until taken, you a gold frame; the
        // picked lane's isle carries a gold bar, the guide's isle a blue bar
        const double CX = 300, CY = 300, Radius = 170;
        const bool HasGuide = Option == 1 && !Core.Over;
        const spiritkite::Action Guide = HasGuide ? Core.DemoAction() : spiritkite::Action{spiritkite::Kind::Land, 0};
        const int Picked = Core.Over ? -1 : PickedIsle();
        for(int I = 0; I < N; ++I) {
            const double A = -Pi / 2 + 2 * Pi * I / N, X = CX + Radius * std::cos(A), Y = CY + Radius * std::sin(A);
            const bool Gathered = Core.IsGathered(I);
            F.AddCircle(X, Y, 22, I == spiritkite::Anchor ? AnchorTint : Gathered ? Taken : Lantern);
            F.AddText(X - 6, Y - 8, std::to_string(I), White, 13);
            if(I != spiritkite::Anchor) F.AddText(X - 10, Y + 26, "+" + std::to_string(Core.Values[static_cast<size_t>(I)]), Mist, 11);
            if(I == Picked) F.AddRect(X - 24, Y - 34, 48, 4, Gold);
            if(HasGuide && Guide.K == spiritkite::Kind::Fly && I == Guide.Isle) F.AddRect(X - 24, Y + 30, 48, 4, Sky);
            if(I == Core.At) {
                F.AddRect(X - 30, Y - 30, 60, 3, Gold);
                F.AddRect(X - 30, Y + 27, 60, 3, Gold);
                F.AddRect(X - 30, Y - 30, 3, 60, Gold);
                F.AddRect(X + 27, Y - 30, 3, 60, Gold);
            }
        }

        // Lanes out of the current isle, in pick order
        F.AddText(600, 110, "LANES FROM " + std::to_string(Core.At), Mist, 14);
        const std::vector<int> L = Lanes();
        for(size_t I = 0; I < L.size() && I < 10; ++I) {
            const int To = L[I], W = Core.Adj[static_cast<size_t>(Core.At)][static_cast<size_t>(To)];
            const bool IsPick = !Core.Over && static_cast<int>(I) == std::min(Pick, static_cast<int>(L.size()) - 1);
            F.AddText(600, 132 + 18 * static_cast<double>(I), std::string(IsPick ? "> " : "  ") + "isle " + std::to_string(To) + "  wind " + std::to_string(W) + "  home " + std::to_string(Core.Dist[static_cast<size_t>(To)][spiritkite::Anchor]), IsPick ? Gold : Mist, 12);
        }
        if(Core.Trail.size() == 1 && !Core.Over) {
            F.AddText(600, 360, "FLY   Left/Right pick a lane; A flies it (costs its wind)", Mist, 11);
            F.AddText(600, 378, "LIGHT first landing on an isle gathers its lantern", Mist, 11);
            F.AddText(600, 396, "HOME  B lands on isle 0; reach the target with wind to spare", Mist, 11);
        }
        if(!LastResult.empty() && !Core.Over) F.AddText(600, 300, LastResult, Gold, 12);
        if(Core.Over) F.AddText(600, 330, Core.Won ? "WON: HEAVY WITH LIGHT" : (Landed ? "LOST: SHORT OF THE TARGET" : "LOST: THE KITE DRIFTS AWAY"), Gold, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string Tally = "lanterns " + std::to_string(Core.Lanterns()) + "/" + std::to_string(Core.Target) + ", wind " + std::to_string(Core.Wind);
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Heavy with light; " : (Landed ? "Short of the target; " : "The kite drifted away; ");
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R strings a new sky; " + Tally};
        }
        return {Core.Score, 1, false, false, "Isle " + std::to_string(Core.At) + "; " + Tally};
    }
};

}} // daedalus::desktop
