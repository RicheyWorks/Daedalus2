// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopSportsCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
using GameType=DodgeBallGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
bool SameColor(Color A,Color B) {return A.R==B.R&&A.G==B.G&&A.B==B.B&&A.A==B.A;}
bool Chevron(const DrawCommand& C) {return C.Kind==Shape::Line&&Close(std::abs(C.A.X-C.B.X),4)&&Close(std::abs(C.A.Y-C.B.Y),6);}
int MarkerLines(const Frame& F) {return static_cast<int>(std::count_if(F.Commands.begin(),F.Commands.end(),Chevron));}
bool Marker(const Frame& F,double X,double Y,Color* Tint=nullptr) {
    int Found=0;
    for(int Side:{-1,1}) for(int Vertical:{-1,1}) {
        const Vec Outer{X+Side*22,Y+Vertical*6},Inner{X+Side*18,Y};
        const auto Match=[&](const DrawCommand& C) {
            return C.Kind==Shape::Line&&((Close(C.A.X,Outer.X)&&Close(C.A.Y,Outer.Y)&&Close(C.B.X,Inner.X)&&Close(C.B.Y,Inner.Y))
                ||(Close(C.B.X,Outer.X)&&Close(C.B.Y,Outer.Y)&&Close(C.A.X,Inner.X)&&Close(C.A.Y,Inner.Y)));
        };
        const auto It=std::find_if(F.Commands.begin(),F.Commands.end(),Match);
        if(It!=F.Commands.end()) {if(Tint&&Found==0) *Tint=It->Tint;++Found;}
    }
    return Found==4&&MarkerLines(F)==4;
}
bool Text(const Frame& F,const std::string& Label) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Text&&C.Label==Label;});
}
GameType Match(int Owner=0,int Country=0) {
    GameType G;G.Reset(static_cast<std::uint32_t>(730+Country));G.Data.SelectedCountry=Country;G.Data.OpponentCountry=(Country+1)%8;G.StartMatch();
    for(auto& P:G.Data.Players) P.HasBall=false;
    for(int N=3;N<6;++N) {auto& P=G.Data.Players[static_cast<std::size_t>(N)];P.X=500;P.Y=P.BaseY=200+(N-3)*100;}
    auto& P=G.Data.Players[static_cast<std::size_t>(Owner)];P.HasBall=true;
    G.Data.DodgeBall={};G.Data.DodgeBall.Owner=Owner;G.Data.DodgeBall.X=P.X+20;G.Data.DodgeBall.Y=P.Y-5;return G;
}
std::string Snapshot(const GameType& G) {
    const auto& D=G.Data;std::ostringstream O;O.precision(17);
    const auto ColorOut=[&](Color C){O<<' '<<static_cast<int>(C.R)<<' '<<static_cast<int>(C.G)<<' '<<static_cast<int>(C.B)<<' '<<static_cast<int>(C.A);};
    O<<D.SelectedCountry<<' '<<D.OpponentCountry<<' '<<D.HumanScore<<' '<<D.CpuScore<<' '<<D.Round<<' '<<static_cast<int>(D.Mode);
    for(const auto& P:D.Players) O<<' '<<P.X<<' '<<P.Y<<' '<<P.BaseY<<' '<<P.Speed<<' '<<P.Power<<' '<<P.JumpVelocity
        <<' '<<P.CountryIndex<<' '<<P.Health<<' '<<P.ThrowCooldown<<' '<<P.JumpCooldown<<' '<<P.Charge<<' '<<P.SuperType
        <<' '<<P.Cpu<<' '<<P.HasBall<<' '<<P.FacingRight<<' '<<P.OnGround<<' '<<P.JumpWasDown;
    const auto& B=D.DodgeBall;O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Owner<<' '<<B.InAir<<' '<<B.PowerBall;ColorOut(B.ThrowColor);
    O<<' '<<D.Particles.size();for(const auto& P:D.Particles) {O<<' '<<P.X<<' '<<P.Y<<' '<<P.Vx<<' '<<P.Vy<<' '<<P.Size<<' '<<P.Life;ColorOut(P.Tint);}return O.str();
}
void Selection() {
    Frame F;
    for(int Owner=0;Owner<3;++Owner) {
        auto G=Match(Owner);G.Render(F);const auto& Target=G.Data.Players[static_cast<std::size_t>(Owner+3)];
        Check(Marker(F,Target.X,Target.Y),"each human holder uses its own nearest opponent");
        const std::string Cue="throw READY -> C"+std::to_string(Owner+1);
        Check(G.GetStatus().Note.find(Cue)!=std::string::npos&&std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Text&&C.Label.find(Cue)!=std::string::npos;}),"ready HUD and status identify the same numbered opponent");
    }
    auto G=Match();G.Data.Players[3].Y=100;G.Data.Players[4].Y=300;G.Data.Players[5].X=700;G.Data.Players[5].Y=500;G.Render(F);
    Check(Marker(F,500,100)&&G.GetStatus().Note.find(" -> C1")!=std::string::npos,"equal distances keep existing first-opponent tie choice");
    G.Data.Players[3].Health=0;G.Render(F);
    Check(Marker(F,500,300)&&G.GetStatus().Note.find(" -> C2")!=std::string::npos,"defeated nearest opponent is replaced immediately");
    G.Data.Players[4].X=700;G.Data.Players[4].Y=500;G.Data.Players[5].X=480;G.Data.Players[5].Y=220;G.Render(F);
    Check(Marker(F,480,220)&&G.GetStatus().Note.find(" -> C3")!=std::string::npos,"changed player positions derive a new target without cached aim");
    G=Match();Color Ready{},Wait{};G.Render(F);const bool ReadyMarker=Marker(F,500,200,&Ready);
    G.Data.Players[0].ThrowCooldown=3;const auto Before=Snapshot(G);G.Render(F);const bool WaitMarker=Marker(F,500,200,&Wait);
    Check(ReadyMarker&&WaitMarker&&Ready.G>Ready.R&&Ready.B>Ready.R&&!SameColor(Ready,Wait)
        &&static_cast<int>(Wait.R)+Wait.G+Wait.B<static_cast<int>(Ready.R)+Ready.G+Ready.B,"ready cyan target becomes muted during cooldown");
    Check(G.GetStatus().Note.find("throw wait 3 steps -> C1")!=std::string::npos&&Snapshot(G)==Before,"cooldown target is a read-only current snapshot");
    G=Match();auto& Target=G.Data.Players[3];Target.X=500.9;Target.Y=200.9;Target.BaseY=220.9;Target.OnGround=false;Target.JumpVelocity=-8.9;G.Render(F);
    bool Body=false;std::size_t FirstBody=F.Commands.size(),LastMarker=0;
    for(std::size_t N=0;N<F.Commands.size();++N) {const auto& C=F.Commands[N];
        if(C.Kind==Shape::Circle&&Close(C.Size,14)) {FirstBody=std::min(FirstBody,N);if(Close(C.A.X,500)&&Close(C.A.Y,198)) Body=true;}
        if(Chevron(C)) LastMarker=N;
    }
    Check(Body&&Marker(F,500,198)&&LastMarker<FirstBody,"marker shares quantized airborne body center and sits behind players");
}
void Suppression() {
    const auto Hidden=[](GameType G,const std::string& Why) {
        Frame F;G.Render(F);Check(MarkerLines(F)==0&&G.GetStatus().Note.find(" -> C")==std::string::npos,Why);
    };
    auto G=Match();G.Data.Players[0].HasBall=false;G.Data.DodgeBall.Owner=3;G.Data.Players[3].HasBall=true;Hidden(G,"CPU-held ball has no human throw target");
    G=Match();G.Data.Players[0].HasBall=false;G.Data.DodgeBall.Owner=-1;Hidden(G,"loose ball has no target");
    G=Match();G.Data.DodgeBall.InAir=true;Hidden(G,"airborne ball suppresses target even with stale possession metadata");
    G=Match();G.Data.Players[0].HasBall=false;Hidden(G,"owner without possession has no target");
    G=Match();G.Data.Players[0].Health=0;Hidden(G,"defeated holder has no target");
    G=Match();G.Data.DodgeBall.Owner=6;Hidden(G,"out-of-range owner has no target");
    G=Match();for(int N=3;N<6;++N) G.Data.Players[static_cast<std::size_t>(N)].Health=0;Hidden(G,"no living opponent means no marker or numbered aim");
    for(auto Mode:{GameType::Phase::Title,GameType::Phase::CountrySelect,GameType::Phase::Won,GameType::Phase::Lost}) {
        G=Match();G.Data.Mode=Mode;Hidden(G,"non-playing modes suppress stale target presentation");
    }
    Frame F;G.Reset(730);G.Render(F);Check(Text(F,"Auto-aim: nearest living opponent"),"title teaches the actual automatic target rule");
}
void ActualThrows() {
    for(int Owner=0;Owner<3;++Owner) {
        auto G=Match(Owner);const auto Holder=G.Data.Players[static_cast<std::size_t>(Owner)];auto& Target=G.Data.Players[static_cast<std::size_t>(Owner+3)];
        Target.X=500.7;Target.Y=Holder.Y+30.6;const double Dx=Target.X-Holder.X,Dy=Target.Y-Holder.Y,Length=std::hypot(Dx,Dy);
        const double Vx=Dx/Length*8.5*Holder.Power,Vy=Dy/Length*8.5*Holder.Power;const auto Ball=G.Data.DodgeBall;Frame F;G.Render(F);
        Check(Marker(F,500,std::trunc(Target.Y)),"display identifies the opponent used for this fresh throw");
        Input Throw;Throw.FirePressed=true;G.Step(Throw);const auto& After=G.Data.DodgeBall;
        Check(After.InAir&&After.Owner==-1&&!After.PowerBall&&!G.Data.Players[static_cast<std::size_t>(Owner)].HasBall,"fresh normal throw leaves valid holder offset without a friendly self-hit");
        Check(Close(After.X,Ball.X+Vx)&&Close(After.Y,Ball.Y+Vy)&&Close(After.Vx,Vx*.985)&&Close(After.Vy,Vy*.985),"actual aim keeps raw body direction and existing post-update ball drag");
    }
}
void PresentationPurity() {
    Frame F;
    for(int Country=0;Country<8;++Country) {
        auto Observed=Match(1,Country);auto Quiet=Observed;const auto Before=Snapshot(Observed);const auto Note=Observed.GetStatus().Note;
        for(int N=0;N<3;++N) {Observed.Render(F);Observed.GetStatus();}
        Check(Snapshot(Observed)==Before&&Observed.GetStatus().Note==Note,"repeated presentation leaves country "+std::to_string(Country)+" state intact");
        for(int N=0;N<24;++N) {
            Observed.Render(F);Observed.GetStatus();Input I;I.PadRight=N<4;I.PadUp=N>=4&&N<8;I.JumpPressed=N==2;
            I.FirePressed=N==0||N==12;I.Fire=N>=5&&N<=8;Observed.Step(I);Quiet.Step(I);
            Check(Snapshot(Observed)==Snapshot(Quiet)&&Observed.GetStatus().Note==Quiet.GetStatus().Note,"extra rendering preserves paired country "+std::to_string(Country)+" future step "+std::to_string(N));
        }
    }
}
}
int main() {
    Selection();Suppression();ActualThrows();PresentationPurity();
    std::cout<<"Dodge throw target: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
