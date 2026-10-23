// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void Mixed(PacmanGame& G,int Shortest) {
        for(auto& E:G.Ghosts) {E.X=-1000;E.Y=-1000;E.Alive=true;E.Frightened=false;E.FrightenedTimer=0;}
        G.Ghosts[0].Frightened=true;G.Ghosts[0].FrightenedTimer=180;
        G.Ghosts[1].Frightened=true;G.Ghosts[1].FrightenedTimer=Shortest;
        G.Ghosts[2].Alive=false;G.Ghosts[2].Frightened=true;G.Ghosts[2].FrightenedTimer=1;
        G.RespawnFrames=50;
    }
    static void PowerPickup(PacmanGame& G) {
        for(auto& E:G.Ghosts) {E.X=-1000;E.Y=-1000;E.Frightened=false;E.FrightenedTimer=0;}
        // Isolate the pickup/timer from collisions while retaining real Step and RNG updates.
        G.Pellets={{G.Hero.X,G.Hero.Y,true,true},{10,10,false,true}};G.Remaining=2;
    }
    static void ClearFright(PacmanGame& G,bool AllDead) {
        for(auto& E:G.Ghosts) {E.Frightened=false;E.Alive=!AllDead;}
    }
    static void Terminal(PacmanGame& G,bool Won) {G.Won=Won;G.Over=!Won;}
    static std::string Snapshot(const PacmanGame& G) {
        std::ostringstream Out;
        Out.precision(17);
        Out<<G.SessionSeed<<' '<<G.Score<<' '<<G.Lives<<' '<<G.Remaining<<' '<<G.Level<<' '<<G.RespawnFrames<<' '<<G.Over<<' '<<G.Won;
        Out<<' '<<G.Hero.X<<' '<<G.Hero.Y<<' '<<G.Hero.Dir.X<<' '<<G.Hero.Dir.Y<<' '<<G.Hero.Next.X<<' '<<G.Hero.Next.Y<<' '<<G.Hero.Mouth;
        for(const auto& E:G.Ghosts)
            Out<<' '<<E.X<<' '<<E.Y<<' '<<E.Dir.X<<' '<<E.Dir.Y<<' '<<static_cast<int>(E.Tint.R)<<' '<<static_cast<int>(E.Tint.G)
                <<' '<<static_cast<int>(E.Tint.B)<<' '<<static_cast<int>(E.Tint.A)<<' '<<E.Alive<<' '<<E.Frightened<<' '<<E.FrightenedTimer;
        Out<<' '<<G.Pellets.size();
        for(const auto& P:G.Pellets) Out<<' '<<P.X<<' '<<P.Y<<' '<<P.Power<<' '<<P.Alive;
        Random Copy=G.Rng;Out<<' '<<Copy.Next(); // Observe a copied stream, never the game's RNG.
        return Out.str();
    }
};
}}

namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
const DrawCommand* Text(const Frame& F,const std::string& Label) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label==Label) return &C;
    return nullptr;
}
bool HasLiveCountdown(const Frame& F) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && (C.Label.find("First recovery:")==0 || C.Label=="FINAL SECOND")) return true;
    return false;
}
}

int main() {
    PacmanGame G;G.Reset(730);MazeTestAccess::Mixed(G,61);
    auto Window=G.GetPowerWindow();
    Check(Window.Alive==3 && Window.Frightened==2 && Window.Frames==61 && Window.Seconds()==2,"window counts only living frightened pursuers and uses shortest timer");
    Frame F;G.Render(F);
    Check(Text(F,"Frightened: 2/3 alive") && Text(F,"First recovery: 2s"),"mixed power HUD does not imply every living pursuer is frightened");
    Check(G.GetStatus().Note.find("Frightened 2/3 alive.")!=std::string::npos && G.GetStatus().Note.find("First recovery: 2s.")!=std::string::npos,"status exposes the same conservative mixed window");

    MazeTestAccess::Mixed(G,60);G.Render(F);
    const DrawCommand* Ending=Text(F,"FINAL SECOND");
    const DrawCommand* Grace=Text(F,"Respawn grace: 50 steps");
    Check(Ending && Ending->Tint.R==255 && Ending->Tint.G==180,"last second has a steady explicit warning");
    Check(Ending && Grace && Ending->A.Y+Ending->Size<Grace->A.Y,"power warning and respawn grace do not overlap vertically");
    Check(G.GetStatus().Note.find("First recovery: 1s (final second).")!=std::string::npos,"last second rounds upward and is named in status");
    PacmanGame Unobserved=G;const std::string Before=MazeTestAccess::Snapshot(G);
    for(int N=0;N<40;++N) {G.Render(F);G.GetStatus();G.GetPowerWindow();}
    Check(MazeTestAccess::Snapshot(G)==Before,"repeated presentation reads preserve complete gameplay and RNG state");
    Check(Text(F,"FINAL SECOND") && Text(F,"First recovery: 1s"),"warning remains steady without presentation-driven flashing");
    for(int N=0;N<20;++N) {Input I;I.PadRight=N<10;G.Step(I);Unobserved.Step(I);}
    Check(MazeTestAccess::Snapshot(G)==MazeTestAccess::Snapshot(Unobserved),"extra presentation calls do not change future simulation or randomness");

    G.Reset(730);MazeTestAccess::ClearFright(G,false);G.Render(F);
    Window=G.GetPowerWindow();
    Check(Window.Alive==4 && Window.Frightened==0 && Window.Frames==0 && Window.Seconds()==0,"no active power has no stale timer");
    Check(Text(F,"Frightened: 0/4 alive") && Text(F,"No active fright window") && !HasLiveCountdown(F),"ordinary HUD clearly reports no active window");
    MazeTestAccess::ClearFright(G,true);Window=G.GetPowerWindow();
    Check(Window.Alive==0 && Window.Frightened==0 && Window.Frames==0,"all-dead view is bounded and contains no active window");

    for(bool Won:{false,true}) {
        G.Reset(730);MazeTestAccess::Mixed(G,1);MazeTestAccess::Terminal(G,Won);G.Render(F);
        const auto Note=G.GetStatus().Note;
        Check(Text(F,Won?"YOU WIN!":"GAME OVER") && !HasLiveCountdown(F),"terminal result replaces live countdown");
        Check(Note.find("First recovery:")==std::string::npos && Note.find("Frightened")==std::string::npos,"terminal status does not suggest a running power timer");
    }

    G.Reset(730);MazeTestAccess::PowerPickup(G);G.Step({});
    Check(G.GetStatus().Score==50 && G.DotsLeft()==1 && !G.GetStatus().Over && !G.GetStatus().Won,"real power pickup starts an unfinished live game");
    struct Boundary {int Frames,Seconds;bool Ending;};
    int Remaining=300;
    for(const Boundary B:std::array<Boundary,8>{{{300,5,false},{299,5,false},{241,5,false},{240,4,false},{61,2,false},{60,1,true},{1,1,true},{0,0,false}}}) {
        while(Remaining>B.Frames) {G.Step({});--Remaining;}
        Window=G.GetPowerWindow();G.Render(F);
        Check(Window.Alive==4 && Window.Frightened==(B.Frames?4:0) && Window.Frames==B.Frames && Window.Seconds()==B.Seconds,"real 300-step expiry retains existing count and ceiling seconds at boundaries");
        Check((Text(F,"FINAL SECOND")!=nullptr)==B.Ending,"final-second cue follows real source timer boundaries");
    }
    Check(Text(F,"No active fright window") && !HasLiveCountdown(F),"expiry clears countdown without extending source effect");
    std::cout<<"Pacman power-window display: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
