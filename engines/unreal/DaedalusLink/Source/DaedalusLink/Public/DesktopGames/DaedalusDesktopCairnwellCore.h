// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <string>

namespace daedalus { namespace desktop {
// Cairnwell: stack single stones. A full layer sinks away. Option 0 is the
// normal well. Option 1 is a four-column practice with a slower fall.
// Option 2 is the hard well: the same width, fewer rows, the same fast fall.
// Stones are single blocks, so this is not a rotating-piece puzzle.
class CairnwellGame final : public Game {
    int Option=0;
    int Cols=6;
    int Rows=8;
    int DropEvery=16;
    int FallCol=0;
    int FallTick=0;
    int Locks=0;
    int Clears=0;
    bool Falling=false;
    bool Lost=false;
    bool WasLeft=false;
    bool WasRight=false;
    bool WasDown=false;
    std::uint32_t SessionSeed=730;
    std::vector<int> Height;
    void Deal() {
        if(Option==1) { Cols=4; Rows=4; DropEvery=28; }
        else if(Option==2) { Cols=6; Rows=5; DropEvery=8; }
        else { Cols=6; Rows=7; DropEvery=8; }
        Height.assign(static_cast<std::size_t>(Cols),0);
        FallTick=0; Locks=0; Clears=0; Lost=false; Falling=true;
        WasLeft=WasRight=WasDown=false;
        FallCol=static_cast<int>(SessionSeed%static_cast<std::uint32_t>(Cols));
    }
    void Spawn() {
        FallTick=0;
        FallCol=static_cast<int>((SessionSeed+static_cast<std::uint32_t>(Locks))%static_cast<std::uint32_t>(Cols));
        if(Height[static_cast<std::size_t>(FallCol)]>=Rows) { Lost=true; Falling=false; }
        else Falling=true;
    }
    void Lock() {
        if(FallCol<0 || FallCol>=Cols || Height[static_cast<std::size_t>(FallCol)]>=Rows) {
            Lost=true; Falling=false; return;
        }
        Height[static_cast<std::size_t>(FallCol)]++;
        ++Locks;
        int Layers=Rows;
        for(int H:Height) Layers=std::min(Layers,H);
        if(Layers>0) {
            for(int& H:Height) H-=Layers;
            Clears+=Layers;
        }
        Spawn();
    }
    bool Pressed(const Input& I) const { return I.FirePressed||I.JumpPressed||I.ActionPressed; }
    static bool GoLeft(const Input& I) { return I.Left||I.PadLeft||I.AxisX<-0.4; }
    static bool GoRight(const Input& I) { return I.Right||I.PadRight||I.AxisX>0.4; }
public:
    void Reset(std::uint32_t Seed) override { SessionSeed=Seed?Seed:1; Deal(); }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>2) return false;
        Option=Value; SessionSeed=Seed?Seed:1; Deal(); return true;
    }
    int GetOption() const override { return Option; }
    bool SourceKeyDown(int Key) override {
        if(Lost && (Key==5 || Key==6 || Key==7 || Key==8)) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Lost) { if(Pressed(I)) Deal(); return; }
        if(Height.empty() || !Falling) return;
        const bool LeftNow=GoLeft(I), RightNow=GoRight(I), DownNow=I.Down||I.PadDown;
        int Dir=0;
        if(LeftNow && !WasLeft) Dir=-1;
        else if(RightNow && !WasRight) Dir=1;
        WasLeft=LeftNow; WasRight=RightNow;
        if(Dir) {
            const int Next=FallCol+Dir;
            if(Next>=0 && Next<Cols && Height[static_cast<std::size_t>(Next)]<Rows) FallCol=Next;
        }
        ++FallTick;
        if(FallTick>=DropEvery || (DownNow && !WasDown)) { WasDown=DownNow; Lock(); return; }
        WasDown=DownNow;
    }
    int ColumnCount() const { return Cols; }
    int RowCount() const { return Rows; }
    int DropEveryCount() const { return DropEvery; }
    int StackHeight(int Column) const {
        return Column>=0 && Column<Cols ? Height[static_cast<std::size_t>(Column)] : 0;
    }
    int FallingColumn() const { return FallCol; }
    int LayerCount() const { return Clears; }
    std::string HintLine() const {
        if(Lost) return "HINT Pad A or R starts the same well again.";
        if(Option==1) return "HINT Practice: four columns and a slower fall.";
        if(Option==2) return "HINT A short well: six columns and a fast fall.";
        return "HINT Slide the stone. A full layer sinks away.";
    }
    std::string ActionCue() const { return Lost?"CUE Retry":"CUE Slide"; }
    std::string HowToLine() const override { return "HOW Slide the falling stone and clear a full layer."; }
    std::string KeyHint() const override { return "KEYS Left or Right slides the stone."; }
    std::string ContrastMark() const override { return Lost?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{22,18,16,255});
        F.AddText(28,20,Option==1?"CAIRNWELL PRACTICE":Option==2?"CAIRNWELL HARD":"CAIRNWELL",{255,220,170,255},28);
        F.AddText(28,56,"LAYERS: "+std::to_string(Clears)+"   STONES: "+std::to_string(Locks),White,18);
        const double Cell=44, Left=180, Floor=470;
        F.AddRect(Left-8,Floor-Rows*Cell-8,Cols*Cell+16,Rows*Cell+16,{40,32,28,255});
        for(int C=0;C<Cols;++C) for(int R=0;R<StackHeight(C);++R)
            F.AddRect(Left+C*Cell+4,Floor-(R+1)*Cell+4,Cell-8,Cell-8,{196,140,72,255});
        if(Falling && !Lost)
            F.AddRect(Left+FallCol*Cell+4,Floor-(StackHeight(FallCol)+1)*Cell+4,Cell-8,Cell-8,{255,214,120,255});
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::int64_t Score=static_cast<std::int64_t>(Locks)*10+static_cast<std::int64_t>(Clears)*100;
        if(Lost) return {Score,0,true,false,"The well is full; pad A or R starts again; layers "+std::to_string(Clears)};
        return {Score,1,false,false,"Layers "+std::to_string(Clears)+"; stones "+std::to_string(Locks)};
    }
};
}} // daedalus::desktop
