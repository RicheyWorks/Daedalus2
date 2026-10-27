// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
struct GloamLatchTestAccess;
// Gloam Latch: a 5x5 lamp puzzle. Flipping a lamp also flips its orthogonal
// neighbors. The opening is built by flipping a solved dark board, so every
// seed can be cleared by repeating those same flips.
class GloamLatchGame final : public Game {
    friend struct GloamLatchTestAccess;
    static constexpr int MaxN=5;
    std::array<bool,MaxN*MaxN> Lamp{};
    std::vector<int> Opening;
    int Option=0;
    int Width=5;
    int CursorCell=12;
    int Moves=0;
    bool Won=false;
    std::uint32_t SessionSeed=730;
    void Flip(int X,int Y) {
        if(X<0||Y<0||X>=Width||Y>=Width) return;
        Lamp[static_cast<std::size_t>(Y*Width+X)]=!Lamp[static_cast<std::size_t>(Y*Width+X)];
    }
    void Press(int Cell) {
        const int X=Cell%Width,Y=Cell/Width;
        Flip(X,Y);Flip(X-1,Y);Flip(X+1,Y);Flip(X,Y-1);Flip(X,Y+1);
    }
    bool Dark() const {
        for(int Cell=0;Cell<Width*Width;++Cell) if(Lamp[static_cast<std::size_t>(Cell)]) return false;
        return true;
    }
    void Deal() {
        Width=Option==1?3:5;
        Lamp.fill(false); Opening.clear(); CursorCell=Width*Width/2; Moves=0; Won=false;
        Random Rng; Rng.Seed(SessionSeed);
        const int Cells=Width*Width;
        const int Flips=Option==1?4:8;
        for(int I=0;I<Flips;++I) Opening.push_back(Rng.Int(0,Cells-1));
        for(int Cell:Opening) Press(Cell);
        if(Dark()) { Opening.push_back(Cells/2); Press(Cells/2); }
    }
    std::int64_t Points() const { return Won?std::max<std::int64_t>(0,1000-static_cast<std::int64_t>(Moves)*25):0; }
public:
    void Reset(std::uint32_t Seed) override { SessionSeed=Seed?Seed:1; Deal(); }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value; SessionSeed=Seed?Seed:1; Deal(); return true;
    }
    int GetOption() const override { return Option; }
    // Save: option, seed, cursor, moves and the lit lamps as a bit mask. A cleared board
    // has nothing to continue, so it saves nothing. Retry after a restore deals the same latch.
    std::string SaveState() const override {
        if(Won) return {};
        std::uint32_t Bits=0;
        for(int Cell=0;Cell<Width*Width;++Cell) if(Lamp[static_cast<std::size_t>(Cell)]) Bits|=1u<<Cell;
        return "GLS1 "+std::to_string(Option)+" "+std::to_string(SessionSeed)+" "+std::to_string(CursorCell)
            +" "+std::to_string(Moves)+" "+std::to_string(Bits);
    }
    bool RestoreState(const std::string& Payload,std::uint32_t) override {
        if(Payload.size()>96) return false;
        std::istringstream In(Payload);std::string Version,Extra;
        long long Mode=-1,SeedValue=-1,Cell=-1,MoveCount=-1,Bits=-1;
        if(!(In>>Version>>Mode>>SeedValue>>Cell>>MoveCount>>Bits) || Version!="GLS1" || (In>>Extra)) return false;
        if(Mode<0 || Mode>1 || SeedValue<1 || SeedValue>4294967295LL || MoveCount<0 || MoveCount>1000000) return false;
        const int W=Mode==1?3:5;
        if(Cell<0 || Cell>=W*W || Bits<=0 || Bits>=(1LL<<(W*W))) return false;
        Option=static_cast<int>(Mode);SessionSeed=static_cast<std::uint32_t>(SeedValue);Deal();
        for(int C=0;C<W*W;++C) Lamp[static_cast<std::size_t>(C)]=((Bits>>C)&1)!=0;
        CursorCell=static_cast<int>(Cell);Moves=static_cast<int>(MoveCount);Won=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    bool SourceKeyDown(int Key) override {
        if(Won && (Key==5 || Key==6 || Key==7 || Key==8)) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Won) {
            if(I.FirePressed || I.JumpPressed || I.ActionPressed) Deal();
            return;
        }
        int X=CursorCell%Width,Y=CursorCell/Width;
        if(I.Left||I.PadLeft) X=std::max(0,X-1);
        if(I.Right||I.PadRight) X=std::min(Width-1,X+1);
        if(I.Up||I.PadUp) Y=std::max(0,Y-1);
        if(I.Down||I.PadDown) Y=std::min(Width-1,Y+1);
        CursorCell=Y*Width+X;
        if(!(I.FirePressed||I.JumpPressed||I.ActionPressed)) return;
        Press(CursorCell); ++Moves;
        if(Dark()) Won=true;
    }
    std::string HintLine() const {
        return Won?"HINT Pad A or R starts the same latch again."
                  :"HINT Flip a lamp and its neighbors until the board is dark.";
    }
    std::string ActionCue() const { return Won?"CUE Retry":"CUE Flip"; }
    std::string HowToLine() const override { return "HOW Flip a lamp and its neighbors until the board is dark."; }
    std::string KeyHint() const override { return "KEYS Arrows move. J flips."; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{16,18,32,255});
        F.AddText(30,24,"GLOAM LATCH",{255,236,180,255},28);
        F.AddText(30,58,"MOVES: "+std::to_string(Moves),White,18);
        for(int Y=0;Y<Width;++Y) for(int X=0;X<Width;++X) {
            const int Cell=Y*Width+X;
            const double Px=180.0+X*88.0,Py=120.0+Y*80.0;
            const bool Lit=Lamp[static_cast<std::size_t>(Cell)];
            F.AddRect(Px-4,Py-4,72,64,Cell==CursorCell?Color{255,236,180,255}:Color{28,32,48,255});
            F.AddRect(Px,Py,64,56,Lit?Color{255,196,70,255}:Color{36,42,64,255});
        }
        F.AddText(30,548,HintLine(),{255,236,180,255},16);
        F.AddText(30,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,520,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        int Lit=0; for(int Cell=0;Cell<Width*Width;++Cell) Lit+=Lamp[static_cast<std::size_t>(Cell)]?1:0;
        if(Won) return {Points(),1,true,true,"All lamps dark; pad A or R retries; moves "+std::to_string(Moves)};
        return {0,1,false,false,"Lit lamps "+std::to_string(Lit)+"; moves "+std::to_string(Moves)};
    }
    int BoardWidth() const { return Width; }
    int Cursor() const { return CursorCell; }
    int LitCount() const { int NLit=0; for(bool L:Lamp) NLit+=L?1:0; return NLit; }
    bool LitAt(int Cell) const { return Cell>=0 && Cell<Width*Width && Lamp[static_cast<std::size_t>(Cell)]; }
};
}} // daedalus::desktop
