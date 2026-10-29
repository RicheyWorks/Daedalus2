// SPDX-License-Identifier: MIT
// One original how-to line per cabinet. It is drawn on the opening frame.
// Twinwake keeps its six-command match opening and shows the line in practice.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool HasText(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label.find(Part)!=std::string::npos) return true;
    return false;
}
bool Original(const std::string& Line) {
    std::string Lower=Line;
    for(char& C:Lower) if(C>='A' && C<='Z') C=static_cast<char>(C-'A'+'a');
    for(const char* Ban:{"zelda","pacman","pac-man","pong","contra","sega","asteroids","minesweeper","mario"})
        if(Lower.find(Ban)!=std::string::npos) return false;
    return Line.rfind("HOW ",0)==0 && Line.size()>8;
}
}

int main() {
    Check(Catalog().size()==22,"how-to covers every registered game");
    for(const Entry& E:Catalog()) {
        auto G=CreateGame(E.Id);
        Check(bool(G),E.Id+": factory");
        if(!G) continue;
        G->Reset(730);
        const std::string Line=G->HowToLine();
        Check(Original(Line),E.Id+": original how-to line");
        Check(G->GetStatus().Note.find("HOW")==std::string::npos,E.Id+": how-to stays out of status");
        Frame F;G->Render(F);
        if(E.Id=="twinwake") {
            Check(F.Commands.size()==6,E.Id+": match opening stays six commands");
            Check(G->SetOption(1,730),E.Id+": practice opens");
            G->Render(F);
        }
        Check(HasText(F,Line),E.Id+": how-to is on the frame");
    }
    std::cout<<"howto: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
