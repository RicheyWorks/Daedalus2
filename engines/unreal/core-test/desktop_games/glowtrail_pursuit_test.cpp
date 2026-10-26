// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void Crossing(GlowtrailGame& G) {
        G.Reset(730);G.Hero={};G.Hero.X=530;G.Hero.Y=290;
        for(auto& P:G.Pellets) P.Alive=false;
        G.Pellets.front().Alive=true;G.Remaining=1;
        for(auto& E:G.Ghosts) E.Alive=false;
        auto& E=G.Ghosts[0];E.Alive=true;E.X=.5;E.Y=290;E.Dir={1,0};E.Frightened=false;
        G.Rng.Seed(0x80000000u); // No initial turn; chase sample is below .6.
    }
    static std::uint32_t NextRandom(const GlowtrailGame& G) {auto R=G.Rng;return R.Next();}
};
}}
namespace {
using Ghost=GlowtrailGame::Ghost;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
Ghost At(double X,double Y=290,int Dx=0,int Dy=0) {Ghost G;G.X=X;G.Y=Y;G.Dir={Dx,Dy};return G;}
void Aim(Ghost& G,double X,double Y=290,double Turn=1,double Chase=0,bool RepairDoor=true,bool UseTunnels=true) {
    GlowtrailGame::Player P;P.X=X;P.Y=Y;G.UpdateWithChoices(P,Turn,Chase,{{{1,0},{-1,0},{0,1},{0,-1}}},RepairDoor,UseTunnels);
}
void Position(const Ghost& G,double X,double Y,int Dx,int Dy,const char* Why) {Check(Close(G.X,X)&&Close(G.Y,Y)&&G.Dir.X==Dx&&G.Dir.Y==Dy,Why);}
void EdgePursuit() {
    auto G=At(.5);Aim(G,550);Position(G,558.5,290,-1,0,"left-edge ghost pursues through seam with fractional overshoot");
    G=At(559.5);Aim(G,10);Position(G,1.5,290,1,0,"right-edge ghost pursues through seam with fractional overshoot");
    G=At(10);Aim(G,408);Position(G,8,290,-1,0,"fully clear right target approach permits the shorter seam route");
    G=At(152.9);Aim(G,550);Position(G,150.9,290,-1,0,"quantized left body ending at pixel159 has a clear seam approach");
    G=At(.5);Aim(G,550,292.5);Position(G,558.5,290,-1,0,"last valid quantized target row remains tunnel eligible");
    G=At(.5,288);Aim(G,559.5,292.5);Position(G,.5,290,0,1,"existing axis comparison uses the wrapped distance while preserving vertical delta");
    G=At(.5);Aim(G,550,290,1,0,false,true);Position(G,558.5,290,-1,0,"door repair flag does not disable a clear passage");
}
void RouteFences() {
    auto G=At(10);Aim(G,407.999);Position(G,12,290,1,0,"target body still touching wall column19 keeps raw pursuit");
    G=At(230);Aim(G,550);Position(G,232,290,1,0,"left wall blocks a central-compartment ghost from shortcutting to the seam");
    G=At(330);Aim(G,10);Position(G,328,290,-1,0,"right wall likewise blocks a central-compartment reverse shortcut");
    G=At(10);Aim(G,350);Position(G,12,290,1,0,"central target cannot be reached through its obstructed edge approach");
    G=At(.5);Aim(G,550,293);Position(G,2.5,290,1,0,"target spanning the adjacent row retains raw direction");
    G=At(130,293);Aim(G,550);Position(G,132,293,1,0,"off-row ghost in an ordinary vertical corridor retains raw direction");
    G=At(-.5);Aim(G,550);Position(G,1.5,290,1,0,"noncanonical ghost cannot choose a periodic chase alias");
    G=At(.5);Aim(G,560.5);Position(G,2.5,290,1,0,"noncanonical target cannot choose a periodic chase alias");
    G=At(10);Aim(G,550,290,1,0,false,false);Position(G,12,290,1,0,"false,false source mode retains the original raw chase");
    G=At(150);Aim(G,430);Position(G,152,290,1,0,"positive half-period tie keeps raw direction");
    G=At(430);Aim(G,150);Position(G,428,290,-1,0,"negative half-period tie keeps raw direction");
    G=At(100);Aim(G,145);Position(G,102,290,1,0,"already short positive path is unchanged");
    G=At(450);Aim(G,410);Position(G,448,290,-1,0,"already short negative path is unchanged");
    G=At(152,290,-1);Aim(G,200);Position(G,150,290,-1,0,"blocked chase probe still preserves the existing legal direction");
}
void OriginalDecisionGates() {
    auto G=At(.5,290,1);Aim(G,550,290,1,.6);Position(G,2.5,290,1,0,"exact chase probability boundary leaves current movement unchanged");
    G=At(.5,290,1);Aim(G,550,290,1,.599999);Position(G,558.5,290,-1,0,"sample below the original boundary can choose the seam");
    G=At(.5);Aim(G,550,290,0,1);Position(G,2.5,290,1,0,"nonchasing random turn still takes the first supplied valid choice");
    G=At(.5);Aim(G,550,290,0,0);Position(G,558.5,290,-1,0,"accepted chase retains its existing priority after an initial random turn");
    G=At(.5,290,1);G.Frightened=true;G.FrightenedTimer=2;Aim(G,550);
    Position(G,2.5,290,1,0,"still-frightened ghost does not start pursuing through the seam");Check(G.Frightened&&G.FrightenedTimer==1,"living fright timer still ticks once");
    G=At(.5,290,1);G.Frightened=true;G.FrightenedTimer=1;Aim(G,550);
    Position(G,558.5,290,-1,0,"expiry on this decision restores normal seam pursuit");Check(!G.Frightened&&G.FrightenedTimer==0,"fright expiry keeps its existing timing");
    G=At(.5,290,1);G.Alive=false;G.Frightened=true;G.FrightenedTimer=1;Aim(G,550,290,0,0);
    Position(G,.5,290,1,0,"dead ghost does not turn or cross");Check(G.Frightened&&G.FrightenedTimer==1,"dead ghost does not consume its fright timer");
}
void RandomAndGameStep() {
    GlowtrailGame::Player P;P.X=550;P.Y=290;Random SeamRandom,OrdinaryRandom,Expected;SeamRandom.Seed(730);OrdinaryRandom=Expected=SeamRandom;
    auto Seam=At(.5),Ordinary=At(130);Seam.Update(P,SeamRandom);Ordinary.Update(P,OrdinaryRandom);
    for(int N=0;N<5;++N) Expected.Next();
    const auto Sixth=Expected.Next();
    Check(SeamRandom.Next()==Sixth&&OrdinaryRandom.Next()==Sixth,"actual alive updates retain exactly two samples plus three shuffle draws");
    auto Dead=At(.5);Dead.Alive=false;Dead.Frightened=true;Dead.FrightenedTimer=3;Random R;R.Seed(730);Expected=R;Dead.Update(P,R);
    Check(R.Next()==Expected.Next()&&Dead.FrightenedTimer==3&&Dead.X==.5,"actual dead update consumes neither RNG nor timer");
    GlowtrailGame G;MazeTestAccess::Crossing(G);Expected.Seed(0x80000000u);const double Turn=Expected.Unit(),Chase=Expected.Unit();
    Check(Turn>=.05&&Chase<.6,"full-game fixture uses normal nonturning chase samples");
    for(int N=0;N<3;++N) Expected.Next();
    const auto Next=Expected.Next();G.Step({});const auto& E=G.GetGhosts()[0];
    Position(E,558.5,290,-1,0,"full game Step uses passage pursuit rather than continuing away from the player");
    Check(G.GetPlayer().X==530&&G.GetPlayer().Y==290&&G.GetStatus().Lives==3&&G.GetStatus().Score==0&&G.DotsLeft()==1&&E.Alive,"crossing preserves unrelated collectible, player and progress");
    Check(MazeTestAccess::NextRandom(G)==Next,"full-game crossing consumes the original five ghost random draws only");
}
}
int main() {
    EdgePursuit();RouteFences();OriginalDecisionGates();RandomAndGameStep();
    std::cout<<"Glowtrail tunnel pursuit: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
