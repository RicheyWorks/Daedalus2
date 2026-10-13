// SPDX-License-Identifier: MIT

#pragma once

// The 8-bit realm's look (ADR-052, 2026-10-13 "lets work this realm"): the window kit and the field tiles that make
// it read like a late-80s console role-playing game. Original art: the shapes and colours are ours; only the genre's
// conventions are borrowed (black windows with a coloured double rule and rounded corners, a title cut into the top
// rule, a chunky 8-pixel font, a triangle cursor, dialogue in quotes with a paging arrow).
//
// Everything draws into DaedalusRealmDraw.h's Frame. Pure C++17, no Unreal: realm_core_test.cpp renders it headless.

#include "DaedalusRealmDraw.h"

namespace daedalus
{
namespace realm
{
namespace Ui
{

/** What a realm's windows look like. The spec may override Ink per realm ("ui" line, DaedalusRealmSpec). */
struct Style
{
    uint32_t Ink = 0xF8A070;      // the rule round every window: warm salmon on black
    uint32_t InkDark = 0xB05828;  // the inner, thinner rule
    uint32_t Text = 0xFCFCFC;
    uint32_t Dim = 0x9C9C9C;      // rows you can't pick
    uint32_t Hot = 0xF8D878;      // the party member whose turn it is
    bool Bold = true;             // glyphs one pixel wider: the chunky console look
};

inline Style& Current()
{
    static Style S;
    return S;
}

/** Bold text: each glyph drawn twice, one pixel apart, so strokes are two pixels wide. */
inline void TextB(Frame& F, int X, int Y, const std::string& S, uint32_t C = 0)
{
    const Style& St = Current();
    if (C == 0) C = St.Text;
    if (!St.Bold) { realm::Text(F, X, Y, S, C); return; }
    realm::Text(F, X, Y, S, C);
    realm::Text(F, X + 1, Y, S, C);
}

/** The triangle cursor, 7 pixels wide, pointing right. */
inline void Cursor(Frame& F, int X, int Y, uint32_t C = 0)
{
    if (C == 0) C = Current().Text;
    for (int j = 0; j < 7; ++j)
    {
        const int Half = j < 4 ? j : 6 - j;
        F.Rect(X, Y + j, Half + 1, 1, C);
    }
}

/** A shiny's sparkle: four-point stars that twinkle round a point (ADR-065's rare roll, seen at a glance). */
inline void Sparkle(Frame& F, int CX, int CY, int Anim)
{
    static const int Dx[6] = {-26, 24, -18, 20, 0, -8}, Dy[6] = {-20, -16, 14, 18, -30, 26};
    for (int k = 0; k < 6; ++k)
    {
        const int Ph = (Anim / 3 + k * 2) % 6;
        if (Ph > 3) continue;
        const int R = Ph == 0 ? 1 : Ph == 1 ? 3 : Ph == 2 ? 2 : 1;
        const uint32_t C = k % 2 ? Pal::White : Current().Hot;
        F.Rect(CX + Dx[k] - R, CY + Dy[k], 2 * R + 1, 1, C);
        F.Rect(CX + Dx[k], CY + Dy[k] - R, 1, 2 * R + 1, C);
    }
}

/** The paging arrow: a down triangle. */
inline void PageArrow(Frame& F, int X, int Y, uint32_t C = 0)
{
    if (C == 0) C = Current().Text;
    for (int j = 0; j < 4; ++j) F.Rect(X + j, Y + j, 7 - 2 * j, 1, C);
}

/**
 * A window: black inside, a 2-pixel outer rule with the corners rounded, a 1-pixel gap, a 1-pixel inner rule.
 * Title (optional) is cut into the top rule, centred, the way the genre labels its menus.
 */
inline void Window(Frame& F, int X, int Y, int W, int H, const std::string& Title = "")
{
    const Style& St = Current();
    F.Rect(X, Y, W, H, Pal::Black);
    // outer rule, 2 px, corners rounded by leaving the corner pixels black
    F.Rect(X + 2, Y, W - 4, 2, St.Ink);
    F.Rect(X + 2, Y + H - 2, W - 4, 2, St.Ink);
    F.Rect(X, Y + 2, 2, H - 4, St.Ink);
    F.Rect(X + W - 2, Y + 2, 2, H - 4, St.Ink);
    F.Set(X + 1, Y + 1, St.Ink); F.Set(X + W - 2, Y + 1, St.Ink);
    F.Set(X + 1, Y + H - 2, St.Ink); F.Set(X + W - 2, Y + H - 2, St.Ink);
    // inner rule, 1 px, one pixel in from the outer rule
    F.Rect(X + 4, Y + 3, W - 8, 1, St.InkDark);
    F.Rect(X + 4, Y + H - 4, W - 8, 1, St.InkDark);
    F.Rect(X + 3, Y + 4, 1, H - 8, St.InkDark);
    F.Rect(X + W - 4, Y + 4, 1, H - 8, St.InkDark);
    if (!Title.empty())
    {
        const int TW = static_cast<int>(Title.size()) * 8 + (St.Bold ? 1 : 0);
        const int TX = X + (W - TW) / 2;
        F.Rect(TX - 4, Y, TW + 8, 8, Pal::Black);   // the title cuts the rule
        TextB(F, TX, Y, Title, St.Ink);
    }
}

/** Rows in Cols columns with the cursor on Cursor's row/col. Cell width is in characters. Returns the row height. */
inline void Grid(Frame& F, int X, int Y, const std::vector<std::string>& Rows, int Cols, int CellChars, int Cursor,
                 bool Active, int Anim, const std::vector<bool>* Enabled = nullptr)
{
    const Style& St = Current();
    const int N = static_cast<int>(Rows.size());
    const int RowsN = (N + Cols - 1) / Cols;
    for (int i = 0; i < N; ++i)
    {
        const int R = i / Cols, C = i % Cols;
        const int CX = X + 12 + C * CellChars * 8, CY = Y + R * 12;
        const bool On = !Enabled || (static_cast<size_t>(i) < Enabled->size() && (*Enabled)[static_cast<size_t>(i)]);
        TextB(F, CX, CY, Rows[static_cast<size_t>(i)], On ? St.Text : St.Dim);
        if (i == Cursor)
        {
            if (Active) { if ((Anim / 4) % 2 == 0) Ui::Cursor(F, CX - 10, CY); }
            else Ui::Cursor(F, CX - 10, CY, St.Dim);
        }
    }
    (void)RowsN;
}

/** One party member's name window and, to its right, its H/M/L panel. */
inline void MemberCard(Frame& F, int X, int Y, const std::string& Name, int Hp, int Mp, int Lvl, uint32_t C)
{
    Window(F, X, Y, 56, 36);
    TextB(F, X + 8, Y + 6, Name.substr(0, 5), C);
    char B[32];
    std::snprintf(B, sizeof(B), "H%3d", Hp);
    TextB(F, X + 8, Y + 16, B, C);
    std::snprintf(B, sizeof(B), "M%3d", Mp);
    TextB(F, X + 8, Y + 26, B, C);
    (void)Lvl;
}

/** The party strip: one card per member, left to right along the top. */
template <typename MemberT>
inline void PartyStrip(Frame& F, const std::vector<MemberT>& Party, int Hot, const std::vector<int>* HpShown = nullptr)
{
    const Style& St = Current();
    const int N = static_cast<int>(Party.size());
    const int CardW = 56, Gap = 4;
    const int Total = N * CardW + (N - 1) * Gap;
    int X = (ScreenW - Total) / 2;
    for (int i = 0; i < N; ++i)
    {
        const MemberT& P = Party[static_cast<size_t>(i)];
        const int Hp = HpShown && static_cast<size_t>(i) < HpShown->size() ? (*HpShown)[static_cast<size_t>(i)] : P.Hp;
        uint32_t C = Hp <= 0 ? Pal::Red : P.Asleep > 0 ? St.Dim : P.Poisoned ? Pal::Lime : St.Text;
        if (i == Hot) C = St.Hot;
        MemberCard(F, X, 4, P.Name, Hp, P.Mp, P.Lvl, C);
        X += CardW + Gap;
    }
}

/**
 * The dialogue window along the bottom. Lines are shown up to Shown characters (the typewriter); a line that starts
 * with a quote mark is speech and keeps its quotes. More pages or a waiting close show the paging arrow.
 */
inline void Dialogue(Frame& F, const std::vector<std::string>& Rows, int Page, int Shown, bool More, int Anim)
{
    const Style& St = Current();
    Window(F, 8, 160, 240, 72);
    int Left = Shown;
    for (int k = 0; k < 4; ++k)
    {
        const size_t L = static_cast<size_t>(Page * 4 + k);
        if (L >= Rows.size() || Left <= 0) break;
        const std::string& Row = Rows[L];
        const std::string Part = Row.substr(0, static_cast<size_t>(std::max(0, std::min(Left, static_cast<int>(Row.size())))));
        TextB(F, 20, 170 + k * 12, Part, St.Text);
        Left -= static_cast<int>(Row.size());
    }
    if (More && Shown >= 100000 && (Anim / 4) % 2) PageArrow(F, 124, 224);
}

/** How many characters are on a page (for the typewriter's "done" test). */
inline int PageChars(const std::vector<std::string>& Rows, int Page)
{
    int N = 0;
    for (int k = 0; k < 4; ++k)
    {
        const size_t L = static_cast<size_t>(Page * 4 + k);
        if (L < Rows.size()) N += static_cast<int>(Rows[L].size());
    }
    return N;
}

} // namespace Ui

// ------------------------------------------------------------------------------------------ richer field tiles

/**
 * The forest tile the way the genre draws it: the whole cell is canopy, scalloped rows of dark leaf with a light
 * crown per bush, so a forest reads as a mass, not as lollipops on a lawn. Salt varies the crowns.
 */
inline void DrawForest(Frame& F, int X, int Y, uint64_t Salt)
{
    F.Rect(X, Y, 16, 16, Pal::TreeDark);
    // four round bushes in a 2x2 (a touch of jitter each), lit from the top-left, a black shadow line under each
    for (int by = 0; by < 2; ++by)
        for (int bx = 0; bx < 2; ++bx)
        {
            const int CX = X + 4 + bx * 8 + static_cast<int>(Mix(Salt + static_cast<uint64_t>(bx * 3 + by * 7)) % 2);
            const int CY = Y + 4 + by * 8;
            F.Ellipse(CX, CY, 4, 3, Pal::TreeLight);
            F.Rect(CX - 2, CY - 2, 2, 1, Pal::Lime); F.Set(CX - 3, CY - 1, Pal::Lime);
            F.Rect(CX - 3, CY + 3, 7, 1, Pal::Black);
            F.Set(CX + 3, CY + 2, Pal::TreeDark);
        }
}

/** Grass: a flat field with a few two-pixel blades, not confetti. */
inline void DrawMeadow(Frame& F, int X, int Y, uint64_t Salt)
{
    F.Rect(X, Y, 16, 16, Pal::Grass);
    for (int k = 0; k < 3; ++k)
    {
        const int GX = X + static_cast<int>(Mix(Salt * 31 + static_cast<uint64_t>(k)) % 14);
        const int GY = Y + static_cast<int>(Mix(Salt * 53 + static_cast<uint64_t>(k)) % 13);
        F.Set(GX, GY, Pal::GrassDot); F.Set(GX + 1, GY + 1, Pal::GrassDot); F.Set(GX + 1, GY, Pal::GrassDot);
    }
}

/** A town's stone path: light flags with dark mortar, offset every other row. */
inline void DrawFlagstones(Frame& F, int X, int Y)
{
    F.Rect(X, Y, 16, 16, Pal::StoneLo);
    for (int j = 0; j < 16; j += 8)
    {
        const int Off = (j / 8) % 2 ? 4 : 0;
        F.Rect(X, Y + j, 16, 1, Pal::CobbleDark);
        for (int i = -4; i < 16; i += 8) F.Rect(X + i + Off, Y + j, 1, 8, Pal::CobbleDark);
        for (int i = -4; i < 16; i += 8) F.Rect(X + i + Off + 1, Y + j + 1, 6, 1, Pal::StoneHi);
    }
}

/** A town wall: light blocks with black seams and a shadow line, the stone that rings a castle town. */
inline void DrawBlockWall(Frame& F, int X, int Y)
{
    F.Rect(X, Y, 16, 16, Pal::LightGrey);
    for (int j = 0; j < 16; j += 8)
    {
        const int Off = (j / 8) % 2 ? 8 : 0;
        F.Rect(X, Y + j, 16, 1, Pal::Black);
        F.Rect(X + Off, Y + j, 1, 8, Pal::Black);
        F.Rect(X + Off + 1, Y + j + 1, 7, 1, Pal::White);
        F.Rect(X + Off + 1, Y + j + 6, 7, 1, Pal::Grey);
    }
}

/**
 * The battle backdrop: a framed picture of where the fight is. 0 = open field (sky bands, far hills, a sun), 1 = a
 * town street (walls, flagstones), 2 = a cave (rock, stalactites, a torch glow). The frame is the realm's window rule.
 */
inline void DrawBattleScene(Frame& F, int Kind, int Anim)
{
    const int X = 36, Y = 48, W = 184, H = 100;
    Ui::Window(F, X - 4, Y - 4, W + 8, H + 8);
    const int IX = X, IY = Y, IW = W, IH = H;
    if (Kind == 2)
    {
        F.Rect(IX, IY, IW, IH, Pal::CaveWall);
        for (int k = 0; k < 7; ++k) F.Tri(IX + 12 + k * 27, IY, 7, -(12 + (k % 3) * 5), Pal::CaveWallHi);
        for (int k = 0; k < 7; ++k) F.Tri(IX + 12 + k * 27, IY, 5, -(8 + (k % 3) * 4), Pal::CaveWall);
        F.Rect(IX, IY + IH - 28, IW, 28, Pal::CaveFloor);
        for (int i = 0; i < IW; i += 5) if ((i / 5) % 3 == 0) F.Set(IX + i, IY + IH - 20 + (i / 7) % 6, Pal::CaveDot);
        // a torch glow breathes on the wall
        const int R = 22 + (Anim / 6) % 2;
        F.Ellipse(IX + 30, IY + 40, R, R / 2, 0x5C4030);
        F.Ellipse(IX + 30, IY + 40, R / 2, R / 4, 0x8C6040);
        return;
    }
    // sky in three bands, lighter toward the horizon
    F.Rect(IX, IY, IW, IH, 0x3878F8);
    F.Rect(IX, IY + 26, IW, 20, 0x58A0F8);
    F.Rect(IX, IY + 46, IW, 14, 0x90C8F8);
    F.Ellipse(IX + 150, IY + 16, 8, 8, Pal::Gold);
    for (int k = 0; k < 3; ++k) { const int CX = IX + 24 + k * 60 + (Anim / 20) % 4; F.Ellipse(CX, IY + 20, 12, 4, Pal::White); F.Ellipse(CX + 8, IY + 18, 8, 4, Pal::White); }
    if (Kind == 1)
    {
        F.Rect(IX, IY + 36, IW, 36, Pal::LightGrey);     // a town wall across the back
        for (int j = 0; j < 36; j += 9) { F.Rect(IX, IY + 36 + j, IW, 1, Pal::Black); for (int i = (j / 9) % 2 * 9; i < IW; i += 18) F.Rect(IX + i, IY + 36 + j, 1, 9, Pal::Black); }
        F.Rect(IX, IY + 72, IW, 28, Pal::StoneLo);
        for (int j = 0; j < 28; j += 7) F.Rect(IX, IY + 72 + j, IW, 1, Pal::CobbleDark);
        for (int i = 0; i < IW; i += 14) F.Rect(IX + i, IY + 72, 1, 28, Pal::CobbleDark);
        return;
    }
    // far mountains, near hills, the field
    for (int k = 0; k < 5; ++k) F.Tri(IX + 20 + k * 40, IY + 62, 22, 26 + (k % 2) * 8, Pal::Rock);
    for (int k = 0; k < 5; ++k) F.Tri(IX + 20 + k * 40, IY + 62 - 26 - (k % 2) * 8 + 10, 5, 10, Pal::Snow);
    for (int k = 0; k < 4; ++k) F.Ellipse(IX + 30 + k * 45, IY + 66, 30, 10, Pal::HillDark);
    for (int k = 0; k < 4; ++k) F.Ellipse(IX + 30 + k * 45, IY + 68, 22, 6, Pal::Hill);
    F.Rect(IX, IY + 70, IW, 30, Pal::Grass);
    for (int i = 0; i < IW; i += 6) if ((i / 6) % 2 == 0) { F.Set(IX + i, IY + 78 + (i / 3) % 9, Pal::GrassDot); F.Set(IX + i + 1, IY + 79 + (i / 3) % 9, Pal::GrassDot); }
}

} // namespace realm
} // namespace daedalus
