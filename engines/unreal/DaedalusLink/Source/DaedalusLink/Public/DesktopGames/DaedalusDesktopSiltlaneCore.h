// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Siltlane: a three-lane runner. Silt stones drift toward the runner. Switching
// lanes lets a stone pass; standing in its lane ends the run. The C++ core is
// the playable rules. Easy drifts slowly, hard drifts quickly.
class SiltlaneGame final : public Game {
    struct Stone { int Lane = 0; int Row = 0; };
    int Lane = 1;
    int Passed = 0;
    bool Lost = false;
    int FallEvery = 12;
    int SpawnEvery = 24;
    int Tick = 0;
    bool WasLeft = false, WasRight = false;
    std::vector<Stone> Stones;
    Random Rng;
    std::uint32_t SessionSeed = 730;
    void ApplyPace() {
        const std::string Name = CabinetDifficulty();
        if (Name == "easy") { FallEvery = 20; SpawnEvery = 36; }
        else if (Name == "hard") { FallEvery = 8; SpawnEvery = 14; }
        else { FallEvery = 12; SpawnEvery = 24; }
    }
    void Deal() {
        Lane = 1; Passed = 0; Lost = false; Tick = 0;
        WasLeft = WasRight = false; Stones.clear();
        Rng.Seed(SessionSeed); ApplyPace();
    }
    void Fall() {
        for (Stone& S : Stones) --S.Row;
        for (const Stone& S : Stones) if (S.Row == 0 && S.Lane == Lane) { Lost = true; return; }
        std::vector<Stone> Kept;
        for (const Stone& S : Stones) {
            if (S.Row >= 0) Kept.push_back(S);
            else ++Passed;
        }
        Stones.swap(Kept);
    }
    void Spawn() { Stones.push_back({Rng.Int(0, 2), 7}); }
public:
    void Reset(std::uint32_t Seed) override { SessionSeed = Seed ? Seed : 1; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if (!Game::SetCabinetDifficulty(Name)) return false;
        ApplyPace();
        return true;
    }
    bool SourceKeyDown(int Key) override {
        if (Lost && (Key == 5 || Key == 6 || Key == 7 || Key == 8)) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if (Lost) {
            if (I.FirePressed || I.JumpPressed || I.ActionPressed) Deal();
            return;
        }
        const bool LeftNow = I.Left || I.PadLeft || I.AxisX < -0.4;
        const bool RightNow = I.Right || I.PadRight || I.AxisX > 0.4;
        if (LeftNow && !WasLeft && Lane > 0) --Lane;
        else if (RightNow && !WasRight && Lane < 2) ++Lane;
        WasLeft = LeftNow; WasRight = RightNow;
        ++Tick;
        if (Tick % FallEvery == 0) Fall();
        if (!Lost && Tick % SpawnEvery == 0) Spawn();
    }
    std::string HintLine() const {
        return Lost ? "HINT Pad A or R starts the same lane again."
                    : "HINT Left and right switch lanes before the silt reaches you.";
    }
    std::string ActionCue() const { return Lost ? "CUE Retry" : "CUE Switch"; }
    std::string HowToLine() const override { return "HOW Switch lanes so the drifting silt passes you."; }
    std::string KeyHint() const override { return "KEYS Left and right switch lanes."; }
    std::string ContrastMark() const override { return Lost ? "MARK WAIT" : "MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800, 600, {16, 18, 32, 255});
        F.AddText(30, 24, "SILTLANE", {255, 236, 180, 255}, 28);
        F.AddText(30, 58, "PASSED: " + std::to_string(Passed), White, 18);
        for (int Column = 0; Column < 3; ++Column) {
            const double X = 180.0 + Column * 140.0;
            F.AddRect(X, 120, 100, 360, Column == Lane ? Color{48, 56, 84, 255} : Color{28, 32, 48, 255});
        }
        for (const Stone& S : Stones) {
            if (S.Row < 0 || S.Row > 7) continue;
            F.AddRect(196.0 + S.Lane * 140.0, 132.0 + (7 - S.Row) * 42.0, 68, 28, {180, 140, 90, 255});
        }
        F.AddRect(196.0 + Lane * 140.0, 430, 68, 28, {120, 225, 255, 255});
        F.AddText(30, 548, HintLine(), {255, 236, 180, 255}, 16);
        F.AddText(30, 528, HowToLine(), {255, 236, 180, 255}, 14);
        DrawAccess(F, 300, 520, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), {120, 225, 255, 255}, 16);
    }
    Status GetStatus() const override {
        if (Lost) return {Passed, 0, true, false, "The silt caught the runner; passed " + std::to_string(Passed)};
        return {Passed, 1, false, false, "Lane " + std::to_string(Lane) + "; passed " + std::to_string(Passed)};
    }
    int LaneIndex() const { return Lane; }
    int FallEveryCount() const { return FallEvery; }
    int SpawnEveryCount() const { return SpawnEvery; }
    int ClosestSilt() const {
        int Best = 99;
        for (const Stone& S : Stones) if (S.Lane == Lane && S.Row >= 0 && S.Row < Best) Best = S.Row;
        return Best;
    }
};
}} // daedalus::desktop
