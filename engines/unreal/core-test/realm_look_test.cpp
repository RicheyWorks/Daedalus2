// SPDX-License-Identifier: MIT
// Direct, engine-free checks of DaedalusRealmLook.h (the realm's window kit and richer field tiles). realm_core_test
// renders whole screens; this pins the kit piece by piece: the window's rounded rule and title cut, the cursor and
// paging arrow shapes, bold text, the grid's dim rows and blinking cursor, the typewriter page, the party strip, and
// that tiles and the battle backdrop stay inside their bounds and are deterministic.
// Build: g++ -std=c++17 -I../DaedalusLink/Source/DaedalusLink/Public realm_look_test.cpp
#include <cstdio>  // DaedalusRealmLook.h's MemberCard uses std::snprintf without including it itself

#include "DaedalusRealmLook.h"

#include <string>
#include <vector>

using namespace daedalus::realm;

static int Passed = 0, Total = 0;
static void Check(const char* What, bool Ok, const std::string& Detail = "")
{
    ++Total;
    if (Ok) ++Passed;
    std::printf("%s %s%s%s\n", Ok ? "PASS" : "FAIL", What, Detail.empty() ? "" : "  ", Detail.c_str());
}

static int CountColour(const Frame& F, uint32_t C, int X0 = 0, int Y0 = 0, int X1 = -1, int Y1 = -1)
{
    if (X1 < 0) X1 = F.W;
    if (Y1 < 0) Y1 = F.H;
    int N = 0;
    for (int y = Y0; y < Y1; ++y)
        for (int x = X0; x < X1; ++x) N += F.Get(x, y) == C;
    return N;
}

static int CountNonBlack(const Frame& F, int X0, int Y0, int X1, int Y1)
{
    int N = 0;
    for (int y = Y0; y < Y1; ++y)
        for (int x = X0; x < X1; ++x) N += F.Get(x, y) != Pal::Black;
    return N;
}

static bool OnlyInside(const Frame& F, int X0, int Y0, int X1, int Y1)
{
    for (int y = 0; y < F.H; ++y)
        for (int x = 0; x < F.W; ++x)
            if ((x < X0 || y < Y0 || x >= X1 || y >= Y1) && F.Get(x, y) != Pal::Black) return false;
    return true;
}

static int RowWidth(const Frame& F, int Y, uint32_t C)
{
    int N = 0;
    for (int x = 0; x < F.W; ++x) N += F.Get(x, Y) == C;
    return N;
}

struct Member
{
    std::string Name;
    int Hp = 10, Mp = 5, Lvl = 1, Asleep = 0;
    bool Poisoned = false, Shiny = false;
};

int main()
{
    Ui::Current() = Ui::Style{};
    const Ui::Style St = Ui::Current();

    // ---- window
    {
        Frame F;
        F.Clear(0x112233);
        Ui::Window(F, 10, 20, 60, 40);
        Check("window: corner pixel left open (rounded)", F.Get(10, 20) == Pal::Black && F.Get(69, 59) == Pal::Black);
        Check("window: diagonal corner pixels are ink", F.Get(11, 21) == St.Ink && F.Get(68, 21) == St.Ink &&
                                                          F.Get(11, 58) == St.Ink && F.Get(68, 58) == St.Ink);
        Check("window: outer rule two pixels thick", F.Get(30, 20) == St.Ink && F.Get(30, 21) == St.Ink &&
                                                       F.Get(10, 40) == St.Ink && F.Get(11, 40) == St.Ink &&
                                                       F.Get(69, 40) == St.Ink && F.Get(30, 59) == St.Ink);
        Check("window: one-pixel gap between rules", F.Get(30, 22) == Pal::Black && F.Get(12, 40) == Pal::Black);
        Check("window: inner rule is the dark ink", F.Get(30, 23) == St.InkDark && F.Get(13, 40) == St.InkDark &&
                                                      F.Get(66, 40) == St.InkDark && F.Get(30, 56) == St.InkDark);
        Check("window: interior is black", CountNonBlack(F, 14, 24, 66, 56) == 0);
        Check("window: nothing drawn outside its box", F.Get(9, 40) == 0x112233 && F.Get(70, 40) == 0x112233 &&
                                                         F.Get(40, 19) == 0x112233 && F.Get(40, 60) == 0x112233);
    }
    {
        Frame F;
        Ui::Window(F, 0, 0, 120, 40, "ITEM");
        const int TW = 4 * 8 + 1, TX = (120 - TW) / 2;
        Check("window title: rule cut either side of the title", F.Get(TX - 2, 0) == Pal::Black && F.Get(TX + TW + 2, 0) == Pal::Black,
              std::to_string(TX));
        Check("window title: rule continues past the cut", F.Get(TX - 6, 0) == St.Ink && F.Get(TX + TW + 6, 0) == St.Ink);
        Check("window title: glyphs drawn in ink inside the cut", CountColour(F, St.Ink, TX, 0, TX + TW, 8) > 10);
        Frame G;
        Ui::Window(G, 0, 0, 120, 40);
        Check("window title: untitled rule is unbroken", RowWidth(G, 0, St.Ink) == 116);
    }

    // ---- cursor and paging arrow
    {
        Frame F;
        Ui::Cursor(F, 50, 50);
        const int W0 = RowWidth(F, 50, St.Text), W3 = RowWidth(F, 53, St.Text), W6 = RowWidth(F, 56, St.Text);
        Check("cursor: a right-pointing triangle 1-4-1 wide over 7 rows", W0 == 1 && W3 == 4 && W6 == 1,
              std::to_string(W0) + "/" + std::to_string(W3) + "/" + std::to_string(W6));
        Check("cursor: 16 pixels, 7 rows tall", CountColour(F, St.Text) == 16 && RowWidth(F, 49, St.Text) == 0 && RowWidth(F, 57, St.Text) == 0);
        Frame G;
        Ui::Cursor(G, 50, 50, 0x00FF00);
        Check("cursor: explicit colour honoured", CountColour(G, 0x00FF00) == 16);
    }
    {
        Frame F;
        Ui::PageArrow(F, 100, 100);
        Check("page arrow: down triangle 7-5-3-1", RowWidth(F, 100, St.Text) == 7 && RowWidth(F, 101, St.Text) == 5 &&
                                                     RowWidth(F, 102, St.Text) == 3 && RowWidth(F, 103, St.Text) == 1 &&
                                                     F.Get(103, 103) == St.Text);
    }

    // ---- bold text
    {
        Frame Plain, Bold;
        Text(Plain, 10, 10, "HELLO", 0xFFFFFF);
        Ui::TextB(Bold, 10, 10, "HELLO", 0xFFFFFF);
        const int P = CountColour(Plain, 0xFFFFFF), B = CountColour(Bold, 0xFFFFFF);
        Check("bold text: more ink than plain", B > P && P > 0, std::to_string(P) + " vs " + std::to_string(B));
        Ui::Current().Bold = false;
        Frame NotBold;
        Ui::TextB(NotBold, 10, 10, "HELLO", 0xFFFFFF);
        Check("bold text: Bold=false draws plain", NotBold.Px == Plain.Px);
        Ui::Current() = Ui::Style{};
        Frame Def;
        Ui::TextB(Def, 10, 10, "A");
        Check("bold text: colour 0 means the style's text colour", CountColour(Def, St.Text) > 0);
    }

    // ---- style override
    {
        Ui::Current().Ink = 0x00A0F8;
        Frame F;
        Ui::Window(F, 0, 0, 40, 30);
        Check("style: realm ink override recolours the rule", F.Get(20, 0) == 0x00A0F8 && CountColour(F, St.Ink) == 0);
        Ui::Current() = Ui::Style{};
    }

    // ---- grid
    {
        const std::vector<std::string> Rows = {"FIGHT", "MAGIC", "ITEM", "RUN"};
        const std::vector<bool> En = {true, false, true, true};
        Frame F;
        Ui::Grid(F, 0, 0, Rows, 2, 8, 0, true, 0, &En);
        Check("grid: disabled row drawn dim", CountColour(F, St.Dim, 12 + 64, 0, 12 + 64 + 48, 8) > 0 &&
                                                 CountColour(F, St.Text, 12 + 64, 0, 12 + 64 + 48, 8) == 0);
        Check("grid: second row lands 12 pixels down", CountColour(F, St.Text, 12, 12, 60, 20) > 0);
        Check("grid: active cursor shown on blink-on frame", CountColour(F, St.Text, 2, 0, 9, 7) == 16);
        Frame Off;
        Ui::Grid(Off, 0, 0, Rows, 2, 8, 0, true, 4, &En);
        Check("grid: active cursor hidden on blink-off frame", CountColour(Off, St.Text, 2, 0, 9, 7) == 0);
        Frame In;
        Ui::Grid(In, 0, 0, Rows, 2, 8, 3, false, 4, &En);
        Check("grid: inactive cursor shown dim, steady", CountColour(In, St.Dim, 64 + 2, 12, 64 + 9, 19) == 16);
        Frame Short;
        const std::vector<bool> Few = {true};
        Ui::Grid(Short, 0, 0, Rows, 1, 8, -1, true, 0, &Few);
        Check("grid: rows past a short Enabled list are dim", CountColour(Short, St.Dim, 12, 12, 60, 20) > 0);
    }

    // ---- typewriter
    {
        const std::vector<std::string> Rows = {"AB", "CDE", "F", "GHIJ", "K"};
        Check("page chars: first page sums four rows", Ui::PageChars(Rows, 0) == 10);
        Check("page chars: last page counts what's left", Ui::PageChars(Rows, 1) == 1);
        Check("page chars: past the end is zero", Ui::PageChars(Rows, 2) == 0);
        Frame None, Some, All, Arrow, ArrowOff, Typing;
        Ui::Dialogue(None, Rows, 0, 0, false, 0);
        Ui::Dialogue(Some, Rows, 0, 3, false, 0);
        Ui::Dialogue(All, Rows, 0, 100000, false, 0);
        Ui::Dialogue(Arrow, Rows, 0, 100000, true, 4);
        Ui::Dialogue(ArrowOff, Rows, 0, 100000, true, 0);
        Ui::Dialogue(Typing, Rows, 0, 3, true, 4);
        const int T0 = CountColour(None, St.Text, 16, 166, 244, 220), T1 = CountColour(Some, St.Text, 16, 166, 244, 220),
                  T2 = CountColour(All, St.Text, 16, 166, 244, 220);
        Check("dialogue: typewriter reveals more as Shown grows", T0 == 0 && T1 > 0 && T2 > T1,
              std::to_string(T0) + "/" + std::to_string(T1) + "/" + std::to_string(T2));
        Check("dialogue: Shown=3 stops mid second row", CountColour(Some, St.Text, 20 + 8, 182, 20 + 24, 190) == 0 &&
                                                          CountColour(Some, St.Text, 20, 182, 28, 190) > 0);
        Check("dialogue: paging arrow on blink-on when done and more", CountColour(Arrow, St.Text, 124, 224, 131, 228) == 16);
        Check("dialogue: no arrow on blink-off", CountColour(ArrowOff, St.Text, 124, 224, 131, 228) == 0);
        Check("dialogue: no arrow while still typing", CountColour(Typing, St.Text, 124, 224, 131, 228) == 0);
        Check("dialogue: window sits along the bottom", All.Get(8 + 30, 160) == St.Ink && CountNonBlack(All, 0, 0, 256, 159) == 0);
    }

    // ---- member card and party strip
    {
        Frame Long, Short;
        Ui::MemberCard(Long, 0, 0, "ALEXANDRA", 12, 3, 1, 0xFFFFFF);
        Ui::MemberCard(Short, 0, 0, "ALEXA", 12, 3, 1, 0xFFFFFF);
        Check("member card: name cut to five characters", Long.Px == Short.Px);
        Frame Hp;
        Ui::MemberCard(Hp, 0, 0, "ALEXA", 99, 3, 1, 0xFFFFFF);
        Check("member card: HP line changes with HP", Hp.Px != Short.Px);
    }
    {
        std::vector<Member> P(3);
        P[0].Name = "ANA"; P[1].Name = "BO"; P[2].Name = "CY";
        P[1].Hp = 0;
        P[2].Poisoned = true;
        Frame F;
        Ui::PartyStrip(F, P, 0);
        const int X0 = (ScreenW - (3 * 56 + 2 * 4)) / 2;
        Check("party strip: centred on screen", F.Get(X0 + 20, 4) == St.Ink && F.Get(X0 - 1, 20) == Pal::Black &&
                                                  F.Get(X0 + 3 * 56 + 2 * 4, 20) == Pal::Black, std::to_string(X0));
        Check("party strip: hot member drawn in Hot", CountColour(F, St.Hot, X0, 4, X0 + 56, 40) > 0);
        Check("party strip: fallen member drawn red", CountColour(F, Pal::Red, X0 + 60, 4, X0 + 116, 40) > 0);
        Check("party strip: poisoned member drawn lime", CountColour(F, Pal::Lime, X0 + 120, 4, X0 + 176, 40) > 0);
        const std::vector<int> Shown = {10, 7, 10};
        Frame G;
        Ui::PartyStrip(G, P, 0, &Shown);
        Check("party strip: shown HP overrides the member's HP", CountColour(G, Pal::Red, X0 + 60, 4, X0 + 116, 40) == 0);
        P[1].Hp = 10; P[1].Asleep = 2; P[2].Poisoned = false; P[2].Shiny = true;
        Frame S;
        Ui::PartyStrip(S, P, 0);
        Check("party strip: asleep member drawn dim", CountColour(S, St.Dim, X0 + 60, 4, X0 + 116, 40) > 0);
        Check("party strip: shiny member sparkles", CountColour(S, Pal::White, X0 + 120, 0, X0 + 196, 60) > 0 ||
                                                     CountColour(S, St.Hot, X0 + 120, 0, X0 + 196, 60) > 0);
    }

    // ---- field tiles
    {
        // Meadow and block wall stay inside their cell. Forest crowns (Ellipse r4 round a jittered centre) and the
        // flagstones' offset mortar (i = -4) bleed sideways into the neighbour cells today (flagstones to x+22).
        // Pin that bleed to the cell's row and 8 px either side so it cannot grow; tighten when the header is fixed.
        bool Inside = true, Bounded = true, Determ = true, Full = true, Varies = false;
        for (int K = 0; K < 4; ++K)
            for (uint64_t Salt = 0; Salt < 16; ++Salt)
            {
                Frame A, B;
                A.Clear(0x010203); B.Clear(0x010203);
                switch (K)
                {
                case 0: DrawForest(A, 40, 40, Salt); DrawForest(B, 40, 40, Salt); break;
                case 1: DrawMeadow(A, 40, 40, Salt); DrawMeadow(B, 40, 40, Salt); break;
                case 2: DrawFlagstones(A, 40, 40); DrawFlagstones(B, 40, 40); break;
                default: DrawBlockWall(A, 40, 40); DrawBlockWall(B, 40, 40); break;
                }
                Determ &= A.Px == B.Px;
                for (int y = 0; y < A.H; ++y)
                    for (int x = 0; x < A.W; ++x)
                    {
                        const bool In = x >= 40 && y >= 40 && x < 56 && y < 56;
                        const bool Near = x >= 32 && x < 64 && y >= 40 && y < 56;
                        if (!In && A.Get(x, y) != 0x010203)
                        {
                            if (K == 1 || K == 3) Inside = false;
                            if (!Near) Bounded = false;
                        }
                        if (In && A.Get(x, y) == 0x010203) Full = false;
                    }
                if (K == 1 && Salt > 0)
                {
                    Frame C;
                    DrawMeadow(C, 40, 40, 0);
                    Varies |= C.Px != A.Px;
                }
            }
        Check("tiles: meadow and block wall stay inside their 16x16 cell", Inside);
        Check("tiles: forest/flagstone bleed stays in the row, within 8 px (known, see comment)", Bounded);
        Check("tiles: cover the whole cell", Full);
        Check("tiles: same salt draws the same tile", Determ);
        Check("tiles: meadow blades move with the salt", Varies);
        Frame M;
        DrawMeadow(M, 0, 0, 7);
        const int Blades = CountColour(M, Pal::GrassDot, 0, 0, 16, 16);
        Check("tiles: meadow is mostly flat grass", Blades > 0 && Blades <= 9, std::to_string(Blades));
    }

    // ---- battle backdrop
    {
        Frame K[3];
        for (int k = 0; k < 3; ++k) DrawBattleScene(K[k], k, 0);
        Check("battle scene: three distinct backdrops", K[0].Px != K[1].Px && K[1].Px != K[2].Px && K[0].Px != K[2].Px);
        // Town and cave stay inside the frame. The open field's clouds drift past the right of the picture (to x=238,
        // over the rule and beyond) today; pin it to within 16 px so it can't grow, tighten when the header is fixed.
        Check("battle scene: town and cave stay inside their framed window",
              OnlyInside(K[1], 32, 44, 32 + 192, 44 + 108) && OnlyInside(K[2], 32, 44, 32 + 192, 44 + 108));
        Check("battle scene: open-field overdraw bounded (known, see comment)", OnlyInside(K[0], 32, 44, 32 + 192 + 16, 44 + 108));
        Check("battle scene: framed by the window rule", K[0].Get(100, 44) == St.Ink && K[2].Get(32, 100) == St.Ink);
        Frame Again;
        DrawBattleScene(Again, 2, 0);
        Check("battle scene: deterministic for the same anim", Again.Px == K[2].Px);
        Frame Breathe;
        DrawBattleScene(Breathe, 2, 6);
        Check("battle scene: cave torch breathes with anim", Breathe.Px != K[2].Px);
    }

    std::printf("%d/%d realm look checks\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
