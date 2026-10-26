// SPDX-License-Identifier: MIT
// Checkpoint saves for Driftstone Patrol / driftstone (DAS1) and Gleamwing Sentinel / riftwing (DSS1).
// catalog-capability: save_restore: driftstone riftwing
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct DriftstoneTestAccess {
    static void Stats(DriftstoneGame& G,std::int64_t Score,int Lives,int Level) {G.Score=Score;G.Lives=Lives;G.Level=Level;}
    static void End(DriftstoneGame& G,bool Won) {G.Over=!Won;G.Won=Won;}
    static std::size_t Rocks(const DriftstoneGame& G) {return G.Rocks.size();}
    static int Level(const DriftstoneGame& G) {return G.Level;}
};
struct RiftwingTestAccess {
    static void Stats(RiftwingGame& G,std::int64_t Score,int Lives,int Power) {G.Score=Score;G.Pilot.Lives=Lives;G.Pilot.Power=Power;}
    static void End(RiftwingGame& G,bool Won) {G.Over=!Won;G.Won=Won;}
    static int Power(const RiftwingGame& G) {return G.Pilot.Power;}
};
}}  // namespace daedalus::desktop
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}

void Driftstone() {
    for(int Mode=0;Mode<2;++Mode) for(int Level:{1,3}) {
        DriftstoneGame G;G.SetOption(Mode,5);DriftstoneTestAccess::Stats(G,1250,2,Level);
        const std::string Save=G.SaveState();
        const std::string Tag="driftstone mode "+std::to_string(Mode)+" level "+std::to_string(Level)+": ";
        Check(Save=="DAS1 "+std::to_string(Mode)+" 1250 2 "+std::to_string(Level),Tag+"payload "+Save);
        DriftstoneGame H;
        Check(H.RestoreState(Save,5),Tag+"restores");
        Check(H.GetOption()==Mode && H.GetStatus().Score==1250 && H.GetStatus().Lives==2 && DriftstoneTestAccess::Level(H)==Level,Tag+"mode, score, lives, level");
        Check(DriftstoneTestAccess::Rocks(H)==(Level==1?6u:static_cast<std::size_t>(4+Level)),Tag+"fresh field sized for the level");
        Check(H.SaveState()==Save,Tag+"round trip");
        Check(!H.GetStatus().Over,Tag+"live run");
    }
    DriftstoneGame P;P.SetOption(2,1);Check(P.SaveState().empty(),"flight practice is not saved");
    for(bool Won:{false,true}) {DriftstoneGame E;DriftstoneTestAccess::End(E,Won);Check(E.SaveState().empty(),"finished driftstone not saved");}
    for(const char* Bad:{"","DAS2 0 0 3 1","DAS1 0 0 3","DAS1 0 0 3 1 x","DAS1 2 0 3 1","DAS1 0 -1 3 1","DAS1 0 0 0 1",
                         "DAS1 0 0 4 1","DAS1 0 0 3 0","DAS1 1 0 3 4","DAS1 0 1000000000001 3 1"}) {
        DriftstoneGame G;G.SetOption(1,2);DriftstoneTestAccess::Stats(G,40,2,2);
        Check(!G.RestoreState(Bad,2) && G.GetOption()==1 && G.GetStatus().Score==40,std::string("driftstone rejects '")+Bad+"'");
    }
}

void Riftwing() {
    for(int Mode=0;Mode<2;++Mode) {
        RiftwingGame G;G.SetOption(Mode,5);RiftwingTestAccess::Stats(G,900,4,3);
        const std::string Save=G.SaveState();
        const std::string Tag="riftwing mode "+std::to_string(Mode)+": ";
        Check(Save=="DSS1 "+std::to_string(Mode)+" 900 4 3",Tag+"payload "+Save);
        RiftwingGame H;
        Check(H.RestoreState(Save,5),Tag+"restores");
        Check(H.GetOption()==Mode && H.GetStatus().Score==900 && H.GetStatus().Lives==4 && RiftwingTestAccess::Power(H)==3,Tag+"mode, score, lives, power");
        Check(H.SaveState()==Save,Tag+"round trip");
        Check(!H.GetStatus().Over,Tag+"live run");
    }
    for(bool Won:{false,true}) {RiftwingGame E;RiftwingTestAccess::End(E,Won);Check(E.SaveState().empty(),"finished riftwing not saved");}
    for(const char* Bad:{"","DSS2 0 0 3 1","DSS1 0 0 3","DSS1 0 0 3 1 x","DSS1 2 0 3 1","DSS1 0 -1 3 1","DSS1 0 0 0 1",
                         "DSS1 0 0 6 1","DSS1 0 0 3 0","DSS1 0 0 3 4"}) {
        RiftwingGame G;G.SetOption(1,2);RiftwingTestAccess::Stats(G,40,2,2);
        Check(!G.RestoreState(Bad,2) && G.GetOption()==1 && G.GetStatus().Score==40,std::string("riftwing rejects '")+Bad+"'");
    }
}

void ThroughDriver() {
    for(const char* Id:{"driftstone","riftwing"}) {
        Driver D;D.Select(Id,3);
        for(int N=0;N<20;++N) D.Advance(Driver::StepSeconds);
        const std::string Save=D.CaptureSave();
        Driver E;E.Select(Id,3);
        Check(!Save.empty() && E.RestoreSave(Save) && E.CaptureSave()==Save,std::string(Id)+": driver Continue round-trips");
    }
}
}  // namespace

int main() {
    Driftstone();Riftwing();ThroughDriver();
    std::cout<<"shooter saves: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
