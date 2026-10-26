// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopPlatformersCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <iomanip>
#include <limits>

using namespace daedalus::desktop;
using namespace daedalus::desktop::platformers;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess {
    static IronwakePlayer& PlayerOf(IronwakeGame& G) { return G.Player; }
    static void IronwakeEncounter(IronwakeGame& G,const IronwakeEnemy& E,const IronwakeBullet& B) {
        G.Enemies={E}; G.Bullets={B}; G.EnemyBullets.clear(); G.Powerups.clear();
    }
    static void IronwakePickup(IronwakeGame& G,bool Rapid) {
        G.Enemies.clear(); G.Bullets.clear(); G.EnemyBullets.clear();
        G.Powerups={{G.Player.X,G.Player.Y,0,Rapid}};
    }
    static NinjaPlayer& PlayerOf(EmberstepGame& G) { return G.Player; }
    static void NinjaEncounter(EmberstepGame& G,const NinjaEnemy& E,const NinjaAttack& A) {
        G.Enemies={E}; G.Attacks={A}; G.Gold.clear(); G.SpawnTimer=100;
    }
    static void NinjaGold(EmberstepGame& G) { G.Gold={{G.Player.X,G.Player.Y}}; G.SpawnTimer=100; }
    static void NinjaBossEncounter(EmberstepGame& G) {
        G.BossActive=true; G.Boss={500,380,0,1,40};
        G.Attacks={{491,375,1,50,true,0}}; G.Enemies.clear(); G.Gold.clear(); G.SpawnTimer=100;
        G.Player.X=175; G.Player.Y=380; G.Player.Invincible=100;
    }
};
}}}

namespace {
int Checks=0,Fixtures=0;
std::string Context;
void Check(bool Pass,const std::string& What) {
    ++Checks;
    if(!Pass) {
        throw std::runtime_error(Context+": "+What);
    }
}
void Near(double Actual,double Expected,const std::string& Field) {
    ++Checks;
    if(!std::isfinite(Actual) || std::abs(Actual-Expected)>1e-8) {
        std::ostringstream S; S<<Context<<": "<<Field<<" actual="<<std::setprecision(17)<<Actual<<" expected="<<Expected;
        throw std::runtime_error(S.str());
    }
}
struct Row {
    std::istringstream S;
    explicit Row(const std::string& Line):S(Line){}
    double D() {
        double X=0;
        if(!(S>>X)) {
            throw std::runtime_error(Context+": malformed fixture");
        }
        return X;
    }
    int I() { return static_cast<int>(D()); }
    bool B() { return I()!=0; }
};
IronwakePlayer ReadIronwake(Row& R) {
    IronwakePlayer P; P.X=R.D();P.Y=R.D();P.VY=R.D();P.FacingRight=R.B();P.OnGround=R.B();P.Crouching=R.B();
    P.Lives=R.I();P.Score=static_cast<std::int64_t>(R.D());P.Cooldown=R.I();P.FireRate=R.I();P.Spread=R.B();P.SpreadTimer=R.I();P.Invincible=R.I(); return P;
}
void Compare(const IronwakePlayer& P,Row& R) {
    Near(P.X,R.D(),"x");Near(P.Y,R.D(),"y");Near(P.VY,R.D(),"vy");Near(P.FacingRight,R.D(),"facing");Near(P.OnGround,R.D(),"ground");Near(P.Crouching,R.D(),"crouch");
    Near(P.Lives,R.D(),"lives");Near(static_cast<double>(P.Score),R.D(),"score");Near(P.Cooldown,R.D(),"cooldown");Near(P.FireRate,R.D(),"fire rate");Near(P.Spread,R.D(),"spread");Near(P.SpreadTimer,R.D(),"spread timer");Near(P.Invincible,R.D(),"invincible");
}
IronwakeBullet ReadBullet(Row& R) { IronwakeBullet B;B.X=R.D();B.Y=R.D();B.VX=R.D();B.VY=R.D();B.Life=R.I();return B; }
void Compare(const IronwakeBullet& B,Row& R) { Near(B.X,R.D(),"bullet x");Near(B.Y,R.D(),"bullet y");Near(B.VX,R.D(),"bullet vx");Near(B.VY,R.D(),"bullet vy");Near(B.Life,R.D(),"bullet life"); }
IronwakeEnemy ReadIronwakeEnemy(Row& R) { IronwakeEnemy E;E.X=R.D();E.Y=R.D();E.VX=R.D();E.Health=R.I();E.ShootTimer=R.I();E.Kind=R.I();return E; }
void Compare(const IronwakeEnemy& E,Row& R) { Near(E.X,R.D(),"enemy x");Near(E.Y,R.D(),"enemy y");Near(E.VX,R.D(),"enemy vx");Near(E.Health,R.D(),"enemy hp");Near(E.ShootTimer,R.D(),"enemy timer");Near(E.Kind,R.D(),"enemy kind"); }
NinjaPlayer ReadNinja(Row& R) {
    NinjaPlayer P;P.X=R.D();P.Y=R.D();P.VX=R.D();P.VY=R.D();P.OnGround=R.B();P.Facing=R.I();P.AttackCooldown=R.I();P.Health=R.I();P.Invincible=R.I();
    P.DoubleJump=R.B();P.Spinning=R.I();P.SpinCooldown=R.I();P.OnWall=R.B();P.WallDir=R.I();P.JumpWasDown=R.B();return P;
}
void Compare(const NinjaPlayer& P,Row& R) {
    Near(P.X,R.D(),"ninja x");Near(P.Y,R.D(),"ninja y");Near(P.VX,R.D(),"ninja vx");Near(P.VY,R.D(),"ninja vy");Near(P.OnGround,R.D(),"ground");Near(P.Facing,R.D(),"facing");
    Near(P.AttackCooldown,R.D(),"attack cooldown");Near(P.Health,R.D(),"health");Near(P.Invincible,R.D(),"invincible");Near(P.DoubleJump,R.D(),"double jump");
    Near(P.Spinning,R.D(),"spinning");Near(P.SpinCooldown,R.D(),"spin cooldown");Near(P.OnWall,R.D(),"wall");Near(P.WallDir,R.D(),"wall direction");Near(P.JumpWasDown,R.D(),"jump edge");
}
NinjaAttack ReadAttack(Row& R) { NinjaAttack A;A.X=R.D();A.Y=R.D();A.Direction=R.I();A.Life=R.I();A.Star=R.B();A.Angle=R.I();return A; }
void Compare(const NinjaAttack& A,Row& R) { Near(A.X,R.D(),"attack x");Near(A.Y,R.D(),"attack y");Near(A.Direction,R.D(),"direction");Near(A.Life,R.D(),"life");Near(A.Star,R.D(),"star");Near(A.Angle,R.D(),"angle"); }
NinjaEnemy ReadNinjaEnemy(Row& R) { NinjaEnemy E;E.X=R.D();E.Y=R.D();E.VX=R.D();E.VY=R.D();E.Health=R.I();E.Jumper=R.B();return E; }
void Compare(const NinjaEnemy& E,Row& R) { Near(E.X,R.D(),"enemy x");Near(E.Y,R.D(),"enemy y");Near(E.VX,R.D(),"enemy vx");Near(E.VY,R.D(),"enemy vy");Near(E.Health,R.D(),"enemy health");Near(E.Jumper,R.D(),"jumper"); }
NinjaBoss ReadBoss(Row& R) { NinjaBoss B;B.X=R.D();B.Y=R.D();B.VX=R.D();B.Health=R.I();B.AttackTimer=R.I();return B; }
void Compare(const NinjaBoss& B,Row& R) { Near(B.X,R.D(),"boss x");Near(B.Y,R.D(),"boss y");Near(B.VX,R.D(),"boss vx");Near(B.Health,R.D(),"boss health");Near(B.AttackTimer,R.D(),"boss timer"); }
void RunFixture(const std::string& Line) {
    Row R(Line);std::string Tag,Label;R.S>>Tag>>Label;Context=Tag+" "+Label;++Fixtures;
    if(Tag=="CSTEP") {
        auto P=ReadIronwake(R);const int Frames=R.I(),Preset=R.I();const double Camera=R.D();const int K=R.I();Input I;
        I.Left=(K&1)!=0;I.Right=(K&2)!=0;I.Down=(K&4)!=0;I.Jump=(K&8)!=0;I.AxisX=R.D();I.AxisY=R.D();I.Down=R.B()||I.Down;I.Jump=R.B()||I.Jump;
        std::vector<Rect> Plats;
        if(Preset==1) {
            Plats.assign(IronwakePlatforms().begin(),IronwakePlatforms().end());
        } else if(Preset==2) {
            Plats={{100,400,100,20}};
        }
        for(int F=0;F<Frames;++F) {
            P.Update(I,Plats,Camera);
        }
        Compare(P,R);
    } else if(Tag=="CSHOT") {
        auto P=ReadIronwake(R);std::vector<IronwakeBullet> B;P.Shoot(B);Near(P.Cooldown,R.D(),"cooldown");const int Count=R.I();Near(static_cast<double>(B.size()),Count,"count");
        for(int J=0;J<3;++J) {
            if(J<Count) {
                Compare(B[static_cast<std::size_t>(J)],R);
            } else {
                for(int K=0;K<5;++K) {
                    Near(0,R.D(),"empty slot");
                }
            }
        }
    } else if(Tag=="CBULLET") {
        auto B=ReadBullet(R);const int Frames=R.I();
        for(int F=0;F<Frames;++F) {
            B.Update();
        }
        Compare(B,R);
    } else if(Tag=="CENEMY") {
        auto E=ReadIronwakeEnemy(R);const int Frames=R.I();IronwakePlayer P;P.X=R.D();const double RandomValue=R.D();const int RandomInt=R.I();std::vector<IronwakeBullet> B;
        for(int F=0;F<Frames;++F) {
            E.Update(P,B,RandomValue<.02,RandomInt);
        }
        Compare(E,R);const int Count=R.I();Near(static_cast<double>(B.size()),Count,"count");
        if(Count>0) {
            Compare(B[0],R);
        } else {
            for(int K=0;K<5;++K) {
                Near(0,R.D(),"empty slot");
            }
        }
    } else if(Tag=="NSTEP") {
        auto P=ReadNinja(R);const int Frames=R.I(),Preset=R.I(),K=R.I();Input I;I.Left=(K&1)!=0;I.Right=(K&2)!=0;I.Up=(K&4)!=0;I.Down=(K&8)!=0;I.Jump=(K&16)!=0;
        I.AxisX=R.D();I.AxisY=R.D();const double HatX=R.D(),HatY=R.D();I.Jump=R.B()||I.Jump;std::vector<Rect> Plats;
        if(Preset==1) {
            Plats.assign(NinjaPlatforms().begin(),NinjaPlatforms().end());
        } else if(Preset==2) {
            Plats={{100,300,200,12}};
        }
        if(Preset==1) {
            // Exercise the actual Game adapter for canonical-platform cases;
            // a pure-player test alone would miss a dropped D-pad binding.
            EmberstepGame G;G.Reset(10);TestAccess::PlayerOf(G)=P;
            I.PadLeft=HatX<0;I.PadRight=HatX>0;I.PadDown=HatY<0;I.PadUp=HatY>0;
            for(int F=0;F<Frames;++F) {
                G.Step(I);
            }
            Compare(G.GetPlayer(),R);
        } else {
            for(int F=0;F<Frames;++F) {
                P.Update(I,Plats,HatX,HatY);
            }
            Compare(P,R);
        }
    } else if(Tag=="NATTACK") {
        auto P=ReadNinja(R);const bool Star=R.B();NinjaAttack A;const bool Created=P.TryAttack(Star,A);Near(P.AttackCooldown,R.D(),"cooldown");Near(Created,R.D(),"created");
        if(Created) {
            Compare(A,R);
        } else {
            for(int K=0;K<6;++K) {
                Near(0,R.D(),"empty attack");
            }
        }
    } else if(Tag=="NSPIN") {
        auto P=ReadNinja(R);const bool Active=P.Spin();Near(P.Spinning,R.D(),"spinning");Near(P.SpinCooldown,R.D(),"cooldown");Near(Active,R.D(),"active");
    } else if(Tag=="NPROJECTILE") {
        auto A=ReadAttack(R);const int Frames=R.I();
        for(int F=0;F<Frames;++F) {
            A.Update();
        }
        Compare(A,R);
    } else if(Tag=="NENEMY") {
        auto E=ReadNinjaEnemy(R);const int Frames=R.I();const double RandomValue=R.D();
        for(int F=0;F<Frames;++F) {
            E.Update(RandomValue<.02);
        }
        Compare(E,R);
    } else if(Tag=="NBOSS") {
        auto B=ReadBoss(R);NinjaPlayer P;P.X=R.D();P.Y=R.D();P.Health=R.I();P.Invincible=R.I();const int Frames=R.I();
        for(int F=0;F<Frames;++F) {
            B.Update(P);
        }
        Compare(B,R);
        Near(P.X,R.D(),"player x");Near(P.Y,R.D(),"player y");Near(P.Health,R.D(),"player health");Near(P.Invincible,R.D(),"player invincible");
    } else if(Tag=="CREWARD") {
        IronwakeGame G;G.Reset(10);IronwakeEnemy E;E.Kind=R.I();E.Health=R.I();E.X=200;E.Y=470;E.VX=0;E.ShootTimer=80;
        const double BX=R.D(),BY=R.D();TestAccess::IronwakeEncounter(G,E,{BX,BY,0,0,60});G.Step({});
        Near(static_cast<double>(G.GetStatus().Score),R.D(),"score");Near(static_cast<double>(G.EnemyCount()),R.D(),"enemies");Near(static_cast<double>(G.BulletCount()),R.D(),"bullets");
    } else if(Tag=="NREWARD") {
        EmberstepGame G;G.Reset(10);const bool Star=R.B();NinjaEnemy E;E.X=400;E.Y=450;E.VX=0;E.Health=R.I();
        TestAccess::NinjaEncounter(G,E,{Star?391.0:397.0,450,1,Star?50:12,Star,0});G.Step({});
        Near(static_cast<double>(G.GetStatus().Score),R.D(),"score");Near(static_cast<double>(G.EnemyCount()),R.D(),"enemies");Near(static_cast<double>(G.AttackCount()),R.D(),"attacks");
    } else if(Tag=="NSREWARD") {
        EmberstepGame G;G.Reset(10);auto& P=TestAccess::PlayerOf(G);P.X=400;P.Y=450;P.Spinning=5;
        NinjaEnemy E;E.X=420;E.Y=450;E.VX=0;E.Health=R.I();TestAccess::NinjaEncounter(G,E,{0,0,1,0,false,0});G.Step({});
        Near(static_cast<double>(G.GetStatus().Score),R.D(),"score");Near(static_cast<double>(G.EnemyCount()),R.D(),"enemies");
    } else if(Tag=="NPICKUP") {
        EmberstepGame G;G.Reset(10);auto& P=TestAccess::PlayerOf(G);P.X=400;P.Y=450;TestAccess::NinjaGold(G);G.Step({});
        Near(static_cast<double>(G.GetStatus().Score),R.D(),"score");Near(static_cast<double>(G.GoldCount()),R.D(),"gold");
    } else if(Tag=="CPICKUP") {
        IronwakeGame G;G.Reset(10);const bool Rapid=R.B();TestAccess::IronwakePickup(G,Rapid);G.Step({});
        Near(G.GetPlayer().Spread,R.D(),"spread");Near(G.GetPlayer().SpreadTimer,R.D(),"timer");Near(G.GetPlayer().FireRate,R.D(),"rate");
    } else {
        throw std::runtime_error("Unknown fixture: "+Tag);
    }
    std::string Extra;Check(!(R.S>>Extra),"no trailing fixture fields");
}
void Integration() {
    Context="IRONWAKE integration";IronwakeGame C;Input I;Frame F;
    Check(C.EnemyCount()==2,"latest start has two enemies");
    Check(C.GetPlayer().Lives==3 && C.GetPlayer().Score==0,"initial lives and score");
    IronwakeEnemy E;E.X=200;E.Y=470;E.VX=0;E.ShootTimer=80;
    TestAccess::IronwakeEncounter(C,E,{188,480,12,0,60});C.Step({});
    Check(C.GetStatus().Score==100,"grunt hit pays 100 once");C.Step({});Check(C.GetStatus().Score==100,"dead enemy cannot pay twice");
    C.Reset(10);E.Kind=2;E.Health=2;TestAccess::IronwakeEncounter(C,E,{188,480,12,0,60});C.Step({});Check(C.GetStatus().Score==0,"boss survives one bullet");
    E.Health=1;TestAccess::IronwakeEncounter(C,E,{188,480,12,0,60});C.Step({});Check(C.GetStatus().Score==500,"boss kill pays 500");
    C.Reset(10);TestAccess::IronwakePickup(C,false);C.Step({});Check(C.GetPlayer().Spread && C.GetPlayer().SpreadTimer==900,"spread pickup lasts 900 steps");
    TestAccess::IronwakePickup(C,true);C.Step({});Check(C.GetPlayer().FireRate==4,"rapid pickup halves cooldown");
    C.Reset(10);
    for(int Key:{0,0,1,1,2,3,2,3,4,5}) {
        C.SubmitCheatKey(Key);
    }
    Check(C.GetPlayer().Lives==8 && C.GetPlayer().SpreadTimer==600,"source in-play cheat grants five lives and spread");
    C.Reset(10);
    for(int Key:{0,0,1,1,2,3,2,3,4,5}) {
        C.SubmitCheatKey(Key,true);
    }
    Check(C.GetPlayer().Lives==30 && !C.GetPlayer().Spread,"optional source title cheat grants 30 lives");
    C.Reset(10);auto& CP=TestAccess::PlayerOf(C);CP.X=2801;CP.Invincible=900;C.Step({});Check(C.GetStatus().Won && C.GetStatus().Over,"source distance victory preserved");
    const double StoppedX=C.GetPlayer().X;I.Right=true;
    for(int K=0;K<60;++K) {
        C.Step(I);
    }
    Near(C.GetPlayer().X,StoppedX,"won game stops");
    C.Reset(10);CP.Lives=1;CP.Invincible=0;E={CP.X,CP.Y,0,1,100,0};TestAccess::IronwakeEncounter(C,E,{0,0,0,0,0});C.Step({});Check(C.GetStatus().Over && !C.GetStatus().Won,"death terminates session");
    C.Reset(10);Check(!C.GetStatus().Over && C.GetStatus().Score==0 && C.GetPlayer().Lives==3,"restart clears terminal state");

    Context="Emberstep Ascent integration";EmberstepGame N;
    Check(N.GetPlayer().OnGround && N.GetPlayer().X==175 && N.GetPlayer().Y==380,"latest safe platform start");
    Check(N.GoldCount()==5 && N.GetPlayer().Health==5,"initial gold and health");
    I={};I.Jump=true;N.Step(I);Near(N.GetPlayer().Y,369,"first jump");N.Step(I);Check(N.GetPlayer().DoubleJump,"held jump does not consume double jump");
    N.Step({});N.Step(I);Check(!N.GetPlayer().DoubleJump && N.GetPlayer().VY== -9,"second edge consumes double jump");
    N.Reset(11);TestAccess::NinjaGold(N);N.Step({});Check(N.GetStatus().Score==50 && N.GoldCount()==0,"gold pickup pays once");N.Step({});Check(N.GetStatus().Score==50,"removed gold cannot pay twice");
    N.Reset(11);NinjaEnemy NE;NE.X=400;NE.Y=450;NE.VX=0;NE.Health=1;
    TestAccess::NinjaEncounter(N,NE,{397,450,1,12,false,0});N.Step({});Check(N.GetStatus().Score==150,"sword kill pays 150");
    N.Reset(11);TestAccess::NinjaEncounter(N,NE,{391,450,1,50,true,0});N.Step({});Check(N.GetStatus().Score==100,"star kill pays 100");
    N.Reset(11);auto& NP=TestAccess::PlayerOf(N);NP.X=400;NP.Y=450;NP.Spinning=5;NE.X=420;TestAccess::NinjaEncounter(N,NE,{0,0,1,0,false,0});N.Step({});Check(N.GetStatus().Score==200,"spin kill pays 200");
    N.Reset(11);TestAccess::NinjaBossEncounter(N);N.Step({});Check(N.GetStatus().Won && N.GetStatus().Over && N.GetStatus().Score==800,"boss kill terminal reward");
    N.Step(I);Check(N.GetStatus().Score==800,"boss reward once");
    N.Reset(11);NP.Y=541;NP.X=400;N.Step({});Check(N.GetStatus().Over && N.GetPlayer().Health==0,"pit death");
    N.Reset(11);Check(!N.GetStatus().Over && !N.HasBoss() && N.AttackCount()==0 && N.EnemyCount()==0 && N.GoldCount()==5,"complete reset clears transient state");
    I={};I.Left=true;I.PadRight=true;N.Step(I);Near(N.GetPlayer().X,180,"D-pad right wins over keyboard left");Check(N.GetPlayer().Facing==1,"D-pad right sets facing");
    N.Reset(11);I={};I.Right=true;I.PadLeft=true;N.Step(I);Near(N.GetPlayer().X,170,"D-pad left wins over keyboard right");Check(N.GetPlayer().Facing== -1,"D-pad left sets facing");
    N.Reset(11);I={};I.AxisX= -1;I.PadRight=true;N.Step(I);Near(N.GetPlayer().X,180,"D-pad right wins over stick left");
    N.Reset(11);I={};I.AxisX=1;I.PadLeft=true;N.Step(I);Near(N.GetPlayer().X,170,"D-pad left wins over stick right");
    N.Reset(11);I={};I.AxisX=1;I.PadLeft=true;I.PadRight=true;N.Step(I);Near(N.GetPlayer().X,180,"opposing D-pad flags cancel to neutral hat");
    N.Reset(11);NP.X=30;NP.Y=200;NP.OnGround=false;I={};I.PadUp=true;N.Step(I);Near(N.GetPlayer().Y,197.6,"D-pad up reaches wall climb through Game adapter");
    N.Reset(11);NP.X=30;NP.Y=200;NP.OnGround=false;I={};I.PadDown=true;N.Step(I);Near(N.GetPlayer().Y,203.6,"D-pad down reaches wall descent through Game adapter");
    N.Reset(11);NP.X=30;NP.Y=200;NP.OnGround=false;I={};I.Down=true;I.PadUp=true;N.Step(I);Near(N.GetPlayer().Y,200.6,"opposing vertical inputs preserve source additive climb conditions");
    N.Reset(11);
    NP.X=770;NP.Y=100;NP.Spinning=5;NP.Facing=1;N.Step({});Check(N.GetPlayer().X<=770,"spin cannot escape arena");
    NP.X=30;NP.Y=-100;I={};I.Up=true;N.Step(I);Check(N.GetPlayer().Y>= -100,"wall climb bounded above arena");

    Context="bounded replay and frame validation";Random R;R.Seed(135);IronwakeGame C2;EmberstepGame N2;
    C.Reset(17);C2.Reset(17);N.Reset(17);N2.Reset(17);
    for(int K=0;K<20000;++K) {
        I={};const int Bits=R.Int(0,255);I.Left=(Bits&1)!=0;I.Right=(Bits&2)!=0;I.Up=(Bits&4)!=0;I.Down=(Bits&8)!=0;
        I.Fire=(Bits&16)!=0;I.Jump=(Bits&32)!=0;I.Action=(Bits&64)!=0;I.Dash=(Bits&128)!=0;
        I.AxisX=R.Between(-1,1);I.AxisY=R.Between(-1,1);C.Step(I);C2.Step(I);N.Step(I);N2.Step(I);
        if(K%200==0) {
            Check(C.BulletCount()<=192 && C.EnemyCount()<=6 && C.ParticleCount()<=160,"IRONWAKE entity bounds");
            Check(N.AttackCount()<=64 && N.EnemyCount()<=5 && N.GoldCount()<=5,"Ninja entity bounds");
            Check(C.GetPlayer().X==C2.GetPlayer().X && C.GetStatus().Score==C2.GetStatus().Score && C.EnemyCount()==C2.EnemyCount(),"IRONWAKE deterministic replay");
            Check(N.GetPlayer().X==N2.GetPlayer().X && N.GetStatus().Score==N2.GetStatus().Score && N.EnemyCount()==N2.EnemyCount(),"Ninja deterministic replay");
            C.Render(F);Check(F.Commands.size()<Frame::MaxCommands,"IRONWAKE bounded render");
            for(const auto& D:F.Commands) {
                Check(std::isfinite(D.A.X)&&std::isfinite(D.A.Y)&&std::isfinite(D.B.X)&&std::isfinite(D.B.Y),"IRONWAKE finite geometry");
            }
            N.Render(F);Check(F.Commands.size()<Frame::MaxCommands,"Ninja bounded render");
            for(const auto& D:F.Commands) {
                Check(std::isfinite(D.A.X)&&std::isfinite(D.A.Y)&&std::isfinite(D.B.X)&&std::isfinite(D.B.Y),"Ninja finite geometry");
            }
        }
        if(K%300==299) {
            const auto Seed=static_cast<std::uint32_t>(K);C.Reset(Seed);C2.Reset(Seed);N.Reset(Seed);N2.Reset(Seed);
        }
    }
    I={};I.AxisX=std::numeric_limits<double>::quiet_NaN();I.AxisY=std::numeric_limits<double>::infinity();C.Reset(1);N.Reset(1);C.Step(I);N.Step(I);
    Check(std::isfinite(C.GetPlayer().X) && std::isfinite(N.GetPlayer().X),"malformed axes sanitized");
}
}
int main(int Argc,char** Argv) {
    try {
        const char* Path=Argc>1?Argv[1]:"platformers_parity.txt";std::ifstream File(Path);
        if(!File) {
            throw std::runtime_error(std::string("Cannot open source fixtures: ")+Path);
        }
        std::string Line;
        while(std::getline(File,Line)) {
            if(!Line.empty() && Line[0]!='#') {
                RunFixture(Line);
            }
        }
        Check(Fixtures>20,"meaningful source fixture coverage");Integration();
        std::cout<<"Platformers: "<<Checks<<" checks passed; "<<Fixtures<<" executed-source fixtures; 20000 deterministic lifecycle steps per game\n";return 0;
    } catch(const std::exception& E) { std::cerr<<"FAIL "<<E.what()<<"\n";return 1; }
}
