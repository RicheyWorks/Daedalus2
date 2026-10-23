// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <limits>
#include <locale>
#include <sstream>
#include <utility>
namespace daedalus { namespace desktop {
// Original native implementation. First reveal protects the entire 3x3 neighbourhood.
class MinesweeperGame final : public Game {
    struct Cell { bool Mine=false, Open=false, Flag=false; int Near=0; };
    std::vector<Cell> Cells;
    Random Rng;
    int Width=9, Height=9, Mines=10, Option=0, X=0, Y=0, Repeat=0;
    bool Planted=false, Lost=false, Won=false, WasMoving=false;
    std::uint64_t Ticks=0;
    std::uint32_t BoardSeed=730;
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
    static bool ReadNumber(std::istream& In,std::uint64_t Limit,std::uint64_t& Out) {
        std::string Token;
        if(!(In>>Token) || Token.empty() || Token.size()>20) return false;
        std::uint64_t Value=0;
        for(char C:Token) {
            if(C<'0'||C>'9') return false;
            const auto Digit=static_cast<std::uint64_t>(C-'0');
            if(Digit>Limit || Value>(Limit-Digit)/10) return false;
            Value=Value*10+Digit;
        }
        Out=Value;return true;
    }
public:
    void Reset(std::uint32_t Seed) override {
        Width=Option==0?9:Option==1?16:30;Height=Option==0?9:16;Mines=Option==0?10:Option==1?40:99;
        Cells.assign(Width*Height,Cell{});BoardSeed=Seed;Rng.Seed(Seed);X=Y=Repeat=0;Ticks=0;
        Planted=Lost=Won=WasMoving=false;
    }
    bool SetOption(int Value,std::uint32_t Seed) override {if(Value<0||Value>2)return false;Option=Value;Reset(Seed);return true;}
    int GetOption() const override {return Option;}
    std::uint32_t SeedAfterRestore(std::uint32_t) const override {return BoardSeed;}
    std::string SaveState() const override {
        if(Cells.size()!=static_cast<std::size_t>(Width*Height)) return {};
        std::ostringstream Out;Out.imbue(std::locale::classic());
        Out<<"DGM1 "<<BoardSeed<<' '<<Option<<' '<<X<<' '<<Y<<' '<<Ticks<<' '
            <<(Planted?1:0)<<' '<<(Lost?1:0)<<' '<<(Won?1:0)<<' ';
        for(const auto& C:Cells) Out<<static_cast<char>('0'+(C.Mine?1:0)+(C.Open?2:0)+(C.Flag?4:0));
        return Out.str();
    }
    bool RestoreState(const std::string& Payload,std::uint32_t) override {
        if(Payload.empty() || Payload.size()>4096) return false;
        std::istringstream In(Payload);In.imbue(std::locale::classic());
        std::string Version,Layout,Extra;
        std::uint64_t SavedSeed=0,SavedOption=0,SavedX=0,SavedY=0,SavedTicks=0;
        std::uint64_t SavedPlanted=0,SavedLost=0,SavedWon=0;
        if(!(In>>Version) || Version!="DGM1"
            || !ReadNumber(In,std::numeric_limits<std::uint32_t>::max(),SavedSeed)
            || !ReadNumber(In,2,SavedOption) || !ReadNumber(In,29,SavedX) || !ReadNumber(In,15,SavedY)
            || !ReadNumber(In,std::numeric_limits<std::uint64_t>::max(),SavedTicks)
            || !ReadNumber(In,1,SavedPlanted) || !ReadNumber(In,1,SavedLost) || !ReadNumber(In,1,SavedWon)
            || !(In>>Layout) || (In>>Extra)) return false;
        // Restore into a separate board: a refused file must never damage the live run.
        MinesweeperGame Candidate;
        Candidate.Option=static_cast<int>(SavedOption);Candidate.Reset(static_cast<std::uint32_t>(SavedSeed));
        if(SavedX>=static_cast<std::uint64_t>(Candidate.Width) || SavedY>=static_cast<std::uint64_t>(Candidate.Height)
            || Layout.size()!=Candidate.Cells.size()) return false;
        int MineCount=0,OpenSafe=0,OpenMines=0;
        for(std::size_t I=0;I<Layout.size();++I) {
            if(Layout[I]<'0'||Layout[I]>'7') return false;
            const int Bits=Layout[I]-'0';auto& C=Candidate.Cells[I];
            C.Mine=(Bits&1)!=0;C.Open=(Bits&2)!=0;C.Flag=(Bits&4)!=0;
            if(C.Open&&C.Flag) return false;
            MineCount+=C.Mine?1:0;OpenSafe+=C.Open&&!C.Mine?1:0;OpenMines+=C.Open&&C.Mine?1:0;
        }
        if(!SavedPlanted) {
            if(MineCount || OpenSafe || OpenMines || SavedTicks || SavedLost || SavedWon) return false;
        } else {
            if(MineCount!=Candidate.Mines || OpenSafe==0 || OpenMines>1
                || (SavedLost && (OpenSafe==Candidate.Width*Candidate.Height-Candidate.Mines || SavedTicks==0))
                || (SavedLost!=0)!=(OpenMines==1)
                || (SavedWon!=0)!=(OpenSafe==Candidate.Width*Candidate.Height-Candidate.Mines && !SavedLost)) return false;
            for(int I=0;I<Candidate.Width*Candidate.Height;++I)
                Candidate.Neighbours(I,[&](int J){if(Candidate.Cells[J].Mine) ++Candidate.Cells[I].Near;});
        }
        Candidate.X=static_cast<int>(SavedX);Candidate.Y=static_cast<int>(SavedY);Candidate.Ticks=SavedTicks;
        Candidate.Planted=SavedPlanted!=0;Candidate.Lost=SavedLost!=0;Candidate.Won=SavedWon!=0;
        // Reset repeat/held navigation; the saved seed is sufficient before the first planting.
        *this=std::move(Candidate);return true;
    }
    void Step(const Input& I) override {
        if(Lost||Won) return;
        if(Planted && Ticks<UINT64_MAX) ++Ticks;
        int Dx=Horizontal(I)>.3?1:Horizontal(I)<-.3?-1:0;
        int Dy=Vertical(I)>.3?1:Vertical(I)<-.3?-1:0;
        bool Moving=Dx||Dy;
        if(Moving&&(!WasMoving||++Repeat>=10)) {X=std::max(0,std::min(Width-1,X+Dx));Y=std::max(0,std::min(Height-1,Y+Dy));Repeat=0;}
        if(!Moving) Repeat=0;
        WasMoving=Moving;
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
