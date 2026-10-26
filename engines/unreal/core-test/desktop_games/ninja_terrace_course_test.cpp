// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static void Fall(ShadowNinjaGame& G) {
        auto& P=G.Player;P.Y=541;P.VY=1;P.OnGround=P.DoubleJump=P.OnWall=false;P.JumpWasDown=true;
        P.GroundGraceFrames=P.JumpBufferFrames=0;P.AttackCooldown=0;
    }
    static std::uint32_t NextRandom(const ShadowNinjaGame& G) {auto R=G.Rng;return R.Next();}
    static std::string Snapshot(const ShadowNinjaGame& G) {
        std::ostringstream O;O.precision(17);const auto& P=G.Player;
        O<<G.GetOption()<<' '<<G.CourseStage<<' '<<G.SessionSeed<<' '<<G.Score<<' '<<G.Over<<' '<<G.Won<<' '<<G.BossActive<<' '<<G.SpawnTimer<<' '<<G.BossPulseCueFrames;
        O<<' '<<P.X<<' '<<P.Y<<' '<<P.VX<<' '<<P.VY<<' '<<P.OnGround<<' '<<P.Facing<<' '<<P.AttackCooldown<<' '<<P.Health<<' '<<P.Invincible
            <<' '<<P.DoubleJump<<' '<<P.Spinning<<' '<<P.SpinCooldown<<' '<<P.OnWall<<' '<<P.WallDir<<' '<<P.JumpWasDown<<' '<<P.GroundGraceFrames<<' '<<P.JumpBufferFrames;
        O<<' '<<G.Gold.size();for(const auto& V:G.Gold) O<<' '<<V.X<<' '<<V.Y;
        O<<' '<<G.Attacks.size();for(const auto& A:G.Attacks) O<<' '<<A.X<<' '<<A.Y<<' '<<A.Direction<<' '<<A.Life<<' '<<A.Star<<' '<<A.Angle;
        O<<' '<<G.Enemies.size();for(const auto& E:G.Enemies) O<<' '<<E.X<<' '<<E.Y<<' '<<E.VX<<' '<<E.VY<<' '<<E.Health<<' '<<E.Jumper;
        O<<' '<<G.Boss.X<<' '<<G.Boss.Y<<' '<<G.Boss.VX<<' '<<G.Boss.Health<<' '<<G.Boss.AttackTimer;
        const auto& I=G.Previous;O<<' '<<I.Left<<' '<<I.Right<<' '<<I.Up<<' '<<I.Down<<' '<<I.PadLeft<<' '<<I.PadRight<<' '<<I.PadUp<<' '<<I.PadDown
            <<' '<<I.AxisX<<' '<<I.AxisY<<' '<<I.Fire<<' '<<I.Jump<<' '<<I.Action<<' '<<I.Dash<<' '<<I.FirePressed<<' '<<I.JumpPressed<<' '<<I.ActionPressed<<' '<<I.DashPressed;
        O<<' '<<NextRandom(G);return O.str();
    }
};
}}}
namespace {
using Ninja=ShadowNinjaGame;
using Access=platformers::TestAccess;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
Ninja Course(std::uint32_t Seed=730) {Ninja G;G.SetOption(1,Seed);return G;}
Vec Goal(const Ninja& G) {
    Frame F;G.Render(F);for(const auto& C:F.Commands) if(C.Kind==Shape::Circle&&C.Size==6&&C.Tint.R==255&&C.Tint.G==200&&C.Tint.B==50) return C.A;
    return {-1000,-1000};
}
bool SamePoint(Vec A,Vec B) {return Close(A.X,B.X)&&Close(A.Y,B.Y);}
bool PublicRoute(std::array<Ninja,3>& Stages,Ninja& Finished) {
    auto G=Course();Stages[0]=G;int Steps=0;const auto Step=[&](const Input& I){G.Step(I);++Steps;};Input Right;Right.Right=true;
    for(int N=0;N<11;++N) Step(Right);
    Check(G.GetPlayer().X==230&&G.GetPlayer().OnGround,"ordinary right movement reaches the first jumping ledge");
    Input Jump=Right;Jump.Jump=Jump.JumpPressed=true;Step(Jump);
    for(int N=0;N<60&&G.GetStatus().Score<50;++N) Step(Right);
    Check(G.GetStatus().Score==50&&G.GetPlayer().OnGround&&G.GoldCount()==1&&SamePoint(Goal(G),{640,210}),"one fresh ground jump and normal movement light the first goal and reveal the second");
    if(G.GetStatus().Score!=50) return false;
    Stages[1]=G;
    for(int N=0;N<30&&G.GetPlayer().X<445;++N) Step(Right);
    Check(G.GetPlayer().X==445&&G.GetPlayer().OnGround,"ordinary movement reaches the second jumping ledge");Step(Jump);
    for(int N=0;N<60&&G.GetStatus().Score<100;++N) Step(Right);
    Check(G.GetStatus().Score==100&&G.GetPlayer().OnGround&&G.GoldCount()==1&&SamePoint(Goal(G),{765,140}),"second ground jump lights the upper terrace with only the wall goal remaining");
    if(G.GetStatus().Score!=100) return false;
    Stages[2]=G;
    Input Climb=Right;Climb.Up=true;for(int N=0;N<140&&!G.GetStatus().Over;++N) Step(Climb);
    const auto S=G.GetStatus();Check(S.Score==150&&S.Won&&S.Over&&G.GoldCount()==0&&G.EnemyCount()==0&&!G.HasBoss()&&Steps<=303,"public jumps and wall climb collect all three lights for exactly 150 points without combat");
    std::cout<<"Terrace public route: "<<Steps<<" steps, score "<<S.Score<<", health "<<S.Lives<<'\n';Finished=G;return S.Won&&S.Score==150;
}
void Checkpoints(const std::array<Ninja,3>& Stages) {
    constexpr std::array<Vec,3> Anchors{{{175,380},{410,300},{640,220}}};
    for(std::size_t N=0;N<Stages.size();++N) {
        auto G=Stages[N];const auto Target=Goal(G);Access::Fall(G);Input Falling;Falling.Jump=Falling.Fire=Falling.FirePressed=true;G.Step(Falling);
        const auto& P=G.GetPlayer();Check(SamePoint({P.X,P.Y},Anchors[N])&&P.Health==5&&P.OnGround&&G.GetStatus().Score==static_cast<std::int64_t>(N)*50&&SamePoint(Goal(G),Target)&&G.GoldCount()==1&&!G.GetStatus().Over,"real fall recovery preserves reached light and goal at its safe anchor");
        Check(G.AttackCount()==0&&P.AttackCooldown==0&&P.VY==0,"recovery clears the attack created on the fall frame and restores fresh movement state");
        Input Held;Held.Jump=Held.Fire=true;G.Step(Held);
        Check(SamePoint({G.GetPlayer().X,G.GetPlayer().Y},Anchors[N])&&G.GetPlayer().OnGround&&G.AttackCount()==0,"held jump and fire cannot become fresh recovery actions");
        G.Step({});Input Fresh;Fresh.Jump=Fresh.JumpPressed=true;G.Step(Fresh);
        Check(G.GetPlayer().VY==-11&&Close(G.GetPlayer().Y,Anchors[N].Y-11),"release followed by a fresh jump uses the unchanged ground impulse");
    }
}
void ModesAndPurity() {
    Ninja Default;Default.Reset(730);Random R;R.Seed(730);for(int N=0;N<10;++N) R.Next();
    Check(Default.GetOption()==0&&Default.GoldCount()==5&&Access::NextRandom(Default)==R.Next(),"default Adventure retains its five random lights and ten reset draws");
    auto G=Course();R.Seed(730);Check(G.GetOption()==1&&G.GetStatus().Score==0&&G.GetStatus().Lives==5&&G.EnemyCount()==0&&!G.HasBoss()&&G.GoldCount()==1&&SamePoint(Goal(G),{410,290})&&Access::NextRandom(G)==R.Next(),"course opens with one ordered goal normal health and no random spawn draws");
    Input Sword;Sword.FirePressed=true;G.Step(Sword);Check(G.AttackCount()==1,"existing sword remains available in the course");
    const auto Before=Access::Snapshot(G);auto Quiet=G;Frame F,Again;G.Render(F);
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();}
    Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"course presentation preserves movement counters attacks goals and RNG");
    for(int Value:{-1,2}) Check(!G.SetOption(Value,99)&&Access::Snapshot(G)==Before,"invalid mode refuses before mutating the active course");
    for(int N=0;N<20;++N) {G.Step({});Quiet.Step({});}
    Check(G.AttackCount()==0&&G.EnemyCount()==0&&!G.HasBoss()&&Access::Snapshot(G)==Access::Snapshot(Quiet),"course animates and expires attacks while presentation reads leave future simulation unchanged");
    G.Reset(99);auto Fresh=Course(99);Check(G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Fresh),"Reset retains course but clears stage score checkpoint and attacks");
    G.SetOption(0,730);for(int N=0;N<4;++N) {Input I;I.Right=N<2;I.FirePressed=N==0;G.Step(I);Default.Step(I);}
    Check(Access::Snapshot(G)==Access::Snapshot(Default),"returning to Adventure preserves seeded spawning combat and movement steps");
}
void ResultAndDriver(const Ninja& Complete) {
    auto G=Complete;const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);Input Held;Held.Up=Held.Right=Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
    Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;for(int N=0;N<8;++N) G.Step(Held);G.Render(Again);
    Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"completion freezes all movement combat score and goal state until an explicit retry");
    Check(G.SourceControllerButton(0)&&G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Course()),"fresh controller retry retains course and clears completion");
    G=Complete;Check(G.SourceKeyDown(7)&&Access::Snapshot(G)==Access::Snapshot(Course()),"fresh Space retry also starts the same course cleanly");
    Driver D;Check(D.Select("shadow_ninja",730),"Driver opens the existing Ninja engine");D.Advance(Driver::StepSeconds*2.5);Input Stale;Stale.Right=Stale.Jump=Stale.JumpPressed=Stale.FirePressed=true;D.SetInput(Stale);
    Check(D.SetOption(1)&&D.GetOption()==1&&D.Ticks()==0&&D.Advance(Driver::StepSeconds*.5)==0,"course selection clears old input and partial time");
    auto Expected=Course();Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first course step has no old jump attack or movement");
    D.SetPaused(true);D.SetInput(Stale);D.Restart();Expected=Course();Expected.Render(F);
    Check(D.GetOption()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart retains course and clears pause and progress");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"restart discards queued paused actions");
}
}
int main() {
    ModesAndPurity();std::array<Ninja,3> Stages;Ninja Complete;
    if(PublicRoute(Stages,Complete)) {Checkpoints(Stages);ResultAndDriver(Complete);}
    std::cout<<"Ninja terrace course: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
