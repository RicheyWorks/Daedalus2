// SPDX-License-Identifier: MIT
// Checkpoint saves for Threadlight Dungeon (DDS1) and Lanternwild Quest / zelda (DZS1).
// catalog-capability: save_restore: dungeon zelda
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void LightDungeon(DungeonGame& G,int Count,bool Trail,std::uint64_t Frames) {
        for(int N=0;N<Count;++N) G.Lit[static_cast<std::size_t>(G.Order[static_cast<std::size_t>(N)])]=true;
        G.LitCount=Count;G.TrailEnabled=Trail;G.RunFrames=Frames;G.Started=true;
    }
    static void FinishDungeon(DungeonGame& G) {G.Complete=true;}
    static void ZeldaStats(ZeldaGame& G,std::int64_t Score,int Health,int Rupees) {G.Score=Score;G.Hero.Health=Health;G.Hero.Rupees=Rupees;}
    static void EndZelda(ZeldaGame& G,bool Won) {G.Over=!Won;G.Won=Won;}
};
}}  // namespace daedalus::desktop
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}

void Dungeon() {
    for(int Room=0;Room<2;++Room) for(int Lit=0;Lit<=3;++Lit) {
        DungeonGame G;G.SetOption(Room,4);MazeTestAccess::LightDungeon(G,Lit,Lit%2==1,600+Lit);
        const std::string Save=G.SaveState();
        const std::string Tag="dungeon room "+std::to_string(Room)+" lit "+std::to_string(Lit)+": ";
        Check(Save.rfind("DDS1 ",0)==0,Tag+"payload is DDS1");
        DungeonGame H;
        Check(H.RestoreState(Save,999),Tag+"restores");
        Check(H.GetOption()==Room && H.GetLitCount()==Lit && H.GetElapsedFrames()==static_cast<std::uint64_t>(600+Lit),Tag+"room, lanterns and time restored");
        Check(H.SaveState()==Save,Tag+"round trip");
        Check(H.SeedAfterRestore(999)==4,Tag+"circuit seed comes from the save, not the host");
        Check(H.GetStatus().Note==G.GetStatus().Note,Tag+"same circuit, progress and trail text");
        Check(H.GetPlayer().X==DungeonGame::Player{}.X && H.GetPlayer().Y==DungeonGame::Player{}.Y,Tag+"restart at the start tile");
        Check(H.GetCircuitStage()==(Lit==3?DungeonGame::CircuitStage::ExitUnlocked:DungeonGame::CircuitStage::Lanterns),Tag+"stage follows lanterns");
    }
    DungeonGame C;MazeTestAccess::FinishDungeon(C);
    Check(C.SaveState().empty(),"completed dungeon is not saved");
    for(const char* Bad:{"","DDS2 0 1 0 0 0","DDS1 0 1 0 0","DDS1 0 1 0 0 0 x","DDS1 2 1 0 0 0","DDS1 0 -1 0 0 0",
                         "DDS1 0 2147483648 0 0 0","DDS1 0 1 4 0 0","DDS1 0 1 -1 0 0","DDS1 0 1 0 2 0","DDS1 0 1 0 0 -1"}) {
        DungeonGame G;G.SetOption(1,2);MazeTestAccess::LightDungeon(G,1,false,5);
        Check(!G.RestoreState(Bad,2) && G.GetOption()==1 && G.GetLitCount()==1,std::string("dungeon rejects '")+Bad+"'");
    }
}

void Zelda() {
    for(int Mode=0;Mode<2;++Mode) {
        ZeldaGame G;G.SetOption(Mode,6);MazeTestAccess::ZeldaStats(G,350,4,7);
        G.Step([] {Input I;I.DashPressed=true;return I;}());
        const std::string Save=G.SaveState();
        const std::string Tag="zelda mode "+std::to_string(Mode)+": ";
        Check(Save.rfind("DZS1 ",0)==0,Tag+"payload is DZS1");
        ZeldaGame H;
        Check(H.RestoreState(Save,6),Tag+"restores");
        Check(H.GetOption()==Mode && H.GetStatus().Score==350 && H.GetStatus().Lives==4,Tag+"option, score and health restored");
        Check(H.IsSwordAssistEnabled()==G.IsSwordAssistEnabled(),Tag+"live assist toggle restored");
        Check(H.SaveState()==Save,Tag+"round trip");
        ZeldaGame Fresh;Fresh.SetOption(Mode,6);
        Check(H.GetStatus().Note.find("Enemies left: 4/4")!=std::string::npos,Tag+"fresh roster");
        (void)Fresh;
    }
    for(bool Won:{false,true}) {ZeldaGame E;MazeTestAccess::EndZelda(E,Won);Check(E.SaveState().empty(),"finished zelda is not saved");}
    for(const char* Bad:{"","DZS2 0 0 6 0 0","DZS1 0 0 6 0","DZS1 0 0 6 0 0 x","DZS1 2 0 6 0 0","DZS1 0 -1 6 0 0",
                         "DZS1 0 0 0 0 0","DZS1 0 0 7 0 0","DZS1 0 0 6 -1 0","DZS1 0 0 6 0 2","DZS1 0 1000000001 6 0 0"}) {
        ZeldaGame G;G.SetOption(1,3);MazeTestAccess::ZeldaStats(G,10,5,1);
        Check(!G.RestoreState(Bad,3) && G.GetOption()==1 && G.GetStatus().Score==10,std::string("zelda rejects '")+Bad+"'");
    }
}

void ThroughDriver() {
    for(const char* Id:{"dungeon","zelda"}) {
        Driver D;D.Select(Id,3);Input I;I.Right=true;D.SetInput(I);
        for(int N=0;N<20;++N) D.Advance(Driver::StepSeconds);
        const std::string Save=D.CaptureSave();
        Driver E;E.Select(Id,77);
        Check(!Save.empty() && E.RestoreSave(Save) && E.CaptureSave()==Save,std::string(Id)+": driver Continue round-trips");
    }
}
}  // namespace

int main() {
    Dungeon();Zelda();ThroughDriver();
    std::cout<<"maze saves: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
