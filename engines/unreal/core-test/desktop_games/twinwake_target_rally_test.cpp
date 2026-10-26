// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <array>
#include <iostream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0,RouteSteps=0,RouteReturns=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameState(const TwinwakeGame::State& A,const TwinwakeGame::State& B) {
    return A.PlayerY==B.PlayerY&&A.ComputerY==B.ComputerY&&A.BallX==B.BallX&&A.BallY==B.BallY&&A.BallVX==B.BallVX&&A.BallVY==B.BallVY
        &&A.PlayerScore==B.PlayerScore&&A.ComputerScore==B.ComputerScore&&A.ServeFrames==B.ServeFrames&&A.ContactFrames==B.ContactFrames
        &&A.PointFrames==B.PointFrames&&A.LastPoint==B.LastPoint&&A.LastContact==B.LastContact&&A.Rally==B.Rally&&A.BestRally==B.BestRally;
}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
bool HasText(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&C.Label.find(Part)!=std::string::npos) return true;
    return false;
}
TwinwakeGame Target() {TwinwakeGame G;G.SetOption(3,730);return G;}
Input Edge(int N) {Input I;I.FirePressed=N==0;I.JumpPressed=N==1;I.ActionPressed=N==2;return I;}
TwinwakeGame Wall(int Stage,double Y,double Vx=4) {
    auto G=Target();G.S.ServeFrames=0;G.S.PlayerScore=Stage;G.S.Rally=4;G.S.BestRally=7;
    G.S.BallX=Vx>0?729:734;G.S.BallY=Y;G.S.BallVX=Vx;G.S.BallVY=0;G.S.PointFrames=0;G.Step({});return G;
}
// Public inputs only: a small impact-spin choice is previewed on copies until a
// real right-wall reflection. The route instance receives no pose/score writes.
double ImpactAxis(const TwinwakeGame& G,double Fallback) {
    constexpr std::array<double,17> Axes{{-1,-.875,-.75,-.625,-.5,-.375,-.25,-.21,0,.21,.25,.375,.5,.625,.75,.875,1}};
    const double Center=G.S.PlayerScore==0?140:G.S.PlayerScore==1?310:480;
    double Best=Fallback,Error=1e9;
    for(double AxisY:Axes) {
        auto Probe=G;Input I;I.AxisY=AxisY;Probe.Step(I);
        if(Probe.S.BallVX<=0) continue;
        for(int N=0;N<180;++N) {
            const auto Before=Probe.S;Probe.Step({});
            if(Before.BallVX>0&&Probe.S.BallVX<0&&Probe.S.BallX==732) {
                const double Candidate=std::abs(Probe.S.BallY-Center);
                if(Candidate<Error) {Error=Candidate;Best=AxisY;}break;
            }
        }
    }return Best;
}
TwinwakeGame PublicRoute() {
    auto G=Target();
    for(;RouteSteps<6000&&RouteReturns<12&&!G.GetStatus().Over;++RouteSteps) {
        const auto Before=G.S;Input I;I.AxisY=Clamp((Before.BallY-(Before.PlayerY+70))/8,-1,1);
        if(Before.ServeFrames==0&&Before.BallVX<0&&Before.BallX+Before.BallVX>50&&Before.BallX+Before.BallVX<70)
            I.AxisY=ImpactAxis(G,I.AxisY);
        G.Step(I);
        if(Before.ServeFrames==0&&Before.BallVX<0&&G.S.BallVX>0) ++RouteReturns;
    }
    Check(G.GetOption()==3&&G.S.PlayerScore==3&&G.GetStatus().Over&&G.GetStatus().Won,"bounded real paddle inputs complete all three target bands from Reset");
    Check(RouteSteps<=6000&&RouteReturns<=12&&RouteReturns>=3&&G.S.ComputerScore==0,"public route stays within its declared return/step budget without CPU points");
    return G;
}
void BoundariesAndMiss() {
    constexpr double Low[3]={60,230,400},High[3]={220,390,560};
    for(int Stage=0;Stage<3;++Stage) {
        for(double Y:{Low[Stage],High[Stage]}) {
            auto G=Wall(Stage,Y);
            Check(G.S.PlayerScore==Stage+1&&G.S.BallX==732&&G.S.BallVX==-4,"inclusive band endpoint counts on the actual outward wall bounce");
            Check(G.S.Rally==4&&G.S.BestRally==7&&G.S.PointFrames==90&&G.S.LastPoint==1,"target hit preserves rally and sets its temporary success cue");
            Check(G.GetStatus().Score==Stage+1&&G.GetStatus().Over==(Stage==2)&&G.GetStatus().Won==(Stage==2),"only third target completes the round and status counts cleared targets");
            const auto Score=G.S.PlayerScore;G.Step({});Check(G.S.PlayerScore==Score,"a reflected ball or final frame cannot count the same target twice");
        }
        for(double Y:{Low[Stage]-.01,High[Stage]+.01}) {
            const auto G=Wall(Stage,Y);Check(G.S.PlayerScore==Stage&&G.S.BallVX==-4&&G.S.PointFrames==0,"outside current band still reflects normally without progress or success cue");
        }
        const auto Incoming=Wall(Stage,(Low[Stage]+High[Stage])/2,-4);
        Check(Incoming.S.PlayerScore==Stage&&Incoming.S.BallVX==-4,"incoming right-side overlap does not advance a target");
    }
    Check(Wall(0,310).S.PlayerScore==0&&Wall(1,480).S.PlayerScore==1,"later bands cannot be collected out of order");
    auto G=Target();G.S.PlayerScore=2;G.S.ServeFrames=0;G.S.BallX=1;G.S.BallVX=-4;G.S.BallY=300;G.S.BallVY=-4;G.S.Rally=8;G.S.BestRally=9;G.Step({});
    Check(G.S.PlayerScore==2&&G.S.ComputerScore==0&&G.S.Rally==0&&G.S.BestRally==9&&!G.GetStatus().Over,"left miss keeps completed targets and best while resetting current rally");
    Check(G.S.ServeFrames==120&&G.S.BallX==400&&G.S.BallY==300&&G.S.BallVX==-4&&G.S.BallVY==2,"miss prepares the existing gentle practice serve");
    G.Step(Edge(0));Check(G.S.ServeFrames==0&&G.S.BallX==400,"fresh action ends preparation without an implicit ball move");
    G.Step({});Check(G.S.BallX==396&&G.S.BallY==302&&G.S.PlayerScore==2,"following frame serves with retained target progress");
}
void ModesAndResults(const TwinwakeGame& Result) {
    TwinwakeGame G;Frame F;G.Render(F);Check(G.GetOption()==0&&F.Width==800&&F.Height==600&&F.Commands.size()==6,"default endless Match keeps its original opening");
    G.SetOption(1,730);G.Render(F);Check(G.S.ServeFrames==120&&F.Height==720&&!G.GetStatus().Over,"ordinary practice retains its opening");
    auto T=Target();T.S.ServeFrames=0;G.S=T.S;
    for(int N=0;N<12;++N) {Input I;I.AxisY=N<6?.5:-.5;G.Step(I);T.Step(I);}
    Check(SameState(G.S,T.S),"before a wall target event mode three keeps ordinary practice physics");
    G.SetOption(2,730);G.Render(F);Check(G.S.ServeFrames==45&&F.Height==690&&!G.GetStatus().Over,"First to 5 retains its own opening");
    T=Target();const auto Before=T.S;T.Render(F);const auto BeforeFrame=F;
    Check(!T.SetOption(-1,99)&&!T.SetOption(4,99)&&T.GetOption()==3&&SameState(T.S,Before),"invalid modes preserve the active target rally");
    T.Render(F);Check(SameFrame(F,BeforeFrame),"invalid options preserve presentation");
    T=Result;const auto End=T.S;T.Render(F);const auto Picture=F;const auto Note=T.GetStatus().Note;
    Input Held;Held.Fire=Held.Jump=Held.Action=true;Held.Down=true;Held.AxisY=1;
    for(int N=0;N<8;++N) {T.Step(Held);T.Render(F);T.GetStatus();}
    Check(SameState(T.S,End)&&SameFrame(F,Picture)&&T.GetStatus().Note==Note,"result freezes ball paddles targets timers and rendering under held input");
    Check(HasText(Picture,"TARGET")&&HasText(Picture,"Space"),"result identifies target play and offers an explicit replay control");
    for(int N=0;N<3;++N) {T=Result;auto I=Edge(N);I.Down=true;T.Step(I);
        Check(T.GetOption()==3&&SameState(T.S,Target().S)&&!T.GetStatus().Over,"fresh replay edges retain mode and return before movement or early serve");}
    T=Result;T.Reset(99);Check(T.GetOption()==3&&SameState(T.S,Target().S),"Reset retains selected target mode and clears all progress");
    T=Target();const auto Pure=T.S;T.Render(F);const auto P=F;
    for(int N=0;N<3;++N) {T.Render(F);T.GetStatus();}
    Check(SameState(T.S,Pure)&&SameFrame(F,P),"live presentation and status are side-effect free");
}
void DriverLifecycle() {
    Driver D;Check(D.Select("twinwake",730),"Driver selects existing Twinwake");D.Advance(Driver::StepSeconds*2.5);
    Input Stale;Stale.Down=Stale.Fire=Stale.Jump=Stale.Action=true;Stale.FirePressed=Stale.JumpPressed=Stale.ActionPressed=true;D.SetInput(Stale);D.SetPaused(true);D.SetInput(Stale);
    Check(D.SetOption(3)&&D.GetOption()==3&&!D.IsPaused()&&D.Ticks()==0&&D.GetSeed()==730,"mode selection clears pause and accounting while retaining seed");
    Check(D.Advance(Driver::StepSeconds*.5)==0,"mode selection drops previous partial time debt");
    auto Expected=Target();Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first fixed step has no old held movement or early-serve edge");
    const auto Paused=D.GetFrame();D.SetPaused(true);D.SetInput(Stale);
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Paused,D.GetFrame()),"pause freezes target rally");
    D.SetPaused(false);Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"unpause clears queued source inputs");
    D.SetInput(Stale);D.Restart();Expected=Target();Expected.Render(F);
    Check(D.GetOption()==3&&D.Ticks()==0&&!D.IsPaused()&&SameFrame(D.GetFrame(),F),"Restart keeps target mode with clean preparation");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"Restart also clears stale held and fresh actions");
}
}
int main() {
    const auto Result=PublicRoute();BoundariesAndMiss();ModesAndResults(Result);DriverLifecycle();
    std::cout<<"Twinwake target rally: "<<Checks-Failed<<'/'<<Checks<<" checks passed; route "<<RouteSteps<<" steps, "<<RouteReturns<<" returns\n";
    return Failed?1:0;
}
