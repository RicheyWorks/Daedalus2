// SPDX-License-Identifier: MIT
//
// DSP 1 (DaedalusRealmSprites.h) agrees with tools/realm/sprites.py: every case in sprites_parity.txt gets the same
// refusal word for word, a good pack parses, and a sprite draws with its transparent pixels left alone.
//
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public realm_sprites_test.cpp -o realm_sprites_test
//   ./realm_sprites_test ../../../tools/realm/sprites_parity.txt      prints n/m last; exits 1 on a failure

#include "DaedalusRealmSprites.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>

using namespace daedalus::realm;

static int Passed = 0, Total = 0;
static void Check(const std::string& Label, bool Ok, const std::string& Detail = "")
{
    ++Total;
    Passed += Ok;
    std::printf("%s %s%s\n", Ok ? "PASS" : "FAIL", Label.c_str(), Ok || Detail.empty() ? "" : ("  " + Detail).c_str());
}

static std::string Unescape(const std::string& S)
{
    std::string Out;
    for (size_t i = 0; i < S.size(); ++i)
    {
        if (S[i] == '\\' && i + 1 < S.size() && S[i + 1] == 'n') { Out += '\n'; ++i; }
        else Out += S[i];
    }
    return Out;
}

int main(int Argc, char** Argv)
{
    const std::string Fixture = Argc > 1 ? Argv[1] : "../../../tools/realm/sprites_parity.txt";
    std::ifstream In(Fixture);
    Check("the parity fixture opens", In.good(), Fixture);
    std::string Line, Case;
    while (std::getline(In, Line))
    {
        if (Line.rfind("CASE ", 0) == 0) { Case = Unescape(Line.substr(5)); continue; }
        if (Line.rfind("WANT ", 0) != 0) continue;
        const std::string Want = Line.substr(5);
        SpritePack P;
        std::string Err;
        const bool Ok = P.Parse(Case, Err);
        if (Want.rfind("OK ", 0) == 0)
            Check("parses: " + Want, Ok && std::to_string(P.Sprites.size()) == Want.substr(3), Err);
        else
            Check("refuses: " + Want, !Ok && Err == Want, Err);
    }
    // draw one
    SpritePack P;
    std::string Err;
    const std::string Text = "DSP 1\npalette 2 000000 58D840\nsprite BLOB 4 2 2\n.11.\n1111\n1..1\n.11.\n";
    Check("a small pack parses", P.Parse(Text, Err), Err);
    const Sprite* S = P.Find("BLOB");
    Check("and its sprite is found", S && S->W == 4 && S->H == 2 && S->Frames == 2);
    Frame F(8, 8);
    F.Clear(0x123456);
    if (S) SpritePack::Draw(F, 2, 2, *S, 1);
    Check("frame 1 drawn: corners painted, middle left alone", F.Get(2, 2) == 0x58D840 && F.Get(3, 2) == 0x123456 && F.Get(5, 2) == 0x58D840
        && F.Get(3, 3) == 0x58D840 && F.Get(2, 3) == 0x123456);
    F.Clear(0x123456);
    if (S) SpritePack::Draw(F, 0, 0, *S, 0, true);
    Check("hurt paints every opaque pixel white", F.Get(1, 0) == Pal::White && F.Get(0, 0) == 0x123456);
    Check("black in a palette is stored as 010101", P.Palette[0] == 0x010101u);
    std::printf("%d/%d\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
