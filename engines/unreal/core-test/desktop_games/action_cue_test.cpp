// SPDX-License-Identifier: MIT
// Short action chips beside the hint line. The chip names the immediate action
// and stays out of score, movement, and saved status text.
// catalog-capability: action_cue: beacon_sweep driftstone dungeon dodge_ball lanternwild twinwake
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <stdexcept>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool HasText(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label.find(Part)!=std::string::npos) return true;
    return false;
}
void Expect(Game& G,const std::string& Cue,const std::string& What) {
    const auto Note=G.GetStatus().Note;
    Frame F;G.Render(F);
    Check(G.GetStatus().Note==Note && Note.find("CUE")==std::string::npos,What+" leaves status unchanged");
    Check(HasText(F,Cue),What);
}
void DungeonCues() {
    DungeonGame G;
    Expect(G,"CUE Next lantern","fresh circuit cues the next lantern");
    Check(G.SetOption(1,730) && G.ActionCue()=="CUE Next lantern","switchback room keeps the lantern cue");
}
void DodgeCues() {
    DodgeBallGame G;
    Expect(G,"CUE Countries","title cues the country list");
    G.Data.Mode=DodgeBallGame::Phase::CountrySelect;
    Check(G.ActionCue()=="CUE Confirm","country select cues confirm");
    G.Data.Mode=DodgeBallGame::Phase::Playing;
    Check(G.ActionCue()=="CUE Charge","ground round cues a charge");
    G.Data.DodgeBall.InAir=true;
    Check(G.ActionCue()=="CUE Catch","airborne ball cues a catch");
    G.Data.DodgeBall.InAir=false;G.Data.Mode=DodgeBallGame::Phase::Won;G.Data.Round=2;
    Check(G.ActionCue()=="CUE Next round","mid-tournament cues the next round");
    G.Data.Round=4;
    Check(G.ActionCue()=="CUE New score","finished tournament cues a new score");
}
void BeaconCues() {
    BeaconSweepGame G;G.Reset(730);
    Expect(G,"CUE Reveal","fresh board cues a reveal");
    Input Flag;Flag.ActionPressed=true;G.Step(Flag);
    Check(G.ActionCue()=="CUE Unflag","a flag cues unflag");
}
void DriftstoneCues() {
    DriftstoneGame G;G.Reset(730);
    Expect(G,"CUE Fire","fresh patrol cues fire");
    Check(G.SetOption(2,730),"flight practice opens");
    Expect(G,"CUE Dock","flight practice cues the dock");
}
void TwinwakeCues() {
    TwinwakeGame G;
    Check(G.SetOption(1,730),"practice mode opens");
    Expect(G,"CUE Serve","practice cues the serve");
}
void LanternwildCues() {
    LanternwildGame G;
    Expect(G,"CUE Swing","fresh quest cues one swing");
    Input Swing;Swing.FirePressed=true;G.Step(Swing);
    Check(G.ActionCue()=="CUE Wait","a swing cues the recovery wait");
}
}

int main() {
    try { BeaconCues();DriftstoneCues();DungeonCues();DodgeCues();LanternwildCues();TwinwakeCues(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
