// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
std::vector<std::string> Fields(const std::string& Save) {
    std::istringstream In(Save);std::vector<std::string> Out;std::string Part;
    while(In>>Part) Out.push_back(Part);
    return Out;
}
int Bits(const std::vector<std::string>& Save,int N) {return Save[9][static_cast<std::size_t>(N)]-'0';}
bool Click(Driver& D,int N,int Button=0) {
    int I=0;
    for(const auto& C:D.GetFrame().Commands) if(C.Kind==Shape::Rectangle && I++==N) {
        const double X=C.A.X+C.B.X/2,Y=C.A.Y+C.B.Y/2;
        return D.SourcePointerButton(X,Y,Button);
    }
    return false;
}
bool DifferentStream(std::uint32_t A,std::uint32_t B) {
    Random Left,Right;Left.Seed(A);Right.Seed(B);
    for(int I=0;I<8;++I) if(Left.Next()!=Right.Next()) return true;
    return false;
}
void CheckFresh(const Driver& D,int Option) {
    const auto S=Fields(D.CaptureSave());
    Check(D.ActiveId()=="beacon_sweep" && D.GetOption()==Option && std::stoul(S[2])==static_cast<unsigned long>(Option),"new puzzle retains the active game and selected size");
    bool Empty=S[3]=="0" && S[4]=="0" && S[5]=="0" && S[6]=="0" && S[7]=="0" && S[8]=="0";
    for(char C:S[9]) Empty=Empty && C=='0';
    Check(Empty && D.Ticks()==0 && !D.IsPaused() && !D.GetStatus().Over && !D.GetStatus().Won,"fresh puzzle clears board cursor timer pause and result without revealing a cell");
    Check(std::stoull(S[1])==D.GetSeed() && D.GetSeed()<=0x7fffffffu,"saved seed agrees with bounded native seed presentation");
}
void SeedAndResume(int Option,std::uint32_t Original,std::uint32_t Candidate) {
    Driver D;D.Select("beacon_sweep",Original);D.SetOption(Option);
    const int W=Option==0?9:Option==1?16:30,H=Option==0?9:16,First=(H/2)*W+W/2;
    Click(D,0,1);Click(D,First);D.Advance(Driver::StepSeconds*3);
    const std::string Saved=D.CaptureSave();
    Check(D.NewBeaconSweepPuzzle(Candidate),"explicit new puzzle succeeds from a played board");
    CheckFresh(D,Option);
    const auto NewSeed=D.GetSeed();
    Check(DifferentStream(Original,NewSeed),"new puzzle avoids the old RNG stream including zero-seed aliases");
    const std::string Fresh=D.CaptureSave();
    Driver Continued;Continued.Select("beacon_sweep",123);
    Check(Continued.RestoreSave(Fresh) && Continued.CaptureSave()==Fresh && Continued.GetOption()==Option && Continued.GetSeed()==NewSeed,"an unrevealed new puzzle roundtrips through existing DGM1");
    Click(D,First);const auto Planted=Fields(D.CaptureSave());bool Safe=Planted[6]=="1";
    for(int Dy=-1;Dy<=1;++Dy) for(int Dx=-1;Dx<=1;++Dx) Safe=Safe && !(Bits(Planted,First+Dy*W+Dx)&1);
    Check(Safe,"new puzzle keeps the full first-opening safe neighborhood");
    const std::string FirstBoard=D.CaptureSave();D.Restart();
    Check(D.CaptureSave()==Fresh,"ordinary Restart retains the new puzzle seed and size");
    Click(D,First);Check(D.CaptureSave()==FirstBoard,"same seed and same first cell replay the new layout deterministically");
    Check(D.RestoreSave(Saved) && D.CaptureSave()==Saved && D.GetSeed()==Original && D.GetOption()==Option,"Continue can still restore the previous saved puzzle exactly");
    D.Restart();Click(D,First);
    Driver OriginalReplay;OriginalReplay.Select("beacon_sweep",Original);OriginalReplay.SetOption(Option);Click(OriginalReplay,First);
    Check(D.CaptureSave()==OriginalReplay.CaptureSave(),"Restart after Continue follows the restored original puzzle rather than the discarded new seed");
}
void InputAndResults() {
    Driver D;D.Select("beacon_sweep",730);D.SetOption(1);
    Input Held;Held.Right=Held.Fire=Held.FirePressed=Held.ActionPressed=true;D.SetInput(Held);
    Check(D.Advance(Driver::StepSeconds*.5)==0,"fixture retains a fractional fixed step and queued input");
    Check(D.NewBeaconSweepPuzzle(731),"new puzzle accepts a current board with queued input");
    const std::string Fresh=D.CaptureSave();
    Check(D.Advance(Driver::StepSeconds*.5)==0 && D.Ticks()==0,"new puzzle discards old fractional catch-up time");
    D.Advance(Driver::StepSeconds*.5);D.Advance(Driver::StepSeconds*8);
    Check(D.CaptureSave()==Fresh,"old held navigation reveal and flag edges cannot enter the fresh puzzle");
    D.SetPaused(true);Check(D.NewBeaconSweepPuzzle(732),"explicit new puzzle starts from pause");CheckFresh(D,1);
    Input Move;Move.Right=Move.FirePressed=true;D.SetInput(Move);D.Advance(Driver::StepSeconds);
    Check(Fields(D.CaptureSave())[3]=="1" && Fields(D.CaptureSave())[6]=="1","fresh keyboard input remains usable after the transition");

    D.Select("beacon_sweep",730);Click(D,40);auto S=Fields(D.CaptureSave());
    int Mine=-1;for(int I=0;I<81;++I) if(Bits(S,I)&1) {Mine=I;break;}
    Check(Mine>=0 && Click(D,Mine) && D.GetStatus().Over && !D.GetStatus().Won,"fixture reaches a real loss through ordinary pointer input");
    Check(D.NewBeaconSweepPuzzle(730),"new puzzle accepts a loss even when its candidate equals the old seed");CheckFresh(D,0);
    Click(D,40);S=Fields(D.CaptureSave());
    for(int I=0;I<81 && !D.GetStatus().Over;++I) if(!(Bits(S,I)&1)) Click(D,I);
    Check(D.GetStatus().Won,"fixture reaches a real win by revealing safe cells");
    Check(D.NewBeaconSweepPuzzle(D.GetSeed()),"new puzzle starts after a win with a different stream");CheckFresh(D,0);
}
void RefusedGames() {
    Driver Empty;Check(!Empty.NewBeaconSweepPuzzle(1) && Empty.ActiveId().empty() && Empty.GetSeed()==730 && Empty.Ticks()==0,"absent game refuses without changing driver state");
    for(const auto& E:Catalog()) if(E.Id!="beacon_sweep") {
        Driver D;D.Select(E.Id,730);D.SetPaused(true);
        const auto Before=D.GetStatus();const std::string Save=D.CaptureSave();
        const bool Paused=D.IsPaused();const int Option=D.GetOption();
        Check(!D.NewBeaconSweepPuzzle(1) && D.ActiveId()==E.Id && D.GetSeed()==730 && D.Ticks()==0
            && D.IsPaused()==Paused && D.GetOption()==Option && D.CaptureSave()==Save
            && D.GetStatus().Note==Before.Note && D.GetStatus().Score==Before.Score,"Mines-only action leaves each other existing game and its saved state untouched");
    }
    Random Zero,Alias;Zero.Seed(0);Alias.Seed(0x6d2b79f5u);
    bool Same=true;for(int I=0;I<8;++I) Same=Same && Zero.Next()==Alias.Next();
    Check(Same,"existing zero-seed stream mapping remains compatible");
}
}
int main() {
    for(int Option=0;Option<3;++Option)
        for(std::uint32_t Original:{0u,730u,0x6d2b79f5u,0x7fffffffu,UINT32_MAX})
            for(std::uint32_t Candidate:{0u,730u,0x6d2b79f5u,0x7fffffffu,UINT32_MAX}) SeedAndResume(Option,Original,Candidate);
    InputAndResults();RefusedGames();
    std::cout<<"Beacon Sweep new puzzle: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
