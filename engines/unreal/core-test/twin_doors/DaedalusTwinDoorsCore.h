// SPDX-License-Identifier: MIT
// LAB07 Twin Doors, plain C++17 port of com.daedalus.world.labyrinth.TwinDoors.
// Header-only, no engine dependencies; byte-identical TWD 1 text with the Java core
// (fixture docs/contracts/twin-doors-v1/riddles.twd).
#pragma once

#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>

namespace daedalus::labyrinth {

enum class TwinQuestion { Direct, OtherGuard, Embedded, Self };
enum class TwinTone { Low, High };

class TwinDoors {
public:
    static constexpr double kLowHz = 146.832;   // D3
    static constexpr double kHighHz = 219.999;  // A3
    static constexpr double kGain = 0.5;

    TwinDoors(int64_t seed, int difficulty) : Seed(seed), Difficulty(difficulty) {
        if (difficulty < 0 || difficulty > 1) throw std::invalid_argument("difficulty 0-1");
        uint64_t state = static_cast<uint64_t>(seed) ^ 0x54574431ULL;
        auto next = [&state]() {
            uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
            z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
            z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
            return z ^ (z >> 31);
        };
        SafeDoor = static_cast<int>(next() % 2);
        Liar = static_cast<int>(next() % 2);
        LowMeansYes = difficulty == 0 || next() % 2 == 1;
    }

    int GetSafeDoor() const { return SafeDoor; }
    int GetLiar() const { return Liar; }
    bool GetLowMeansYes() const { return LowMeansYes; }
    static double Hz(TwinTone t) { return t == TwinTone::Low ? kLowHz : kHighHz; }

    TwinTone Answer(int guard, TwinQuestion q, int door) const {
        Check(guard); Check(door);
        return Tone(SafeDoor, Liar, LowMeansYes, guard, q, door);
    }
    bool Choose(int door) const { Check(door); return door == SafeDoor; }

    // Returns the provably safe door (0/1) or -1 if the answer leaves both possible.
    static int Deduce(int difficulty, int guard, TwinQuestion q, int door, TwinTone heard) {
        int agreed = -1;
        for (int safe = 0; safe < 2; ++safe)
            for (int liar = 0; liar < 2; ++liar)
                for (int y = 0; y < 2; ++y) {
                    if (difficulty == 0 && y == 0) continue;
                    if (Tone(safe, liar, y == 1, guard, q, door) != heard) continue;
                    if (agreed < 0) agreed = safe;
                    else if (agreed != safe) return -1;
                }
        return agreed;
    }

    std::string ToWire() const {
        static const char* kQ[] = {"DIRECT", "OTHER_GUARD", "EMBEDDED", "SELF"};
        char buf[128];
        std::snprintf(buf, sizeof buf, "TWD 1\ndoors %lld %d %d %d %d\n", static_cast<long long>(Seed), Difficulty, SafeDoor, Liar, LowMeansYes ? 1 : 0);
        std::string s = buf;
        for (int qi = 0; qi < 4; ++qi)
            for (int g = 0; g < 2; ++g)
                for (int d = 0; d < 2; ++d) {
                    const auto q = static_cast<TwinQuestion>(qi);
                    const TwinTone t = Answer(g, q, d);
                    const int k = Deduce(Difficulty, g, q, d, t);
                    std::snprintf(buf, sizeof buf, "ask %d %s %d %s %s\n", g, kQ[qi], d, t == TwinTone::Low ? "LOW" : "HIGH",
                                  k < 0 ? "-" : (k == 0 ? "0" : "1"));
                    s += buf;
                }
        return s + "end\n";
    }

private:
    static void Check(int v) { if (v != 0 && v != 1) throw std::invalid_argument("side must be 0 or 1"); }
    static TwinTone Tone(int safe, int liar, bool lowYes, int guard, TwinQuestion q, int door) {
        const bool lies = guard == liar;
        const bool doorSafe = safe == door;
        bool yes = true;
        switch (q) {
            case TwinQuestion::Direct: yes = doorSafe != lies; break;
            case TwinQuestion::OtherGuard: yes = (doorSafe != !lies) != lies; break;
            case TwinQuestion::Embedded: yes = ((doorSafe != lies) == lowYes) != lies; break;
            case TwinQuestion::Self: yes = true; break;
        }
        return yes == lowYes ? TwinTone::Low : TwinTone::High;
    }

    int64_t Seed;
    int Difficulty;
    int SafeDoor = 0;
    int Liar = 0;
    bool LowMeansYes = true;
};

}  // namespace daedalus::labyrinth
