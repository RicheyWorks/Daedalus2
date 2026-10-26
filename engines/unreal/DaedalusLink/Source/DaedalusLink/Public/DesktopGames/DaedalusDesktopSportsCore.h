// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <cmath>
#include <sstream>
#include <string>

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
    enum class GoalScorer { None, Human, Cpu };
    enum class KickReceipt { None, Accepted, Cooldown };
    static constexpr int GoalReceiptFrames=90,KickReceiptFrames=12;
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
    void Reset(std::uint32_t) override {
        Data=State{};ClearFeedback();PracticeStage=PracticePhase::Aim;FlightFrames=0;PracticeNotice.clear();
        if(Option==1) { RackPractice();Data.Mode=Phase::Title; }
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    // Checkpoint save: mode, scores and whole seconds left. Restore re-racks the
    // kick-off (ball and players at their spots). Title and finished runs are not saved.
    std::string SaveState() const override {
        if(Data.Mode!=Phase::Playing) return {};
        return "DFS1 "+std::to_string(Option)+" "+std::to_string(Data.HumanScore)+" "+std::to_string(Data.CpuScore)
            +" "+std::to_string(Option==1?0:static_cast<int>(std::ceil(Data.Seconds)));
    }
    bool RestoreState(const std::string& Payload,std::uint32_t Seed) override {
        if(Payload.size()>128) return false;
        std::istringstream In(Payload);std::string Version,Extra;long long Mode=-1,Human=-1,Cpu=-1,Secs=-1;
        if(!(In>>Version>>Mode>>Human>>Cpu>>Secs) || Version!="DFS1" || (In>>Extra)) return false;
        if(Mode==0 && (Human<0 || Cpu<0 || Human>999 || Cpu>999 || Secs<1 || Secs>90)) return false;
        if(Mode==1 && (Human<0 || Human>2 || Cpu!=0 || Secs!=0)) return false;
        if(Mode!=0 && Mode!=1) return false;
        Option=static_cast<int>(Mode);Reset(Seed);
        if(Option==1) RackPractice(); else Data.Mode=Phase::Playing;
        Data.HumanScore=static_cast<int>(Human);Data.CpuScore=static_cast<int>(Cpu);
        if(Option==0) Data.Seconds=static_cast<double>(Secs);
        return true;
    }
    static void MovePlayer(Player& P,const Input& I,const Ball& B) {
        // Mirror the existing Slate hat merge for direct portable/Blueprint input.
        // Right/down precedence and the original stick override stay unchanged.
        Input Controls=I;
        Controls.Left=I.Left || I.PadLeft; Controls.Right=I.Right || I.PadRight;
        Controls.Up=I.Up || I.PadUp; Controls.Down=I.Down || I.PadDown;
        Vec D=P.Cpu ? sports_detail::Unit(B.X-P.X,B.Y-P.Y) : sports_detail::Direction(Controls);
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
        if(Option==1) { StepPractice(I);return; }
        if(Data.Mode!=Phase::Playing) {
            if(!(I.FirePressed || I.ActionPressed)) return;
            Data=State{};Data.Mode=Phase::Playing;ClearFeedback();
        } else {
            if(GoalCueFrames>0) --GoalCueFrames;
            if(KickCueFrames>0 && --KickCueFrames==0) LastKick=KickReceipt::None;
            if(I.FirePressed) {
                LastKick=Kick(Data.Human,Data.Football)?KickReceipt::Accepted:KickReceipt::Cooldown;
                KickCueFrames=KickReceiptFrames;
            }
        }
        MovePlayer(Data.Human,I,Data.Football);MovePlayer(Data.Cpu,I,Data.Football);
        UpdateBall(Data.Football);Deflect(Data.Human,Data.Football);Deflect(Data.Cpu,Data.Football);
        const bool LeftGoal=Data.Football.X<50 && Data.Football.Y>220 && Data.Football.Y<380;
        const bool RightGoal=Data.Football.X>750 && Data.Football.Y>220 && Data.Football.Y<380;
        if(LeftGoal || RightGoal) {
            if(LeftGoal) ++Data.CpuScore; else ++Data.HumanScore;
            Data.Football=Ball{};Data.Human.X=200;Data.Human.Y=300;Data.Cpu.X=600;Data.Cpu.Y=300;
            LastScorer=LeftGoal?GoalScorer::Cpu:GoalScorer::Human;GoalCueFrames=GoalReceiptFrames;
            LastKick=KickReceipt::None;KickCueFrames=0;
            // Receipt only: the source's immediate reset, live movement and
            // clock continue unchanged. Goal reset retains source kick cooldowns.
        }
        Data.Seconds-=1.0/60.0;
        if(Data.Seconds<=0) {
            Data.Seconds=0; // Safe display; source otherwise shows a negative final fraction.
            Data.Mode=Data.HumanScore>Data.CpuScore ? Phase::Won :
                      (Data.CpuScore>Data.HumanScore ? Phase::Lost : Phase::Draw);
        }
    }
    Status GetStatus() const override {
        if(Option==1) return {Data.HumanScore,0,Data.Mode==Phase::Won,Data.Mode==Phase::Won,
            "Target practice "+std::to_string(Data.HumanScore)+"/3. "+PracticeText()};
        const bool End=Data.Mode==Phase::Won || Data.Mode==Phase::Lost || Data.Mode==Phase::Draw;
        std::string Text;
        if(Data.Mode==Phase::Title) Text="Football: fresh Fire/Action starts a 90-second match. Move: keys/stick/hat; attack right.";
        else if(End) Text=ResultText()+" Final score "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore)
            +". Fresh Fire/Action plays again; host R/Restart returns to title.";
        else {
            Text="YOU "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore)+" CPU | "
                +std::to_string(static_cast<int>(Data.Seconds))+"s | "+KickReadiness()+". Attack right; source kicks work from any distance.";
            if(GoalCueFrames>0) Text+=" "+GoalText();
            if(KickCueFrames>0) Text+=" "+KickText();
        }
        return {Data.HumanScore,0,End,Data.Mode==Phase::Won,Text};
    }
    bool IsKickReady() const { return Data.Mode==Phase::Playing && Data.Human.KickCooldown==0 && (Option==0 || PracticeStage==PracticePhase::Aim); }
    int GoalReceiptFramesRemaining() const { return GoalCueFrames; }
    int KickReceiptFramesRemaining() const { return KickCueFrames; }
    GoalScorer GetLastScorer() const { return LastScorer; }
    KickReceipt GetLastKickReceipt() const { return LastKick; }
    std::string HowToLine() const override { return "HOW Move the player and kick the ball into the goal."; }
    void Render(Frame& F) const override {
        if(Option==1) { RenderPractice(F);return; }
        constexpr Color Green{0,128,0,255},Blue{30,100,255,255},Red{255,50,50,255};
        F.Clear(800,600,Green);
        F.AddRect(0,0,800,34,{0,65,0,255});
        sports_detail::Ring(F,400,300,60,White,3);F.AddCircle(400,300,8,White);
        F.AddLine(400,40,400,560,White,3);
        sports_detail::Outline(F,30,220,20,160,White,4);sports_detail::Outline(F,750,220,20,160,White,4);
        sports_detail::Outline(F,30,150,120,300,White,3);sports_detail::Outline(F,650,150,120,300,White,3);
        if(Data.Mode==Phase::Playing) {
            F.AddText(35,195,"DEFEND",White,13);F.AddText(680,195,"ATTACK",White,13);
            if(GoalCueFrames>0) {
                const bool HumanGoal=LastScorer==GoalScorer::Human;
                const Color Cue=HumanGoal?Color{180,220,255,255}:Color{255,180,180,255};
                sports_detail::Outline(F,HumanGoal?750:30,220,20,160,Cue,6);
                F.AddRect(230,70,365,32,{0,50,0,230});F.AddText(245,76,GoalText(),Cue,16);
            }
            F.AddCircle(Data.Human.X,Data.Human.Y,12,Blue);sports_detail::Ring(F,Data.Human.X,Data.Human.Y,12,White);
            if(KickCueFrames>0) sports_detail::Ring(F,Data.Human.X,Data.Human.Y,18,
                LastKick==KickReceipt::Accepted?Color{255,235,100,255}:Color{255,180,100,255},3);
            F.AddCircle(Data.Cpu.X,Data.Cpu.Y,12,Red);sports_detail::Ring(F,Data.Cpu.X,Data.Cpu.Y,12,White);
            F.AddCircle(Data.Football.X,Data.Football.Y,8,White);sports_detail::Ring(F,Data.Football.X,Data.Football.Y,8,Black);
            F.AddText(25,5,"YOU: "+std::to_string(Data.HumanScore),Blue,24);
            F.AddText(640,5,"CPU: "+std::to_string(Data.CpuScore),Red,24);
            F.AddText(340,5,"TIME: "+std::to_string(static_cast<int>(Data.Seconds)),White,24);
            F.AddText(25,565,"Move: WASD/arrows/stick/hat  Kick: Space/J/Z/X or pad A/X (fresh press)",White,13);
            F.AddText(25,583,KickReadiness()+" | "+(KickCueFrames>0?KickText():"Attack RIGHT; source kicks work from any distance."),White,12);
        } else if(Data.Mode==Phase::Title) {
            F.AddText(270,160,"FOOTBALL",White,48);F.AddText(235,235,"1980s STYLE FOOTBALL",White,24);
            F.AddText(170,320,"Fresh Fire / Action: kick off",White,26);
            F.AddText(150,380,"Move: WASD/arrows/stick/hat. Attack the RIGHT goal.",White,17);
            F.AddText(190,410,"Kick: Space/J/Z/X or pad A/X; fresh press.",White,17);
            F.AddText(185,445,"90 seconds. Source kicks work from any distance.",White,17);
            F.AddText(150,475,HowToLine(),{255,236,180,255},16);
        } else {
            F.AddText(255,230,ResultText(),White,42);
            F.AddText(260,310,"Final score: "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore),White,26);
            F.AddText(170,375,"Fresh Fire / Action: play again",White,24);
            F.AddText(240,415,"Host R / Restart: title",White,18);
            if(GoalCueFrames>0) F.AddText(260,450,LastScorer==GoalScorer::Human?"Last goal: YOU":"Last goal: CPU",White,16);
        }
    }
private:
    enum class PracticePhase { Aim, Flight, Feedback };
    inline static constexpr std::array<double,3> PracticeTargets{{300,250,350}};
    int Option=0,FlightFrames=0;
    PracticePhase PracticeStage=PracticePhase::Aim;
    std::string PracticeNotice;
    double PracticeTarget() const { return PracticeTargets[static_cast<std::size_t>(std::max(0,std::min(2,Data.HumanScore)))]; }
    const char* PracticePocket() const { return Data.HumanScore==0?"middle":(Data.HumanScore==1?"upper":"lower"); }
    void RackPractice() {
        Data.Human=Player{560,300,3.5,false,0};Data.Football=Ball{600,300,0,0};
        Data.CpuScore=0;Data.Seconds=0;Data.Mode=Phase::Playing;
        PracticeStage=PracticePhase::Aim;FlightFrames=0;PracticeNotice.clear();ClearFeedback();
    }
    void PracticeResult(bool Hit,const char* Notice) {
        if(Hit) Data.HumanScore=std::min(3,Data.HumanScore+1);
        PracticeNotice=Notice;PracticeStage=PracticePhase::Feedback;
        LastScorer=Hit?GoalScorer::Human:GoalScorer::None;GoalCueFrames=60;
        LastKick=KickReceipt::None;KickCueFrames=0;
        if(Data.HumanScore==3) Data.Mode=Phase::Won;
    }
    void StepPractice(const Input& I) {
        if(Data.Mode!=Phase::Playing) {
            if(!(I.FirePressed || I.ActionPressed)) return;
            Data=State{};RackPractice();return; // One fresh press enters Aim; it never kicks too.
        }
        if(I.ActionPressed) { RackPractice();return; }
        if(PracticeStage==PracticePhase::Feedback) {
            if(I.FirePressed || (GoalCueFrames>0 && --GoalCueFrames==0)) RackPractice();
            return;
        }
        if(KickCueFrames>0 && --KickCueFrames==0) LastKick=KickReceipt::None;
        MovePlayer(Data.Human,I,Data.Football);
        if(PracticeStage==PracticePhase::Aim) {
            if(I.FirePressed) {
                LastKick=Kick(Data.Human,Data.Football)?KickReceipt::Accepted:KickReceipt::Cooldown;
                KickCueFrames=KickReceiptFrames;
                if(LastKick==KickReceipt::Accepted) { PracticeStage=PracticePhase::Flight;FlightFrames=0; }
            }
            return; // Launch velocity is set now; flight physics starts next frame.
        }
        UpdateBall(Data.Football);Deflect(Data.Human,Data.Football);++FlightFrames;
        const bool LeftGoal=Data.Football.X<50 && Data.Football.Y>220 && Data.Football.Y<380;
        const bool RightGoal=Data.Football.X>750 && Data.Football.Y>220 && Data.Football.Y<380;
        if(RightGoal) {
            const bool Hit=std::abs(Data.Football.Y-PracticeTarget())<=22;
            PracticeResult(Hit,Hit?"Gold pocket hit! Your progress is kept.":"That goal missed the gold pocket. Targets kept; try again.");
        } else if(LeftGoal) PracticeResult(false,"Aim at the right goal. Targets kept; try again.");
        else if(std::hypot(Data.Football.Vx,Data.Football.Vy)<=.12) PracticeResult(false,"The ball slowed down. Targets kept; try again.");
        else if(FlightFrames>=240) PracticeResult(false,"Ready for another shot? Targets kept; try again.");
    }
    std::string PracticeText() const {
        if(Data.Mode==Phase::Title) return "Fresh Fire/Action starts aiming. Hit three gold pockets; no clock or opponent.";
        if(Data.Mode==Phase::Won) return "All three targets reached! Fresh Fire/Action tries again; R/Restart returns to title.";
        if(PracticeStage==PracticePhase::Feedback) return PracticeNotice+" Fresh Fire/Action continues without kicking.";
        if(PracticeStage==PracticePhase::Flight) return "Ball in flight: one kick per shot. Move to nudge it; Action resets this shot and keeps targets.";
        return std::string("Aim for the ")+PracticePocket()+" gold pocket. Move behind the ball; fresh Fire kicks, Action resets this shot.";
    }
    void RenderPractice(Frame& F) const {
        constexpr Color Green{0,128,0,255},Blue{30,100,255,255},Gold{255,210,70,255},Mint{90,220,160,255},Muted{85,125,100,255};
        F.Clear(800,600,Green);F.AddRect(0,0,800,48,{0,65,0,255});
        sports_detail::Ring(F,400,300,60,White,3);F.AddCircle(400,300,8,White);F.AddLine(400,40,400,560,White,3);
        sports_detail::Outline(F,30,220,20,160,White,4);sports_detail::Outline(F,750,220,20,160,White,4);
        sports_detail::Outline(F,30,150,120,300,White,3);sports_detail::Outline(F,650,150,120,300,White,3);
        for(int N=0;N<3;++N) {
            const double Y=PracticeTargets[static_cast<std::size_t>(N)];
            const Color Tint=N<Data.HumanScore?Mint:(N==Data.HumanScore?Gold:Muted);
            F.AddRect(750,Y-22,20,44,Tint);F.AddText(753,Y-8,std::to_string(N+1),Black,12);
        }
        if(Data.Mode==Phase::Playing && PracticeStage==PracticePhase::Aim) {
            const auto D=sports_detail::Unit(Data.Football.X-Data.Human.X,Data.Football.Y-Data.Human.Y);
            if(D.X!=0 || D.Y!=0) F.AddLine(Data.Football.X,Data.Football.Y,Data.Football.X+D.X*32,Data.Football.Y+D.Y*32,Gold,2);
        }
        F.AddCircle(Data.Human.X,Data.Human.Y,12,Blue);sports_detail::Ring(F,Data.Human.X,Data.Human.Y,12,White);
        F.AddCircle(Data.Football.X,Data.Football.Y,8,White);sports_detail::Ring(F,Data.Football.X,Data.Football.Y,8,Black);
        F.AddText(24,10,"TARGET PRACTICE",White,24);F.AddText(520,10,"Targets "+std::to_string(Data.HumanScore)+"/3",Gold,24);
        std::string Caption,Controls;
        if(Data.Mode==Phase::Title) { Caption="Find your angle. Hit the gold pockets in order.";Controls="Fresh Space/J or pad A/X: start aiming. The short line shows the first kick direction."; }
        else if(Data.Mode==Phase::Won) { Caption="All three targets reached!";Controls="Space/J/pad A/X or K/Enter/pad B: replay. R/Restart: title."; }
        else if(PracticeStage==PracticePhase::Feedback) { Caption=PracticeNotice;Controls="Next setup soon. Space/J/pad A/X or K/Enter/pad B: next ball; no kick."; }
        else if(PracticeStage==PracticePhase::Flight) { Caption="Ball in flight: one kick per shot.";Controls="Move to nudge the ball. K/Enter/pad B resets this shot; targets are kept."; }
        else { Caption=std::string("Aim at the GOLD ")+PracticePocket()+" pocket.";Controls="Stand behind the ball. The short line shows the first direction, not a full path."; }
        F.AddText(24,64,Caption,White,18);
        F.AddText(24,565,"Move: WASD/arrows/stick/hat. Space/J or pad A/X: kick. K/Enter/pad B: reset shot.",White,13);
        F.AddText(24,583,Controls,White,12);
    }
    GoalScorer LastScorer=GoalScorer::None;
    KickReceipt LastKick=KickReceipt::None;
    int GoalCueFrames=0,KickCueFrames=0;
    void ClearFeedback() {
        LastScorer=GoalScorer::None;LastKick=KickReceipt::None;GoalCueFrames=KickCueFrames=0;
    }
    std::string ResultText() const {
        return Data.Mode==Phase::Won?"YOU WIN!":(Data.Mode==Phase::Lost?"CPU WINS!":"IT'S A DRAW!");
    }
    std::string KickReadiness() const {
        return Data.Human.KickCooldown==0?"Kick READY":"Kick wait "+std::to_string(Data.Human.KickCooldown)+" steps";
    }
    std::string GoalText() const { return LastScorer==GoalScorer::Human?"YOU scored; play continues.":"CPU scored; play continues."; }
    std::string KickText() const {
        // Acceptance describes the input receipt. Later contact deflection may
        // overwrite the same step's velocity; this is not a trajectory promise.
        return LastKick==KickReceipt::Accepted?"Kick press accepted.":"Kick press ignored: cooldown.";
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
    bool UpWasDown=false,DownWasDown=false,CountryStickArmed=false;
    int Option=0;
    int PassReceiver=-1;
    int NextPassTarget(int Owner) const {
        if(Owner<0 || Owner>=3) return -1;
        for(int Offset=1;Offset<3;++Offset) {
            const int Next=(Owner+Offset)%3;
            if(Data.Players[Next].Health>0) return Next;
        }
        return -1;
    }
    bool TryHumanPass() {
        const int Owner=HumanBallHolder();
        if(Owner<0 || Data.DodgeBall.InAir || Data.Players[Owner].ThrowCooldown>0) return false;
        const int Target=NextPassTarget(Owner);
        if(Target<0) return false;
        Ball Flight=Data.DodgeBall;
        UpdateBall(Flight,Data.Players); // Attach the valid holder before aiming from the hand.
        const auto& Receiver=Data.Players[Target];
        const Vec D=sports_detail::Unit(Receiver.X-Flight.X,Receiver.Y-Flight.Y);
        if(D.X==0 && D.Y==0) return false; // No flight direction; keep the existing possession intact.
        if(!Throw(Flight,Data.Players[Owner],D,false)) return false;
        Data.DodgeBall=Flight;PassReceiver=Target;return true;
    }
    static bool CountryStickCentered(const Input& I) {
        return std::abs(Axis(I.AxisX))<=0.3 && std::abs(Axis(I.AxisY))<=0.3;
    }
    int CountryStickStep(const Input& I) {
        if(CountryStickCentered(I)) {CountryStickArmed=true;return 0;}
        const double Y=Axis(I.AxisY);
        if(!CountryStickArmed || std::abs(Y)<=0.6) return 0;
        CountryStickArmed=false;return Y<0?-1:1;
    }
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
        if(!P.HasBall) PassReceiver=-1;
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
        UpWasDown=DownWasDown=CountryStickArmed=false;
        PassReceiver=-1;
        Data.SelectedCountry=Option; // Option presets the country cursor; select still confirms.
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>=static_cast<int>(Countries.size())) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    // Checkpoint save during play: countries, tournament score and round. Restore
    // replays the current round from kickoff. Title, country select and round results are not saved.
    std::string SaveState() const override {
        if(Data.Mode!=Phase::Playing) return {};
        return "DBS1 "+std::to_string(Data.SelectedCountry)+" "+std::to_string(Data.OpponentCountry)+" "
            +std::to_string(Data.HumanScore)+" "+std::to_string(Data.CpuScore)+" "+std::to_string(Data.Round);
    }
    bool RestoreState(const std::string& Payload,std::uint32_t Seed) override {
        if(Payload.size()>128) return false;
        std::istringstream In(Payload);std::string Version,Extra;long long Mine=-1,Theirs=-1,Wins=-1,Losses=-1,Turn=-1;
        if(!(In>>Version>>Mine>>Theirs>>Wins>>Losses>>Turn) || Version!="DBS1" || (In>>Extra)) return false;
        const long long Last=static_cast<long long>(Countries.size())-1;
        if(Mine<0 || Mine>Last || Theirs<0 || Theirs>Last || Mine==Theirs || Turn<1 || Turn>4
            || Wins<0 || Losses<0 || Wins+Losses!=Turn-1) return false;
        Reset(Seed);
        Data.SelectedCountry=static_cast<int>(Mine);Data.OpponentCountry=static_cast<int>(Theirs);
        Data.HumanScore=static_cast<int>(Wins);Data.CpuScore=static_cast<int>(Losses);Data.Round=static_cast<int>(Turn);
        StartMatch();
        return true;
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
        PassReceiver=-1;
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
        if(!Data.DodgeBall.InAir || Data.DodgeBall.Owner>=0) PassReceiver=-1;
        const bool Guarding=I.Dash && !I.FirePressed; // A fresh throw retains its complete legacy catch/rethrow ordering.
        const bool Confirm=I.FirePressed || I.ActionPressed;
        const bool AnyButton=Confirm || I.JumpPressed || I.DashPressed;
        const bool UpDown=I.Up || I.PadUp,DownDown=I.Down || I.PadDown;
        const bool UpPressed=UpDown && !UpWasDown,DownPressed=DownDown && !DownWasDown;
        UpWasDown=UpDown;DownWasDown=DownDown;
        if(Data.Mode==Phase::Title) {
            if(AnyButton || std::abs(Axis(I.AxisX))>0.6 || std::abs(Axis(I.AxisY))>0.6) {
                Data.Mode=Phase::CountrySelect;
                CountryStickArmed=CountryStickCentered(I); // Consume a stick gesture that opened the picker.
            }
            return;
        }
        if(Data.Mode==Phase::CountrySelect) {
            const int StickStep=CountryStickStep(I); // Consume even when a simultaneous digital edge wins.
            if(UpPressed) Data.SelectedCountry=(Data.SelectedCountry+7)%8;
            else if(DownPressed) Data.SelectedCountry=(Data.SelectedCountry+1)%8;
            else if(StickStep!=0) Data.SelectedCountry=(Data.SelectedCountry+8+StickStep)%8;
            if(!Confirm) return;
            Data.OpponentCountry=Opponent();Data.HumanScore=Data.CpuScore=0;Data.Round=1;StartMatch();
        } else if(Data.Mode==Phase::Won || Data.Mode==Phase::Lost) {
            if(!AnyButton) return;
            if(Data.Round>=4) { Data.Mode=Phase::Title;Data.Round=1;return; }
            ++Data.Round;Data.OpponentCountry=Opponent();StartMatch();
        } else {
            // Only a step that began Playing can pass. A valid deliberate pass wins a simultaneous throw press.
            const bool Passed=I.DashPressed && TryHumanPass();
            if(!Passed && I.FirePressed) for(int N=0;N<3;++N) if(Data.Players[N].HasBall && Data.Players[N].ThrowCooldown==0) {
                AimAndThrow(N);break;
            }
        }
        for(int N=0;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.Health<=0) { P.HasBall=false;continue; }
            if(P.Cpu) MoveCpu(N);else MoveHuman(P,I);
            BoundAndCooldown(P);
        }
        Ball& B=Data.DodgeBall;UpdateBall(B,Data.Players);
        if(!B.InAir || B.Owner>=0) PassReceiver=-1;
        RecoverLooseBall(B);
        if(B.Owner<0 && !B.InAir) for(int N=0;N<6;++N) if(Pickup(B,Data.Players[N],N)) break;
        if(IsTeamPassInFlight()) {
            Player& Receiver=Data.Players[PassReceiver];
            if(Catch(B,Receiver,PassReceiver)) {
                PassReceiver=-1;
                Receiver.ThrowCooldown=std::max(Receiver.ThrowCooldown,14);
                Burst(Receiver.X,Receiver.Y,{255,255,200,255},8,2.5);
            }
        }
        if(B.InAir && !IsTeamPassInFlight()) for(int N=0;N<3;++N) {
            Player& P=Data.Players[N];const double Radius=P.OnGround ? 22 : 35;
            if(P.Health>0 && !P.HasBall && Distance(B.X,B.Y,P.X,P.Y)<Radius && (!P.OnGround || I.Fire || Guarding)) {
                if(Catch(B,P,N)) { Burst(P.X,P.Y,{255,255,200,255},8,2.5);break; }
            }
        }
        if(B.InAir) for(int N=3;N<6;++N) {
            Player& P=Data.Players[N];
            if(P.Health>0 && !P.HasBall && Rng.Unit()<0.12 && Catch(B,P,N)) {PassReceiver=-1;break;}
        }
        // Holding the pass/catch control keeps possession; a fresh throw above is still explicit.
        if(I.Fire && !Guarding) for(int N=0;N<3;++N) if(Data.Players[N].HasBall && Data.Players[N].ThrowCooldown==0) {
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
            if(N<3 && IsTeamPassInFlight()) continue; // Teammate passes never deal friendly damage.
            if(P.Health>0 && Distance(B.X,B.Y,P.X,P.Y)<18) {
                const bool Power=B.PowerBall;const double X=B.X,Y=B.Y;const Color Tint=B.ThrowColor;
                if(Hit(B,P)) { PassReceiver=-1;Burst(X,Y,Tint,Power ? 15 : 8,4);MatchResult();break; }
            }
        }
        for(Particle& P:Data.Particles) {
            P.X+=P.Vx;P.Y+=P.Vy;P.Vx*=0.92;P.Vy*=0.92;--P.Life;P.Size=std::max(1.0,P.Size*0.95);
        }
        Data.Particles.erase(std::remove_if(Data.Particles.begin(),Data.Particles.end(),
            [](const Particle& P){return P.Life<=0;}),Data.Particles.end());
    }
    // Read-only gameplay/feedback state. Selectors match the actual recipients
    // and never consume randomness.
    int LivingPlayers(bool Cpu=false) const {
        int Count=0;const int Start=Cpu?3:0;
        for(int N=Start;N<Start+3;++N) if(Data.Players[N].Health>0) ++Count;
        return Count;
    }
    int TeamHealth(bool Cpu=false) const {
        int Health=0;const int Start=Cpu?3:0;
        for(int N=Start;N<Start+3;++N) Health+=Data.Players[N].Health;
        return Health;
    }
    int HumanBallHolder() const {
        const int Owner=Data.DodgeBall.Owner;
        return Owner>=0 && Owner<3 && Data.Players[Owner].Health>0 && Data.Players[Owner].HasBall?Owner:-1;
    }
    bool IsTeamPassInFlight() const {
        return Data.Mode==Phase::Playing && PassReceiver>=0 && PassReceiver<3 && Data.DodgeBall.InAir && Data.DodgeBall.Owner<0;
    }
    int HumanPassTarget() const {
        if(Data.Mode!=Phase::Playing) return -1;
        if(IsTeamPassInFlight()) return Data.Players[PassReceiver].Health>0?PassReceiver:-1;
        return Data.DodgeBall.InAir?-1:NextPassTarget(HumanBallHolder());
    }
    bool IsHumanThrowReady() const {
        const int Owner=HumanBallHolder();
        return Data.Mode==Phase::Playing && Owner>=0 && Data.Players[Owner].ThrowCooldown==0 && Nearest(Owner)>=0;
    }
    bool IsHumanSuperCharged() const {
        const int Owner=HumanBallHolder();
        return Data.Mode==Phase::Playing && Owner>=0 && Data.Players[Owner].Charge>30;
    }
    int JumpReadyPlayers() const {
        if(Data.Mode!=Phase::Playing) return 0;
        int Count=0;
        for(int N=0;N<3;++N) { const Player& P=Data.Players[N];
            if(P.Health>0 && P.OnGround && P.JumpCooldown<=0) ++Count;
        }
        return Count;
    }
    int AirbornePlayers() const {
        int Count=0;for(int N=0;N<3;++N) if(Data.Players[N].Health>0 && !Data.Players[N].OnGround) ++Count;
        return Count;
    }
    double HumanCatchRadius(int Index) const {
        if(Index<0 || Index>=3 || Data.Mode!=Phase::Playing || !Data.DodgeBall.InAir) return 0;
        const Player& P=Data.Players[Index];
        if(P.Health<=0 || P.HasBall) return 0;
        // Both Step's gate and Catch's radius apply: <22 normal, <18 super,
        // <34 airborne. Ground catches require held Fire or Dash; airborne is automatic.
        return !P.OnGround?34.0:(Data.DodgeBall.PowerBall?18.0:22.0);
    }
    Status GetStatus() const override {
        const bool End=Data.Mode==Phase::Won || Data.Mode==Phase::Lost;
        std::string Text;
        if(Data.Mode==Phase::Title) Text="Courtyard Clash: Space/Enter/pad A chooses a country for four rounds. All three living humans share movement and jump. Host R/Restart clears the tournament.";
        else if(Data.Mode==Phase::CountrySelect) Text=std::string("Selected ")+Countries[Data.SelectedCountry].Name
            +" | "+CountryStats()+" | Up/Down, hat or stick flick selects; center stick between choices. Fresh Fire/Action confirms. Random opponents may repeat.";
        else {
            Text="Round "+std::to_string(Data.Round)+"/4 | "+Countries[Data.SelectedCountry].Name+" vs "+Countries[Data.OpponentCountry].Name
                +" | Match wins "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore)
                +" | YOU "+std::to_string(LivingPlayers())+" alive / "+std::to_string(TeamHealth())+" HP, CPU "
                +std::to_string(LivingPlayers(true))+" alive / "+std::to_string(TeamHealth(true))+" HP. ";
            if(End) {
                if(Data.Round>=4) Text+=TournamentResultText()+" ";
                Text+=(Data.Mode==Phase::Won?"YOU won this match. ":"CPU won this match. ")+ContinueText()
                    +" Host R/Restart clears the tournament.";
            }
            else Text+=BallReadiness()+" | "+JumpReadiness()
                +". Move the trio together. Held Space/Z/J/pad A catches and can immediately rethrow; pad X/RB throws on fresh press. "
                +"Charge: keyboard Up/W or original stick up beyond 0.5; hat movement alone does not charge. "
                +"Hold V/Y/LB to catch and keep the ball, even with Fire held. Let go of Fire first, then release and press V/Y/LB again to pass; a fresh Fire press while carrying still throws. "
                +"Ground catch is <22 normal / <18 super pixels; airborne catch is automatic at <34. Attack throws can hit teammates; V/Y/LB passes are safe.";
        }
        return {Data.HumanScore,LivingPlayers(),End,Data.Mode==Phase::Won,Text};
    }
    std::string HintLine() const {
        if(Data.Mode==Phase::Title) return "HINT Press Space, Enter, or pad A to open the country list.";
        if(Data.Mode==Phase::CountrySelect) return "HINT Up and Down change country. A fresh Fire press confirms.";
        if(Data.Mode==Phase::Playing) {
            if(Data.DodgeBall.InAir) return "HINT Hold Fire or Dash on the ground to catch. A jump catches in range.";
            return "HINT The trio moves together. Hold Up to charge, then throw.";
        }
        if(Data.Round>=4) return "HINT Confirm a country to start a fresh four-round score.";
        return "HINT Press Fire to start the next round.";
    }
    std::string ActionCue() const {
        if(Data.Mode==Phase::Title) return "CUE Countries";
        if(Data.Mode==Phase::CountrySelect) return "CUE Confirm";
        if(Data.Mode==Phase::Playing) return Data.DodgeBall.InAir ? "CUE Catch" : "CUE Charge";
        if(Data.Round>=4) return "CUE New score";
        return "CUE Next round";
    }
    void DrawPlayer(Frame& F,const Player& P) const {
        constexpr Color Yellow{255,220,50,255},Red{220,50,50,255};
        if(P.Health<=0) { F.AddCircle(P.X,P.Y,10,{70,70,70,255});F.AddText(P.X-10,P.Y-8,"KO",White,14);return; }
        const Vec Picture=PlayerDrawPosition(P);const double X=Picture.X,Y=Picture.Y;
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
    std::string HowToLine() const override { return "HOW Lead the team, then throw or catch the ball."; }
    void Render(Frame& F) const override {
        constexpr Color Yellow{255,220,50,255},Red{220,50,50,255},Blue{50,100,220,255},PassTint{120,225,255,255};
        F.Clear();
        if(Data.Mode==Phase::Playing) {
            F.AddRect(40,40,720,520,{50,120,50,255});sports_detail::Outline(F,40,40,720,520,White,4);
            F.AddLine(400,40,400,560,White,4);sports_detail::Ring(F,400,300,50,White,3);
            F.AddText(165,50,Countries[Data.SelectedCountry].Name,White,16);
            F.AddText(565,50,Countries[Data.OpponentCountry].Name,White,16);
            const int Target=HumanThrowTarget();
            if(Target>=0) {
                const Vec Aim=PlayerDrawPosition(Data.Players[Target]);
                const Color Cue=IsHumanThrowReady()?Color{120,225,255,255}:Color{120,145,150,255};
                F.AddLine(Aim.X-22,Aim.Y-6,Aim.X-18,Aim.Y,Cue,2);
                F.AddLine(Aim.X-18,Aim.Y,Aim.X-22,Aim.Y+6,Cue,2);
                F.AddLine(Aim.X+22,Aim.Y-6,Aim.X+18,Aim.Y,Cue,2);
                F.AddLine(Aim.X+18,Aim.Y,Aim.X+22,Aim.Y+6,Cue,2);
            }
            const int Receiver=HumanPassTarget();
            if(IsTeamPassInFlight() && Receiver>=0) {
                const Vec Aim=PlayerDrawPosition(Data.Players[Receiver]);
                sports_detail::Ring(F,Aim.X,Aim.Y,23,PassTint,2);
            }
            for(int N=0;N<6;++N) {
                const Player& P=Data.Players[N];DrawPlayer(F,P);
                const double Y=PlayerDrawPosition(P).Y;
                F.AddText(P.X-9,Y+(P.Health>0?29:15),std::string(N<3?"P":"C")+std::to_string(N%3+1),White,11);
            }
            const Ball& B=Data.DodgeBall;F.AddCircle(B.X,B.Y,11,B.PowerBall ? Red : B.ThrowColor);
            sports_detail::Ring(F,B.X,B.Y,11,IsTeamPassInFlight()?PassTint:(B.PowerBall ? Yellow : White),3);
            if(B.PowerBall) F.AddCircle(B.X,B.Y,5,Yellow);
            for(const Particle& P:Data.Particles) F.AddCircle(P.X,P.Y,std::trunc(P.Size),P.Tint);
            F.AddText(16,5,std::string("YOU ")+Countries[Data.SelectedCountry].Name+": "+std::to_string(Data.HumanScore),Blue,18);
            F.AddText(535,5,std::string("CPU ")+Countries[Data.OpponentCountry].Name+": "+std::to_string(Data.CpuScore),Red,18);
            F.AddText(347,6,"ROUND "+std::to_string(Data.Round)+" / 4",Yellow,15);
            F.AddText(16,25,RosterText(false),White,10);F.AddText(535,25,RosterText(true),White,10);
            F.AddText(12,563,"Move ALL 3: keys/stick/hat | Jump: Shift/pad B | "+JumpReadiness(),White,11);
            F.AddText(12,576,BallReadiness(),IsHumanSuperCharged()?Yellow:White,11);
            F.AddText(12,589,"Space/Z/J/A: throw/rethrow | X/RB: fresh throw | Hold V/Y/LB: catch + keep | Charge: W/Up/stick up",White,11);
        } else if(Data.Mode==Phase::CountrySelect) {
            F.AddText(135,65,"CHOOSE YOUR COUNTRY",White,38);
            for(int N=0;N<8;++N) F.AddText(125,135+N*42,std::string(N==Data.SelectedCountry ? "> " : "  ")+Countries[N].Name,Countries[N].Tint,24);
            F.AddText(450,145,Countries[Data.SelectedCountry].Name,Countries[Data.SelectedCountry].Tint,26);
            F.AddText(450,190,CountryStats(),White,15);
            F.AddText(450,225,"3 players; each starts with 3 HP",White,15);
            F.AddText(450,265,CountrySuperText(),Yellow,14);
            F.AddText(450,305,"Four rounds; cumulative match wins",White,14);
            F.AddText(450,335,"Random opponents can repeat",White,14);
            F.AddText(125,495,"Select: W/S, arrows, hat or stick flick | Confirm: Space/Enter/pad A",White,17);
            F.AddText(125,530,"All three living teammates share your movement and jump.",White,15);
            F.AddText(125,555,"Friendly hits: normal 1 HP, super 2 HP. Host R clears the tournament.",White,14);
        } else if(Data.Mode==Phase::Title) {
            F.AddText(160,145,"COURTYARD CLASH",Yellow,42);F.AddText(195,205,"Auto-aim: nearest living opponent",White,20);
            F.AddText(190,265,"8 countries - 3 vs 3 - four rounds",White,20);
            F.AddText(150,340,"Space / Enter / pad A: choose country",White,24);
            F.AddText(120,400,"Move ALL 3: WASD/arrows, left stick or hat | Jump: Shift/pad B",White,16);
            F.AddText(120,435,"Throw: Space/J/A or X/RB | V/Y/LB: pass; hold to catch + keep",White,16);
            F.AddText(120,470,"Charge: hold keyboard Up/W or stick up; super at charge 31/60",White,16);
            F.AddText(120,505,"Hat moves independently; jumping catches automatically in range.",White,16);
            F.AddText(195,545,"Friendly hits are possible. Host R/Restart clears the session.",White,14);
        } else if(Data.Round>=4) {
            RenderTournamentResult(F);
        } else {
            F.AddText(145,230,Data.Mode==Phase::Won ? "YOU WIN THE MATCH!" : "YOU LOSE THE MATCH!",Data.Mode==Phase::Won ? Yellow : Red,40);
            F.AddText(260,285,std::string(Countries[Data.SelectedCountry].Name)+" vs "+Countries[Data.OpponentCountry].Name,White,22);
            F.AddText(250,325,"Match wins: "+std::to_string(Data.HumanScore)+" - "+std::to_string(Data.CpuScore),White,24);
            F.AddText(225,370,"Round "+std::to_string(Data.Round)+" of 4 complete",White,24);
            F.AddText(120,425,ContinueText(),White,18);
            F.AddText(150,465,Data.Round<4?"Next opponent is random; repeats are allowed.":"New country confirmation starts a fresh four-round score.",White,16);
            F.AddText(120,510,"Space/Enter/A/X/RB/B continues | Host R/Restart clears the tournament",White,14);
        }
        const double HintY=Data.Mode==Phase::Playing?36.0:578.0;
        F.AddText(16,HintY,HintLine(),Color{255,236,180,255},12);
        F.AddText(16,Data.Mode==Phase::Playing?20.0:8.0,HowToLine(),{255,236,180,255},12);
        F.AddText(560,HintY,ActionCue(),Color{120,225,255,255},12);
    }
private:
    std::string TournamentResultText() const {
        if(Data.HumanScore>Data.CpuScore) return "YOU WIN THE TOURNAMENT!";
        if(Data.HumanScore<Data.CpuScore) return "OPPONENTS WIN THE TOURNAMENT!";
        return "TOURNAMENT DRAW";
    }
    void RenderTournamentResult(Frame& F) const {
        constexpr Color Gold{255,220,50,255},Blue{110,170,255,255},Red{255,135,135,255};
        const Color Result=Data.HumanScore>Data.CpuScore?Gold:(Data.HumanScore<Data.CpuScore?Red:White);
        F.AddText(80,80,"TOURNAMENT COMPLETE",Gold,36);
        F.AddText(80,140,TournamentResultText(),Result,32);
        for(int Team=0;Team<2;++Team) {
            const double X=Team==0?70:430;
            const int Wins=Team==0?Data.HumanScore:Data.CpuScore;
            const Color Tint=Team==0?Blue:Red;
            F.AddRect(X,225,300,155,{25,35,50,255});
            F.AddText(X+20,240,Team==0?std::string("YOU / ")+Countries[Data.SelectedCountry].Name:"OPPONENTS",Tint,24);
            F.AddText(X+20,285,std::to_string(Wins)+" match wins",White,26);
            for(int N=0;N<4;++N) F.AddRect(X+20+N*60,335,52,12,N<Wins?Tint:Color{65,75,90,255});
        }
        F.AddText(80,410,std::string("Last match: ")+Countries[Data.SelectedCountry].Name+" vs "+Countries[Data.OpponentCountry].Name
            +(Data.Mode==Phase::Won?" - YOU won.":" - CPU won."),White,18);
        F.AddText(80,460,ContinueText(),White,16);
        F.AddText(80,495,"Choose a country again for a fresh four-round score.",White,16);
        F.AddText(80,550,"Space/Enter/A/X/RB/B continues | Host R/Restart clears the tournament",White,14);
    }
    static Vec PlayerDrawPosition(const Player& P) {
        return {std::trunc(P.X),std::trunc(P.Y)-std::trunc(P.OnGround?0:std::abs(P.JumpVelocity)*0.3)};
    }
    int HumanThrowTarget() const {
        if(Data.Mode!=Phase::Playing || Data.DodgeBall.InAir) return -1;
        const int Owner=HumanBallHolder();
        return Owner>=0?Nearest(Owner):-1;
    }
    std::string RosterText(bool Cpu) const {
        const int Start=Cpu?3:0;std::string Text;
        for(int N=0;N<3;++N) Text+=(N?"  ":"")+std::string(Cpu?"C":"P")+std::to_string(N+1)+":"
            +std::to_string(Data.Players[Start+N].Health);
        return Text+" | "+std::to_string(LivingPlayers(Cpu))+"/3 alive, "+std::to_string(TeamHealth(Cpu))+" HP";
    }
    std::string CountryStats() const {
        const Country& C=Countries[Data.SelectedCountry];
        return "Power "+std::to_string(static_cast<int>(std::lround(C.Power*100)))+"% | Speed "
            +std::to_string(static_cast<int>(std::lround(C.Speed*100)))+"%";
    }
    std::string CountrySuperText() const {
        constexpr const char* Text[8]={"Super: flatter throw","Super: two angle variants","Super: upward throw",
            "Super: 28-step recovery","Super: flatter throw","Super: 32-step recovery","Super: upward throw","Super: two angle variants"};
        return Text[Data.SelectedCountry];
    }
    std::string BallReadiness() const {
        if(IsTeamPassInFlight()) {
            const int Receiver=HumanPassTarget();
            return Receiver>=0?"PASS -> P"+std::to_string(Receiver+1)+" | automatic teammate catch"
                :"Pass in flight; receiver unavailable. Teammates are safe.";
        }
        const int Owner=HumanBallHolder();
        if(Owner>=0) {
            const Player& P=Data.Players[Owner];
            const std::string Ready=IsHumanThrowReady()?"throw READY":(P.ThrowCooldown>0?
                "throw wait "+std::to_string(P.ThrowCooldown)+" steps":"no living target");
            const int Target=HumanThrowTarget();
            const int Teammate=HumanPassTarget();
            return "P"+std::to_string(Owner+1)+": "+Ready+(Target>=0?" -> C"+std::to_string(Target-2):"")+" | charge "+std::to_string(P.Charge)+"/60"
                +(IsHumanSuperCharged()?" SUPER charged":"; SUPER at 31")
                +(Teammate>=0?" | pass V/Y -> P"+std::to_string(Teammate+1):" | no living teammate to pass to");
        }
        const Ball& B=Data.DodgeBall;
        if(B.Owner>=3 && B.Owner<6) return "C"+std::to_string(B.Owner-2)+" holds ball | Catch + keep: hold V/Y/LB; airborne catch: automatic";
        if(B.InAir) return std::string(B.PowerBall?"SUPER ball flying (2 HP)":"Normal ball flying (1 HP)")
            +" | Hold V/Y/LB: catch + keep (<"+(B.PowerBall?"18":"22")+"px); airborne: automatic (<34px)";
        return "Loose ball: approach to pick up (<24px) | Friendly hits remain possible";
    }
    std::string JumpReadiness() const {
        return "Jump READY "+std::to_string(JumpReadyPlayers())+"/"+std::to_string(LivingPlayers())
            +"; airborne "+std::to_string(AirbornePlayers());
    }
    std::string ContinueText() const {
        return Data.Round<4?"Fresh throw/confirm/jump: start round "+std::to_string(Data.Round+1)+" of 4."
            :"Four rounds complete. Fresh throw/confirm/jump: return to title.";
    }
};
}} // daedalus::desktop
