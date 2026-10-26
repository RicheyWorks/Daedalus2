// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
using Dodge=DodgeBallGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
Input Pass() {Input I;I.DashPressed=true;return I;}
Dodge Match() {Dodge G;G.Reset(730);G.StartMatch();return G;}
std::string Snapshot(const Dodge& G) {
    const auto& D=G.Data;std::ostringstream O;O.precision(17);
    const auto ColorOut=[&](Color C){O<<' '<<static_cast<int>(C.R)<<' '<<static_cast<int>(C.G)<<' '<<static_cast<int>(C.B)<<' '<<static_cast<int>(C.A);};
    O<<D.SelectedCountry<<' '<<D.OpponentCountry<<' '<<D.HumanScore<<' '<<D.CpuScore<<' '<<D.Round<<' '<<static_cast<int>(D.Mode)<<' '<<G.IsTeamPassInFlight()<<' '<<G.HumanPassTarget();
    for(const auto& P:D.Players) O<<' '<<P.X<<' '<<P.Y<<' '<<P.BaseY<<' '<<P.Speed<<' '<<P.Power<<' '<<P.JumpVelocity
        <<' '<<P.CountryIndex<<' '<<P.Health<<' '<<P.ThrowCooldown<<' '<<P.JumpCooldown<<' '<<P.Charge<<' '<<P.SuperType
        <<' '<<P.Cpu<<' '<<P.HasBall<<' '<<P.FacingRight<<' '<<P.OnGround<<' '<<P.JumpWasDown;
    const auto& B=D.DodgeBall;O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Owner<<' '<<B.InAir<<' '<<B.PowerBall;ColorOut(B.ThrowColor);
    O<<' '<<D.Particles.size();for(const auto& P:D.Particles) {O<<' '<<P.X<<' '<<P.Y<<' '<<P.Vx<<' '<<P.Vy<<' '<<P.Size<<' '<<P.Life;ColorOut(P.Tint);}return O.str();
}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
bool Receive(Dodge& G,int Receiver,bool HoldFire=false) {
    Input I;I.Fire=HoldFire;int Steps=0;
    while(G.IsTeamPassInFlight()&&Steps<90) {G.Step(I);++Steps;}
    const bool Caught=G.Data.DodgeBall.Owner==Receiver&&!G.Data.DodgeBall.InAir&&G.Data.Players[static_cast<std::size_t>(Receiver)].HasBall;
    Check(Caught&&Steps<=90&&!G.IsTeamPassInFlight(),"intended teammate automatically catches within bounded real flight");
    Check(Caught&&G.Data.Players[static_cast<std::size_t>(Receiver)].ThrowCooldown>=14,"receiver settles with a post-tick cooldown even under held Fire");return Caught;
}
void FullCycle() {
    auto G=Match();G.Data.Players[1].Charge=60;int Owner=1;
    for(int Receiver:{2,0,1}) {
        Check(G.HumanPassTarget()==Receiver&&!G.IsTeamPassInFlight(),"next living teammate follows the P2 P3 P1 P2 cycle");
        const auto Sender=G.Data.Players[static_cast<std::size_t>(Owner)];const auto Target=G.Data.Players[static_cast<std::size_t>(Receiver)];
        const double X=Sender.X+20,Y=Sender.Y-5,Dx=Target.X-X,Dy=Target.Y-Y,Length=std::hypot(Dx,Dy),Speed=8.5*Sender.Power;
        G.Step(Pass());const auto B=G.Data.DodgeBall;
        Check(G.IsTeamPassInFlight()&&G.HumanPassTarget()==Receiver&&B.Owner==-1&&B.InAir&&!B.PowerBall&&G.Data.Players[static_cast<std::size_t>(Owner)].Charge==0,"fresh pass launches a normal uncharged teammate flight");
        Check(Close(B.X,X+Dx/Length*Speed)&&Close(B.Y,Y+Dy/Length*Speed)&&Close(B.Vx,Dx/Length*Speed*.985)&&Close(B.Vy,Dy/Length*Speed*.985),"pass attaches the stale owned ball to the hand and uses existing normal throw and drag");
        if(Owner==1) {
            const auto Before=G.Data.DodgeBall;const double OldX=G.Data.Players[2].X;Input Move;Move.PadRight=true;G.Step(Move);
            Check(Close(G.Data.DodgeBall.X,Before.X+Before.Vx)&&Close(G.Data.DodgeBall.Y,Before.Y+Before.Vy)&&Close(G.Data.Players[2].X,OldX+G.Data.Players[2].Speed),"teammate movement leaves the pass on its original straight flight");
        }
        if(!Receive(G,Receiver,Owner==1)) return;
        Input Held;Held.Fire=true;G.Step(Held);Check(G.Data.DodgeBall.Owner==Receiver&&!G.Data.DodgeBall.InAir,"held Fire cannot immediately rethrow the received pass");
        int Wait=0;while(G.Data.Players[static_cast<std::size_t>(Receiver)].ThrowCooldown>0&&Wait<20) {G.Step({});++Wait;}
        Check(Wait<20&&G.Data.DodgeBall.Owner==Receiver&&G.TeamHealth()==9&&G.Data.HumanScore==0&&G.Data.CpuScore==0,"cooldown wait preserves all teammates and match progress");Owner=Receiver;
    }
}
void Refused(Dodge G,const std::string& Why) {
    auto Plain=G;G.Step(Pass());Plain.Step({});Check(Snapshot(G)==Snapshot(Plain),Why);
    for(int N=0;N<3;++N) {G.Step({});Plain.Step({});}
    Check(Snapshot(G)==Snapshot(Plain),"refused pass retains ordinary future simulation and RNG-driven CPU movement");
}
void EligibilityAndPriority() {
    auto G=Match();G.Data.Players[2].Health=0;Check(G.HumanPassTarget()==0,"target selection skips the knocked-out next teammate");G.Step(Pass());Receive(G,0);
    G=Match();G.Data.Players[0].Health=G.Data.Players[2].Health=0;Check(G.HumanPassTarget()==-1,"sole survivor has no pass recipient");Refused(G,"sole survivor refusal changes only the ordinary fixed step");
    G=Match();G.Data.Players[1].ThrowCooldown=3;Check(G.HumanPassTarget()==2,"cooldown still exposes the next living target");Refused(G,"cooldown refusal preserves ball and possession apart from ordinary timers");
    G=Match();G.Data.Players[1].HasBall=false;Refused(G,"owner without possession cannot pass");
    G=Match();G.Data.Players[1].Health=0;Refused(G,"knocked-out holder cannot pass");
    G=Match();G.Data.Players[1].HasBall=false;G.Data.DodgeBall.Owner=-1;Refused(G,"loose ball cannot pass");
    G=Match();G.Data.Players[1].HasBall=false;G.Data.DodgeBall.Owner=3;G.Data.Players[3].HasBall=true;Refused(G,"CPU possession cannot pass");
    G=Match();G.Data.DodgeBall.Owner=6;Refused(G,"out-of-range possession cannot pass");
    G=Match();G.Data.Players[1].HasBall=false;G.Data.DodgeBall={300,100,4,0,-1,true,false,White};Refused(G,"ordinary airborne ball cannot pass");
    G=Match();G.Data.Players[1].OnGround=false;G.Data.Players[1].Y=292.6;G.Data.Players[1].JumpVelocity=-7.4;G.Step(Pass());
    Check(G.IsTeamPassInFlight()&&!G.Data.Players[1].OnGround,"valid jumping holder can pass without adding a grounded restriction");
    G=Match();auto PassOnly=G;Input Both=Pass();Both.FirePressed=true;G.Step(Both);PassOnly.Step(Pass());
    Check(G.IsTeamPassInFlight()&&Snapshot(G)==Snapshot(PassOnly),"successful pass wins a simultaneous fresh ordinary throw without extra effects");
    G=Match();G.Data.Players[0].Health=G.Data.Players[2].Health=0;Dodge::UpdateBall(G.Data.DodgeBall,G.Data.Players);G.Step(Both);
    Check(G.Data.DodgeBall.InAir&&G.Data.DodgeBall.Owner==-1&&!G.IsTeamPassInFlight(),"refused pass preserves simultaneous ordinary FirePressed fallback");
    G=Match();G.Data.Players[2].X=200;G.Data.Players[2].Y=G.Data.Players[2].BaseY=295;G.Data.Players[1].Charge=60;
    Refused(G,"zero hand-to-target direction refuses before committing ball or charge changes");
    auto FireOnly=G;Input Fire;Fire.FirePressed=true;G.Step(Both);FireOnly.Step(Fire);
    Check(Snapshot(G)==Snapshot(FireOnly)&&!G.IsTeamPassInFlight(),"zero-direction refusal retains the ordinary simultaneous Fire fallback");
}
void SafetyAndRecovery() {
    auto G=Match();G.Step(Pass());auto& B=G.Data.DodgeBall;B.X=G.Data.Players[0].X-4;B.Y=G.Data.Players[0].Y;B.Vx=4;B.Vy=0;Input Held;Held.Fire=true;G.Step(Held);
    Check(G.IsTeamPassInFlight()&&B.InAir&&B.Owner==-1&&G.Data.Players[0].Health==3&&!G.Data.Players[0].HasBall,"unselected human cannot catch or take friendly damage from an active pass");
    G=Match();G.Step(Pass());G.Data.Players[2].Health=0;
    Check(G.IsTeamPassInFlight()&&G.HumanPassTarget()==-1,"knocked-out recipient hides its target while flight safety remains active");
    auto& Miss=G.Data.DodgeBall;Miss.X=G.Data.Players[0].X-4;Miss.Y=G.Data.Players[0].Y;Miss.Vx=4;Miss.Vy=0;G.Step({});
    Check(G.IsTeamPassInFlight()&&G.HumanPassTarget()==-1&&G.Data.Players[0].Health==3&&Miss.InAir,"unavailable recipient cannot turn an ongoing pass into friendly damage");
    Miss.X=250;Miss.Y=300;Miss.Vx=.1;Miss.Vy=0;G.Step({});
    Check(!G.IsTeamPassInFlight()&&!Miss.InAir&&Miss.Owner==-1&&G.Data.Players[0].Health==3&&G.Data.Players[1].Health==3,"missed pass clears safety only when unchanged ball physics settles it");
    Miss.X=G.Data.Players[0].X+1;Miss.Y=G.Data.Players[0].Y;G.Step({});Check(Miss.Owner==0&&G.Data.Players[0].HasBall&&!G.IsTeamPassInFlight(),"settled pass returns to the ordinary loose pickup loop");
    G=Match();G.Data.Players[1].HasBall=false;G.Data.DodgeBall={G.Data.Players[0].X-4,G.Data.Players[0].Y,4,0,-1,true,false,White};G.Step({});
    Check(G.Data.Players[0].Health==2&&!G.Data.DodgeBall.InAir&&!G.IsTeamPassInFlight(),"ordinary attack flight retains existing friendly damage");
    G=Match();G.Step(Pass());G.Data.Players[4].Health=G.Data.Players[5].Health=0;int Steps=0;
    while(G.IsTeamPassInFlight()&&Steps<64) {
        auto& Cpu=G.Data.Players[3];Cpu.ThrowCooldown=100;auto& Flight=G.Data.DodgeBall;Flight.X=Cpu.X-22;Flight.Y=Cpu.Y;Flight.Vx=2;Flight.Vy=0;G.Step({});++Steps;
    }
    Check(Steps<=64&&G.Data.DodgeBall.Owner==3&&G.Data.Players[3].HasBall&&!G.IsTeamPassInFlight()&&G.Data.Players[3].Health==3,"normal CPU catch can intercept a pass and clears its safety tag");
    G=Match();int Attempts=0;
    while(G.Data.HumanScore==0&&Attempts<8) {
        G.StartMatch();G.Step(Pass());G.Data.Players[4].Health=G.Data.Players[5].Health=0;auto& Cpu=G.Data.Players[3];Cpu.Health=1;Cpu.ThrowCooldown=100;
        auto& Flight=G.Data.DodgeBall;Flight.X=Cpu.X-4;Flight.Y=Cpu.Y;Flight.Vx=4;Flight.Vy=0;G.Step({});++Attempts;
    }
    Check(G.Data.HumanScore==1&&G.Data.Mode==Dodge::Phase::Won&&G.Data.Players[3].Health==0&&!G.IsTeamPassInFlight(),"pass safety still permits an uncaught ball to defeat an opponent through normal Hit");
    G=Match();G.Step(Pass());G.StartMatch();Check(!G.IsTeamPassInFlight()&&G.Data.DodgeBall.Owner==1,"StartMatch clears the old pass before initializing the next round");G.Step(Pass());G.Reset(730);
    Check(!G.IsTeamPassInFlight()&&G.HumanPassTarget()==-1&&G.Data.Mode==Dodge::Phase::Title,"Reset clears all pass state");
}
void TransitionsAndPurity() {
    Dodge G;G.Reset(730);G.Step(Pass());Check(G.Data.Mode==Dodge::Phase::CountrySelect&&!G.IsTeamPassInFlight(),"fresh pass alias still opens the existing country picker from title");
    G.Step(Pass());Check(G.Data.Mode==Dodge::Phase::CountrySelect,"pass alone does not confirm a country");Input Both=Pass();Both.FirePressed=true;G.Step(Both);
    Check(G.Data.Mode==Dodge::Phase::Playing&&G.Data.DodgeBall.Owner==1&&!G.IsTeamPassInFlight(),"country confirmation cannot fall through into a first-frame pass");
    G.Data.Mode=Dodge::Phase::Won;G.Data.Round=1;G.Step(Pass());Check(G.Data.Round==2&&G.Data.DodgeBall.Owner==1&&!G.IsTeamPassInFlight(),"result continuation starts a round without accidentally passing");
    G=Match();Input Held;Held.Dash=true;G.Step(Held);Check(G.Data.DodgeBall.Owner==1&&!G.IsTeamPassInFlight(),"held Dash alone is not a pass action");
    G.Step(Pass());auto Quiet=G;const auto Before=Snapshot(G);Frame F,Again;G.Render(F);const auto Note=G.GetStatus().Note;
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();G.HumanPassTarget();G.IsTeamPassInFlight();}
    Check(Snapshot(G)==Before&&SameFrame(F,Again)&&G.GetStatus().Note==Note&&Note.find("PASS -> P3")!=std::string::npos,"derived pass cues are readable and preserve active flight state");
    for(int N=0;N<12;++N) {G.Step({});Quiet.Step({});}
    Check(Snapshot(G)==Snapshot(Quiet),"extra pass presentation reads preserve future catches particles and RNG-driven CPU movement");
}
void DriverEdges() {
    Driver D;Check(D.Select("dodge_ball",730),"Driver opens the existing Dodge engine");Dodge Expected;Expected.Reset(730);Input Confirm;Confirm.FirePressed=true;
    for(int N=0;N<3;++N) {const Input I=N==1?Input{}:Confirm;D.SetInput(I);D.Advance(Driver::StepSeconds);Expected.Step(I);}
    Frame F;Expected.Render(F);const auto Before=D.GetFrame();D.SetPaused(true);D.SetInput(Pass());
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Before,D.GetFrame()),"pause holds a queued fresh pass without changing the court");
    D.SetPaused(false);D.Advance(Driver::StepSeconds);Expected.Step({});Expected.Render(F);Check(SameFrame(D.GetFrame(),F)&&Expected.Data.DodgeBall.Owner==1,"unpause clears the paused pass edge");
    Input Press=Pass();Press.Dash=true;D.SetInput(Press);
    for(int Chunk=0;Chunk<4;++Chunk) {D.Advance(Driver::StepSeconds*8);for(int N=0;N<8;++N) {Input I;I.Dash=true;if(Chunk==0&&N==0) I.DashPressed=true;Expected.Step(I);}}
    Expected.Render(F);Check(SameFrame(D.GetFrame(),F)&&Expected.Data.DodgeBall.Owner==2&&!Expected.IsTeamPassInFlight(),"catch-up consumes one fresh pass edge and held Dash cannot restart it after receiver cooldown");
}
}
int main() {
    FullCycle();EligibilityAndPriority();SafetyAndRecovery();TransitionsAndPurity();DriverEdges();
    std::cout<<"Dodge team pass: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
