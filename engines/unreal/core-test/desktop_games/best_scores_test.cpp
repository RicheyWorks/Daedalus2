// SPDX-License-Identifier: MIT
// Arcade host best scores: plays every catalog game through the Driver, feeds
// Status.Score (the scoreboard hook) into BestScores, and checks save/restore,
// old-id aliases, clamping and refusal of bad files.
#include "DesktopGames/DaedalusDesktopBestScores.h"
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
}

int main() {
    BestScores B;
    for(const Entry& E:Catalog()) {
        Driver D;Check(D.Select(E.Id,730),E.Id+": selects");
        Input Held;Held.Right=true;Held.Fire=true;Held.FirePressed=true;
        std::int64_t Top=0;
        for(int N=0;N<120;++N) { D.SetInput(Held); D.Advance(Driver::StepSeconds); B.Record(E.Id,D.GetStatus().Score); if(D.GetStatus().Score>Top) Top=D.GetStatus().Score; }
        Check(B.Has(E.Id) && B.Get(E.Id)==Top,E.Id+": best equals the highest score seen");
    }
    Check(B.Size()==Catalog().size(),"one best per catalog game");
    const std::string File=B.Save();
    BestScores R;Check(R.Restore(File) && R.Save()==File,"save/restore round-trips");
    Check(R.Restore(B.Save()) && R.Size()==B.Size(),"restore replaces, not appends");

    BestScores S;
    Check(S.Record("twinwake",50) && !S.Record("twinwake",40) && !S.Record("twinwake",50) && S.Record("twinwake",51),"only a higher score is a new best");
    Check(S.Get("twinwake")==51,"best kept");
    Check(S.Record("pong",60) && S.Get("twinwake")==60,"old id records under the renamed game");
    Check(!S.Record("twinwake",-1) && !S.Record("",5) && !S.Record("Bad Id",5) && !S.Record("../x",5),"bad scores and ids refused");
    S.Record("reedbeat",BestScores::MaxScore+5);
    Check(S.Get("reedbeat")==BestScores::MaxScore,"score clamped to host range");
    Check(S.Get("nope")==0 && !S.Has("nope"),"unknown game reads 0");

    BestScores L;Check(L.Restore("DSB1\npong 9\ntwinwake 4\n") && L.Get("twinwake")==9 && L.Size()==1,"legacy ids merge on restore");
    const std::string Before=S.Save();
    for(const char* Bad:{"","DSB2\n","DSB1\ntwinwake\n","DSB1\ntwinwake -1\n","DSB1\ntwinwake 1 2\n","DSB1\nTwin 1\n","DSB1\ntwinwake 1000000000001\n","DSB1\ntwinwake x\n"}) {
        Check(!S.Restore(Bad) && S.Save()==Before,std::string("refuses bad file, table unchanged: ")+std::to_string(std::string(Bad).size()));
    }
    BestScores Many;for(int N=0;N<70;++N) Many.Record("g"+std::to_string(N),1);
    Check(Many.Size()==BestScores::MaxGames,"table capped at MaxGames");
    Check(std::string(BestScores::FileName)=="best_scores.dgs" && !FindSaveSlot("best_scores"),"file name does not collide with a save slot");
    std::cout<<"best scores: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
