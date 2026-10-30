// SPDX-License-Identifier: MIT
// Every cabinet accepts easy, normal, and hard, and starts on normal.
// The setting does not change the option, the score, or the status note.
// catalog-capability: difficulty: beacon_sweep twinwake dungeon driftstone football glowtrail riftwing emberstep star_shooter dodge_ball ironwake lanternwild gloam_latch reedbeat cairnwell prismcairn prismvault siltlane
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
}

int main() {
    Check(Catalog().size()==23,"difficulty covers every registered game");
    for(const Entry& E:Catalog()) {
        auto G=CreateGame(E.Id);
        Check(bool(G),E.Id+": factory");
        if(!G) continue;
        G->Reset(730);
        const auto Note=G->GetStatus().Note;
        const auto Score=G->GetStatus().Score;
        const int Option=G->GetOption();
        Check(G->CabinetDifficulty()=="normal",E.Id+": defaults to normal");
        Check(G->SetCabinetDifficulty("easy") && G->CabinetDifficulty()=="easy",E.Id+": accepts easy");
        Check(G->SetCabinetDifficulty("hard") && G->CabinetDifficulty()=="hard",E.Id+": accepts hard");
        Check(G->SetCabinetDifficulty("normal") && G->CabinetDifficulty()=="normal",E.Id+": returns to normal");
        Check(!G->SetCabinetDifficulty("Easy") && !G->SetCabinetDifficulty("") && G->CabinetDifficulty()=="normal",E.Id+": rejects an unknown name");
        Check(G->GetOption()==Option && G->GetStatus().Score==Score && G->GetStatus().Note==Note,E.Id+": option, score, and note stay put");
        auto Fresh=CreateGame(E.Id);
        Fresh->Reset(730);
        Check(Fresh->CabinetDifficulty()=="normal",E.Id+": a new run starts on normal");
    }
    std::cout<<"difficulty: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
