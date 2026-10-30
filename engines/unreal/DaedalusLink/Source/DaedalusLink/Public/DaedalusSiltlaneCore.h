// SPDX-License-Identifier: MIT
// Siltlane rules core. Header-only and engine-free. The desktop host renders this;
// tools/minigames/siltlane_parity.py deals the same xorshift stream and is the fixture.
//
// Option 0 is three lanes and starts in the middle. Option 1 is a two-lane practice
// and starts on the left. A stone that reaches the runner's row catches the run.
// A stone that drifts past scores one pass. Easy clears six (four on practice),
// normal clears eight (five on practice), and hard clears ten (six on practice).
// Easy will not drop a stone on the lane the runner already occupies. Hard stones
// start one row closer. The cabinet stands at Spawn overlook, the silt course beside the dock.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace siltlane {

class Game {
public:
    struct Stone { int Lane = 0; int Row = 0; };

    int Target() const {
        const int CourseTarget = Difficulty_ == "easy" ? 6 : Difficulty_ == "hard" ? 10 : 8;
        const int PracticeTarget = Difficulty_ == "easy" ? 4 : Difficulty_ == "hard" ? 6 : 5;
        return Option_ == 1 ? PracticeTarget : CourseTarget;
    }
    int SpawnRow() const { return Difficulty_ == "hard" ? 6 : 7; }
    bool Over() const { return Lost_ || Cleared_; }
    int Lane() const { return Lane_; }
    int Course() const { return Course_; }
    int Passed() const { return Passed_; }
    int Option() const { return Option_; }
    int FallEvery() const { return FallEvery_; }
    int SpawnEvery() const { return SpawnEvery_; }
    int Tick() const { return Tick_; }
    bool Lost() const { return Lost_; }
    bool Cleared() const { return Cleared_; }
    const std::string& Difficulty() const { return Difficulty_; }
    const std::vector<Stone>& Stones() const { return Stones_; }

    void Reset(std::uint32_t Seed) { Seed_ = Seed ? Seed : 1; Deal(); }
    bool SetOption(int Value, std::uint32_t Seed) {
        if (Value < 0 || Value > 1) return false;
        Option_ = Value;
        Seed_ = Seed ? Seed : 1;
        Deal();
        return true;
    }
    bool SetDifficulty(const std::string& Name) {
        if (Name != "easy" && Name != "normal" && Name != "hard") return false;
        Difficulty_ = Name;
        ApplyPace();
        if (Passed_ >= Target()) Cleared_ = true;
        return true;
    }
    void Step(bool LeftNow, bool RightNow) {
        if (Over()) return;
        if (LeftNow && !WasLeft_ && Lane_ > 0) --Lane_;
        else if (RightNow && !WasRight_ && Lane_ < Course_ - 1) ++Lane_;
        WasLeft_ = LeftNow;
        WasRight_ = RightNow;
        ++Tick_;
        if (Tick_ % FallEvery_ == 0) Fall();
        if (!Over() && Tick_ % SpawnEvery_ == 0) Spawn();
    }
    int Closest() const {
        int Best = 99;
        for (const Stone& S : Stones_) if (S.Lane == Lane_ && S.Row >= 0 && S.Row < Best) Best = S.Row;
        return Best;
    }
    std::string Note() const {
        if (Cleared_) return "The runner cleared the silt course; passed " + std::to_string(Passed_);
        if (Lost_) return "The silt caught the runner; passed " + std::to_string(Passed_);
        return "Lane " + std::to_string(Lane_) + "; passed " + std::to_string(Passed_) + " of " + std::to_string(Target());
    }

private:
    struct Rng {
        std::uint32_t State = 730;
        void Seed(std::uint32_t Value) { State = Value ? Value : 1; }
        std::uint32_t Next() {
            State ^= State << 13;
            State ^= State >> 17;
            State ^= State << 5;
            return State;
        }
        int Mint(int Low, int High) {
            if (High <= Low) return Low;
            return Low + static_cast<int>(Next() % static_cast<std::uint32_t>(High - Low + 1));
        }
    };

    int Option_ = 0;
    int Course_ = 3;
    int Lane_ = 1;
    int Passed_ = 0;
    bool Lost_ = false;
    bool Cleared_ = false;
    int FallEvery_ = 12;
    int SpawnEvery_ = 24;
    int Tick_ = 0;
    bool WasLeft_ = false;
    bool WasRight_ = false;
    std::vector<Stone> Stones_;
    Rng Stream_;
    std::uint32_t Seed_ = 730;
    std::string Difficulty_ = "normal";

    void ApplyPace() {
        if (Difficulty_ == "easy") { FallEvery_ = 20; SpawnEvery_ = 36; }
        else if (Difficulty_ == "hard") { FallEvery_ = 8; SpawnEvery_ = 14; }
        else { FallEvery_ = 12; SpawnEvery_ = 24; }
    }
    void Deal() {
        Course_ = Option_ == 1 ? 2 : 3;
        Lane_ = Option_ == 1 ? 0 : 1;
        Passed_ = 0;
        Lost_ = false;
        Cleared_ = false;
        Tick_ = 0;
        WasLeft_ = WasRight_ = false;
        Stones_.clear();
        Stream_.Seed(Seed_);
        ApplyPace();
    }
    void Fall() {
        for (Stone& S : Stones_) --S.Row;
        for (const Stone& S : Stones_) if (S.Row == 0 && S.Lane == Lane_) { Lost_ = true; return; }
        std::vector<Stone> Kept;
        for (const Stone& S : Stones_) {
            if (S.Row >= 0) Kept.push_back(S);
            else if (Passed_ < Target()) {
                ++Passed_;
                if (Passed_ >= Target()) Cleared_ = true;
            }
        }
        Stones_.swap(Kept);
    }
    void Spawn() {
        int Drop = Stream_.Mint(0, Course_ - 1);
        if (Difficulty_ == "easy" && Course_ > 1 && Drop == Lane_) Drop = (Drop + 1) % Course_;
        Stones_.push_back({Drop, SpawnRow()});
    }
};

}} // daedalus::siltlane
