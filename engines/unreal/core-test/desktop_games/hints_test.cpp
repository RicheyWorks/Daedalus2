// SPDX-License-Identifier: MIT
// Accessibility hints for the three cabinets that only had options and focus freeze.
// The line is drawn on the frame. It does not change score, movement, or saves.
// catalog-capability: hints: beacon_sweep cairnwell dodge_ball driftstone dungeon emberkiln facetlock fogbell glimmerloom glowmoss gloam_latch lanternwild lumenpath prismcairn prismchime prismvault reedbeat riftwing roostcall shadewatch shardfall shardring shardscale shuntline sluicegate siltlane spiritkite stonecourse twinwake wardens_accord
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
void CairnwellHints() {
    CairnwellGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Slide the stone. A full layer sinks away.","fresh well teaches the layer");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"cairnwell hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"practice hint names the slower well");
}
void LumenpathHints() {
    LumenpathGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT Mirrors cycle",0)==0,"fresh lattice teaches the mirror cycle");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"lumenpath hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void WardensAccordHints() {
    WardensAccordGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Take a shard each round; spend matching shards to summon.","fresh altar teaches the loop");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"wardens hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void FacetlockHints() {
    FacetlockGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Rows and columns wrap. Make every row one hue.","fresh lattice teaches the wrap");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"facetlock hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void PrismcairnHints() {
    PrismcairnGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Lift the last shard. Leave the Warden a balanced field.","fresh duel teaches the goal");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"prismcairn hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void PrismvaultHints() {
    PrismvaultGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Split the suspects in three; the lighter pan holds the hollow one.","fresh vault teaches the split");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"prismvault hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void ShuntlineHints() {
    ShuntlineGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh yard teaches the order rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"shuntline hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void StonecourseHints() {
    StonecourseGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh wall teaches the rest rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"stonecourse hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void ShardscaleHints() {
    ShardscaleGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh line teaches the hand rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"shardscale hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void SpiritkiteHints() {
    SpiritkiteGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh sky teaches the wind rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"spiritkite hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void GlowmossHints() {
    GlowmossGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh shaft teaches the lamp rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"glowmoss hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void SluicegateHints() {
    SluicegateGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT ",0)==0 && G.HintLine().find("Pad A or R")==std::string::npos,"fresh field teaches the gate rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"sluicegate hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void EmberkilnHints() {
    EmberkilnGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT A coal",0)==0,"fresh floor teaches the heat rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"emberkiln hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void RoostcallHints() {
    RoostcallGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Birds fly to the open cell farthest from you. Walk up behind them, roost-side last.","fresh yard teaches the flee rule");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"roostcall hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void FogbellHints() {
    FogbellGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Low ground floods first. Pick up lanterns on the way and keep a dry route home.","fresh voyage teaches the tide");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"fogbell hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void PrismchimeHints() {
    PrismchimeGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT A tap pulses a chime's charge along its arrow; a chime at four peals and lights.","fresh ring teaches the tap");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"prismchime hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void GlimmerloomHints() {
    GlimmerloomGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine().rfind("HINT Rumor: ",0)==0,"fresh market hint carries the rumor");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"glimmerloom hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void ShadewatchHints() {
    ShadewatchGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Flare the nearest shade; kindle when the lanes are quiet.","fresh vigil teaches flare and kindle");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"shadewatch hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void ShardfallHints() {
    ShardfallGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Draw to grow the pot; bank before the second crack.","fresh seam teaches the gamble");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"shardfall hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice counsel");
}
void ShardringHints() {
    ShardringGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Three of one hue in a row resonate and clear.","fresh ring teaches resonance");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"shardring hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"guide hint names the practice marker");
}
void ReedbeatHints() {
    ReedbeatGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Strike when the reed glows. Early taps count as misses.","fresh round teaches the glow");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"reedbeat hint is on the frame and stays out of status");
    Check(G.SetOption(1,730) && G.HintLine().find("Practice")!=std::string::npos,"practice hint names the wider glow");
}
void GloamLatchHints() {
    GloamLatchGame G;G.Reset(730);
    const auto Note=G.GetStatus().Note;
    Check(G.HintLine()=="HINT Flip a lamp and its neighbors until the board is dark.","fresh latch teaches the flip");
    Frame F;G.Render(F);
    Check(HasText(F,G.HintLine()) && G.GetStatus().Note==Note && Note.find("HINT")==std::string::npos,"gloam latch hint is on the frame and stays out of status");
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
    try { BeaconHints();CairnwellHints();FacetlockHints();DriftstoneHints();DungeonHints();DodgeHints();GloamLatchHints();LanternwildHints();LumenpathHints();PrismcairnHints();PrismvaultHints();ReedbeatHints();RiftwingHints();RoostcallHints();EmberkilnHints();SluicegateHints();GlowmossHints();SpiritkiteHints();ShardscaleHints();StonecourseHints();ShuntlineHints();FogbellHints();PrismchimeHints();GlimmerloomHints();ShadewatchHints();ShardfallHints();ShardringHints();TwinwakeHints();WardensAccordHints(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
