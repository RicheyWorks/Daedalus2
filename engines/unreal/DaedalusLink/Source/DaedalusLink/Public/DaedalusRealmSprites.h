// SPDX-License-Identifier: MIT

#pragma once

// DSP 1: the 8-bit realm's sprite pack (ADR-052, 2026-10-13). Sol's Blender cast for the portal realm arrives as
// pixel sprites in this text format and the realm draws them in place of its procedural shapes. Pure C++17, no
// Unreal; tools/realm/sprites.py writes it from PNG sheets and parses it the same way (parity test).
//
//   DSP 1
//   palette 3 F8A070 000000 FCFCFC         up to 62 colours; index i is the base-62 digit i (0-9 A-Z a-z)
//   sprite BLIGHT_SLIME 32 32 2            id, width, height, frames; then frames*height rows of width digits
//   ....1111....                           '.' is transparent
//   ...
//
// Ids: a monster's id ("BLIGHT_SLIME"), its tiers ("BLIGHT_SLIME:2", ":3"), a party member ("MEMBER:HERO"), an NPC
// role ("NPC:INN"). People have 8 frames: down0 down1 up0 up1 left0 left1 right0 right1. Monsters have 2 (idle bob).
// Limits: 4096 sprites, 128x128, 16 frames, 62 colours, lines of 1024 bytes. Bad input gives "line N: why".

#include <cstdint>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>

#include "DaedalusRealmDraw.h"

namespace daedalus
{
namespace realm
{

struct Sprite
{
    int W = 0, H = 0, Frames = 0;
    std::vector<uint32_t> Px;   // Frames * H * W, 0 = transparent (colours never use pure 0; 0x000000 becomes 0x010101)

    uint32_t At(int Frame, int X, int Y) const
    {
        if (Frame < 0 || Frame >= Frames || X < 0 || X >= W || Y < 0 || Y >= H) return 0;
        return Px[static_cast<size_t>((Frame * H + Y) * W + X)];
    }
};

class SpritePack
{
public:
    static constexpr int MaxSprites = 4096, MaxSize = 128, MaxFrames = 16, MaxColours = 62;
    static constexpr size_t MaxLine = 1024;

    std::map<std::string, Sprite> Sprites;
    std::vector<uint32_t> Palette;

    const Sprite* Find(const std::string& Id) const
    {
        auto It = Sprites.find(Id);
        return It == Sprites.end() ? nullptr : &It->second;
    }

    static int Digit(char C)
    {
        if (C >= '0' && C <= '9') return C - '0';
        if (C >= 'A' && C <= 'Z') return 10 + C - 'A';
        if (C >= 'a' && C <= 'z') return 36 + C - 'a';
        return -1;
    }

    static bool IsId(const std::string& S)
    {
        if (S.empty() || S.size() > 64) return false;
        for (char C : S) if (!(std::isalnum(static_cast<unsigned char>(C)) || C == '_' || C == ':' || C == '-')) return false;
        return true;
    }

    /** Parse the whole pack. False with Error "line N: why". Nothing is kept on failure. */
    bool Parse(const std::string& Text, std::string& Error)
    {
        SpritePack Out;
        std::vector<std::string> Lines;
        {
            std::string Cur;
            for (char C : Text)
            {
                if (C == '\n') { Lines.push_back(Cur); Cur.clear(); }
                else if (C != '\r') Cur += C;
            }
            if (!Cur.empty()) Lines.push_back(Cur);
        }
        auto Fail = [&](size_t I, const std::string& Why) { Error = "line " + std::to_string(I + 1) + ": " + Why; return false; };
        if (Lines.empty() || Lines[0] != "DSP 1") return Fail(0, "expected 'DSP 1'");
        size_t I = 1;
        Sprite* Open = nullptr;
        std::string OpenId;
        int RowsLeft = 0;
        for (; I < Lines.size(); ++I)
        {
            const std::string& L = Lines[I];
            if (L.size() > MaxLine) return Fail(I, "line too long");
            if (RowsLeft > 0)
            {
                if (static_cast<int>(L.size()) != Open->W) return Fail(I, "row of " + std::to_string(L.size()) + " for a sprite " + std::to_string(Open->W) + " wide");
                for (char C : L)
                {
                    if (C == '.') { Open->Px.push_back(0); continue; }
                    const int D = Digit(C);
                    if (D < 0 || D >= static_cast<int>(Out.Palette.size())) return Fail(I, std::string("colour '") + C + "' is not in the palette");
                    Open->Px.push_back(Out.Palette[static_cast<size_t>(D)]);
                }
                if (--RowsLeft == 0) { Open = nullptr; OpenId.clear(); }
                continue;
            }
            if (L.empty() || L[0] == '#') continue;
            std::vector<std::string> F;
            {
                std::string W;
                for (char C : L) { if (C == ' ') { if (!W.empty()) F.push_back(W); W.clear(); } else if (C == '\t') return Fail(I, "tab"); else W += C; }
                if (!W.empty()) F.push_back(W);
            }
            if (F[0] == "palette")
            {
                if (!Out.Palette.empty()) return Fail(I, "a second palette");
                if (F.size() < 2) return Fail(I, "expected 'palette <n> <hex>...'");
                const int N = std::atoi(F[1].c_str());
                if (N < 1 || N > MaxColours || static_cast<int>(F.size()) != N + 2) return Fail(I, "palette count does not match");
                for (int k = 0; k < N; ++k)
                {
                    const std::string& Hx = F[static_cast<size_t>(k + 2)];
                    if (Hx.size() != 6) return Fail(I, "bad colour " + Hx);
                    for (char C : Hx) if (!std::isxdigit(static_cast<unsigned char>(C))) return Fail(I, "bad colour " + Hx);
                    uint32_t V = static_cast<uint32_t>(std::strtoul(Hx.c_str(), nullptr, 16));
                    if (V == 0) V = 0x010101;   // 0 means transparent in the pixel store
                    Out.Palette.push_back(V);
                }
            }
            else if (F[0] == "sprite")
            {
                if (Out.Palette.empty()) return Fail(I, "sprite before the palette");
                if (F.size() != 5) return Fail(I, "expected 'sprite <id> <w> <h> <frames>'");
                if (!IsId(F[1])) return Fail(I, "bad sprite id");
                if (Out.Sprites.count(F[1])) return Fail(I, "duplicate sprite " + F[1]);
                if (static_cast<int>(Out.Sprites.size()) >= MaxSprites) return Fail(I, "too many sprites");
                const int W = std::atoi(F[2].c_str()), H = std::atoi(F[3].c_str()), Fr = std::atoi(F[4].c_str());
                if (W < 1 || W > MaxSize || H < 1 || H > MaxSize) return Fail(I, "bad size");
                if (Fr < 1 || Fr > MaxFrames) return Fail(I, "bad frame count");
                Sprite S;
                S.W = W; S.H = H; S.Frames = Fr;
                S.Px.reserve(static_cast<size_t>(W * H * Fr));
                Open = &Out.Sprites[F[1]];
                *Open = std::move(S);
                OpenId = F[1];
                RowsLeft = H * Fr;
            }
            else return Fail(I, "unknown record " + F[0]);
        }
        if (RowsLeft > 0) return Fail(Lines.size(), "sprite " + OpenId + " ends early");
        if (Out.Palette.empty()) return Fail(Lines.size(), "no palette");
        *this = std::move(Out);
        return true;
    }

    /** Draw a frame at (X, Y), transparent pixels skipped. Hurt paints it white (the hit flash). */
    static void Draw(Frame& F, int X, int Y, const Sprite& S, int Frame, bool Hurt = false, bool Mirror = false)
    {
        if (S.Frames == 0) return;
        Frame %= S.Frames;
        for (int j = 0; j < S.H; ++j)
            for (int i = 0; i < S.W; ++i)
            {
                const uint32_t C = S.At(Frame, Mirror ? S.W - 1 - i : i, j);
                if (C) F.Set(X + i, Y + j, Hurt ? Pal::White : C);
            }
    }
};

} // namespace realm
} // namespace daedalus
