// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
using Dodge=DodgeBallGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
Input Guard(bool Fire=false) {Input I;I.Dash=true;I.Fire=Fire;return I;}
Dodge Incoming(double Distance=10,bool Super=false,bool Air=false) {
    Dodge G;G.Reset(730);G.StartMatch();for(auto& P:G.Data.Players) P.HasBall=false;
    auto& P=G.Data.Players[1];if(Air) {P.Y=250;P.OnGround=false;P.JumpVelocity=0;}
    G.Data.DodgeBall={P.X+Distance+1,Air?P.Y+.6:P.Y,-1,0,-1,true,Super,Dodge::Countries[G.Data.OpponentCountry].Tint};return G;
}
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
void CatchAndHold() {
    for(bool Super:{false,true}) {
        auto G=Incoming(10,Super);G.Step(Guard());
        Check(G.Data.DodgeBall.Owner==1&&!G.Data.DodgeBall.InAir&&!G.Data.DodgeBall.PowerBall&&G.Data.Players[1].HasBall&&G.Data.Players[1].Health==3,"held guard catches a real incoming normal or super ball without damage");
        Check(G.Data.Players[1].ThrowCooldown==0&&!G.IsTeamPassInFlight(),"guard catch adds no cooldown or pass state");
        auto Plain=Incoming(10,Super);Plain.Step({});
        Check(Plain.Data.Players[1].Health==(Super?1:2)&&!Plain.Data.DodgeBall.InAir,"unguarded grounded input retains original normal and super damage");
        G=Incoming(10,Super);Input Press=Guard(true);Press.DashPressed=true;G.Step(Press);
        for(int N=0;N<32;++N) G.Step(Guard(true));
        Check(G.Data.DodgeBall.Owner==1&&G.Data.Players[1].HasBall&&G.Data.Players[1].Health==3&&G.Data.Players[1].ThrowCooldown==0&&!G.IsTeamPassInFlight(),"guard plus held Fire holds ownership beyond cooldown and never chains a pass");
        Input Release;Release.Fire=true;G.Step(Release);
        Check(G.Data.DodgeBall.Owner==-1&&G.Data.DodgeBall.InAir&&!G.Data.Players[1].HasBall&&G.Data.Players[1].ThrowCooldown==14,"releasing guard restores the existing held-Fire throw");
    }
    auto Legacy=Incoming(21);Input Fire;Fire.Fire=true;Legacy.Step(Fire);
    Check(Legacy.Data.DodgeBall.Owner==-1&&Legacy.Data.DodgeBall.InAir&&Legacy.Data.Players[1].ThrowCooldown==14&&Legacy.Data.Players[1].Health==3,"held Fire without guard still catches and immediately rethrows");
}
void CatchBoundaries() {
    struct Boundary {bool Super,Air;double Radius;};
    for(const auto B:std::array<Boundary,3>{{{false,false,22},{true,false,18},{false,true,34}}}) {
        auto G=Incoming(B.Radius,B.Super,B.Air);Check(G.HumanCatchRadius(1)==B.Radius,"existing displayed catch radius is unchanged");G.Step(Guard());
        Check(G.Data.DodgeBall.Owner==-1&&G.Data.DodgeBall.InAir&&G.Data.Players[1].Health==3,"exact normal super or airborne catch boundary stays excluded");
        G=Incoming(B.Radius-.001,B.Super,B.Air);G.Step(B.Air?Input{}:Guard());
        Check(G.Data.DodgeBall.Owner==1&&G.Data.Players[1].HasBall&&G.Data.Players[1].Health==3,"inside boundary catches and airborne still requires no guard input");
    }
    auto G=Incoming();G.Data.Players[1].Health=0;G.Step(Guard());
    Check(G.Data.DodgeBall.Owner==-1&&G.Data.DodgeBall.InAir&&!G.Data.Players[1].HasBall&&G.Data.Players[1].Health==0,"guard cannot catch for a knocked-out teammate");
}
void ExplicitFireParity() {
    for(bool Air:{false,true}) for(bool HeldFire:{false,true}) {
        auto G=Incoming();G.Step(Guard());
        auto& P=G.Data.Players[1];P.ThrowCooldown=HeldFire?1:0;
        if(Air) {P.OnGround=false;P.Y=292.6;P.JumpVelocity=-7.4;}
        auto Plain=G;Input Fresh=Guard(HeldFire);Fresh.FirePressed=true;Input Original=Fresh;Original.Dash=false;
        G.Step(Fresh);Plain.Step(Original);
        Check(Snapshot(G)==Snapshot(Plain),"fresh Fire disables guard for legacy self-catch and post-tick backup ordering on ground or in air");
        for(int N=0;N<3;++N) {G.Step({});Plain.Step({});}
        Check(Snapshot(G)==Snapshot(Plain),"explicit throw parity extends to subsequent catches and RNG-driven movement");
    }
}
void DeliberatePassAndPurity() {
    auto G=Incoming();Input Press=Guard(true);Press.DashPressed=true;G.Step(Press);
    Check(G.Data.DodgeBall.Owner==1&&!G.IsTeamPassInFlight(),"fresh pass press without prior possession guards the incoming ball instead");
    Input Moving=Guard(true);Moving.Right=Moving.Up=true;for(int N=0;N<4;++N) G.Step(Moving);
    Check(G.Data.DodgeBall.Owner==1&&G.Data.Players[1].X>180&&G.Data.Players[1].Y<300&&G.Data.Players[1].Charge==8,"guard retains the catch while the team moves and the holder charges");
    G.Step(Guard());Check(G.Data.DodgeBall.Owner==1&&!G.IsTeamPassInFlight(),"releasing Fire first preserves possession under guard");
    G.Step({});Press=Guard();Press.DashPressed=true;G.Step(Press);
    Check(G.IsTeamPassInFlight()&&G.HumanPassTarget()==2,"release and a new pass press deliberately launch to the next teammate");
    int Steps=0;while(G.IsTeamPassInFlight()&&Steps<90) {G.Step(Guard(true));++Steps;}
    Check(Steps<=90&&G.Data.DodgeBall.Owner==2&&!G.IsTeamPassInFlight()&&G.Data.Players[2].ThrowCooldown>=14,"guard through real teammate flight still reaches the dedicated automatic pass catch");
    for(int N=0;N<32;++N) G.Step(Guard(true));
    Check(G.Data.DodgeBall.Owner==2&&G.Data.Players[2].ThrowCooldown==0&&G.TeamHealth()==9&&!G.IsTeamPassInFlight(),"continued guard suppresses backup rethrow after pass cooldown without passing again");
    const auto Before=Snapshot(G);auto Quiet=G;Frame F,Again;G.Render(F);const auto Note=G.GetStatus().Note;
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();}
    Check(Snapshot(G)==Before&&SameFrame(F,Again)&&G.GetStatus().Note==Note,"guard-related presentation reads leave public possession and feedback state unchanged");
    for(int N=0;N<6;++N) {G.Step(Guard(true));Quiet.Step(Guard(true));}
    Check(Snapshot(G)==Snapshot(Quiet),"extra rendering preserves future hold behavior particles and RNG-driven CPU movement");
    G.Reset(730);G.Step(Guard());Check(G.Data.Mode==Dodge::Phase::Title&&!G.IsTeamPassInFlight(),"held guard does not open the title or preserve an old pass");
    Press=Guard();Press.DashPressed=true;G.Step(Press);G.Step(Guard());
    Check(G.Data.Mode==Dodge::Phase::CountrySelect,"fresh pass alias still opens country selection and held guard never confirms it");
}
void DriverBoundaries() {
    Driver D;Check(D.Select("dodge_ball",730),"Driver opens the existing Dodge engine");Dodge Expected;Expected.Reset(730);Frame F;
    D.SetInput(Guard());D.Advance(Driver::StepSeconds);Expected.Step(Guard());Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&Expected.Data.Mode==Dodge::Phase::Title,"held modifier alone remains inert at title during fixed-step catch-up");
    Input Confirm;Confirm.FirePressed=true;
    for(int N=0;N<3;++N) {const Input I=N==1?Input{}:Confirm;D.SetInput(I);D.Advance(Driver::StepSeconds);Expected.Step(I);}
    const auto Before=D.GetFrame();Input Queued=Guard(true);Queued.FirePressed=Queued.DashPressed=true;D.SetPaused(true);D.SetInput(Queued);
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Before,D.GetFrame()),"pause freezes queued guard throw and pass input");
    D.SetPaused(false);D.Advance(Driver::StepSeconds);Expected.Step({});Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&Expected.Data.DodgeBall.Owner==1,"unpause clears queued fresh actions instead of passing or throwing");
    D.SetInput(Guard(true));D.Advance(Driver::StepSeconds*8);for(int N=0;N<8;++N) Expected.Step(Guard(true));Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&Expected.Data.DodgeBall.Owner==1,"catch-up retains held guard and suppresses automatic Fire throws");
    Input Release;Release.Fire=true;D.SetInput(Release);D.Advance(Driver::StepSeconds);Expected.Step(Release);Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&Expected.Data.DodgeBall.Owner==-1,"modifier release reaches the next fixed step and restores legacy Fire");
    D.SetInput(Queued);D.Restart();Dodge Fresh;Fresh.Reset(730);Fresh.Render(F);
    Check(!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Restart clears old guard possession input and tournament state");
    D.Advance(Driver::StepSeconds*8);Check(SameFrame(D.GetFrame(),F),"restart discards stale fresh edges before title catch-up");
}
}
int main() {
    CatchAndHold();CatchBoundaries();ExplicitFireParity();DeliberatePassAndPurity();DriverBoundaries();
    std::cout<<"Dodge catch guard: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
