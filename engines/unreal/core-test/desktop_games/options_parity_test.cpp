// SPDX-License-Identifier: MIT
// Cabinet options for Lanternwild Quest (lanternwild) and Pebblecourt Rally (dodge_ball).
// Option 0 must match the original default exactly; other options are presets.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Dash() {Input I;I.DashPressed=true;return I;}

void Lanternwild() {
    LanternwildGame Default;Default.Reset(9);
    LanternwildGame Zero;Check(Zero.SetOption(0,9),"lanternwild option 0 accepted");
    Check(Zero.GetOption()==0 && !Zero.IsSwordAssistEnabled(),"lanternwild option 0 keeps fresh-press sword");
    Check(Zero.GetStatus().Note==Default.GetStatus().Note,"lanternwild option 0 matches the default run");
    LanternwildGame A;Check(A.SetOption(1,9),"lanternwild option 1 accepted");
    Check(A.GetOption()==1 && A.IsSwordAssistEnabled(),"lanternwild option 1 starts with sword assist");
    A.Reset(9);
    Check(A.IsSwordAssistEnabled() && A.GetOption()==1,"assist preset survives a retry");
    A.Step(Dash());
    Check(!A.IsSwordAssistEnabled(),"live toggle still turns assist off");
    Check(A.GetOption()==1,"option records the cabinet preset, not the live toggle");
    Check(A.SetOption(0,9) && !A.IsSwordAssistEnabled(),"switching back to option 0 clears assist");
    Check(!A.SetOption(2,9) && !A.SetOption(-1,9) && A.GetOption()==0,"out-of-range lanternwild option refused");
    Game& Core=A;Check(Core.SetOption(1,9) && Core.GetOption()==1,"lanternwild option reachable through Game");
}

void Dodge() {
    DodgeBallGame Default;Default.Reset(9);
    DodgeBallGame Zero;Check(Zero.SetOption(0,9),"dodge option 0 accepted");
    Check(Zero.Data.SelectedCountry==0 && Zero.Data.Mode==DodgeBallGame::Phase::Title,"dodge option 0 is the original start");
    Check(Zero.GetStatus().Note==Default.GetStatus().Note,"dodge option 0 matches the default run");
    for(int C=0;C<8;++C) {
        DodgeBallGame G;
        Check(G.SetOption(C,9) && G.GetOption()==C,"dodge option "+std::to_string(C)+" accepted");
        Check(G.Data.SelectedCountry==C,"dodge option presets country "+std::to_string(C));
        G.Reset(9);
        Check(G.Data.SelectedCountry==C,"country preset survives reset "+std::to_string(C));
        Check(G.Data.Mode==DodgeBallGame::Phase::Title,"preset does not skip the title");
    }
    DodgeBallGame G;G.SetOption(5,9);
    Check(!G.SetOption(8,9) && !G.SetOption(-1,9) && G.GetOption()==5,"out-of-range dodge option refused");
    Game& Core=G;Check(Core.SetOption(2,9) && Core.GetOption()==2,"dodge option reachable through Game");
}
}  // namespace

int main() {
    Lanternwild();Dodge();
    std::cout<<"options parity: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
