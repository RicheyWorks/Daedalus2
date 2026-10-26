// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct GloamLatchTestAccess {
    static const std::vector<int>& Opening(const GloamLatchGame& G) { return G.Opening; }
};
}}

namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
void MoveTo(GloamLatchGame& G,int Cell) {
    while(G.Cursor()%5<Cell%5) {Input I;I.Right=true;G.Step(I);}
    while(G.Cursor()%5>Cell%5) {Input I;I.Left=true;G.Step(I);}
    while(G.Cursor()/5<Cell/5) {Input I;I.Down=true;G.Step(I);}
    while(G.Cursor()/5>Cell/5) {Input I;I.Up=true;G.Step(I);}
}
void Flip(GloamLatchGame& G,int Cell) {
    MoveTo(G,Cell);
    Input I;I.FirePressed=true;G.Step(I);
}
}

int main() {
    GloamLatchGame Fresh;Fresh.Reset(730);
    Check(Fresh.LitCount()>0 && !Fresh.GetStatus().Over && Fresh.GetStatus().Note.find("HINT")==std::string::npos,"a fresh latch is lit and still open");
    const int Before=Fresh.LitCount();
    Input Held;Held.Fire=true;Fresh.Step(Held);
    Check(Fresh.LitCount()==Before,"held fire does not flip a lamp");
    GloamLatchGame Solved;Solved.Reset(730);
    for(int Cell:GloamLatchTestAccess::Opening(Solved)) Flip(Solved,Cell);
    Check(Solved.LitCount()==0 && Solved.GetStatus().Won && Solved.GetStatus().Score>0,"repeating the opening flips clears the board");
    const auto Score=Solved.GetStatus().Score;
    Input Idle;Solved.Step(Idle);Solved.Step(Held);
    Check(Solved.GetStatus().Won && Solved.GetStatus().Score==Score,"a finished latch stays until a fresh press");
    Input Again;Again.JumpPressed=true;Solved.Step(Again);
    Check(!Solved.GetStatus().Won && Solved.LitCount()>0,"a fresh press deals the same latch again");
    GloamLatchGame Keys;Keys.Reset(730);
    for(int Cell:GloamLatchTestAccess::Opening(Keys)) Flip(Keys,Cell);
    Check(Keys.SourceKeyDown(8) && !Keys.GetStatus().Won,"R starts the same latch again");
    Driver D;Check(D.Select("gloam_latch",730) && D.ActiveId()=="gloam_latch","driver selects Gloam Latch");
    std::cout<<"gloam latch: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
