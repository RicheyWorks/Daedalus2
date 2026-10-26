// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
std::vector<std::string> Fields(const std::string& Save) {
    std::istringstream In(Save);std::vector<std::string> Out;std::string Token;
    while(In>>Token) Out.push_back(Token);
    return Out;
}
int Width(const BeaconSweepGame& G) {return G.GetOption()==0?9:G.GetOption()==1?16:30;}
void Move(BeaconSweepGame& G,int X,int Y) {
    G.Step({}); // Begin each deliberate tap sequence with no held movement.
    const auto F=Fields(G.SaveState());const int StartX=std::stoi(F[3]),StartY=std::stoi(F[4]);
    for(int N=0;N<std::abs(X-StartX);++N) {Input I;I.Left=X<StartX;I.Right=X>StartX;G.Step(I);G.Step({});}
    for(int N=0;N<std::abs(Y-StartY);++N) {Input I;I.Up=Y<StartY;I.Down=Y>StartY;G.Step(I);G.Step({});}
}
void Reveal(BeaconSweepGame& G) {Input I;I.FirePressed=true;G.Step(I);}
void Flag(BeaconSweepGame& G) {Input I;I.ActionPressed=true;G.Step(I);}
BeaconSweepGame ActualLoss(int Option,std::uint32_t Seed) {
    BeaconSweepGame G;G.SetOption(Option,Seed);Reveal(G);
    const std::string Layout=Fields(G.SaveState())[9];const int W=Width(G);
    int Target=-1,Marker=-1;
    for(std::size_t N=0;N<Layout.size();++N) if(((Layout[N]-'0')&1) && N%static_cast<std::size_t>(W)>0) {Target=static_cast<int>(N);break;}
    for(std::size_t N=0;N<Layout.size();++N) if(((Layout[N]-'0')&1) && static_cast<int>(N)!=Target) {Marker=static_cast<int>(N);break;}
    Move(G,Marker%W,Marker/W);Flag(G);
    Move(G,Target%W-1,Target/W);
    // Reach a real mine with repeat debt 5, distinct from fresh movement and its repeat threshold.
    Input Held;Held.Right=true;G.Step(Held);
    for(int N=0;N<4;++N) G.Step(Held);
    Held.FirePressed=true;G.Step(Held);
    return G;
}
BeaconSweepGame ActualWin(std::uint32_t Seed) {
    BeaconSweepGame G;G.Reset(Seed);Reveal(G);
    const auto Layout=Fields(G.SaveState())[9];
    for(std::size_t N=0;N<Layout.size();++N) if((Layout[N]-'0')&1) {Move(G,static_cast<int>(N)%9,static_cast<int>(N)/9);Flag(G);break;}
    // Test-only route reads the saved layout, but all completion transitions use real Step input.
    for(int N=0;N<81 && !G.GetStatus().Over;++N) {
        const char Bits=Fields(G.SaveState())[9][static_cast<std::size_t>(N)];
        if(((Bits-'0')&3)==0) {Move(G,N%9,N/9);Reveal(G);}
    }
    return G;
}
void Replay(BeaconSweepGame G,int Option,std::uint32_t Seed,bool Won) {
    Game& Core=G;const std::string Terminal=G.SaveState();
    Check(G.GetStatus().Over && G.GetStatus().Won==Won,"real play reaches the requested result");
    Check(G.GetStatus().Note.find("Pad A / R: replay. Start: pause/save")!=std::string::npos,"result names replay and preserves pause/save discoverability");
    Check(!Core.SourceControllerButton(1) && !Core.SourceControllerButton(2) && !Core.SourceControllerButton(-1)
        && !Core.SourceKeyDown(6) && !Core.SourceKeyDown(7) && G.SaveState()==Terminal,"Start and keyboard events do not replace a completed board");
    Input Held;Held.Right=Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
    Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;
    for(int N=0;N<12;++N) G.Step(Held);
    Check(G.SaveState()==Terminal,"held gameplay actions and timer remain frozen on result");
    const bool Accepted=Core.SourceControllerButton(0);Check(Accepted,"fresh A replays the completed board");
    if(!Accepted) return; // The unchanged preceding header fails cleanly without continuing a terminal run.
    BeaconSweepGame Fresh;Fresh.SetOption(Option,Seed);
    Check(G.SaveState()==Fresh.SaveState() && G.GetOption()==Option,"replay clears board flags cursor timer and terminal state while retaining seed/difficulty");
    Check(!Core.SourceControllerButton(0) && !Core.SourceControllerButton(1) && G.SaveState()==Fresh.SaveState(),"active A/Start raw events do not restart a new board");
    Input Right;Right.Right=true;
    for(int N=0;N<12;++N) {G.Step(Right);Fresh.Step(Right);}
    Check(G.SaveState()==Fresh.SaveState(),"replay navigation cadence matches fresh state after dirty terminal repeat");
    Reveal(G);Reveal(Fresh);
    Check(G.SaveState()==Fresh.SaveState(),"replay retains deterministic first-reveal planting for its seed");
    Check(G.RestoreState(Terminal,12345) && G.SaveState()==Terminal,"previous DGM1 terminal snapshot remains restorable after replay");
}
}

int main() {
    const auto Loss=ActualLoss(0,730),Win=ActualWin(730),ExpertLoss=ActualLoss(2,0);
    Replay(Loss,0,730,false);Replay(Win,0,730,true);Replay(ExpertLoss,2,0,false);
    const std::string SavedExpert=ExpertLoss.SaveState();
    Driver D;Check(D.Select("beacon_sweep",99) && D.RestoreSave(SavedExpert) && D.GetSeed()==0 && D.GetOption()==2,"terminal resume adopts persisted seed and expert difficulty over unrelated driver seed");
    Check(!D.SourceControllerButton(1) && D.CaptureSave()==SavedExpert,"terminal Start remains unconsumed for the host pause/save path");
    D.SetPaused(true);
    Check(!D.SourceControllerButton(0) && D.IsPaused() && D.CaptureSave()==SavedExpert,"paused board cannot replay through A while save controls own input");
    D.SetPaused(false); // Existing host Start resumes the pause; it does not consume replay.
    Input Stale;Stale.Right=true;Stale.FirePressed=Stale.JumpPressed=Stale.ActionPressed=Stale.DashPressed=true;D.SetInput(Stale);
    const bool Accepted=D.SourceControllerButton(0);Check(Accepted,"fresh A replays after returning from pause");
    if(Accepted) {
        BeaconSweepGame Fresh;Fresh.SetOption(2,0);const std::string Blank=Fresh.SaveState();
        Check(D.CaptureSave()==Blank && !D.IsPaused(),"Driver replay preserves restored seed/difficulty and starts unplanted");
        D.Advance(Driver::StepSeconds);
        Check(D.CaptureSave()==Blank,"accepted replay clears stale semantic edges and movement");
        // Native host deliberately forwards the same fresh pad A as a new Jump edge.
        // It may reveal cursor0 immediately; this test does not hide or suppress that behavior.
        Input Forwarded;Forwarded.JumpPressed=true;D.SetInput(Forwarded);D.Advance(Driver::StepSeconds);Fresh.Step(Forwarded);
        const auto Started=Fields(D.CaptureSave());
        Check(D.CaptureSave()==Fresh.SaveState() && Started[6]=="1" && ((Started[9][0]-'0')&2)!=0,"native-style fresh A forwarding safely reveals the new first cell");
    }
    std::cout<<"Beacon Sweep terminal replay: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
