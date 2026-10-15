// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <limits>
#include <set>
using namespace daedalus::desktop;
int main() {
    int checks=0,failed=0;
    auto check=[&](bool ok,const char* what) {++checks; if(!ok) {++failed;std::cerr<<"FAIL "<<what<<'\n';}};
    std::set<std::string> ids;
    check(Catalog().size()==11,"all eleven canonical game families registered");
    for(const Entry& e:Catalog()) {
        check(ids.insert(e.Id).second,"catalog IDs unique");
        auto game=CreateGame(e.Id); check(bool(game),"registered factory exists");
        if(!game) continue;
        game->Reset(730); Frame frame; game->Render(frame);
        check(!frame.Commands.empty() && frame.Commands.size()<=Frame::MaxCommands,"registered game renders bounded frame");
        Input input; input.Right=true;input.Fire=true; input.JumpPressed=true;
        for(int i=0;i<1200;++i) { game->Step(input);input.JumpPressed=false; }
        game->Render(frame); check(frame.Commands.size()<=Frame::MaxCommands,"long-run rendering remains bounded");
        game->Reset(730); check(!game->GetStatus().Over,"restart clears terminal state");
    }
    Driver d; check(d.Select("pong",730),"driver selects source Pong");
    check(d.Advance(0.1)==6 && d.Ticks()==6,"fixed-step cadence");
    const auto ticks=d.Ticks();check(d.Advance(1000)==8 && d.Ticks()==ticks+8,"hitch catch-up bounded");
    check(!d.Select("not-a-game",0) && d.ActiveId()=="pong","invalid selection preserves current game");
    const auto before=d.Ticks();d.SetPaused(true);check(d.Advance(1)==0 && d.Ticks()==before,"pause does not age rules");
    d.SetPaused(false);check(d.Advance(-1)==0 && d.Advance(std::numeric_limits<double>::quiet_NaN())==0,"invalid elapsed rejected");
    d.Restart();check(d.Ticks()==0 && d.ActiveId()=="pong" && !d.IsPaused(),"restart resets driver lifecycle");
    const Frame& picture=d.GetFrame();check(picture.Commands.size()==6,"restart creates source initial picture");
    d.SourceKeyDown(0);check(d.GetFrame().Commands.size()==6,"optional raw-key no-op preserves other games");
    check(!d.SourceControllerButton(0) && !d.SourceControllerButton(1),"optional controller no-op preserves generic behavior");
    check(d.Select("contra",42) && d.GetStatus().Note.find("TITLE")!=std::string::npos,"Driver selection binds source title");
    for(int Key:{0,0,1,1,2,3,2,3,4,5}) d.SourceKeyDown(Key);
    check(d.GetStatus().Lives==30 && d.GetStatus().Note.find("TITLE")!=std::string::npos && d.Ticks()==0,"ordered key dispatch arms30 before any fixed step");
    d.SetPaused(true);d.SourceKeyDown(6);check(d.GetStatus().Note.find("TITLE")!=std::string::npos,"paused keyboard dispatch cannot start title");
    check(!d.SourceControllerButton(0),"paused controller dispatch cannot start title");d.SetPaused(false);
    d.SourceKeyDown(6);check(d.GetStatus().Lives==30 && d.GetStatus().Note.find("TITLE")==std::string::npos,"Driver Enter starts preserving30 immediately");
    check(!d.SourceControllerButton(1),"live Start remains unconsumed for generic pause");
    d.Restart();check(d.GetStatus().Lives==3 && d.Ticks()==0 && d.GetStatus().Note.find("TITLE")==std::string::npos,"host Restart remains immediate standard run");
    d.Select("contra",42);d.SourceKeyDown(0);d.SourceKeyDown(0);check(d.SourceControllerButton(0),"Driver controller A starts title");
    for(int Key:{1,1,2,3,2,3,4,5}) d.SourceKeyDown(Key);
    check(d.GetStatus().Lives==8,"ordered controller start preserves prefix then in-play award");
    for(int Start:{0,1}) {
        d.Select("contra",42);Input Old;Old.FirePressed=true;d.SetInput(Old);d.SetInput({});
        if(Start==0) d.SourceKeyDown(6); else d.SourceControllerButton(0);
        d.Advance(Driver::StepSeconds);
        check(d.GetStatus().Note.find("FIRE: ready")!=std::string::npos,"released title shot edge cannot leak across keyboard/controller start");
    }
    d.Select("contra",42);Input HeldShot;HeldShot.Fire=true;HeldShot.FirePressed=true;d.SetInput(HeldShot);
    d.SourceKeyDown(6);HeldShot.FirePressed=false;d.SetInput(HeldShot);d.Advance(Driver::StepSeconds);
    check(d.GetStatus().Note.find("FIRE: cooldown")!=std::string::npos,"held fire rebuilt after start still follows source held firing");
    std::cout<<"Desktop registry: "<<checks-failed<<'/'<<checks<<" checks passed\n";return failed ? 1 : 0;
}
