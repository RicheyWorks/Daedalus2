// SPDX-License-Identifier: MIT
// Dungeon viewing: the player tile keeps a white corner mark above lanterns and the exit.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <cstdint>
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
using Dungeon=DungeonGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool IsGreenBody(const DrawCommand& C,const Dungeon& G) {
    return C.Kind==Shape::Rectangle && C.Tint.R==0 && C.Tint.G==255 && C.Tint.B==0
        && C.A.X==G.GetPlayer().X && C.A.Y==G.GetPlayer().Y && C.B.X==Dungeon::Tile && C.B.Y==Dungeon::Tile;
}
bool IsCorner(const DrawCommand& C,const Dungeon& G) {
    return C.Kind==Shape::Rectangle && C.Tint.R==255 && C.Tint.G==255 && C.Tint.B==255
        && C.A.X==G.GetPlayer().X && C.A.Y==G.GetPlayer().Y && C.B.X==8 && C.B.Y==3;
}
void MarkOrder(const Dungeon& G,const std::string& What) {
    Frame F;const auto Note=G.GetStatus().Note;G.Render(F);
    Check(G.GetStatus().Note==Note,What+" leaves status unchanged");
    std::size_t Body=F.Commands.size(),Lantern=F.Commands.size(),Corner=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(IsGreenBody(C,G)) Body=N;
        if(C.Kind==Shape::Circle && C.Size==16 && Lantern==F.Commands.size()) Lantern=N;
        if(IsCorner(C,G)) Corner=N;
    }
    Check(Body<Lantern && Lantern<Corner && Corner<F.Commands.size(),What+" draws the body, then a lantern, then the corner mark");
}
bool ExitLabel(const Dungeon& G,std::uint8_t R,std::uint8_t Gv,std::uint8_t B) {
    Frame F;G.Render(F);
    for(const auto& C:F.Commands)
        if(C.Kind==Shape::Text && C.Label=="EXIT" && C.Tint.R==R && C.Tint.G==Gv && C.Tint.B==B) return true;
    return false;
}
bool WallCap(const Dungeon& G,bool Light) {
    Frame F;G.Render(F);
    std::size_t Full=F.Commands.size(),Cap=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Rectangle || C.A.X!=0 || C.A.Y!=0) continue;
        if(C.B.X==Dungeon::Tile && C.B.Y==Dungeon::Tile && C.Tint.R==100 && C.Tint.G==100 && C.Tint.B==100) Full=N;
        if(C.B.X==Dungeon::Tile && C.B.Y==6 && C.Tint.R==176 && C.Tint.G==176 && C.Tint.B==176) Cap=N;
    }
    return Light ? (Full<Cap && Cap<F.Commands.size()) : Cap==F.Commands.size();
}
void View() {
    Dungeon Fresh;
    Check(ExitLabel(Fresh,255,255,255),"sealed exit label is white on the gray door");
    Check(WallCap(Fresh,true),"original room walls keep a light top edge");
    Frame Numbers;Fresh.Render(Numbers);int WhiteNumbers=0,BlackNumbers=0;
    for(const auto& C:Numbers.Commands) if(C.Kind==Shape::Text && C.Label.size()==1 && C.Label[0]>='1' && C.Label[0]<='3') {
        if(C.Tint.R==255 && C.Tint.G==255 && C.Tint.B==255) ++WhiteNumbers;
        if(C.Tint.R==0 && C.Tint.G==0 && C.Tint.B==0) ++BlackNumbers;
    }
    Check(WhiteNumbers==2 && BlackNumbers==1,"dim lantern numbers are white and the next lantern number stays black");
    std::size_t Ring=Numbers.Commands.size(),Glass=Numbers.Commands.size();
    for(std::size_t N=0;N<Numbers.Commands.size();++N) {
        const auto& C=Numbers.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=Dungeon::Lanterns[0].X || C.A.Y!=Dungeon::Lanterns[0].Y) continue;
        if(C.Size==19 && C.Tint.R==24 && C.Tint.G==28 && C.Tint.B==40) Ring=N;
        if(C.Size==16) Glass=N;
    }
    Check(Ring<Glass && Glass<Numbers.Commands.size(),"each lantern keeps a dark ring on the wall");
    MarkOrder(Fresh,"fresh room");
    Input Right;Right.Right=true;Fresh.Step(Right);
    MarkOrder(Fresh,"moved room");
    Dungeon Switch;
    Check(Switch.SetOption(1,730),"switchback option");
    Check(WallCap(Switch,false),"switchback keeps its brown cap instead of the gray edge");
    MarkOrder(Switch,"switchback room");
}
}

int main() {
    try { View(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
