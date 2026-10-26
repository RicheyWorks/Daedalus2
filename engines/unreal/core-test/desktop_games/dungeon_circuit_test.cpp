// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <limits>

using namespace daedalus::desktop;
namespace {
using Dungeon=DungeonGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto ColorEqual=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!ColorEqual(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!ColorEqual(C.Tint,D.Tint)) return false;
    }return true;
}
std::string Lower(std::string S) {for(char& C:S) if(C>='A'&&C<='Z') C=static_cast<char>(C-'A'+'a');return S;}
bool HasText(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&Lower(C.Label).find(Lower(Part))!=std::string::npos) return true;
    return false;
}
std::array<int,3> VisibleOrder(const Frame& F) {
    std::array<int,3> Order{{-1,-1,-1}};
    for(std::size_t L=0;L<Dungeon::Lanterns.size();++L) for(const auto& C:F.Commands)
        if(C.Kind==Shape::Text&&C.A.X==Dungeon::Lanterns[L].X-5&&C.A.Y==Dungeon::Lanterns[L].Y-10
            &&C.Label.size()==1&&C.Label[0]>='1'&&C.Label[0]<='3') Order[static_cast<std::size_t>(C.Label[0]-'1')]=static_cast<int>(L);
    return Order;
}
bool NextAt(const Frame& F,Vec P) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Circle&&C.Size==16&&C.A.X==P.X&&C.A.Y==P.Y&&C.Tint.R==255&&C.Tint.G==255&&C.Tint.B==0) return true;
    return false;
}
bool NoTrail(const Frame& F) {
    return std::none_of(F.Commands.begin(),F.Commands.end(),[](const DrawCommand& C){return C.Kind==Shape::Circle&&C.Size==3;});
}
Frame FreshFrame(std::uint32_t Seed) {Dungeon G;G.Reset(Seed);Frame F;G.Render(F);return F;}
void HelpersAndOrders() {
    const std::array<std::uint32_t,7> Seeds{{0,5,6,730,static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()),0x80000000u,std::numeric_limits<std::uint32_t>::max()}};
    for(const auto Seed:Seeds) {
        const auto Signed=static_cast<std::int32_t>(Seed);const auto ActorRoundtrip=static_cast<std::uint32_t>(Signed);
        Check(ActorRoundtrip==Seed&&Dungeon::CircuitNumber(ActorRoundtrip)==Seed%6+1,"full-width Actor-style seed retains its circuit number");
        std::array<bool,6> Seen{};auto Current=ActorRoundtrip;
        for(int N=0;N<6;++N) {
            const auto Number=Dungeon::CircuitNumber(Current);
            const bool Valid=Number>=1&&Number<=6;Check(Valid,"circuit number stays in one through six");if(!Valid) break;
            const auto Index=static_cast<std::size_t>(Number-1);Check(!Seen[Index],"next-circuit cycle visits a different order once");Seen[Index]=true;
            const auto Next=Dungeon::NextCircuitSeed(Current);
            Check(Next<6&&Next==Number%6,"next seed is the bounded canonical next residue");Current=Next;
        }
        Check(std::all_of(Seen.begin(),Seen.end(),[](bool V){return V;})&&Current==Seed%6,"six next choices return to the starting route without overflow");
    }
    std::array<std::array<int,3>,6> Orders{};
    for(std::size_t N=0;N<Orders.size();++N) {
        Dungeon G;G.Reset(static_cast<std::uint32_t>(N));Frame F;G.Render(F);Orders[N]=VisibleOrder(F);
        Check(Orders[N]==Dungeon::Routes[N],"Reset renders the complete authored order for every residue");
        const auto Label="circuit "+std::to_string(N+1)+"/6";
        Check(HasText(F,Label)&&Lower(G.GetStatus().Note).find(Label)!=std::string::npos,"frame and status name the selected circuit");
        for(std::size_t Earlier=0;Earlier<N;++Earlier) Check(Orders[Earlier]!=Orders[N],"all six full orders are distinct");
    }
}
void FirstLanternAndReset() {
    Dungeon A,B;A.Reset(0);B.Reset(1);Input Toggle;Toggle.DashPressed=true;A.Step(Toggle);B.Step(Toggle);
    Check(A.GetElapsedFrames()==0&&B.GetElapsedFrames()==0,"opening the optional guide does not start either circuit");
    Input Move;Move.Up=true;for(int N=0;N<8;++N) {A.Step(Move);B.Step(Move);}
    Move={};Move.Right=true;for(int N=0;N<8;++N) {A.Step(Move);B.Step(Move);}
    Check(A.GetPlayer().X==120&&A.GetPlayer().Y==40&&B.GetPlayer().X==120&&B.GetPlayer().Y==40&&A.GetLitCount()==0&&B.GetLitCount()==0,"sixteen ordinary moves reach the shared Hall lantern without lighting automatically");
    Input Light;Light.FirePressed=true;A.Step(Light);B.Step(Light);Frame FA,FB;A.Render(FA);B.Render(FB);
    Check(A.GetLitCount()==1&&B.GetLitCount()==1&&A.GetElapsedFrames()==17&&B.GetElapsedFrames()==17,"one explicit interaction advances each circuit once with the normal timer");
    Check(NextAt(FA,Dungeon::Lanterns[1])&&NextAt(FB,Dungeon::Lanterns[2]),"orders zero and one choose Watch versus Root as their actual second target");
    const auto Note=A.GetStatus().Note;const auto X=A.GetPlayer().X,Y=A.GetPlayer().Y;const auto Elapsed=A.GetElapsedFrames();std::uint32_t QuerySum=0;
    for(std::uint32_t Seed:{0u,5u,6u,730u,0x80000000u,std::numeric_limits<std::uint32_t>::max()}) {QuerySum+=Dungeon::CircuitNumber(Seed)+Dungeon::NextCircuitSeed(Seed);}
    Frame After;A.Render(After);
    Check(QuerySum>0&&SameFrame(FA,After)&&A.GetStatus().Note==Note&&A.GetLitCount()==1&&A.GetElapsedFrames()==Elapsed&&A.GetPlayer().X==X&&A.GetPlayer().Y==Y,"pure helper queries preserve the active circuit, timer, guide and position");
    A.Reset(Dungeon::NextCircuitSeed(0));A.Render(After);
    Check(SameFrame(After,FreshFrame(1))&&A.GetLitCount()==0&&A.GetElapsedFrames()==0&&A.GetCircuitStage()==Dungeon::CircuitStage::Lanterns&&NoTrail(After),"explicit next-seed Reset clears old light, timer, notice and guide");
    Input Reset;Reset.ActionPressed=Reset.DashPressed=Reset.FirePressed=Reset.Right=true;B.Step(Reset);B.Render(After);
    Check(SameFrame(After,FreshFrame(1))&&B.GetLitCount()==0&&B.GetElapsedFrames()==0&&NoTrail(After),"Action retains the chosen route and reset priority while clearing its run");
}
void DriverLifecycle() {
    Driver D;Check(D.Select("dungeon",1),"Driver opens the chosen circuit");Input Dirty;Dirty.Down=Dirty.Dash=true;Dirty.DashPressed=true;
    D.SetInput(Dirty);D.Advance(Driver::StepSeconds*2.5);Input Stale;Stale.Right=Stale.FirePressed=Stale.DashPressed=Stale.ActionPressed=true;D.SetInput(Stale);
    D.Restart();Check(D.GetSeed()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),FreshFrame(1)),"Driver Restart keeps its circuit and clears the live guide and timer");
    Check(D.Advance(Driver::StepSeconds*.5)==0&&D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),FreshFrame(1)),"same-seed restart clears partial time and queued movement, interaction and toggle");
    D.SetInput(Dirty);D.Advance(Driver::StepSeconds*2.5);D.SetInput(Stale);const auto Next=Dungeon::NextCircuitSeed(D.GetSeed());
    Check(D.Select("dungeon",Next)&&D.GetSeed()==2&&D.Ticks()==0&&SameFrame(D.GetFrame(),FreshFrame(2)),"same-ID selection starts the next actual route with a clean chapter");
    Check(D.Advance(Driver::StepSeconds*.5)==0&&D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),FreshFrame(2)),"same-ID next selection clears old time debt and held or pressed input");
    D.SetPaused(true);D.SetInput(Stale);
    Check(D.Select("dungeon",Dungeon::NextCircuitSeed(D.GetSeed()))&&D.GetSeed()==3&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),FreshFrame(3)),"explicit same-ID next circuit leaves pause through the existing selection lifecycle");
    Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),FreshFrame(3)),"paused selection also discards stale actions before the first live step");
}
}
int main() {
    HelpersAndOrders();FirstLanternAndReset();DriverLifecycle();
    std::cout<<"Dungeon circuit choice: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
