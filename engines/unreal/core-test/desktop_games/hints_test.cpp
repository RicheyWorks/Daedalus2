// SPDX-License-Identifier: MIT
// Accessibility hints for the three cabinets that only had options and focus freeze.
// The line is drawn on the frame. It does not change score, movement, or saves.
// catalog-capability: hints: beacon_sweep driftstone dungeon dodge_ball lanternwild riftwing twinwake
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
void DungeonHints() {
    DungeonGame G;
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Light the lantern marked NEXT. Shift or pad Y shows the trail.","fresh circuit names the NEXT lantern");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"dungeon hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("NEXT")!=std::string::npos,"switchback room keeps the lantern hint");
}
void DodgeHints() {
    DodgeBallGame G;
    const auto Title=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Press Space, Enter, or pad A to open the country list.","title hint opens the country list");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Title,"dodge title hint is drawn and status is unchanged");
    G.Data.Mode=DodgeBallGame::Phase::CountrySelect;
    Check(G.HintLine().find("fresh Fire press")!=std::string::npos,"country select hint tells how to confirm");
    G.Data.Mode=DodgeBallGame::Phase::Playing;
    Check(G.HintLine().find("Hold Up to charge")!=std::string::npos,"live round hint teaches the charge");
    G.Data.DodgeBall.InAir=true;
    Check(G.HintLine().find("catch")!=std::string::npos,"airborne ball hint teaches the catch");
    G.Data.DodgeBall.InAir=false;G.Data.Mode=DodgeBallGame::Phase::Won;G.Data.Round=2;
    Check(G.HintLine().find("next round")!=std::string::npos,"mid-tournament hint continues the next round");
    G.Data.Round=4;
    Check(G.HintLine().find("fresh four-round")!=std::string::npos,"finished tournament hint starts a new score");
}
void BeaconHints() {
    BeaconSweepGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT The first reveal is safe.","fresh board says the first reveal is safe");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"beacon hint is on the frame and stays out of status");
    Input Flag;Flag.ActionPressed=true;G.Step(Flag);
    Check(G.HintLine()=="HINT K or pad B lifts the flag.","a flag tells how to lift it");
}
void DriftstoneHints() {
    DriftstoneGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Turn, thrust, and hold fire. Rocks split.","fresh patrol teaches the split");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"driftstone hint is on the frame and stays out of status");
    Check(G.SetOption(2,730) && G.HintLine().find("gold ring")!=std::string::npos,"flight practice hint names the ring");
    Frame Practice;G.Render(Practice);
    Check(HasText(Practice,G.HintLine()),"flight practice draws the hint");
}
void RiftwingHints() {
    RiftwingGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Hold fire. Pickups raise power, speed, and lives.","fresh run teaches pickups");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"riftwing hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("boss")!=std::string::npos,"rehearsal hint names the boss");
}
void TwinwakeHints() {
    TwinwakeGame G;
    Check(G.SetOption(1,730),"practice mode opens");
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Move as you meet the ball to bend it.","practice hint teaches the bend");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"twinwake hint is on the practice frame and stays out of status");
    Check(G.SetOption(0,730) && G.HintLine().find("add spin")!=std::string::npos,"match hint teaches spin");
    Frame Open;G.Render(Open);
    Check(Open.Commands.size()==6,"match opening stays six commands");
}
void LanternwildHints() {
    LanternwildGame G;
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Press J or pad A once to swing. Shift toggles held-sword assist.","fresh quest hint teaches one swing");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"lanternwild hint is on the frame and stays out of status");
    Input Swing;Swing.FirePressed=true;G.Step(Swing);
    Check(G.HintLine().find("recovering")!=std::string::npos,"a swing replaces the hint while the sword recovers");
}
}

int main() {
    try { BeaconHints();DriftstoneHints();DungeonHints();DodgeHints();LanternwildHints();RiftwingHints();TwinwakeHints(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
