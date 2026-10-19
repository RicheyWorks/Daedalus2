// SPDX-License-Identifier: MIT
// DaedalusEchoBellSessionCore.h
//
// Engine-free play session for the LAB03 Echo Bell gate (contest gap G01, echo-bell-v1).
// AEchoBellGate is a thin wrapper around this: it feeds the clock and Use-key taps in and
// plays the cues that come out. core-test/echo_bell/echo_bell_gate_session_test.cpp replays
// docs/contracts/echo-bell-v1/CUE-SHEET.md and peals.ebg through exactly this code.
//
// The peal itself (rings, hz, gain, depth, echo times, window, Judge) comes unchanged from
// DaedalusEchoBellCore.h, a byte-identical copy of core-test/echo_bell/DaedalusEchoBellCore.h
// (Prometheus's port of daedalus-core world/labyrinth/EchoBellGate.java; CI compares the two).
// Plain C++17, no engine headers, no exceptions reached: configs are validated first so the
// core's invalid_argument paths are never taken from game code.
#pragma once

#include "DaedalusEchoBellCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace daedalus::labyrinth {

// Fixed rules from CUE-SHEET.md ("Fixed rules for the actor").
struct EchoCueRules {
    static constexpr double kMaxGain = 0.6;          // never above 0.6
    static constexpr double kEchoGainScale = 0.5;    // echo = same bell, gain x0.5
    static constexpr double kEchoLowPassHz = 1200.0; // echo low-passed ~1.2 kHz
    static constexpr double kCricketGain = 0.2;      // cricket assist chirp, gain <= 0.2
    static constexpr double kBellDecaySeconds = 1.5; // struck bronze decay
};

enum class EchoCueKind { Bell = 0, Echo = 1, Cricket = 2 };

struct EchoCue {
    EchoCueKind Kind;
    int AtMs;         // from peal start
    int BellIndex;
    double Hz;        // 0 for crickets
    double Gain;
    double LowPassHz; // 0 = no filter
};

struct EchoGateConfig {
    int64_t Seed = 1;
    int Difficulty = 0;       // 0..3 -> 3..6 bells
    bool Crickets = false;    // Echo Crickets assist: window x1.5 plus a chirp on each echo
    std::vector<int> Depths;  // corridor depth in maze cells per bell; empty = the seed picks
};

inline bool ValidateGateConfig(const EchoGateConfig& c, std::string* why = nullptr) {
    auto fail = [why](const char* m) { if (why) *why = m; return false; };
    if (c.Difficulty < 0 || c.Difficulty > 3) return fail("difficulty 0-3");
    if (!c.Depths.empty()) {
        if (c.Depths.size() != static_cast<size_t>(3 + c.Difficulty)) return fail("one depth per bell");
        for (int d : c.Depths) {
            if (d < 1 || d > 40) return fail("corridor depth 1-40 cells");
        }
    }
    return true;
}

// Bells at RingMs, echoes at EchoMs (gain x0.5, low-passed), a cricket tick on each echo when
// assisted. Stable order: time, then Bell < Echo < Cricket, then bell index.
inline std::vector<EchoCue> BuildCues(const EchoBellGate& gate, bool crickets) {
    std::vector<EchoCue> cues;
    for (const EchoRing& r : gate.GetRings()) {
        const double g = std::min(r.Gain, EchoCueRules::kMaxGain);
        cues.push_back({EchoCueKind::Bell, r.RingMs, r.Index, r.Hz, g, 0.0});
        cues.push_back({EchoCueKind::Echo, r.EchoMs, r.Index, r.Hz, g * EchoCueRules::kEchoGainScale,
                        EchoCueRules::kEchoLowPassHz});
        if (crickets) cues.push_back({EchoCueKind::Cricket, r.EchoMs, r.Index, 0.0, EchoCueRules::kCricketGain, 0.0});
    }
    std::stable_sort(cues.begin(), cues.end(), [](const EchoCue& a, const EchoCue& b) {
        if (a.AtMs != b.AtMs) return a.AtMs < b.AtMs;
        if (a.Kind != b.Kind) return static_cast<int>(a.Kind) < static_cast<int>(b.Kind);
        return a.BellIndex < b.BellIndex;
    });
    return cues;
}

enum class EchoPhase { Idle, Listening, Opened, Failed };

inline const char* EchoPhaseName(EchoPhase p) {
    switch (p) {
        case EchoPhase::Listening: return "listening";
        case EchoPhase::Opened: return "opened";
        case EchoPhase::Failed: return "failed";
        case EchoPhase::Idle: default: return "idle";
    }
}

// One gate's play loop: Start -> (Advance + Tap)* -> JudgeDue -> Finish -> Opened, or Failed -> Retry.
class EchoBellSession {
public:
    bool Start(const EchoGateConfig& c, std::string* why = nullptr) {
        if (!ValidateGateConfig(c, why)) return false;
        Config = c;
        Gate.emplace(c.Seed, c.Difficulty, c.Crickets, c.Depths);
        Cues = BuildCues(*Gate, c.Crickets);
        int lastEcho = 0;
        for (const EchoRing& r : Gate->GetRings()) lastEcho = std::max(lastEcho, r.EchoMs);
        DeadlineMs = lastEcho + Gate->GetWindowMs();
        AttemptCount = 0;
        Arm();
        return true;
    }

    // Same peal again after a miss.
    bool Retry() {
        if (PhaseNow != EchoPhase::Failed) return false;
        Arm();
        return true;
    }

    // Appends every cue due at or before nowMs, each exactly once, in order.
    void Advance(int nowMs, std::vector<EchoCue>& due) {
        due.clear();
        if (PhaseNow != EchoPhase::Listening) return;
        while (NextCue < Cues.size() && Cues[NextCue].AtMs <= nowMs) due.push_back(Cues[NextCue++]);
    }

    // A Use-key tap at nowMs (ms from peal start). Ignored unless listening.
    bool Tap(int nowMs) {
        if (PhaseNow != EchoPhase::Listening) return false;
        Taps.push_back(nowMs);
        return true;
    }

    // Judge once every echo has a tap, or once the last echo's window has closed.
    bool JudgeDue(int nowMs) const {
        return PhaseNow == EchoPhase::Listening && (Taps.size() >= Gate->GetRings().size() || nowMs > DeadlineMs);
    }

    const EchoVerdict& Finish() {
        LastVerdict = Gate->Judge(Taps);
        PhaseNow = LastVerdict.Open ? EchoPhase::Opened : EchoPhase::Failed;
        return LastVerdict;
    }

    // Sorted echo times: the taps that open the gate (tests, hints, demo playback).
    std::vector<int> PerfectTaps() const {
        std::vector<int> e;
        if (!Gate) return e;
        for (const EchoRing& r : Gate->GetRings()) e.push_back(r.EchoMs);
        std::sort(e.begin(), e.end());
        return e;
    }

    EchoPhase Phase() const { return PhaseNow; }
    int Attempts() const { return AttemptCount; }
    int DeadlineAtMs() const { return DeadlineMs; }
    int WindowMs() const { return Gate ? Gate->GetWindowMs() : 0; }
    size_t CuesPlayed() const { return NextCue; }
    const std::vector<EchoCue>& GetCues() const { return Cues; }
    const std::vector<int>& GetTaps() const { return Taps; }
    const EchoVerdict& Verdict() const { return LastVerdict; }
    const EchoBellGate* GetGate() const { return Gate ? &*Gate : nullptr; }
    const EchoGateConfig& GetConfig() const { return Config; }

private:
    void Arm() {
        NextCue = 0;
        Taps.clear();
        LastVerdict = EchoVerdict{false, 0, -1, {}};
        PhaseNow = EchoPhase::Listening;
        ++AttemptCount;
    }

    EchoGateConfig Config;
    std::optional<EchoBellGate> Gate;
    std::vector<EchoCue> Cues;
    std::vector<int> Taps;
    EchoVerdict LastVerdict{false, 0, -1, {}};
    EchoPhase PhaseNow = EchoPhase::Idle;
    size_t NextCue = 0;
    int DeadlineMs = 0;
    int AttemptCount = 0;
};

}  // namespace daedalus::labyrinth