// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static const std::vector<ContraBullet>& Shots(const ContraGame& G) {return G.Bullets;}
    static void ShotAt(ContraGame& G,double X,double Y,int Life=60,bool Twice=false) {
        G.Bullets={{X-12,Y,12,0,Life}};if(Twice) G.Bullets.push_back({X-11,Y,12,0,Life});
    }
    static std::uint32_t NextRandom(const ContraGame& G) {auto R=G.Rng;return R.Next();}
    static std::string PlayerCode(const ContraPlayer& P) {
        std::ostringstream O;O.precision(17);O<<P.X<<' '<<P.Y<<' '<<P.VY<<' '<<P.FacingRight<<' '<<P.OnGround<<' '<<P.Crouching<<' '<<P.Lives<<' '<<P.Cooldown
            <<' '<<P.FireRate<<' '<<P.SpreadTimer<<' '<<P.Invincible<<' '<<P.Score<<' '<<P.Spread<<' '<<P.GroundGraceFrames;return O.str();
    }
    static std::string Snapshot(const ContraGame& G) {
        std::ostringstream O;O.precision(17);O<<G.Option<<' '<<G.RangeStage<<' '<<G.SessionSeed<<' '<<G.CameraX<<' '<<G.Progress<<' '<<G.Over<<' '<<G.Won<<' '<<G.FinalBossSpawned<<' '<<G.AtTitle<<' '<<G.NamedKeyInput<<' '<<G.CheatIndex<<' '<<PlayerCode(G.Player);
        const auto Bullets=[&](const std::vector<ContraBullet>& V){O<<' '<<V.size();for(const auto& B:V) O<<' '<<B.X<<' '<<B.Y<<' '<<B.VX<<' '<<B.VY<<' '<<B.Life;};Bullets(G.Bullets);Bullets(G.EnemyBullets);
        O<<' '<<G.Enemies.size();for(const auto& E:G.Enemies) O<<' '<<E.X<<' '<<E.Y<<' '<<E.VX<<' '<<E.Health<<' '<<E.ShootTimer<<' '<<E.Kind;
        O<<' '<<G.Powerups.size();for(const auto& P:G.Powerups) O<<' '<<P.X<<' '<<P.Y<<' '<<P.Bob<<' '<<P.Rapid;
        O<<' '<<G.Particles.size();for(const auto& P:G.Particles) O<<' '<<P.X<<' '<<P.Y<<' '<<P.VX<<' '<<P.VY<<' '<<P.Life<<' '<<static_cast<int>(P.Tint.R)<<' '<<static_cast<int>(P.Tint.G)<<' '<<static_cast<int>(P.Tint.B)<<' '<<static_cast<int>(P.Tint.A);
        const auto& I=G.Previous;O<<' '<<I.Left<<' '<<I.Right<<' '<<I.Up<<' '<<I.Down<<' '<<I.PadLeft<<' '<<I.PadRight<<' '<<I.PadUp<<' '<<I.PadDown<<' '<<I.AxisX<<' '<<I.AxisY<<' '<<I.Fire<<' '<<I.Jump<<' '<<I.Action<<' '<<I.Dash<<' '<<I.FirePressed<<' '<<I.JumpPressed<<' '<<I.ActionPressed<<' '<<I.DashPressed;
        auto C=G.CosmeticRng;O<<' '<<NextRandom(G)<<' '<<C.Next();return O.str();
    }
};
}}}
namespace {
using Contra=ContraGame;
using Access=platformers::TestAccess;
constexpr std::array<Rect,3> Targets{{{340,485,24,20},{620,340,24,40},{970,503,24,15}}};
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
bool SameShots(const std::vector<platformers::ContraBullet>& A,const std::vector<platformers::ContraBullet>& B) {
    if(A.size()!=B.size()) return false;
    for(std::size_t N=0;N<A.size();++N) if(A[N].X!=B[N].X||A[N].Y!=B[N].Y||A[N].VX!=B[N].VX||A[N].VY!=B[N].VY||A[N].Life!=B[N].Life) return false;return true;
}
Contra Range(std::uint32_t Seed=730) {Contra G;G.SetOption(1,Seed);return G;}
void ModesAndPhysics() {
    Contra Full;Full.Reset(730);Check(Full.GetOption()==0&&Full.EnemyCount()==2,"Full run remains default with its original two enemies");
    auto G=Range();Random R;R.Seed(730);Check(G.GetOption()==1&&!G.IsAtTitle()&&G.GetRangeHits()==0&&G.EnemyCount()==0&&G.BulletCount()==0&&G.GetStatus().Score==0&&G.GetStatus().Lives==3&&Access::NextRandom(G)==R.Next(),"explicit range selection starts active with normal player state and no spawn draws");
    G.SetOption(0,730);Check(Access::Snapshot(G)==Access::Snapshot(Full),"returning to Full run restores its complete original seeded state");
    for(int N=0;N<4;++N) {Input I;I.Right=N<2;I.Fire=N<3;G.Step(I);Full.Step(I);}Check(Access::Snapshot(G)==Access::Snapshot(Full),"short full-run companion retains combat physics and RNG");
    G=Range();auto Player=G.GetPlayer();std::vector<platformers::ContraBullet> Bullets;double Camera=0;
    for(int N=0;N<12;++N) {
        Input I;I.Right=N<4;I.Jump=I.JumpPressed=N==4;I.Down=N>=8;I.Fire=true;I.FirePressed=N==0;
        if(I.FirePressed) Player.Shoot(Bullets);
        Player.Update(I,platformers::ContraPlatforms(),Camera);if(I.Fire||I.FirePressed) Player.Shoot(Bullets);
        Camera=Camera*.85+std::max(0.0,Player.X-350)*.15;for(auto& B:Bullets) B.Update();
        Bullets.erase(std::remove_if(Bullets.begin(),Bullets.end(),[&](const auto& B){return B.Life<=0||B.X>Camera+900||B.X<Camera-100;}),Bullets.end());G.Step(I);
        Check(G.GetRangeHits()==0&&Access::PlayerCode(G.GetPlayer())==Access::PlayerCode(Player)&&SameShots(Access::Shots(G),Bullets)&&G.GetCameraX()==Camera,"range reuses exact player shoot update camera and projectile expiry order");
    }
    G=Range();const auto Before=Access::NextRandom(G);Input Walk;Walk.Right=true;for(int N=0;N<600;++N) G.Step(Walk);
    Check(G.GetPlayer().X>Contra::FinishX&&!G.GetStatus().Over&&!G.GetStatus().Won&&G.GetRangeHits()==0&&G.EnemyCount()==0&&G.BulletCount()==0&&G.GetStatus().Lives==3&&G.GetStatus().Score==0&&Access::NextRandom(G)==Before,"long safe range movement neither spawns threats nor uses the full-run distance victory");
}
bool PublicRoute(std::array<Contra,3>& Stages,Contra& Complete) {
    auto G=Range();Stages[0]=G;int Steps=0;const auto Step=[&](const Input& I){G.Step(I);++Steps;};Input Fire;Fire.Fire=true;
    Step(Fire);Check(Access::Shots(G).size()==1&&Access::Shots(G)[0].Y==496&&G.GetPlayer().Cooldown==8,"standing held shot retains its original height and eight-step cooldown");
    for(int N=1;N<40&&G.GetRangeHits()==0;++N) Step(Fire);
    Check(G.GetRangeHits()==1&&G.GetPlayer().OnGround&&!G.GetPlayer().Crouching,"standing held fire hits the first panel through real bullet flight");if(G.GetRangeHits()!=1) return false;Stages[1]=G;
    Input Right;Right.Right=true;for(int N=0;N<80&&G.GetPlayer().X<450;++N) Step(Right);
    Check(G.GetPlayer().X==450&&G.GetPlayer().OnGround,"ordinary movement reaches the high-shot launch position");
    Input Jump=Fire;Jump.Jump=true;Step(Jump);for(int N=0;N<60&&G.GetRangeHits()==1;++N) Step(Fire);
    Check(G.GetRangeHits()==2&&!G.GetPlayer().OnGround,"one real ground jump and original fire cadence hit the high panel");if(G.GetRangeHits()!=2) return false;Stages[2]=G;
    Input LowMove=Right;LowMove.Down=true;for(int N=0;N<80&&G.GetPlayer().X<800;++N) Step(LowMove);
    Check(G.GetPlayer().X==800&&G.GetPlayer().OnGround&&G.GetPlayer().Crouching,"crouched movement reaches the final firing position without shooting ahead");
    Input LowFire=Fire;LowFire.Down=true;Step(LowFire);Check(Access::Shots(G).size()==1&&Access::Shots(G)[0].Y==512&&G.GetPlayer().Cooldown==8,"crouched held shot retains its original low muzzle height and cooldown");
    for(int N=1;N<40&&!G.GetStatus().Over;++N) Step(LowFire);
    Check(G.GetRangeHits()==3&&G.GetStatus().Won&&G.GetStatus().Over&&G.GetStatus().Score==0&&G.GetStatus().Lives==3&&Steps<=303,"public standing jumping and crouching shots complete all targets without score or damage changes");
    std::cout<<"Contra range public route: "<<Steps<<" steps\n";Complete=G;return G.GetStatus().Won;
}
void BoundariesAndPurity(const std::array<Contra,3>& Stages) {
    for(std::size_t N=0;N<Stages.size();++N) {
        auto G=Stages[N];const auto T=Targets[N];Access::ShotAt(G,T.X+2,T.Y+2,60,true);G.Step({});
        Check(G.GetRangeHits()==static_cast<int>(N)+1&&Access::Shots(G).size()==1&&Access::Shots(G)[0].X==T.X+3&&G.GetStatus().Score==0,"active target consumes exactly one real updated bullet per step");
    }
    auto G=Stages[0];Access::ShotAt(G,Targets[1].X+2,Targets[1].Y+2);G.Step({});Check(G.GetRangeHits()==0&&G.BulletCount()==1,"future target cannot accept a shot out of order");
    struct Point {double X,Y;bool Hit;};
    for(const auto P:std::array<Point,5>{{{339.999,490,false},{340,490,true},{364,490,false},{350,505,false},{363.999,504.999,true}}}) {
        G=Stages[0];Access::ShotAt(G,P.X,P.Y);G.Step({});Check(G.GetRangeHits()==(P.Hit?1:0),"target containment retains original quantized lower and exclusive upper pixel bounds");
    }
    G=Stages[0];Access::ShotAt(G,350,490,1);G.Step({});Check(G.GetRangeHits()==0&&G.BulletCount()==0,"expired bullet is removed before target qualification");
    G=Stages[1];const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);for(int Value:{-1,2}) Check(!G.SetOption(Value,99)&&Access::Snapshot(G)==Before,"invalid mode refuses before mutating the active range");
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();G.GetRangeHits();}Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"render and progress getters preserve the whole range and both RNG streams");
    G.Reset(99);Check(G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Range(99)),"Reset keeps range mode while clearing targets bullets particles and progress");
}
void TitleAndRetry(const Contra& Complete) {
    auto G=Range();G.EnterTitle();Input Held;Held.Fire=Held.Jump=true;Held.JumpPressed=true;G.Step(Held);
    Check(G.GetOption()==1&&G.IsAtTitle()&&G.BulletCount()==0,"range retains title's explicit raw-start requirement");
    for(int Key:{0,0,1,1,2,3,2,3,4,5}) G.SourceKeyDown(Key);
    Check(G.IsAtTitle()&&G.GetStatus().Lives==30,"original keyboard title code still selects thirty lives");
    Check(G.SourceControllerButton(0)&&!G.IsAtTitle()&&G.GetOption()==1&&G.GetStatus().Lives==30&&G.GetRangeHits()==0&&G.BulletCount()==0,"raw title start retains chosen lives and selected range without implicitly shooting");
    G=Complete;const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);Held.Right=Held.Down=Held.Action=Held.Dash=true;Held.FirePressed=Held.JumpPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);
    G.Render(Again);Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"completed range freezes held and semantic input with all bullets and feedback");
    Check(G.SourceControllerButton(0)&&G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Range()),"fresh controller retry preserves range and resets the original seed");
    G=Complete;G.SourceKeyDown(6);auto Expected=Range();Expected.SourceKeyDown(9);
    Check(G.GetOption()==1&&!G.GetStatus().Over&&G.GetRangeHits()==0&&G.GetPlayer().Lives==3&&G.BulletCount()==0&&Access::Snapshot(G)==Access::Snapshot(Expected),"fresh Enter retry keeps range through the existing named-key lifecycle");
}
void DriverLifecycle() {
    Driver D;Check(D.Select("contra",730)&&D.GetOption()==0,"fresh Driver selection defaults to Full run title");D.Advance(Driver::StepSeconds*2.5);Input Stale;Stale.Right=Stale.Fire=Stale.FirePressed=Stale.Jump=true;D.SetInput(Stale);
    Check(D.SetOption(1)&&D.GetOption()==1&&D.Ticks()==0&&D.Advance(Driver::StepSeconds*.5)==0,"explicit range selection starts active and clears title input and partial time");
    Contra Expected;Expected.EnterTitle();Expected.SetOption(1,730);Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first range step has no queued shot jump or movement");
    D.SetPaused(true);D.SetInput(Stale);const auto Before=D.GetFrame();Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Before,D.GetFrame()),"Driver pause freezes the range");
    D.Restart();Expected.Reset(730);Expected.Render(F);Check(D.GetOption()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart retains range while clearing paused input and target progress");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"restart clears stale held actions before active simulation");
    D.Select("contra",730);Contra Fresh;Fresh.EnterTitle();Fresh.Render(F);Check(D.GetOption()==0&&SameFrame(D.GetFrame(),F),"fresh cabinet selection returns to original Full run title");
}
}
int main() {
    ModesAndPhysics();std::array<Contra,3> Stages;Contra Complete;
    if(PublicRoute(Stages,Complete)) {BoundariesAndPurity(Stages);TitleAndRetry(Complete);}DriverLifecycle();
    std::cout<<"Contra target range: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
