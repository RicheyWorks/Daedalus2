// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>

namespace daedalus { namespace desktop {
namespace sports_detail {
inline double Stick(double Value) {
    const double Clean=Axis(Value);
    return std::abs(Clean)>0.15 ? Clean : 0.0;
}
// These sources let the last digital direction win, then replace both axes
// with the stick when either axis exceeds 0.2. They do not normalize diagonals.
inline Vec Direction(const Input& I) {
    Vec D{I.Right ? 1.0 : (I.Left ? -1.0 : 0.0),
          I.Down ? 1.0 : (I.Up ? -1.0 : 0.0)};
    const double X=Stick(I.AxisX),Y=Stick(I.AxisY);
    if(std::abs(X)>0.2 || std::abs(Y)>0.2) D={X,Y};
    return D;
}
inline Vec Unit(double X,double Y) {
    const double Length=std::hypot(X,Y);
    return Length>0 ? Vec{X/Length,Y/Length} : Vec{};
}
inline void Ring(Frame& F,double X,double Y,double Radius,Color C,double Thickness=2) {
    constexpr int Segments=32;
    for(int I=0;I<Segments;++I) {
        const double A=6.283185307179586*I/Segments;
        const double B=6.283185307179586*(I+1)/Segments;
        F.AddLine(X+std::cos(A)*Radius,Y+std::sin(A)*Radius,
                  X+std::cos(B)*Radius,Y+std::sin(B)*Radius,C,Thickness);
    }
}
inline void Outline(Frame& F,double X,double Y,double W,double H,Color C,double T=2) {
    F.AddLine(X,Y,X+W,Y,C,T);F.AddLine(X+W,Y,X+W,Y+H,C,T);
    F.AddLine(X+W,Y+H,X,Y+H,C,T);F.AddLine(X,Y+H,X,Y,C,T);
}
}

// Source: Desktop/football_pygame_ce.py, SHA256 7b013f81...36ca3ebe.
// The data structs also support host inspection and deterministic replay tests.
class FootballGame final : public Game {
public:
    enum class Phase { Title, Playing, Won, Lost, Draw };
    struct Player {
        double X=200,Y=300,Speed=3.5;
        bool Cpu=false;
        int KickCooldown=0;
    };
    struct Ball { double X=400,Y=300,Vx=0,Vy=0; };
    struct State {
        Player Human{},Cpu{600,300,2.8,true,0};
        Ball Football{};
        int HumanScore=0,CpuScore=0;
        double Seconds=90;
        Phase Mode=Phase::Title;
    } Data;
    FootballGame() { Reset(730); }
    void Reset(std::uint32_t) override { Data=State{}; }
    static void MovePlayer(Player& P,const Input& I,const Ball& B) {
        Vec D=P.Cpu ? sports_detail::Unit(B.X-P.X,B.Y-P.Y) : sports_detail::Direction(I);
        const double Rate=P.Speed*(P.Cpu ? 0.9 : 1.0);
        P.X=Clamp(P.X+D.X*Rate,40,760);P.Y=Clamp(P.Y+D.Y*Rate,40,560);
        if(P.KickCooldown>0) --P.KickCooldown;
    }
    static bool Kick(Player& P,Ball& B) {
        if(P.KickCooldown!=0) return false;
        P.KickCooldown=12;
        const Vec D=sports_detail::Unit(B.X-P.X,B.Y-P.Y);
        B.Vx=D.X*8;B.Vy=D.Y*8;
        return true;
    }
    static void UpdateBall(Ball& B) {
        B.X+=B.Vx;B.Y+=B.Vy;B.Vx*=0.96;B.Vy*=0.96;
        if(B.X<40 || B.X>760) { B.Vx*=-0.8;B.X=Clamp(B.X,40,760); }
        if(B.Y<40 || B.Y>560) { B.Vy*=-0.8;B.Y=Clamp(B.Y,40,560); }
    }
    static bool Deflect(const Player& P,Ball& B) {
        if(Distance(B.X,B.Y,P.X,P.Y)>=20) return false;
        const Vec D=sports_detail::Unit(B.X-P.X,B.Y-P.Y);
        B.Vx=D.X*6;B.Vy=D.Y*6;return true;
    }
    void Step(const Input& I) override {
        if(Data.Mode!=Phase::Playing) {
            if(!(I.FirePressed || I.ActionPressed)) return;
            Data=State{};Data.Mode=Phase::Playing;
        } else if(I.FirePressed) Kick(Data.Human,Data.Football);
        MovePlayer(Data.Human,I,Data.Football);MovePlayer(Data.Cpu,I,Data.Football);
        UpdateBall(Data.Football);Deflect(Data.Human,Data.Football);Deflect(Data.Cpu,Data.Football);
        const bool LeftGoal=Data.Football.X<50 && Data.Football.Y>220 && Data.Football.Y<380;
        const bool RightGoal=Data.Football.X>750 && Data.Football.Y>220 && Data.Football.Y<380;
        if(LeftGoal || RightGoal) {
            if(LeftGoal) ++Data.CpuScore; else ++Data.HumanScore;
            Data.Football=Ball{};Data.Human.X=200;Data.Human.Y=300;Data.Cpu.X=600;Data.Cpu.Y=300;
        }
        Data.Seconds-=1.0/60.0;
        if(Data.Seconds<=0) {
            Data.Seconds=0; // Safe display; source otherwise shows a negative final fraction.
            Data.Mode=Data.HumanScore>Data.CpuScore ? Phase::Won :
                      (Data.CpuScore>Data.HumanScore ? Phase::Lost : Phase::Draw);
        }
    }
    Status GetStatus() const override {
        const bool End=Data.Mode==Phase::Won || Data.Mode==Phase::Lost || Data.Mode==Phase::Draw;
        return {Data.HumanScore,0,End,Data.Mode==Phase::Won,
            Data.Mode==Phase::Title ? "Football: Fire/Action to start" :
            (End ? "Football: Fire/Action to restart" : "Move; Fire press kicks; 90 seconds")};
    }
    void Render(Frame& F) const override {
        constexpr Color Green{0,128,0,255},Blue{30,100,255,255},Red{255,50,50,255};
        F.Clear(800,600,Green);
        sports_detail::Ring(F,400,300,60,White,3);F.AddCircle(400,300,8,White);
        F.AddLine(400,40,400,560,White,3);
        sports_detail::Outline(F,30,220,20,160,White,4);sports_detail::Outline(F,750,220,20,160,White,4);
        sports_detail::Outline(F,30,150,120,300,White,3);sports_detail::Outline(F,650,150,120,300,White,3);
        if(Data.Mode==Phase::Playing) {
            F.AddCircle(Data.Human.X,Data.Human.Y,12,Blue);sports_detail::Ring(F,Data.Human.X,Data.Human.Y,12,White);
            F.AddCircle(Data.Cpu.X,Data.Cpu.Y,12,Red);sports_detail::Ring(F,Data.Cpu.X,Data.Cpu.Y,12,White);
            F.AddCircle(Data.Football.X,Data.Football.Y,8,White);sports_detail::Ring(F,Data.Football.X,Data.Football.Y,8,Black);
            F.AddText(25,5,"YOU: "+std::to_string(Data.HumanScore),Blue,24);
            F.AddText(640,5,"CPU: "+std::to_string(Data.CpuScore),Red,24);
            F.AddText(340,5,"TIME: "+std::to_string(static_cast<int>(Data.Seconds)),White,24);
            F.AddText(250,565,"Move: arrows / stick; Fire: kick",White,18);
        } else if(Data.Mode==Phase::Title) {
            F.AddText(270,160,"FOOTBALL",White,48);F.AddText(235,235,"1980s STYLE FOOTBALL",White,24);
            F.AddText(200,320,"Fire / Action to kick off",White,26);
            F.AddText(190,385,"Move: arrows / stick; Fire: kick",White,20);
            F.AddText(220,440,"Score goals and beat the CPU!",White,20);
        } else {
            F.AddText(255,230,Data.Mode==Phase::Won ? "YOU WIN!" : (Data.Mode==Phase::Lost ? "CPU WINS!" : "IT'S A DRAW!"),White,42);
            F.AddText(260,310,"Final score: "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore),White,26);
            F.AddText(210,375,"Fire / Action to play again",White,24);
        }
    }
};

// Source: Desktop/super_dodge_ball_fixed.py, SHA256 359b4bc0...21cb6.
// One fixed step equals one source 60 Hz frame. Six players and one ball are
// always bounded. Ownership is an index, so resets never leave dangling pointers.
class DodgeBallGame final : public Game {
public:
    enum class Phase { Title, CountrySelect, Playing, Won, Lost };
    struct Country { const char* Name;Color Tint;double Power,Speed; };
    inline static constexpr std::array<Country,8> Countries{{
        {"USA",{50,100,220,255},1.2,1.0},{"Japan",{220,50,50,255},1.0,1.3},
        {"Brazil",{50,180,50,255},1.1,1.1},{"Germany",{255,200,50,255},1.3,0.9},
        {"UK",{150,50,200,255},1.0,1.2},{"Russia",{200,50,50,255},1.4,0.85},
        {"China",{255,150,50,255},1.15,1.05},{"Australia",{50,150,200,255},1.1,1.15}
    }};
    struct Player {
        double X=0,Y=0,BaseY=0,Speed=3.2,Power=1,JumpVelocity=0;
        int CountryIndex=0,Health=3,ThrowCooldown=0,JumpCooldown=0,Charge=0,SuperType=1;
        bool Cpu=false,HasBall=false,FacingRight=true,OnGround=true,JumpWasDown=false;
    };
    struct Ball {
        double X=400,Y=300,Vx=0,Vy=0;
        int Owner=-1;
        bool InAir=false,PowerBall=false;
        Color ThrowColor=White;
    };
    struct Particle { double X,Y,Vx,Vy,Size;int Life;Color Tint; };
    static constexpr std::size_t MaxParticles=256;
    struct State {
        std::array<Player,6> Players{};
        Ball DodgeBall{};
        int SelectedCountry=0,OpponentCountry=1,HumanScore=0,CpuScore=0,Round=1;
        Phase Mode=Phase::Title;
        std::vector<Particle> Particles;
    } Data;
private:
    Random Rng;
    bool UpWasDown=false,DownWasDown=false;
    int Opponent() {
        const int Pick=Rng.Int(0,6);
        return Pick>=Data.SelectedCountry ? Pick+1 : Pick;
    }
    void Burst(double X,double Y,Color Tint,int Count=10,double Power=3) {
        for(int N=0;N<Count;++N) {
            // Consume all draws even at capacity, keeping replay independent of rendering limits.
            Particle P{X,Y,Rng.Between(-Power,Power),Rng.Between(-Power,Power),0,0,Tint};
            P.Life=Rng.Int(14,26);P.Size=Rng.Int(3,6);
            if(Data.Particles.size()<MaxParticles) Data.Particles.push_back(P);
        }
    }
    int Nearest(int PlayerIndex) const {
        const Player& P=Data.Players[PlayerIndex];double Best=1e30;int Target=-1;
        const int Start=P.Cpu ? 0 : 3;
        for(int N=Start;N<Start+3;++N) {
            const Player& O=Data.Players[N];
            const double D=Distance(P.X,P.Y,O.X,O.Y);
            if(O.Health>0 && D<Best) { Best=D;Target=N; }
        }
        return Target;
    }
    void AimAndThrow(int Index,bool ForceSuper=false) {
        Player& P=Data.Players[Index];const int Target=Nearest(Index);
        if(Target<0 || !P.HasBall) return;
        const Player& O=Data.Players[Target];const Vec D=sports_detail::Unit(O.X-P.X,O.Y-P.Y);
        const bool Super=ForceSuper || P.Charge>30;
        if(Super) Burst(P.X,P.Y-5,Countries[P.CountryIndex].Tint,14,4);
        CountryThrow(Data.DodgeBall,P,D,Super);
    }
    void MoveCpu(int Index) {
        Player& P=Data.Players[Index];Ball& B=Data.DodgeBall;
        if(B.Owner==Index) {
            P.Charge=std::min(60,P.Charge+2);
            const int Target=Nearest(Index);
            if(Target>=0 && P.ThrowCooldown==0 && Rng.Unit()<0.05) {
                const Player& O=Data.Players[Target];const Vec D=sports_detail::Unit(O.X-P.X,O.Y-P.Y);
                Throw(B,P,D,Rng.Unit()<0.35);P.Charge=0;
            }
        } else if(B.Owner<0 && !B.InAir) {
            const Vec D=sports_detail::Unit(B.X-P.X,B.Y-P.Y);
            P.X+=D.X*P.Speed*0.7;P.Y+=D.Y*P.Speed*0.7;
        } else P.Y+=Rng.Int(-1,1)*P.Speed*0.3;
        P.FacingRight=false;
    }
    void MatchResult() {
        bool Humans=false,Cpus=false;
        for(int N=0;N<3;++N) Humans=Humans || Data.Players[N].Health>0;
        for(int N=3;N<6;++N) Cpus=Cpus || Data.Players[N].Health>0;
        if(!Humans) { ++Data.CpuScore;Data.Mode=Phase::Lost; }
        else if(!Cpus) { ++Data.HumanScore;Data.Mode=Phase::Won; }
    }
public:
    DodgeBallGame() { Reset(730); }
    void Reset(std::uint32_t Seed) override {
        Rng.Seed(Seed);Data=State{};Data.Particles.reserve(MaxParticles);
        UpWasDown=DownWasDown=false;
    }
    static Player MakePlayer(int CountryIndex,int Slot,bool Cpu,int SuperType=1) {
        const int SafeCountry=std::max(0,std::min(7,CountryIndex));
        const int SafeSlot=std::max(0,std::min(2,Slot));
        constexpr double Xs[3]={200,180,220},Ys[3]={200,300,400};
        constexpr double PowerScale[3]={1,0.9,1.1},SpeedScale[3]={1,1.1,0.9};
        Player P;P.CountryIndex=SafeCountry;P.Cpu=Cpu;P.FacingRight=!Cpu;
        P.X=Cpu ? 800-Xs[SafeSlot] : Xs[SafeSlot];P.Y=P.BaseY=Ys[SafeSlot];
        P.Power=Countries[SafeCountry].Power*PowerScale[SafeSlot];
        P.Speed=3.2*Countries[SafeCountry].Speed*SpeedScale[SafeSlot];
        P.SuperType=SuperType==2 ? 2 : 1;return P;
    }
    void StartMatch() {
        for(int N=0;N<3;++N) Data.Players[N]=MakePlayer(Data.SelectedCountry,N,false,Rng.Int(1,2));
        for(int N=0;N<3;++N) Data.Players[N+3]=MakePlayer(Data.OpponentCountry,N,true,Rng.Int(1,2));
        Data.DodgeBall=Ball{};Data.DodgeBall.Owner=1;Data.Players[1].HasBall=true;
        Data.Particles.clear();Data.Mode=Phase::Playing;
    }
    static void MoveHuman(Player& P,const Input& I) {
        Vec D=sports_detail::Direction(I);
        const Vec Pad{(I.PadRight ? 1.0 : 0.0)-(I.PadLeft ? 1.0 : 0.0),
                      (I.PadDown ? 1.0 : 0.0)-(I.PadUp ? 1.0 : 0.0)};
        if(Pad.X!=0 || Pad.Y!=0) D=Pad;
        if(D.X>0) P.FacingRight=true;else if(D.X<0) P.FacingRight=false;
        P.X+=D.X*P.Speed;P.Y+=D.Y*P.Speed;
        const bool JumpPressed=(I.Jump && !P.JumpWasDown) || I.JumpPressed;
        P.JumpWasDown=I.Jump;
        if(JumpPressed && P.OnGround && P.JumpCooldown<=0) {
            P.JumpVelocity=-8;P.OnGround=false;P.JumpCooldown=15;
        }
        if(!P.OnGround) {
            P.JumpVelocity+=0.6;P.Y+=P.JumpVelocity;
            if(P.Y>=P.BaseY) { P.Y=P.BaseY;P.OnGround=true;P.JumpVelocity=0; }
        }
        if(P.HasBall) {
            if(sports_detail::Stick(I.AxisY)<-0.5 || I.Up) P.Charge=std::min(60,P.Charge+2);
            else P.Charge=std::max(0,P.Charge-2);
        } else P.Charge=0;
    }
    static void BoundAndCooldown(Player& P) {
        P.X=Clamp(P.X,P.Cpu ? 440 : 60,P.Cpu ? 740 : 360);P.Y=Clamp(P.Y,80,510);
        if(P.ThrowCooldown>0) --P.ThrowCooldown;
        if(P.JumpCooldown>0) --P.JumpCooldown;
    }
    static bool Throw(Ball& B,Player& P,Vec Direction,bool PowerBall=false) {
        if(P.ThrowCooldown>0) return false;
        B.Owner=-1;B.InAir=true;B.PowerBall=PowerBall;B.ThrowColor=Countries[P.CountryIndex].Tint;
        const double Speed=PowerBall ? 12 : 8.5;
        B.Vx=Direction.X*Speed*P.Power;B.Vy=Direction.Y*Speed*P.Power;
        P.HasBall=false;P.Charge=0;P.ThrowCooldown=PowerBall ? 22 : 14;
        return true;
    }
    static void CountryThrow(Ball& B,Player& P,Vec D,bool Super) {
        if(!Super) { Throw(B,P,D);return; }
        switch(P.CountryIndex) {
        case 0: D.Y*=0.25;break;
        case 1: D.X*=0.75;D.Y*=P.SuperType==1 ? 1.3 : -1.3;break;
        case 2: D.X*=0.65;D.Y-=1;break;
        case 4: D.Y*=0.8;break;
        case 5: D.X*=0.95;D.Y*=0.95;break;
        case 6: D.X*=0.8;D.Y-=0.75;break;
        case 7: D.X*=1.1;D.Y+=P.SuperType==1 ? 0.6 : -0.6;break;
        default: break;
        }
        Throw(B,P,D,true);
        if(P.CountryIndex==3) P.ThrowCooldown=std::max(P.ThrowCooldown,28);
        if(P.CountryIndex==5) P.ThrowCooldown=std::max(P.ThrowCooldown,32);
    }
    static void UpdateBall(Ball& B,const std::array<Player,6>& Players) {
        if(B.Owner>=0 && B.Owner<6) {
            const Player& P=Players[B.Owner];B.X=P.X+(P.FacingRight ? 20 : -20);B.Y=P.Y-5;
        } else if(B.InAir) {
            B.X+=B.Vx;B.Y+=B.Vy;B.Vx*=0.985;B.Vy*=0.985;
            if(B.X<50) { B.X=50;B.Vx*=-0.6; }
            if(B.X>750) { B.X=750;B.Vx*=-0.6; }
            if(B.Y<70) { B.Y=70;B.Vy*=-0.6; }
            if(B.Y>520) { B.Y=520;B.Vy*=-0.6; }
            if(std::abs(B.Vx)+std::abs(B.Vy)<0.45) { B.InAir=false;B.PowerBall=false; }
        }
    }
    static bool Pickup(Ball& B,Player& P,int Index) {
        if(B.Owner>=0 || B.InAir || P.Health<=0 || Index<0 || Index>=6) return false;
        if(Distance(B.X,B.Y,P.X,P.Y)>=24) return false;
        B.Owner=Index;P.HasBall=true;return true;
    }
    static bool Catch(Ball& B,Player& P,int Index) {
        if(!B.InAir || P.Health<=0 || Index<0 || Index>=6) return false;
        const double Radius=!P.OnGround ? 34 : (B.PowerBall ? 18 : 23);
        if(Distance(B.X,B.Y,P.X,P.Y)>=Radius) return false;
        B.Owner=Index;B.InAir=false;B.PowerBall=false;P.HasBall=true;return true;
    }
    static bool Hit(Ball& B,Player& P) {
        if(!B.InAir || P.Health<=0 || Distance(B.X,B.Y,P.X,P.Y)>=18) return false;
        P.Health=std::max(0,P.Health-(B.PowerBall ? 2 : 1));
        B.InAir=false;B.PowerBall=false;B.Owner=-1;B.Vx*=-0.4;B.Vy*=-0.4;
        // Source clears this on the next player update. Immediate clearing keeps
        // the host-facing possession invariant valid even on the result screen.
        P.HasBall=false;return true;
    }
    static bool RecoverLooseBall(Ball& B) {
        // Source side limits are x<=360 / x>=440 and pickup is strictly <24.
        // A stationary ball in [384,416] is therefore unreachable by either
        // team. Move only that dead strip's loose ball to a reachable edge;
        // never change airborne or possessed ball physics.
        if(B.Owner>=0 || B.InAir || B.X<384 || B.X>416) return false;
        B.X=B.X<=400 ? 380 : 420;return true;
    }
    void Step(const Input& I) override {
        const bool Confirm=I.FirePressed || I.ActionPressed;
        const bool AnyButton=Confirm || I.JumpPressed || I.DashPressed;
        const bool UpDown=I.Up || I.PadUp,DownDown=I.Down || I.PadDown;
        const bool UpPressed=UpDown && !UpWasDown,DownPressed=DownDown && !DownWasDown;
        UpWasDown=UpDown;DownWasDown=DownDown;
        if(Data.Mode==Phase::Title) {
            if(AnyButton || std::abs(Axis(I.AxisX))>0.6 || std::abs(Axis(I.AxisY))>0.6)
                Data.Mode=Phase::CountrySelect;
            return;
        }
        if(Data.Mode==Phase::CountrySelect) {
            if(UpPressed) Data.SelectedCountry=(Data.SelectedCountry+7)%8;
            else if(DownPressed) Data.SelectedCountry=(Data.SelectedCountry+1)%8;
            if(!Confirm) return;
            Data.OpponentCountry=Opponent();Data.HumanScore=Data.CpuScore=0;Data.Round=1;StartMatch();
        } else if(Data.Mode==Phase::Won || Data.Mode==Phase::Lost) {
            if(!AnyButton) return;
            if(Data.Round>=4) { Data.Mode=Phase::Title;Data.Round=1;return; }
            ++Data.Round;Data.OpponentCountry=Opponent();StartMatch();
        } else if(I.FirePressed) {
            for(int N=0;N<3;++N) if(Data.Players[N].HasBall && Data.Players[N].ThrowCooldown==0) {
                AimAndThrow(N);break;
            }
        }
        for(int N=0;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.Health<=0) { P.HasBall=false;continue; }
            if(P.Cpu) MoveCpu(N);else MoveHuman(P,I);
            BoundAndCooldown(P);
        }
        Ball& B=Data.DodgeBall;UpdateBall(B,Data.Players);RecoverLooseBall(B);
        if(B.Owner<0 && !B.InAir) for(int N=0;N<6;++N) if(Pickup(B,Data.Players[N],N)) break;
        if(B.InAir) for(int N=0;N<3;++N) {
            Player& P=Data.Players[N];const double Radius=P.OnGround ? 22 : 35;
            if(P.Health>0 && !P.HasBall && Distance(B.X,B.Y,P.X,P.Y)<Radius && (!P.OnGround || I.Fire)) {
                if(Catch(B,P,N)) { Burst(P.X,P.Y,{255,255,200,255},8,2.5);break; }
            }
        }
        if(B.InAir) for(int N=3;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.Health>0 && !P.HasBall && Rng.Unit()<0.12 && Catch(B,P,N)) break;
        }
        if(I.Fire) for(int N=0;N<3;++N) if(Data.Players[N].HasBall && Data.Players[N].ThrowCooldown==0) {
            AimAndThrow(N);break;
        }
        for(int N=3;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.HasBall && P.ThrowCooldown==0 && Rng.Unit()<0.03) {
                P.SuperType=Rng.Int(1,2);P.Charge=Rng.Int(0,60);AimAndThrow(N,Rng.Unit()<0.35);
            }
        }
        if(B.InAir) for(int N=0;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.Health>0 && Distance(B.X,B.Y,P.X,P.Y)<18) {
                const bool Power=B.PowerBall;const double X=B.X,Y=B.Y;const Color Tint=B.ThrowColor;
                if(Hit(B,P)) { Burst(X,Y,Tint,Power ? 15 : 8,4);MatchResult();break; }
            }
        }
        for(Particle& P:Data.Particles) {
            P.X+=P.Vx;P.Y+=P.Vy;P.Vx*=0.92;P.Vy*=0.92;--P.Life;P.Size=std::max(1.0,P.Size*0.95);
        }
        Data.Particles.erase(std::remove_if(Data.Particles.begin(),Data.Particles.end(),
            [](const Particle& P){return P.Life<=0;}),Data.Particles.end());
    }
    Status GetStatus() const override {
        int Lives=0;for(int N=0;N<3;++N) if(Data.Players[N].Health>0) ++Lives;
        const bool End=Data.Mode==Phase::Won || Data.Mode==Phase::Lost;
        return {Data.HumanScore,Lives,End,Data.Mode==Phase::Won,
            Data.Mode==Phase::Playing ? "Move trio; Fire throw/catch; Up charges; Jump evades" :
            (Data.Mode==Phase::CountrySelect ? "Up/Down select country; Fire/Action confirms" : "Fire/Action continues")};
    }
    void DrawPlayer(Frame& F,const Player& P) const {
        constexpr Color Yellow{255,220,50,255},Red{220,50,50,255};
        if(P.Health<=0) { F.AddCircle(P.X,P.Y,10,{70,70,70,255});F.AddText(P.X-10,P.Y-8,"KO",White,14);return; }
        const double X=std::trunc(P.X),Y=std::trunc(P.Y)-std::trunc(P.OnGround ? 0 : std::abs(P.JumpVelocity)*0.3);
        if(!P.OnGround) { const double R=std::max(4.0,std::trunc(14-std::abs(P.JumpVelocity)*0.8));
            F.AddRect(X-R,P.BaseY+15,R*2,6,{10,40,10,255}); }
        F.AddCircle(X,Y,14,Countries[P.CountryIndex].Tint);sports_detail::Ring(F,X,Y,14,White);
        switch(P.CountryIndex) {
        case 0: F.AddRect(X-10,Y-4,20,8,{255,50,50,255});for(int N=0;N<3;++N) F.AddCircle(X-6+N*6,Y,2,White);
            F.AddRect(X-8,Y-20,16,6,{50,50,150,255});break;
        case 1: F.AddCircle(X,Y,6,White);F.AddRect(X-10,Y-18,20,4,White);break;
        case 2: F.AddCircle(X,Y,5,{255,215,0,255});F.AddRect(X-10,Y-18,20,5,{0,100,0,255});break;
        case 3: F.AddRect(X-10,Y-8,20,5,Black);F.AddRect(X-10,Y-3,20,5,{255,50,50,255});
            F.AddRect(X-10,Y+2,20,5,{255,215,0,255});F.AddRect(X-9,Y-20,18,7,Black);break;
        case 4: F.AddLine(X-10,Y,X+10,Y,White,3);F.AddLine(X,Y-10,X,Y+10,White,3);
            F.AddLine(X-10,Y-17,X,Y-22,White,3);F.AddLine(X,Y-22,X+10,Y-17,White,3);break;
        case 5: F.AddRect(X-10,Y-8,20,5,White);F.AddRect(X-10,Y-3,20,5,{50,100,200,255});
            F.AddRect(X-10,Y+2,20,5,{255,50,50,255});F.AddRect(X-9,Y-21,18,9,{80,40,40,255});break;
        case 6: F.AddCircle(X-4,Y-4,3,{255,215,0,255});F.AddCircle(X+5,Y+3,2,{255,215,0,255});
            F.AddRect(X-8,Y-20,16,6,{200,30,30,255});F.AddCircle(X,Y-17,2,{255,215,0,255});break;
        case 7: F.AddCircle(X-3,Y-3,2,White);F.AddCircle(X+4,Y+4,2,White);F.AddRect(X-11,Y-20,22,8,{139,90,43,255});break;
        default: break;
        }
        for(int N=0;N<P.Health;++N) F.AddCircle(X-8+N*8,Y-24,3,Red);
        if(P.HasBall) sports_detail::Ring(F,X,Y,20,Yellow);
        if(P.HasBall && P.Charge>5) { F.AddRect(X-12,Y+20,std::trunc(P.Charge/60.0*24),4,Yellow);
            sports_detail::Outline(F,X-12,Y+20,24,4,White,1); }
    }
    void Render(Frame& F) const override {
        constexpr Color Yellow{255,220,50,255},Red{220,50,50,255},Blue{50,100,220,255};
        F.Clear();
        if(Data.Mode==Phase::Playing) {
            F.AddRect(40,40,720,520,{50,120,50,255});sports_detail::Outline(F,40,40,720,520,White,4);
            F.AddLine(400,40,400,560,White,4);sports_detail::Ring(F,400,300,50,White,3);
            F.AddText(165,50,Countries[Data.SelectedCountry].Name,White,16);
            F.AddText(565,50,Countries[Data.OpponentCountry].Name,White,16);
            for(const Player& P:Data.Players) DrawPlayer(F,P);
            const Ball& B=Data.DodgeBall;F.AddCircle(B.X,B.Y,11,B.PowerBall ? Red : B.ThrowColor);
            sports_detail::Ring(F,B.X,B.Y,11,B.PowerBall ? Yellow : White,3);
            if(B.PowerBall) F.AddCircle(B.X,B.Y,5,Yellow);
            for(const Particle& P:Data.Particles) F.AddCircle(P.X,P.Y,std::trunc(P.Size),P.Tint);
            F.AddText(60,5,std::string("YOU (")+Countries[Data.SelectedCountry].Name+"): "+std::to_string(Data.HumanScore),Blue,22);
            F.AddText(535,5,std::string("CPU (")+Countries[Data.OpponentCountry].Name+"): "+std::to_string(Data.CpuScore),Red,22);
            F.AddText(350,10,"ROUND "+std::to_string(Data.Round),Yellow,16);
            F.AddText(155,575,"Move trio; Fire throw/catch; Up charge; Jump",White,17);
        } else if(Data.Mode==Phase::CountrySelect) {
            F.AddText(135,65,"CHOOSE YOUR COUNTRY",White,38);
            for(int N=0;N<8;++N) F.AddText(310,135+N*42,std::string(N==Data.SelectedCountry ? "> " : "  ")+Countries[N].Name,Countries[N].Tint,24);
            F.AddText(200,510,"Up / Down selects; Fire / Action confirms",White,20);
        } else if(Data.Mode==Phase::Title) {
            F.AddText(160,145,"SUPER DODGE BALL",Yellow,42);F.AddText(250,205,"TOURNAMENT EDITION",White,24);
            F.AddText(190,265,"8 countries - 3 vs 3 - four rounds",White,20);
            F.AddText(195,340,"Fire / Action to choose country",White,26);
            F.AddText(170,405,"Move: arrows / stick; Fire: throw / catch",White,20);
            F.AddText(230,445,"Jump evades; Up charges throw",White,20);
        } else {
            F.AddText(145,230,Data.Mode==Phase::Won ? "YOU WIN THE MATCH!" : "YOU LOSE THE MATCH!",Data.Mode==Phase::Won ? Yellow : Red,40);
            F.AddText(280,310,"Score: "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore),White,26);
            F.AddText(220,360,"Round "+std::to_string(Data.Round)+" of 4",White,24);
            F.AddText(190,410,"Fire / Action to continue tournament",White,22);
        }
    }
};
}} // daedalus::desktop
