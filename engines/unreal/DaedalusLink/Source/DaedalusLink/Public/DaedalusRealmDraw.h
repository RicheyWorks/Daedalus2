// SPDX-License-Identifier: MIT
//
// DaedalusRealmDraw.h: the 8-bit realm's screen (ADR-052): a 256x240 frame, an NES-ish palette, an original 5x7
// font, and every tile, person and monster drawn pixel by pixel from shapes and tiny bitmaps. No art is loaded, so
// the realm looks the same in Unreal, in a command-line test, or anywhere this compiles. Standard C++17.

#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus
{
namespace realm
{

constexpr int ScreenW = 256;
constexpr int ScreenH = 240;
constexpr int TileSize = 16;

/** The realm's tiles. Each but ChestOpen has the character the Java engines write in the spec (RetroTile). */
enum class Tile : uint8_t
{
    Grass, Tree, Water, Hill, Mountain, Sand, Bridge, Swamp, Cobble, Stone, Brick, Door, Locked, Chest, StairsDown,
    StairsUp, Town, Castle, Cave, Portal, Throne, Carpet, Counter, Floor, Wall, ChestOpen, Count
};

inline const char* TileChars() { return ".T~h^:=%,#bDLC><VKAOQ|-_Wc"; }

inline bool TileFromChar(char C, Tile& Out)
{
    const char* S = TileChars();
    for (int i = 0; S[i]; ++i)
        if (S[i] == C) { Out = static_cast<Tile>(i); return true; }
    return false;
}

inline bool Walkable(Tile T)
{
    switch (T)
    {
    case Tile::Water: case Tile::Mountain: case Tile::Stone: case Tile::Locked: case Tile::Chest: case Tile::Throne:
    case Tile::Counter: case Tile::Wall: case Tile::ChestOpen:
        return false;
    default:
        return true;
    }
}

// ------------------------------------------------------------------------------------------------- utilities

/** xorshift64*: small, fast, and the same everywhere. */
struct Rng
{
    uint64_t S;
    explicit Rng(uint64_t Seed = 1) : S(Seed ? Seed : 0x9E3779B97F4A7C15ull) {}
    uint64_t Next()
    {
        S ^= S >> 12; S ^= S << 25; S ^= S >> 27;
        return S * 0x2545F4914F6CDD1Dull;
    }
    /** Lo..Hi inclusive. */
    int Range(int Lo, int Hi) { return Hi <= Lo ? Lo : Lo + static_cast<int>(Next() % static_cast<uint64_t>(Hi - Lo + 1)); }
    bool Chance(int OneIn) { return OneIn > 0 && Next() % static_cast<uint64_t>(OneIn) == 0; }
};

inline uint64_t Mix(uint64_t Z)
{
    Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
    Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
    return Z ^ (Z >> 31);
}

// --------------------------------------------------------------------------------------------- the screen

/** The palette: an NES-ish set, chosen for this realm. 0xRRGGBB. */
namespace Pal
{
constexpr uint32_t Black = 0x000000, White = 0xFCFCFC, Grey = 0x7C7C7C, LightGrey = 0xBCBCBC, DarkGrey = 0x3C3C3C;
constexpr uint32_t Grass = 0x80D010, GrassDot = 0x40A000, TreeDark = 0x007800, TreeLight = 0x38B818, Trunk = 0x7C4C14;
constexpr uint32_t Water = 0x2858F8, WaterLight = 0x7CA8FC, Sand = 0xF0D090, SandDot = 0xC8A050;
constexpr uint32_t Hill = 0x58C838, HillDark = 0x2C8C18, Rock = 0x9C9C9C, Snow = 0xF8F8F8;
constexpr uint32_t Cobble = 0x8C7C6C, CobbleDark = 0x5C4C40, StoneHi = 0xE8E8E8, StoneLo = 0xA0A0A8;
constexpr uint32_t Brick = 0xC84C0C, BrickDark = 0x881400, Mortar = 0xE09060;
constexpr uint32_t Wood = 0xA0581C, WoodDark = 0x603008, Gold = 0xF8B800, Red = 0xD82800, Purple = 0x8C34C8;
constexpr uint32_t Cyan = 0x3CE0E0, Teal = 0x008888, Skin = 0xFCB894, Orange = 0xF87818, Blue = 0x0058F8;
constexpr uint32_t NavyBlue = 0x0028A0, Pink = 0xF878C8, Lime = 0xB8F818, Slime = 0x58D840, SlimeDark = 0x188C10;
constexpr uint32_t Bog = 0x506030, BogDark = 0x304018, CaveFloor = 0x6C5840, CaveDot = 0x4C3C2C, CaveWall = 0x302820;
constexpr uint32_t CaveWallHi = 0x5C4C3C, Silver = 0xD8D8E8;
}

/** Darken a colour (for shading the accent side of a palette swap). */
inline uint32_t Shade(uint32_t C, int Num, int Den)
{
    const uint32_t R = ((C >> 16) & 255) * static_cast<uint32_t>(Num) / static_cast<uint32_t>(Den);
    const uint32_t G = ((C >> 8) & 255) * static_cast<uint32_t>(Num) / static_cast<uint32_t>(Den);
    const uint32_t B = (C & 255) * static_cast<uint32_t>(Num) / static_cast<uint32_t>(Den);
    return (std::min(R, 255u) << 16) | (std::min(G, 255u) << 8) | std::min(B, 255u);
}

class Frame
{
public:
    int W = ScreenW, H = ScreenH;
    std::vector<uint32_t> Px;
    Frame(int InW = ScreenW, int InH = ScreenH) : W(InW), H(InH), Px(static_cast<size_t>(InW * InH), Pal::Black) {}
    void Clear(uint32_t C) { std::fill(Px.begin(), Px.end(), C); }
    void Set(int X, int Y, uint32_t C)
    {
        if (X >= 0 && Y >= 0 && X < W && Y < H) Px[static_cast<size_t>(Y * W + X)] = C;
    }
    uint32_t Get(int X, int Y) const { return (X >= 0 && Y >= 0 && X < W && Y < H) ? Px[static_cast<size_t>(Y * W + X)] : 0; }
    void Rect(int X, int Y, int RW, int RH, uint32_t C)
    {
        for (int j = 0; j < RH; ++j) for (int i = 0; i < RW; ++i) Set(X + i, Y + j, C);
    }
    void Ellipse(int CX, int CY, int RX, int RY, uint32_t C)
    {
        if (RX <= 0 || RY <= 0) return;
        for (int j = -RY; j <= RY; ++j)
            for (int i = -RX; i <= RX; ++i)
                if ((i * i) * RY * RY + (j * j) * RX * RX <= RX * RX * RY * RY) Set(CX + i, CY + j, C);
    }
    /** A filled triangle, apex up when Ht > 0 (down when negative). */
    void Tri(int CX, int Base, int Half, int Ht, uint32_t C)
    {
        const int N = std::abs(Ht);
        for (int j = 0; j < N; ++j)
        {
            const int HalfW = Half * (N - j) / N;
            const int Y = Ht > 0 ? Base - j : Base + j;
            for (int i = -HalfW; i <= HalfW; ++i) Set(CX + i, Y, C);
        }
    }
    /** Draw Ink around everything that is not Bg inside a box: the NES black edge. */
    void Outline(int X, int Y, int BW, int BH, uint32_t Bg, uint32_t Ink)
    {
        std::vector<uint8_t> Mask(static_cast<size_t>(BW * BH));
        for (int j = 0; j < BH; ++j) for (int i = 0; i < BW; ++i) Mask[static_cast<size_t>(j * BW + i)] = Get(X + i, Y + j) != Bg;
        for (int j = 0; j < BH; ++j)
            for (int i = 0; i < BW; ++i)
            {
                if (Mask[static_cast<size_t>(j * BW + i)]) continue;
                const bool Edge = (i > 0 && Mask[static_cast<size_t>(j * BW + i - 1)]) || (i + 1 < BW && Mask[static_cast<size_t>(j * BW + i + 1)])
                    || (j > 0 && Mask[static_cast<size_t>((j - 1) * BW + i)]) || (j + 1 < BH && Mask[static_cast<size_t>((j + 1) * BW + i)]);
                if (Edge) Set(X + i, Y + j, Ink);
            }
    }
    /** A message window: black, a white border two pixels in, rounded corners. */
    void Window(int X, int Y, int WW, int WH)
    {
        Rect(X, Y, WW, WH, Pal::Black);
        Rect(X + 2, Y + 3, WW - 4, 2, Pal::White);
        Rect(X + 2, Y + WH - 5, WW - 4, 2, Pal::White);
        Rect(X + 3, Y + 2, 2, WH - 4, Pal::White);
        Rect(X + WW - 5, Y + 2, 2, WH - 4, Pal::White);
        Set(X + 3, Y + 3, Pal::Black); Set(X + WW - 4, Y + 3, Pal::Black);
        Set(X + 3, Y + WH - 4, Pal::Black); Set(X + WW - 4, Y + WH - 4, Pal::Black);
    }
    /** Copy Src onto this frame at (X, Y), skipping Key-coloured pixels. */
    void Blit(const Frame& Src, int X, int Y, uint32_t Key)
    {
        for (int j = 0; j < Src.H; ++j)
            for (int i = 0; i < Src.W; ++i)
            {
                const uint32_t C = Src.Get(i, j);
                if (C != Key) Set(X + i, Y + j, C);
            }
    }
    /** Copy Src shrunk by Factor (nearest pixel), skipping Key. */
    void BlitSmall(const Frame& Src, int X, int Y, int Factor, uint32_t Key)
    {
        for (int j = 0; j < Src.H / Factor; ++j)
            for (int i = 0; i < Src.W / Factor; ++i)
            {
                uint32_t C = Key;
                for (int b = 0; b < Factor && C == Key; ++b)   // take any non-key pixel in the block so thin parts survive
                    for (int a = 0; a < Factor && C == Key; ++a) C = Src.Get(i * Factor + a, j * Factor + b);
                if (C != Key) Set(X + i, Y + j, C);
            }
    }
};

// ------------------------------------------------------------------------------------------------ the font

/** 5x7 glyphs (one row per byte, bit 4 = left), drawn in 8x8 cells. Original, made for this realm. */
inline const uint8_t* Glyph(char Ch)
{
    struct G { char C; uint8_t R[7]; };
    static const G Font[] = {
        {'A', {14, 17, 17, 31, 17, 17, 17}}, {'B', {30, 17, 17, 30, 17, 17, 30}}, {'C', {14, 17, 16, 16, 16, 17, 14}},
        {'D', {30, 17, 17, 17, 17, 17, 30}}, {'E', {31, 16, 16, 30, 16, 16, 31}}, {'F', {31, 16, 16, 30, 16, 16, 16}},
        {'G', {14, 17, 16, 23, 17, 17, 15}}, {'H', {17, 17, 17, 31, 17, 17, 17}}, {'I', {14, 4, 4, 4, 4, 4, 14}},
        {'J', {7, 2, 2, 2, 2, 18, 12}}, {'K', {17, 18, 20, 24, 20, 18, 17}}, {'L', {16, 16, 16, 16, 16, 16, 31}},
        {'M', {17, 27, 21, 21, 17, 17, 17}}, {'N', {17, 25, 21, 19, 17, 17, 17}}, {'O', {14, 17, 17, 17, 17, 17, 14}},
        {'P', {30, 17, 17, 30, 16, 16, 16}}, {'Q', {14, 17, 17, 17, 21, 18, 13}}, {'R', {30, 17, 17, 30, 20, 18, 17}},
        {'S', {15, 16, 16, 14, 1, 1, 30}}, {'T', {31, 4, 4, 4, 4, 4, 4}}, {'U', {17, 17, 17, 17, 17, 17, 14}},
        {'V', {17, 17, 17, 17, 17, 10, 4}}, {'W', {17, 17, 17, 21, 21, 21, 10}}, {'X', {17, 17, 10, 4, 10, 17, 17}},
        {'Y', {17, 17, 10, 4, 4, 4, 4}}, {'Z', {31, 1, 2, 4, 8, 16, 31}},
        {'0', {14, 17, 19, 21, 25, 17, 14}}, {'1', {4, 12, 4, 4, 4, 4, 14}}, {'2', {14, 17, 1, 2, 4, 8, 31}},
        {'3', {30, 1, 1, 14, 1, 1, 30}}, {'4', {2, 6, 10, 18, 31, 2, 2}}, {'5', {31, 16, 30, 1, 1, 17, 14}},
        {'6', {6, 8, 16, 30, 17, 17, 14}}, {'7', {31, 1, 2, 4, 8, 8, 8}}, {'8', {14, 17, 17, 14, 17, 17, 14}},
        {'9', {14, 17, 17, 15, 1, 2, 12}}, {'.', {0, 0, 0, 0, 0, 12, 12}}, {',', {0, 0, 0, 0, 12, 4, 8}},
        {'!', {4, 4, 4, 4, 4, 0, 4}}, {'?', {14, 17, 1, 2, 4, 0, 4}}, {'\'', {4, 4, 8, 0, 0, 0, 0}},
        {'-', {0, 0, 0, 31, 0, 0, 0}}, {':', {0, 12, 12, 0, 12, 12, 0}}, {'/', {1, 1, 2, 4, 8, 16, 16}},
        {'>', {8, 12, 14, 15, 14, 12, 8}}, {'+', {0, 4, 4, 31, 4, 4, 0}}, {'*', {0, 21, 14, 31, 14, 21, 0}},
        {'(', {2, 4, 8, 8, 8, 4, 2}}, {')', {8, 4, 2, 2, 2, 4, 8}}, {'&', {12, 18, 20, 8, 21, 18, 13}},
        {'=', {0, 0, 31, 0, 31, 0, 0}}, {'#', {10, 31, 10, 10, 31, 10, 0}}, {'"', {10, 10, 0, 0, 0, 0, 0}},
    };
    for (const G& F : Font) if (F.C == Ch) return F.R;
    return nullptr;
}

inline void Text(Frame& F, int X, int Y, const std::string& S, uint32_t C = Pal::White)
{
    int CX = X;
    for (char Ch : S)
    {
        if (Ch == '\n') { CX = X; Y += 10; continue; }
        const char U = (Ch >= 'a' && Ch <= 'z') ? static_cast<char>(Ch - 32) : Ch;
        if (const uint8_t* R = Glyph(U))
            for (int j = 0; j < 7; ++j)
                for (int i = 0; i < 5; ++i)
                    if (R[j] & (16 >> i)) F.Set(CX + i, Y + j, C);
        CX += 8;
    }
}

/** Word-wrap to Width characters a line; existing newlines are kept. */
inline std::vector<std::string> Wrap(const std::string& S, size_t Width)
{
    std::vector<std::string> Out;
    std::string Para;
    auto Flush = [&](const std::string& P) {
        std::string Line;
        size_t i = 0;
        while (i <= P.size())
        {
            size_t j = P.find(' ', i);
            if (j == std::string::npos) j = P.size();
            const std::string Word = P.substr(i, j - i);
            if (!Line.empty() && Line.size() + 1 + Word.size() > Width) { Out.push_back(Line); Line.clear(); }
            if (!Line.empty()) Line += ' ';
            Line += Word;
            while (Line.size() > Width) { Out.push_back(Line.substr(0, Width)); Line = Line.substr(Width); }
            i = j + 1;
        }
        Out.push_back(Line);
    };
    for (char C : S)
    {
        if (C == '\n') { Flush(Para); Para.clear(); }
        else Para += C;
    }
    if (!Para.empty()) Flush(Para);
    return Out;
}

// ------------------------------------------------------------------------------------------------- the tiles

/** Draws one 16x16 tile. Tier colours a lock (1 bronze, 2 silver, 3 star); Anim drives water and the portal. */
inline void DrawTile(Frame& F, int X, int Y, Tile T, uint64_t Salt, int Anim, int Tier = 1)
{
    auto Dots = [&](uint32_t Base, uint32_t Dot, int Every) {
        F.Rect(X, Y, 16, 16, Base);
        for (int j = 0; j < 16; ++j)
            for (int i = 0; i < 16; ++i)
                if (Mix(Salt * 977 + static_cast<uint64_t>(j * 16 + i)) % static_cast<uint64_t>(Every) == 0) F.Set(X + i, Y + j, Dot);
    };
    auto Floor = [&]() {
        F.Rect(X, Y, 16, 16, Pal::CaveFloor);
        for (int j = 0; j < 16; ++j)
            for (int i = 0; i < 16; ++i)
                if (Mix(Salt * 131 + static_cast<uint64_t>(j * 16 + i)) % 9 == 0) F.Set(X + i, Y + j, Pal::CaveDot);
    };
    switch (T)
    {
    case Tile::Grass: Dots(Pal::Grass, Pal::GrassDot, 13); break;
    case Tile::Tree:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Rect(X + 7, Y + 11, 3, 4, Pal::Trunk);
        F.Ellipse(X + 8, Y + 7, 6, 5, Pal::TreeDark);
        F.Ellipse(X + 7, Y + 6, 3, 2, Pal::TreeLight);
        F.Set(X + 11, Y + 8, Pal::TreeLight);
        F.Outline(X, Y, 16, 16, Pal::Grass, Pal::Black);
        break;
    case Tile::Water:
        F.Rect(X, Y, 16, 16, Pal::Water);
        for (int k = 0; k < 2; ++k)
        {
            const int WY = Y + 4 + k * 8, Off = (Anim + k * 3) % 8;
            for (int i = 0; i < 5; ++i) F.Set(X + ((Off + i + k * 6) % 16), WY + (i == 2 ? -1 : 0), Pal::WaterLight);
        }
        break;
    case Tile::Bridge:
        F.Rect(X, Y, 16, 16, Pal::Water);
        F.Rect(X, Y + 2, 16, 12, Pal::Wood);
        for (int i = 0; i < 16; i += 4) F.Rect(X + i, Y + 2, 1, 12, Pal::WoodDark);
        break;
    case Tile::Sand: Dots(Pal::Sand, Pal::SandDot, 11); break;
    case Tile::Swamp:
    {
        // marsh: a still dark pool with a lighter rim, reeds along two edges, a bubble that comes and goes
        F.Rect(X, Y, 16, 16, Pal::Bog);
        const int PX2 = X + 4 + static_cast<int>(Mix(Salt) % 4), PY2 = Y + 6 + static_cast<int>(Mix(Salt * 3) % 4);
        F.Ellipse(PX2 + 3, PY2 + 2, 6, 3, Pal::BogDark);
        F.Ellipse(PX2 + 3, PY2 + 2, 4, 2, 0x203818);
        for (int k = 0; k < 3; ++k)
        {
            const int RX = X + 1 + k * 5 + static_cast<int>(Mix(Salt + static_cast<uint64_t>(k) * 7) % 3);
            F.Rect(RX, Y + 1, 1, 4, Pal::HillDark); F.Set(RX, Y + 1, Pal::Lime);
            F.Rect(RX + 2, Y + 11, 1, 4, Pal::HillDark); F.Set(RX + 2, Y + 11, Pal::Lime);
        }
        if ((Anim / 6 + static_cast<int>(Salt % 7)) % 4 == 0) F.Set(PX2 + 2, PY2 + 1, Pal::LightGrey);
        break;
    }
    case Tile::Hill:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Ellipse(X + 8, Y + 11, 7, 5, Pal::Hill);
        F.Ellipse(X + 6, Y + 9, 3, 2, Pal::Lime);
        F.Rect(X + 1, Y + 14, 14, 2, Pal::Grass);
        F.Outline(X, Y, 16, 15, Pal::Grass, Pal::HillDark);
        break;
    case Tile::Mountain:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Tri(X + 8, Y + 14, 7, 12, Pal::Rock);
        F.Tri(X + 8, Y + 6, 3, 5, Pal::Snow);
        for (int j = 0; j < 8; ++j) F.Set(X + 8 + j / 2, Y + 7 + j, Pal::Grey);
        F.Outline(X, Y, 16, 16, Pal::Grass, Pal::Black);
        break;
    case Tile::Cobble:
        F.Rect(X, Y, 16, 16, Pal::Cobble);
        for (int j = 0; j < 16; j += 4)
            for (int i = ((j / 4) % 2) * 3; i < 16; i += 6) F.Rect(X + i, Y + j, 1, 3, Pal::CobbleDark);
        for (int j = 3; j < 16; j += 4) F.Rect(X, Y + j, 16, 1, Pal::CobbleDark);
        break;
    case Tile::Brick:
        F.Rect(X, Y, 16, 16, Pal::Brick);
        for (int j = 3; j < 16; j += 4) F.Rect(X, Y + j, 16, 1, Pal::BrickDark);
        for (int r = 0; r < 4; ++r)
            for (int i = (r % 2) * 4; i < 16; i += 8) F.Rect(X + i, Y + r * 4, 1, 3, Pal::Mortar);
        break;
    case Tile::Stone:
        F.Rect(X, Y, 16, 16, Pal::StoneLo);
        F.Rect(X + 1, Y + 1, 14, 13, Pal::StoneHi);
        F.Rect(X + 1, Y + 14, 15, 2, Pal::Grey);
        F.Rect(X + 14, Y + 1, 2, 15, Pal::Grey);
        break;
    case Tile::Door: case Tile::Locked:
    {
        F.Rect(X, Y, 16, 16, Pal::StoneLo);
        const uint32_t Leaf = T == Tile::Door ? Pal::Wood : Tier >= 3 ? Pal::Purple : Tier == 2 ? Pal::Grey : Pal::WoodDark;
        F.Rect(X + 3, Y + 4, 10, 12, Leaf);
        F.Ellipse(X + 8, Y + 5, 5, 3, Leaf);
        F.Rect(X + 8, Y + 3, 1, 13, Pal::Black);
        if (T == Tile::Locked)
        {
            const uint32_t Lock = Tier >= 3 ? Pal::Gold : Tier == 2 ? Pal::Silver : Pal::Orange;
            F.Rect(X + 6, Y + 8, 5, 5, Lock);
            F.Rect(X + 7, Y + 6, 3, 2, Lock);
            F.Set(X + 8, Y + 10, Pal::Black);
            if (Tier >= 3) { F.Set(X + 4, Y + 6, Pal::White); F.Set(X + 12, Y + 13, Pal::White); }
        }
        else F.Set(X + 10, Y + 10, Pal::Gold);
        break;
    }
    case Tile::Chest: case Tile::ChestOpen:
        F.Rect(X, Y, 16, 16, Pal::Black);
        F.Rect(X + 2, Y + 5, 12, 9, Pal::Wood);
        F.Rect(X + 2, Y + 8, 12, 1, Pal::WoodDark);
        F.Rect(X + 2, Y + 5, 1, 9, Pal::Gold); F.Rect(X + 13, Y + 5, 1, 9, Pal::Gold);
        if (T == Tile::Chest) F.Rect(X + 7, Y + 8, 2, 3, Pal::Gold);
        else F.Rect(X + 3, Y + 6, 10, 2, Pal::Black);
        break;
    case Tile::StairsDown: case Tile::StairsUp:
        F.Rect(X, Y, 16, 16, Pal::DarkGrey);
        for (int k = 0; k < 4; ++k)
        {
            const int Step = T == Tile::StairsDown ? k : 3 - k;
            F.Rect(X + Step * 3, Y + 2 + k * 3, 16 - Step * 3, 2, Pal::StoneHi);
        }
        break;
    case Tile::Town:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        for (int k = 0; k < 2; ++k)
        {
            const int HX = X + 1 + k * 8, HY = Y + 4 + k * 4;
            F.Rect(HX, HY + 3, 7, 5, Pal::StoneHi);
            F.Tri(HX + 3, HY + 3, 4, 4, Pal::Red);
            F.Rect(HX + 3, HY + 5, 1, 3, Pal::Wood);
        }
        F.Outline(X, Y, 16, 16, Pal::Grass, Pal::Black);
        break;
    case Tile::Castle:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Rect(X + 2, Y + 6, 12, 9, Pal::StoneLo);
        F.Rect(X + 1, Y + 3, 4, 12, Pal::StoneHi);
        F.Rect(X + 11, Y + 3, 4, 12, Pal::StoneHi);
        F.Rect(X + 6, Y + 10, 4, 5, Pal::Black);
        F.Set(X + 3, Y + 1, Pal::Red); F.Set(X + 3, Y + 2, Pal::Red);
        F.Outline(X, Y, 16, 16, Pal::Grass, Pal::Black);
        break;
    case Tile::Cave:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Tri(X + 8, Y + 15, 8, 13, Pal::Rock);
        F.Ellipse(X + 8, Y + 12, 4, 4, Pal::Black);
        F.Rect(X + 4, Y + 12, 9, 4, Pal::Black);
        F.Outline(X, Y, 16, 16, Pal::Grass, Pal::DarkGrey);
        break;
    case Tile::Portal:
        Dots(Pal::Grass, Pal::GrassDot, 13);
        F.Ellipse(X + 8, Y + 8, 6, 7, Pal::Purple);
        F.Ellipse(X + 8, Y + 8, 4, 5, (Anim / 2) % 2 ? Pal::Cyan : Pal::Teal);
        F.Ellipse(X + 8, Y + 8, 2, 2, Pal::White);
        break;
    case Tile::Throne:
        F.Rect(X, Y, 16, 16, Pal::Red);
        F.Rect(X + 3, Y + 1, 10, 14, Pal::Gold);
        F.Rect(X + 5, Y + 4, 6, 8, Pal::Purple);
        break;
    case Tile::Carpet:
        F.Rect(X, Y, 16, 16, Pal::Red);
        F.Rect(X, Y, 1, 16, Pal::Gold); F.Rect(X + 15, Y, 1, 16, Pal::Gold);
        break;
    case Tile::Counter:
        DrawTile(F, X, Y, Tile::Brick, Salt, Anim);
        F.Rect(X, Y + 3, 16, 10, Pal::Wood);
        F.Rect(X, Y + 3, 16, 2, Pal::Mortar);
        F.Rect(X, Y + 12, 16, 1, Pal::WoodDark);
        break;
    case Tile::Floor: Floor(); break;
    case Tile::Wall:
        F.Rect(X, Y, 16, 16, Pal::CaveWall);
        for (int r = 0; r < 4; ++r)
            for (int i = (r % 2) * 4; i < 16; i += 8)
            {
                F.Rect(X + i + 1, Y + r * 4 + 1, 6, 2, Pal::CaveWallHi);
                F.Set(X + i, Y + r * 4 + 3, Pal::Black);
            }
        break;
    default:
        F.Rect(X, Y, 16, 16, Pal::Black);
        break;
    }
}

// ------------------------------------------------------------------------------------------------ the people

/** A 16x16 person from a template; Look sets hair, top, legs, a pointed hat and a cape (0 = none). */
struct Look
{
    uint32_t Hair = 0x7C4C14, Top = Pal::Teal, Legs = Pal::NavyBlue, Hat = 0, Cape = 0;
};

inline void DrawPerson(Frame& F, int X, int Y, const Look& L, int Facing /*0 down 1 up 2 left 3 right*/, int Step)
{
    // Rows of 16: K outline, S skin, H hair, T top, P legs, B boots, E eye.
    static const char* Front[16] = {
        "................", ".....KKKKKK.....", "....KHHHHHHK....", "...KHHHHHHHHK...",
        "...KHSSSSSSHK...", "...KSESSSSESK...", "...KSSSSSSSSK...", "....KSSSSSSK....",
        "...KTTKSSKTTK...", "..KTTTTTTTTTTK..", "..KSKTTTTTTKSK..", "..KSKTTKKTTKSK..",
        "...KKPPPPPPKK...", "....KPPKKPPK....", "....KBBK.KBBK...", "....KKK...KKK...",
    };
    static const char* Side[16] = {   // facing left; mirrored for right
        "................", "......KKKKK.....", ".....KHHHHHK....", "....KHHHHHHHK...",
        "....KSSHHHHHK...", "...KSESSHHHHK...", "...KSSSSSHHK....", "....KSSSSSK.....",
        ".....KTTTTK.....", "....KTTTTTTK....", "....KTSSTTTK....", "....KTSSTTTK....",
        ".....KPPPPK.....", ".....KPPKPK.....", "....KBBK.KBK....", "....KKK...KK....",
    };
    const bool Back = Facing == 1;
    const bool Sideways = Facing == 2 || Facing == 3;
    for (int j = 0; j < 16; ++j)
        for (int i = 0; i < 16; ++i)
        {
            const int SI = Facing == 3 ? 15 - i : i;
            char C = Sideways ? Side[j][SI] : Front[j][i];
            if (Back && (C == 'S' || C == 'E') && j >= 4 && j <= 7) C = 'H';
            if (j >= 13 && Step % 2 == 1)
                C = Sideways ? (j == 14 ? "....KBK..KBBK..."[SI] : C) : Front[j][15 - i];
            uint32_t Col = 0;
            switch (C)
            {
            case 'K': case 'E': Col = Pal::Black; break;
            case 'S': Col = Pal::Skin; break;
            case 'H': Col = L.Hair; break;
            case 'T': Col = L.Top; break;
            case 'P': Col = L.Legs; break;
            case 'B': Col = Pal::WoodDark; break;
            default: continue;
            }
            F.Set(X + i, Y + j, Col);
        }
    if (L.Hat)
    {
        F.Tri(X + 8, Y + 3, 6, 6, L.Hat);
        F.Rect(X + 3, Y + 2, 10, 2, L.Hat);
    }
    if (L.Cape && Back) F.Rect(X + 4, Y + 9, 8, 4, L.Cape);
    else if (L.Cape && Sideways) F.Rect(Facing == 2 ? X + 10 : X + 3, Y + 9, 3, 5, L.Cape);
}

// ---------------------------------------------------------------------------------------------- the monsters

/**
 * A monster drawn from shapes into a 64x64 box (black is see-through), recoloured by Body and Accent so one drawing
 * serves a whole family. Shapes: 0 slime, 1 wisp, 2 shellback, 3 mushroom, 4 knight, 5 bat, 6 mimic chest, 7 eye.
 */
inline void DrawMonster(Frame& F, int X, int Y, int Shape, uint32_t Body, uint32_t Accent, int Anim, bool Hurt)
{
    Frame M(64, 64);
    const int Bob = (Anim / 8) % 2;
    const uint32_t Dark = Shade(Body, 2, 3);
    switch (Shape)
    {
    case 0:   // slime: a lumpy ooze with a drip and two eyes
        M.Ellipse(32, 46 + Bob, 22, 13, Body);
        M.Ellipse(22, 36 + Bob, 9, 8, Body);
        M.Ellipse(40, 34 + Bob, 11, 10, Body);
        M.Ellipse(34, 50 + Bob, 14, 6, Accent);
        M.Rect(14, 55 + Bob, 3, 5, Body);
        M.Ellipse(26, 40 + Bob, 3, 4, Pal::White); M.Ellipse(40, 39 + Bob, 3, 4, Pal::White);
        M.Rect(27, 41 + Bob, 2, 2, 0x010101); M.Rect(41, 40 + Bob, 2, 2, 0x010101);
        M.Ellipse(36, 29 + Bob, 3, 2, Shade(Body, 4, 3));
        break;
    case 1:   // wisp: a flame that flickers
        M.Ellipse(32, 40, 16, 16, Body);
        M.Tri(32, 30, 13, 22 + Bob * 3, Body);
        M.Ellipse(32, 42, 10, 10, Shade(Body, 5, 4));
        M.Rect(26, 38, 3, 5, Accent); M.Rect(36, 38, 3, 5, Accent);
        M.Rect(30, 47, 5, 2, Accent);
        break;
    case 2:   // shellback: a stone shell with crystal spikes on short legs
        M.Ellipse(32, 42, 24, 13, Body);
        for (int k = 0; k < 4; ++k) M.Tri(18 + k * 9, 34, 4, 14 + (k % 2) * 4, Accent);
        for (int k = 0; k < 4; ++k) M.Rect(14 + k * 11, 52, 4, 7, Dark);
        M.Ellipse(9, 46, 7, 6, Dark);
        M.Rect(6, 44, 2, 2, Pal::Red);
        break;
    case 3:   // mushroom: a walking cap, spotted
        M.Ellipse(32, 26 + Bob, 24, 14, Body);
        M.Ellipse(22, 22 + Bob, 4, 3, Pal::White); M.Ellipse(38, 18 + Bob, 5, 3, Pal::White);
        M.Ellipse(44, 28 + Bob, 3, 2, Pal::White);
        M.Rect(22, 34, 20, 18, Accent);
        M.Rect(26, 40, 3, 4, 0x010101); M.Rect(35, 40, 3, 4, 0x010101);
        M.Rect(20, 52, 8, 5, Pal::Wood); M.Rect(36, 52, 8, 5, Pal::Wood);
        break;
    case 4:   // knight: armour, visor slit, shield and sword
        M.Rect(22, 8, 20, 16, Dark);
        M.Rect(25, 14, 14, 3, Accent);
        M.Tri(32, 8, 4, 6, Accent);
        M.Rect(18, 24, 28, 24, Body);
        M.Rect(22, 48, 8, 14, Dark); M.Rect(34, 48, 8, 14, Dark);
        M.Ellipse(12, 36, 8, 12, Shade(Accent, 3, 4)); M.Rect(11, 28, 2, 16, Pal::Gold);
        M.Rect(50, 6 - Bob, 3, 40, Pal::StoneHi); M.Rect(46, 40 - Bob, 11, 3, Pal::Gold);
        break;
    case 5:   // bat: wide wings that beat
    {
        const int Lift = Bob ? -6 : 4;
        M.Ellipse(32, 34, 9, 10, Body);
        M.Tri(14, 34, 12, Lift > 0 ? -12 : 14, Body);
        M.Tri(50, 34, 12, Lift > 0 ? -12 : 14, Body);
        M.Rect(8, 32, 48, 4, Body);
        M.Tri(27, 25, 3, 6, Body); M.Tri(37, 25, 3, 6, Body);
        M.Rect(28, 32, 3, 3, Accent); M.Rect(34, 32, 3, 3, Accent);
        M.Rect(30, 40, 1, 3, Pal::White); M.Rect(34, 40, 1, 3, Pal::White);
        break;
    }
    case 6:   // mimic: a chest with a tongue and teeth
        M.Rect(10, 30, 44, 26, Body);
        M.Rect(10, 14 - Bob * 2, 44, 12, Body);
        M.Rect(10, 26 - Bob * 2, 44, 4, 0x010101);
        M.Rect(10, 30, 44, 6, 0x5C0000);
        for (int k = 0; k < 6; ++k) { M.Tri(14 + k * 7, 26 - Bob * 2, 2, -4, Pal::White); M.Tri(14 + k * 7, 34, 2, 4, Pal::White); }
        M.Ellipse(32, 40, 7, 4, Pal::Pink);
        M.Rect(10, 30, 2, 26, Accent); M.Rect(52, 30, 2, 26, Accent); M.Rect(10, 14 - Bob * 2, 44, 2, Accent);
        M.Rect(24, 18 - Bob * 2, 4, 4, Pal::Gold); M.Rect(36, 18 - Bob * 2, 4, 4, Pal::Gold);
        M.Rect(25, 19 - Bob * 2, 2, 2, 0x010101); M.Rect(37, 19 - Bob * 2, 2, 2, 0x010101);
        break;
    case 7:   // eye: a floating eye with a ring of lashes
        M.Ellipse(32, 32 + Bob, 20, 20, Body);
        M.Ellipse(32 + (Anim / 16 % 3) - 1, 32 + Bob, 10, 10, Accent);
        M.Ellipse(32 + (Anim / 16 % 3) - 1, 32 + Bob, 4, 4, 0x010101);
        M.Rect(26, 26 + Bob, 3, 3, Pal::White);
        for (int k = 0; k < 8; ++k)
        {
            const double A = k * 3.14159265 / 4;
            M.Rect(32 + static_cast<int>(std::cos(A) * 24), 32 + Bob + static_cast<int>(std::sin(A) * 24), 3, 3, Shade(Body, 1, 2));
        }
        break;
    default:
        M.Ellipse(32, 32, 20, 20, Body);
        break;
    }
    M.Outline(0, 0, 64, 64, Pal::Black, 0x010101);
    if (Hurt)
        for (uint32_t& P : M.Px) if (P != Pal::Black) P = Pal::White;
    F.Blit(M, X, Y, Pal::Black);
}

}   // namespace realm
}   // namespace daedalus
