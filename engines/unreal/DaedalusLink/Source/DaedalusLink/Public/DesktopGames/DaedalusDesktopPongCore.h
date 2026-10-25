// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <limits>

namespace daedalus { namespace desktop {
class PongGame final : public Game {
    int Option=0;
    bool Practice() const { return Option==1 || Option==3; }
    bool QuickMatch() const { return Option==2; }
    bool TargetRally() const { return Option==3; }
    inline static constexpr std::array<Vec,3> TargetWindows{{{60,220},{230,390},{400,560}}};
public:
    struct State {
        double PlayerY=250, ComputerY=250, BallX=400, BallY=300, BallVX=5, BallVY=3;
        std::int64_t PlayerScore=0, ComputerScore=0;
        int ServeFrames=0, ContactFrames=0, PointFrames=0, LastPoint=0, LastContact=0;
        std::uint32_t Rally=0, BestRally=0;
    } S;
    void Reset(std::uint32_t) override { S=State{};if(Practice() || QuickMatch()) PrepareServe(0); }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>3) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    void Step(const Input& I) override {
        if(QuickMatchOver() || TargetRallyOver()) {
            if(I.FirePressed || I.JumpPressed || I.ActionPressed) Reset(0);
            return; // A deliberate rematch cannot also move a paddle or skip its serve.
        }
        if(S.ContactFrames>0) --S.ContactFrames;
        if(S.PointFrames>0) --S.PointFrames;
        const double PreviousPlayerY=S.PlayerY;
        const double PlayerLimit=Practice()?460:500;
        if((I.Up || I.PadUp) && S.PlayerY>0) S.PlayerY-=6;
        if((I.Down || I.PadDown) && S.PlayerY<PlayerLimit) S.PlayerY+=6;
        const double StickY=Axis(I.AxisY);
        if(std::abs(StickY)>0.2) S.PlayerY+=StickY*8;
        // Polish: keyboard overshoot cannot strand a paddle outside the playfield.
        S.PlayerY=Clamp(S.PlayerY,0,PlayerLimit);
        const double PaddleDelta=S.PlayerY-PreviousPlayerY;
        // Keep the source's two sequential AI tests, including its near-target quirk.
        if(!Practice()) {
            if(S.ComputerY+50<S.BallY) S.ComputerY+=4;
            if(S.ComputerY+50>S.BallY) S.ComputerY-=4;
            S.ComputerY=Clamp(S.ComputerY,0,500);
        }
        // Match opens immediately as in the source; practice prepares from Reset.
        // Both keep paddles controllable throughout a bounded serve window.
        if(S.ServeFrames>0) {
            if(I.FirePressed || I.JumpPressed || I.ActionPressed) S.ServeFrames=0;
            else --S.ServeFrames;
            return; // Launch on the following fixed frame, including an early serve.
        }
        S.BallX+=S.BallVX; S.BallY+=S.BallVY;
        // Match constants/collision windows retained. Direction checks deliberately
        // fix repeated flip-flops while a ball remains inside a paddle/wall window.
        if((S.BallY<=0 && S.BallVY<0) || (S.BallY>=590 && S.BallVY>0)) S.BallVY=-S.BallVY;
        const bool TouchesPlayer=Practice() ? S.BallY+8>=S.PlayerY && S.BallY-8<=S.PlayerY+140
            : S.BallY>S.PlayerY && S.BallY<S.PlayerY+100;
        if(S.BallVX<0 && S.BallX>50 && S.BallX<70 && TouchesPlayer) {
            S.BallVX=-S.BallVX;
            // Native play-loop polish: only actual movement at a player return
            // bends the shot. Neutral hits, CPU returns and serve rules stay intact.
            if(PaddleDelta!=0) {
                const double SpinLimit=Practice()?4:7;
                S.BallVY=Clamp(S.BallVY+0.5*PaddleDelta,-SpinLimit,SpinLimit);
            }
            RecordContact(1);
        }
        if(Practice()) {
            // Full-height return wall: its visible x=740 face meets the ball's radius8.
            if(S.BallVX>0 && S.BallX>=732) {
                S.BallX=732;S.BallVX=-S.BallVX;S.LastContact=-1;S.ContactFrames=8;
                if(TargetRally()) {
                    const Vec Window=TargetWindows[static_cast<std::size_t>(S.PlayerScore)];
                    if(S.BallY>=Window.X && S.BallY<=Window.Y) {
                        ++S.PlayerScore;S.PointFrames=90;S.LastPoint=1;
                        if(TargetRallyOver()) return;
                    }
                }
            }
        }
        else if(S.BallVX>0 && S.BallX>730 && S.BallX<750 && S.BallY>S.ComputerY && S.BallY<S.ComputerY+100) { S.BallVX=-S.BallVX; RecordContact(-1); }
        if(S.BallX<0) {
            if(!Practice() && S.ComputerScore<std::numeric_limits<std::int64_t>::max()) ++S.ComputerScore;
            PrepareServe(-1);
        }
        if(!Practice() && S.BallX>800) {
            if(S.PlayerScore<std::numeric_limits<std::int64_t>::max()) ++S.PlayerScore;
            PrepareServe(1);
        }
    }
    Status GetStatus() const override {
        if(TargetRally()) {
            const bool End=TargetRallyOver();
            std::string Note="Target rally; "+std::to_string(S.PlayerScore)+"/3 windows cleared";
            if(End) Note+=". Space/pad A or R: replay.";
            else Note+=(S.ServeFrames>0?"; ready - Space/pad A serves early":"; hit the gold window; move at impact to add spin")
                +std::string("; misses keep cleared targets.");
            return {S.PlayerScore,0,End,End,Note};
        }
        if(QuickMatch()) {
            const bool End=QuickMatchOver();
            std::string Note="First to 5 | YOU "+std::to_string(S.PlayerScore)+" - "+std::to_string(S.ComputerScore)+" CPU";
            if(End) Note+=(S.PlayerScore>=5?"; you reached 5!":"; CPU reached 5.")+std::string(" Space/pad A or R: play again.");
            else Note+=S.ServeFrames>0?"; ready - Space/pad A serves early":"; move at impact to add spin";
            return {S.PlayerScore,0,End,End && S.PlayerScore>=5,Note};
        }
        if(Practice()) {
            std::string Note="Rally practice; "+std::to_string(S.Rally)+" returns; session best "+std::to_string(S.BestRally);
            Note+=S.ServeFrames>0?"; ready - Space/pad A serves early":"; move at impact to add spin";
            return {S.Rally,0,false,false,Note};
        }
        std::string Note="CPU "+std::to_string(S.ComputerScore)+"; rally "+std::to_string(S.Rally)+"; best "+std::to_string(S.BestRally);
        Note+="; move paddle at impact to add spin";
        if(S.ServeFrames>0) Note+="; ready - Fire/Jump/Action serves early";
        else if(S.PointFrames>0) Note+=S.LastPoint>0?"; your point":"; CPU point";
        return {S.PlayerScore,0,false,false,Note}; // Preserve the endless source match.
    }
    void Render(Frame& Out) const override {
        if(Practice()) {RenderPractice(Out);return;}
        if(QuickMatch()) {RenderQuickMatch(Out);return;}
        const Color Flash{100,220,255,255};
        Out.Clear(); Out.AddRect(50,S.PlayerY,10,100,S.ContactFrames>0 && S.LastContact>0?Flash:White);
        Out.AddRect(740,S.ComputerY,10,100,S.ContactFrames>0 && S.LastContact<0?Flash:White);
        Out.AddCircle(S.BallX,S.BallY,8,White); Out.AddLine(400,0,400,600,White,2);
        Out.AddText(300,20,std::to_string(S.PlayerScore),White,36);
        Out.AddText(480,20,std::to_string(S.ComputerScore),White,36);
        // Keep the original six-command opening frame; cues appear after real play events.
        if(S.Rally>0 || S.BestRally>0 || S.ServeFrames>0 || S.PointFrames>0) {
            Out.AddText(250,70,"Rally "+std::to_string(S.Rally)+"   Best "+std::to_string(S.BestRally),White,18);
            Out.AddText(250,98,"Move paddle at impact to add spin",White,14);
        }
        if(S.ServeFrames>0) {
            Out.AddText(220,410,S.LastPoint>0?"Your point. Ready for the next rally.":"CPU point. Ready for the next rally.",White,18);
            Out.AddText(220,442,"J/Space or pad A/X/B: serve early. Paddles stay live.",White,15);
        }
        else if(S.PointFrames>0) Out.AddText(320,410,S.LastPoint>0?"Your point":"CPU point",White,20);
    }
private:
    bool QuickMatchOver() const { return QuickMatch() && (S.PlayerScore>=5 || S.ComputerScore>=5); }
    bool TargetRallyOver() const { return TargetRally() && S.PlayerScore>=static_cast<std::int64_t>(TargetWindows.size()); }
    void RecordContact(int Side) {
        S.LastContact=Side; S.ContactFrames=8;
        if(S.Rally<std::numeric_limits<std::uint32_t>::max()) {
            ++S.Rally;
            if(Option==1 && Side>0 && S.Rally%5==0) {S.PointFrames=90;S.LastPoint=1;}
        }
        S.BestRally=std::max(S.BestRally,S.Rally);
    }
    void PrepareServe(int Scorer) {
        S.BallX=400; S.BallY=300; S.BallVX=Practice()?-4:Scorer>0?-5:5;
        if(Practice()) S.BallVY=2;
        S.ServeFrames=Practice()?120:45; S.LastPoint=Scorer; S.PointFrames=90;
        S.Rally=0; S.ContactFrames=0;
    }
    void RenderPractice(Frame& Out) const {
        constexpr Color Mint{99,230,195,255},Gold{255,200,96,255},Blue{89,165,236,255},Quiet{148,179,197,255};
        constexpr double CourtTop=120;
        // Dedicated score strip keeps the ball and paddle away from the large counters.
        Out.Clear(800,720,{12,24,39,255});Out.AddRect(0,CourtTop,800,600,{8,17,29,255});
        Out.AddLine(400,CourtTop,400,720,{38,67,84,255},2);
        Out.AddRect(50,S.PlayerY+CourtTop,10,140,S.ContactFrames>0 && S.LastContact>0?White:Mint);
        Out.AddRect(740,CourtTop,10,600,S.ContactFrames>0 && S.LastContact<0?White:Blue);
        if(TargetRally()) for(std::size_t N=0;N<TargetWindows.size();++N) {
            const Vec Window=TargetWindows[N];const auto Index=static_cast<std::int64_t>(N);
            const Color Tint=Index<S.PlayerScore?Mint:(Index==S.PlayerScore?Gold:Quiet);
            Out.AddRect(740,CourtTop+Window.X,10,Window.Y-Window.X,Tint);
            Out.AddText(762,CourtTop+(Window.X+Window.Y)/2-9,std::to_string(N+1),Tint,18);
        }
        Out.AddCircle(S.BallX,S.BallY+CourtTop,8,Gold);
        Out.AddText(24,10,TargetRally()?"TARGET RALLY":"RALLY PRACTICE",Mint,24);
        Out.AddText(24,44,TargetRally()?"Targets "+std::to_string(S.PlayerScore)+"/3":"Returns "+std::to_string(S.Rally),White,34);
        const bool ShowTargetHit=TargetRally() && !TargetRallyOver() && S.PointFrames>0 && S.LastPoint>0;
        Out.AddText(430,50,ShowTargetHit?"Window "+std::to_string(S.PlayerScore)+" cleared":"Session best "+std::to_string(S.BestRally),Gold,24);
        Out.AddText(24,91,TargetRally()?"Hit the GOLD window. Move at impact to add spin; cleared targets stay.":"Move at impact to bend the ball.",Quiet,16);
        if(TargetRallyOver()) {
            Out.AddRect(180,330,440,140,{12,24,39,245});
            Out.AddText(230,352,"Three windows cleared!",Gold,26);
            Out.AddText(220,398,"Space/pad A: replay   R: restart",White,18);
            return;
        }
        if(S.ServeFrames>0) {
            Out.AddText(280,370,"Ready in "+std::to_string((S.ServeFrames-1)/60+1),White,30);
            Out.AddText(230,462,"Space / pad A: serve early",Mint,20);
            if(S.LastPoint<0 && S.PointFrames>0) Out.AddText(260,508,TargetRally()?"Targets kept. Let's go again!":"Nice try. Let's go again!",Gold,20);
        }
        else if(Option==1 && S.PointFrames>0 && S.LastPoint>0)
            Out.AddText(230,370,std::to_string(S.Rally)+" returns! Keep it going.",Gold,22);
    }
    void RenderQuickMatch(Frame& Out) const {
        constexpr double CourtTop=90;
        constexpr Color Gold{255,200,96,255},Flash{100,220,255,255},Panel{12,24,39,255};
        Out.Clear(800,690,Panel);Out.AddRect(0,CourtTop,800,600,Black);
        Out.AddRect(50,S.PlayerY+CourtTop,10,100,S.ContactFrames>0 && S.LastContact>0?Flash:White);
        Out.AddRect(740,S.ComputerY+CourtTop,10,100,S.ContactFrames>0 && S.LastContact<0?Flash:White);
        Out.AddCircle(S.BallX,S.BallY+CourtTop,8,White);Out.AddLine(400,CourtTop,400,690,White,2);
        Out.AddText(210,15,"YOU "+std::to_string(S.PlayerScore),White,30);
        Out.AddText(480,15,"CPU "+std::to_string(S.ComputerScore),White,30);
        Out.AddText(350,58,"FIRST TO 5",Gold,16);
        if(QuickMatchOver()) {
            Out.AddRect(180,CourtTop+210,440,140,Panel);
            Out.AddText(240,CourtTop+230,S.PlayerScore>=5?"You reached 5!":"CPU reached 5.",Gold,28);
            Out.AddText(220,CourtTop+282,"Space/pad A: rematch   R: restart",White,18);
        } else if(S.ServeFrames>0) {
            const std::string Ready=S.LastPoint==0?"Ready for the first rally.":
                (S.LastPoint>0?"Your point. Ready for the next rally.":"CPU point. Ready for the next rally.");
            Out.AddText(225,CourtTop+280,Ready,White,18);
            Out.AddText(270,CourtTop+320,"Space/pad A: serve early",Gold,18);
        }
    }
};
}} // daedalus::desktop
