// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPlatformersCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static void Encounter(ShadowNinjaGame& G,bool Jumper,int Health) {
        G.Reset(730);G.Enemies={{400,450,0,0,Health,Jumper}};G.Attacks.clear();G.Gold.clear();G.SpawnTimer=100;
        G.Player.Invincible=100;
    }
    static NinjaEnemy& Enemy(ShadowNinjaGame& G) {return G.Enemies.front();}
    static void Strike(ShadowNinjaGame& G,bool Star) {G.Attacks={{Star?391.0:397.0,450,1,Star?50:12,Star,0}};}
    static void Spin(ShadowNinjaGame& G) {G.Player.X=400;G.Player.Y=450;G.Player.Spinning=5;G.Enemies.front().X=425;}
    static std::string Snapshot(const ShadowNinjaGame& G) {
        std::ostringstream O;O.precision(17);const auto& P=G.Player;auto R=G.Rng;
        O<<G.SessionSeed<<' '<<G.Score<<' '<<G.SpawnTimer<<' '<<G.BossPulseCueFrames<<' '<<G.BossActive<<' '<<G.Over<<' '<<G.Won<<' '<<R.Next();
        O<<' '<<P.X<<' '<<P.Y<<' '<<P.VX<<' '<<P.VY<<' '<<P.OnGround<<' '<<P.Facing<<' '<<P.AttackCooldown<<' '<<P.Health<<' '<<P.Invincible
            <<' '<<P.DoubleJump<<' '<<P.Spinning<<' '<<P.SpinCooldown<<' '<<P.OnWall<<' '<<P.WallDir<<' '<<P.JumpWasDown<<' '<<P.GroundGraceFrames<<' '<<P.JumpBufferFrames;
        O<<' '<<G.Previous.Fire<<' '<<G.Previous.Action<<' '<<G.Previous.Dash;
        O<<' '<<G.Boss.X<<' '<<G.Boss.Y<<' '<<G.Boss.VX<<' '<<G.Boss.Health<<' '<<G.Boss.AttackTimer;
        O<<' '<<G.Enemies.size();for(const auto& E:G.Enemies) O<<' '<<E.X<<' '<<E.Y<<' '<<E.VX<<' '<<E.VY<<' '<<E.Health<<' '<<E.Jumper;
        O<<' '<<G.Attacks.size();for(const auto& A:G.Attacks) O<<' '<<A.X<<' '<<A.Y<<' '<<A.Direction<<' '<<A.Life<<' '<<A.Star<<' '<<A.Angle;
        O<<' '<<G.Gold.size();for(const auto& V:G.Gold) O<<' '<<V.X<<' '<<V.Y;return O.str();
    }
};
}}}
namespace {
using Access=platformers::TestAccess;
int Checks=0,Failed=0;
constexpr Color Plate{20,20,40,255},Filled{255,215,100,255},Empty{70,70,90,255};
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Tint(Color A,Color B) {return A.R==B.R&&A.G==B.G&&A.B==B.B&&A.A==B.A;}
bool RectAt(const Frame& F,double X,double Y,double W,double H,Color ColorValue) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Rectangle
        &&C.A.X==X&&C.A.Y==Y&&C.B.X==W&&C.B.Y==H&&Tint(C.Tint,ColorValue);});
}
int PipCount(const Frame& F,Color ColorValue) {
    return static_cast<int>(std::count_if(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Rectangle
        &&C.B.X==6&&C.B.Y==5&&Tint(C.Tint,ColorValue);}));
}
bool Pips(const Frame& F,const platformers::NinjaEnemy& E) {
    const int Max=E.Jumper?4:2;const double Top=E.Y-(E.Jumper?28:42);
    if(!RectAt(F,E.X-Max*4-1,Top,Max*8+2,9,Plate)) return false;
    for(int N=0;N<Max;++N) if(!RectAt(F,E.X-Max*4+1+N*8,Top+2,6,5,N<E.Health?Filled:Empty)) return false;
    return PipCount(F,Filled)==E.Health&&PipCount(F,Empty)==Max-E.Health;
}
void FullAndPosition() {
    for(bool Jumper:{false,true}) {
        ShadowNinjaGame G;Access::Encounter(G,Jumper,Jumper?4:2);Frame F;G.Render(F);const auto& E=Access::Enemy(G);
        Check(Pips(F,E),"full health shows each enemy type's actual two/four-hit capacity");
        if(!Jumper) Check(RectAt(F,E.X-10,E.Y-18,20,26,{220,50,50,255}),"walker body rectangle is retained below its pips");
        else Check(std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Circle
            &&C.A.X==E.X&&C.A.Y==E.Y&&C.Size==15&&Tint(C.Tint,{150,50,50,255});}),"jumper body circle is retained below its pips");
        for(double X:{31.25,770.5}) {
            auto& Moving=Access::Enemy(G);Moving.X=X;Moving.Y=300.75;Moving.VX=-1.5;Moving.VY=-6;G.Step({});G.Render(F);
            Check(Pips(F,Moving)&&Moving.X==X-1.5&&Moving.Y<300.75,"health cue follows fractional edge movement and vertical motion");
        }
    }
}
void ActualDamage() {
    for(int Kind=0;Kind<3;++Kind) for(bool Jumper:{false,true}) {
        const int Maximum=Jumper?4:2;ShadowNinjaGame G;Access::Encounter(G,Jumper,Maximum);
        if(Kind==2) Access::Spin(G);else Access::Strike(G,Kind==1);
        G.Step({});Frame F;G.Render(F);
        Check(G.EnemyCount()==1&&Access::Enemy(G).Health==Maximum-1&&Pips(F,Access::Enemy(G)),"surviving sword/star/spin hit removes exactly one filled health pip");
        Check(G.AttackCount()==0&&G.GetStatus().Score==0,"surviving hit consumes its projectile and awards no kill score");
        Access::Encounter(G,Jumper,1);if(Kind==2) Access::Spin(G);else Access::Strike(G,Kind==1);
        G.Step({});G.Render(F);
        Check(G.EnemyCount()==0&&G.AttackCount()==0&&PipCount(F,Filled)==0&&PipCount(F,Empty)==0,"lethal hit removes both enemy and all its health pips");
        Check(G.GetStatus().Score==(Kind==2?200:(Kind==1?100:150)),"sword/star/spin retain their original once-only kill scores");
    }
}
void PresentationPurity() {
    ShadowNinjaGame Observed;Access::Encounter(Observed,true,3);auto Quiet=Observed;const auto Before=Access::Snapshot(Observed);
    const auto Note=Observed.GetStatus().Note;Frame F;
    for(int N=0;N<4;++N) {Observed.Render(F);Observed.GetStatus();}
    Check(Pips(F,Access::Enemy(Observed))&&Access::Snapshot(Observed)==Before&&Observed.GetStatus().Note==Note,"repeated presentation preserves partial health, input state, timers and future random state");
    for(int N=0;N<24;++N) {
        Observed.Render(F);Observed.GetStatus();Input I;I.Right=N<8;I.Left=N>=8&&N<16;I.JumpPressed=N==3;
        I.FirePressed=N==0;I.ActionPressed=N==6;I.DashPressed=N==12;Observed.Step(I);Quiet.Step(I);
        Check(Access::Snapshot(Observed)==Access::Snapshot(Quiet)&&Observed.GetStatus().Note==Quiet.GetStatus().Note,"extra presentation preserves paired future step "+std::to_string(N));
    }
    Observed.Reset(730);Observed.Render(F);
    Check(Observed.EnemyCount()==0&&PipCount(F,Filled)==0&&PipCount(F,Empty)==0,"Reset clears old enemies and their derived health display");
}
}
int main() {
    FullAndPosition();ActualDamage();PresentationPurity();
    std::cout<<"Ninja enemy health: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
