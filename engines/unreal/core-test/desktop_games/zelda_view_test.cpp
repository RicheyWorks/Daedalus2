// SPDX-License-Identifier: MIT
// Lanternwild viewing: a dark outline sits behind the hero so the tunic reads on the grass.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Outline(const DrawCommand& C,const ZeldaGame::Player& P) {
    return C.Kind==Shape::Rectangle && C.A.X==P.X-10 && C.A.Y==P.Y-6 && C.B.X==20 && C.B.Y==24
        && C.Tint.R==12 && C.Tint.G==40 && C.Tint.B==12;
}
bool Tunic(const DrawCommand& C,const ZeldaGame::Player& P) {
    return C.Kind==Shape::Rectangle && C.A.X==P.X-8 && C.A.Y==P.Y-4 && C.B.X==16 && C.B.Y==20
        && C.Tint.R==50 && C.Tint.G==150 && C.Tint.B==50;
}
void View() {
    ZeldaGame G;
    const auto Note=G.GetStatus().Note;
    Frame F;G.Render(F);
    Check(G.GetStatus().Note==Note,"view render leaves status unchanged");
    const auto& P=G.GetPlayer();
    std::size_t Rim=F.Commands.size(),Body=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        if(Outline(F.Commands[N],P)) Rim=N;
        if(Tunic(F.Commands[N],P)) Body=N;
    }
    Check(Rim<Body && Body<F.Commands.size(),"dark outline draws behind the tunic");
}
}

int main() {
    try { View(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
