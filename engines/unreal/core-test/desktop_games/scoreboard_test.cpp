// SPDX-License-Identifier: MIT
// The arcade host shows Status.Score. Every catalog game must report that number
// inside the range the host already clamps. This does not read or write saves.
// catalog-capability: scoreboard: beacon_sweep twinwake dungeon driftstone football glowtrail riftwing emberstep star_shooter dodge_ball ironwake lanternwild gloam_latch reedbeat cairnwell shardring lumenpath wardens_accord facetlock prismcairn
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
constexpr std::int64_t HostMax=1000000000000LL;
bool Showable(std::int64_t Score) { return Score>=0 && Score<=HostMax; }
}

int main() {
    for(const Entry& E:Catalog()) {
        Driver D;
        Check(D.Select(E.Id,730),E.Id+": selects");
        const auto First=D.GetStatus().Score;
        Check(Showable(First),E.Id+": opening score is host-visible");
        Check(D.GetStatus().Score==First,E.Id+": a second read keeps the same score");
        Input Held;Held.Right=true;Held.Fire=true;
        for(int N=0;N<30;++N) { D.SetInput(Held); D.Advance(Driver::StepSeconds); }
        Check(Showable(D.GetStatus().Score),E.Id+": score stays host-visible after play");
    }
    std::cout<<"scoreboard: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
