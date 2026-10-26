// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
struct GloamLatchTestAccess;
// Gloam Latch: a 5x5 lamp puzzle. Flipping a lamp also flips its orthogonal
// neighbors. The opening is built by flipping a solved dark board, so every
// seed can be cleared by repeating those same flips.
class GloamLatchGame final : public Game {
    friend struct GloamLatchTestAccess;
    static constexpr int N=5;
    std::array<bool,N*N> Lamp{};
    std::vector<int> Opening;
    int CursorCell=N*N/2;
    int Moves=0;
    bool Won=false;
    std::uint32_t SessionSeed=730;
    void Flip(int X,int Y) {
        if(X<0||Y<0||X>=N||Y>=N) return;
        Lamp[static_cast<std::size_t>(Y*N+X)]=!Lamp[static_cast<std::size_t>(Y*N+X)];
    }
    void Press(int Cell) {
        const int X=Cell%N,Y=Cell/N;
        Flip(X,Y);Flip(X-1,Y);Flip(X+1,Y);Flip(X,Y-1);Flip(X,Y+1);
    }
    bool Dark() const { for(bool L:Lamp) if(L) return false; return true; }
    void Deal() {
        Lamp.fill(false); Opening.clear(); CursorCell=N*N/2; Moves=0; Won=false;
        Random Rng; Rng.Seed(SessionSeed);
        for(int I=0;I<8;++I) Opening.push_back(Rng.Int(0,N*N-1));
        for(int Cell:Opening) Press(Cell);
        if(Dark()) { Opening.push_back(N*N/2); Press(N*N/2); }
    }
    std::int64_t Points() const { return Won?std::max<std::int64_t>(0,1000-static_cast<std::int64_t>(Moves)*25):0; }
public:
    void Reset(std::uint32_t Seed) override { SessionSeed=Seed?Seed:1; Deal(); }
    bool SourceKeyDown(int Key) override {
        if(Won && (Key==5 || Key==6 || Key==7 || Key==8)) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Won) {
            if(I.FirePressed || I.JumpPressed || I.ActionPressed) Deal();
            return;
        }
        int X=CursorCell%N,Y=CursorCell/N;
        if(I.Left||I.PadLeft) X=std::max(0,X-1);
        if(I.Right||I.PadRight) X=std::min(N-1,X+1);
        if(I.Up||I.PadUp) Y=std::max(0,Y-1);
        if(I.Down||I.PadDown) Y=std::min(N-1,Y+1);
        CursorCell=Y*N+X;
        if(!(I.FirePressed||I.JumpPressed||I.ActionPressed)) return;
        Press(CursorCell); ++Moves;
        if(Dark()) Won=true;
    }
    std::string HintLine() const {
        return Won?"HINT Pad A or R starts the same latch again."
                  :"HINT Flip a lamp and its neighbors until the board is dark.";
    }
    std::string ActionCue() const { return Won?"CUE Retry":"CUE Flip"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{16,18,32,255});
        F.AddText(30,24,"GLOAM LATCH",{255,236,180,255},28);
        F.AddText(30,58,"MOVES: "+std::to_string(Moves),White,18);
        for(int Y=0;Y<N;++Y) for(int X=0;X<N;++X) {
            const int Cell=Y*N+X;
            const double Px=180.0+X*88.0,Py=120.0+Y*80.0;
            const bool Lit=Lamp[static_cast<std::size_t>(Cell)];
            F.AddRect(Px-4,Py-4,72,64,Cell==CursorCell?Color{255,236,180,255}:Color{28,32,48,255});
            F.AddRect(Px,Py,64,56,Lit?Color{255,196,70,255}:Color{36,42,64,255});
        }
        F.AddText(30,548,HintLine(),{255,236,180,255},16);
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        int Lit=0; for(bool L:Lamp) Lit+=L?1:0;
        if(Won) return {Points(),1,true,true,"All lamps dark; pad A or R retries; moves "+std::to_string(Moves)};
        return {0,1,false,false,"Lit lamps "+std::to_string(Lit)+"; moves "+std::to_string(Moves)};
    }
    int Cursor() const { return CursorCell; }
    int LitCount() const { int NLit=0; for(bool L:Lamp) NLit+=L?1:0; return NLit; }
    bool LitAt(int Cell) const { return Cell>=0 && Cell<N*N && Lamp[static_cast<std::size_t>(Cell)]; }
};
}} // daedalus::desktop
