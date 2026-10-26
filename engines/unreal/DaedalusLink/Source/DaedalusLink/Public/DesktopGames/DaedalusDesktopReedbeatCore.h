// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <string>

namespace daedalus { namespace desktop {
// Reedbeat: strike when the reed glows. Option 0 is an eight-note round with a
// short window. Option 1 is a four-note practice round with a wider window.
class ReedbeatGame final : public Game {
    int Option=0;
    int Total=8;
    int Gap=36;
    int Window=8;
    int Clock=0;
    int NextAt=36;
    int Hits=0;
    int Misses=0;
    bool Won=false;
    bool Lost=false;
    std::uint32_t SessionSeed=730;
    void Deal() {
        Total=Option==1?4:8;
        Gap=Option==1?40:36;
        Window=Option==1?18:8;
        Clock=0; NextAt=Gap+static_cast<int>(SessionSeed%5); Hits=0; Misses=0; Won=false; Lost=false;
    }
    bool Pressed(const Input& I) const { return I.FirePressed||I.JumpPressed||I.ActionPressed; }
public:
    void Reset(std::uint32_t Seed) override { SessionSeed=Seed?Seed:1; Deal(); }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value; SessionSeed=Seed?Seed:1; Deal(); return true;
    }
    int GetOption() const override { return Option; }
    bool SourceKeyDown(int Key) override {
        if((Won||Lost) && (Key==5 || Key==6 || Key==7 || Key==8)) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Won||Lost) { if(Pressed(I)) Deal(); return; }
        ++Clock;
        const bool Open=Clock>=NextAt && Clock<NextAt+Window;
        if(Pressed(I)) {
            if(Open) { ++Hits; if(Hits>=Total) Won=true; else NextAt+=Gap; }
            else if(++Misses>=3) Lost=true;
            return;
        }
        if(Clock>=NextAt+Window) { if(++Misses>=3) Lost=true; else NextAt+=Gap; }
    }
    bool WindowOpen() const { return !Won && !Lost && Clock>=NextAt && Clock<NextAt+Window; }
    int HitCount() const { return Hits; }
    int MissCount() const { return Misses; }
    std::string HintLine() const {
        if(Won||Lost) return "HINT Pad A or R starts the same round again.";
        return Option==1?"HINT Practice: strike while the reed stays bright."
                        :"HINT Strike when the reed glows. Early taps count as misses.";
    }
    std::string ActionCue() const {
        if(Won||Lost) return "CUE Retry";
        return WindowOpen()?"CUE Strike":"CUE Wait";
    }
    std::string HowToLine() const override { return "HOW Strike while the reed is bright."; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{18,16,28,255});
        F.AddText(30,24,Option==1?"REEDBEAT PRACTICE":"REEDBEAT",{255,236,180,255},28);
        F.AddText(30,58,"HITS: "+std::to_string(Hits)+"/"+std::to_string(Total)+"   MISSES: "+std::to_string(Misses)+"/3",White,18);
        const Color Glow=WindowOpen()?Color{255,196,70,255}:Color{48,40,64,255};
        F.AddRect(330,180,140,220,Glow);
        F.AddRect(360,210,80,160,WindowOpen()?Color{255,236,180,255}:Color{28,24,40,255});
        F.AddText(30,548,HintLine(),{255,236,180,255},16);
        F.AddText(30,528,HowToLine(),{255,236,180,255},14);
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::int64_t Score=static_cast<std::int64_t>(Hits)*100;
        if(Won) return {Score,3-Misses,false,true,"Round clear; pad A or R retries; hits "+std::to_string(Hits)};
        if(Lost) return {Score,0,true,false,"Round dropped; pad A or R retries; misses "+std::to_string(Misses)};
        return {Score,3-Misses,false,false,"Hits "+std::to_string(Hits)+"/"+std::to_string(Total)+"; misses "+std::to_string(Misses)};
    }
};
}} // daedalus::desktop
