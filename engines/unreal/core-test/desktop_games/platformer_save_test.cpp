// SPDX-License-Identifier: MIT
// Checkpoint saves for ironwake (DCS1), emberstep (DNS1) and dodge_ball (DBS1).
// catalog-capability: save_restore: ironwake emberstep dodge_ball
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>
#include <utility>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static void Ironwake(IronwakeGame& G,std::int64_t Score,int Lives,bool Spread,int Hits) {G.Player.Score=Score;G.Player.Lives=Lives;G.Player.Spread=Spread;G.RangeStage=Hits;}
    static void EndIronwake(IronwakeGame& G,bool Won) {G.Over=true;G.Won=Won;}
    static bool Spread(const IronwakeGame& G) {return G.Player.Spread;}
    static void Ninja(EmberstepGame& G,std::int64_t Score,int Health,int Stage) {G.Score=Score;G.Player.Health=Health;G.CourseStage=Stage;}
    static void EndNinja(EmberstepGame& G,bool Won) {G.Over=true;G.Won=Won;}
    static int Stage(const EmberstepGame& G) {return G.CourseStage;}
    static double PlayerX(const EmberstepGame& G) {return G.Player.X;}
};
}}}  // namespace daedalus::desktop::platformers
using platformers::TestAccess;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}

void Ironwake() {
    for(int Mode=0;Mode<2;++Mode) {
        IronwakeGame G;G.SetOption(Mode,5);TestAccess::Ironwake(G,700,30,true,Mode==1?2:0);
        const std::string Save=G.SaveState();const std::string Tag="ironwake mode "+std::to_string(Mode)+": ";
        Check(Save=="DCS1 "+std::to_string(Mode)+" 700 30 1 "+(Mode==1?"2":"0"),Tag+"payload "+Save);
        IronwakeGame H;Check(H.RestoreState(Save,5),Tag+"restores");
        Check(H.GetOption()==Mode && H.GetStatus().Score==700 && H.GetStatus().Lives==30 && TestAccess::Spread(H)
            && H.GetRangeHits()==(Mode==1?2:0),Tag+"fields");
        Check(H.SaveState()==Save && !H.GetStatus().Over,Tag+"round trip, live run");
    }
    for(bool Won:{false,true}) {IronwakeGame E;TestAccess::EndIronwake(E,Won);Check(E.SaveState().empty(),"finished ironwake not saved");}
    for(const char* Bad:{"","DCS2 0 0 3 0 0","DCS1 0 0 3 0","DCS1 0 0 3 0 0 x","DCS1 2 0 3 0 0","DCS1 0 -1 3 0 0","DCS1 0 0 0 0 0",
                         "DCS1 0 0 100 0 0","DCS1 0 0 3 2 0","DCS1 0 0 3 0 1","DCS1 1 0 3 0 3"}) {
        IronwakeGame G;G.SetOption(1,2);TestAccess::Ironwake(G,40,2,false,1);
        Check(!G.RestoreState(Bad,2) && G.GetOption()==1 && G.GetStatus().Score==40 && G.GetRangeHits()==1,std::string("ironwake rejects '")+Bad+"'");
    }
}

void Ninja() {
    for(int Mode=0;Mode<2;++Mode) {
        EmberstepGame G;G.SetOption(Mode,5);TestAccess::Ninja(G,650,3,Mode==1?2:0);
        const std::string Save=G.SaveState();const std::string Tag="ninja mode "+std::to_string(Mode)+": ";
        Check(Save=="DNS1 "+std::to_string(Mode)+" 650 3 "+(Mode==1?"2":"0"),Tag+"payload "+Save);
        EmberstepGame H;Check(H.RestoreState(Save,5),Tag+"restores");
        Check(H.GetOption()==Mode && H.GetStatus().Score==650 && H.GetStatus().Lives==3 && TestAccess::Stage(H)==(Mode==1?2:0),Tag+"fields");
        if(Mode==1) Check(TestAccess::PlayerX(H)==640,Tag+"stands on the last lit terrace");
        Check(H.SaveState()==Save && !H.GetStatus().Over,Tag+"round trip, live run");
    }
    for(bool Won:{false,true}) {EmberstepGame E;TestAccess::EndNinja(E,Won);Check(E.SaveState().empty(),"finished ninja not saved");}
    for(const char* Bad:{"","DNS2 0 0 3 0","DNS1 0 0 3","DNS1 0 0 3 0 x","DNS1 2 0 3 0","DNS1 0 -1 3 0","DNS1 0 0 0 0",
                         "DNS1 0 0 6 0","DNS1 0 0 3 1","DNS1 1 0 3 3"}) {
        EmberstepGame G;G.SetOption(1,2);TestAccess::Ninja(G,40,2,1);
        Check(!G.RestoreState(Bad,2) && G.GetOption()==1 && G.GetStatus().Score==40 && TestAccess::Stage(G)==1,std::string("ninja rejects '")+Bad+"'");
    }
}

void Dodge() {
    DodgeBallGame T;Check(T.SaveState().empty(),"dodge title not saved");
    DodgeBallGame G;G.Data.SelectedCountry=2;G.Data.OpponentCountry=5;G.StartMatch();G.Data.HumanScore=1;G.Data.CpuScore=1;G.Data.Round=3;
    const std::string Save=G.SaveState();
    Check(Save=="DBS1 2 5 1 1 3","dodge payload "+Save);
    DodgeBallGame H;Check(H.RestoreState(Save,9),"dodge restores");
    Check(H.Data.Mode==DodgeBallGame::Phase::Playing && H.Data.SelectedCountry==2 && H.Data.OpponentCountry==5
        && H.Data.HumanScore==1 && H.Data.CpuScore==1 && H.Data.Round==3,"dodge fields");
    bool Fresh=true;for(const auto& P:H.Data.Players) Fresh=Fresh && P.Health==3;
    Check(Fresh && H.Data.Players[1].HasBall,"dodge round replays from kickoff");
    Check(H.SaveState()==Save,"dodge round trip");
    G.Data.Mode=DodgeBallGame::Phase::Won;Check(G.SaveState().empty(),"dodge round result not saved");
    for(const char* Bad:{"","DBS2 0 1 0 0 1","DBS1 0 1 0 0","DBS1 0 1 0 0 1 x","DBS1 8 1 0 0 1","DBS1 0 0 0 0 1","DBS1 0 1 0 0 5",
                         "DBS1 0 1 0 0 0","DBS1 0 1 1 0 1","DBS1 0 1 -1 1 1"}) {
        DodgeBallGame B;B.Data.SelectedCountry=3;B.Data.OpponentCountry=4;B.StartMatch();
        Check(!B.RestoreState(Bad,2) && B.Data.SelectedCountry==3 && B.Data.Round==1,std::string("dodge rejects '")+Bad+"'");
    }
}

void ThroughDriver() {
    for(const auto& [Id,Payload]:{std::pair<const char*,const char*>{"ironwake","DCS1 0 700 3 1 0"},{"emberstep","DNS1 0 650 4 0"},{"dodge_ball","DBS1 2 5 1 0 2"}}) {
        Driver E;E.Select(Id,3);
        Check(E.RestoreSave(Payload) && E.CaptureSave()==Payload,std::string(Id)+": driver Continue round-trips");
    }
    Driver T;T.Select("dodge_ball",3);Check(T.CaptureSave().empty(),"dodge_ball: driver title has no save");
}
}  // namespace

int main() {
    Ironwake();Ninja();Dodge();ThroughDriver();
    std::cout<<"platformer/dodge saves: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
