// SPDX-License-Identifier: MIT
// G04 LAB07 Twin Doors for the plugin: the same riddle as prometheus' core-test/twin_doors core and the Java
// com.daedalus.world.labyrinth.TwinDoors (contract docs/contracts/twin-doors-v1), rebuilt WITHOUT C++ exceptions
// because Unreal game targets compile with them off (preflight P8). Bad input is reported, never thrown:
// difficulty outside 0..1 clamps and clears Valid(); a guard or door outside 0..1 answers nothing (Ask returns false).
// core-test/twin_doors_plugin/twin_doors_plugin_test.cpp proves byte parity with riddles.twd under /EHs-c-.
#pragma once

#include <cstdint>
#include <cstdio>
#include <string>

namespace daedalus::twindoors {

enum class Question { Direct, OtherGuard, Embedded, Self };
enum class Tone { Low, High };

constexpr double kLowHz = 146.832;   // D3
constexpr double kHighHz = 219.999;  // A3
constexpr double kGain = 0.5;

inline bool IsSide(int V) { return V == 0 || V == 1; }
inline double Hz(Tone T) { return T == Tone::Low ? kLowHz : kHighHz; }
inline const char* QuestionName(Question Q)
{
    static const char* kQ[] = {"DIRECT", "OTHER_GUARD", "EMBEDDED", "SELF"};
    return kQ[static_cast<int>(Q)];
}

// The bell a guard rings (contract truth table). lowYes: the low bell means yes.
inline Tone ToneFor(int Safe, int Liar, bool LowYes, int Guard, Question Q, int Door)
{
    const bool Lies = Guard == Liar;
    const bool DoorSafe = Safe == Door;
    bool Yes = true;
    switch (Q)
    {
        case Question::Direct: Yes = DoorSafe != Lies; break;
        case Question::OtherGuard: Yes = (DoorSafe != !Lies) != Lies; break;
        case Question::Embedded: Yes = ((DoorSafe != Lies) == LowYes) != Lies; break;
        case Question::Self: Yes = true; break;
    }
    return Yes == LowYes ? Tone::Low : Tone::High;
}

// The provably safe door after hearing one answer, or -1 if worlds disagree (or the input is not a side).
inline int Deduce(int Difficulty, int Guard, Question Q, int Door, Tone Heard)
{
    if (!IsSide(Guard) || !IsSide(Door)) { return -1; }
    int Agreed = -1;
    for (int Safe = 0; Safe < 2; ++Safe)
        for (int Liar = 0; Liar < 2; ++Liar)
            for (int Y = 0; Y < 2; ++Y)
            {
                if (Difficulty == 0 && Y == 0) { continue; }
                if (ToneFor(Safe, Liar, Y == 1, Guard, Q, Door) != Heard) { continue; }
                if (Agreed < 0) { Agreed = Safe; }
                else if (Agreed != Safe) { return -1; }
            }
    return Agreed;
}

class Riddle
{
public:
    Riddle(int64_t InSeed, int InDifficulty)
        : Seed(InSeed), Difficulty(InDifficulty < 0 ? 0 : (InDifficulty > 1 ? 1 : InDifficulty)), bValid(IsSide(InDifficulty))
    {
        uint64_t State = static_cast<uint64_t>(InSeed) ^ 0x54574431ULL;
        SafeDoor = static_cast<int>(Next(State) % 2);
        Liar = static_cast<int>(Next(State) % 2);
        bLowMeansYes = Difficulty == 0 || Next(State) % 2 == 1;
    }

    bool Valid() const { return bValid; }
    int64_t GetSeed() const { return Seed; }
    int GetDifficulty() const { return Difficulty; }
    int GetSafeDoor() const { return SafeDoor; }
    int GetLiar() const { return Liar; }
    bool GetLowMeansYes() const { return bLowMeansYes; }

    // False (Out untouched) when guard or door is not 0 or 1.
    bool Answer(int Guard, Question Q, int Door, Tone& Out) const
    {
        if (!IsSide(Guard) || !IsSide(Door)) { return false; }
        Out = ToneFor(SafeDoor, Liar, bLowMeansYes, Guard, Q, Door);
        return true;
    }
    bool IsSafe(int Door) const { return IsSide(Door) && Door == SafeDoor; }

    // TWD 1 text, byte-identical with TwinDoors.toWire() in Java.
    std::string ToWire() const
    {
        char Buf[128];
        std::snprintf(Buf, sizeof Buf, "TWD 1\ndoors %lld %d %d %d %d\n", static_cast<long long>(Seed), Difficulty, SafeDoor, Liar, bLowMeansYes ? 1 : 0);
        std::string S = Buf;
        for (int Qi = 0; Qi < 4; ++Qi)
            for (int G = 0; G < 2; ++G)
                for (int D = 0; D < 2; ++D)
                {
                    const Question Q = static_cast<Question>(Qi);
                    Tone T = Tone::High;
                    Answer(G, Q, D, T);
                    const int K = Deduce(Difficulty, G, Q, D, T);
                    std::snprintf(Buf, sizeof Buf, "ask %d %s %d %s %s\n", G, QuestionName(Q), D, T == Tone::Low ? "LOW" : "HIGH",
                                  K < 0 ? "-" : (K == 0 ? "0" : "1"));
                    S += Buf;
                }
        return S + "end\n";
    }

private:
    static uint64_t Next(uint64_t& State)
    {
        uint64_t Z = (State += 0x9e3779b97f4a7c15ULL);
        Z = (Z ^ (Z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        Z = (Z ^ (Z >> 27)) * 0x94d049bb133111ebULL;
        return Z ^ (Z >> 31);
    }

    int64_t Seed;
    int Difficulty;
    bool bValid;
    int SafeDoor = 0;
    int Liar = 0;
    bool bLowMeansYes = true;
};

enum class Step { AskFirst, AlreadyAsked, AlreadyChosen, BadSide, Ok };

// Java TwinDoors.Session: exactly one question, then exactly one door. Refusals are a Step, not an exception.
class Session
{
public:
    explicit Session(const Riddle& InRiddle) : R(InRiddle) {}
    Step Ask(int Guard, Question Q, int Door, Tone& Out)
    {
        if (bAsked) { return Step::AlreadyAsked; }
        if (!R.Answer(Guard, Q, Door, Heard)) { return Step::BadSide; }
        bAsked = true;
        Out = Heard;
        return Step::Ok;
    }
    Step Choose(int Door, bool& bOpened)
    {
        if (!bAsked) { return Step::AskFirst; }
        if (bChosen) { return Step::AlreadyChosen; }
        if (!IsSide(Door)) { return Step::BadSide; }
        bChosen = true;
        bOpened = R.IsSafe(Door);
        return Step::Ok;
    }
    bool Asked() const { return bAsked; }
    bool Chosen() const { return bChosen; }
    Tone HeardTone() const { return Heard; }

private:
    Riddle R;
    Tone Heard = Tone::High;
    bool bAsked = false;
    bool bChosen = false;
};

}  // namespace daedalus::twindoors