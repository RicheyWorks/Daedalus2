// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPlatformersCore.h"
#include <fstream>
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static IronwakePlayer& PlayerOf(IronwakeGame& G) {return G.Player;}
    static void Encounter(IronwakeGame& G,bool Projectile) {
        G.Enemies.clear();G.Bullets.clear();G.EnemyBullets.clear();G.Powerups.clear();
        if(Projectile) G.EnemyBullets.push_back({210,365,0,0,60});
        else G.Enemies.push_back({200,350,0,1,60,1});
    }
    static void Hurt(IronwakeGame& G) {G.Hurt();}
    static void Terminal(IronwakeGame& G) {G.Over=true;G.Player.Lives=0;}
};
}}}
namespace {
using Player=platformers::IronwakePlayer;
const std::vector<Rect> LandingPad{{100,400,100,20}},Empty;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
std::array<double,13> OriginalState(const Player& P) {
    return {{P.X,P.Y,P.VY,static_cast<double>(P.FacingRight),static_cast<double>(P.OnGround),static_cast<double>(P.Crouching),
        static_cast<double>(P.Lives),static_cast<double>(P.Score),static_cast<double>(P.Cooldown),static_cast<double>(P.FireRate),
        static_cast<double>(P.Spread),static_cast<double>(P.SpreadTimer),static_cast<double>(P.Invincible)}};
}
Player ReadPlayer(const std::vector<double>& V) {
    Player P;P.X=V[0];P.Y=V[1];P.VY=V[2];P.FacingRight=V[3]!=0;P.OnGround=V[4]!=0;P.Crouching=V[5]!=0;
    P.Lives=static_cast<int>(V[6]);P.Score=static_cast<std::int64_t>(V[7]);P.Cooldown=static_cast<int>(V[8]);P.FireRate=static_cast<int>(V[9]);
    P.Spread=V[10]!=0;P.SpreadTimer=static_cast<int>(V[11]);P.Invincible=static_cast<int>(V[12]);return P;
}
Input Tap() {Input I;I.JumpPressed=true;return I;}
Player WalkedOff() {
    Player P;P.X=195;P.Y=352;P.VY=1;P.Update({},LandingPad,0); // Real quantized landing primes ground state.
    Input Right;Right.Right=true;P.Update(Right,LandingPad,0);return P;
}
bool CanLateJump(Player P) {
    P.X=200;P.Y=352.6;P.VY=.6;P.OnGround=false;P.Update(Tap(),Empty,0);return Close(P.VY,-12.4);
}
bool HasText(const Frame& F,const std::string& Prefix) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&C.Label.find(Prefix)==0) return true;
    return false;
}
void SourceSteps(const char* Filename) {
    std::ifstream File(Filename);Check(static_cast<bool>(File),"existing platformer fixtures readable");if(!File) return;
    std::string Line;int Cases=0;
    while(std::getline(File,Line)) {
        std::istringstream In(Line);std::string Tag,Label;In>>Tag>>Label;if(Tag!="CSTEP") continue;
        std::vector<double> V;double Value=0;while(In>>Value) V.push_back(Value);
        const bool Shape=In.eof()&&V.size()==34;Check(Shape,"CSTEP "+Label+" original shape");if(!Shape) continue;
        auto P=ReadPlayer(V);const int Frames=static_cast<int>(V[13]),Preset=static_cast<int>(V[14]),Keys=static_cast<int>(V[16]);
        if(Frames<0||Frames>6000) {Check(false,"CSTEP bounded frame count");continue;}
        Input I;I.Left=(Keys&1)!=0;I.Right=(Keys&2)!=0;I.Down=(Keys&4)!=0||V[19]!=0;I.Jump=(Keys&8)!=0||V[20]!=0;
        I.AxisX=V[17];I.AxisY=V[18];std::vector<Rect> Platforms;
        if(Preset==1) Platforms.assign(platformers::IronwakePlatforms().begin(),platformers::IronwakePlatforms().end());
        else if(Preset==2) Platforms=LandingPad;
        for(int F=0;F<Frames;++F) P.Update(I,Platforms,V[15]);
        const auto Actual=OriginalState(P);
        for(std::size_t F=0;F<Actual.size();++F) Check(Close(Actual[F],V[F+21]),"CSTEP "+Label+" original field "+std::to_string(F));
        ++Cases;
    }
    Check(Cases==51,"only all 51 CSTEP source cases consumed");
}
void GraceWindow() {
    auto P=WalkedOff();Check(P.X==200&&Close(P.Y,352.6)&&!P.OnGround,"normal movement leaves the actual platform edge");
    const double Before=P.Y;P.Update(Tap(),LandingPad,0);
    Check(Close(P.VY,-12.4)&&Close(P.Y,Before-12.4)&&!P.OnGround,"first late press preserves -13 impulse then same-frame gravity");
    P.Update(Tap(),LandingPad,0);Check(Close(P.VY,-11.8),"successful ledge jump consumes grace and cannot jump twice in air");
    P=WalkedOff();for(int N=0;N<5;++N) P.Update({},LandingPad,0);P.Update(Tap(),LandingPad,0);
    Check(Close(P.VY,-12.4)&&!P.OnGround,"sixth decision after walkoff still jumps");
    P=WalkedOff();for(int N=0;N<6;++N) P.Update({},LandingPad,0);P.Update(Tap(),LandingPad,0);
    Check(P.VY>0&&!P.OnGround,"seventh decision cannot revive expired grace");
    Input Crouch;Crouch.Down=true;Crouch.Jump=true;P=WalkedOff();P.Update(Crouch,LandingPad,0);
    Check(P.Crouching&&P.VY>0,"crouching blocks a late jump even while grace is warm");
    for(int N=0;N<5;++N) P.Update(Crouch,LandingPad,0);
    P.Update(Tap(),LandingPad,0);
    Check(!P.Crouching&&P.VY>0,"crouching decisions expire grace rather than saving it until release");
    P=WalkedOff();Input Held;Held.Jump=true;P.Update(Held,LandingPad,0);
    Check(Close(P.VY,-12.4),"source held jump is accepted during grace without a new edge");
    P={};P.X=150;P.Y=300;P.VY=2;P.Update(Tap(),Empty,0);
    Check(Close(P.VY,2.6)&&Close(P.Y,302.6),"ordinary unavailable air tap creates no jump or landing queue");
    int Wait=0;while(!P.OnGround&&Wait<40) {P.Update({},Empty,0);++Wait;}
    Check(Wait<40&&P.Y==472&&P.VY==0,"unavailable tap does not launch automatically on later landing");
    P={};P.X=100;P.Y=472;P.OnGround=true;int Landed=0,Hopped=0;
    for(int N=0;N<90;++N) {const bool Was=P.OnGround;P.Update(Held,Empty,0);if(P.OnGround&&!Was) ++Landed;if(Was&&P.VY<0) ++Hopped;}
    Check(Landed>=2&&Hopped>=3,"unchanged held jump repeats after each actual landing");
    P=WalkedOff();Input Left;Left.Left=true;P.Update(Left,Empty,180);
    Check(P.X==230&&P.VY>0,"camera clamp retains source precedence during ledge grace");
}
void DamageAndReadiness() {
    IronwakeGame G;Frame F;platformers::TestAccess::PlayerOf(G)=WalkedOff();G.Render(F);
    Check(HasText(F,"JUMP: ready"),"readiness names a currently usable ledge jump");
    for(bool Projectile:{false,true}) {
        G.Reset(730);platformers::TestAccess::PlayerOf(G)=WalkedOff();platformers::TestAccess::Encounter(G,Projectile);G.Step({});
        Check(G.GetStatus().Lives==2&&G.GetPlayer().Invincible==90,"real "+std::string(Projectile?"projectile":"enemy")+" damage is accepted");
        Check(!CanLateJump(G.GetPlayer()),"accepted damage clears an actual warm ledge window");
        G.Render(F);Check(HasText(F,"JUMP: airborne"),"damage-cleared grace no longer advertises jump readiness");
    }
    G.Reset(730);auto& P=platformers::TestAccess::PlayerOf(G);P=WalkedOff();P.Invincible=10;
    platformers::TestAccess::Hurt(G);
    Check(P.Lives==3&&P.Invincible==10&&CanLateJump(P),"invincible rejected Hurt preserves real grace and life");
    for(int N=0;N<6;++N) P.Update({},LandingPad,0);
    G.Render(F);
    Check(HasText(F,"JUMP: airborne"),"expired grace uses ordinary airborne readiness");
}
void Lifecycle() {
    IronwakeGame G;platformers::TestAccess::PlayerOf(G)=WalkedOff();Check(CanLateJump(G.GetPlayer()),"lifecycle fixture contains real warm grace");
    G.Reset(730);Check(!CanLateJump(G.GetPlayer()),"Reset clears the previous run's grace");
    platformers::TestAccess::PlayerOf(G)=WalkedOff();G.EnterTitle();
    Check(G.IsAtTitle()&&!CanLateJump(G.GetPlayer()),"entering title clears gameplay grace");
    platformers::TestAccess::PlayerOf(G)=WalkedOff();
    Check(G.SourceControllerButton(0)&&!G.IsAtTitle()&&!CanLateJump(G.GetPlayer()),"explicit title-to-play reset clears a controlled warm window");
    platformers::TestAccess::PlayerOf(G)=WalkedOff();platformers::TestAccess::Terminal(G);
    const auto Before=OriginalState(G.GetPlayer());Input Held;Held.Jump=true;Held.Right=true;Held.Fire=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(OriginalState(G.GetPlayer())==Before&&CanLateJump(G.GetPlayer()),"terminal fixed steps freeze original state and warm grace");
    Check(G.SourceControllerButton(0)&&!G.GetStatus().Over&&G.GetStatus().Lives==3&&!CanLateJump(G.GetPlayer()),"fresh controller replay starts without terminal grace");
}
}
int main(int Argc,char** Argv) {
    if(Argc!=2) {std::cerr<<"Usage: ironwake_ledge_grace_test <platformers_parity.txt>\n";return 2;}
    SourceSteps(Argv[1]);GraceWindow();DamageAndReadiness();Lifecycle();
    std::cout<<"Ironwake ledge grace: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
