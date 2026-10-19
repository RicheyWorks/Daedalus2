// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <limits>

namespace daedalus { namespace desktop {
class PongGame final : public Game {
public:
    struct State {
        double PlayerY=250, ComputerY=250, BallX=400, BallY=300, BallVX=5, BallVY=3;
        std::int64_t PlayerScore=0, ComputerScore=0;
        int ServeFrames=0, ContactFrames=0, PointFrames=0, LastPoint=0, LastContact=0;
        std::uint32_t Rally=0, BestRally=0;
    } S;
    void Reset(std::uint32_t) override { S=State{}; }
    void Step(const Input& I) override {
        if(S.ContactFrames>0) --S.ContactFrames;
        if(S.PointFrames>0) --S.PointFrames;
        if((I.Up || I.PadUp) && S.PlayerY>0) S.PlayerY-=6;
        if((I.Down || I.PadDown) && S.PlayerY<500) S.PlayerY+=6;
        const double StickY=Axis(I.AxisY);
        if(std::abs(StickY)>0.2) S.PlayerY+=StickY*8;
        // Polish: keyboard overshoot cannot strand a paddle outside the playfield.
        S.PlayerY=Clamp(S.PlayerY,0,500);
        // Keep the source's two sequential AI tests, including its near-target quirk.
        if(S.ComputerY+50<S.BallY) S.ComputerY+=4;
        if(S.ComputerY+50>S.BallY) S.ComputerY-=4;
        S.ComputerY=Clamp(S.ComputerY,0,500);
        // The opening rally is immediate, as in the source. A scored point adds
        // a bounded preparation window; paddles remain controllable throughout.
        if(S.ServeFrames>0) {
            if(I.FirePressed || I.JumpPressed || I.ActionPressed) S.ServeFrames=0;
            else --S.ServeFrames;
            return; // Launch on the following fixed frame, including an early serve.
        }
        S.BallX+=S.BallVX; S.BallY+=S.BallVY;
        // Source constants/collision windows retained. Direction checks deliberately
        // fix repeated flip-flops while a ball remains inside a paddle/wall window.
        if((S.BallY<=0 && S.BallVY<0) || (S.BallY>=590 && S.BallVY>0)) S.BallVY=-S.BallVY;
        if(S.BallVX<0 && S.BallX>50 && S.BallX<70 && S.BallY>S.PlayerY && S.BallY<S.PlayerY+100) { S.BallVX=-S.BallVX; RecordContact(1); }
        if(S.BallVX>0 && S.BallX>730 && S.BallX<750 && S.BallY>S.ComputerY && S.BallY<S.ComputerY+100) { S.BallVX=-S.BallVX; RecordContact(-1); }
        if(S.BallX<0) {
            if(S.ComputerScore<std::numeric_limits<std::int64_t>::max()) ++S.ComputerScore;
            PrepareServe(-1);
        }
        if(S.BallX>800) {
            if(S.PlayerScore<std::numeric_limits<std::int64_t>::max()) ++S.PlayerScore;
            PrepareServe(1);
        }
    }
    Status GetStatus() const override {
        std::string Note="CPU "+std::to_string(S.ComputerScore)+"; rally "+std::to_string(S.Rally)+"; best "+std::to_string(S.BestRally);
        if(S.ServeFrames>0) Note+="; ready - Fire/Jump/Action serves early";
        else if(S.PointFrames>0) Note+=S.LastPoint>0?"; your point":"; CPU point";
        return {S.PlayerScore,0,false,false,Note}; // Preserve the endless source match.
    }
    void Render(Frame& Out) const override {
        const Color Flash{100,220,255,255};
        Out.Clear(); Out.AddRect(50,S.PlayerY,10,100,S.ContactFrames>0 && S.LastContact>0?Flash:White);
        Out.AddRect(740,S.ComputerY,10,100,S.ContactFrames>0 && S.LastContact<0?Flash:White);
        Out.AddCircle(S.BallX,S.BallY,8,White); Out.AddLine(400,0,400,600,White,2);
        Out.AddText(300,20,std::to_string(S.PlayerScore),White,36);
        Out.AddText(480,20,std::to_string(S.ComputerScore),White,36);
        // Keep the original six-command opening frame; cues appear after real play events.
        if(S.Rally>0 || S.BestRally>0 || S.ServeFrames>0 || S.PointFrames>0)
            Out.AddText(250,70,"Rally "+std::to_string(S.Rally)+"   Best "+std::to_string(S.BestRally),White,18);
        if(S.ServeFrames>0) {
            Out.AddText(220,410,S.LastPoint>0?"Your point. Ready for the next rally.":"CPU point. Ready for the next rally.",White,18);
            Out.AddText(220,442,"J/Space or pad A/X/B: serve early. Paddles stay live.",White,15);
        }
        else if(S.PointFrames>0) Out.AddText(320,410,S.LastPoint>0?"Your point":"CPU point",White,20);
    }
private:
    void RecordContact(int Side) {
        S.LastContact=Side; S.ContactFrames=8;
        if(S.Rally<std::numeric_limits<std::uint32_t>::max()) ++S.Rally;
        S.BestRally=std::max(S.BestRally,S.Rally);
    }
    void PrepareServe(int Scorer) {
        S.BallX=400; S.BallY=300; S.BallVX=Scorer>0?-5:5;
        S.ServeFrames=45; S.LastPoint=Scorer; S.PointFrames=90;
        S.Rally=0; S.ContactFrames=0;
    }
};
}} // daedalus::desktop
