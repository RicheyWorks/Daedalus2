// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
namespace daedalus { namespace desktop {
// Original native implementation. First reveal protects the entire 3x3 neighbourhood.
class MinesweeperGame final : public Game {
    struct Cell { bool Mine=false, Open=false, Flag=false; int Near=0; };
    std::vector<Cell> Cells;
    Random Rng;
    int Width=9, Height=9, Mines=10, Option=0, X=0, Y=0, Repeat=0;
    bool Planted=false, Lost=false, Won=false, WasMoving=false;
    std::uint64_t Ticks=0;
    int Index(int C,int R) const { return R*Width+C; }
    template<class F> void Neighbours(int I,F Fn) {
        for(int Dy=-1;Dy<=1;++Dy) for(int Dx=-1;Dx<=1;++Dx) {
            int C=I%Width+Dx,R=I/Width+Dy;
            if((Dx||Dy) && C>=0 && C<Width && R>=0 && R<Height) Fn(Index(C,R));
        }
    }
    void Plant(int Safe) {
        std::vector<int> Candidates;
        for(int I=0;I<Width*Height;++I)
            if(std::abs(I%Width-Safe%Width)>1 || std::abs(I/Width-Safe/Width)>1) Candidates.push_back(I);
        for(int I=0;I<Mines;++I) {
            int J=Rng.Int(I,static_cast<int>(Candidates.size())-1);
            std::swap(Candidates[I],Candidates[J]); Cells[Candidates[I]].Mine=true;
        }
        for(int I=0;I<Width*Height;++I) Neighbours(I,[&](int J){if(Cells[J].Mine) ++Cells[I].Near;});
        Planted=true;
    }
    void Reveal(int I) {
        if(Lost||Won||Cells[I].Flag||Cells[I].Open) return;
        if(!Planted) Plant(I);
        std::vector<int> Pending{I};
        while(!Pending.empty()) {
            int J=Pending.back();Pending.pop_back();auto& C=Cells[J];
            if(C.Open||C.Flag) continue;
            C.Open=true;
            if(C.Mine) {Lost=true;return;}
            if(C.Near==0) Neighbours(J,[&](int K){if(!Cells[K].Open&&!Cells[K].Flag) Pending.push_back(K);});
        }
        int Open=0;for(const auto& C:Cells) if(C.Open&&!C.Mine) ++Open;
        Won=Open==Width*Height-Mines;
    }
public:
    void Reset(std::uint32_t Seed) override {
        Width=Option==0?9:Option==1?16:30;Height=Option==0?9:16;Mines=Option==0?10:Option==1?40:99;
        Cells.assign(Width*Height,Cell{});Rng.Seed(Seed);X=Y=Repeat=0;Ticks=0;
        Planted=Lost=Won=WasMoving=false;
    }
    bool SetOption(int Value,std::uint32_t Seed) override {if(Value<0||Value>2)return false;Option=Value;Reset(Seed);return true;}
    int GetOption() const override {return Option;}
    void Step(const Input& I) override {
        if(Lost||Won) return;
        if(Planted && Ticks<UINT64_MAX) ++Ticks;
        int Dx=Horizontal(I)>.3?1:Horizontal(I)<-.3?-1:0;
        int Dy=Vertical(I)>.3?1:Vertical(I)<-.3?-1:0;
        bool Moving=Dx||Dy;
        if(Moving&&(!WasMoving||++Repeat>=10)) {X=std::max(0,std::min(Width-1,X+Dx));Y=std::max(0,std::min(Height-1,Y+Dy));Repeat=0;}
        if(!Moving) Repeat=0;WasMoving=Moving;
        int N=Index(X,Y);
        if(I.ActionPressed&&!Cells[N].Open) Cells[N].Flag=!Cells[N].Flag;
        if(I.FirePressed||I.JumpPressed) Reveal(N);
        if(I.DashPressed&&Cells[N].Open) {
            int Flags=0;Neighbours(N,[&](int J){if(Cells[J].Flag) ++Flags;});
            if(Flags==Cells[N].Near) Neighbours(N,[&](int J){Reveal(J);});
        }
    }
    Status GetStatus() const override {
        int Flags=0,Open=0;for(const auto& C:Cells){Flags+=C.Flag?1:0;Open+=C.Open&&!C.Mine?1:0;}
        return {Won?1000:Open,0,Lost||Won,Won,"Mines remaining "+std::to_string(Mines-Flags)+" | "+std::to_string(Ticks/60)+" active seconds"};
    }
    void Render(Frame& F) const override {
        F.Clear(800,600,{13,23,35,255});F.AddText(25,12,"MINESWEEPER",{116,224,195,255},26);
        F.AddText(25,48,GetStatus().Note,White,18);
        double Size=std::min(740.0/Width,440.0/Height),Left=(800-Width*Size)/2,Top=90;
        for(int I=0;I<Width*Height;++I) {
            const auto& C=Cells[I];double Px=Left+(I%Width)*Size,Py=Top+(I/Width)*Size;
            F.AddRect(Px,Py,Size-1,Size-1,C.Open?Color{39,55,68,255}:Color{78,106,119,255});
            if(C.Flag) F.AddText(Px+Size*.25,Py+Size*.1,"F",{255,191,69,255},Size*.65);
            else if(C.Mine&&(Lost||Won)) F.AddCircle(Px+Size/2,Py+Size/2,Size*.2,{249,93,92,255});
            else if(C.Open&&C.Near) F.AddText(Px+Size*.25,Py+Size*.1,std::to_string(C.Near),{127,231,217,255},Size*.65);
        }
        double Px=Left+X*Size,Py=Top+Y*Size;
        F.AddLine(Px,Py,Px+Size,Py,White,2);F.AddLine(Px,Py,Px,Py+Size,White,2);
        F.AddLine(Px+Size,Py,Px+Size,Py+Size,White,2);F.AddLine(Px,Py+Size,Px+Size,Py+Size,White,2);
        F.AddText(25,550,Won?"Cleared! Restart for another run.":Lost?"Mine hit. Restart to try again.":"Move: arrows | J/Space: reveal | K: flag | Shift: chord",White,18);
    }
};
}}
