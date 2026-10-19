// SPDX-License-Identifier: MIT
// LAB03 Echo Bell timing gate, plain C++17 port of com.daedalus.world.labyrinth.EchoBellGate.
// Header-only, no engine dependencies. Same seed -> same peal, byte-identical EBG 1 text
// (fixture docs/contracts/echo-bell-v1/peals.ebg is produced by the Java core).
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>

namespace daedalus::labyrinth {

struct EchoRing { int Index; int RingMs; double Hz; double Gain; int DepthCells; int EchoMs; };
struct EchoVerdict { bool Open; int Hits; int FirstMiss; std::vector<int> OffsetsMs; };

class EchoBellGate {
public:
    static constexpr double kRootHz = 146.832;
    static constexpr double kMaxHz = 360.0;

    // depths: empty = seed picks them; otherwise exactly 3 + difficulty values in 1..40.
    EchoBellGate(int64_t seed, int difficulty, bool crickets, const std::vector<int>& depths = {})
        : Seed(seed), Difficulty(difficulty), Crickets(crickets) {
        if (difficulty < 0 || difficulty > 3) throw std::invalid_argument("difficulty 0-3");
        const int n = 3 + difficulty;
        if (!depths.empty() && static_cast<int>(depths.size()) != n) throw std::invalid_argument("one depth per bell");
        static constexpr int kPenta[5] = {0, 3, 5, 7, 10};
        uint64_t state = static_cast<uint64_t>(seed) ^ 0x45424731ULL;
        auto next = [&state]() {
            uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
            z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
            z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
            return z ^ (z >> 31);
        };
        int t = 0;
        for (int i = 0; i < n; ++i) {
            const int degree = kPenta[next() % 5];
            const int octave = static_cast<int>(next() % 2);
            int semis = degree + 12 * octave;
            if (semis > 15) semis -= 12;
            const int gap = 600 + 150 * static_cast<int>(next() % 5);
            const int rolled = 2 + static_cast<int>(next() % 9);
            const int depth = depths.empty() ? rolled : depths[static_cast<size_t>(i)];
            if (depth < 1 || depth > 40) throw std::invalid_argument("corridor depth 1-40 cells");
            t += gap;
            const double hz = std::round(kRootHz * std::pow(2.0, semis / 12.0) * 1000.0) / 1000.0;
            Rings.push_back({i, t, hz, gap <= 750 ? 0.3 : 0.6, depth, t + EchoDelayMs(depth)});
        }
        const int base = 140 - 20 * difficulty;
        WindowMs = crickets ? base * 3 / 2 : base;
    }

    static int EchoDelayMs(int depthCells) { return 200 + 70 * depthCells; }
    const std::vector<EchoRing>& GetRings() const { return Rings; }
    int GetWindowMs() const { return WindowMs; }

    EchoVerdict Judge(const std::vector<int>& taps) const {
        std::vector<int> echoes;
        for (const auto& r : Rings) echoes.push_back(r.EchoMs);
        std::sort(echoes.begin(), echoes.end());
        EchoVerdict v{false, 0, -1, {}};
        for (size_t i = 0; i < echoes.size(); ++i) {
            if (i >= taps.size() || (i > 0 && taps[i] < taps[i - 1])) {
                if (v.FirstMiss < 0) v.FirstMiss = static_cast<int>(i);
                continue;
            }
            const int off = taps[i] - echoes[i];
            v.OffsetsMs.push_back(off);
            if (std::abs(off) <= WindowMs) ++v.Hits;
            else if (v.FirstMiss < 0) v.FirstMiss = static_cast<int>(i);
        }
        v.Open = v.Hits == static_cast<int>(echoes.size()) && taps.size() == echoes.size();
        if (!v.Open && v.FirstMiss < 0) v.FirstMiss = static_cast<int>(echoes.size());
        if (v.Open) v.FirstMiss = -1;
        return v;
    }

    std::string ToWire() const {
        char buf[160];
        std::snprintf(buf, sizeof buf, "EBG 1\ngate %lld %d %d %d\n", static_cast<long long>(Seed), Difficulty, Crickets ? 1 : 0, WindowMs);
        std::string s = buf;
        for (const auto& r : Rings) {
            std::snprintf(buf, sizeof buf, "bell %d %d %.3f %.3f %d %d\n", r.Index, r.RingMs, r.Hz, r.Gain, r.DepthCells, r.EchoMs);
            s += buf;
        }
        return s + "end\n";
    }

private:
    int64_t Seed;
    int Difficulty;
    bool Crickets;
    int WindowMs = 0;
    std::vector<EchoRing> Rings;
};

}  // namespace daedalus::labyrinth
