// SPDX-License-Identifier: MIT
// Siltlane desktop host. Rules live in DaedalusSiltlaneCore.h. This cabinet draws the
// course, reads the keyboard and the stick, and reports the score the arcade host shows.
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusSiltlaneCore.h"
#include <string>

namespace daedalus { namespace desktop {

class SiltlaneGame final : public Game {
    siltlane::Game Rules;
    std::uint32_t SessionSeed = 730;
public:
    std::string HintLine() const {
        if (Rules.Cleared()) return "HINT Pad A or R runs the silt course again.";
        if (Rules.Lost()) return "HINT Pad A or R starts the same lane again.";
        return "HINT Left and right switch lanes. " + std::to_string(Rules.Target() - Rules.Passed()) + " stones still to clear.";
    }
    std::string ActionCue() const {
        if (Rules.Cleared()) return "CUE Again";
        if (Rules.Lost()) return "CUE Retry";
        return "CUE Switch";
    }
    void Reset(std::uint32_t Seed) override { SessionSeed = Seed ? Seed : 1; Rules.Reset(SessionSeed); }
    bool SetOption(int Value, std::uint32_t Seed) override {
        if (Value < 0 || Value > 1) return false;
        if (!Rules.SetOption(Value, Seed)) return false;
        SessionSeed = Seed ? Seed : 1;
        return true;
    }
    int GetOption() const override { return Rules.Option(); }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if (!Game::SetCabinetDifficulty(Name)) return false;
        return Rules.SetDifficulty(Name);
    }
    bool SourceKeyDown(int Key) override {
        if (Rules.Over() && (Key == 5 || Key == 6 || Key == 7 || Key == 8)) { Rules.Reset(SessionSeed); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if (Rules.Over()) {
            if (I.FirePressed || I.JumpPressed || I.ActionPressed) Rules.Reset(SessionSeed);
            return;
        }
        const bool LeftNow = I.Left || I.PadLeft || I.AxisX < -0.4;
        const bool RightNow = I.Right || I.PadRight || I.AxisX > 0.4;
        Rules.Step(LeftNow, RightNow);
    }
    std::string HowToLine() const override {
        return "HOW Switch lanes so the drifting silt passes you. Clear eight stones, or five on the two-lane practice.";
    }
    std::string KeyHint() const override { return "KEYS Left and right switch lanes."; }
    std::string ContrastMark() const override { return Rules.Over() ? "MARK WAIT" : "MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800, 600, {16, 18, 32, 255});
        F.AddText(30, 24, "SILTLANE", {255, 236, 180, 255}, 28);
        F.AddText(30, 58, "PASSED: " + std::to_string(Rules.Passed()), White, 18);
        for (int Column = 0; Column < Rules.Course(); ++Column) {
            const double X = 180.0 + Column * 140.0;
            F.AddRect(X, 120, 100, 360, Column == Rules.Lane() ? Color{48, 56, 84, 255} : Color{28, 32, 48, 255});
        }
        for (const siltlane::Game::Stone& S : Rules.Stones()) {
            if (S.Row < 0 || S.Row > 7) continue;
            F.AddRect(196.0 + S.Lane * 140.0, 132.0 + (7 - S.Row) * 42.0, 68, 28, {180, 140, 90, 255});
        }
        F.AddRect(196.0 + Rules.Lane() * 140.0, 430, 68, 28, {120, 225, 255, 255});
        F.AddText(30, 548, HintLine(), {255, 236, 180, 255}, 16);
        F.AddText(30, 528, HowToLine(), {255, 236, 180, 255}, 14);
        DrawAccess(F, 300, 520, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), {120, 225, 255, 255}, 16);
    }
    Status GetStatus() const override {
        if (Rules.Cleared()) return {Rules.Passed(), 0, true, true, Rules.Note()};
        if (Rules.Lost()) return {Rules.Passed(), 0, true, false, Rules.Note()};
        return {Rules.Passed(), 1, false, false, Rules.Note()};
    }
    int LaneIndex() const { return Rules.Lane(); }
    int LaneCount() const { return Rules.Course(); }
    int FallEveryCount() const { return Rules.FallEvery(); }
    int SpawnEveryCount() const { return Rules.SpawnEvery(); }
    int ClosestSilt() const { return Rules.Closest(); }
    int PassTarget() const { return Rules.Target(); }
};

}} // daedalus::desktop
