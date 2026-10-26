// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <limits>
#include <sstream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
std::vector<std::string> Fields(const std::string& Save) {
    std::istringstream In(Save);std::vector<std::string> Out;std::string Part;
    while(In>>Part) Out.push_back(Part);
    return Out;
}
std::string Pack(const std::vector<std::string>& Parts) {
    std::string Out;for(const auto& P:Parts){if(!Out.empty()) Out+=' ';Out+=P;}return Out;
}
Vec Center(const Frame& F,int Index) {
    int N=0;
    // Mine board rectangles, in row order; coordinates come from the actual rendered cells.
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle && N++==Index) return {C.A.X+C.B.X/2,C.A.Y+C.B.Y/2};
    return {-1,-1};
}
bool Click(MinesweeperGame& G,int Index,int Button) {
    Frame F;G.Render(F);const auto P=Center(F,Index);Game& Core=G;
    return Core.SourcePointerButton(P.X,P.Y,Button);
}
int Bits(const std::vector<std::string>& S,int Index) {return S[9][static_cast<std::size_t>(Index)]-'0';}
std::vector<int> Neighbours(int N,int W,int H) {
    std::vector<int> Out;
    for(int Dy=-1;Dy<=1;++Dy) for(int Dx=-1;Dx<=1;++Dx) {
        const int X=N%W+Dx,Y=N/W+Dy;
        if((Dx||Dy) && X>=0 && X<W && Y>=0 && Y<H) Out.push_back(Y*W+X);
    }
    return Out;
}
void Geometry(int Option) {
    MinesweeperGame G;G.SetOption(Option,730);Game& Core=G;
    const int W=Option==0?9:Option==1?16:30,H=Option==0?9:16;
    for(int N:{0,W-1,(H-1)*W,W*H-1,(H/2)*W+W/2}) {
        Check(Click(G,N,1),"each rendered corner/center accepts one right press");
        const auto S=Fields(G.SaveState());
        Check(std::stoi(S[3])==N%W && std::stoi(S[4])==N/W && Bits(S,N)==4,"pointer targets the rendered cell and flags it");
        Check(S[1]=="730" && std::stoi(S[2])==Option && S[5]=="0" && S[6]=="0","selection and flagging preserve seed preset clock and first reveal");
        Check(Click(G,N,1) && Bits(Fields(G.SaveState()),N)==0,"a second right press removes the flag once");
    }
    const std::string Before=G.SaveState();
    const double Left=Option==2?30:180,Right=Option==2?770:620,Bottom=Option==2?90+16*(740.0/30):530;
    for(Vec P: {Vec{Left-1,100},Vec{Right,100},Vec{200,89},Vec{200,Bottom},Vec{-1e300,100},
        Vec{std::numeric_limits<double>::quiet_NaN(),100},Vec{200,std::numeric_limits<double>::infinity()}}) {
        Check(!Core.SourcePointerButton(P.X,P.Y,0) && G.SaveState()==Before,"outside and nonfinite clicks do not alter any saved field");
    }
    Frame F;G.Render(F);const auto P=Center(F,0);
    Check(!Core.SourcePointerButton(P.X,P.Y,-1) && !Core.SourcePointerButton(P.X,P.Y,3) && G.SaveState()==Before,"unsupported buttons do not select or mutate");
    Check(Core.SourcePointerButton(Left,90,1) && Bits(Fields(G.SaveState()),0)==4,"top and left bounds are included");
    Check(Core.SourcePointerButton(Left,90,1),"included boundary flag can be removed");
    // The visible one-pixel gutter still belongs to its cell slot.
    const double Size=Option==2?740.0/30:440.0/H;
    Check(Core.SourcePointerButton(Left+Size-0.1,90+Size-0.1,1) && Bits(Fields(G.SaveState()),0)==4,"cell gutters remain forgiving click targets");
}
void SafeOpeningAndLoss(int Option,std::uint32_t Seed) {
    const int W=Option==0?9:Option==1?16:30,H=Option==0?9:16,N=(H/2)*W+W/2;
    MinesweeperGame G;G.SetOption(Option,Seed);
    Check(Click(G,N,1) && Click(G,N,0) && Fields(G.SaveState())[6]=="0","a flagged first cell cannot plant or reveal");
    Check(Click(G,N,1) && Click(G,N,0),"unflag then reveal starts the board through normal rules");
    const auto S=Fields(G.SaveState());bool Safe=S[6]=="1";
    for(int I:Neighbours(N,W,H)) Safe=Safe && !(Bits(S,I)&1);
    Check(Safe && !(Bits(S,N)&1) && S[5]=="0","first pointer reveal protects its full neighborhood without advancing the timer");
    MinesweeperGame Fresh;Fresh.SetOption(Option,Seed);Click(Fresh,N,0);
    Check(G.SaveState()==Fresh.SaveState(),"preplaced and removed flag does not change deterministic planting");
    const auto OpenBefore=G.SaveState();Check(Click(G,N,1) && G.SaveState()==OpenBefore,"open cells cannot acquire flags");
    int Mine=-1;for(int I=0;I<W*H;++I) if(Bits(S,I)&1) {Mine=I;break;}
    Check(Mine>=0,"real planted layout provides a mine for fast-loss fixture");if(Mine<0) return;
    Check(Click(G,Mine,0) && G.GetStatus().Over && !G.GetStatus().Won && Fields(G.SaveState())[5]=="0","two immediate reveals can lose before a timer step");
    const std::string Loss=G.SaveState();MinesweeperGame Restored;
    Check(Restored.RestoreState(Loss,1) && Restored.SaveState()==Loss,"zero-tick fast loss restores exact board flags cursor seed and result");
    Check(!Click(G,N,0) && !Click(G,N,1) && !Click(G,N,2) && G.SaveState()==Loss,"terminal pointer presses cannot restart or change the result");
    auto Invalid=Fields(Loss);
    for(char& C:Invalid[9]) if(!((C-'0')&1)) C='0';
    Check(!Restored.RestoreState(Pack(Invalid),1) && Restored.SaveState()==Loss,"zero-tick first-reveal mine loss remains structurally impossible");
}
void Chords() {
    constexpr int W=9,H=9;
    MinesweeperGame Base;Base.Reset(730);Click(Base,40,0);const auto S=Fields(Base.SaveState());
    int Number=-1;std::vector<int> Mines,Safe;
    for(int N=0;N<W*H && Number<0;++N) if((Bits(S,N)&3)==2) {
        std::vector<int> M,C;
        for(int I:Neighbours(N,W,H)) {if(Bits(S,I)&1) M.push_back(I);else if(!(Bits(S,I)&2)) C.push_back(I);}
        if(!M.empty() && !C.empty()) {Number=N;Mines=M;Safe=C;}
    }
    Check(Number>=0,"real opening supplies an open number with covered mines and safe neighbors");if(Number<0) return;
    MinesweeperGame Correct=Base;
    const auto Before=S[9];Check(Click(Correct,Number,2) && Fields(Correct.SaveState())[9]==Before,"mismatched flag count leaves neighbors covered");
    for(int I:Mines) Click(Correct,I,1);
    Check(Click(Correct,Number,2) && (!Correct.GetStatus().Over || Correct.GetStatus().Won),"correct matching flags chord without a loss");
    bool Opened=true;for(int I:Safe) Opened=Opened && (Bits(Fields(Correct.SaveState()),I)&2);
    Check(Opened && Fields(Correct.SaveState())[5]=="0","chord opens safe neighbors once without adding timer frames");
    MinesweeperGame Wrong=Base;
    for(std::size_t I=1;I<Mines.size();++I) Click(Wrong,Mines[I],1);
    Click(Wrong,Safe[0],1);
    Check(Click(Wrong,Number,2) && Wrong.GetStatus().Over && !Wrong.GetStatus().Won,"matching but wrong flags retain the normal chord loss");
    MinesweeperGame Restored;
    Check(Restored.RestoreState(Wrong.SaveState(),0) && Restored.SaveState()==Wrong.SaveState(),"fast wrong-flag chord loss also resumes exactly");
}
void WinAndDriver() {
    MinesweeperGame G;G.Reset(730);Click(G,40,0);const auto S=Fields(G.SaveState());
    for(int N=0;N<81 && !G.GetStatus().Over;++N) if(!(Bits(S,N)&1)) Click(G,N,0);
    Check(G.GetStatus().Won && Fields(G.SaveState())[5]=="0","mouse can finish a complete safe board without fake time");
    MinesweeperGame Restored;
    Check(Restored.RestoreState(G.SaveState(),1) && Restored.GetStatus().Won,"zero-tick completed board retains existing save support");
    Driver D;D.Select("minesweeper",730);const auto P=Center(D.GetFrame(),40);
    const std::string Before=D.CaptureSave();D.SetPaused(true);
    Check(!D.SourcePointerButton(P.X,P.Y,0) && D.CaptureSave()==Before && D.Ticks()==0,"paused pointer cannot reveal or automatically resume");
    D.SetPaused(false);Input Pending;Pending.Right=Pending.ActionPressed=true;D.SetInput(Pending);
    Check(D.SourcePointerButton(P.X,P.Y,1) && D.Ticks()==0,"driver consumes exactly one pointer press without advancing fixed time");
    D.Advance(Driver::StepSeconds*8);const auto After=Fields(D.CaptureSave());
    Check(After[3]=="4" && After[4]=="4" && Bits(After,40)==4 && After[5]=="0","accepted pointer clears stale navigation and flag edges across catch-up");
    D.SetInput(Pending);D.Advance(Driver::StepSeconds);
    Check(Fields(D.CaptureSave())[3]=="5","a fresh keyboard action still works after mouse input");
    Check(D.Select("twinwake",730) && !D.SourcePointerButton(P.X,P.Y,0) && D.Ticks()==0,"other existing games keep their unsupported pointer behavior");
}
}
int main() {
    MinesweeperGame Uninitialized;Check(!Uninitialized.SourcePointerButton(200,100,0),"uninitialized board ignores pointer events");
    for(int Option=0;Option<3;++Option) {
        Geometry(Option);for(std::uint32_t Seed:{0u,730u,UINT32_MAX}) SafeOpeningAndLoss(Option,Seed);
    }
    Chords();WinAndDriver();
    std::cout<<"Minesweeper pointer: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
