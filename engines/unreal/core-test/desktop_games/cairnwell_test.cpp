// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
void Press(CairnwellGame& G,int Dir) {
    Input I; if(Dir<0) I.Left=true; else if(Dir>0) I.Right=true; G.Step(I);
}
void Slide(CairnwellGame& G,int Dir) { Press(G,Dir); G.Step({}); }
void Drop(CairnwellGame& G) { Input I; I.Down=true; G.Step(I); G.Step({}); }
void FillColumn(CairnwellGame& G,int Column) {
    while(!G.GetStatus().Over && G.FallingColumn()!=Column) Slide(G,G.FallingColumn()<Column?1:-1);
    if(!G.GetStatus().Over) Drop(G);
}
}

int main() {
    CairnwellGame Fresh;Fresh.Reset(730);
    Check(Fresh.ColumnCount()==6 && Fresh.FallingColumn()==730%6,"a fresh well has six columns");
    Check(!Fresh.GetStatus().Over && Fresh.GetStatus().Score==0 && Fresh.GetStatus().Note.find("HINT")==std::string::npos,"opening score is clear and the hint stays off the note");
    const int Start=Fresh.FallingColumn();
    Press(Fresh,-1);
    Check(Fresh.FallingColumn()==Start-1,"one left press slides the stone");
    Press(Fresh,-1);
    Check(Fresh.FallingColumn()==Start-1,"held left does not slide again");
    Drop(Fresh);
    Check(Fresh.StackHeight(Start-1)==1 && Fresh.GetStatus().Score==10,"a drop locks one stone");
    CairnwellGame Practice;
    Check(Practice.SetOption(1,730) && Practice.GetOption()==1 && Practice.ColumnCount()==4,"practice opens four columns");
    Check(!Practice.SetOption(2,730) && Practice.GetOption()==1,"an out-of-range well option is refused");
    for(int C=0;C<4;++C) FillColumn(Practice,C);
    Check(Practice.LayerCount()==1 && Practice.StackHeight(0)==0 && Practice.GetStatus().Score==140,"one stone in every column sinks a layer");
    CairnwellGame Pile;Pile.Reset(730);
    for(int N=0;N<8 && !Pile.GetStatus().Over;++N) FillColumn(Pile,0);
    Check(Pile.GetStatus().Over && !Pile.GetStatus().Won,"a column that reaches the rim ends the well");
    Check(Pile.SourceKeyDown(8) && !Pile.GetStatus().Over,"R starts the same well again");
    Frame F;Pile.Render(F);
    Check(!F.Commands.empty(),"the well draws");
    Driver D;Check(D.Select("cairnwell",730) && D.ActiveId()=="cairnwell","driver selects Cairnwell");
    std::cout<<"cairnwell: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
