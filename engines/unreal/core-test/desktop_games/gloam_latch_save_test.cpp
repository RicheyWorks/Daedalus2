// SPDX-License-Identifier: MIT
// Gloam Latch host save: a mid-puzzle board round-trips through the Driver
// Continue path with the same lamps, cursor, moves and seed; a cleared board
// saves nothing; bad payloads are refused.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include "DesktopGames/DaedalusDesktopGloamLatchCore.h"
#include "DesktopGames/DaedalusDesktopSaveSlots.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
}

int main() {
    Check(SupportsManualSave("gloam_latch") && std::string(SaveFileFor("gloam_latch"))=="gloam_latch.dgs","slot: manual, gloam_latch.dgs");
    for(int Mode=0;Mode<2;++Mode) {
        GloamLatchGame G;G.Reset(91);Check(G.SetOption(Mode,91),"option "+std::to_string(Mode));
        Input Move;Move.Right=true;G.Step(Move);
        Input Flip;Flip.FirePressed=true;G.Step(Flip);
        const std::string Save=G.SaveState();
        Check(Save.rfind("GLS1 ",0)==0,"mode "+std::to_string(Mode)+": save written");
        GloamLatchGame R;R.Reset(5);
        Check(R.RestoreState(Save,5),"mode "+std::to_string(Mode)+": restores");
        Check(R.SaveState()==Save && R.GetOption()==Mode && R.Cursor()==G.Cursor() && R.LitCount()==G.LitCount(),"mode "+std::to_string(Mode)+": same board");
        Check(R.SeedAfterRestore(5)==91,"mode "+std::to_string(Mode)+": keeps original seed for retry");
    }
    Driver D;D.Select("gloam_latch",44);
    Input Flip;Flip.FirePressed=true;D.SetInput(Flip);D.Advance(Driver::StepSeconds);
    const std::string Save=D.CaptureSave();
    Driver E;Check(!Save.empty() && E.Select("gloam_latch",3) && E.RestoreSave(Save) && E.CaptureSave()==Save,"driver Continue round-trips");
    for(const char* Bad:{"","GLS1","GLS2 0 1 0 0 1","GLS1 2 1 0 0 1","GLS1 0 0 0 0 1","GLS1 0 1 25 0 1",
                         "GLS1 0 1 0 0 0","GLS1 0 1 0 0 33554432","GLS1 1 1 0 0 512","GLS1 0 1 0 -1 1","GLS1 0 1 0 0 1 x"}) {
        GloamLatchGame R;R.Reset(1);Check(!R.RestoreState(Bad,1),std::string("refuses '")+Bad+"'");
    }
    std::cout<<"gloam latch save: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
