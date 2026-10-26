// SPDX-License-Identifier: MIT
// Host save-slot table: every slot is a real save-capable game with a unique,
// safe file name; Minesweeper and Star keep their original files and styles;
// unslotted games keep the legacy Star fallback; manual slots round-trip a
// started run through the same Driver path the host uses for Continue.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include "DesktopGames/DaedalusDesktopSaveSlots.h"
#include <iostream>
#include <set>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SafeName(const std::string& S) {
    if(S.empty() || S.size()>40) return false;
    for(char C:S) if(!((C>='a' && C<='z') || C=='_' || C=='.')) return false;
    return S.find("..")==std::string::npos;
}
}  // namespace

int main() {
    std::set<std::string> Files,Ids;
    for(const SaveSlot& Slot:SaveSlots) {
        const std::string Id=Slot.Id,File=Slot.File;
        Check(Ids.insert(Id).second,Id+": listed once");
        Check(Files.insert(File).second,Id+": owns a unique file");
        Check(SafeName(File) && File.size()>4 && File.compare(File.size()-4,4,".dgs")==0,Id+": file name is plain *.dgs");
        Check(File==Id+".dgs",Id+": file is named after the game");
        Check(CreateGame(Id)!=nullptr,Id+": is a registered game");
        Check(FindSaveSlot(Id)==&Slot && std::string(ResumeGameId(Id))==Id && std::string(SaveFileFor(Id))==File,Id+": lookups agree");
        if(Slot.Style!=SaveStyle::Manual) continue;
        Driver D;D.Select(Id,11);
        Input Start;Start.FirePressed=true;Start.JumpPressed=true;D.SetInput(Start);
        for(int N=0;N<20;++N) D.Advance(Driver::StepSeconds);
        const std::string Save=D.CaptureSave();
        Check(!Save.empty() && Save.size()<=4096,Id+": started run produces a bounded save");
        Driver E;
        Check(E.Select(ResumeGameId(Id),11) && E.RestoreSave(Save),Id+": Continue path restores the save");
        Check(E.CaptureSave()==Save,Id+": Continue path round-trips");
    }
    Check(std::string(SaveFileFor("minesweeper"))=="minesweeper.dgs" && SupportsManualSave("minesweeper"),"minesweeper unchanged: manual, minesweeper.dgs");
    Check(std::string(SaveFileFor("star_shooter"))=="star_shooter.dgs" && !SupportsManualSave("star_shooter"),"star unchanged: source menu only, star_shooter.dgs");
    for(const char* Id:{"shadow_ninja","dodge_ball","contra","","nope"}) {
        Check(!FindSaveSlot(Id) && !SupportsManualSave(Id),std::string(Id)+": no slot, no manual save");
        Check(std::string(ResumeGameId(Id))=="star_shooter" && std::string(SaveFileFor(Id))=="star_shooter.dgs",std::string(Id)+": keeps legacy Star fallback");
    }
    std::cout<<"save slots: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
