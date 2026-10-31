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
    check(Catalog().size()==35,"all thirty-five game families registered (fourteen canonical + beacon_sweep + nineteen Prism cabinets + siltlane)");
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
    Driver d; check(d.Select("twinwake",730),"driver selects source Twinwake");
    check(d.Advance(0.1)==6 && d.Ticks()==6,"fixed-step cadence");
    const auto ticks=d.Ticks();check(d.Advance(1000)==8 && d.Ticks()==ticks+8,"hitch catch-up bounded");
    check(!d.Select("not-a-game",0) && d.ActiveId()=="twinwake","invalid selection preserves current game");
    const auto before=d.Ticks();d.SetPaused(true);check(d.Advance(1)==0 && d.Ticks()==before,"pause does not age rules");
    d.SetPaused(false);check(d.Advance(-1)==0 && d.Advance(std::numeric_limits<double>::quiet_NaN())==0,"invalid elapsed rejected");
    d.Restart();check(d.Ticks()==0 && d.ActiveId()=="twinwake" && !d.IsPaused(),"restart resets driver lifecycle");
    const Frame& picture=d.GetFrame();check(picture.Commands.size()==6,"restart creates source initial picture");
    std::cout<<"Desktop registry: "<<checks-failed<<'/'<<checks<<" checks passed\n";return failed ? 1 : 0;
}
