// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <limits>
#include <sstream>

namespace daedalus { namespace desktop {
namespace shooter_detail {
inline constexpr double Pi = 3.14159265358979323846;
inline constexpr Color Red{255,50,50,255}, Cyan{0,255,255,255}, Yellow{255,255,0,255},
    Orange{255,165,0,255}, Purple{180,0,255,255}, Gold{255,215,0,255}, Pink{255,80,200,255},
    LightBlue{100,180,255,255}, DarkRed{180,0,0,255}, Green{50,255,50,255};
inline double Radians(double Degrees) { return Degrees*Pi/180.0; }
inline void Wrap(double& Value,double Limit) { if(Value<0) Value=Limit; else if(Value>Limit) Value=0; }
inline double DeadAxis(double Value) { Value=Axis(Value); return std::abs(Value)>0.15 ? Value : 0; }
inline int RoundEven(double Value) {
    const double Low=std::floor(Value), Fraction=Value-Low;
    return static_cast<int>(Low)+(Fraction>0.5 || (Fraction==0.5 && static_cast<int>(Low)%2!=0) ? 1 : 0);
}
template<class T,class Predicate> inline void Remove(std::vector<T>& Values,Predicate Dead) {
    Values.erase(std::remove_if(Values.begin(),Values.end(),Dead),Values.end());
}
template<class T> inline bool Append(std::vector<T>& Values,const T& Value,std::size_t Limit) {
    if(Values.size()>=Limit) return false;
    Values.push_back(Value); return true;
}
inline void AddScore(std::int64_t& Score,int Points) {
    Score=std::min<std::int64_t>(Score+Points,1000000000000LL);
}
inline void Outline(Frame& F,const std::vector<Vec>& Points,Color Tint,double Width=2) {
    for(std::size_t Index=0;Index<Points.size();++Index) {
        const Vec A=Points[Index],B=Points[(Index+1)%Points.size()]; F.AddLine(A.X,A.Y,B.X,B.Y,Tint,Width);
    }
}
inline void Polygon(Frame& F,const std::vector<Vec>& Points,Color Tint) {
    for(std::size_t Index=1;Index+1<Points.size();++Index) F.AddTriangle(Points[0],Points[Index],Points[Index+1],Tint);
}
inline void Ellipse(Frame& F,double X,double Y,double Rx,double Ry,Color Tint,bool Filled=false) {
    std::vector<Vec> Points;
    for(int N=0;N<24;++N) {const double A=N*Pi/12;Points.push_back({X+Rx*std::cos(A),Y+Ry*std::sin(A)});}
    if(Filled) Polygon(F,Points,Tint);else Outline(F,Points,Tint);
}
struct Star { double X=0,Y=0,Speed=1; };
template<std::size_t N> inline void MakeStars(std::array<Star,N>& Stars,Random& R) {
    for(auto& S:Stars) S={static_cast<double>(R.Int(0,800)),static_cast<double>(R.Int(0,600)),R.Between(0.5,3)};
}
} // shooter_detail

// Latest Desktop asteroids_pygame_ce.py: ship inertia, splitting rocks and UFOs.
// One Step is one source 60 Hz frame; host owns elapsed-time accumulation/input.
class AsteroidsGame final : public Game {
    friend struct AsteroidsTestAccess;
public:
    struct Ship {
        double X=400,Y=300,Angle=-90,Vx=0,Vy=0;
        bool Thrust=false;
        int Cooldown=0;
        bool Braking=false;
        void Update(const Input& I,int HatX=0,int HatY=0) {
            if(I.Left) Angle-=5;
            if(I.Right) Angle+=5;
            Angle+=shooter_detail::DeadAxis(I.AxisX)*6;
            HatX+=(I.PadRight?1:0)-(I.PadLeft?1:0);
            HatY+=(I.PadUp?1:0)-(I.PadDown?1:0);
            if(HatX<0) Angle-=5;else if(HatX>0) Angle+=5;
            Braking=I.Action || I.ActionPressed;
            Thrust=!Braking && (I.Up || shooter_detail::DeadAxis(I.AxisY)<-0.4 || HatY>0);
            if(Thrust) { const double R=shooter_detail::Radians(Angle); Vx+=std::cos(R)*0.15; Vy+=std::sin(R)*0.15; }
            Vx*=0.985; Vy*=0.985;
            if(Braking) {
                Vx*=0.8;Vy*=0.8;
                if(std::abs(Vx)<0.02) Vx=0;
                if(std::abs(Vy)<0.02) Vy=0;
            }
            X+=Vx; Y+=Vy;
            shooter_detail::Wrap(X,800); shooter_detail::Wrap(Y,600);
            if(Cooldown>0) --Cooldown;
            // Keep trig arguments precise through very long sessions; equivalent rotation.
            if(std::abs(Angle)>360000) Angle=std::fmod(Angle,360.0);
        }
    };
    struct Bullet {
        double X=0,Y=0,Vx=0,Vy=0;
        int Life=45;
        bool PlayerOwned=true;
        static Bullet At(double SpawnX,double SpawnY,double Angle,bool Owner=true) {
            const double R=shooter_detail::Radians(Angle); return {SpawnX,SpawnY,std::cos(R)*8,std::sin(R)*8,45,Owner};
        }
        void Update() { X+=Vx; Y+=Vy; --Life; shooter_detail::Wrap(X,800); shooter_detail::Wrap(Y,600); }
    };
    struct Rock {
        double X=0,Y=0,Vx=0,Vy=0,Angle=0,Rotation=0;
        int Size=3;
        std::array<double,8> Shape{{1,1,1,1,1,1,1,1}};
        double Radius() const { return Size*12.0; }
        int SplitCount() const { return Size>1 ? 2 : 0; }
        void Update() { X+=Vx; Y+=Vy; Angle+=Rotation; shooter_detail::Wrap(X,800); shooter_detail::Wrap(Y,600); }
    };
    struct Ufo { double X=0,Y=0,Vx=2; int ShootTimer=60; };
    static constexpr std::size_t MaxBullets=128,MaxRocks=256,MaxUfos=8;
    static int RockPoints(int Size) { return 100*Size; }
    static bool Shoot(Ship& S,Bullet& Out) {
        if(S.Cooldown!=0) return false;
        S.Cooldown=8; const double R=shooter_detail::Radians(S.Angle);
        Out=Bullet::At(S.X+15*std::cos(R),S.Y+15*std::sin(R),S.Angle); return true;
    }
    const Ship& GetShip() const { return Player; }
    int GetLevel() const { return Level; }
    std::size_t GetRockCount() const { return Rocks.size(); }
    std::size_t GetUfoCount() const { return Ufos.size(); }
    int GetProtectionFrames() const { return RespawnGrace; }
    bool IsFireReady() const { return Option!=2 && !Over && !Won && Bullets.size()<MaxBullets && Player.Cooldown==0; }
    int GetDockedBeaconCount() const { return FlightStage; }
    std::size_t EntityCount() const { return Rocks.size()+Bullets.size()+Ufos.size(); }
    void Reset(std::uint32_t Seed) override {
        SessionSeed=Seed;
        Rng.Seed(Seed); Player=Ship{}; Score=0; Lives=3; Level=1; Over=false; Won=false; RespawnGrace=0; UfoTimer=300;
        Bullets.clear(); Ufos.clear(); Rocks.clear(); shooter_detail::MakeStars(Stars,Rng);
        FlightStage=0;if(Option!=2) CreateRocks(6);
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>2) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    bool SourceControllerButton(int Button) override {
        if((Over || Won) && (Button==0 || Button==1)) {Reset(SessionSeed);return true;}
        return false;
    }
    bool SourceKeyDown(int Key) override {
        if((Over || Won) && (Key==6 || Key==7)) {Reset(SessionSeed);return true;}
        return false;
    }
    void Step(const Input& I) override {
        if(Over || Won) return;
        if(Option==2) {
            Player.Update(I);
            const Vec Goal=FlightBeacons[static_cast<std::size_t>(FlightStage)];
            if(Player.Braking && Player.Vx==0 && Player.Vy==0 && Distance(Player.X,Player.Y,Goal.X,Goal.Y)<28) {
                ++FlightStage;Won=FlightStage==static_cast<int>(FlightBeacons.size());
            }
            return; // Empty practice space never enters firing, UFOs or wave progression.
        }
        if(RespawnGrace>0) --RespawnGrace;
        // Source KEYDOWN/JOYBUTTONDOWN can shoot before ship.update; held fire after.
        if(I.FirePressed) Fire();
        Player.Update(I);
        if(I.Fire) Fire();
        for(auto& B:Bullets) B.Update();
        shooter_detail::Remove(Bullets,[](const Bullet& B){return B.Life<=0;});
        for(auto& A:Rocks) A.Update();
        --UfoTimer;
        if(UfoTimer<=0 && Rng.Unit()<0.3) {
            const bool Left=Rng.Int(0,1)==0;
            shooter_detail::Append(Ufos,Ufo{Left?0.0:800.0,static_cast<double>(Rng.Int(50,550)),Left?2.0:-2.0,Rng.Int(40,80)},MaxUfos);
            UfoTimer=Rng.Int(400,700);
        }
        for(auto& U:Ufos) {
            U.X+=U.Vx; --U.ShootTimer;
            if(U.ShootTimer<=0) {
                U.ShootTimer=Rng.Int(50,90);
                shooter_detail::Append(Bullets,Bullet::At(U.X,U.Y,std::atan2(Player.Y-U.Y,Player.X-U.X)*180/shooter_detail::Pi,false),MaxBullets);
            }
        }
        shooter_detail::Remove(Ufos,[](const Ufo& U){return U.X<-30 || U.X>830;});
        if(RespawnGrace==0) {
            for(const auto& A:Rocks) if(Distance(Player.X,Player.Y,A.X,A.Y)<A.Radius()+10) { LoseLife(true); break; }
        }
        // Split after the collision pass so children cannot be hit again by the same bullet.
        std::vector<Rock> Splits;
        for(auto& A:Rocks) {
            if(A.Size<=0) continue;
            for(auto& B:Bullets) {
                if(B.Life<=0 || !B.PlayerOwned) continue;
                if(Distance(B.X,B.Y,A.X,A.Y)<A.Radius()) {
                    B.Life=0; shooter_detail::AddScore(Score,RockPoints(A.Size));
                    for(int N=0;N<A.SplitCount();++N) shooter_detail::Append(Splits,MakeRock(A.X,A.Y,A.Size-1),MaxRocks);
                    A.Size=0; break;
                }
            }
        }
        shooter_detail::Remove(Rocks,[](const Rock& A){return A.Size<=0;});
        for(const auto& A:Splits) shooter_detail::Append(Rocks,A,MaxRocks);
        for(auto& U:Ufos) for(auto& B:Bullets) {
            if(B.Life>0 && B.PlayerOwned && Distance(B.X,B.Y,U.X,U.Y)<15) {
                B.Life=0; U.X=-100; shooter_detail::AddScore(Score,500); break;
            }
        }
        if(!Over && RespawnGrace==0) for(auto& B:Bullets) {
            if(B.Life>0 && !B.PlayerOwned && Distance(B.X,B.Y,Player.X,Player.Y)<12) { B.Life=0; LoseLife(false); break; }
        }
        shooter_detail::Remove(Ufos,[](const Ufo& U){return U.X<-30 || U.X>830;});
        shooter_detail::Remove(Bullets,[](const Bullet& B){return B.Life<=0;});
        if(!Over && Rocks.empty()) {
            if(Option==1 && Level>=3) {Won=true;return;}
            Level=std::min(Level+1,1000000); Player=Ship{}; Bullets.clear(); Ufos.clear(); UfoTimer=Rng.Int(300,600);
            CreateRocks(std::min(4+Level,32)); RespawnGrace=60;
        }
    }
    void Render(Frame& F) const override {
        using namespace shooter_detail;
        F.Clear(); for(const auto& S:Stars) F.AddCircle(S.X,S.Y,1,White);
        if(Option==2) for(std::size_t N=0;N<FlightBeacons.size();++N) {
            const Vec Goal=FlightBeacons[N];const int Index=static_cast<int>(N);
            const Color Tint=Index<FlightStage?Green:(Index==FlightStage?Gold:Color{75,95,125,255});
            Ellipse(F,Goal.X,Goal.Y,Index==FlightStage?28:16,Index==FlightStage?28:16,Tint);
            F.AddText(Goal.X-5,Goal.Y-9,std::to_string(Index+1),Tint,16);
        }
        if(!Over && (RespawnGrace==0 || (RespawnGrace/4)%2!=0)) {
            const double R=Radians(Player.Angle);
            Outline(F,{{Player.X+15*std::cos(R),Player.Y+15*std::sin(R)},
                {Player.X+10*std::cos(R+2.5),Player.Y+10*std::sin(R+2.5)},
                {Player.X+10*std::cos(R-2.5),Player.Y+10*std::sin(R-2.5)}},White);
            if(Player.Braking) for(int Side:{-1,1}) {
                const double Sx=-std::sin(R)*Side*16,Sy=std::cos(R)*Side*16;
                F.AddLine(Player.X+Sx-8*std::cos(R),Player.Y+Sy-8*std::sin(R),
                    Player.X+Sx+4*std::cos(R),Player.Y+Sy+4*std::sin(R),LightBlue,3);
            }
            if(Player.Thrust) F.AddTriangle({Player.X-12*std::cos(R),Player.Y-12*std::sin(R)},
                {Player.X-4*std::cos(R+2.2),Player.Y-4*std::sin(R+2.2)},
                {Player.X-4*std::cos(R-2.2),Player.Y-4*std::sin(R-2.2)},Yellow);
        }
        if(Option==2) { RenderFlightPractice(F);return; }
        for(const auto& A:Rocks) {
            std::vector<Vec> Points;
            for(int N=0;N<8;++N) { const double R=Radians(A.Angle+N*45); Points.push_back({A.X+A.Radius()*A.Shape[N]*std::cos(R),A.Y+A.Radius()*A.Shape[N]*std::sin(R)}); }
            Outline(F,Points,{180,180,180,255});
        }
        for(const auto& B:Bullets) F.AddCircle(B.X,B.Y,3,B.PlayerOwned?White:Red);
        for(const auto& U:Ufos) { const Color UfoGreen{80,255,80,255};Ellipse(F,U.X,U.Y,15,6,UfoGreen);Outline(F,{{U.X-8,U.Y-12},{U.X+8,U.Y-12},{U.X+8,U.Y-4},{U.X-8,U.Y-4}},UfoGreen); }
        F.AddText(30,15,"SCORE: "+std::to_string(Score)); F.AddText(660,15,"LIVES: "+std::to_string(Lives));
        F.AddText(355,15,std::string(Option==1?"WAVE: ":"LEVEL: ")+std::to_string(Level)+(Option==1?"/3":""),Yellow,18);
        F.AddText(30,42,"ROCKS: "+std::to_string(GetRockCount())+"   UFOs: "+std::to_string(GetUfoCount()),White,16);
        F.AddText(30,65,"FIRE: "+FireNote(),IsFireReady()?Green:Yellow,15);
        if(!Over && !Won) {
            if(Player.Braking) F.AddText(420,42,"BRAKING",LightBlue,17);
            F.AddText(420,65,ProtectionNote(),RespawnGrace>0?Cyan:White,15);
            if(RespawnGrace>0) Ellipse(F,Player.X,Player.Y,23,23,Cyan);
        }
        F.AddText(30,548,Option==1?"Voyage: clear all rocks in three waves. Larger rocks split into two."
            :"Clear all rocks to advance; larger rocks split into two.",White,15);
        F.AddText(30,572,"Left/Right: turn   Up: thrust   K/LT: brake   Space/pad: fire",White,15);
        if(Over || Won) {
            F.AddRect(170,225,460,115,{15,20,35,235});
            F.AddText(Won?210:285,238,Won?"THREE WAVES CLEARED!":"GAME OVER",Won?Green:Red,Won?30:40);
            F.AddText(200,290,"Wave "+std::to_string(Level)+"   Final score "+std::to_string(Score),White,18);
            F.AddText(185,315,"Pad A/Start, Enter/Space or R/Restart: retry",Cyan,17);
        }
    }
    Status GetStatus() const override {
        if(Option==2) return {Score,Lives,false,Won,Won?
            "Flight practice complete; pad A/Start, Enter/Space or R/Restart to retry":
            "Flight practice: docked "+std::to_string(FlightStage)+"/3; stop under braking inside the gold ring. Turn / thrust / K-LT brake; edges wrap."};
        if(Won) return {Score,Lives,false,true,"Three-wave voyage complete; pad A/Start, Enter/Space or R/Restart to retry"};
        if(Over) return {Score,Lives,true,false,"Game over at wave "+std::to_string(Level)+"; pad A/Start, Enter/Space or R/Restart to retry"};
        return {Score,Lives,false,false,"Wave "+std::to_string(Level)+(Option==1?"/3 voyage":"")+"; rocks "+std::to_string(GetRockCount())+"; UFOs "+std::to_string(GetUfoCount())+
            "; "+ProtectionNote()+"; fire "+FireNote()+(Player.Braking?"; BRAKING":"")+"; turn / thrust / K-LT brake / hold fire"};
    }
private:
    Random Rng; Ship Player; std::vector<Rock> Rocks; std::vector<Bullet> Bullets; std::vector<Ufo> Ufos;
    std::array<shooter_detail::Star,80> Stars{};
    std::uint32_t SessionSeed=730;
    std::int64_t Score=0; int Lives=3,Level=1,UfoTimer=300,RespawnGrace=0,Option=0,FlightStage=0; bool Over=false,Won=false;
    inline static constexpr std::array<Vec,3> FlightBeacons{{{400,180},{650,180},{100,420}}};
    void RenderFlightPractice(Frame& F) const {
        using namespace shooter_detail;
        F.AddText(30,15,"FLIGHT PRACTICE",White,24);
        F.AddText(610,15,"DOCKED "+std::to_string(FlightStage)+"/3",Gold,22);
        F.AddText(30,52,Player.Braking?(Player.Vx==0 && Player.Vy==0?"STOPPED":"BRAKING"):"Find the next gold ring",LightBlue,17);
        F.AddText(30,548,"Stop under braking inside the GOLD ring. Edges wrap.",White,15);
        F.AddText(30,572,"Left/Right, stick or hat: turn | Up: thrust | K/LT: brake",White,15);
        if(Won) {
            F.AddRect(170,225,460,115,{15,20,35,235});
            F.AddText(215,248,"DOCKING COMPLETE!",Green,30);
            F.AddText(185,305,"Pad A/Start, Enter/Space or R/Restart: retry",Cyan,17);
        }
    }
    std::string ProtectionNote() const {
        // The source-style timer decrements before the next collision pass.
        if(RespawnGrace==1) return "PROTECTION EXPIRES NEXT LIVE STEP";
        return RespawnGrace>1?"PROTECTION TIMER: "+std::to_string(RespawnGrace):"COLLISIONS ACTIVE";
    }
    std::string FireNote() const {
        if(Over || Won) return "RUN ENDED";
        if(Bullets.size()>=MaxBullets) return "SHOT LIMIT";
        return Player.Cooldown>0?"COOLDOWN "+std::to_string(Player.Cooldown)+" STEPS":"READY";
    }
    void Fire() {
        if(Bullets.size()>=MaxBullets) return;
        Bullet B;
        if(Shoot(Player,B)) Bullets.push_back(B);
    }
    Rock MakeRock(double X,double Y,int Size) {
        Rock A; A.X=X; A.Y=Y; A.Size=Size; A.Vx=Rng.Between(-1.5,1.5); A.Vy=Rng.Between(-1.5,1.5);
        A.Angle=Rng.Int(0,360); A.Rotation=Rng.Between(-2,2); for(auto& V:A.Shape) V=Rng.Between(0.75,1.25); return A;
    }
    void CreateRocks(int Count) {
        for(int N=0;N<Count;++N) {
            double X=50,Y=50;
            // The original uses unbounded rejection sampling; deterministic fallback is safe.
            for(int Attempt=0;Attempt<64;++Attempt) { X=Rng.Int(50,750); Y=Rng.Int(50,550); if(Distance(X,Y,400,300)>120) break; if(Attempt==63){X=50;Y=50;} }
            shooter_detail::Append(Rocks,MakeRock(X,Y,3),MaxRocks);
        }
    }
    void LoseLife(bool ClearBullets) {
        --Lives; if(Lives<=0) { Lives=0; Over=true; return; }
        Player=Ship{};
        if(ClearBullets) Bullets.clear();
        RespawnGrace=60;
    }
};

// Source Sega-themed horizontal shooter. No enemy shots exist in the source.
// Native boss hit/engagement and held fire repair otherwise unreachable victory.
class SegaShooterGame final : public Game {
    friend struct SegaTestAccess;
public:
    struct Bullet { double X=0,Y=0,Vx=10,Vy=0; bool Alive=true; void Update(){X+=Vx;Y+=Vy;} };
    struct Player {
        double X=150,Y=300,Speed=5;
        int Cooldown=0,Power=1,Lives=3,Invincible=0;
        void Update(const Input& I) {
            double Dx=0,Dy=0;
            // Match the existing cabinet's merged directions for direct core input.
            if(I.Left || I.PadLeft) Dx=-1;
            if(I.Right || I.PadRight) Dx=1;
            if(I.Up || I.PadUp) Dy=-1;
            if(I.Down || I.PadDown) Dy=1;
            const double Sx=shooter_detail::DeadAxis(I.AxisX),Sy=shooter_detail::DeadAxis(I.AxisY);
            if(std::abs(Sx)>0.2 || std::abs(Sy)>0.2) {Dx=Sx;Dy=Sy;}
            X=Clamp(X+Dx*Speed,30,750); Y=Clamp(Y+Dy*Speed,20,580);
            if(Cooldown>0) --Cooldown;
            if(Invincible>0) --Invincible;
        }
        std::vector<Bullet> Shoot() {
            if(Cooldown!=0) return {};
            Cooldown=6;
            if(Power==1) return {{X+20,Y,10,0,true}};
            if(Power==2) return {{X+20,Y-5,10,0,true},{X+20,Y+5,10,0,true}};
            return {{X+20,Y,10,0,true},{X+18,Y-8,9,-1.5,true},{X+18,Y+8,9,1.5,true}};
        }
    };
    enum class PowerKind { Power,Speed,Life };
    struct Powerup { double X=0,Y=0; PowerKind Kind=PowerKind::Power; bool Alive=true; void Update(){X-=2.5;if(X<-20) Alive=false;} };
    struct Enemy {
        double X=820,Y=300,Speed=3;
        int Health=2,ShootTimer=60;
        bool Chaser=false,Alive=true;
        void Update(const Player& P) {
            X-=Speed; Y+=Chaser?(P.Y-Y)*0.03:std::sin(X/30)*1.5; if(ShootTimer>0) --ShootTimer;
        }
    };
    static constexpr std::size_t MaxBullets=256,MaxEnemies=64,MaxPowerups=32;
    static void ApplyPower(Player& P,PowerKind Kind) {
        if(Kind==PowerKind::Power) P.Power=std::min(3,P.Power+1);
        else if(Kind==PowerKind::Speed) P.Speed=std::min(8.0,P.Speed+1);
        else P.Lives=std::min(5,P.Lives+1);
    }
    const Player& GetPlayer() const { return Pilot; }
    bool HasBoss() const { return BossActive; }
    int GetBossHealth() const { return BossActive?std::max(0,Boss.Health):0; }
    std::size_t GetEnemyCount() const { return Enemies.size(); }
    std::size_t GetPickupCount() const { return Powerups.size(); }
    bool IsFireReady() const { return !Over && !Won && Bullets.size()+3<=MaxBullets && Pilot.Cooldown==0; }
    std::size_t EntityCount() const { return Bullets.size()+Enemies.size()+Powerups.size()+(BossActive?1:0); }
    void Reset(std::uint32_t Seed) override {
        SessionSeed=Seed;
        Rng.Seed(Seed); Pilot=Player{}; Score=0; SpawnTimer=0; Over=false; Won=false; BossActive=false; Boss=Enemy{};
        Bullets.clear(); Enemies.clear(); Powerups.clear(); shooter_detail::MakeStars(Stars,Rng);
        if(Option==1) StartBoss();
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    bool SourceControllerButton(int Button) override {
        if((Over || Won) && (Button==0 || Button==1)) {Reset(SessionSeed);return true;}
        return false;
    }
    bool SourceKeyDown(int Key) override {
        if((Over || Won) && (Key==6 || Key==7)) {Reset(SessionSeed);return true;}
        return false;
    }
    void Step(const Input& I) override {
        if(Over || Won) return;
        if(I.FirePressed) Fire();
        Pilot.Update(I);
        if(I.Fire) Fire();
        for(auto& S:Stars) { S.X-=S.Speed; if(S.X<0) S.X+=800; }
        --SpawnTimer;
        if(SpawnTimer<=0) {
            const bool Chase=Rng.Int(0,1)!=0;
            shooter_detail::Append(Enemies,Enemy{820,static_cast<double>(Rng.Int(50,550)),Rng.Between(2.5,4),Chase?4:2,Rng.Int(40,80),Chase,true},MaxEnemies);
            SpawnTimer=Rng.Int(25,45);
        }
        for(auto& E:Enemies) { E.Update(Pilot); if(E.X<-20) E.Alive=false; }
        for(auto& B:Bullets) { B.Update(); if(B.X>820 || B.Y<-20 || B.Y>620) B.Alive=false; }
        for(auto& P:Powerups) P.Update();
        for(auto& B:Bullets) {
            if(!B.Alive) continue;
            for(auto& E:Enemies) if(E.Alive && Distance(B.X,B.Y,E.X,E.Y)<18) {
                B.Alive=false; if(--E.Health<=0) {
                    E.Alive=false; shooter_detail::AddScore(Score,100);
                    if(Rng.Unit()<0.25) shooter_detail::Append(Powerups,Powerup{E.X,E.Y,static_cast<PowerKind>(Rng.Int(0,2)),true},MaxPowerups);
                }
                break; // A single projectile cannot damage a second overlapping enemy.
            }
            if(B.Alive && BossActive && Distance(B.X,B.Y,Boss.X,Boss.Y)<18) { B.Alive=false; --Boss.Health; }
        }
        if(Pilot.Invincible==0) {
            for(auto& E:Enemies) if(E.Alive && Distance(Pilot.X,Pilot.Y,E.X,E.Y)<22) { E.Alive=false; Damage(); break; }
            if(Pilot.Invincible==0 && BossActive && Distance(Pilot.X,Pilot.Y,Boss.X,Boss.Y)<22) Damage();
        }
        // Defeat blocks pickups; the existing boss outcome still settles below, including a mutual loss.
        if(!Over) {
            for(auto& P:Powerups) if(P.Alive && Distance(Pilot.X,Pilot.Y,P.X,P.Y)<18) {ApplyPower(Pilot,P.Kind);P.Alive=false;}
        }
        if(Score>=1500 && !BossActive && !Won) StartBoss();
        if(BossActive) {
            Boss.Update(Pilot); Boss.X=std::max(600.0,Boss.X);
            if(Boss.Health<=0) { BossActive=false; shooter_detail::AddScore(Score,500); Won=true; }
        }
        shooter_detail::Remove(Enemies,[](const Enemy& E){return !E.Alive;});
        shooter_detail::Remove(Bullets,[](const Bullet& B){return !B.Alive;});
        shooter_detail::Remove(Powerups,[](const Powerup& P){return !P.Alive;});
    }
    void Render(Frame& F) const override {
        using namespace shooter_detail;
        F.Clear(800,600,{0,0,40,255}); for(const auto& S:Stars) F.AddCircle(S.X,S.Y,S.Speed,White);
        if(Pilot.Invincible==0 || (Pilot.Invincible/4)%2!=0) {
            F.AddTriangle({Pilot.X+18,Pilot.Y},{Pilot.X-10,Pilot.Y-12},{Pilot.X-10,Pilot.Y+12},{100,200,255,255});
            F.AddCircle(Pilot.X+1,Pilot.Y,6,{200,255,255,255});
            F.AddTriangle({Pilot.X-12,Pilot.Y},{Pilot.X-22,Pilot.Y-6},{Pilot.X-22,Pilot.Y+6},{255,200,50,255});
        }
        auto DrawEnemy=[&F](const Enemy& E){ if(E.Chaser) F.AddTriangle({E.X+10,E.Y},{E.X-12,E.Y-10},{E.X-12,E.Y+10},{255,100,100,255}); else { Ellipse(F,E.X,E.Y,12,8,{255,80,80,255},true);F.AddCircle(E.X+5,E.Y,5,{255,150,150,255}); } };
        for(const auto& E:Enemies) {
            DrawEnemy(E);
            const int MaxHealth=E.Chaser?4:2;
            const double Top=E.Y-(E.Chaser?23:21);
            F.AddRect(E.X-MaxHealth*4-1,Top,MaxHealth*8+2,9,{0,0,40,255});
            for(int N=0;N<MaxHealth;++N) F.AddRect(E.X-MaxHealth*4+1+N*8,Top+2,6,5,
                N<E.Health?Color{255,215,100,255}:Color{70,70,90,255});
        }
        for(const auto& B:Bullets) {F.AddCircle(B.X,B.Y,4,{255,255,100,255});F.AddCircle(B.X,B.Y,2,White);}
        for(const auto& P:Powerups) {
            if(P.Kind==PowerKind::Speed) Polygon(F,{{P.X,P.Y-8},{P.X+8,P.Y},{P.X,P.Y+8},{P.X-8,P.Y}},Green);
            else { F.AddCircle(P.X,P.Y,P.Kind==PowerKind::Power?8:7,P.Kind==PowerKind::Power?Yellow:Red);F.AddCircle(P.X,P.Y,3,White); }
            F.AddText(Clamp(P.X-18,4,748),Clamp(P.Y+10,42,532),PickupName(P.Kind),White,13);
        }
        if(BossActive) {DrawEnemy(Boss);F.AddRect(Boss.X-30,Boss.Y-40,60,6,Red);F.AddRect(Boss.X-30,Boss.Y-40,60*Clamp(Boss.Health/20.0,0,1),6,Green);}
        F.AddText(30,20,"SCORE: "+std::to_string(Score)); F.AddText(660,20,"LIVES: "+std::to_string(Pilot.Lives),Red);
        F.AddText(350,20,"POWER: "+std::to_string(Pilot.Power),Yellow,18);
        F.AddText(30,45,std::string(Option==1?"REHEARSAL | ENEMIES: ":"ENEMIES: ")+std::to_string(GetEnemyCount())+"   PICKUPS: "+std::to_string(GetPickupCount()),White,15);
        F.AddText(420,45,BossNote(),BossActive?Red:Yellow,15);
        F.AddText(30,67,"FIRE: "+FireNote()+"   SHOT: "+ShotName(),IsFireReady()?Green:Yellow,15);
        F.AddText(30,89,"SPEED: "+std::to_string(static_cast<int>(Pilot.Speed))+"/8   "+ProtectionNote(),Cyan,15);
        F.AddText(30,548,"POWER +1 (max 3)   SPEED +1 (max 8)   LIFE +1 (max 5)",White,15);
        F.AddText(30,572,"WASD/arrows, D-pad or stick: move   Space/J/Z/pad: hold fire",White,15);
        if(Over || Won) {
            F.AddRect(145,225,510,120,{15,20,40,235});
            const std::string Result=Over?(Won?"BOSS DOWN / SHIP LOST":(Option==1?"REHEARSAL ENDED":"GAME OVER"))
                :(Option==1?"REHEARSAL COMPLETE!":"BOSS DEFEATED!");
            F.AddText(175,238,Result,Over?Red:Green,30);
            F.AddText(175,285,"Final score: "+std::to_string(Score),White,20);
            F.AddText(175,315,"Pad A/Start, Enter/Space or R/Restart: retry",Cyan,17);
        }
    }
    Status GetStatus() const override {
        const std::string Mode=Option==1?"Boss rehearsal; ":"";
        if(Over || Won) return {Score,Pilot.Lives,Over,Won,Mode+(Over?(Won?"Boss defeated; ship lost":"Game over"):"Boss defeated")+
            std::string("; final score ")+std::to_string(Score)+"; pad A/Start, Enter/Space or R/Restart to retry"};
        return {Score,Pilot.Lives,false,false,Mode+BossNote()+"; enemies "+std::to_string(GetEnemyCount())+"; pickups "+std::to_string(GetPickupCount())+
            "; "+ShotName()+"; speed "+std::to_string(static_cast<int>(Pilot.Speed))+"/8; "+ProtectionNote()+"; fire "+FireNote()};
    }
private:
    Random Rng; Player Pilot; Enemy Boss; std::vector<Bullet> Bullets; std::vector<Enemy> Enemies; std::vector<Powerup> Powerups;
    std::uint32_t SessionSeed=730;
    int Option=0;
    std::array<shooter_detail::Star,80> Stars{};
    std::int64_t Score=0; int SpawnTimer=0; bool Over=false,Won=false,BossActive=false;
    void StartBoss() { Boss={750,300,1.5,20,60,true,true};BossActive=true; }
    static const char* PickupName(PowerKind Kind) { return Kind==PowerKind::Power?"POWER":(Kind==PowerKind::Speed?"SPEED":"LIFE"); }
    std::string ShotName() const { return Pilot.Power==1?"NORMAL":(Pilot.Power==2?"DOUBLE":"SPREAD"); }
    std::string ProtectionNote() const {
        if(Over || Won) return "RUN ENDED";
        if(Pilot.Invincible==1) return "PROTECTION EXPIRES NEXT LIVE STEP";
        return Pilot.Invincible>1?"PROTECTION TIMER: "+std::to_string(Pilot.Invincible):"COLLISIONS ACTIVE";
    }
    std::string BossNote() const {
        if(BossActive) return "BOSS HP: "+std::to_string(GetBossHealth())+"/20";
        if(Won) return "BOSS DEFEATED";
        return "BOSS AT 1500: "+std::to_string(std::max<std::int64_t>(0,1500-Score))+" TO GO";
    }
    std::string FireNote() const {
        if(Over || Won) return "RUN ENDED";
        if(Bullets.size()+3>MaxBullets) return "SHOT LIMIT";
        return Pilot.Cooldown>0?"COOLDOWN "+std::to_string(Pilot.Cooldown)+" STEPS":"READY";
    }
    void Fire() {
        if(Bullets.size()+3>MaxBullets) return;
        for(const auto& B:Pilot.Shoot()) Bullets.push_back(B);
    }
    void Damage() {Pilot.Lives=std::max(0,Pilot.Lives-1);Pilot.Invincible=60;if(Pilot.Lives==0) Over=true;}
};

// Latest star_shootergpt1_fixed.py. Difficulty, escort bonuses, dive types and
// multi-stage bosses are separate explicit rules so the host does not duplicate them.
class StarShooterGame final : public Game {
    friend struct StarTerminalTestAccess;
public:
    enum class Difficulty { Easy=0,Medium=1,Hard=2 };
    struct DifficultyConfig { double EnemySpeed,EnemyHp,ShootDelay,DiveChance,BossHp; int SpawnRate,Lives; };
    static DifficultyConfig Config(Difficulty D) {
        if(D==Difficulty::Easy) return {0.60,0.55,1.80,0.40,0.50,135,5};
        if(D==Difficulty::Medium) return {0.80,0.75,1.30,0.70,0.75,110,4};
        return {1,1,1,1,1,90,3};
    }
    struct Bullet {
        double X=0,Y=0,Dx=0,Dy=0; Color Tint=shooter_detail::Cyan;
        bool Big=false,BossOwned=false,PlayerOwned=true,Alive=true;
        void Update() {X+=Dx;Y+=Dy;if(!(X>-20 && X<820 && Y>-20 && Y<620)) Alive=false;}
        Rect Bounds() const {const double S=Big?7:4;return {std::trunc(X-S),std::trunc(Y-S),S*2,S*2};}
    };
    struct Player {
        double X=400,Y=500;
        int Lives=3,Cooldown=0,Invincible=0;
        bool Shield=false,Triple=false,SpeedBoost=false;
        void Update(const Input& I) {
            double Dx=shooter_detail::DeadAxis(I.AxisX),Dy=shooter_detail::DeadAxis(I.AxisY);
            // Match the existing cabinet merge; digital directions still override the stick.
            if(I.Left || I.PadLeft) Dx=-1;
            if(I.Right || I.PadRight) Dx=1;
            if(I.Up || I.PadUp) Dy=-1;
            if(I.Down || I.PadDown) Dy=1;
            const double Speed=6*(SpeedBoost?1.6:1.0); X=Clamp(X+Dx*Speed,20,780);Y=Clamp(Y+Dy*Speed,20,580);
            if(Cooldown>0) --Cooldown;
            if(Invincible>0) --Invincible;
        }
        std::vector<Bullet> Shoot() {
            if(Cooldown!=0) return {};
            Cooldown=10;
            if(Triple) return {{X-14,Y-10,-1,-13},{X,Y-14,0,-14},{X+14,Y-10,1,-13}};
            return {{X-12,Y-10,0,-13},{X+12,Y-10,0,-13}};
        }
        static bool WantsToShoot(bool Space,double Trigger) {return Space || (std::isfinite(Trigger) && Trigger>0.5);}
        bool Hit() {if(Shield){Shield=false;Invincible=60;return false;}--Lives;Invincible=90;return Lives<=0;}
        void ResetPowerups() {Shield=false;Triple=false;SpeedBoost=false;}
        Rect Bounds() const {return {std::trunc(X-12),std::trunc(Y-18),24,36};}
    };
    enum class EnemyKind { Bee=0,Butterfly=1,Cruiser=2 };
    enum class EnemyState { Descend,Dive };
    struct EnemyData { Color Tint,Explosion; int Size,Hp; double SpeedLow,SpeedHigh; int BasePoints,DivePoints,ShootLow,ShootHigh; double DiveSpeed; };
    static EnemyData Data(EnemyKind K) {
        using namespace shooter_detail;
        if(K==EnemyKind::Bee) return {Red,Orange,12,1,2,3.5,50,100,80,180,5.5};
        if(K==EnemyKind::Butterfly) return {Purple,Pink,16,2,1.2,2.2,160,320,55,120,4.5};
        return {Gold,Yellow,20,3,0.8,1.6,300,300,35,75,0};
    }
    struct Enemy {
        EnemyKind Kind=EnemyKind::Bee; EnemyState State=EnemyState::Descend;
        double X=400,Y=-100,Speed=2,Sway=0,SwayTimer=0,DiveDx=0,DiveDy=0;
        int Hp=1,MaxHp=1,Size=12,ShootTimer=80,ShootLow=80,ShootHigh=180,DiveTimer=0;
        std::uint64_t Id=0,EscortFor=0; int EscortsRemaining=0; bool Alive=true;
        static Enemy Create(EnemyKind K,int Wave,Difficulty D,double SpawnX,double SpawnY,double SampleSpeed,double SampleSway,double SampleSwayTimer,int SampleTimer) {
            const EnemyData A=Data(K); const DifficultyConfig C=Config(D); Enemy E;
            E.Kind=K; E.X=SpawnX; E.Y=SpawnY; E.Size=A.Size;
            E.Speed=std::min(SampleSpeed*C.EnemySpeed+Wave*0.15*C.EnemySpeed,5.5);
            E.Hp=std::max(1,shooter_detail::RoundEven((A.Hp+Wave/3)*C.EnemyHp)); E.MaxHp=E.Hp;
            E.ShootLow=static_cast<int>(A.ShootLow*C.ShootDelay);E.ShootHigh=static_cast<int>(A.ShootHigh*C.ShootDelay);
            E.ShootTimer=SampleTimer;E.Sway=SampleSway;E.SwayTimer=SampleSwayTimer;return E;
        }
        void StartDive(double Px,double Py) {
            const double A=std::atan2(Py-Y,Px-X);State=EnemyState::Dive;DiveDx=std::cos(A)*Data(Kind).DiveSpeed;DiveDy=std::sin(A)*Data(Kind).DiveSpeed;DiveTimer=0;
        }
        void Update(double Px,double Py,int CurrentWave,Difficulty D,double DiveRoll,bool EscortLocked=false) {
            if(State==EnemyState::Descend) {
                Y+=Speed;SwayTimer+=0.05;X=Clamp(X+std::sin(SwayTimer)*Sway,20,780);if(Y>640) Alive=false;
                if(Kind!=EnemyKind::Cruiser && Y>60 && !EscortLocked) {
                    double Chance=(0.004+CurrentWave*0.0003)*Config(D).DiveChance;if(Kind==EnemyKind::Butterfly) Chance*=0.6;
                    if(DiveRoll<Chance) StartDive(Px,Py);
                }
            } else {
                ++DiveTimer;X+=DiveDx;if(Kind==EnemyKind::Butterfly){X+=std::sin(DiveTimer*0.22)*4;Y+=std::abs(DiveDy)+1.5;}else Y+=DiveDy;
                if(Y>640 || X<-60 || X>860) Alive=false;
            }
            if(ShootTimer>0) --ShootTimer;
        }
        std::vector<Bullet> Shoot(int NextTimer) {
            if(ShootTimer!=0) return {};
            ShootTimer=NextTimer; const EnemyData A=Data(Kind);
            auto Make=[&](double XOffset,double Dx,double Dy,bool Big=false){return Bullet{X+XOffset,Y+Size,Dx,Dy,A.Tint,Big,false,false,true};};
            if(Kind==EnemyKind::Bee) return {Make(0,0,6)};
            if(Kind==EnemyKind::Butterfly) return {Make(-6,-0.6,5.5),Make(6,0.6,5.5)};
            return {Make(-14,-0.9,5,true),Make(0,0,6,true),Make(14,0.9,5,true)};
        }
        int Points() const { const EnemyData A=Data(Kind);return Kind==EnemyKind::Cruiser?A.BasePoints*(EscortsRemaining==0?2:1):(State==EnemyState::Dive?A.DivePoints:A.BasePoints); }
        Rect Bounds() const {return {std::trunc(X-Size),std::trunc(Y-Size),Size*2.0,Size*2.0};}
    };
    enum class BossState { Entering,Pacing,Charging,Returning };
    enum class Pattern { Spread,Ring,Aimed };
    struct Boss {
        double X=400,Y=-100,BaseSpeed=1.8,Speed=1.8,ChargeDx=0,ChargeDy=0;
        int Hp=60,MaxHp=60,BaseShootRate=40,ShootRate=40,MoveTimer=0,Direction=1,ShootTimer=80,ChargeTimer=400,AlertTimer=0;
        Color BaseColor=shooter_detail::DarkRed,Tint=shooter_detail::DarkRed;
        Pattern FirePattern=Pattern::Spread; BossState State=BossState::Entering;
        bool Phase66=false,Phase33=false;
        static Boss Create(int Wave,Difficulty D,int SampleChargeTimer) {
            const int Index=std::max(0,std::min(Wave/5-1,2));Boss B;
            const int Hps[3]={60,100,150},Rates[3]={40,25,18};const double Speeds[3]={1.8,2.5,3.2};
            const Color Colors[3]={shooter_detail::DarkRed,shooter_detail::Purple,shooter_detail::Gold};
            B.MaxHp=std::max(1,shooter_detail::RoundEven(Hps[Index]*Config(D).BossHp));B.Hp=B.MaxHp;
            B.BaseSpeed=Speeds[Index];B.Speed=B.BaseSpeed;B.BaseShootRate=Rates[Index];B.ShootRate=B.BaseShootRate;
            B.BaseColor=Colors[Index];B.Tint=B.BaseColor;B.FirePattern=static_cast<Pattern>(Index);B.ChargeTimer=SampleChargeTimer;return B;
        }
        // Returns number of newly summoned bees. Threshold effects run once.
        int CheckPhases() {
            int Summon=0;const double Frac=static_cast<double>(Hp)/MaxHp;
            if(!Phase66 && Frac<=0.66) {
                Phase66=true;Speed=BaseSpeed*1.4;ShootRate=std::max(15,static_cast<int>(BaseShootRate*0.7));
                Tint=BaseColor.R==180 && BaseColor.G==0 && BaseColor.B==0?shooter_detail::Orange:
                    (BaseColor.B==255?shooter_detail::Pink:shooter_detail::Yellow);AlertTimer=130;Summon+=2;
            }
            if(!Phase33 && Frac<=0.33) {
                Phase33=true;Speed=BaseSpeed*1.85;ShootRate=std::max(11,static_cast<int>(BaseShootRate*0.5));
                FirePattern=Pattern::Aimed;Tint=shooter_detail::Red;AlertTimer=130;Summon+=3;
            }
            return Summon;
        }
        int Update(double Px,double Py,int NextChargeTimer) {
            if(State==BossState::Entering) {Y+=2;if(Y>=120){Y=120;State=BossState::Pacing;}return 0;}
            const int Summon=CheckPhases();if(AlertTimer>0) --AlertTimer;
            if(State==BossState::Pacing) {
                ++MoveTimer;if(MoveTimer>120){MoveTimer=0;Direction*=-1;}X=Clamp(X+Direction*Speed,80,720);--ChargeTimer;
                if(ChargeTimer<=0){ChargeTimer=NextChargeTimer;const double A=std::atan2(Py-Y,Px-X);ChargeDx=std::cos(A)*BaseSpeed*3.2;ChargeDy=std::sin(A)*BaseSpeed*3.2;State=BossState::Charging;}
            } else if(State==BossState::Charging) {
                X+=ChargeDx;Y+=ChargeDy;if(Y>660 || X<-80 || X>880){X=400;Y=-120;State=BossState::Returning;}
            } else {Y+=4;if(Y>=120){Y=120;State=BossState::Pacing;}}
            if(ShootTimer>0) --ShootTimer;
            return Summon;
        }
        std::vector<Bullet> Shoot(double Px,double Py) {
            using namespace shooter_detail;
            if(State==BossState::Entering || State==BossState::Returning || ShootTimer!=0) return {};
            ShootTimer=ShootRate;std::vector<Bullet> Result;
            auto Add=[&](double XOffset,double YOffset,double Dx,double Dy){Result.push_back({X+XOffset,Y+YOffset,Dx,Dy,Tint,true,true,false,true});};
            if(State==BossState::Charging) {const double D=std::max(Distance(Px,Py,X,Y),1.0e-300);Add(0,30,(Px-X)/D*9,(Py-Y)/D*9);}
            else if(FirePattern==Pattern::Spread) for(int Angle=-30;Angle<=30;Angle+=15) Add(0,50,std::cos(Radians(90+Angle))*5,std::sin(Radians(90+Angle))*5);
            else if(FirePattern==Pattern::Ring) for(int N=0;N<8;++N) Add(0,0,std::cos(Radians(N*45))*5,std::sin(Radians(N*45))*5);
            else {const double D=std::max(Distance(Px,Py,X,Y),1.0e-300);const double Dx=(Px-X)/D*7,Dy=(Py-Y)/D*7;Add(0,50,Dx,Dy);Add(-20,50,Dx*0.9,Dy+1);Add(20,50,Dx*0.9,Dy+1);}
            return Result;
        }
        Rect Bounds() const {return {std::trunc(X-60),std::trunc(Y-40),120,90};}
    };
    enum class PowerKind { Triple=0,Shield=1,Speed=2 };
    struct Powerup {
        double X=0,Y=0,Bob=0;PowerKind Kind=PowerKind::Triple;bool Alive=true;
        void Update(){Y+=2;Bob+=0.1;if(Y>620) Alive=false;}
        void Apply(Player& P) const {if(Kind==PowerKind::Triple) P.Triple=true;else if(Kind==PowerKind::Shield) P.Shield=true;else P.SpeedBoost=true;}
        Rect Bounds() const {return {std::trunc(X-14),std::trunc(Y-14),28,28};}
    };
    // Same lightweight fields as source Save & Quit, not a full world snapshot.
    // Serializing/writing this value and the top-ten leaderboard is a host task.
    struct RunSnapshot {
        std::int64_t Score=0;int Wave=1,SpawnRate=110,Lives=4;
        bool Triple=false,Shield=false,SpeedBoost=false,BossKilledThisWave=false;
        Difficulty Mode=Difficulty::Medium;
    };
    static constexpr std::size_t MaxBullets=1024,MaxEnemies=128,MaxPowerups=64,MaxEffects=256,MaxPopups=64;
    void SetDifficulty(Difficulty D) {Mode=ValidDifficulty(D)?D:Difficulty::Medium;}
    Difficulty GetDifficulty() const {return Mode;}
    bool SetOption(int Option,std::uint32_t Seed) override {
        if(Option<0 || Option>2) return false;
        Mode=static_cast<Difficulty>(Option);Reset(Seed);return true;
    }
    int GetOption() const override {return static_cast<int>(Mode);}
    const Player& GetPlayer() const {return Pilot;}
    int GetWave() const {return Wave;}
    int GetSpawnRate() const {return SpawnRate;}
    bool HasBoss() const {return BossActive;}
    const Boss& GetBoss() const {return BossActor;}
    std::size_t GetEnemyCount() const {return Enemies.size();}
    std::size_t GetPickupCount() const {return Powerups.size();}
    int GetWaveFramesRemaining() const {return std::max(0,1200-WaveTimer);}
    bool IsFireReady() const {return !Over && !QuitRequested && !Paused && Bullets.size()+3<=MaxBullets && Pilot.Cooldown==0;}
    bool IsPaused() const {return Paused;}
    bool WantsQuit() const {return QuitRequested;}
    bool HasSaveRequest() const {return SaveRequested;}
    const RunSnapshot& GetSaveRequest() const {return PendingSave;}
    void ClearSaveRequest() {SaveRequested=false;}
    void SetPaused(bool Value) {Paused=Value;PauseSelection=0;PauseNavCooldown=0;}
    void SaveAndQuit() {PendingSave=CaptureRun();SaveRequested=true;QuitRequested=true;Paused=true;}
    RunSnapshot CaptureRun() const {return {Score,Wave,SpawnRate,Pilot.Lives,Pilot.Triple,Pilot.Shield,Pilot.SpeedBoost,BossKilledThisWave,Mode};}
    bool OwnPause(bool Value) override {SetPaused(Value);return true;}
    bool IsCorePaused() const override {return IsPaused();}
    std::string SaveState() const override {
        const RunSnapshot S=SaveRequested?PendingSave:CaptureRun();std::ostringstream Out;
        Out<<"DGS1 "<<S.Score<<' '<<S.Wave<<' '<<S.SpawnRate<<' '<<S.Lives<<' '
            <<(S.Triple?1:0)<<' '<<(S.Shield?1:0)<<' '<<(S.SpeedBoost?1:0)<<' '
            <<static_cast<int>(S.Mode)<<' '<<(S.BossKilledThisWave?1:0);return Out.str();
    }
    bool RestoreState(const std::string& Payload,std::uint32_t Seed) override {
        if(Payload.size()>256) return false;
        std::istringstream In(Payload);std::string Version,Extra;RunSnapshot S;int Triple=0,Shield=0,Speed=0,Diff=0,Killed=0;
        if(!(In>>Version>>S.Score>>S.Wave>>S.SpawnRate>>S.Lives>>Triple>>Shield>>Speed>>Diff>>Killed) || Version!="DGS1" || (In>>Extra)) return false;
        if((Triple!=0 && Triple!=1) || (Shield!=0 && Shield!=1) || (Speed!=0 && Speed!=1) || (Killed!=0 && Killed!=1) || Diff<0 || Diff>2) return false;
        S.Triple=Triple!=0;S.Shield=Shield!=0;S.SpeedBoost=Speed!=0;S.Mode=static_cast<Difficulty>(Diff);S.BossKilledThisWave=Killed!=0;
        return ResumeRun(S,Seed);
    }
    bool SavePending() const override {return HasSaveRequest();}
    void ClearSavePending() override {ClearSaveRequest();}
    bool WantsExit() const override {return WantsQuit();}
    bool ResumeRun(const RunSnapshot& S,std::uint32_t Seed) {
        if(!ValidDifficulty(S.Mode) || S.Score<0 || S.Score>1000000000000LL || S.Wave<1 || S.Wave>1000000 || S.SpawnRate<28 || S.SpawnRate>135 || S.Lives<1 || S.Lives>99) return false;
        Mode=S.Mode;Reset(Seed);Score=S.Score;Wave=S.Wave;SpawnRate=S.SpawnRate;Pilot.Lives=S.Lives;
        Pilot.Triple=S.Triple;Pilot.Shield=S.Shield;Pilot.SpeedBoost=S.SpeedBoost;BossKilledThisWave=S.BossKilledThisWave;return true;
    }
    std::size_t EntityCount() const {return Bullets.size()+Enemies.size()+Powerups.size()+Effects.size()+Popups.size()+(BossActive?1:0);}
    void Reset(std::uint32_t Seed) override {
        Rng.Seed(Seed);Pilot=Player{};Pilot.Lives=Config(Mode).Lives;Score=0;Wave=1;WaveTimer=0;SpawnTimer=0;SpawnRate=Config(Mode).SpawnRate;
        Over=false;BossActive=false;BossKilledThisWave=false;Paused=false;QuitRequested=false;SaveRequested=false;
        PauseSelection=0;PauseNavCooldown=0;NextId=1;BossActor=Boss{};Bullets.clear();Enemies.clear();Powerups.clear();Effects.clear();Popups.clear();shooter_detail::MakeStars(Stars,Rng);
    }
    void Step(const Input& I) override {
        if(Over || QuitRequested) return;
        if(I.ActionPressed) {SetPaused(!Paused);return;}
        if(Paused) {
            if(PauseNavCooldown>0) --PauseNavCooldown;
            else {
                const double Y=(I.Down?1.0:0.0)-(I.Up?1.0:0.0)+Axis(I.AxisY);
                if(Y<-0.5){PauseSelection=(PauseSelection+2)%3;PauseNavCooldown=16;}
                else if(Y>0.5){PauseSelection=(PauseSelection+1)%3;PauseNavCooldown=16;}
            }
            if(I.FirePressed || I.JumpPressed) {
                if(PauseSelection==0) SetPaused(false);
                else if(PauseSelection==1) SaveAndQuit();
                else QuitRequested=true;
            }
            if(I.DashPressed) SetPaused(false);
            return;
        }
        for(auto& S:Stars) {S.Y+=1.5*S.Speed;if(S.Y>=600) S.Y-=600;}
        Pilot.Update(I);if(I.Fire) Fire();
        ++SpawnTimer;++WaveTimer;
        if(!BossActive && SpawnTimer>=SpawnRate) {SpawnTimer=0;SpawnGroup();}
        if(WaveTimer>=1200) {WaveTimer=0;Wave=std::min(Wave+1,1000000);SpawnRate=std::max(28,SpawnRate-8);BossKilledThisWave=false;}
        if(Wave%5==0 && !BossActive && !BossKilledThisWave) {BossActor=Boss::Create(Wave,Mode,Rng.Int(320,500));BossActive=true;}
        if(BossActive) {
            const int Summon=BossActor.Update(Pilot.X,Pilot.Y,Rng.Int(280,440));
            if(Summon>0) SummonBees(Summon);
            AddBullets(BossActor.Shoot(Pilot.X,Pilot.Y));
            if(BossActor.Hp<=0) DefeatBoss();
        }
        for(auto& E:Enemies) {
            if(!E.Alive) continue;
            const bool Locked=E.EscortFor!=0 && std::any_of(Enemies.begin(),Enemies.end(),[&E](const Enemy& C){return C.Id==E.EscortFor && C.Alive;});
            E.Update(Pilot.X,Pilot.Y,Wave,Mode,Rng.Unit(),Locked);
            if(E.Alive) AddBullets(E.Shoot(Rng.Int(E.ShootLow,E.ShootHigh)));
        }
        shooter_detail::Remove(Enemies,[](const Enemy& E){return !E.Alive;});
        for(auto& B:Bullets) B.Update();
        shooter_detail::Remove(Bullets,[](const Bullet& B){return !B.Alive;});
        for(auto& P:Powerups) P.Update();
        shooter_detail::Remove(Powerups,[](const Powerup& P){return !P.Alive;});
        for(auto& B:Bullets) {
            if(!B.PlayerOwned || !B.Alive) continue;
            for(auto& E:Enemies) if(E.Alive && B.Bounds().Overlaps(E.Bounds())) {
                B.Alive=false;--E.Hp;if(E.Hp<=0) DefeatEnemy(E);break;
            }
            if(B.Alive && BossActive && B.Bounds().Overlaps(BossActor.Bounds())) {B.Alive=false;--BossActor.Hp;}
        }
        // Source checks invincible only once before several loops. Check after each
        // hit so overlapping projectiles cannot remove multiple lives in one step.
        if(Pilot.Invincible==0) for(auto& B:Bullets) if(B.Alive && !B.PlayerOwned && B.Bounds().Overlaps(Pilot.Bounds())) {B.Alive=false;HitPlayer();break;}
        if(Pilot.Invincible==0) for(auto& E:Enemies) if(E.Alive && E.Bounds().Overlaps(Pilot.Bounds())) {E.Alive=false;HitPlayer();break;}
        if(Pilot.Invincible==0 && BossActive && BossActor.State!=BossState::Entering && BossActor.State!=BossState::Returning && BossActor.Bounds().Overlaps(Pilot.Bounds())) HitPlayer();
        // Keep the final loadout at the lethal contact; surviving hits still collect normally.
        if(!Over) {
            for(auto& P:Powerups) if(P.Alive && P.Bounds().Overlaps(Pilot.Bounds())) {P.Apply(Pilot);P.Alive=false;}
        }
        for(auto& P:Effects) {P.X+=P.Dx;P.Y+=P.Dy;--P.Life;}
        for(auto& P:Popups) {P.Y-=0.65;--P.Life;}
        shooter_detail::Remove(Effects,[](const Effect& P){return P.Life<=0;});
        shooter_detail::Remove(Popups,[](const Popup& P){return P.Life<=0;});
        shooter_detail::Remove(Enemies,[](const Enemy& E){return !E.Alive;});
        shooter_detail::Remove(Bullets,[](const Bullet& B){return !B.Alive;});
        shooter_detail::Remove(Powerups,[](const Powerup& P){return !P.Alive;});
    }
    void Render(Frame& F) const override {
        using namespace shooter_detail;
        F.Clear();for(const auto& S:Stars) F.AddCircle(S.X,S.Y,S.Speed<1.5?1:2,White);
        for(const auto& P:Effects) F.AddCircle(P.X,P.Y,3,P.Tint);
        for(const auto& E:Enemies) DrawEnemy(F,E);
        for(const auto& B:Bullets) if(B.Big) F.AddCircle(B.X,B.Y,7,B.Tint);else F.AddRect(B.X-2,B.Y-6,4,12,B.Tint);
        for(const auto& P:Powerups) { const double Y=P.Y+std::sin(P.Bob)*3;F.AddCircle(P.X,Y,14,PowerColor(P.Kind));F.AddText(P.X-12,Y-9,PowerLabel(P.Kind),Black,16); }
        if(BossActive) DrawBoss(F);
        if(Pilot.Shield) {for(int N=0;N<24;++N){const double A=N*Pi/12,B=(N+1)*Pi/12;F.AddLine(Pilot.X+30*std::cos(A),Pilot.Y+30*std::sin(A),Pilot.X+30*std::cos(B),Pilot.Y+30*std::sin(B),LightBlue,2);}}
        if(Pilot.SpeedBoost) F.AddCircle(Pilot.X,Pilot.Y+20,6,Yellow);
        if(Pilot.Invincible==0 || (Pilot.Invincible/4)%2!=0) {
            Polygon(F,{{Pilot.X,Pilot.Y-22},{Pilot.X-16,Pilot.Y+14},{Pilot.X,Pilot.Y+6},{Pilot.X+16,Pilot.Y+14}},Pilot.Triple?LightBlue:Cyan);
            F.AddCircle(Pilot.X,Pilot.Y+14,5,Orange);
        }
        for(const auto& P:Popups) F.AddText(P.X,P.Y,P.Label,P.Tint,17);
        F.AddText(15,40,"SCORE "+std::to_string(Score)); F.AddText(345,40,"WAVE "+std::to_string(Wave),Yellow);
        F.AddText(655,40,"LIVES "+std::to_string(Pilot.Lives),Cyan);
        F.AddText(15,65,"ENEMIES "+std::to_string(GetEnemyCount())+"   PICKUPS "+std::to_string(GetPickupCount())+
            "   WAVE SHIFT IN "+std::to_string(GetWaveFramesRemaining())+" STEPS",White,15);
        F.AddText(15,88,std::string(Pilot.Triple?"TRIPLE":"TWIN")+" SHOT   FIRE: "+FireNote(),IsFireReady()?Green:Yellow,15);
        F.AddText(420,88,ProtectionNote(),Cyan,15);
        F.AddText(15,110,BossNote(),BossActive?BossActor.Tint:Yellow,15);
        F.AddText(15,548,"Move: WASD/arrows, D-pad or stick   Hold Space/J/X/RT: fire   P/Start: pause",White,14);
        F.AddText(15,572,DifficultyName(Mode),Mode==Difficulty::Easy?Green:(Mode==Difficulty::Medium?Yellow:Red),17);
        double BadgeX=135;
        if(Pilot.Triple) {F.AddText(BadgeX,572,"[ 3X SHOT ]",LightBlue,17);BadgeX+=135;}
        if(Pilot.Shield) {F.AddText(BadgeX,572,"[ SHIELD ]",Green,17);BadgeX+=125;}
        if(Pilot.SpeedBoost) F.AddText(BadgeX,572,"[ SPEED ]",Yellow,17);
        if(BossActive && BossActor.State==BossState::Entering) F.AddText(270,280,"BOSS INCOMING!",DarkRed,28);
        if(Over) {
            F.AddRect(170,225,460,120,{15,20,40,235});
            F.AddText(280,238,"GAME OVER",Red,40);
            F.AddText(200,288,"Final score "+std::to_string(Score)+"   Wave "+std::to_string(Wave),White,18);
            F.AddText(200,318,"Pad A / Start or R / Restart: retry",Cyan,17);
        }
        if(Paused && !Over) {
            F.AddRect(200,180,400,250,{15,20,40,235});F.AddText(330,195,"PAUSED",White,32);
            const char* Labels[3]={"Resume","Save & Quit","Quit to Menu"};
            for(int N=0;N<3;++N) F.AddText(265,260+N*45,std::string(PauseSelection==N?"> ":"  ")+Labels[N],PauseSelection==N?Cyan:White,22);
            F.AddText(225,400,"Up/Down: select   J/X or Space/A: confirm",White,14);
        }
    }
    Status GetStatus() const override {
        if(QuitRequested) return {Score,std::max(0,Pilot.Lives),Over,false,SaveRequested?"Save & Quit requested; host persistence pending":"Quit requested"};
        if(Over) return {Score,std::max(0,Pilot.Lives),true,false,"Game over; wave "+std::to_string(Wave)+"; fresh pad A/Start or R/Restart to retry"};
        if(Paused) return {Score,std::max(0,Pilot.Lives),false,false,"Paused: Up/Down select; J/X or Space/A confirm; Shift/Y resume"};
        return {Score,std::max(0,Pilot.Lives),false,false,std::string(DifficultyName(Mode))+"; wave "+std::to_string(Wave)+"; shift in "+std::to_string(GetWaveFramesRemaining())+
            " steps; enemies "+std::to_string(GetEnemyCount())+"; pickups "+std::to_string(GetPickupCount())+"; "+BossNote()+"; "+
            (Pilot.Triple?"triple":"twin")+" shot; fire "+FireNote()+"; "+ProtectionNote()+"; speed "+(Pilot.SpeedBoost?"boosted":"normal")};
    }
    static const char* DifficultyName(Difficulty D) {return D==Difficulty::Easy?"Easy":(D==Difficulty::Medium?"Medium":"Hard");}
private:
    struct Effect {double X,Y,Dx,Dy;int Life;Color Tint;};
    struct Popup {double X,Y;std::string Label;int Life;Color Tint;};
    Random Rng;Player Pilot;Boss BossActor;Difficulty Mode=Difficulty::Medium;
    std::vector<Bullet> Bullets;std::vector<Enemy> Enemies;std::vector<Powerup> Powerups;std::vector<Effect> Effects;std::vector<Popup> Popups;
    std::array<shooter_detail::Star,150> Stars{};
    std::int64_t Score=0;std::uint64_t NextId=1;int Wave=1,WaveTimer=0,SpawnTimer=0,SpawnRate=110,PauseSelection=0,PauseNavCooldown=0;
    bool Over=false,BossActive=false,BossKilledThisWave=false,Paused=false,QuitRequested=false,SaveRequested=false;
    RunSnapshot PendingSave;
    std::string FireNote() const {
        if(Over || QuitRequested) return "RUN ENDED";
        if(Paused) return "PAUSED";
        if(Bullets.size()+3>MaxBullets) return "SHOT LIMIT";
        return Pilot.Cooldown>0?"COOLDOWN "+std::to_string(Pilot.Cooldown)+" STEPS":"READY";
    }
    std::string ProtectionNote() const {
        if(Over || QuitRequested) return "RUN ENDED";
        if(Pilot.Invincible==1) return std::string("PROTECTION EXPIRES NEXT LIVE STEP")+(Pilot.Shield?" + SHIELD":"");
        if(Pilot.Invincible>1) return "PROTECTION TIMER: "+std::to_string(Pilot.Invincible)+(Pilot.Shield?" + SHIELD":"");
        return Pilot.Shield?"SHIELD READY":"COLLISIONS ACTIVE";
    }
    std::string BossNote() const {
        if(!BossActive) return BossKilledThisWave?"LAST BOSS CLEARED; POWERUPS RESET ON DEFEAT":"BOSSES ARRIVE EVERY FIFTH WAVE";
        const char* State=BossActor.State==BossState::Entering?"ENTERING":(BossActor.State==BossState::Pacing?"PACING":(BossActor.State==BossState::Charging?"CHARGING":"RETURNING"));
        const char* Phase=BossActor.Phase33?"BERSERK":(BossActor.Phase66?"ENRAGED":"NORMAL");
        return "BOSS HP "+std::to_string(std::max(0,BossActor.Hp))+"/"+std::to_string(BossActor.MaxHp)+"   "+State+"   "+Phase;
    }
    static bool ValidDifficulty(Difficulty D) {return D==Difficulty::Easy || D==Difficulty::Medium || D==Difficulty::Hard;}
    static Color PowerColor(PowerKind K) {return K==PowerKind::Triple?shooter_detail::LightBlue:(K==PowerKind::Shield?shooter_detail::Green:shooter_detail::Yellow);}
    static const char* PowerLabel(PowerKind K) {return K==PowerKind::Triple?"3X":(K==PowerKind::Shield?"SH":">>");}
    void AddBullets(const std::vector<Bullet>& Values) {for(const auto& B:Values) shooter_detail::Append(Bullets,B,MaxBullets);}
    void Fire() {if(Bullets.size()+3<=MaxBullets) AddBullets(Pilot.Shoot());}
    EnemyKind PickKind() {
        if(Wave<=2) return EnemyKind::Bee;
        const int Bee=Wave<=4?5:(Wave<=7?4:3),Butterfly=Wave<=4?1:2,Cruiser=Wave<=4?0:(Wave<=7?1:2);
        const int Roll=Rng.Int(1,Bee+Butterfly+Cruiser);return Roll<=Bee?EnemyKind::Bee:(Roll<=Bee+Butterfly?EnemyKind::Butterfly:EnemyKind::Cruiser);
    }
    Enemy MakeEnemy(EnemyKind Kind,double X=-1) {
        const EnemyData A=Data(Kind);const auto C=Config(Mode);
        Enemy E=Enemy::Create(Kind,Wave,Mode,X<0?Rng.Int(40,760):X,Rng.Int(-220,-40),Rng.Between(A.SpeedLow,A.SpeedHigh),Rng.Between(-1.5,1.5),Rng.Between(0,shooter_detail::Pi*2),Rng.Int(static_cast<int>(A.ShootLow*C.ShootDelay),static_cast<int>(A.ShootHigh*C.ShootDelay)));
        E.Id=NextId++;return E;
    }
    void SpawnGroup() {
        if(Enemies.size()+3>MaxEnemies) return;
        const EnemyKind Kind=PickKind();
        if(Kind==EnemyKind::Cruiser) {
            Enemy Cruiser=MakeEnemy(Kind,Rng.Int(80,720));const int Count=Rng.Int(1,2);Cruiser.EscortsRemaining=Count;
            for(int N=0;N<Count;++N) {Enemy Bee=MakeEnemy(EnemyKind::Bee,Cruiser.X+(N*2-(Count-1))*52);Bee.Y=Cruiser.Y+Rng.Int(-25,25);Bee.EscortFor=Cruiser.Id;Enemies.push_back(Bee);}
            Enemies.push_back(Cruiser);
        } else {Enemies.push_back(MakeEnemy(Kind));if(Rng.Unit()<0.35) Enemies.push_back(MakeEnemy(Kind));}
    }
    void SummonBees(int Count) {
        for(int N=0;N<Count;++N) {Enemy E=MakeEnemy(EnemyKind::Bee,BossActor.X+(N-Count/2)*55);E.Y=BossActor.Y+40;shooter_detail::Append(Enemies,E,MaxEnemies);}
    }
    void Explode(double X,double Y,Color Tint,int Count=20) {
        for(int N=0;N<Count;++N) {const double A=Rng.Between(0,shooter_detail::Pi*2),Speed=Rng.Between(1,5);shooter_detail::Append(Effects,Effect{X,Y,std::cos(A)*Speed,std::sin(A)*Speed,Rng.Int(15,35),Tint},MaxEffects);}
    }
    void DefeatEnemy(Enemy& E) {
        E.Alive=false;Explode(E.X,E.Y,Data(E.Kind).Explosion);
        if(E.EscortFor!=0) for(auto& C:Enemies) if(C.Id==E.EscortFor) {C.EscortsRemaining=std::max(0,C.EscortsRemaining-1);break;}
        const int Points=E.Points();shooter_detail::AddScore(Score,Points);
        shooter_detail::Append(Popups,Popup{E.X,E.Y,std::to_string(Points)+(E.Kind==EnemyKind::Cruiser && E.EscortsRemaining==0?"! BONUS!":""),65,Data(E.Kind).Tint},MaxPopups);
        if(Rng.Unit()<0.13) shooter_detail::Append(Powerups,Powerup{E.X,E.Y,0,static_cast<PowerKind>(Rng.Int(0,2)),true},MaxPowerups);
    }
    void DefeatBoss() {
        Explode(BossActor.X,BossActor.Y,BossActor.Tint,60);Explode(BossActor.X,BossActor.Y,White,30);shooter_detail::AddScore(Score,1000);
        shooter_detail::Append(Popups,Popup{BossActor.X,BossActor.Y-20,"1000!",65,shooter_detail::Gold},MaxPopups);
        shooter_detail::Remove(Bullets,[](const Bullet& B){return B.BossOwned;});Pilot.ResetPowerups();
        std::array<PowerKind,3> Kinds{{PowerKind::Triple,PowerKind::Shield,PowerKind::Speed}};
        for(int N=2;N>0;--N) std::swap(Kinds[N],Kinds[Rng.Int(0,N)]);
        for(int N=0;N<3;++N) shooter_detail::Append(Powerups,Powerup{BossActor.X+(N-1)*60,BossActor.Y,0,Kinds[N],true},MaxPowerups);
        Pilot.Invincible=std::max(Pilot.Invincible,120);BossActive=false;BossKilledThisWave=true;
        Wave=std::min(Wave+1,1000000);WaveTimer=0;SpawnRate=std::max(28,SpawnRate-8);
    }
    void HitPlayer() {const bool Shield=Pilot.Shield;Over=Pilot.Hit();Explode(Pilot.X,Pilot.Y,Shield?shooter_detail::LightBlue:shooter_detail::Cyan,Shield?10:20);}
    static void DrawEnemy(Frame& F,const Enemy& E) {
        using namespace shooter_detail;
        const double X=E.X,Y=E.Y,S=E.Size;
        if(E.Kind==EnemyKind::Bee) {Polygon(F,{{X,Y-S},{X-S,Y},{X,Y+S},{X+S,Y}},Red);if(E.Hp>1) Outline(F,{{X,Y-S},{X-S,Y},{X,Y+S},{X+S,Y}},Orange);}
        else if(E.Kind==EnemyKind::Butterfly) {const std::vector<Vec> Points={{X,Y-S},{X-std::trunc(S*1.4),Y-std::floor(S/2)},{X-S,Y+std::floor(S/2)},{X,Y+std::floor(S/3)},{X+S,Y+std::floor(S/2)},{X+std::trunc(S*1.4),Y-std::floor(S/2)}};Polygon(F,Points,Purple);Outline(F,Points,Pink);F.AddCircle(X,Y,4,White);}
        else {std::vector<Vec> Points;for(int N=0;N<6;++N) Points.push_back({X+std::trunc(S*std::cos(Radians(N*60-30))),Y+std::trunc(S*std::sin(Radians(N*60-30)))});Polygon(F,Points,Gold);Outline(F,Points,Yellow);F.AddCircle(X,Y,std::floor(S/3),Orange);F.AddRect(X-S,Y+S+3,S*2,4,DarkRed);F.AddRect(X-S,Y+S+3,S*2*Clamp(static_cast<double>(E.Hp)/E.MaxHp,0,1),4,{160,255,60,255});}
        if(E.State==EnemyState::Dive) for(int N=0;N<16;++N){const double A=N*Pi/8,B=(N+1)*Pi/8;F.AddLine(X+(S+5)*std::cos(A),Y+(S+5)*std::sin(A),X+(S+5)*std::cos(B),Y+(S+5)*std::sin(B),White);}
    }
    void DrawBoss(Frame& F) const {
        using namespace shooter_detail;
        const double X=BossActor.X,Y=BossActor.Y;const std::vector<Vec> Points={{X,Y-50},{X-70,Y+10},{X-40,Y+50},{X,Y+30},{X+40,Y+50},{X+70,Y+10}};
        Polygon(F,Points,BossActor.Tint);Outline(F,Points,White);F.AddCircle(X,Y,18,White);F.AddCircle(X,Y,12,BossActor.Tint);F.AddCircle(X,Y,5,White);
        const double Frac=Clamp(static_cast<double>(BossActor.Hp)/BossActor.MaxHp,0,1);
        F.AddRect(250,12,300,18,DarkRed);F.AddRect(250,12,300*Frac,18,Frac<=0.33?Red:(Frac<=0.66?Orange:BossActor.Tint));F.AddText(370,12,"BOSS",White,17);
        if(BossActor.AlertTimer>0) F.AddText(300,340,BossActor.Phase33?"BERSERK!":"ENRAGED!",BossActor.Tint,28);
        if(BossActor.State==BossState::Charging) {F.AddCircle(X,Y,34,White);F.AddCircle(X,Y,26,Yellow);F.AddCircle(X,Y,18,BossActor.Tint);F.AddText(350,70,"CHARGING!",Yellow,17);}
    }
};
}} // daedalus::desktop
