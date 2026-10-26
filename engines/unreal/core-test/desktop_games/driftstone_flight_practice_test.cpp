// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct DriftstoneTestAccess {
    static void Pose(DriftstoneGame& G,double X,double Y,double Vx=0,double Vy=0) {G.Player.X=X;G.Player.Y=Y;G.Player.Vx=Vx;G.Player.Vy=Vy;}
    static std::uint32_t NextRandom(const DriftstoneGame& G) {auto R=G.Rng;return R.Next();}
    static int UfoCountdown(const DriftstoneGame& G) {return G.UfoTimer;}
    static bool SameStars(const DriftstoneGame& A,const DriftstoneGame& B) {
        for(std::size_t N=0;N<A.Stars.size();++N) if(A.Stars[N].X!=B.Stars[N].X||A.Stars[N].Y!=B.Stars[N].Y||A.Stars[N].Speed!=B.Stars[N].Speed) return false;
        return true;
    }
    static bool OnlyStarDraws(const DriftstoneGame& G) {Random R;R.Seed(G.SessionSeed);for(std::size_t N=0;N<G.Stars.size()*3;++N) R.Next();return R.Next()==NextRandom(G);}
    static std::string Snapshot(const DriftstoneGame& G,bool Mode=true) {
        std::ostringstream O;O.precision(17);if(Mode) O<<G.Option<<' ';
        O<<G.GetDockedBeaconCount()<<' '<<G.SessionSeed<<' '<<G.Score<<' '<<G.Lives<<' '<<G.Level<<' '<<G.UfoTimer<<' '<<G.RespawnGrace<<' '<<G.Over<<' '<<G.Won;
        const auto& P=G.Player;O<<' '<<P.X<<' '<<P.Y<<' '<<P.Angle<<' '<<P.Vx<<' '<<P.Vy<<' '<<P.Thrust<<' '<<P.Cooldown<<' '<<P.Braking;
        O<<' '<<G.Rocks.size();for(const auto& R:G.Rocks) {O<<' '<<R.X<<' '<<R.Y<<' '<<R.Vx<<' '<<R.Vy<<' '<<R.Angle<<' '<<R.Rotation<<' '<<R.Size;for(double V:R.Shape) O<<' '<<V;}
        O<<' '<<G.Bullets.size();for(const auto& B:G.Bullets) O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Life<<' '<<B.PlayerOwned;
        O<<' '<<G.Ufos.size();for(const auto& U:G.Ufos) O<<' '<<U.X<<' '<<U.Y<<' '<<U.Vx<<' '<<U.ShootTimer;
        for(const auto& S:G.Stars) O<<' '<<S.X<<' '<<S.Y<<' '<<S.Speed;
        O<<' '<<NextRandom(G);return O.str();
    }
};
}}
namespace {
using Driftstone=DriftstoneGame;
using Access=DriftstoneTestAccess;
constexpr std::array<Vec,3> Beacons{{{400,180},{650,180},{100,420}}};
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
bool SameShip(const Driftstone::Ship& A,const Driftstone::Ship& B) {return A.X==B.X&&A.Y==B.Y&&A.Angle==B.Angle&&A.Vx==B.Vx&&A.Vy==B.Vy&&A.Thrust==B.Thrust&&A.Cooldown==B.Cooldown&&A.Braking==B.Braking;}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
Driftstone Practice(std::uint32_t Seed=730) {Driftstone G;G.SetOption(2,Seed);return G;}
Input Brake() {Input I;I.Action=true;return I;}
void ModesAndEmptySpace() {
    Driftstone Full,Voyage;Full.Reset(730);Voyage.SetOption(1,730);
    Check(Full.GetOption()==0&&Voyage.GetOption()==1&&Full.GetRockCount()==6&&Access::Snapshot(Full,false)==Access::Snapshot(Voyage,false),"Endless and Three waves retain the same seeded opening world");
    auto G=Practice();Check(G.GetOption()==2&&G.GetDockedBeaconCount()==0&&G.EntityCount()==0&&!G.IsFireReady()&&Access::SameStars(Full,G)&&Access::OnlyStarDraws(G),"flight practice preserves stars and skips only combat creation and its random draws");
    for(int N=0;N<4;++N) {Input I;I.Up=N<2;I.Right=N==1;I.Action=N==2;I.Fire=N<3;Full.Step(I);Voyage.Step(I);}
    Check(Access::Snapshot(Full,false)==Access::Snapshot(Voyage,false),"short affected Endless and voyage steps preserve the same physics combat and RNG");
    const auto Rng=Access::NextRandom(G);Input Noise=Brake();Noise.Up=Noise.Fire=true;
    for(int N=0;N<360;++N) {Noise.FirePressed=N%7==0;G.Step(Noise);}
    Check(G.GetDockedBeaconCount()==0&&G.EntityCount()==0&&G.GetRockCount()==0&&G.GetUfoCount()==0&&!G.IsFireReady()&&Access::UfoCountdown(G)==300&&Access::NextRandom(G)==Rng,"more than a UFO interval of held and fresh fire cannot create combat or advance its timer and RNG");
    Check(G.GetStatus().Score==0&&G.GetStatus().Lives==3&&G.GetLevel()==1&&!G.GetStatus().Won&&!G.GetStatus().Over&&G.GetShip().X==400&&G.GetShip().Y==300,"braking outside a beacon leaves an endless quiet practice space without penalties");
}
bool PublicRoute(std::array<Driftstone,3>& Stages,Driftstone& Complete) {
    auto G=Practice();Stages[0]=G;int Total=0;bool Physics=true,Quiet=true;
    for(int Stage=0;Stage<3;++Stage) {
        bool Stopping=false;int Steps=0;
        while(G.GetDockedBeaconCount()==Stage&&Steps<800) {
            const auto S=G.GetShip();const auto Goal=Beacons[static_cast<std::size_t>(Stage)];
            const double Dx=Goal.X-S.X,Dy=Goal.Y-S.Y,DistanceToGoal=std::hypot(Dx,Dy),Speed=std::hypot(S.Vx,S.Vy);
            const double Error=std::remainder(std::atan2(Dy,Dx)*180/shooter_detail::Pi-S.Angle,360.0);
            if(Stopping&&S.Vx==0&&S.Vy==0) Stopping=false;
            if(DistanceToGoal<=20+4*Speed) Stopping=true;
            Input I;I.AxisX=Clamp(Error/6,-1,1);I.Action=Stopping||std::abs(Error)>4;I.Up=!I.Action&&Speed<3;I.Fire=true;
            auto Expected=S;Expected.Update(I);G.Step(I);Physics=Physics&&SameShip(Expected,G.GetShip());
            Quiet=Quiet&&G.EntityCount()==0&&G.GetStatus().Score==0&&G.GetStatus().Lives==3&&G.GetLevel()==1;++Steps;++Total;
        }
        Check(G.GetDockedBeaconCount()==Stage+1&&Steps<=800,"bounded real turn thrust and brake inputs dock exactly the next beacon");
        if(G.GetDockedBeaconCount()!=Stage+1) {std::cerr<<"route stopped at beacon "<<Stage<<" ship "<<G.GetShip().X<<','<<G.GetShip().Y<<'\n';return false;}
        Check(G.GetShip().Braking&&G.GetShip().Vx==0&&G.GetShip().Vy==0,"real arrival reaches full stationary braking before progressing");
        if(Stage<2) Stages[static_cast<std::size_t>(Stage+1)]=G;
    }
    Check(Physics&&Quiet&&G.GetStatus().Won&&!G.GetStatus().Over&&Total<=2400,"public route retains exact Ship.Update and completes all three docks without combat rewards or damage");
    std::cout<<"Flight practice public route: "<<Total<<" steps\n";Complete=G;return G.GetStatus().Won;
}
void LocalQualification(const std::array<Driftstone,3>& Stages) {
    for(std::size_t Stage=0;Stage<Stages.size();++Stage) {
        auto G=Stages[Stage];const auto Wrong=Beacons[(Stage+1)%Beacons.size()];Access::Pose(G,Wrong.X,Wrong.Y);G.Step(Brake());
        Check(G.GetDockedBeaconCount()==static_cast<int>(Stage),"stationary braking at another beacon never skips the active order");
        G=Stages[Stage];const auto Goal=Beacons[Stage];Access::Pose(G,Goal.X+27.999,Goal.Y);Input Stop=Brake();if(Stage==0) {Stop.Action=false;Stop.ActionPressed=true;}G.Step(Stop);
        Check(G.GetDockedBeaconCount()==static_cast<int>(Stage)+1&&G.GetShip().X==Goal.X+27.999&&G.GetShip().Y==Goal.Y,"qualifying held or tapped brake advances one goal without teleporting the ship");
    }
    auto G=Stages[1];const auto Goal=Beacons[1];Access::Pose(G,Goal.X+28,Goal.Y);G.Step(Brake());Check(G.GetDockedBeaconCount()==1,"exact twenty-eight pixel radius is excluded");
    G=Stages[1];Access::Pose(G,Goal.X,Goal.Y);G.Step({});Check(G.GetDockedBeaconCount()==1&&!G.GetShip().Braking,"stationary proximity alone does not dock without braking");
    for(bool Vertical:{false,true}) {G=Stages[1];Access::Pose(G,Goal.X,Goal.Y,Vertical?0:.03,Vertical?.03:0);G.Step(Brake());Check(G.GetDockedBeaconCount()==1&&G.GetShip().Braking,"each velocity component must actually reach zero to dock");}
    G=Stages[0];Access::Pose(G,799,300,4,0);auto Expected=G.GetShip();Expected.Update({});G.Step({});Check(G.GetShip().X==0&&SameShip(G.GetShip(),Expected)&&G.GetDockedBeaconCount()==0,"practice preserves ordinary wrap with discarded overshoot on a missed approach");
    G=Stages[1];const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);
    for(int Value:{-1,3}) Check(!G.SetOption(Value,99)&&Access::Snapshot(G)==Before,"invalid modes preserve docked progress seed and the active ship");
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();G.GetDockedBeaconCount();}
    Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"practice rendering and progress reads preserve the complete game and RNG state");
    G.Reset(99);Check(G.GetOption()==2&&Access::Snapshot(G)==Access::Snapshot(Practice(99)),"Reset keeps practice but clears all previous docking progress");
}
void FinalAndDriver(const Driftstone& Complete) {
    auto G=Complete;const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);Input Held;Held.Up=Held.Right=Held.Fire=Held.Action=true;Held.FirePressed=Held.ActionPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);
    G.Render(Again);Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"completed practice freezes turning thrust brake fire and all feedback state");
    Check(G.SourceControllerButton(0)&&G.GetOption()==2&&Access::Snapshot(G)==Access::Snapshot(Practice()),"fresh controller retry keeps practice and resets the original seeded route");
    G=Complete;Check(G.SourceKeyDown(7)&&Access::Snapshot(G)==Access::Snapshot(Practice()),"fresh Space retry restores the same clean practice opening");
    Driver D;Check(D.Select("driftstone",730),"Driver opens the existing Driftstone engine");D.Advance(Driver::StepSeconds*2.5);Input Stale;Stale.Up=Stale.Fire=Stale.FirePressed=Stale.Action=true;D.SetInput(Stale);
    Check(D.SetOption(2)&&D.GetOption()==2&&D.Ticks()==0&&D.GetSeed()==730&&D.Advance(Driver::StepSeconds*.5)==0,"practice selection clears partial time and keeps seed");
    auto Expected=Practice();Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first practice step contains no stale thrust fire or brake");
    D.SetPaused(true);D.SetInput(Stale);const auto Paused=D.GetFrame();Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Paused,D.GetFrame()),"Driver pause freezes practice");
    D.Restart();Expected=Practice();Expected.Render(F);Check(D.GetOption()==2&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart retains flight practice and restores the first goal");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"restart clears queued paused inputs");
}
}
int main() {
    ModesAndEmptySpace();std::array<Driftstone,3> Stages;Driftstone Complete;
    if(PublicRoute(Stages,Complete)) {LocalQualification(Stages);FinalAndDriver(Complete);}
    std::cout<<"Driftstone flight practice: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
