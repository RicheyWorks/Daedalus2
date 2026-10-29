// SPDX-License-Identifier: MIT
// Focus loss: the host calls Driver::SetPaused(true). Every registered game must
// freeze (no simulation, unchanged picture and status, source buttons ignored,
// held input dropped) and resume cleanly on SetPaused(false). Games that own
// their pause (OwnPause) freeze through the core instead of the driver.
// catalog-capability: focus_freeze: beacon_sweep twinwake dungeon driftstone football glowtrail riftwing emberstep star_shooter dodge_ball ironwake lanternwild gloam_latch reedbeat cairnwell shardring lumenpath
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
bool SameStatus(const Status& A,const Status& B) {
    return A.Score==B.Score && A.Lives==B.Lives && A.Over==B.Over && A.Won==B.Won && A.Note==B.Note;
}
Input Held() {Input I;I.Right=true;I.Fire=true;I.AxisX=1;return I;}

void Freeze(const std::string& Id) {
    Driver D;
    Check(D.Select(Id,77),Id+": selects");
    Input Start;Start.FirePressed=true;Start.JumpPressed=true;D.SetInput(Start);D.Advance(Driver::StepSeconds);
    for(int N=0;N<20;++N) {D.SetInput(Held());D.Advance(Driver::StepSeconds);}
    D.SetInput(Held());
    D.SetPaused(true);
    Check(D.IsPaused(),Id+": reports paused after focus loss");
    D.Advance(Driver::StepSeconds);  // Owning cores may draw their pause picture once.
    const Frame Before=D.GetFrame();const Status S0=D.GetStatus();const auto T0=D.Ticks();
    for(int N=0;N<30;++N) {D.SetInput(Held());D.Advance(0.25);}
    Check(SameFrame(Before,D.GetFrame()),Id+": picture frozen while unfocused");
    Check(SameStatus(S0,D.GetStatus()),Id+": status frozen while unfocused");
    Check(D.IsPaused(),Id+": stays paused under held input");
    if(D.Ticks()==T0) Check(!D.SourceControllerButton(0),Id+": source buttons ignored while unfocused");
    D.SetPaused(false);
    Check(!D.IsPaused(),Id+": refocus resumes");
    Check(D.Advance(Driver::StepSeconds)==1,Id+": one step after resume, no catch-up burst");
    Check(D.Advance(10.0)<=Driver::MaxSteps,Id+": long stall stays bounded");
}
}  // namespace

int main() {
    for(const char* Id:{"beacon_sweep","twinwake","dungeon","driftstone","football","glowtrail","riftwing",
                        "emberstep","star_shooter","dodge_ball","ironwake","lanternwild","gloam_latch","reedbeat","cairnwell","shardring","lumenpath"}) Freeze(Id);
    Driver None;Check(!None.Select("not_a_game",1),"unknown id refused");
    std::cout<<"focus freeze: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
