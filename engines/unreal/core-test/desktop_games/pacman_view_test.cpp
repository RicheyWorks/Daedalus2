// SPDX-License-Identifier: MIT
// Glowtrail viewing: gold power pellets, and frightened ghosts that read on blue walls.
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <iostream>
#include <string>

namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void Fright(PacmanGame& G) {
        auto& E=G.Ghosts[0];
        E.X=400; E.Y=300; E.Alive=true; E.Frightened=true; E.FrightenedTimer=120;
    }
};
}}

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Gold(const Color& C) { return C.R==255 && C.G==204 && C.B==40; }
bool White(const Color& C) { return C.R==255 && C.G==255 && C.B==255; }
bool Pale(const Color& C) { return C.R==190 && C.G==210 && C.B==255; }
void Pellets() {
    PacmanGame G;
    const auto Note=G.GetStatus().Note;
    Frame F;G.Render(F);
    Check(G.GetStatus().Note==Note,"pellet view leaves status unchanged");
    int Powers=0,Dots=0;
    for(const auto& C:F.Commands) if(C.Kind==Shape::Circle) {
        if(C.Size==6) { ++Powers; Check(Gold(C.Tint),"power pellet is gold"); }
        if(C.Size==3 && White(C.Tint)) ++Dots;
    }
    Check(Powers==4 && Dots>0,"four gold power pellets stay distinct from white dots");
}
void WallCap() {
    PacmanGame G;
    Check(PacmanGame::IsWall(0,0),"the corner cell is a wall");
    Frame F;G.Render(F);
    std::size_t Full=F.Commands.size(),Cap=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Rectangle || C.A.X!=0 || C.A.Y!=0) continue;
        if(C.B.X==PacmanGame::Tile && C.B.Y==PacmanGame::Tile && C.Tint.R==0 && C.Tint.G==0 && C.Tint.B==180) Full=N;
        if(C.B.X==PacmanGame::Tile && C.B.Y==4 && C.Tint.R==110 && C.Tint.G==150 && C.Tint.B==255) Cap=N;
    }
    Check(Full<Cap && Cap<F.Commands.size(),"maze walls keep a light top edge");
    Check(F.Commands.size()<Frame::MaxCommands,"wall edges stay inside the frame budget");
}
void HeroRing() {
    PacmanGame G;
    const auto& P=G.GetPlayer();
    Frame F;G.Render(F);
    std::size_t Ring=F.Commands.size(),Body=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=P.X || C.A.Y!=P.Y) continue;
        if(C.Size==12 && C.Tint.R==24 && C.Tint.G==24 && C.Tint.B==24) Ring=N;
        if(C.Size==10 && C.Tint.R==255 && C.Tint.G==255 && C.Tint.B==0) Body=N;
    }
    Check(Ring<Body && Body<F.Commands.size(),"hero keeps a dark ring behind the yellow body");
}
void GhostRim() {
    PacmanGame G;
    Frame F;G.Render(F);
    std::size_t Rim=F.Commands.size(),Body=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=290 || C.A.Y!=290) continue;
        if(C.Size==12 && C.Tint.R==12 && C.Tint.G==16 && C.Tint.B==48) Rim=N;
        if(C.Size==9 && C.Tint.R==0 && C.Tint.G==255 && C.Tint.B==255) Body=N;
    }
    Check(Rim<Body && Body<F.Commands.size(),"cyan ghost keeps a dark ring on the blue walls");
}
void Fright() {
    PacmanGame G;
    MazeTestAccess::Fright(G);
    Frame F;G.Render(F);
    std::size_t Halo=F.Commands.size(),Body=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=400 || C.A.Y!=300) continue;
        if(C.Size==11 && White(C.Tint)) Halo=N;
        if(C.Size==9 && Pale(C.Tint)) Body=N;
    }
    Check(Halo<Body && Body<F.Commands.size(),"frightened ghost has a white halo behind a pale body");
}
}

int main() {
    try { Pellets();WallCap();HeroRing();GhostRim();Fright(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
