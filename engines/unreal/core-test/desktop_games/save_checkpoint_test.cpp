// SPDX-License-Identifier: MIT
// Checkpoint saves for Football (DFS1) and Glowtrail Chase / Glowtrail (DMS1):
// round trips, fresh re-rack on restore, finished runs not saved, strict
// validation that leaves the run untouched, and Driver capture/restore.
// catalog-capability: save_restore: football glowtrail
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void End(GlowtrailGame& G,bool Won) {G.Over=!Won;G.Won=Won;}
};
}}  // namespace daedalus::desktop
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Fire() {Input I;I.FirePressed=true;return I;}

void Football() {
    FootballGame T;Check(T.SaveState().empty(),"football title is not saved");
    FootballGame G;G.Step(Fire());G.Data.HumanScore=2;G.Data.CpuScore=1;G.Data.Seconds=41.3;
    G.Data.Football={700,250,3,1};
    const std::string Save=G.SaveState();
    Check(Save=="DFS1 0 2 1 42","football match payload: "+Save);
    FootballGame H;Check(H.RestoreState(Save,4),"football match restores");
    Check(H.Data.Mode==FootballGame::Phase::Playing && H.Data.HumanScore==2 && H.Data.CpuScore==1 && H.Data.Seconds==42,"match score and clock restored");
    Check(H.Data.Football.X==400 && H.Data.Football.Vx==0 && H.Data.Human.X==200,"restore re-racks the kick-off");
    Check(H.SaveState()==Save,"football round trip");
    H.Step(Input{});Check(H.Data.Seconds<42 && !H.GetStatus().Over,"restored clock runs");

    FootballGame P;P.SetOption(1,4);P.Step(Fire());P.Data.HumanScore=2;
    const std::string PS=P.SaveState();
    Check(PS=="DFS1 1 2 0 0","football practice payload: "+PS);
    FootballGame Q;Check(Q.RestoreState(PS,4) && Q.GetOption()==1 && Q.Data.HumanScore==2,"practice targets restored");
    Check(Q.IsKickReady(),"restored practice is ready to aim");
    Check(Q.SaveState()==PS,"practice round trip");

    FootballGame E;E.Step(Fire());E.Data.Seconds=1.0/60.0;E.Step(Input{});
    Check(E.GetStatus().Over && E.SaveState().empty(),"finished match is not saved");

    for(const char* B:{"","DFS2 0 0 0 10","DFS1 0 0 0","DFS1 0 0 0 10 x","DFS1 2 0 0 10","DFS1 0 -1 0 10",
                       "DFS1 0 0 0 0","DFS1 0 0 0 91","DFS1 0 1000 0 10","DFS1 1 3 0 0","DFS1 1 1 1 0","DFS1 1 1 0 5"}) {
        FootballGame F;F.Step(Fire());F.Data.HumanScore=1;
        Check(!F.RestoreState(B,1) && F.Data.HumanScore==1 && F.Data.Mode==FootballGame::Phase::Playing,
            std::string("football rejects '")+B+"' and keeps the run");
    }
}

void Glowtrail() {
    GlowtrailGame G;G.Reset(8);
    const std::string Zero=G.SaveState();
    Check(Zero=="DMS1 0 0 3","glowtrail fresh payload: "+Zero);
    GlowtrailGame H;Check(H.RestoreState("DMS1 1 4560 2",8),"glowtrail restores");
    Check(H.GetOption()==1 && H.GetStatus().Score==4560 && H.GetStatus().Lives==2 && !H.GetStatus().Over,"score, lives and mode restored");
    Check(H.SaveState()=="DMS1 1 4560 2","glowtrail round trip");
    GlowtrailGame Ref;Ref.SetOption(1,8);
    Frame A,B;H.Render(A);Ref.Render(B);
    Check(A.Commands.size()==B.Commands.size(),"restore starts a fresh maze");
    for(bool Won:{false,true}) {
        GlowtrailGame E;E.Reset(8);MazeTestAccess::End(E,Won);
        Check(E.SaveState().empty(),std::string("finished glowtrail run is not saved (")+(Won?"won":"lost")+")");
    }
    for(const char* Bad:{"","DMS2 0 0 3","DMS1 0 0","DMS1 0 0 3 x","DMS1 2 0 3","DMS1 0 -5 3","DMS1 0 0 0",
                         "DMS1 0 0 4","DMS1 0 1000000001 3","DMS1 0 x 3"}) {
        GlowtrailGame F;F.Reset(8);F.SetOption(1,8);
        Check(!F.RestoreState(Bad,8) && F.GetOption()==1 && F.GetStatus().Score==0,std::string("glowtrail rejects '")+Bad+"'");
    }
}

void ThroughDriver() {
    for(const char* Id:{"football","glowtrail"}) {
        Driver D;D.Select(Id,5);
        Input I;I.FirePressed=true;D.SetInput(I);
        for(int N=0;N<30;++N) D.Advance(Driver::StepSeconds);
        const std::string Save=D.CaptureSave();
        Check(!Save.empty(),std::string(Id)+": driver captures a save");
        Driver E;E.Select(Id,5);
        Check(E.RestoreSave(Save) && E.CaptureSave()==Save,std::string(Id)+": driver restore round-trips");
        Check(E.Advance(Driver::StepSeconds)==1,std::string(Id)+": restored run steps");
    }
}
}  // namespace

int main() {
    Football();Glowtrail();ThroughDriver();
    std::cout<<"save checkpoints: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
