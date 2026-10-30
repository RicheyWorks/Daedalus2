// SPDX-License-Identifier: MIT
// Key hints and colour-blind safe marks. The mark is a word plus a shape on a
// dark plate: a triangle for MARK ACT and a bar for MARK WAIT. Colour is not
// the only signal. Twinwake keeps its six-command match opening.
// catalog-capability: key_hint: beacon_sweep twinwake dungeon driftstone football glowtrail riftwing emberstep star_shooter dodge_ball ironwake lanternwild gloam_latch reedbeat cairnwell shardring sluicegate lumenpath wardens_accord emberkiln facetlock prismcairn prismvault siltlane shardfall shadewatch glimmerloom prismchime fogbell roostcall emberkiln
// catalog-capability: contrast_mark: beacon_sweep twinwake dungeon driftstone football glowtrail riftwing emberstep star_shooter dodge_ball ironwake lanternwild gloam_latch reedbeat cairnwell shardring sluicegate lumenpath wardens_accord emberkiln facetlock prismcairn prismvault siltlane shardfall shadewatch glimmerloom prismchime fogbell roostcall emberkiln
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
bool HasShape(const Frame& F,const std::string& Mark) {
    const bool Act=Mark=="MARK ACT";
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle && C.B.X==16 && C.B.Y==4
        && C.Tint.R==(Act?255:120) && C.Tint.G==(Act?236:225)) return true;
    return false;
}
}

int main() {
    Check(Catalog().size()==30,"access covers every registered game");
    for(const Entry& E:Catalog()) {
        auto G=CreateGame(E.Id);
        Check(bool(G),E.Id+": factory");
        if(!G) continue;
        G->Reset(730);
        const std::string Keys=G->KeyHint();
        const std::string Mark=G->ContrastMark();
        Check(Keys.rfind("KEYS ",0)==0,E.Id+": key hint names the controls");
        Check(Mark=="MARK ACT" || Mark=="MARK WAIT",E.Id+": contrast mark is a word");
        Check(G->GetStatus().Note.find("KEYS")==std::string::npos && G->GetStatus().Note.find("MARK ")==std::string::npos,E.Id+": access text stays out of status");
        Frame F;G->Render(F);
        if(E.Id=="twinwake") {
            Check(F.Commands.size()==6,E.Id+": match opening stays six commands");
            Check(G->SetOption(1,730),E.Id+": practice opens");
            G->Render(F);
        }
        Check(HasText(F,Keys) && HasText(F,Mark) && HasShape(F,G->ContrastMark()),E.Id+": key hint and contrast mark are on the frame");
    }
    std::cout<<"a11y: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
