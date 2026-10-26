// SPDX-License-Identifier: MIT
// Fresh-press replay parity for games that restart inside Step rather than via
// SourceControllerButton. A finished run must hold on idle and held buttons, and
// restart only on a fresh press (FirePressed / JumpPressed / ActionPressed, which
// the host raises for keyboard and pad A/B alike).
// catalog-capability: fresh_pad_replay: twinwake football glowtrail
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void End(GlowtrailGame& G,bool Won) {G.Over=!Won;G.Won=Won;G.Score=1234;G.Lives=Won?2:0;}
};
}}  // namespace daedalus::desktop

namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Held() {Input I;I.Fire=true;I.Jump=true;I.Action=true;I.Up=true;return I;}
Input Fresh(int Kind) {Input I;if(Kind==0) I.FirePressed=true;else if(Kind==1) I.JumpPressed=true;else I.ActionPressed=true;return I;}
const char* KindName(int Kind) {return Kind==0?"fire":(Kind==1?"jump":"action");}

void Twinwake() {
    for(int Mode:{2,3}) for(int Kind=0;Kind<3;++Kind) {
        TwinwakeGame G;G.SetOption(Mode,1);
        G.S.PlayerScore=5;G.S.ComputerScore=2;
        const std::string Tag=std::string("twinwake mode ")+std::to_string(Mode)+" "+KindName(Kind)+": ";
        Check(G.GetStatus().Over,Tag+"finished run reports over");
        const double Y=G.S.PlayerY;
        for(int N=0;N<30;++N) G.Step(Input{});
        G.Step(Held());
        Check(G.S.PlayerScore==5 && G.GetStatus().Over,Tag+"idle and held input keep the result");
        Check(G.S.PlayerY==Y,Tag+"held input does not move the paddle on the result");
        G.Step(Fresh(Kind));
        Check(G.S.PlayerScore==0 && G.S.ComputerScore==0 && !G.GetStatus().Over,Tag+"fresh press starts a rematch");
        Check(G.GetOption()==Mode,Tag+"rematch keeps the chosen mode");
    }
}

void Football() {
    for(int Kind=0;Kind<3;++Kind) {
        if(Kind==1) continue;  // Football reads Fire/Action only; Jump is not a kick-off key.
        FootballGame G;G.Step(Fresh(0));
        G.Data.HumanScore=1;G.Data.Seconds=1.0/60.0;G.Step(Input{});
        const std::string Tag=std::string("football ")+KindName(Kind)+": ";
        Check(G.GetStatus().Over && G.GetStatus().Won,Tag+"full time ends the match");
        for(int N=0;N<30;++N) G.Step(Input{});
        G.Step(Held());
        Check(G.GetStatus().Over && G.Data.HumanScore==1,Tag+"idle and held input keep the result");
        G.Step(Fresh(Kind));
        Check(!G.GetStatus().Over && G.Data.HumanScore==0 && G.Data.Mode==FootballGame::Phase::Playing,Tag+"fresh press replays");
    }
    FootballGame J;J.Step(Fresh(0));J.Data.Seconds=1.0/60.0;J.Step(Input{});J.Step(Fresh(1));
    Check(J.GetStatus().Over,"football: jump press alone does not restart (documented key set)");
}

void Glowtrail() {
    for(bool Won:{false,true}) for(int Kind=0;Kind<3;++Kind) {
        GlowtrailGame G;G.Reset(77);MazeTestAccess::End(G,Won);
        const std::string Tag=std::string("glowtrail ")+(Won?"won ":"lost ")+KindName(Kind)+": ";
        Check(G.GetStatus().Over || G.GetStatus().Won,Tag+"finished run reports over or won");
        Check(G.GetStatus().Won==Won,Tag+"win flag matches");
        for(int N=0;N<30;++N) G.Step(Input{});
        G.Step(Held());
        Check((G.GetStatus().Over || G.GetStatus().Won) && G.GetStatus().Score==1234,Tag+"idle and held input keep the result");
        G.Step(Fresh(Kind));
        const auto S=G.GetStatus();
        Check(!S.Over && !S.Won && S.Score==0 && S.Lives==3,Tag+"fresh press replays a full run");
        GlowtrailGame Ref;Ref.Reset(77);
        Check(S.Note==Ref.GetStatus().Note,Tag+"replay uses the session seed");
    }
}
}  // namespace

int main() {
    Twinwake();Football();Glowtrail();
    std::cout<<"replay parity: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
