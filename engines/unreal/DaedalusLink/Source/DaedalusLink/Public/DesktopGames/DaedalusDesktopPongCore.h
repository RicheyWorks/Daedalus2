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
    } S;
    void Reset(std::uint32_t) override { S=State{}; }
    void Step(const Input& I) override {
        if(I.Up && S.PlayerY>0) S.PlayerY-=6;
        if(I.Down && S.PlayerY<500) S.PlayerY+=6;
        const double StickY=Axis(I.AxisY);
        if(std::abs(StickY)>0.2) S.PlayerY+=StickY*8;
        // Polish: keyboard overshoot cannot strand a paddle outside the playfield.
        S.PlayerY=Clamp(S.PlayerY,0,500);
        // Keep the source's two sequential AI tests, including its near-target quirk.
        if(S.ComputerY+50<S.BallY) S.ComputerY+=4;
        if(S.ComputerY+50>S.BallY) S.ComputerY-=4;
        S.BallX+=S.BallVX; S.BallY+=S.BallVY;
        // Source constants/collision windows retained. Direction checks deliberately
        // fix repeated flip-flops while a ball remains inside a paddle/wall window.
        if((S.BallY<=0 && S.BallVY<0) || (S.BallY>=590 && S.BallVY>0)) S.BallVY=-S.BallVY;
        if(S.BallVX<0 && S.BallX>50 && S.BallX<70 && S.BallY>S.PlayerY && S.BallY<S.PlayerY+100) S.BallVX=-S.BallVX;
        if(S.BallVX>0 && S.BallX>730 && S.BallX<750 && S.BallY>S.ComputerY && S.BallY<S.ComputerY+100) S.BallVX=-S.BallVX;
        if(S.BallX<0) {
            if(S.ComputerScore<std::numeric_limits<std::int64_t>::max()) ++S.ComputerScore;
            S.BallX=400; S.BallY=300; S.BallVX=5;
        }
        if(S.BallX>800) {
            if(S.PlayerScore<std::numeric_limits<std::int64_t>::max()) ++S.PlayerScore;
            S.BallX=400; S.BallY=300; S.BallVX=-5;
        }
    }
    Status GetStatus() const override { return {S.PlayerScore,0,false,false,"CPU "+std::to_string(S.ComputerScore)}; }
    void Render(Frame& Out) const override {
        Out.Clear(); Out.AddRect(50,S.PlayerY,10,100,White); Out.AddRect(740,S.ComputerY,10,100,White);
        Out.AddCircle(S.BallX,S.BallY,8,White); Out.AddLine(400,0,400,600,White,2);
        Out.AddText(300,20,std::to_string(S.PlayerScore),White,36);
        Out.AddText(480,20,std::to_string(S.ComputerScore),White,36);
    }
};
}} // daedalus::desktop
