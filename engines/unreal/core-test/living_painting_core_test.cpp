// SPDX-License-Identifier: MIT
// G13 C++ = Java: DaedalusLivingPaintingCore.h against living_painting_parity.txt (LivingPaintingParityTest rebuilds it
// from the Java gallery classes). --write regenerates the file.
// cl /nologo /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /std:c++17 /W4 /WX /I <plugin Public> living_painting_core_test.cpp
#include "DaedalusLivingPaintingCore.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

using namespace daedalus::gallery;

static int GPass = 0, GTotal = 0;
static void Expect(bool Ok, const char* Name)
{
    ++GTotal;
    if (Ok) { ++GPass; }
    std::printf("%-4s %s\n", Ok ? "ok" : "FAIL", Name);
}

static const char kLetter[] = "RYBOGV";

static std::string Colours(int Mask)
{
    std::string S;
    for (int I = 0; I < kPigments; ++I)
        if (Mask & (1 << I)) { S += (S.empty() ? "" : ","); S += PigmentName(static_cast<Pigment>(I)); }
    return S;
}

static std::string MuralLine(int S)
{
    const int64_t Seed = S == 0 ? 0 : (S == 1 ? 999999999LL : (static_cast<int64_t>(S) * 104729LL * 7919LL + 13) % 1000000000LL);
    const int W = 1 + S % 12, H = 1 + (S * 5) % 12;
    Painting P(Seed, W, H);
    Knowledge K;
    for (int I = 0; I < 3; ++I) { K.Learn(Pigment::Red); K.Learn(Pigment::Yellow); K.Learn(Pigment::Blue); }
    std::string Cells;
    for (int Y = 0; Y < H; ++Y)
        for (int X = 0; X < W; ++X) { Pigment T = Pigment::Red; P.Reveal(X, Y, K, T); Cells += kLetter[static_cast<int>(T)]; }
    char Buf[160];
    std::snprintf(Buf, sizeof Buf, "mural s=%d seed=%lld w=%d h=%d subject=%s colours=", S, static_cast<long long>(Seed), W, H, Subject(Seed));
    return std::string(Buf) + Colours(P.ColourMask()) + " cells=" + Cells;
}

static void Session(int S, std::vector<std::string>& Out)
{
    const int64_t Seed = (static_cast<int64_t>(S) * 15485863LL + 101) % 1000000000LL;
    const int W = 2 + S % 3, H = 2 + S % 2;
    Painting P(Seed, W, H);
    Palette Pal;
    Knowledge K;
    static const char* kIng[] = {"beet", "dawnleaf", "cobalt", "copper", "orange", "salt"};
    std::string G = "grind s=" + std::to_string(S) + " seed=" + std::to_string(Seed) + " results=";
    for (int I = 0; I < 6 + 3 * S; ++I) { G += (I ? "," : ""); G += PaletteResultName(Pal.Grind(kIng[I % 6])); }
    Out.push_back(G);
    Out.push_back(std::string("mix s=") + std::to_string(S) + " VIOLET -> " + PaletteResultName(Pal.Mix(Pigment::Violet, K)));
    char Buf[200];
    for (int I = 0; I < W * H; ++I)
    {
        const int X = I % W, Y = I / W;
        const Pigment Pg = static_cast<Pigment>((I + static_cast<int>(Seed % 6)) % kPigments);
        const Result R = P.Paint(X, Y, Pg, Pal, K);
        std::snprintf(Buf, sizeof Buf, "paint s=%d %d %d %s -> %s st=%s pm=%d smudges=%d", S, X, Y, PigmentName(Pg), ResultName(R),
                      StateName(P.GetState()), P.ProgressPm(), P.SmudgeCount());
        Out.push_back(Buf);
        if (R == Result::Smudged)
        {
            const Result Wr = P.Wash(X, Y);
            std::snprintf(Buf, sizeof Buf, "wash s=%d %d %d -> %s again=%s", S, X, Y, ResultName(Wr), ResultName(P.Wash(X, Y)));
            Out.push_back(Buf);
        }
    }
    std::string C = "end s=" + std::to_string(S) + " units=";
    for (int I = 0; I < kPigments; ++I) { C += (I ? "," : ""); C += std::to_string(Pal.Count(static_cast<Pigment>(I))); }
    C += " strokes=";
    for (int I = 0; I < kPigments; ++I) { C += (I ? "," : ""); C += std::to_string(K.StrokesOf(static_cast<Pigment>(I))); }
    C += " abilities=";
    bool First = true;
    for (int I = 0; I < kAbilities; ++I)
        if (K.Has(static_cast<Ability>(I))) { C += (First ? "" : ","); C += AbilityName(static_cast<Ability>(I)); First = false; }
    Pigment Rv = Pigment::Red;
    C += std::string(" reveal=") + (P.Reveal(0, 0, K, Rv) ? PigmentName(Rv) : "refused") + " st=" + StateName(P.GetState());
    Out.push_back(C);
}

int main(int argc, char** argv)
{
    const bool Write = argc > 1 && std::strcmp(argv[1], "--write") == 0;
    const char* Path = argc > 2 ? argv[2] : "engines/unreal/core-test/living_painting_parity.txt";
    std::vector<std::string> Lines;
    for (int S = 0; S < 24; ++S) { Lines.push_back(MuralLine(S)); }
    for (int S = 0; S < 6; ++S) { Session(S, Lines); }
    std::string All;
    for (const std::string& L : Lines) { All += L + "\n"; }
    if (Write)
    {
        FILE* F = std::fopen(Path, "wb");
        if (!F) { std::printf("cannot write %s\n", Path); return 2; }
        std::fwrite(All.data(), 1, All.size(), F);
        std::fclose(F);
        std::printf("wrote %zu lines to %s\n", Lines.size(), Path);
    }
    std::string Have;
    if (FILE* F = std::fopen(Path, "rb")) { char B[4096]; size_t N; while ((N = std::fread(B, 1, sizeof B, F)) > 0) { Have.append(B, N); } std::fclose(F); }
    Expect(Have == All, "parity file matches the C++ core");

    SplitRandom R(42);  // java: new SplittableRandom(42).nextInt(3), nextInt(6), nextInt(1000000000)
    const int A = R.NextInt(3), B = R.NextInt(6), C = R.NextInt(1000000000);
    Expect(A >= 0 && A < 3 && B >= 0 && B < 6 && C >= 0 && C < 1000000000, "SplitRandom bounds");
    Expect(!Painting(-1, 2, 2).Valid() && !Painting(1000000000, 2, 2).Valid() && !Painting(5, 0, 2).Valid() && !Painting(5, 13, 1).Valid()
           && Painting(5, 12, 12).Valid(), "out-of-range seed or side makes an invalid mural (no throw)");
    Painting P(7, 2, 2);
    Palette Pal;
    Knowledge K;
    Pigment T = Pigment::Red;
    Expect(P.Paint(5, 0, Pigment::Red, Pal, K) == Result::BadCell && P.Wash(0, 9) == Result::BadCell && !P.Reveal(0, 0, K, T),
           "bad cell and reveal without PRISM_SIGHT refuse (no throw)");
    Expect(P.Paint(0, 0, Pigment::Red, Pal, K) == Result::NoPigment, "painting with an empty palette");
    Expect(Painting::ForFrame(9, 7, 3).GetWidth() == 12 && Painting::ForFrame(9, 7, 3).GetHeight() == 6, "ForFrame: 2x2 cells per cube, capped at 12");
    std::printf("%d/%d\n", GPass, GTotal);
    return GPass == GTotal ? 0 : 1;
}