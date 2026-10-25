// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameState(const PongGame::State& A,const PongGame::State& B) {
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
std::string Lower(std::string S) {for(char& C:S) if(C>='A'&&C<='Z') C=static_cast<char>(C-'A'+'a');return S;}
bool Text(const Frame& F,const std::string& Part) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Text&&Lower(C.Label).find(Lower(Part))!=std::string::npos;});
}
bool RectAt(const Frame& F,double X,double Y,double W,double H) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Rectangle&&C.A.X==X&&C.A.Y==Y&&C.B.X==W&&C.B.Y==H;});
}
PongGame Quick() {PongGame G;G.SetOption(2,730);return G;}
Input Edge(int Which) {Input I;I.FirePressed=Which==0;I.JumpPressed=Which==1;I.ActionPressed=Which==2;return I;}
void Goal(PongGame& G,bool Human) {
    G.S.ServeFrames=0;G.S.BallX=Human?799:1;G.S.BallY=300;G.S.BallVX=Human?5:-5;G.S.BallVY=0;G.Step({});
}
PongGame Complete(bool Human) {
    auto G=Quick();
    for(int Point=1;Point<=5;++Point) {
        Goal(G,Human);const auto Status=G.GetStatus();
        Check(G.S.PlayerScore==(Human?Point:0)&&G.S.ComputerScore==(Human?0:Point),"real boundary step awards exactly one point");
        Check(Status.Score==G.S.PlayerScore&&Status.Over==(Point==5)&&Status.Won==(Human&&Point==5),"only the fifth point ends the selected side's match");
        if(Point<5) Check(G.S.ServeFrames==45&&G.S.LastPoint==(Human?1:-1),"points one to four retain normal match serve preparation");
    }return G;
}
void ModesAndServe() {
    PongGame G;Frame F;G.Render(F);Check(G.GetOption()==0&&F.Width==800&&F.Height==600&&F.Commands.size()==6,"endless Match remains the unchanged default opening");
    Check(G.SetOption(1,730)&&G.GetOption()==1&&G.S.ServeFrames==120,"rally practice remains selectable");
    G.Render(F);Check(F.Width==800&&F.Height==720,"practice keeps its existing separate court layout");
    Check(G.SetOption(2,730)&&G.GetOption()==2&&G.S.ServeFrames==45&&G.S.LastPoint==0,"First to 5 starts with neutral forty-five-step preparation");
    Check(G.S.PlayerScore==0&&G.S.ComputerScore==0&&!G.GetStatus().Over&&!G.GetStatus().Won,"fresh quick match has clean live score");
    const auto Before=G.S;Frame BeforeFrame;G.Render(BeforeFrame);
    Check(!G.SetOption(3,99)&&G.GetOption()==2&&SameState(Before,G.S),"invalid option three preserves active quick match");
    G.Render(F);Check(SameFrame(F,BeforeFrame),"invalid option also preserves presentation");
    G.S.PlayerScore=3;G.Reset(99);Check(G.GetOption()==2&&SameState(G.S,Quick().S),"Reset retains selected mode and clears match progress");
    Input Down;Down.Down=true;G.Step(Down);
    Check(G.S.PlayerY==256&&G.S.ServeFrames==44&&G.S.BallX==400&&G.S.BallY==300,"paddle stays live while opening ball waits");
    for(int N=0;N<43;++N) G.Step({});Check(G.S.ServeFrames==1&&G.S.BallX==400,"automatic serve keeps the ball still through step forty-four");
    G.Step({});Check(G.S.ServeFrames==0&&G.S.BallX==400&&G.S.BallY==300,"forty-fifth preparation step ends without implicit launch");
    G.Step({});Check(G.S.BallX==405&&G.S.BallY==303,"automatic opening launches on the following frame with match velocity");
    for(int Which=0;Which<3;++Which) {
        G=Quick();auto I=Edge(Which);I.Down=true;G.Step(I);
        Check(G.S.ServeFrames==0&&G.S.PlayerY==256&&G.S.BallX==400&&G.S.BallY==300,"each fresh serve edge ends preparation while retaining paddle control");
        G.Step({});Check(G.S.BallX==405&&G.S.BallY==303,"each early serve launches only on the next frame");
    }
    G=Quick();Input Held;Held.Fire=Held.Jump=Held.Action=true;G.Step(Held);
    Check(G.S.ServeFrames==44&&G.S.BallX==400,"held actions alone do not skip opening preparation");
}
void ResultsAndReplay() {
    const auto Fresh=Quick();
    for(bool Human:{true,false}) {
        auto G=Complete(Human);const auto End=G.S;const auto Note=G.GetStatus().Note;Frame F;G.Render(F);const auto Picture=F;
        Input Held;Held.Fire=Held.Jump=Held.Action=true;Held.Up=Held.Down=true;Held.AxisY=1;
        for(int N=0;N<8;++N) G.Step(Held);
        G.Render(F);Check(SameState(End,G.S)&&SameFrame(Picture,F)&&G.GetStatus().Note==Note,"result freezes all ball, paddle, score and feedback state under held inputs");
        Check(Text(F,Human?"You reached 5":"CPU reached 5")&&Text(F,"Space")&&Text(F,"pad A"),"result identifies the winner and primary replay controls");
        for(int Which=0;Which<3;++Which) {
            auto Replay=G;auto I=Edge(Which);I.Down=true;Replay.Step(I);
            Check(Replay.GetOption()==2&&!Replay.GetStatus().Over&&!Replay.GetStatus().Won&&SameState(Replay.S,Fresh.S),"each fresh replay edge returns to the same clean warmup without moving or serving");
        }
    }
}
void PresentationAndParity() {
    auto G=Quick();Frame F;G.Render(F);
    Check(F.Width==800&&F.Height==690&&RectAt(F,50,G.S.PlayerY+90,10,100)&&RectAt(F,740,G.S.ComputerY+90,10,100),"quick match reserves ninety pixels above its unchanged hundred-pixel paddles");
    const bool Ball=std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Circle&&C.Size==8&&C.A.X==G.S.BallX&&C.A.Y==G.S.BallY+90;});
    Check(Ball&&Text(F,"First to 5")&&Text(F,"Space")&&Text(F,"pad A"),"quick match names its goal and clear early serve beside an offset court");
    int Counters=0;bool AboveCourt=true;for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&(C.Label=="YOU 0"||C.Label=="CPU 0")) {++Counters;AboveCourt=AboveCourt&&C.A.Y>=0&&C.A.Y+C.Size<=90;}
    Check(Counters==2&&AboveCourt&&Text(F,"Ready for the first rally")&&!Text(F,"CPU point"),"both score counters stay above play and neutral opening claims no scored point");
    const auto Before=G.S;const auto Note=G.GetStatus().Note;Frame Again;
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();}
    Check(SameState(Before,G.S)&&SameFrame(F,Again)&&G.GetStatus().Note==Note,"rendering and status leave quick match and timers untouched");
    PongGame Endless;G.S.ServeFrames=0;G.S.BallX=65;G.S.BallY=300;G.S.BallVX=-5;G.S.BallVY=2;G.S.Rally=2;G.S.BestRally=4;Endless.S=G.S;
    for(int N=0;N<80;++N) {
        Input I;I.Down=N%20<10;I.Up=!I.Down;I.AxisY=N%4==0?.25:0;G.Step(I);Endless.Step(I);
        Check(SameState(G.S,Endless.S)&&!G.GetStatus().Over,"preterminal match keeps endless physics step "+std::to_string(N));
    }
    Goal(G,true);Goal(Endless,true);Check(SameState(G.S,Endless.S)&&G.S.PlayerScore==1,"ordinary quick-match point shares endless scoring and serve rules");
}
void DriverLifecycle() {
    Driver D;Check(D.Select("pong",730),"Driver selects existing Pong");D.Advance(Driver::StepSeconds*2.5);
    Input Stale;Stale.Down=Stale.Fire=Stale.Jump=Stale.Action=true;Stale.FirePressed=Stale.JumpPressed=Stale.ActionPressed=true;
    D.SetInput(Stale);
    Check(D.SetOption(2)&&D.GetOption()==2&&!D.IsPaused()&&D.Ticks()==0&&D.GetSeed()==730,"mode selection resets accounting and input while retaining seed");
    Check(D.Advance(Driver::StepSeconds*.5)==0,"mode selection clears previous partial time");
    auto Expected=Quick();Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first driver step has no stale movement or early-serve edge");
    const auto Paused=D.GetFrame();D.SetPaused(true);D.SetInput(Stale);
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Paused,D.GetFrame()),"pause freezes quick match");
    D.SetPaused(false);Expected.Step({});Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"unpause clears queued input rather than serving or moving");
    const auto Before=D.GetFrame();const auto Ticks=D.Ticks();
    Check(!D.SetOption(3)&&D.GetOption()==2&&D.Ticks()==Ticks&&SameFrame(Before,D.GetFrame()),"invalid Driver mode preserves active match and accounting");
    D.SetPaused(true);D.SetInput(Stale);D.Restart();Expected=Quick();Expected.Render(F);
    Check(D.GetOption()==2&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"native Restart retains First to 5 and restores full preparation");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"Restart clears held and fresh input before the next fixed step");
}
}
int main() {
    ModesAndServe();ResultsAndReplay();PresentationAndParity();DriverLifecycle();
    std::cout<<"Pong First to 5: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
