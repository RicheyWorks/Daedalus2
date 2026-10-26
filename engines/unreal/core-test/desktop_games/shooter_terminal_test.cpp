// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Pass,const char* What) {++Checks;if(!Pass){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
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
bool Same(Game& A,Game& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    return SameFrame(F,G) && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note;
}
template<class T> void Retry(T Terminal,std::uint32_t Seed) {
    for(int Event=0;Event<4;++Event) {
        T G=Terminal;Game& Core=G;
        Input Held;Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
        Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;
        for(int N=0;N<8;++N) G.Step(Held);
        Check(Same(G,Terminal),"held gameplay input leaves the result frozen");
        Check(!Core.SourceControllerButton(-1) && !Core.SourceControllerButton(2) && !Core.SourceKeyDown(9)
            && Same(G,Terminal),"unrelated source events preserve the result");
        const bool Replayed=Event<2?Core.SourceControllerButton(Event):Core.SourceKeyDown(Event==2?6:7);
        Check(Replayed,"fresh terminal A/Start/Enter/Space retries through virtual dispatch");
        if(!Replayed) continue;
        T Fresh;Fresh.Reset(Seed);
        Check(Same(G,Fresh),"retry is a complete reset with the original seed");
        Check(!Core.SourceControllerButton(0) && !Core.SourceControllerButton(1) && !Core.SourceKeyDown(6)
            && !Core.SourceKeyDown(7) && Same(G,Fresh),"active source events cannot restart a run");
        for(int N=0;N<12;++N) {
            Input I;I.Up=N<4;I.Right=N<6;I.Fire=N<8;I.FirePressed=N==0;
            G.Step(I);Fresh.Step(I);Check(Same(G,Fresh),"following frames preserve RNG and input reset behavior");
        }
    }
}
template<class T> void IdleLoss(const char* Name,std::uint32_t Seed) {
    T G;G.Reset(Seed);int Steps=0;
    while(!G.GetStatus().Over && Steps<6000) {G.Step({});++Steps;}
    Check(G.GetStatus().Over,"idle pilot reaches a real loss within bounded steps");
    std::cout<<Name<<" idle loss at "<<Steps<<" steps, seed "<<Seed<<'\n';
    if(G.GetStatus().Over) Retry(G,Seed);
}
void RiftwingVictory() {
    // Existing documented pilot, restricted to its known seed and 1,200 steps.
    RiftwingGame G;G.Reset(1);int Steps=0;
    while(!G.GetStatus().Won && !G.GetStatus().Over && Steps<1200) {
        Frame Visible;G.Render(Visible);const auto& P=G.GetPlayer();double TargetY=300,NearestX=10000;
        for(const auto& C:Visible.Commands) {
            double X=0,Y=0;bool Enemy=false;
            if(C.Kind==Shape::Circle && C.Tint.R==255 && C.Tint.G==80 && C.Tint.B==80 && C.Size==12) {X=C.A.X;Y=C.A.Y;Enemy=true;}
            else if(C.Kind==Shape::Triangle && C.Tint.R==255 && C.Tint.G==100 && C.Tint.B==100) {X=C.A.X-10;Y=C.A.Y;Enemy=true;}
            if(Enemy && X>P.X+24 && X<NearestX) {NearestX=X;TargetY=Y;}
        }
        const double TargetX=G.HasBoss()?500:450;
        Input I;I.Fire=true;I.Right=P.X<TargetX-2;I.Left=P.X>TargetX+2;I.Down=P.Y<TargetY-2;I.Up=P.Y>TargetY+2;
        G.Step(I);++Steps;
    }
    Check(G.GetStatus().Won && !G.GetStatus().Over,"documented pilot reaches a distinct real Riftwing victory");
    std::cout<<"Riftwing victory at "<<Steps<<" steps\n";
    if(G.GetStatus().Won) Retry(G,1);
}
void DriverReplay() {
    Driver G;Check(G.Select("driftstone",730),"driver selects Driftstone");
    int Steps=0;
    while(!G.GetStatus().Over && Steps<6000) {G.Advance(Driver::StepSeconds);++Steps;}
    Check(G.GetStatus().Over,"driver reaches bounded terminal state");
    if(!G.GetStatus().Over) return;
    Input Pending;Pending.FirePressed=true;G.SetInput(Pending);
    Check(G.SourceControllerButton(1),"driver consumes terminal Start before generic pause");
    Driver Fresh;Fresh.Select("driftstone",730);
    G.Advance(Driver::StepSeconds);Fresh.Advance(Driver::StepSeconds);
    Check(!G.IsPaused() && SameFrame(G.GetFrame(),Fresh.GetFrame()),"driver replay clears old semantic edges");
}
}
int main() {
    for(std::uint32_t Seed:{0u,730u,UINT32_MAX}) {IdleLoss<DriftstoneGame>("Driftstone",Seed);IdleLoss<RiftwingGame>("Riftwing",Seed);}
    RiftwingVictory();DriverReplay();
    std::cout<<"Shooter terminal replay: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
