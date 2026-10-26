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
void View() {
    Dungeon Fresh;
    Check(ExitLabel(Fresh,255,255,255),"sealed exit label is white on the gray door");
    MarkOrder(Fresh,"fresh room");
    Input Right;Right.Right=true;Fresh.Step(Right);
    MarkOrder(Fresh,"moved room");
    Dungeon Switch;
    Check(Switch.SetOption(1,730),"switchback option");
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
