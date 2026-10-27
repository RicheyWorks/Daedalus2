// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPlatformersCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static void EndRun(EmberstepGame& G,bool Won) {
        // A populated terminal fixture catches incomplete resets, not just Over=false.
        G.Over=true;G.Won=Won;G.Score=1950;G.BossActive=true;G.BossPulseCueFrames=5;G.SpawnTimer=47;
        G.Player.Health=Won?3:0;G.Player.X=471;G.Player.Y=250;G.Player.Invincible=12;
        G.Player.AttackCooldown=9;G.Player.SpinCooldown=24;G.Player.Spinning=4;
        G.Previous.Fire=G.Previous.Jump=G.Previous.Action=G.Previous.Dash=true;
        G.Attacks={{500,250,1,30,true,20}};
        G.Enemies={{600,400,-2,0,2,false}};G.Gold={{320,220}};
    }
};
}}}

namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const EmberstepGame& A,const EmberstepGame& B) {
    Frame F,G;A.Render(F);B.Render(G);
    if(F.Width!=G.Width || F.Height!=G.Height || F.Commands.size()!=G.Commands.size()) return false;
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];const auto& D=G.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    const auto S=A.GetStatus(),T=B.GetStatus();
    return S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note;
}
void CompareFreshPlay(EmberstepGame& Replayed,std::uint32_t Seed) {
    EmberstepGame Fresh;Fresh.Reset(Seed);
    Check(SameFrame(Replayed,Fresh),"replay restores complete initial picture and original seed");
    Check(!Replayed.GetStatus().Over && !Replayed.GetStatus().Won && Replayed.GetStatus().Score==0,"terminal result and score cleared");
    Check(!Replayed.HasBoss() && Replayed.PulseReceiptFramesRemaining()==0 && Replayed.AttackCount()==0
        && Replayed.EnemyCount()==0 && Replayed.GoldCount()==5,"terminal entities and cues reset");
    // First held attack must be a new edge after replay; deterministic following frames
    // also catch stale timers, previous input, player velocity and RNG stream.
    for(int N=0;N<24;++N) {
        Input I;I.Right=N<12;I.Fire=N<4;I.Jump=N<3;I.Action=N==8;I.Dash=N==18;
        Replayed.Step(I);Fresh.Step(I);
        Check(SameFrame(Replayed,Fresh),"replayed live steps match a fresh run");
    }
}
}

int main() {
    for(std::uint32_t Seed:{0u,730u,UINT32_MAX}) for(bool Won:{false,true}) {
        for(int Button:{0,1}) {
            EmberstepGame G;G.Reset(Seed);platformers::TestAccess::EndRun(G,Won);
            EmberstepGame Terminal=G;Game& Core=G;
            Input Held;Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
            Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;
            for(int N=0;N<20;++N) G.Step(Held);
            Check(SameFrame(G,Terminal),"held gameplay input never dismisses a result");
            Check(!Core.SourceControllerButton(-1) && !Core.SourceControllerButton(2) && !Core.SourceKeyDown(9)
                && SameFrame(G,Terminal),"unrelated terminal events preserve the result");
            const bool Replayed=Core.SourceControllerButton(Button);
            Check(Replayed,"fresh A or Start replays win and loss through virtual dispatch");
            if(Replayed) CompareFreshPlay(G,Seed);
            EmberstepGame Active=G;
            Check(!Core.SourceControllerButton(0) && !Core.SourceControllerButton(1)
                && !Core.SourceKeyDown(6) && !Core.SourceKeyDown(7) && SameFrame(G,Active),"live inputs do not restart an active run");
        }
        for(int Key:{6,7}) {
            EmberstepGame G;G.Reset(Seed);platformers::TestAccess::EndRun(G,Won);Game& Core=G;
            const bool Replayed=Core.SourceKeyDown(Key);
            Check(Replayed,"fresh Enter or Space replays terminal result");
            if(Replayed) CompareFreshPlay(G,Seed);
        }
    }
    std::cout<<"Emberstep Ascent replay: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
