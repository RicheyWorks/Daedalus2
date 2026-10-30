// SPDX-License-Identifier: MIT
// Reedbeat host save: hits, misses and mode round-trip through Continue; the
// beat clock restarts; finished rounds save nothing; bad payloads are refused.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include "DesktopGames/DaedalusDesktopReedbeatCore.h"
#include "DesktopGames/DaedalusDesktopSaveSlots.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
void HitOne(ReedbeatGame& G) {
    Input Idle,Strike;Strike.FirePressed=true;
    for(int N=0;N<200 && !G.WindowOpen();++N) G.Step(Idle);
    G.Step(Strike);
}
}

int main() {
    Check(SupportsManualSave("reedbeat") && std::string(SaveFileFor("reedbeat"))=="reedbeat.dgs","slot: manual, reedbeat.dgs");
    for(int Mode=0;Mode<2;++Mode) {
        ReedbeatGame G;G.Reset(12);G.SetOption(Mode,12);
        HitOne(G);HitOne(G);
        Input Early;Early.FirePressed=true;G.Step(Early);
        Check(G.HitCount()==2 && G.MissCount()==1,"mode "+std::to_string(Mode)+": two hits one miss");
        const std::string Save=G.SaveState();
        Check(Save=="RBS1 "+std::to_string(Mode)+" 2 1","mode "+std::to_string(Mode)+": save text");
        ReedbeatGame R;R.Reset(12);
        Check(R.RestoreState(Save,12) && R.SaveState()==Save && R.GetOption()==Mode,"mode "+std::to_string(Mode)+": restores");
        Check(!R.WindowOpen() && R.GetStatus().Score==200,"mode "+std::to_string(Mode)+": clock fresh, score kept");
    }
    ReedbeatGame Lost;Lost.Reset(3);Input Early;Early.FirePressed=true;
    for(int N=0;N<3;++N) Lost.Step(Early);
    Check(Lost.GetStatus().Over && Lost.SaveState().empty(),"dropped round saves nothing");
    Driver D;D.Select("reedbeat",8);D.Advance(Driver::StepSeconds);
    const std::string Save=D.CaptureSave();
    Driver E;Check(!Save.empty() && E.Select("reedbeat",8) && E.RestoreSave(Save) && E.CaptureSave()==Save,"driver Continue round-trips");
    for(const char* Bad:{"","RBS1","RBS2 0 0 0","RBS1 2 0 0","RBS1 0 8 0","RBS1 1 4 0","RBS1 0 0 3","RBS1 0 -1 0","RBS1 0 0 0 x"}) {
        ReedbeatGame R;R.Reset(1);Check(!R.RestoreState(Bad,1),std::string("refuses '")+Bad+"'");
    }
    std::cout<<"reedbeat save: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
