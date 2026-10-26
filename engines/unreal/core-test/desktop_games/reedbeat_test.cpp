// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool WaitOpen(ReedbeatGame& G) {
    for(int N=0;N<240 && !G.WindowOpen() && !G.GetStatus().Over && !G.GetStatus().Won;++N) G.Step({});
    return G.WindowOpen();
}
void Strike(ReedbeatGame& G) { Input I; I.FirePressed=true; G.Step(I); }
}

int main() {
    ReedbeatGame Fresh;Fresh.Reset(730);
    Check(!Fresh.WindowOpen() && !Fresh.GetStatus().Over && Fresh.GetStatus().Note.find("HINT")==std::string::npos,"a fresh round waits for the reed");
    Input Early;Early.FirePressed=true;Fresh.Step(Early);
    Check(Fresh.MissCount()==1 && !Fresh.GetStatus().Over,"an early tap is one miss");
    Input Held;Held.Fire=true;Fresh.Step(Held);
    Check(Fresh.MissCount()==1,"held fire does not add another miss");
    ReedbeatGame Round;Round.Reset(730);
    Check(WaitOpen(Round),"the reed opens");
    const int Hits=Round.HitCount();
    Strike(Round);
    Check(Round.HitCount()==Hits+1 && !Round.WindowOpen(),"a strike on the glow counts");
    ReedbeatGame Practice;
    Check(Practice.SetOption(1,730) && Practice.GetOption()==1,"practice option opens");
    Check(!Practice.SetOption(2,730) && Practice.GetOption()==1,"an out-of-range reed option is refused");
    for(int N=0;N<4;++N) { Check(WaitOpen(Practice),"practice reed "+std::to_string(N+1)+" opens"); Strike(Practice); }
    Check(Practice.GetStatus().Won && Practice.GetStatus().Score==400,"four practice strikes clear the round");
    Practice.Reset(730);
    Check(Practice.GetOption()==1 && !Practice.GetStatus().Won,"practice survives a retry");
    Check(Practice.SourceKeyDown(8)==false,"R does nothing before the round ends");
    for(int N=0;N<4;++N) { WaitOpen(Practice); Strike(Practice); }
    Check(Practice.SourceKeyDown(8) && !Practice.GetStatus().Won,"R starts the same round again");
    Driver D;Check(D.Select("reedbeat",730) && D.ActiveId()=="reedbeat","driver selects Reedbeat");
    std::cout<<"reedbeat: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
