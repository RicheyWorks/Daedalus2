// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
std::vector<std::string> Fields(const std::string& Save) {
    std::istringstream In(Save);std::vector<std::string> Out;std::string Token;
    while(In>>Token) Out.push_back(Token);
    return Out;
}
std::string Pack(const std::vector<std::string>& Tokens) {
    std::string Out;
    for(const auto& Token:Tokens) {if(!Out.empty()) Out+=' ';Out+=Token;}
    return Out;
}
void Move(BeaconSweepGame& Game,int X,int Y) {
    const auto Tokens=Fields(Game.SaveState());
    const int StartX=std::stoi(Tokens[3]),StartY=std::stoi(Tokens[4]);
    for(int N=0;N<std::abs(X-StartX);++N) {
        Input I;I.Left=X<StartX;I.Right=X>StartX;Game.Step(I);Game.Step({});
    }
    for(int N=0;N<std::abs(Y-StartY);++N) {
        Input I;I.Up=Y<StartY;I.Down=Y>StartY;Game.Step(I);Game.Step({});
    }
}
void Reveal(BeaconSweepGame& Game) {Input I;I.FirePressed=true;Game.Step(I);}
void Flag(BeaconSweepGame& Game) {Input I;I.ActionPressed=true;Game.Step(I);}
bool SameFrame(const BeaconSweepGame& A,const BeaconSweepGame& B) {
    Frame F,G;A.Render(F);B.Render(G);
    if(F.Commands.size()!=G.Commands.size() || F.Width!=G.Width || F.Height!=G.Height) return false;
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];const auto& D=G.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
}

int main() {
    int Checks=0,Failed=0;
    auto Check=[&](bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}};
    BeaconSweepGame Uninitialized;Check(Uninitialized.SaveState().empty(),"uninitialized board has no save");
    // Real inputs produce each state; saved hidden cells let this test choose safe/mine targets.
    for(int Option=0;Option<3;++Option) for(std::uint32_t Seed:{0u,730u,UINT32_MAX}) {
        const int Width=Option==0?9:Option==1?16:30,Height=Option==0?9:16;
        BeaconSweepGame Original,Resumed;
        Original.SetOption(Option,Seed);Move(Original,1,1);Flag(Original);Move(Original,Width/2,Height/2);
        const std::string BeforeFirst=Original.SaveState();
        Check(!BeforeFirst.empty() && BeforeFirst.size()<4096,"all difficulties fit bounded save");
        Check(Resumed.RestoreState(BeforeFirst,999),"pre-first-reveal save restores across caller seeds");
        if(Resumed.SaveState()!=BeforeFirst) {Check(false,"pre-first-reveal roundtrip");continue;}
        Check(SameFrame(Original,Resumed),"unplanted flags and cursor render identically");
        Check(Resumed.SeedAfterRestore(999)==Seed,"original seed retained including zero and uint32 max");
        Reveal(Original);Reveal(Resumed);
        Check(Original.SaveState()==Resumed.SaveState(),"first reveal plants identical board after resume");
        const auto Planted=Fields(Original.SaveState());
        bool Safe=true;
        for(int Y=Height/2-1;Y<=Height/2+1;++Y) for(int X=Width/2-1;X<=Width/2+1;++X)
            Safe=Safe&&((Planted[9][static_cast<std::size_t>(Y*Width+X)]-'0')&1)==0;
        Check(Safe,"resumed first reveal still protects 3x3 neighbourhood");
        for(int N=0;N<125;++N) Original.Step({});
        const std::string Midgame=Original.SaveState();
        Check(Resumed.RestoreState(Midgame,1) && Resumed.SaveState()==Midgame,"planted board timer flags option roundtrip");
        Check(SameFrame(Original,Resumed) && Original.GetStatus().Note==Resumed.GetStatus().Note,"numbers and active time restored");
        // The flag at 1,1 may hold back a safe flood cell. Unflag before clearing the board.
        BeaconSweepGame Winning;
        Check(Winning.RestoreState(Midgame,1),"midgame can continue independently");
        if(!Winning.GetStatus().Over) {Move(Winning,1,1);Flag(Winning);}
        for(int N=0;N<Width*Height && !Winning.GetStatus().Over;++N) {
            const char Bits=Fields(Winning.SaveState())[9][static_cast<std::size_t>(N)];
            if(((Bits-'0')&3)==0) {Move(Winning,N%Width,N/Width);Reveal(Winning);}
        }
        Check(Winning.GetStatus().Won,"resumed board can be played to completion");
        const std::string Win=Winning.SaveState();
        Check(Resumed.RestoreState(Win,1) && Resumed.GetStatus().Won && SameFrame(Winning,Resumed),"won board roundtrip");
        Resumed.Step({});Check(Resumed.SaveState()==Win,"terminal time remains frozen after resume");
        int Mine=-1;
        for(int N=0;N<Width*Height;++N) if((Planted[9][static_cast<std::size_t>(N)]-'0')&1) {Mine=N;break;}
        Move(Original,Mine%Width,Mine/Width);Reveal(Original);
        const std::string Loss=Original.SaveState();
        Check(Original.GetStatus().Over&&!Original.GetStatus().Won,"real mine reveal produces loss");
        Check(Resumed.RestoreState(Loss,1) && Resumed.SaveState()==Loss && SameFrame(Original,Resumed),"lost board roundtrip");
    }

    BeaconSweepGame Live;
    Live.Reset(730);Reveal(Live);for(int N=0;N<80;++N) Live.Step({});
    const std::string Good=Live.SaveState();const auto Tokens=Fields(Good);
    auto Refuse=[&](const std::string& Bad) {
        Check(!Live.RestoreState(Bad,77),"malformed/inconsistent save refused");
        Check(Live.SaveState()==Good,"refused save preserves every live field");
    };
    auto Replace=[&](std::size_t Field,const std::string& Value) {auto Bad=Tokens;Bad[Field]=Value;Refuse(Pack(Bad));};
    Refuse("");Refuse(std::string(4097,'0'));Refuse(Good+" extra");Refuse("DGS1 0 1 2");
    Replace(0,"DGM2");Replace(1,"-1");Replace(1,"+1");Replace(1,"4294967296");
    Replace(2,"3");Replace(2,"-1");Replace(3,"9");Replace(4,"9");
    Replace(5,"-1");Replace(5,"18446744073709551616");Replace(5,"1.5");
    Replace(6,"2");Replace(7,"2");Replace(8,"2");Replace(6,"0");Replace(7,"1");Replace(8,"1");
    Replace(9,Tokens[9].substr(1));Replace(9,Tokens[9]+"0");
    auto Layout=Tokens[9];Layout[0]='8';Replace(9,Layout);
    Layout=Tokens[9];Layout[0]='x';Replace(9,Layout);
    Layout=Tokens[9];Layout[0]='6';Replace(9,Layout); // opened + flagged
    Layout=Tokens[9];Layout[0]='7';Replace(9,Layout);
    Layout=Tokens[9];
    for(char& C:Layout) if((C-'0')&1) {C='0';break;}
    Replace(9,Layout); // missing mine
    Layout=Tokens[9];for(char& C:Layout) C=static_cast<char>('0'+((C-'0')&1));
    Replace(9,Layout); // planted but nothing revealed
    auto BadLoss=Tokens;BadLoss[7]="1";
    bool OpenedMine=false;
    for(char& C:BadLoss[9]) {if((C-'0')&1) {if(!OpenedMine) {C='3';OpenedMine=true;}} else C='2';}
    Refuse(Pack(BadLoss)); // cannot lose after the board was already cleared
    BadLoss=Tokens;BadLoss[5]="0";BadLoss[7]="1";
    for(char& C:BadLoss[9]) if((C-'0')&1) {C='3';break;}
    BeaconSweepGame FastLoss;
    Check(FastLoss.RestoreState(Pack(BadLoss),1) && FastLoss.SaveState()==Pack(BadLoss),"multiple pointer events can produce a valid zero-tick later loss");
    for(char& C:BadLoss[9]) if(!((C-'0')&1)) C='0';
    Refuse(Pack(BadLoss)); // a first-reveal loss still cannot have any safe cell open
    auto Maximum=Tokens;Maximum[5]="18446744073709551615";
    BeaconSweepGame Saturated;
    Check(Saturated.RestoreState(Pack(Maximum),1),"uint64 maximum timer accepted without overflow");
    Saturated.Step({});Check(Saturated.SaveState()==Pack(Maximum),"timer saturates on next step");
    BeaconSweepGame Fresh;Fresh.Reset(1);
    auto Empty=Fields(Fresh.SaveState());
    for(std::size_t N:{5u,6u,7u,8u}) {auto Bad=Empty;Bad[N]="1";Refuse(Pack(Bad));}
    Empty[9][0]='1';Refuse(Pack(Empty));Empty[9][0]='2';Refuse(Pack(Empty));

    Driver Source,Destination;
    Check(Source.Select("beacon_sweep",730) && Source.SetOption(2),"driver selects expert Beacon Sweep");
    const std::string DriverSave=Source.CaptureSave();
    Check(Destination.Select("beacon_sweep",99) && Destination.RestoreSave(DriverSave)
        && Destination.GetSeed()==730 && Destination.GetOption()==2,"driver restores difficulty and restart seed");
    Input Pending;Pending.ActionPressed=true;Destination.SetInput(Pending);Destination.SetPaused(true);
    Check(!Destination.RestoreSave("invalid") && Destination.IsPaused() && Destination.CaptureSave()==DriverSave,"failed restore preserves driver pause and board");
    Destination.SetPaused(false);Destination.SetInput(Pending);
    Check(Destination.RestoreSave(DriverSave) && !Destination.IsPaused(),"valid restore returns to playable state");
    Destination.Advance(Driver::StepSeconds);
    Check(Destination.CaptureSave()==DriverSave,"valid restore clears pending flag input");
    Destination.Restart();Check(Destination.CaptureSave()==DriverSave,"restart uses saved seed and difficulty");
    Pending={};Pending.FirePressed=true;Source.SetInput(Pending);Destination.SetInput(Pending);
    Source.Advance(Driver::StepSeconds);Destination.Advance(Driver::StepSeconds);
    Check(Source.CaptureSave()==Destination.CaptureSave(),"driver first reveal stays deterministic after restart");
    Check(!Destination.RestoreSave("DGS1 0 1 135 3 0 0 0 1 0"),"Star payload cannot replace Beacon Sweep");
    Check(Source.Select("star_shooter",730),"Star remains selectable");
    Source.SourceKeyDown(6);const auto StarSave=Source.CaptureSave();
    Check(!StarSave.empty() && Source.RestoreSave(StarSave) && Source.GetSeed()==730,"Star save and fallback seed remain compatible");
    std::cout<<"Beacon Sweep save/resume: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
