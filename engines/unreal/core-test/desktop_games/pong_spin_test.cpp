// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPongCore.h"
#include <iostream>
#include <limits>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
PongGame Return(const Input& I,double PlayerY=250,double BallVY=3,double BallY=300) {
    PongGame G;G.Reset(730);G.S.PlayerY=PlayerY;G.S.BallX=65;G.S.BallY=BallY;G.S.BallVX=-5;G.S.BallVY=BallVY;
    G.Step(I);return G;
}
bool SameState(const PongGame::State& A,const PongGame::State& B) {
    return A.PlayerY==B.PlayerY && A.ComputerY==B.ComputerY && A.BallX==B.BallX && A.BallY==B.BallY
        && A.BallVX==B.BallVX && A.BallVY==B.BallVY && A.PlayerScore==B.PlayerScore && A.ComputerScore==B.ComputerScore
        && A.ServeFrames==B.ServeFrames && A.ContactFrames==B.ContactFrames && A.PointFrames==B.PointFrames
        && A.LastPoint==B.LastPoint && A.LastContact==B.LastContact && A.Rally==B.Rally && A.BestRally==B.BestRally;
}
Input FollowThenMoveAtImpact(const PongGame::State& S) {
    Input I;
    if(S.BallVX<0 && S.BallX<105) {I.Up=S.BallVY<0;I.Down=S.BallVY>0;}
    else I.AxisY=Clamp((S.BallY-(S.PlayerY+50))/8,-1,1);
    return I;
}
bool HasText(const Frame& F,const std::string& Label) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label==Label) return true;
    return false;
}
}

int main() {
    PongGame G=Return({});
    Check(G.S.BallVX==5 && G.S.BallVY==3 && G.S.Rally==1,"neutral source return keeps its angle and one contact");
    G=Return({},250,-6);Check(G.S.BallVY==-6,"neutral return preserves existing spin");
    Input Up,Down,PadUp,PadDown;Up.Up=true;Down.Down=true;PadUp.PadUp=true;PadDown.PadDown=true;
    G=Return(Down);Check(G.S.PlayerY==256 && G.S.BallVY==6,"down movement adds half actual displacement");
    const auto DownState=G.S;
    G=Return(Up,250,-3);Check(G.S.PlayerY==244 && G.S.BallVY==-6,"up movement bends an upward return");
    const auto UpState=G.S;
    Check(SameState(Return(PadDown).S,DownState) && SameState(Return(PadUp,250,-3).S,UpState),"Pad and keyboard use the same moving-paddle rule");
    Input Stick;Stick.AxisY=.75;
    Check(SameState(Return(Stick).S,DownState),"equal analog displacement produces equal spin");
    Stick.AxisY=-.75;Check(SameState(Return(Stick,250,-3).S,UpState),"upward analog displacement matches keyboard");
    G=Return(Up);Check(G.S.BallVY==0,"opposing movement can deliberately flatten a return");
    Input Cancel;Cancel.Up=Cancel.Down=true;
    Check(Return(Cancel).S.BallVY==3,"opposing digital controls use net actual motion");
    Cancel={};Cancel.Down=true;Cancel.AxisY=-.75;
    Check(Return(Cancel).S.BallVY==3,"canceling keyboard and stick do not add spin");
    Input Combined;Combined.Down=true;Combined.AxisY=1;
    G=Return(Combined);Check(G.S.PlayerY==264 && G.S.BallVY==7,"combined downward inputs preserve source movement and cap spin");
    Combined={};Combined.Up=true;Combined.AxisY=-1;
    G=Return(Combined,250,-3);Check(G.S.PlayerY==236 && G.S.BallVY==-7,"combined upward inputs cap spin symmetrically");
    G=Return(Combined,0,3,50);Check(G.S.PlayerY==0 && G.S.BallVY==3,"blocked top-edge motion contributes no spin");
    Combined={};Combined.Down=true;Combined.AxisY=1;
    G=Return(Combined,500,3,550);Check(G.S.PlayerY==500 && G.S.BallVY==3,"blocked bottom-edge motion contributes no spin");
    Combined={};Combined.Up=true;Combined.AxisY=-1;
    G=Return(Combined,2,3,50);Check(G.S.PlayerY==0 && G.S.BallVY==2,"partially clamped upward move uses actual two-pixel displacement");
    Combined={};Combined.Down=true;Combined.AxisY=1;
    G=Return(Combined,498,3,550);Check(G.S.PlayerY==500 && G.S.BallVY==4,"partially clamped downward move uses actual two-pixel displacement");
    for(double AxisValue:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}) {
        Input Invalid;Invalid.AxisY=AxisValue;G=Return(Invalid);
        Check(G.S.BallVY==3 && std::isfinite(G.S.BallVY) && std::isfinite(G.S.PlayerY),"nonfinite stick input keeps a finite neutral return");
    }
    Stick.AxisY=100;G=Return(Stick);Check(G.S.PlayerY==258 && G.S.BallVY==7,"finite out-of-range stick remains bounded by existing input policy");

    G.Reset(730);G.Step(Down);Check(G.S.PlayerY==256 && G.S.BallVY==3,"moving without player contact does not bend the ball");
    G.Reset(730);G.S.BallX=735;G.S.BallVY=6;G.Step(Down);
    Check(G.S.BallVX==-5 && G.S.BallVY==6 && G.S.LastContact==-1 && G.S.ComputerY==250,"CPU return preserves spin and existing AI movement");
    G.Reset(730);G.S.BallX=60;G.Step(Down);
    Check(G.S.BallVX==5 && G.S.BallVY==3 && G.S.Rally==0,"outgoing player-window overlap cannot add spin");
    G=Return(Down);G.Step(Down);
    Check(G.S.BallVY==6 && G.S.Rally==1,"one player contact cannot compound spin while leaving the paddle");

    G.Reset(730);Frame F;G.Render(F);
    Check(F.Commands.size()==6,"initial source presentation stays six commands");
    Check(G.GetStatus().Note.find("move paddle at impact to add spin")!=std::string::npos,"status teaches how to bend returns");
    G=Return(Down);const auto BeforePresentation=G.S;
    for(int N=0;N<8;++N) {G.Render(F);G.GetStatus();}
    Check(HasText(F,"Move paddle at impact to add spin") && SameState(G.S,BeforePresentation),"post-contact guidance is presentation-only");

    G.Reset(730);G.S.BallX=799;G.S.BallY=100;G.S.BallVY=-6;G.Step({});
    Check(G.S.PlayerScore==1 && G.S.BallX==400 && G.S.BallY==300 && G.S.BallVX==-5 && G.S.BallVY==-6,"new point preserves spun velocity under existing serve rule");
    Check(G.S.ServeFrames==45 && G.S.PointFrames==90 && G.S.Rally==0 && !G.GetStatus().Over && !G.GetStatus().Won,"score still creates a bounded serve in an endless match");
    const auto Ready=G.S;G.Step(Down);
    Check(G.S.PlayerY==Ready.PlayerY+6 && G.S.BallX==400 && G.S.BallY==300 && G.S.BallVY==-6 && G.S.ServeFrames==44,"paddles stay live during serve without adding ball spin");
    Input Early;Early.FirePressed=true;G.Step(Early);
    Check(G.S.ServeFrames==0 && G.S.BallX==400 && G.S.BallY==300,"early serve still waits for following live step");
    G.Step({});Check(G.S.BallX==395 && G.S.BallY==294 && G.S.BallVY==-6,"retained spin resumes with original serve timing");
    G.Reset(730);G.S.BallX=1;G.S.BallVX=-5;G.S.BallVY=0;G.Step({});
    Check(G.S.ComputerScore==1 && G.S.BallVY==0 && G.S.ServeFrames==45,"a deliberately flat spin also follows existing serve retention");

    // One bounded real-Reset policy, verified in a private pre-change experiment.
    // No injected ball/paddle state or private candidate wrapper is used here.
    G.Reset(730);int FirstReturn=0,ScoreFrame=0;double FirstDelta=0,FirstVy=0;
    for(int Step=1;Step<=420;++Step) {
        const auto Before=G.S;G.Step(FollowThenMoveAtImpact(Before));
        if(!FirstReturn && G.S.Rally>Before.Rally && G.S.LastContact==1) {
            FirstReturn=Step;FirstDelta=G.S.PlayerY-Before.PlayerY;FirstVy=G.S.BallVY;
        }
        if(G.S.PlayerScore>0) {ScoreFrame=Step;break;}
    }
    Check(FirstReturn>0 && FirstReturn<=420 && FirstDelta==-6 && FirstVy==-6,"ordinary input creates a moving return from real Reset");
    Check(ScoreFrame>FirstReturn && ScoreFrame<=420 && G.S.PlayerScore==1 && G.S.ComputerScore==0,"moving return reaches a real player point through unchanged CPU/scoring");
    Check(!G.GetStatus().Over && !G.GetStatus().Won,"successful return does not invent a match-ending threshold");
    std::cout<<"Pong moving-paddle spin: "<<Checks-Failed<<'/'<<Checks<<" checks passed; return "<<FirstReturn<<", point "<<ScoreFrame<<'\n';
    return Failed?1:0;
}
