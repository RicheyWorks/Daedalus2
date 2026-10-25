// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusGalleryMotifFlipbookCore.h"
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>

namespace flip=daedalus::flipbook;
namespace motif=daedalus::motif;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    std::string IdFor(int Value)
    { const char* Hex="0123456789abcdef"; std::string Out(32,'0'); Out[30]=Hex[(Value>>4)&15]; Out[31]=Hex[Value&15]; return Out; }
    std::array<motif::Document,4> Documents()
    {
        std::array<motif::Document,4> Out;
        for (int Frame=0;Frame<4;++Frame)
        {
            Out[Frame].Id=IdFor(10+Frame);
            for (int Row=0;Row<8;++Row) for (int Column=0;Column<8;++Column)
                Out[Frame].Pixels[Row*8+Column]=static_cast<std::uint8_t>((Frame*3+Row+2*Column)%8);
        }
        Out[0].Parent=IdFor(255); Out[2].Parent=Out[3].Id; Out[3].Parent=Out[0].Id;
        return Out;
    }
    bool Same(const motif::Document* A,const motif::Document& B)
    { return A && A->Id==B.Id && A->Parent==B.Parent && A->Pixels==B.Pixels; }
    bool SameFrames(const flip::Player& Player,const std::array<motif::Document,4>& Expected,int Count)
    {
        if (!Player.Active() || Player.Count()!=Count || Player.Frame(-1)!=nullptr || Player.Frame(Count)!=nullptr) return false;
        for (int I=0;I<Count;++I) if (!Same(Player.Frame(I),Expected[I])) return false;
        return true;
    }
}
int main()
{
    const auto Docs=Documents(); flip::Player Empty;
    Check(!Empty.Active() && Empty.Count()==0 && Empty.Index()==-1 && !Empty.Playing() && Empty.Fps()==2 && Empty.Direction()==1 && Empty.Frame(0)==nullptr &&
        !Empty.TogglePlay() && !Empty.Step(1) && !Empty.Reverse() && !Empty.CycleSpeed() && !Empty.FirstFrame() && !Empty.Advance(1),
        "inactive player has no frame and refuses all playback controls");
    std::array<flip::Player,3> Books; bool Defaults=true;
    for (int Count=2;Count<=4;++Count)
    {
        auto& Book=Books[Count-2]; const bool Captured=Book.Capture(Docs,Count);
        Defaults=Captured && SameFrames(Book,Docs,Count) && Book.Index()==0 && !Book.Playing() && Book.Fps()==2 && Book.Direction()==1 && Defaults;
    }
    Check(Defaults,"two through four canonical documents capture exactly at frame0 paused2fps forward");
    Check(!Empty.Capture(Docs,-1) && !Empty.Capture(Docs,0) && !Empty.Capture(Docs,1) && !Empty.Capture(Docs,5) &&
        !Empty.Active() && Empty.Count()==0 && Empty.Index()==-1 && Empty.Frame(0)==nullptr,
        "invalid frame counts leave an uncaptured player completely unchanged");
    bool Invalid=true;
    for (int Case=0;Case<8;++Case)
    {
        auto Bad=Docs;
        if (Case==0) Bad[0].Id.clear();
        if (Case==1) Bad[0].Id=std::string(32,'0');
        if (Case==2) Bad[0].Id[31]='A';
        if (Case==3) Bad[0].Parent[31]='F';
        if (Case==4) Bad[0].Parent=Bad[0].Id;
        if (Case==5) Bad[1].Id=Bad[0].Id;
        if (Case==6) Bad[2].Pixels[17]=8;
        if (Case==7) Bad[0].Id[5]='\0';
        flip::Player Book;
        Invalid=!Book.Capture(Bad,3) && !Book.Active() && Book.Count()==0 && Book.Index()==-1 && Book.Fps()==2 && Book.Direction()==1 && Invalid;
    }
    Check(Invalid,"invalid/noncanonical IDs or parents, duplicate IDs and invalid pixels refuse atomically");
    auto Unused=Docs; Unused[2].Id=Unused[0].Id; Unused[3].Id.clear(); Unused[3].Pixels[0]=255; flip::Player Two;
    auto SamePixels=Docs; for (auto& Frame:SamePixels) Frame.Pixels=Docs[0].Pixels; flip::Player Identical;
    Check(Two.Capture(Unused,2) && SameFrames(Two,Docs,2) && Identical.Capture(SamePixels,4) && SameFrames(Identical,SamePixels,4),
        "unused slots are ignored and equal images under distinct IDs remain separate frames without a lineage-order rule");
    flip::Player Frozen; std::array<motif::Document,4> Expected{}; bool Captured=false;
    {
        auto Source=Documents(); Expected=Source; Captured=Frozen.Capture(Source,3);
        Source[0].Id=IdFor(99); Source[0].Parent.clear(); Source[0].Pixels.fill(7);
    }
    Check(Captured && SameFrames(Frozen,Expected,3) && !Frozen.Capture(Docs,4) && !Frozen.Capture(Docs,2) && SameFrames(Frozen,Expected,3) &&
        Frozen.Index()==0 && !Frozen.Playing(),"one-time capture preserves exact metadata and row-major pixels after source retarget and lifetime end");
    flip::Player Manual; Manual.Capture(Docs,3);
    Check(Manual.Step(-1) && Manual.Index()==2 && !Manual.Playing() && Manual.Step(1) && Manual.Index()==0 && Manual.Reverse() &&
        Manual.Direction()==-1 && Manual.Step(1) && Manual.Index()==1 && Manual.CycleSpeed() && Manual.Fps()==4 && Manual.FirstFrame() &&
        Manual.Index()==0 && !Manual.Playing() && Manual.Direction()==-1 && Manual.Fps()==4,
        "manual steps wrap independently of playback direction; FirstFrame pauses without changing speed or direction");
    flip::Player Forward; Forward.Capture(Docs,3); Forward.TogglePlay(); const double BeforeHalf=std::nextafter(0.5,0.0);
    Check(!Forward.Advance(BeforeHalf) && Forward.Index()==0 && Forward.Advance(0.5-BeforeHalf) && Forward.Index()==1 &&
        !Forward.Advance(0) && Forward.Index()==1 && Forward.Advance(0.5) && Forward.Index()==2 && Forward.Advance(0.5) && Forward.Index()==0 && Forward.Playing(),
        "2fps advances at the inclusive half-second boundary, never nextafter-before, and wraps forward");
    flip::Player Speed; Speed.Capture(Docs,3); Speed.TogglePlay(); const double BeforeQuarter=std::nextafter(0.25,0.0);
    Check(!Speed.Advance(0.25) && Speed.CycleSpeed() && Speed.Fps()==4 && Speed.Playing() && Speed.Index()==0 &&
        !Speed.Advance(BeforeQuarter) && Speed.Index()==0 && Speed.Advance(0.25-BeforeQuarter) && Speed.Index()==1 &&
        Speed.Advance(0.25) && Speed.Index()==2 && Speed.CycleSpeed() && Speed.Fps()==2 && Speed.Index()==2 && Speed.Playing() &&
        !Speed.Advance(0.25) && Speed.Advance(0.25) && Speed.Index()==0,
        "speed changes reset old fraction, preserve playing/index, and use exact quarter-second4fps boundaries");
    flip::Player Cycles; Cycles.Capture(Docs,3); Cycles.TogglePlay();
    Check(!Cycles.Advance(1.5) && Cycles.Index()==0 && !Cycles.Advance(1.75) && Cycles.Index()==0 &&
        Cycles.Advance(0.25) && Cycles.Index()==1 && !Cycles.Advance(3) && Cycles.Index()==1,
        "full cycles report no current-index change while a full-cycle-plus-fraction still contributes phase");
    flip::Player Reverse; Reverse.Capture(Docs,3); Reverse.TogglePlay();
    Check(!Reverse.Advance(0.25) && Reverse.Reverse() && Reverse.Direction()==-1 && Reverse.Index()==0 && Reverse.Playing() &&
        !Reverse.Advance(0.25) && Reverse.Advance(0.25) && Reverse.Index()==2 && Reverse.Reverse() && Reverse.Direction()==1 &&
        Reverse.Index()==2 && Reverse.Playing() && Reverse.Advance(0.5) && Reverse.Index()==0,
        "three-frame reverse changes direction without jumping and discards the previous fractional phase");
    flip::Player Controls; Controls.Capture(Docs,3); Controls.TogglePlay();
    Check(!Controls.Advance(0.25) && Controls.TogglePlay() && !Controls.Playing() && !Controls.Advance(100) && Controls.Index()==0 &&
        Controls.TogglePlay() && !Controls.Advance(0.25) && Controls.Advance(0.25) && Controls.Index()==1 &&
        !Controls.Advance(0.25) && Controls.FirstFrame() && Controls.Index()==0 && !Controls.Playing() && Controls.FirstFrame() &&
        Controls.TogglePlay() && !Controls.Advance(0.25) && Controls.Advance(0.25) && Controls.Index()==1 && Controls.Step(1) &&
        Controls.Index()==2 && !Controls.Playing(),"play/pause and first controls discard fraction; paused time never advances and stepping always pauses");
    flip::Player InvalidActions; InvalidActions.Capture(Docs,3); InvalidActions.TogglePlay(); InvalidActions.Advance(0.25);
    const double NaN=(std::numeric_limits<double>::quiet_NaN)(),Infinity=(std::numeric_limits<double>::infinity)();
    Check(!InvalidActions.Advance(-1) && !InvalidActions.Advance(NaN) && !InvalidActions.Advance(Infinity) && !InvalidActions.Step(0) &&
        !InvalidActions.Step(2) && !InvalidActions.Step(-2) && !InvalidActions.Capture(Docs,4) && InvalidActions.Index()==0 && InvalidActions.Playing() &&
        InvalidActions.Direction()==1 && InvalidActions.Fps()==2 && InvalidActions.Advance(0.25) && InvalidActions.Index()==1 && SameFrames(InvalidActions,Docs,3),
        "invalid deltas, step directions and repeated capture preserve playing/index/fraction and every frozen document");
    flip::Player Huge; Huge.Capture(Docs,3); Huge.TogglePlay(); const double Power=std::ldexp(1.0,100);
    bool Large=Huge.Advance(Power) && Huge.Index()==2 && Huge.Reverse() && Huge.Advance(Power) && Huge.Index()==0 && Huge.CycleSpeed() &&
        Huge.Advance(Power) && Huge.Index()==2; // 2^101 mod3=2; 2^102 mod3=1, independent of fmod.
    flip::Player Maximum; Maximum.Capture(Docs,4); Maximum.TogglePlay(); const double Biggest=(std::numeric_limits<double>::max)();
    Large=!Maximum.Advance(Biggest) && Maximum.Index()==0 && !Maximum.Advance(0.25) && !Maximum.Advance(Biggest) && Maximum.Index()==0 &&
        Maximum.Advance(0.25) && Maximum.Index()==1 && Large;
    Check(Large,"huge finite deltas use bounded modular steps in both directions and preserve phase across enormous whole cycles");
    flip::Player Small; Small.Capture(Docs,2); Small.TogglePlay(); bool Fractions=true;
    for (int Tick=1;Tick<=16;++Tick)
    {
        const bool Changed=Small.Advance(1.0/16);
        Fractions=Changed==(Tick%8==0) && Small.Index()==(Tick/8)%2 && Fractions;
    }
    Check(Fractions && SameFrames(Small,Docs,2) && SameFrames(Forward,Docs,3) && SameFrames(Speed,Docs,3) && SameFrames(Huge,Docs,3) && SameFrames(Maximum,Docs,4),
        "small exact fractions accumulate to boundaries and all playback leaves every row-major image/ID/parent unchanged");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;frozen2..4 documents, bounded phase playback;no native or visual proof\n";
    return Failures?1:0;
}
