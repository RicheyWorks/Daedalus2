// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <limits>

namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess;
// Latest Desktop sources, selected by the user. See platformers_notes.md for
// source hashes, original defects, source parity and deliberate adaptations.
inline const std::array<Rect,5>& ContraPlatforms() {
    static const std::array<Rect,5> P{{{300,420,120,20},{500,320,80,20},
        {650,440,100,20},{900,380,150,20},{1100,300,60,20}}}; return P;
}
inline const std::array<Rect,4>& NinjaPlatforms() {
    static const std::array<Rect,4> P{{{100,380,150,12},{350,300,120,12},
        {550,220,180,12},{200,480,400,12}}}; return P;
}
inline Rect PixelRect(double X,double Y,double W,double H) {
    return {std::trunc(X),std::trunc(Y),std::trunc(W),std::trunc(H)};
}
inline bool PixelContains(const Rect& R,double X,double Y) {
    return R.Contains(std::trunc(X),std::trunc(Y));
}
inline void AddScore(std::int64_t& Score,int Amount) {
    Score=std::min(Score,std::numeric_limits<std::int64_t>::max()-Amount)+Amount;
}
struct ContraBullet {
    double X=0,Y=0,VX=0,VY=0; int Life=60;
    void Update() { X+=VX; Y+=VY; --Life; }
};
struct ContraPlayer {
    double X=100,Y=480,VY=0;
    bool FacingRight=true,OnGround=false,Crouching=false;
    int Lives=3,Cooldown=0,FireRate=8,SpreadTimer=0,Invincible=0;
    std::int64_t Score=0; bool Spread=false;
    Rect GetRect() const { return PixelRect(X,Y,32,Crouching ? 24 : 48); }
    template<class Platforms>
    void Update(const Input& I,const Platforms& P,double CameraX) {
        double Dx=0;
        if(I.Left) { Dx=-5; FacingRight=false; }
        if(I.Right) { Dx=5; FacingRight=true; }
        const double StickX=Axis(I.AxisX),StickY=Axis(I.AxisY);
        if(std::abs(StickX)>.15) { Dx=StickX*6.25; FacingRight=Dx>0; }
        X+=Dx;
        Crouching=I.Down || StickY>.5;
        const int H=Crouching ? 24 : 48;
        if((I.Jump || I.JumpPressed) && OnGround && !Crouching) { VY=-13; OnGround=false; }
        VY+=.6; Y+=VY; OnGround=false;
        const Rect BeforeGround=GetRect();
        if(Y+H>=520) { Y=520-H; VY=0; OnGround=true; }
        for(const auto& Platform:P) {
            if(BeforeGround.Overlaps(Platform) && VY>=0 && Y+H-VY<=Platform.Y+5) {
                Y=Platform.Y-H; VY=0; OnGround=true;
            }
        }
        X=std::max(X,CameraX+50);
        if(Cooldown>0) --Cooldown;
        if(SpreadTimer>0 && --SpreadTimer==0) Spread=false;
        if(Invincible>0) --Invincible;
    }
    void Shoot(std::vector<ContraBullet>& Bullets) {
        if(Cooldown>0 || Bullets.size()+ (Spread?3u:1u)>96) return;
        Cooldown=FireRate;
        const double StartX=X+(FacingRight?32:0),StartY=Y+(Crouching?16:24);
        const int D=FacingRight?1:-1;
        if(Spread) {
            for(int A:{0,15,-15}) {
                const double Rad=A*D*3.14159265358979323846/180;
                Bullets.push_back({StartX,StartY,12*std::cos(Rad)*D,12*std::sin(Rad),60});
            }
        } else Bullets.push_back({StartX,StartY,12.0*D,0,60});
    }
};
struct ContraEnemy {
    double X=0,Y=470,VX=-2; int Health=1,ShootTimer=60,Kind=0;
    int Width() const { return Kind==2?60:28; }
    int Height() const { return Kind==2?70:40; }
    Rect GetRect() const { return PixelRect(X,Y,Width(),Height()); }
    // Random results are arguments: deterministic source fixtures can inject
    // exact Python decisions without coupling rules to either random generator.
    void Update(const ContraPlayer& P,std::vector<ContraBullet>& Bullets,
                bool Turn,int NextShootTimer) {
        if(Health<=0) return;
        X+=VX;
        if(Kind==0 && Turn) VX=-VX;
        if(--ShootTimer<=0) {
            ShootTimer=NextShootTimer;
            const double Dx=P.X-X,V=Dx/std::max(std::abs(Dx),1.0)*5;
            if(Bullets.size()<96) Bullets.push_back({X+Width()/2.0,Y+15,V,2,60});
        }
        if(Kind==2) VX=X>P.X+200?-1.5:(X<P.X-100?1.5:0);
    }
};
struct ContraPowerup { double X=0,Y=0,Bob=0; bool Rapid=false; };
struct Particle { double X=0,Y=0,VX=0,VY=0; int Life=0; Color Tint; };

struct NinjaAttack {
    double X=0,Y=0; int Direction=1,Life=12; bool Star=false; int Angle=0;
    void Update() { X+=Direction*(Star?9:3); --Life; if(Star) Angle=((Life*30)%360+360)%360; }
};
struct NinjaPlayer {
    double X=175,Y=380,VX=0,VY=0;
    bool OnGround=true; int Facing=1,AttackCooldown=0,Health=5,Invincible=0;
    bool DoubleJump=false; int Spinning=0,SpinCooldown=0;
    bool OnWall=false; int WallDir=0; bool JumpWasDown=false;
    template<class Platforms>
    void Update(const Input& I,const Platforms& P,double HatX=0,double HatY=0) {
        double Dx=0;
        if(I.Left) { Dx=-1; Facing=-1; }
        if(I.Right) { Dx=1; Facing=1; }
        const double Sx=Axis(I.AxisX),Sy=Axis(I.AxisY);
        if(std::abs(Sx)>.2) { Dx=Sx; Facing=Sx>0?1:-1; }
        if(HatX!=0) { Dx=HatX>0?1:-1; Facing=HatX>0?1:-1; }
        // Keep the source controller hat separate from keyboard directions:
        // its horizontal value wins over both the keyboard and the stick.
        VX=Dx*5;
        const bool JumpDown=I.Jump || I.JumpPressed;
        const bool JumpPressed=I.JumpPressed || (JumpDown && !JumpWasDown);
        JumpWasDown=JumpDown;
        VY=std::min(VY+.6,12.0);
        if(JumpPressed && OnGround) { VY=-11; OnGround=false; DoubleJump=true; }
        else if(JumpPressed && !OnGround && DoubleJump) { VY=-9; DoubleJump=false; }
        const double OldY=Y; X+=VX; Y+=VY; X=Clamp(X,30,770);
        OnGround=false;
        for(const auto& Platform:P) {
            const bool Inside=Platform.X<=X && X<=Platform.X+Platform.W;
            const bool Crossed=OldY<=Platform.Y && Platform.Y<=Y;
            const bool Close=Platform.Y-12<Y && Y<Platform.Y+18;
            if(Inside && VY>=0 && (Crossed || Close)) {
                Y=Platform.Y; VY=0; OnGround=true; DoubleJump=false; break;
            }
        }
        OnWall=false;
        if(!OnGround && (X<=35 || X>=765)) {
            OnWall=true; WallDir=X<=35?-1:1; VY=std::min(VY,1.0); DoubleJump=true;
            if(I.Up || Sy<-.3 || HatY>0) Y-=3;
            if(I.Down || Sy>.3 || HatY<0) Y+=3;
            if(JumpPressed) { VX=-WallDir*7; VY=-10; OnWall=false; X-=WallDir*10; }
        }
        if(Y>540) Health=0;
        if(AttackCooldown>0) --AttackCooldown;
        if(SpinCooldown>0) --SpinCooldown;
        if(Spinning>0) { --Spinning; X+=Facing*3; }
        if(Invincible>0) --Invincible;
        // Original spin added movement after the clamp; prevent escaping the
        // arena and bound unlimited wall climbing while preserving wall jumps.
        X=Clamp(X,30,770); Y=std::max(Y,-100.0);
    }
    bool TryAttack(bool Star,NinjaAttack& Out) {
        if(AttackCooldown!=0) return false;
        AttackCooldown=Star?12:18;
        Out={X+Facing*(Star?15:25),Y-5,Facing,Star?50:12,Star,0}; return true;
    }
    bool Spin() {
        if(SpinCooldown!=0 || !OnGround) return false;
        Spinning=25; SpinCooldown=45; return true;
    }
};
struct NinjaEnemy {
    double X=820,Y=420,VX=-2,VY=0; int Health=2; bool Jumper=false;
    void Update(bool JumpDecision) {
        X+=VX;
        if(Jumper && JumpDecision && Y>=450) VY=-8;
        VY+=.5; Y+=VY;
        if(Y>450) { Y=450; VY=0; }
    }
};
struct NinjaBoss {
    static constexpr int InitialAttackFrames=40,AttackPeriodFrames=50,TelegraphFrames=12;
    static constexpr double AttackHalfWidth=300,AttackHalfHeight=100;
    double X=700,Y=380,VX=-1; int Health=25,AttackTimer=InitialAttackFrames;
    bool IsTelegraphing() const { return AttackTimer>0 && AttackTimer<=TelegraphFrames; }
    bool InStrikeRange(const NinjaPlayer& P) const {
        return std::abs(X-P.X)<AttackHalfWidth && std::abs(Y-P.Y)<AttackHalfHeight;
    }
    void Update(NinjaPlayer& P) {
        X+=VX;
        if(X<500 || X>720) VX=-VX;
        if(--AttackTimer<=0) {
            AttackTimer=AttackPeriodFrames;
            if(InStrikeRange(P) && P.Invincible<=0) {
                --P.Health; P.Invincible=60;
            }
        }
    }
};
}}} // daedalus::desktop::platformers

namespace daedalus { namespace desktop {
class ContraGame final : public Game {
    friend struct platformers::TestAccess;
    platformers::ContraPlayer Player;
    std::vector<platformers::ContraBullet> Bullets,EnemyBullets;
    std::vector<platformers::ContraEnemy> Enemies;
    std::vector<platformers::ContraPowerup> Powerups;
    std::vector<platformers::Particle> Particles;
    Random Rng,CosmeticRng;
    double CameraX=0,Progress=0;
    bool Over=false,Won=false,FinalBossSpawned=false;
    int CheatIndex=0;
    Input Previous;
    void Explode(double X,double Y,Color Tint={255,165,0,255}) {
        for(int I=0;I<12 && Particles.size()<160;++I) {
            const double A=CosmeticRng.Between(0,6.283185307179586),S=CosmeticRng.Between(2,6);
            Particles.push_back({X,Y,std::cos(A)*S,std::sin(A)*S-2,CosmeticRng.Int(20,40),Tint});
        }
    }
    void Spawn(double X,double Y,int Kind) {
        if(Enemies.size()>=6) return;
        Enemies.push_back({X,Y,Kind==0?-2.0:0.0,Kind==2?2:1,Rng.Int(30,90),Kind});
    }
    void Hurt() {
        if(Player.Invincible>0 || Over) return;
        --Player.Lives; Player.Invincible=90; Explode(Player.X+16,Player.Y+20);
        if(Player.Lives<=0) { Player.Lives=0; Over=true; }
    }
    bool HasBoss() const {
        for(const auto& E:Enemies) {
            if(E.Kind==2 && E.Health>0) {
                return true;
            }
        }
        return false;
    }
    std::string GoalText() const {
        if(Won) return "DISTANCE GOAL CROSSED";
        const int Remaining=static_cast<int>(std::ceil(std::max(0.0,FinishX-Player.X)));
        return Remaining>0 ? "PASS X 2800: "+std::to_string(Remaining)+" px left" : "PASS X 2800: cross the line";
    }
    std::string WeaponText() const {
        const std::string Shot=Player.Spread ? "SPREAD: "+std::to_string(Player.SpreadTimer)+" steps" : "NORMAL SHOT";
        return Shot+(Player.FireRate<8 ? " | RAPID: 4-step fire, until restart" : " | 8-step fire");
    }
    std::string FireReadiness() const {
        if(Over) return "FIRE: run ended";
        if(Player.Cooldown>0) return "FIRE: cooldown "+std::to_string(Player.Cooldown)+" steps";
        if(Bullets.size()+(Player.Spread?3u:1u)>MaxBullets) return "FIRE: bullet limit; wait for shots to clear";
        return "FIRE: ready (hold to repeat)";
    }
    std::string JumpReadiness() const {
        if(Over) return "JUMP: run ended";
        if(Player.Crouching) return "JUMP: release crouch";
        return Player.OnGround ? "JUMP: ready (hold repeats on landing)" : "JUMP: airborne; land to jump again";
    }
    std::string ProtectionText() const {
        if(Player.Invincible==1) return "PROTECTION expires next live step";
        return "PROTECTION TIMER "+std::to_string(Player.Invincible);
    }
public:
    static constexpr std::size_t MaxBullets=96,MaxEnemies=6,MaxParticles=160;
    static constexpr double FinishX=2800;
    ContraGame() { Reset(730); }
    void Reset(std::uint32_t Seed) override {
        Player={}; Bullets.clear(); EnemyBullets.clear(); Enemies.clear(); Powerups.clear(); Particles.clear();
        Rng.Seed(Seed); CosmeticRng.Seed(Seed^0x38f01a25u);
        CameraX=0; Progress=0; Over=false; Won=false; FinalBossSpawned=false; CheatIndex=0; Previous={};
        // Source's last revision starts a new session with two enemies and this
        // pickup. Restart now uses that same session reset rather than a second
        // inconsistent three-enemy initializer.
        Spawn(450,470,0); Spawn(650,470,0); Powerups.push_back({620,350,0,false});
    }
    // Optional named-key binding for the source cheat: U,U,D,D,L,R,L,R,B,A.
    // 0=up, 1=down, 2=left, 3=right, 4=B/action, 5=A/jump. The common adapter
    // feeds digital edges below; a full keyboard adapter may call this directly.
    void SubmitCheatKey(int Key,bool TitleScreen=false) {
        static constexpr int Code[10]={0,0,1,1,2,3,2,3,4,5};
        if(Key<0 || Key>5 || Over) { CheatIndex=0; return; }
        if(Key==Code[CheatIndex]) ++CheatIndex; else CheatIndex=0;
        if(CheatIndex==10) {
            CheatIndex=0;
            if(TitleScreen) Player.Lives=30;
            else {
                Player.Lives=std::min(Player.Lives+5,99);
                Player.Spread=true; Player.SpreadTimer=600; Explode(Player.X,Player.Y,{0,255,255,255});
            }
        }
    }
    void Step(const Input& I) override {
        if(Over) return;
        // Mirror the existing Slate merge for direct callers; source stick
        // precedence, right-key precedence and held jump/fire stay in Player.
        Input Controls=I;
        Controls.Left=Controls.Left || I.PadLeft; Controls.Right=Controls.Right || I.PadRight;
        Controls.Up=Controls.Up || I.PadUp; Controls.Down=Controls.Down || I.PadDown;
        if(Controls.Up && !Previous.Up) SubmitCheatKey(0);
        if(Controls.Down && !Previous.Down) SubmitCheatKey(1);
        if(Controls.Left && !Previous.Left) SubmitCheatKey(2);
        if(Controls.Right && !Previous.Right) SubmitCheatKey(3);
        if(Controls.ActionPressed || (Controls.Action && !Previous.Action)) SubmitCheatKey(4);
        if(Controls.JumpPressed || (Controls.Jump && !Previous.Jump)) SubmitCheatKey(5);
        Previous=Controls;
        if(Controls.FirePressed) Player.Shoot(Bullets);
        Player.Update(Controls,platformers::ContraPlatforms(),CameraX);
        if(Controls.Fire || Controls.FirePressed) Player.Shoot(Bullets);
        const double Target=std::max(0.0,Player.X-350);
        CameraX=CameraX*.85+Target*.15;
        for(auto& B:Bullets) B.Update();
        Bullets.erase(std::remove_if(Bullets.begin(),Bullets.end(),[&](const auto& B) {
            return B.Life<=0 || B.X>CameraX+900 || B.X<CameraX-100;
        }),Bullets.end());
        for(auto& B:EnemyBullets) B.Update();
        EnemyBullets.erase(std::remove_if(EnemyBullets.begin(),EnemyBullets.end(),[&](const auto& B) {
            return B.Life<=0 || B.X<CameraX-50 || B.X>CameraX+1000;
        }),EnemyBullets.end());
        for(std::size_t EI=0;EI<Enemies.size();) {
            auto& E=Enemies[EI];
            const bool Turn=E.Kind==0 && Rng.Unit()<.02;
            E.Update(Player,EnemyBullets,Turn,Rng.Int(40,100));
            if(E.X<CameraX-100) { Enemies.erase(Enemies.begin()+EI); continue; }
            const Rect ER=E.GetRect();
            for(std::size_t BI=0;BI<Bullets.size();++BI) {
                if(platformers::PixelContains(ER,Bullets[BI].X,Bullets[BI].Y)) {
                    Bullets.erase(Bullets.begin()+BI); --E.Health;
                    Explode(E.X+E.Width()/2.0,E.Y+15,{255,100,0,255});
                    if(E.Health<=0) { platformers::AddScore(Player.Score,E.Kind==2?500:100); Explode(E.X+E.Width()/2.0,E.Y+20); }
                    break;
                }
            }
            if(E.Health<=0) { Enemies.erase(Enemies.begin()+EI); continue; }
            if(Player.Invincible<=0 && Player.GetRect().Overlaps(ER)) Hurt();
            ++EI;
        }
        for(std::size_t BI=0;BI<EnemyBullets.size();) {
            if(Player.Invincible<=0 && platformers::PixelContains(Player.GetRect(),EnemyBullets[BI].X,EnemyBullets[BI].Y)) {
                EnemyBullets.erase(EnemyBullets.begin()+BI); Hurt();
            } else ++BI;
        }
        if(Over) return;
        for(std::size_t PickupIndex=0;PickupIndex<Powerups.size();) {
            auto& P=Powerups[PickupIndex]; P.Bob=std::fmod(P.Bob+.15,6.283185307179586);
            if(platformers::PixelRect(P.X,P.Y,24,24).Overlaps(Player.GetRect())) {
                if(P.Rapid) Player.FireRate=4; else { Player.Spread=true; Player.SpreadTimer=900; }
                Explode(P.X,P.Y,{255,215,0,255}); Powerups.erase(Powerups.begin()+PickupIndex);
            } else ++PickupIndex;
        }
        Progress=std::max(Progress,(Player.X-100)/10);
        if(Enemies.size()<5 && Rng.Unit()<.03+Progress/800) {
            const double X=CameraX+800+Rng.Int(20,150);
            const double Y=Rng.Unit()>.3?470:(Rng.Int(0,1)?400:350);
            Spawn(X,Y,Progress>80 && !HasBoss()?2:0);
        }
        if(Powerups.empty() && Rng.Unit()<.008)
            Powerups.push_back({CameraX+850,400.0-Rng.Int(0,80),0,Rng.Int(0,1)==1});
        // The Python loop spawned a replacement final boss every time its
        // predecessor died. A single encounter is now tracked explicitly.
        if(Player.X>2200 && !HasBoss() && !FinalBossSpawned) {
            Spawn(Player.X+300,420,2); FinalBossSpawned=true;
        }
        if(Player.X>FinishX) { Won=true; Over=true; }
        for(auto& P:Particles) { P.X+=P.VX; P.Y+=P.VY; P.VY+=.2; --P.Life; }
        Particles.erase(std::remove_if(Particles.begin(),Particles.end(),[](const auto& P){return P.Life<=0;}),Particles.end());
        if(Player.Y>650) {
            Hurt(); Player.Y=450; Player.VY=-8; Player.X=std::max(100.0,Player.X-100);
        }
    }
    Status GetStatus() const override {
        const std::string Note=Over ? (Won?"MISSION COMPLETE | R / Restart: play again":"GAME OVER | R / Restart: try again")
            : "CONTRA | "+GoalText()+" | "+FireReadiness()+(Player.Invincible>0 ? " | "+ProtectionText() : "");
        return {Player.Score,Player.Lives,Over,Won,Note};
    }
    const platformers::ContraPlayer& GetPlayer() const { return Player; }
    double GetCameraX() const { return CameraX; }
    std::size_t BulletCount() const { return Bullets.size()+EnemyBullets.size(); }
    std::size_t EnemyCount() const { return Enemies.size(); }
    std::size_t ParticleCount() const { return Particles.size(); }
    void Render(Frame& F) const override {
        F.Clear(800,600,{135,206,235,255});
        for(int I=-2;I<5;++I) {
            const double X=I*300-std::fmod(CameraX*.2,300);
            F.AddTriangle({X,400},{X+150,280},{X+300,400},{0,100,0,255});
        }
        for(int I=-3;I<6;++I) {
            const double X=I*180-std::fmod(CameraX*.5,180);
            F.AddRect(X,350,40,180,{34,139,34,255});
            F.AddTriangle({X-20,350},{X+20,280},{X+60,350},{0,100,0,255});
        }
        F.AddRect(0,520,800,80,{139,69,19,255}); F.AddRect(0,520,800,12,{34,139,34,255});
        for(const auto& P:platformers::ContraPlatforms()) {
            const double X=P.X-CameraX;
            if(X>-150 && X<900) { F.AddRect(X,P.Y,P.W,P.H,{101,67,33,255}); F.AddRect(X,P.Y,P.W,6,{34,139,34,255}); }
        }
        // This line represents the original world-X victory check, not a
        // checkpoint or a boss prerequisite. Crossing requires X strictly >2800.
        const double GoalX=FinishX-CameraX;
        if(GoalX>=0 && GoalX<=800) {
            F.AddLine(GoalX,180,GoalX,520,{50,255,100,255},3);
            F.AddText(Clamp(GoalX-65,20,630),185,"PASS TO FINISH",{10,60,20,255},16);
        }
        const double X=Player.X-CameraX,Y=Player.Y,H=Player.Crouching?24:48;
        F.AddRect(X,Y+12,32,H-20,Player.Crouching?Color{100,100,100,255}:Color{70,130,180,255});
        const double HeadY=Y+(Player.Crouching?8:4);
        F.AddCircle(X+16,HeadY+10,11,{255,218,185,255});
        F.AddRect(X+4,HeadY+2,24,6,Player.FacingRight?Color{30,144,255,255}:Color{220,20,60,255});
        F.AddRect(X+(Player.FacingRight?26:-2),Y+18,8,6,{255,218,185,255});
        F.AddRect(X+(Player.FacingRight?32:-18),Y+16,18,5,{50,50,50,255});
        F.AddRect(X+4,Y+H-16,10,14,{50,50,50,255}); F.AddRect(X+18,Y+H-16,10,14,{50,50,50,255});
        if(Player.Invincible>0 && (Player.Invincible/4)%2==0) {
            F.AddLine(X-2,Y-2,X+34,Y-2,White,2); F.AddLine(X-2,Y+H+2,X+34,Y+H+2,White,2);
        }
        for(const auto& E:Enemies) {
            const double EX=E.X-CameraX;
            if(E.Kind==2) {
                F.AddCircle(EX+30,E.Y+35,35,{100,0,150,255});
                F.AddCircle(EX+30,E.Y+25,20,{200,50,200,255}); F.AddCircle(EX+25,E.Y+22,8,{255,0,0,255});
                for(int K=0;K<5;++K) F.AddTriangle({EX+K*12+5,E.Y},{EX+K*12,E.Y-15},{EX+K*12+10,E.Y-15},{150,0,200,255});
                F.AddText(EX-5,E.Y-38,"BOSS HP: "+std::to_string(E.Health),{50,0,70,255},16);
            } else {
                F.AddRect(EX,E.Y+8,28,28,{220,20,60,255}); F.AddCircle(EX+14,E.Y+9,10,{255,200,150,255});
                F.AddRect(EX+2,E.Y+2,24,5,{30,30,30,255}); F.AddRect(EX+(E.VX<=0?23:-5),E.Y+18,14,4,{40,40,40,255});
            }
        }
        for(const auto& B:Bullets) F.AddCircle(B.X-CameraX,B.Y,4,{255,255,0,255});
        for(const auto& B:EnemyBullets) F.AddCircle(B.X-CameraX,B.Y,4,{255,165,0,255});
        for(const auto& P:Powerups) {
            const double PY=P.Y+std::sin(P.Bob)*4;
            F.AddCircle(P.X-CameraX+12,PY+12,12,P.Rapid?Color{0,255,255,255}:Color{255,215,0,255});
            F.AddText(P.X-CameraX+7,PY+2,P.Rapid?"R":"S",Black,18);
            F.AddText(P.X-CameraX-30,PY-22,P.Rapid?"RAPID: 4-step fire":"SPREAD: 900 steps",{25,35,45,255},14);
        }
        for(const auto& P:Particles) F.AddCircle(P.X-CameraX,P.Y,3,P.Tint);
        // Keep the HUD above the reachable upper-platform jump arc. Remaining
        // readiness/control text lives below the source ground at Y=520.
        F.AddRect(16,12,768,86,{0,0,0,205});
        F.AddText(30,20,"SCORE: "+std::to_string(Player.Score)); F.AddText(660,20,"LIVES: "+std::to_string(Player.Lives));
        F.AddText(30,48,GoalText(),{150,255,180,255},14);
        F.AddText(650,48,"STAGE 1-"+std::to_string(static_cast<int>(Progress/20)+1),{220,220,220,255},14);
        F.AddRect(30,70,420,4,{65,75,70,255});
        F.AddRect(30,70,420*Clamp((Player.X-100)/(FinishX-100),0,1),4,{50,235,120,255});
        F.AddText(30,80,WeaponText(),{255,225,120,255},14);
        F.AddRect(16,526,768,68,{0,0,0,205});
        F.AddText(30,529,FireReadiness(),White,13);
        if(!Over && Player.Invincible>0) F.AddText(480,529,ProtectionText(),{100,245,255,255},13);
        F.AddText(30,545,JumpReadiness(),White,13);
        if(!Over && HasBoss()) F.AddText(500,545,"BOSS LIVE; distance goal unchanged",{245,180,255,255},12);
        F.AddText(25,562,"Move: WASD/arrows, stick/D-pad | Crouch: down | Jump: Space/W or pad A",White,13);
        F.AddText(25,581,"Hold fire: J/Z/X/Ctrl or pad X/RB/RT | R / Restart: new run",White,13);
        if(Over) {
            F.AddRect(140,220,520,210,{0,0,0,230});
            F.AddText(235,250,Won?"MISSION COMPLETE!":"GAME OVER",Won?Color{50,255,50,255}:Color{255,50,50,255},32);
            F.AddText(190,303,"FINAL SCORE: "+std::to_string(Player.Score),White,22);
            F.AddText(190,341,Won?"Passed the original distance goal.":GoalText(),{200,225,205,255},18);
            F.AddText(190,382,"R / Restart: new run with the same seed",White,18);
        }
    }
};

class ShadowNinjaGame final : public Game {
    friend struct platformers::TestAccess;
    platformers::NinjaPlayer Player;
    std::vector<platformers::NinjaAttack> Attacks;
    std::vector<platformers::NinjaEnemy> Enemies;
    std::vector<Vec> Gold;
    platformers::NinjaBoss Boss;
    bool BossActive=false,Over=false,Won=false;
    int SpawnTimer=0,BossPulseCueFrames=0;
    std::int64_t Score=0;
    Random Rng; Input Previous;
    void Attack(bool Star) {
        platformers::NinjaAttack A;
        if(Attacks.size()<64 && Player.TryAttack(Star,A)) Attacks.push_back(A);
    }
    void Hurt(int Frames) {
        if(Player.Invincible>0 || Over) return;
        --Player.Health; Player.Invincible=Frames;
        if(Player.Health<=0) { Player.Health=0; Over=true; }
    }
public:
    static constexpr std::size_t MaxAttacks=64,MaxEnemies=5;
    static constexpr int BossScoreThreshold=1200,PulseReceiptFrames=8;
    ShadowNinjaGame() { Reset(730); }
    void Reset(std::uint32_t Seed) override {
        Player={}; Attacks.clear(); Enemies.clear(); Gold.clear(); Boss={};
        BossActive=false; Over=false; Won=false; SpawnTimer=0; BossPulseCueFrames=0; Score=0; Previous={}; Rng.Seed(Seed);
        for(int I=0;I<5;++I) Gold.push_back({static_cast<double>(Rng.Int(80,700)),static_cast<double>(Rng.Int(200,400))});
    }
    void Step(const Input& I) override {
        if(Over) return;
        if(BossPulseCueFrames>0) --BossPulseCueFrames;
        // Source attacks are KEYDOWN/JOYBUTTONDOWN events, not held auto-fire.
        if(I.FirePressed || (I.Fire && !Previous.Fire)) Attack(false);
        if(I.ActionPressed || (I.Action && !Previous.Action)) Attack(true);
        if(I.DashPressed || (I.Dash && !Previous.Dash)) Player.Spin();
        Previous=I;
        const int HatX=static_cast<int>(I.PadRight)-static_cast<int>(I.PadLeft);
        const int HatY=static_cast<int>(I.PadUp)-static_cast<int>(I.PadDown);
        Player.Update(I,platformers::NinjaPlatforms(),HatX,HatY);
        if(Player.Health<=0) { Player.Health=0; Over=true; return; }
        --SpawnTimer;
        if(SpawnTimer<=0 && Enemies.size()<5) {
            const bool Jumper=Rng.Int(0,1)==1;
            Enemies.push_back({820,420,Jumper?-1.5:-2.0,0,Jumper?4:2,Jumper}); SpawnTimer=Rng.Int(35,60);
        }
        for(auto& E:Enemies) E.Update(E.Jumper && Rng.Unit()<.02);
        Enemies.erase(std::remove_if(Enemies.begin(),Enemies.end(),[](const auto& E){return E.X< -30;}),Enemies.end());
        for(std::size_t GI=0;GI<Gold.size();) {
            if(Distance(Player.X,Player.Y,Gold[GI].X,Gold[GI].Y)<20) {
                platformers::AddScore(Score,50); Gold.erase(Gold.begin()+GI);
            } else ++GI;
        }
        for(auto& A:Attacks) A.Update();
        Attacks.erase(std::remove_if(Attacks.begin(),Attacks.end(),[](const auto& A){return A.Life<=0;}),Attacks.end());
        for(std::size_t AI=0;AI<Attacks.size();) {
            bool Hit=false;
            for(std::size_t EI=0;EI<Enemies.size();++EI) {
                auto& E=Enemies[EI];
                if(Distance(Attacks[AI].X,Attacks[AI].Y,E.X,E.Y)<(Attacks[AI].Star?15:20)) {
                    --E.Health;
                    if(E.Health<=0) { platformers::AddScore(Score,Attacks[AI].Star?100:150); Enemies.erase(Enemies.begin()+EI); }
                    Hit=true; break;
                }
            }
            if(Hit) Attacks.erase(Attacks.begin()+AI); else ++AI;
        }
        if(Player.Spinning>0) {
            for(std::size_t EI=0;EI<Enemies.size();) {
                auto& E=Enemies[EI];
                if(Distance(Player.X,Player.Y,E.X,E.Y)<45 && --E.Health<=0) {
                    platformers::AddScore(Score,200); Enemies.erase(Enemies.begin()+EI);
                } else ++EI;
            }
        }
        if(Player.Invincible<=0) {
            for(const auto& E:Enemies) if(Distance(Player.X,Player.Y,E.X,E.Y)<22) { Hurt(45); break; }
        }
        if(Over) return;
        if(Score>=BossScoreThreshold && !BossActive) { Boss={}; BossActive=true; }
        if(BossActive) {
            const bool PulseThisStep=Boss.AttackTimer<=1;
            Boss.Update(Player);
            // Receipt of the existing instant pulse, including misses/protected
            // players. Cosmetic only: never infer that health changed or extend damage.
            if(PulseThisStep) BossPulseCueFrames=PulseReceiptFrames;
            if(Player.Health<=0) { Player.Health=0; Over=true; return; }
            if(Distance(Player.X,Player.Y,Boss.X,Boss.Y)<35) Hurt(45);
            if(Over) return;
            for(std::size_t AI=0;AI<Attacks.size();) {
                if(Distance(Attacks[AI].X,Attacks[AI].Y,Boss.X,Boss.Y)<30) {
                    --Boss.Health; Attacks.erase(Attacks.begin()+AI);
                    if(Boss.Health<=0) { BossActive=false; platformers::AddScore(Score,800); Won=true; Over=true; break; }
                } else ++AI;
            }
        }
    }
    Status GetStatus() const override {
        std::string Text=Won?"BOSS DEFEATED! Host R/Restart replays."
            :(Over?"GAME OVER. Host R/Restart replays.":ReadinessText());
        if(!Over) {
            if(BossActive && Boss.IsTelegraphing()) Text+=" Boss pulse in "+std::to_string(Boss.AttackTimer)+" steps; current strike range shown.";
            else if(BossActive && BossPulseCueFrames>0) Text+=" Boss pulse fired; contact/enemies remain dangerous.";
            else if(!BossActive) Text+=" Boss at score "+std::to_string(BossScoreThreshold)+".";
        }
        return {Score,Player.Health,Over,Won,Text};
    }
    const platformers::NinjaPlayer& GetPlayer() const { return Player; }
    const platformers::NinjaBoss& GetBoss() const { return Boss; }
    bool HasBoss() const { return BossActive; }
    int PulseReceiptFramesRemaining() const { return BossPulseCueFrames; }
    std::size_t EnemyCount() const { return Enemies.size(); }
    std::size_t AttackCount() const { return Attacks.size(); }
    std::size_t GoldCount() const { return Gold.size(); }
    void Render(Frame& F) const override {
        F.Clear(800,600,{20,20,40,255}); F.AddRect(0,0,800,480,{30,30,60,255});
        for(int X:{80,300,520,720}) { F.AddRect(X,200,8,40,{100,60,20,255}); F.AddCircle(X+4,195,6,{255,150,50,255}); }
        for(const auto& P:platformers::NinjaPlatforms()) { F.AddRect(P.X,P.Y,P.W,12,{80,80,100,255}); F.AddRect(P.X,P.Y,P.W,4,{120,120,140,255}); }
        for(int X:{150,450,650}) { F.AddRect(X,350,20,130,{40,80,40,255}); F.AddCircle(X+10,340,25,{30,100,30,255}); }
        if(BossActive && !Over && Boss.IsTelegraphing()) {
            // The source checks strict axis distances after moving the boss.
            // This outline is current reach, not a prediction or a safe-zone promise.
            const double L=Clamp(Boss.X-platformers::NinjaBoss::AttackHalfWidth,0,800);
            const double R=Clamp(Boss.X+platformers::NinjaBoss::AttackHalfWidth,0,800);
            const double T=Clamp(Boss.Y-platformers::NinjaBoss::AttackHalfHeight,0,600);
            const double B=Clamp(Boss.Y+platformers::NinjaBoss::AttackHalfHeight,0,600);
            const Color Cue{255,150,50,255};
            F.AddLine(L,T,R,T,Cue,2); F.AddLine(R,T,R,B,Cue,2);
            F.AddLine(R,B,L,B,Cue,2); F.AddLine(L,B,L,T,Cue,2);
        }
        if(!(Player.Invincible>0 && Player.Invincible%8<4)) {
            const double X=Player.X,Y=Player.Y;
            F.AddRect(X-8,Y-20,16,28,{60,60,80,255});
            F.AddCircle(X,Y-25,8,{255,200,170,255}); F.AddRect(X-6,Y-28,12,8,{30,30,30,255});
            if(Player.OnWall) {
                F.AddLine(X,Y-15,X+Player.WallDir*12,Y-18,{200,200,200,255},3);
                F.AddLine(X,Y-5,X+Player.WallDir*12,Y-2,{200,200,200,255},3);
                F.AddCircle(X+Player.WallDir*18,Y-10,4,{100,255,100,255});
            }
            if(Player.Spinning>0) {
                for(int K=0;K<3;++K) {
                    const double A=((25-Player.Spinning)*20+K*120)*3.14159265358979323846/180;
                    F.AddLine(X,Y-10,X+std::cos(A)*22,Y-10+std::sin(A)*10,{255,200,50,255},4);
                }
            } else if(Player.AttackCooldown>10) F.AddLine(X+Player.Facing*20,Y-10,X+Player.Facing*38,Y-5,{255,200,50,255},4);
        }
        for(const auto& G:Gold) { F.AddCircle(G.X,G.Y,6,{255,200,50,255}); F.AddCircle(G.X,G.Y,3,{255,255,200,255}); }
        for(const auto& E:Enemies) {
            if(E.Jumper) F.AddCircle(E.X,E.Y,15,{150,50,50,255});
            else { F.AddRect(E.X-10,E.Y-18,20,26,{220,50,50,255}); F.AddCircle(E.X,E.Y-22,7,{200,100,100,255}); }
        }
        for(const auto& A:Attacks) {
            if(!A.Star) F.AddLine(A.X,A.Y,A.X+A.Direction*20,A.Y,{255,200,50,255},5);
            else {
                const double Rad=A.Angle*3.14159265358979323846/180;
                F.AddLine(A.X-std::cos(Rad)*8,A.Y-std::sin(Rad)*8,A.X+std::cos(Rad)*8,A.Y+std::sin(Rad)*8,{200,200,220,255},3);
                F.AddLine(A.X-std::sin(Rad)*8,A.Y+std::cos(Rad)*8,A.X+std::sin(Rad)*8,A.Y-std::cos(Rad)*8,{200,200,220,255},3);
                F.AddCircle(A.X,A.Y,3,White);
            }
        }
        if(BossActive) {
            F.AddRect(Boss.X-25,Boss.Y-35,50,50,{80,30,30,255}); F.AddCircle(Boss.X,Boss.Y-45,15,{150,50,50,255});
            F.AddCircle(Boss.X-6,Boss.Y-48,4,{255,0,0,255}); F.AddCircle(Boss.X+6,Boss.Y-48,4,{255,0,0,255});
            F.AddRect(Boss.X-40,Boss.Y-70,80,8,{255,0,0,255}); F.AddRect(Boss.X-40,Boss.Y-70,std::max(0.0,80.0*Boss.Health/25),8,{0,255,0,255});
        }
        F.AddText(30,20,"SCORE: "+std::to_string(Score),{255,200,50,255});
        F.AddText(630,20,"HEALTH: "+std::to_string(Player.Health),{220,50,50,255}); F.AddText(350,20,"LEVEL: 1",{80,150,255,255},16);
        if(!Over) {
            F.AddText(30,50,ReadinessText(),White,13);
            if(!BossActive) F.AddText(30,72,"Boss entry: "+std::to_string(Score)+" / "+std::to_string(BossScoreThreshold),{255,200,50,255},14);
            else if(Boss.IsTelegraphing()) {
                F.AddText(30,72,"BOSS PULSE IN "+std::to_string(Boss.AttackTimer)+" STEPS: current reach",{255,150,50,255},16);
                F.AddText(30,94,Boss.InStrikeRange(Player)?"Inside current pulse reach. Contact/enemies can still hurt."
                    :"Outside current pulse reach. Boss moves before striking; watch contact/enemies.",White,13);
            } else if(BossPulseCueFrames>0) F.AddText(30,72,"Boss pulse fired (instant strike; hit not implied)",{255,150,50,255},14);
        }
        F.AddText(60,575,"Jump: A/Space  Sword: B/X  Star: Y/RB  Spin: LB  Wall: up/down",White,16);
        if(Over) {
            F.AddRect(180,240,440,130,{20,20,40,240});
            F.AddText(260,270,Won?"BOSS DEFEATED!":"GAME OVER",Won?Color{255,200,50,255}:Color{220,50,50,255},32);
            F.AddText(245,325,"Host R / Restart: fresh run",White,16);
        }
    }
private:
    std::string ReadinessText() const {
        const std::string Jump=Player.OnWall?"wall jump":(Player.OnGround?"ground jump":(Player.DoubleJump?"air jump ready":"air jump used"));
        const std::string Spin=Player.Spinning>0?"spinning":(Player.SpinCooldown>0?"spin wait "+std::to_string(Player.SpinCooldown)
            :(!Player.OnGround?"spin needs ground":"spin ready"));
        const std::string AttackState=Attacks.size()>=MaxAttacks?"attacks full":(Player.AttackCooldown>0?"sword/star wait "+std::to_string(Player.AttackCooldown):"sword/star ready");
        return Jump+" | "+Spin+" | "+AttackState;
    }
};
}} // daedalus::desktop
