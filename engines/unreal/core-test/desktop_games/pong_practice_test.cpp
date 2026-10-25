// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <limits>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameState(const PongGame::State& A,const PongGame::State& B) {
    return A.PlayerY==B.PlayerY && A.ComputerY==B.ComputerY && A.BallX==B.BallX && A.BallY==B.BallY
        && A.BallVX==B.BallVX && A.BallVY==B.BallVY && A.PlayerScore==B.PlayerScore && A.ComputerScore==B.ComputerScore
        && A.ServeFrames==B.ServeFrames && A.ContactFrames==B.ContactFrames && A.PointFrames==B.PointFrames
        && A.LastPoint==B.LastPoint && A.LastContact==B.LastContact && A.Rally==B.Rally && A.BestRally==B.BestRally;
}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()
        || A.Background.R!=B.Background.R || A.Background.G!=B.Background.G
        || A.Background.B!=B.Background.B || A.Background.A!=B.Background.A) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
std::string Lower(std::string Text) {
    for(char& C:Text) if(C>='A' && C<='Z') C=static_cast<char>(C-'A'+'a');
    return Text;
}
bool HasText(const Frame& F,const std::string& Part) {
    const auto Wanted=Lower(Part);
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && Lower(C.Label).find(Wanted)!=std::string::npos) return true;
    return false;
}
bool HasNumber(const Frame& F,int Value) {
    const auto Wanted=std::to_string(Value);
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text) {
        for(std::size_t Pos=C.Label.find(Wanted);Pos!=std::string::npos;Pos=C.Label.find(Wanted,Pos+1)) {
            const auto End=Pos+Wanted.size();
            const bool Before=Pos>0 && C.Label[Pos-1]>='0' && C.Label[Pos-1]<='9';
            const bool After=End<C.Label.size() && C.Label[End]>='0' && C.Label[End]<='9';
            if(!Before && !After) return true;
        }
    }
    return false;
}
bool HasRect(const Frame& F,double X,double Y,double W,double H) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle && C.A.X==X && C.A.Y==Y && C.B.X==W && C.B.Y==H) return true;
    return false;
}
PongGame Practice() {
    PongGame G;Game& Core=G;Core.SetOption(1,730);return G;
}
PongGame PlayerContact(const Input& I={},double PlayerY=250,double BallY=300,double BallVY=2,
    std::uint32_t Rally=0,std::uint32_t Best=0) {
    auto G=Practice();G.S.ServeFrames=0;G.S.PlayerY=PlayerY;
    G.S.BallX=65;G.S.BallY=BallY;G.S.BallVX=-4;G.S.BallVY=BallVY;
    G.S.Rally=Rally;G.S.BestRally=Best;G.Step(I);return G;
}
void Modes() {
    PongGame G;Game& Core=G;
    Check(Core.GetOption()==0,"match remains the default mode");
    Check(Core.SetOption(1,730) && Core.GetOption()==1,"existing virtual option API selects rally practice");
    Check(G.S.ServeFrames==120 && G.S.BallVX==-4 && G.S.BallVY==2,"practice starts with gentle leftward ball and preparation window");
    Check(G.S.Rally==0 && G.S.BestRally==0 && G.S.PlayerScore==0 && G.S.ComputerScore==0,"new practice clears session counts and match points");
    Input Move;Move.Down=true;G.Step(Move);
    const auto Before=G.S;Frame BeforeFrame;G.Render(BeforeFrame);
    for(int Value:{-1,2,std::numeric_limits<int>::min(),std::numeric_limits<int>::max()}) {
        const bool Accepted=Core.SetOption(Value,12);Frame After;G.Render(After);
        Check(!Accepted && Core.GetOption()==1 && SameState(G.S,Before) && SameFrame(After,BeforeFrame),"invalid mode leaves the complete active practice unchanged");
    }
    G.S.Rally=3;G.S.BestRally=9;G.Reset(123);
    Check(Core.GetOption()==1 && G.S.ServeFrames==120 && G.S.Rally==0 && G.S.BestRally==0,
        "Restart retains practice mode while starting a fresh session best");
    Check(Core.SetOption(0,123) && Core.GetOption()==0 && SameState(G.S,PongGame::State{}),"switching to match restores its established initial state");
    Frame Match;G.Render(Match);
    Check(Match.Width==800 && Match.Height==600 && Match.Commands.size()==6,"default match keeps its original opening frame");
    Check(Core.SetOption(1,123) && G.S.ServeFrames==120 && G.S.Rally==0 && G.S.BestRally==0,"returning to practice resets the session deliberately");
}
void CountdownAndMovement() {
    auto G=Practice();const auto Ready=G.S;
    Frame F;G.Render(F);Check(HasText(F,"Ready in 2"),"opening countdown shows two seconds");
    for(int N=0;N<60;++N) G.Step({});
    G.Render(F);Check(G.S.ServeFrames==60 && HasText(F,"Ready in 1"),"countdown advances to one second through normal fixed steps");
    for(int N=0;N<59;++N) G.Step({});
    Check(G.S.ServeFrames==1 && G.S.BallX==Ready.BallX && G.S.BallY==Ready.BallY,"ball stays ready for the full preparation window");
    G.Step({});Check(G.S.ServeFrames==0 && G.S.BallX==Ready.BallX && G.S.BallY==Ready.BallY,"automatic countdown completes before the launch frame");
    G.Step({});Check(G.S.BallX==Ready.BallX-4 && G.S.BallY==Ready.BallY+2,"automatic serve launches gently on the following frame");
    for(int Edge=0;Edge<3;++Edge) {
        G=Practice();const auto Before=G.S;Input I;
        I.FirePressed=Edge==0;I.JumpPressed=Edge==1;I.ActionPressed=Edge==2;G.Step(I);
        Check(G.S.ServeFrames==0 && G.S.BallX==Before.BallX && G.S.BallY==Before.BallY,"each existing fresh serve action ends countdown without moving the ball yet");
        G.Step({});Check(G.S.BallX==Before.BallX-4 && G.S.BallY==Before.BallY+2,"early serve uses the same following-frame launch");
    }
    G=Practice();Input Held;Held.Fire=Held.Jump=Held.Action=true;G.Step(Held);
    Check(G.S.ServeFrames==119,"held actions without a fresh edge do not skip preparation");
    G=Practice();const double Start=G.S.PlayerY;Input Down;Down.Down=true;G.Step(Down);
    Check(G.S.PlayerY==Start+6 && G.S.ServeFrames==119,"digital paddle movement remains live at six pixels during preparation");
    G=Practice();const double PadStart=G.S.PlayerY;Input Pad;Pad.PadUp=true;G.Step(Pad);
    Check(G.S.PlayerY==PadStart-6,"D-pad movement remains available during preparation");
    G=Practice();const double StickStart=G.S.PlayerY;Input Stick;Stick.AxisY=1;G.Step(Stick);
    Check(G.S.PlayerY==StickStart+8,"analog paddle movement keeps its eight-pixel rate");
    G=Practice();G.S.PlayerY=100;Down.AxisY=1;G.Step(Down);
    Check(G.S.PlayerY==114,"digital and analog movement retain their additive source behavior");
    G=Practice();G.S.PlayerY=459;Down.AxisY=0;G.Step(Down);
    Check(G.S.PlayerY==460,"larger practice paddle stops at the lower court boundary");
    G=Practice();G.S.PlayerY=2;Input Up;Up.Up=true;G.Step(Up);
    Check(G.S.PlayerY==0,"practice paddle also clamps at the upper court boundary");
}
void ContactsAndSpin() {
    auto G=PlayerContact();
    Check(G.S.BallVX==4 && G.S.BallVY==2 && G.S.Rally==1 && G.S.BestRally==1,"one neutral player return keeps angle and increments rally and best once");
    Check(G.S.LastContact==1 && G.S.ContactFrames==8,"player return retains contact feedback");
    G.Step({});Check(G.S.BallVX==4 && G.S.Rally==1 && G.S.BestRally==1,"outgoing player overlap does not count a second return");
    Check(PlayerContact({},250,242,0).S.BallVX==4,"ball radius makes exact top-edge contact forgiving");
    Check(PlayerContact({},250,398,0).S.BallVX==4,"ball radius includes the bottom edge of the 140-pixel paddle");
    Check(PlayerContact({},250,241.75,0).S.BallVX==-4,"ball fully above the player paddle is not a return");
    Check(PlayerContact({},250,398.25,0).S.BallVX==-4,"ball fully below the player paddle is not a return");
    G=Practice();G.S.ServeFrames=0;G.S.BallX=54;G.S.BallVX=-4;G.S.BallY=300;G.S.BallVY=0;G.Step({});
    Check(G.S.BallVX==-4 && G.S.Rally==0,"original strict left x-window still excludes its lower boundary");
    G=Practice();G.S.ServeFrames=0;G.S.BallX=74;G.S.BallVX=-4;G.S.BallY=300;G.S.BallVY=0;G.Step({});
    Check(G.S.BallVX==-4 && G.S.Rally==0,"original strict left x-window still excludes its upper boundary");
    Input Down,Up;Down.Down=true;Up.Up=true;
    G=PlayerContact(Down);Check(G.S.PlayerY==256 && G.S.BallVY==4,"moving down adds spin capped at the gentler positive limit");
    G=PlayerContact(Up,250,300,-2);Check(G.S.PlayerY==244 && G.S.BallVY==-4,"moving up has the matching negative spin cap");
    G=PlayerContact(Down,460,500,2);Check(G.S.PlayerY==460 && G.S.BallVY==2,"pushing a blocked paddle cannot create spin");
    G=PlayerContact(Down,458,500,0);Check(G.S.PlayerY==460 && G.S.BallVY==1,"partial bottom clamping adds only actual paddle displacement");
    G=PlayerContact(Up,2,50,0);Check(G.S.PlayerY==0 && G.S.BallVY==-1,"partial top clamping also uses actual movement");
    G=PlayerContact({},250,300,2,4,9);
    Check(G.S.Rally==5 && G.S.BestRally==9 && G.S.PointFrames==90 && G.S.LastPoint==1,"fifth player return celebrates while preserving a higher session best");
    Check(G.GetStatus().Score==5 && !G.GetStatus().Over && !G.GetStatus().Won,"practice score is current returns and milestones do not end play");
    G.Step({});Check(G.S.PointFrames==89,"idle frames count celebration down instead of renewing it");
    const auto Maximum=std::numeric_limits<std::uint32_t>::max();
    G=PlayerContact({},250,300,2,Maximum,Maximum);
    Check(G.S.Rally==Maximum && G.S.BestRally==Maximum,"practice rally counters saturate without wrapping");
}
void WallAndRetry() {
    auto G=Practice();G.S.ServeFrames=0;G.S.BallX=729;G.S.BallY=30;G.S.BallVX=4;G.S.BallVY=0;
    G.S.ComputerY=300;G.S.Rally=2;G.S.BestRally=7;G.Step({});
    Check(G.S.BallX==732 && G.S.BallVX==-4,"practice wall returns the ball radius at the right boundary outside the CPU window");
    Check(G.S.Rally==2 && G.S.BestRally==7 && G.S.PlayerScore==0 && G.S.ComputerScore==0,"wall reflection adds no player return or match point");
    G.Step({});Check(G.S.BallX==728 && G.S.BallVX==-4 && G.S.Rally==2,"outgoing wall overlap neither flips again nor adds a return");
    G=Practice();G.S.ServeFrames=0;G.S.BallX=729;G.S.BallY=570;G.S.BallVX=4;G.S.BallVY=0;
    G.S.ComputerY=0;G.Step({});
    Check(G.S.BallX==732 && G.S.BallVX==-4,"return wall also covers the lower court");
    G=Practice();G.S.ServeFrames=0;G.S.BallX=1;G.S.BallY=320;G.S.BallVX=-4;G.S.BallVY=-4;
    G.S.Rally=7;G.S.BestRally=12;G.Step({});
    Check(G.S.Rally==0 && G.S.BestRally==12 && G.S.PlayerScore==0 && G.S.ComputerScore==0,"miss resets current rally while preserving best without opponent points");
    Check(G.S.BallX==400 && G.S.BallY==300 && G.S.BallVX==-4 && G.S.BallVY==2 && G.S.ServeFrames==120,"miss restores a gentle centered serve and full preparation time");
    Check(G.S.PointFrames==90 && G.S.LastPoint==-1 && !G.GetStatus().Over && !G.GetStatus().Won,"miss gives temporary retry feedback without a terminal state");
    Frame F;G.Render(F);Check(!HasText(F,"CPU point"),"practice retry does not present an opponent penalty");
    Input Early;Early.JumpPressed=true;G.Step(Early);G.Step({});
    Check(G.S.BallX==396 && G.S.BallY==302 && G.S.BestRally==12,"player can immediately begin another rally with the previous best intact");
}
void Presentation() {
    auto G=Practice();G.S.ServeFrames=0;G.S.Rally=3;G.S.BestRally=8;
    Frame F;G.Render(F);
    Check(F.Width==800 && F.Height==720,"practice HUD has its own space above the existing court");
    Check(HasRect(F,50,G.S.PlayerY+120,10,140) && HasRect(F,740,120,10,600),"practice visibly presents the forgiving paddle and full court return wall");
    Check(HasText(F,"practice") && HasText(F,"return") && HasNumber(F,3) && HasText(F,"best") && HasNumber(F,8),"practice presentation identifies mode current returns and session best");
    const auto Before=G.S;const auto StatusBefore=G.GetStatus();const int Option=G.GetOption();
    Frame Again;for(int N=0;N<8;++N) {G.Render(Again);G.GetStatus();}
    const auto StatusAfter=G.GetStatus();
    Check(SameState(Before,G.S) && G.GetOption()==Option && SameFrame(F,Again)
        && StatusBefore.Score==StatusAfter.Score && StatusBefore.Lives==StatusAfter.Lives
        && StatusBefore.Over==StatusAfter.Over && StatusBefore.Won==StatusAfter.Won && StatusBefore.Note==StatusAfter.Note,
        "drawing and reading practice status cannot advance play or alter counters");
    Check(StatusBefore.Score==3 && Lower(StatusBefore.Note).find("practice")!=std::string::npos,"status reports current practice returns and names its mode");
}
void DriverModeChange() {
    Driver D;Check(D.Select("pong",730),"driver opens existing Pong engine");
    D.Advance(Driver::StepSeconds*2);D.Advance(Driver::StepSeconds*0.5);
    Input Stale;Stale.Down=Stale.FirePressed=Stale.JumpPressed=Stale.ActionPressed=true;D.SetInput(Stale);
    Check(D.SetOption(1) && D.GetOption()==1 && D.GetSeed()==730 && D.Ticks()==0,"mode selection keeps driver seed and resets fixed-step accounting");
    Check(D.Advance(Driver::StepSeconds*0.5)==0 && D.Ticks()==0,"mode selection discards old partial time debt");
    auto Expected=Practice();Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*0.5)==1 && SameFrame(D.GetFrame(),F),"mode selection clears stale movement and all early-serve edges");
    D.SetPaused(true);D.SetInput(Stale);
    Check(D.Advance(Driver::StepSeconds*8)==0 && D.IsPaused(),"normal driver pause freezes the practice loop");
    Check(D.SetOption(1) && !D.IsPaused() && D.Ticks()==0,"explicit mode selection restarts from pause");
    Check(D.Advance(Driver::StepSeconds)==1 && SameFrame(D.GetFrame(),F),"paused mode selection also discards queued actions");
    const auto Before=D.GetFrame();const auto Ticks=D.Ticks();
    Check(!D.SetOption(2) && D.GetOption()==1 && D.Ticks()==Ticks && SameFrame(Before,D.GetFrame()),"invalid driver mode leaves the current session and frame intact");
    D.Restart();auto Fresh=Practice();Fresh.Render(F);
    Check(D.GetOption()==1 && !D.IsPaused() && D.Ticks()==0 && SameFrame(D.GetFrame(),F),"driver Restart retains practice but clears this session");
    Check(D.SetOption(0) && D.GetOption()==0 && D.GetFrame().Height==600 && D.GetFrame().Commands.size()==6,"native mode switch can return to unchanged match presentation");
}
void RealOpeningLoop() {
    auto G=Practice();G.Reset(730);int Steps=0,PlayerReturns=0;
    // A simple pupil policy follows the ball with the existing analog input.
    // No state is injected after Reset and no frame is rendered per simulation step.
    for(;Steps<1200 && G.S.Rally<2;++Steps) {
        const auto Before=G.S;Input I;I.AxisY=Clamp((Before.BallY-(Before.PlayerY+70))/8,-1,1);G.Step(I);
        if(Before.ServeFrames==0 && Before.BallVX<0 && G.S.BallVX>0) ++PlayerReturns;
    }
    Check(PlayerReturns>=2 && G.S.Rally>=2 && Steps<=1200,"ordinary tracking input reaches two consecutive player returns from a real practice Reset");
    Check(G.GetOption()==1 && G.S.BestRally>=2 && G.S.PlayerScore==0 && G.S.ComputerScore==0
        && !G.GetStatus().Over && !G.GetStatus().Won,"real rally loop keeps its best without match scoring or an artificial ending");
}
}
int main() {
    Modes();CountdownAndMovement();ContactsAndSpin();WallAndRetry();Presentation();DriverModeChange();RealOpeningLoop();
    std::cout<<"Pong practice: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
