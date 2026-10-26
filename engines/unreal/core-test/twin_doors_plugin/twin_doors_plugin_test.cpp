// SPDX-License-Identifier: MIT
// G04 plugin core (Public/DaedalusTwinDoorsCore.h) under exceptions-off: byte parity with the contract fixture,
// the embedded question always solves, the session rules, and the no-throw refusals.
// cl /nologo /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /std:c++17 /W4 /WX /I <plugin Public> twin_doors_plugin_test.cpp
// usage: twin_doors_plugin_test docs/contracts/twin-doors-v1/riddles.twd
#include "DaedalusTwinDoorsCore.h"

#include <climits>
#include <cstdio>
#include <string>

using namespace daedalus::twindoors;

static int GPass = 0, GTotal = 0;
static void Expect(bool Ok, const char* Name)
{
    ++GTotal;
    if (Ok) { ++GPass; }
    std::printf("%-4s %s\n", Ok ? "ok" : "FAIL", Name);
}

int main(int argc, char** argv)
{
    if (argc != 2) { std::printf("usage: twin_doors_plugin_test riddles.twd\n"); return 2; }
    std::string Want;
    if (FILE* F = std::fopen(argv[1], "rb"))
    {
        char Buf[4096];
        size_t N;
        while ((N = std::fread(Buf, 1, sizeof Buf, F)) > 0) { Want.append(Buf, N); }
        std::fclose(F);
    }
    const int64_t Seeds[] = {1, 42, -7, 0x5EEDCAFE, LLONG_MIN};
    std::string All;
    for (int64_t S : Seeds)
        for (int D = 0; D <= 1; ++D) { All += Riddle(S, D).ToWire(); }
    Expect(!Want.empty() && All == Want, "byte parity with riddles.twd (10 riddles, Java and prometheus core)");

    bool Embedded = true, Worlds[8] = {};
    for (int64_t S = -1000; S < 1000; ++S)
        for (int D = 0; D <= 1; ++D)
        {
            const Riddle R(S, D);
            Worlds[R.GetSafeDoor() * 4 + R.GetLiar() * 2 + (R.GetLowMeansYes() ? 1 : 0)] = true;
            for (int G = 0; G < 2; ++G)
                for (int Door = 0; Door < 2; ++Door)
                {
                    Tone T = Tone::High;
                    R.Answer(G, Question::Embedded, Door, T);
                    if (Deduce(D, G, Question::Embedded, Door, T) != R.GetSafeDoor()) { Embedded = false; }
                }
        }
    bool All8 = true;
    for (bool W : Worlds) { All8 = All8 && W; }
    Expect(Embedded, "embedded question solves every seed (2000 seeds x 2 difficulties x 2 guards x 2 doors)");
    Expect(All8, "seeds reach all 8 worlds");

    const Riddle Bad(1, 2);
    Tone T = Tone::Low;
    Expect(!Bad.Valid() && Bad.GetDifficulty() == 1 && Riddle(1, 0).Valid(), "difficulty 2 clamps to 1 and clears Valid (no throw)");
    Expect(!Riddle(1, 0).Answer(2, Question::Direct, 0, T) && T == Tone::Low && Deduce(0, 0, Question::Direct, 5, Tone::Low) == -1,
           "guard or door outside 0..1 answers nothing (no throw)");

    Session S(Riddle(42, 1));
    bool Opened = false;
    Expect(S.Choose(0, Opened) == Step::AskFirst, "session: choose before asking is refused");
    Expect(S.Ask(0, Question::Embedded, 0, T) == Step::Ok && S.Ask(1, Question::Direct, 0, T) == Step::AlreadyAsked, "session: one question only");
    const int Door = Deduce(1, 0, Question::Embedded, 0, S.HeardTone());
    Expect(Door == 0 && S.Choose(Door, Opened) == Step::Ok && Opened && S.Choose(1, Opened) == Step::AlreadyChosen,
           "session: the deduced door opens (seed 42 diff 1 safe door 0), one door only");
    Expect(Hz(Tone::Low) == 146.832 && Hz(Tone::High) == 219.999 && kGain == 0.5, "bells D3 146.832 / A3 219.999, gain 0.5");

    std::printf("%d/%d\n", GPass, GTotal);
    return GPass == GTotal ? 0 : 1;
}