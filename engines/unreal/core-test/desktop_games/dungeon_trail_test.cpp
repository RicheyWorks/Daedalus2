// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>

using namespace daedalus::desktop;
namespace {
using Dungeon=DungeonGame;
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A) && std::isfinite(B) && std::abs(A-B)<1e-7;}
bool SamePoint(Vec A,Vec B) {return Close(A.X,B.X) && Close(A.Y,B.Y);}
Vec Center(const Dungeon& G) {const auto& P=G.GetPlayer();return {P.X+Dungeon::Tile/2.0,P.Y+Dungeon::Tile/2.0};}
std::vector<Vec> Dots(const Frame& F) {
    std::vector<Vec> Out;
    for(const auto& C:F.Commands) if(C.Kind==Shape::Circle && C.Size==3) Out.push_back(C.A);
    return Out;
}
std::vector<Vec> Dots(const Dungeon& G) {Frame F;G.Render(F);return Dots(F);}
bool HasText(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label.find(Part)!=std::string::npos) return true;
    return false;
}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()
        || A.Background.R!=B.Background.R || A.Background.G!=B.Background.G
        || A.Background.B!=B.Background.B || A.Background.A!=B.Background.A) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
bool SamePlay(const Dungeon& A,const Dungeon& B) {
    const auto S=A.GetStatus(),T=B.GetStatus();
    return SamePoint(Center(A),Center(B)) && A.GetLitCount()==B.GetLitCount()
        && A.GetElapsedFrames()==B.GetElapsedFrames() && A.GetCircuitStage()==B.GetCircuitStage()
        && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won;
}
Input Toggle() {Input I;I.DashPressed=true;return I;}
bool SafeDots(const std::vector<Vec>& Path) {
    if(Path.empty() || Path.size()>Dungeon::Columns*Dungeon::Rows*4+3) return false;
    for(std::size_t N=0;N<Path.size();++N) {
        const auto P=Path[N];
        if(!std::isfinite(P.X) || !std::isfinite(P.Y) || Dungeon::Collides(P.X-Dungeon::Tile/2.0,P.Y-Dungeon::Tile/2.0)) return false;
        if(N==0) continue;
        const Vec A=Path[N-1];const double Dx=P.X-A.X,Dy=P.Y-A.Y;
        const double Length=std::abs(Dx)+std::abs(Dy);
        if((!Close(Dx,0) && !Close(Dy,0)) || Length<=0 || Length>10.000001) return false;
        for(int Sample=1;Sample<=3;++Sample) {
            const double T=Sample/4.0;
            if(Dungeon::Collides(A.X+Dx*T-Dungeon::Tile/2.0,A.Y+Dy*T-Dungeon::Tile/2.0)) return false;
        }
    }
    return true;
}
bool BehindActors(const Frame& F,const Dungeon& G) {
    std::size_t LastDot=0,Hero=F.Commands.size(),Lantern=F.Commands.size();bool Found=false;
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Circle && C.Size==3) {LastDot=N;Found=true;}
        if(C.Kind==Shape::Rectangle && C.Tint.R==0 && C.Tint.G==255 && C.Tint.B==0
            && C.A.X==G.GetPlayer().X && C.A.Y==G.GetPlayer().Y && C.B.X==Dungeon::Tile && C.B.Y==Dungeon::Tile) Hero=N;
        if(C.Kind==Shape::Circle && C.Size==16 && Lantern==F.Commands.size()) Lantern=N;
    }
    return Found && LastDot<Hero && LastDot<Lantern && Hero<F.Commands.size() && Lantern<F.Commands.size();
}
bool Follow(Dungeon& Guided,Dungeon& Plain,const std::vector<Vec>& Path,int& Steps) {
    // Follow actual rendered dots with normal inputs; never move state directly or light automatically.
    for(const auto P:Path) {
        int Attempts=0;
        while(!SamePoint(Center(Guided),P) && Attempts<4 && Steps<2000) {
            const auto Here=Center(Guided);const double Dx=P.X-Here.X,Dy=P.Y-Here.Y;Input I;
            I.AxisX=Clamp(Dx/5,-1,1);I.AxisY=Clamp(Dy/5,-1,1);
            Guided.Step(I);Plain.Step(I);++Attempts;++Steps;
            if(!SamePlay(Guided,Plain) || Dungeon::Collides(Guided.GetPlayer().X,Guided.GetPlayer().Y)) return false;
        }
        if(!SamePoint(Center(Guided),P)) return false;
    }
    return true;
}
void ToggleLifecycle() {
    Dungeon G;G.Reset(0);const auto Fresh=G;Frame Initial;G.Render(Initial);
    Check(Dots(Initial).empty() && HasText(Initial,"trail OFF"),"trail begins off with one readable existing control hint");
    G.Step(Toggle());Frame On;G.Render(On);
    Check(!Dots(On).empty() && HasText(On,"trail ON") && G.GetStatus().Note.find("Trail ON")!=std::string::npos,"fresh Dash press enables a visible route and status cue");
    Check(SamePlay(G,Fresh) && G.GetElapsedFrames()==0,"toggling alone cannot start the clock move light or change the objective");
    Input Held;Held.Dash=true;for(int N=0;N<8;++N) G.Step(Held);
    Check(!Dots(G).empty() && G.GetElapsedFrames()==0,"held Dash does not repeatedly toggle or begin a circuit");
    G.Step(Toggle());Frame Off;G.Render(Off);
    Check(Dots(Off).empty() && SameFrame(Initial,Off),"a second fresh press returns to the same default presentation");
    G.Step(Toggle());G.Reset(0);G.Render(Off);
    Check(Dots(Off).empty() && SameFrame(Initial,Off),"Reset clears the optional trail and preserves the seed-defined chapter");
    Dungeon Plain;Plain.Reset(5);G.Reset(5);Input Move;Move.Down=true;G.Step(Move);Plain.Step(Move);
    G.Step(Toggle());Plain.Step({});
    Check(SamePlay(G,Plain),"toggle during play consumes only its ordinary idle frame");
    for(int N=0;N<24;++N) {Input I;I.Right=N<12;I.Down=N>=12;G.Step(I);Plain.Step(I);}
    Check(SamePlay(G,Plain),"guide on and off retain identical collision movement elapsed time and circuit state");
    Frame F;G.Render(F);const auto Before=G;const auto Note=G.GetStatus().Note;Frame Again;
    for(int N=0;N<8;++N) {G.Render(Again);G.GetStatus();}
    Check(SamePlay(G,Before) && G.GetStatus().Note==Note && SameFrame(F,Again),"deriving and drawing a trail cannot alter the live chapter");
    Input Reset;Reset.ActionPressed=Reset.DashPressed=Reset.FirePressed=Reset.Right=true;G.Step(Reset);
    Dungeon Expected;Expected.Reset(5);Frame ResetFrame,ExpectedFrame;G.Render(ResetFrame);Expected.Render(ExpectedFrame);
    Check(SamePlay(G,Expected) && SameFrame(ResetFrame,ExpectedFrame) && Dots(ResetFrame).empty(),"Action reset has priority over toggle movement and interaction");
}
void UnalignedConnector() {
    Dungeon G;G.Reset(2);Input Down;Down.Down=true;for(int N=0;N<8;++N) G.Step(Down);
    Input Fraction;Fraction.AxisX=.5;G.Step(Fraction);Fraction.AxisX=0;Fraction.AxisY=.5;G.Step(Fraction);
    auto Plain=G;G.Step(Toggle());Plain.Step({});const auto Path=Dots(G);const auto Here=Center(G);
    Check(Close(G.GetPlayer().X,82.5) && Close(G.GetPlayer().Y,122.5),"ordinary analog steps supply a genuinely unaligned legal start");
    Check(Path.size()>=3,"unaligned start receives a bounded connector and route");if(Path.size()<3) return;
    Check(SamePoint(Path[0],Here) && SamePoint(Path[1],{100,142.5}) && SamePoint(Path[2],{100,140}),"connector decreases X to the floor anchor then decreases Y");
    Check(SafeDots(Path),"every unaligned connector dot and intervening segment fits the whole player box");
    const auto Target=Dungeon::Lanterns[static_cast<std::size_t>(Dungeon::Routes[2][0])];
    Check(SamePoint(Path.back(),Target),"connector still ends at the required distant lantern");
    int Steps=0;Check(Follow(G,Plain,Path,Steps) && Steps<2000 && G.GetLitCount()==0,"actual inputs follow the connector without collisions or automatic lighting");
}
void RequiredRatherThanNearest() {
    Dungeon G;G.Reset(2);G.Step(Toggle());Input I;I.Up=true;for(int N=0;N<8;++N) G.Step(I);
    I={};I.Right=true;for(int N=0;N<8;++N) G.Step(I);
    Check(SamePoint(Center(G),Dungeon::Lanterns[0]),"ordinary movement reaches a nearby but out-of-order lantern");
    I={};I.FirePressed=true;G.Step(I);const auto Path=Dots(G);
    Check(G.GetLitCount()==0 && G.GetStatus().Note.find("Not yet")!=std::string::npos,"out-of-order interaction remains forgiving and loses no progress");
    Check(!Path.empty() && SamePoint(Path.back(),Dungeon::Lanterns[1]),"trail follows NEXT instead of the nearest unlit lantern");
}
void Circuit(std::uint32_t Seed) {
    Dungeon Guided,Plain;Guided.Reset(Seed);Plain.Reset(Seed);Guided.Step(Toggle());Plain.Step({});int Steps=0;
    const auto& Order=Dungeon::Routes[Seed%Dungeon::Routes.size()];
    for(int Stage=0;Stage<=Dungeon::LanternCount;++Stage) {
        Frame F;Guided.Render(F);const auto Path=Dots(F);
        Check(!Path.empty(),"each seeded circuit stage has a rendered optional trail");if(Path.empty()) return;
        const Vec Target=Stage<Dungeon::LanternCount?Dungeon::Lanterns[static_cast<std::size_t>(Order[static_cast<std::size_t>(Stage)])]:Dungeon::Exit;
        Check(SamePoint(Path.front(),Center(Guided)) && SamePoint(Path.back(),Target),"trail begins at the player and targets the authored next stage including EXIT only after all lanterns");
        const bool Safe=SafeDots(Path);Check(Safe,"dotted route is bounded orthogonal closely spaced and walkable by the full 40-pixel player");if(!Safe) return;
        Check(BehindActors(F,Guided),"route dots render behind the player and lantern markers");
        Check(Follow(Guided,Plain,Path,Steps),"ordinary movement can follow the actual rendered route with identical guide-off gameplay");
        Check(Steps<2000 && Guided.GetLitCount()==Stage && !Guided.GetStatus().Over,"reaching a target alone never performs its interaction");
        Input Light;Light.FirePressed=Stage%2==0;Light.JumpPressed=Stage%2!=0;Guided.Step(Light);Plain.Step(Light);++Steps;
        Check(SamePlay(Guided,Plain),"explicit Fire and Jump interactions preserve the same seed order timer and circuit outcome");
        if(Stage<Dungeon::LanternCount)
            Check(Guided.GetLitCount()==Stage+1 && Guided.GetCircuitStage()==(Stage+1==Dungeon::LanternCount?Dungeon::CircuitStage::ExitUnlocked:Dungeon::CircuitStage::Lanterns),"only the required lantern advances the original circuit stage");
    }
    Check(Guided.GetStatus().Over && Guided.GetStatus().Won && Guided.GetCircuitStage()==Dungeon::CircuitStage::Complete
        && Guided.GetStatus().Score==0 && Guided.GetStatus().Lives==1,"explicit EXIT interaction completes the original chapter without invented rewards");
    const auto Complete=Guided;Frame Result;Guided.Render(Result);Check(Dots(Result).empty(),"completed chapter no longer draws an active route");
    Input Held;Held.Up=Held.Right=Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
    Held.FirePressed=Held.JumpPressed=Held.DashPressed=true;
    for(int N=0;N<8;++N) Guided.Step(Held);Frame Frozen;Guided.Render(Frozen);
    Check(SamePlay(Guided,Complete) && Guided.GetStatus().Note==Complete.GetStatus().Note && SameFrame(Result,Frozen),"completion freezes toggle movement and interaction until an explicit reset");
    Input Reset;Reset.ActionPressed=Reset.DashPressed=true;Guided.Step(Reset);Dungeon Fresh;Fresh.Reset(Seed);Frame A,B;Guided.Render(A);Fresh.Render(B);
    Check(SamePlay(Guided,Fresh) && SameFrame(A,B) && Dots(A).empty(),"completed reset retains the original seed order and returns trail to off");
}
void DriverEdges() {
    Driver D;Check(D.Select("dungeon",2),"existing Driver selects Threadlight chapter");Input Press=Toggle();Press.Dash=true;D.SetInput(Press);
    Check(D.Advance(Driver::StepSeconds*8)==8 && !Dots(D.GetFrame()).empty(),"catch-up consumes one fresh guide edge rather than toggling every step");
    Input Held;Held.Dash=true;D.SetInput(Held);D.Advance(Driver::StepSeconds*8);
    Check(!Dots(D.GetFrame()).empty(),"continued held guide input leaves the trail enabled");
    const auto Before=D.GetFrame();D.SetPaused(true);D.SetInput(Press);
    Check(D.Advance(Driver::StepSeconds*8)==0 && SameFrame(Before,D.GetFrame()),"normal pause prevents queued guide events from changing the chapter");
    D.SetPaused(false);D.Advance(Driver::StepSeconds);
    Check(!Dots(D.GetFrame()).empty(),"resume clears the stale paused guide edge");
    D.SetInput(Toggle());D.Advance(Driver::StepSeconds);
    Check(Dots(D.GetFrame()).empty(),"a fresh post-resume edge can deliberately hide the trail");
    D.SetInput(Press);D.Restart();D.Advance(Driver::StepSeconds*8);
    Check(Dots(D.GetFrame()).empty(),"Driver restart clears pending toggle input and restores default off");
}
}
int main() {
    ToggleLifecycle();UnalignedConnector();RequiredRatherThanNearest();
    for(std::uint32_t Seed=0;Seed<6;++Seed) Circuit(Seed);
    DriverEdges();std::cout<<"Dungeon trail: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
