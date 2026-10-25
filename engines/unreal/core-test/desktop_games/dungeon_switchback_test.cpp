// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>

using namespace daedalus::desktop;
namespace {
using Dungeon=DungeonGame;
int Checks=0,Failed=0,RouteSteps=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::abs(A-B)<1e-7;}
bool SamePoint(Vec A,Vec B) {return Close(A.X,B.X)&&Close(A.Y,B.Y);}
Vec Center(const Dungeon& G) {return {G.GetPlayer().X+20,G.GetPlayer().Y+20};}
bool SamePlay(const Dungeon& A,const Dungeon& B) {
    const auto S=A.GetStatus(),T=B.GetStatus();
    return SamePoint(Center(A),Center(B))&&A.GetOption()==B.GetOption()&&A.GetLitCount()==B.GetLitCount()
        &&A.GetElapsedFrames()==B.GetElapsedFrames()&&A.GetCircuitStage()==B.GetCircuitStage()
        &&S.Score==T.Score&&S.Lives==T.Lives&&S.Over==T.Over&&S.Won==T.Won;
}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
std::vector<Vec> Dots(const Frame& F) {
    std::vector<Vec> P;for(const auto& C:F.Commands) if(C.Kind==Shape::Circle&&C.Size==3) P.push_back(C.A);return P;
}
std::vector<Vec> Dots(const Dungeon& G) {Frame F;G.Render(F);return Dots(F);}
Input Toggle() {Input I;I.DashPressed=true;return I;}
Dungeon Room(std::uint32_t Seed=0) {Dungeon G;G.SetOption(1,Seed);return G;}
Frame FreshFrame(std::uint32_t Seed=0) {auto G=Room(Seed);Frame F;G.Render(F);return F;}
// Only the new room is searched, at most its 140 whole-player anchors once.
std::vector<Vec> NewRoomPath(const Dungeon& G,Vec Goal) {
    constexpr int Count=Dungeon::Columns*Dungeon::Rows;
    const auto P=G.GetPlayer();const int Start=static_cast<int>(P.Y/40)*20+static_cast<int>(P.X/40);
    const int End=static_cast<int>(Goal.Y/40)*20+static_cast<int>(Goal.X/40);
    std::array<int,Count> Parent{},Queue{};Parent.fill(-1);int Head=0,Tail=0;
    Parent[static_cast<std::size_t>(Start)]=Start;Queue[static_cast<std::size_t>(Tail++)]=Start;
    constexpr std::array<maze::Direction,4> Directions{{{1,0},{0,1},{-1,0},{0,-1}}};
    while(Head<Tail&&Parent[static_cast<std::size_t>(End)]<0) {
        const int N=Queue[static_cast<std::size_t>(Head++)];
        for(const auto D:Directions) {const int X=N%20+D.X,Y=N/20+D.Y;
            if(X<0||X>=20||Y<0||Y>=7||Dungeon::Collides(X*40,Y*40,1)) continue;
            const int Next=Y*20+X;if(Parent[static_cast<std::size_t>(Next)]>=0) continue;
            Parent[static_cast<std::size_t>(Next)]=N;Queue[static_cast<std::size_t>(Tail++)]=Next;
        }
    }
    std::vector<Vec> Path;if(Parent[static_cast<std::size_t>(End)]<0) return Path;
    for(int N=End;;N=Parent[static_cast<std::size_t>(N)]) {Path.push_back({N%20*40+20.0,N/20*40+20.0});if(N==Start) break;}
    std::reverse(Path.begin(),Path.end());return Path;
}
bool SafeDots(const std::vector<Vec>& P) {
    if(P.empty()||P.size()>Dungeon::Columns*Dungeon::Rows*4+3) return false;
    for(std::size_t N=0;N<P.size();++N) {
        if(!std::isfinite(P[N].X)||!std::isfinite(P[N].Y)||Dungeon::Collides(P[N].X-20,P[N].Y-20,1)) return false;
        if(N==0) continue;const Vec A=P[N-1],B=P[N];const double Dx=B.X-A.X,Dy=B.Y-A.Y;
        if((!Close(Dx,0)&&!Close(Dy,0))||std::abs(Dx)+std::abs(Dy)<=0||std::abs(Dx)+std::abs(Dy)>10.000001) return false;
        for(int S=1;S<4;++S) if(Dungeon::Collides(A.X+Dx*S/4-20,A.Y+Dy*S/4-20,1)) return false;
    }return true;
}
bool Follow(Dungeon& G,const std::vector<Vec>& P,int& Steps,Dungeon* Plain=nullptr) {
    if(P.empty()) return false;
    for(const auto Target:P) {
        int Attempts=0;
        while(!SamePoint(Center(G),Target)&&Attempts<16&&Steps<2000) {
            const Vec Here=Center(G);Input I;I.AxisX=Clamp((Target.X-Here.X)/5,-1,1);I.AxisY=Clamp((Target.Y-Here.Y)/5,-1,1);
            G.Step(I);if(Plain) Plain->Step(I);++Attempts;++Steps;
            if(Dungeon::Collides(G.GetPlayer().X,G.GetPlayer().Y,1)||(Plain&&!SamePlay(G,*Plain))) return false;
        }
        if(!SamePoint(Center(G),Target)) return false;
    }return true;
}
void LayoutAndModes() {
    bool Layout=true,Defaults=true;int Walls=0;
    for(int Y=0;Y<7;++Y) {
        const std::string Row=Dungeon::SwitchbackMap[static_cast<std::size_t>(Y)];Layout=Layout&&Row.size()==20;
        for(int X=0;X<20;++X) {
            const bool Wall=Row.size()!=20||Row[static_cast<std::size_t>(X)]=='#';Walls+=Wall?1:0;
            Layout=Layout&&Dungeon::IsWall(X,Y,1)==Wall&&Dungeon::Collides(X*40,Y*40,1)==Wall;
            if(X==0||X==19||Y==0||Y==6) Layout=Layout&&Wall;
            Defaults=Defaults&&Dungeon::IsWall(X,Y)==Dungeon::IsWall(X,Y,0)&&Dungeon::Collides(X*40,Y*40)==Dungeon::Collides(X*40,Y*40,0);
        }
    }
    Check(Layout&&Dungeon::IsWall(-1,2,1)&&Dungeon::IsWall(20,2,1)&&Dungeon::IsWall(2,-1,1)&&Dungeon::IsWall(2,7,1),"new room has twenty-column rows solid borders and whole-body collision matching its authored cells");
    Check(Defaults&&!Dungeon::Collides(360,80)&&Dungeon::Collides(360,80,1),"legacy static calls retain Original while selected room changes a real obstruction");
    Dungeon Original,Explicit;Original.Reset(0);Explicit.SetOption(0,0);Frame A,B;Original.Render(A);Explicit.Render(B);
    Check(Original.GetOption()==0&&SameFrame(A,B),"fresh room defaults to the unchanged Original option");
    for(int N=0;N<16;++N) {Input I;I.Down=N<8;I.Right=N>=8;Original.Step(I);Explicit.Step(I);}
    Original.Render(A);Explicit.Render(B);Check(SamePlay(Original,Explicit)&&SameFrame(A,B),"short default-room input companion agrees with explicit option zero");
    auto G=Room();G.Render(A);int RenderedWalls=0;
    for(const auto& C:A.Commands) if(C.Kind==Shape::Rectangle&&C.Tint.R==110&&C.Tint.G==83&&C.Tint.B==55&&C.B.X==40&&C.B.Y==40) ++RenderedWalls;
    Check(RenderedWalls==Walls&&!Dungeon::Collides(G.GetPlayer().X,G.GetPlayer().Y,1),"new room renders its own walls around a legal unchanged spawn");
    bool Connected=true;for(const Vec Goal:{Dungeon::Lanterns[0],Dungeon::Lanterns[1],Dungeon::Lanterns[2],Dungeon::Exit}) Connected=Connected&&!NewRoomPath(G,Goal).empty();
    Check(Connected,"all three unchanged lanterns and EXIT connect to spawn through full-player new-room anchors");
    const auto Before=G;const auto Picture=A;Check(!G.SetOption(-1,99)&&!G.SetOption(2,99)&&SamePlay(G,Before),"invalid room selection preserves the active room and run");
    G.Render(B);Check(SameFrame(Picture,B),"invalid room selection preserves presentation");
}
void ForgivingAndUnaligned() {
    auto G=Room();Input Light;Light.FirePressed=true;G.Step(Light);
    Check(G.GetLitCount()==0&&!G.GetStatus().Over,"distant interaction cannot light a lantern or complete the room");
    int Steps=0;Check(Follow(G,NewRoomPath(G,Dungeon::Lanterns[0]),Steps),"ordinary input reaches the first required new-room landmark");G.Step(Light);
    Check(G.GetLitCount()==1,"explicit first-lantern interaction establishes progress before refusal checks");
    Check(Follow(G,NewRoomPath(G,Dungeon::Lanterns[2]),Steps),"ordinary input reaches an out-of-order new-room landmark");
    G.Step(Light);Check(G.GetLitCount()==1&&G.GetStatus().Note.find("Not yet")!=std::string::npos,"wrong lantern is forgiving and preserves existing progress");
    Check(Follow(G,NewRoomPath(G,Dungeon::Exit),Steps),"ordinary input reaches the still-sealed exit");G.Step(Light);
    Check(G.GetLitCount()==1&&!G.GetStatus().Over&&G.GetStatus().Note.find("sealed")!=std::string::npos,"early EXIT interaction preserves existing progress and leaves the circuit available");
    G=Room();Input I;I.Up=true;for(int N=0;N<8;++N) G.Step(I);I={};I.Left=true;for(int N=0;N<8;++N) G.Step(I);
    I={};I.AxisX=.5;G.Step(I);I.AxisX=0;I.AxisY=.5;G.Step(I);G.Step(Toggle());const auto P=Dots(G);
    Check(SamePoint(Center(G),{62.5,62.5})&&P.size()>=3,"real analog movement supplies an unaligned start in the new room");
    Check(P.size()>=3&&SamePoint(P[0],{62.5,62.5})&&SamePoint(P[1],{60,62.5})&&SamePoint(P[2],{60,60})&&SafeDots(P),"unaligned trail safely decreases X then Y before its selected-room route");
    Check(!P.empty()&&SamePoint(P.back(),Dungeon::Lanterns[0]),"unaligned route still follows the required lantern");
}
void Circuit(std::uint32_t Seed) {
    auto G=Room(Seed),Plain=G;G.Step(Toggle());Plain.Step({});int Steps=0;
    Check(G.GetElapsedFrames()==0&&!Dots(G).empty(),"opening optional trail alone does not start a new-room circuit");
    const auto& Order=Dungeon::Routes[Seed%Dungeon::Routes.size()];
    for(int Stage=0;Stage<=3;++Stage) {
        const auto P=Dots(G);const Vec Goal=Stage<3?Dungeon::Lanterns[static_cast<std::size_t>(Order[static_cast<std::size_t>(Stage)])]:Dungeon::Exit;
        const bool Route=SafeDots(P)&&SamePoint(P.front(),Center(G))&&SamePoint(P.back(),Goal);
        Check(Route,"each rendered new-room trail safely targets NEXT and only then EXIT");if(!Route) return;
        Check(Follow(G,P,Steps,&Plain)&&Steps<2000,"real guide-following inputs traverse the Switchback without state injection or changed guide-off physics");
        Check(G.GetLitCount()==Stage&&!G.GetStatus().Over,"arrival alone never interacts with a new-room target");
        Input Light;Light.FirePressed=Stage%2==0;Light.JumpPressed=Stage%2!=0;G.Step(Light);Plain.Step(Light);++Steps;
        Check(SamePlay(G,Plain)&&G.GetLitCount()==std::min(Stage+1,3),"explicit interaction advances only the current required lantern or exit");
    }
    RouteSteps+=Steps;Check(G.GetStatus().Over&&G.GetStatus().Won&&G.GetStatus().Score==0&&G.GetCircuitStage()==Dungeon::CircuitStage::Complete,"each of six new-room orders completes with no invented reward");
    const auto Complete=G;Frame F;G.Render(F);const auto Picture=F;Input Held;Held.Up=Held.Fire=Held.Jump=Held.Dash=true;Held.FirePressed=Held.DashPressed=true;
    for(int N=0;N<4;++N) G.Step(Held);G.Render(F);Check(SamePlay(G,Complete)&&SameFrame(F,Picture)&&Dots(F).empty(),"completion freezes guide and movement until explicit replay");
    Input Reset;Reset.ActionPressed=Reset.FirePressed=Reset.DashPressed=Reset.Right=true;G.Step(Reset);G.Render(F);
    Check(G.GetOption()==1&&G.GetLitCount()==0&&G.GetElapsedFrames()==0&&SameFrame(F,FreshFrame(Seed)),"Action reset retains room and circuit with priority over movement interaction and trail");
}
void PureAndDriver() {
    auto G=Room(5);G.Step(Toggle());Input I;I.Up=true;G.Step(I);const auto Before=G;Frame F;G.Render(F);const auto Picture=F;const auto Note=G.GetStatus().Note;
    for(int N=0;N<4;++N) {G.Render(F);G.GetStatus();}Check(SamePlay(G,Before)&&SameFrame(F,Picture)&&G.GetStatus().Note==Note,"selected-map rendering trail and status leave the live circuit untouched");
    G.Reset(5);G.Render(F);Check(G.GetOption()==1&&SameFrame(F,FreshFrame(5)),"Reset preserves room while clearing movement timer and trail");
    Driver D;Check(D.Select("dungeon",5)&&D.GetOption()==0&&D.SetOption(1),"existing Driver explicitly selects the second room");
    Input Dirty;Dirty.Down=Dirty.Dash=true;Dirty.DashPressed=true;D.SetInput(Dirty);D.Advance(Driver::StepSeconds*2.5);D.SetPaused(true);D.SetInput(Dirty);
    const auto Pause=D.GetFrame();Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Pause,D.GetFrame()),"pause freezes new-room play and queued trail input");
    D.Restart();Check(D.GetOption()==1&&D.GetSeed()==5&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),FreshFrame(5)),"Restart keeps selected room and seed with clean chapter state");
    Check(D.Advance(Driver::StepSeconds*.5)==0&&D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),FreshFrame(5)),"restart clears debt and stale held or pressed input");
    const auto Next=Dungeon::NextCircuitSeed(D.GetSeed());
    Check(D.Select("dungeon",Next)&&D.GetOption()==0&&D.SetOption(1)&&D.GetSeed()==0&&SameFrame(D.GetFrame(),FreshFrame(0)),"host-style Select then option restore starts next circuit in the chosen room");
    D.SetInput(Dirty);D.Advance(Driver::StepSeconds);Check(D.SetOption(0)&&D.GetOption()==0&&D.Ticks()==0,"explicit return to Original clears prior room state and accounting");
}
}
int main() {
    LayoutAndModes();ForgivingAndUnaligned();for(std::uint32_t Seed=0;Seed<6;++Seed) Circuit(Seed);PureAndDriver();
    std::cout<<"Dungeon Switchback: "<<Checks-Failed<<'/'<<Checks<<" checks passed; six routes "<<RouteSteps<<" movement/interaction steps\n";return Failed?1:0;
}
