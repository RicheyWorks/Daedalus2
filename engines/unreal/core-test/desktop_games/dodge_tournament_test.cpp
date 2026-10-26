// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopSportsCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
using Dodge=DodgeBallGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameColor(Color A,Color B) {return A.R==B.R&&A.G==B.G&&A.B==B.B&&A.A==B.A;}
const DrawCommand* Text(const Frame& F,const std::string& Label) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&C.Label==Label) return &C;
    return nullptr;
}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width||A.Height!=B.Height||!SameColor(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!SameColor(C.Tint,D.Tint)) return false;
    }return true;
}
std::string Snapshot(const Dodge& G) {
    const auto& D=G.Data;std::ostringstream O;O.precision(17);
    const auto ColorOut=[&](Color C){O<<' '<<static_cast<int>(C.R)<<' '<<static_cast<int>(C.G)<<' '<<static_cast<int>(C.B)<<' '<<static_cast<int>(C.A);};
    O<<D.SelectedCountry<<' '<<D.OpponentCountry<<' '<<D.HumanScore<<' '<<D.CpuScore<<' '<<D.Round<<' '<<static_cast<int>(D.Mode);
    for(const auto& P:D.Players) O<<' '<<P.X<<' '<<P.Y<<' '<<P.BaseY<<' '<<P.Speed<<' '<<P.Power<<' '<<P.JumpVelocity
        <<' '<<P.CountryIndex<<' '<<P.Health<<' '<<P.ThrowCooldown<<' '<<P.JumpCooldown<<' '<<P.Charge<<' '<<P.SuperType
        <<' '<<P.Cpu<<' '<<P.HasBall<<' '<<P.FacingRight<<' '<<P.OnGround<<' '<<P.JumpWasDown;
    const auto& B=D.DodgeBall;O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Owner<<' '<<B.InAir<<' '<<B.PowerBall;ColorOut(B.ThrowColor);
    O<<' '<<D.Particles.size();for(const auto& P:D.Particles) {O<<' '<<P.X<<' '<<P.Y<<' '<<P.Vx<<' '<<P.Vy<<' '<<P.Size<<' '<<P.Life;ColorOut(P.Tint);}return O.str();
}
std::string Outcome(const Dodge& G) {
    return G.Data.HumanScore>G.Data.CpuScore?"YOU WIN THE TOURNAMENT!":(G.Data.HumanScore<G.Data.CpuScore?"OPPONENTS WIN THE TOURNAMENT!":"TOURNAMENT DRAW");
}
bool FinishRound(Dodge& G,bool HumanWins) {
    const int Victim=HumanWins?3:0,Start=HumanWins?3:0;
    for(int N=0;N<6;++N) {auto& P=G.Data.Players[static_cast<std::size_t>(N)];P.HasBall=false;P.OnGround=true;P.JumpVelocity=0;}
    for(int N=Start;N<Start+3;++N) G.Data.Players[static_cast<std::size_t>(N)].Health=N==Victim?1:0;
    // A normal incoming ball meets the last living opponent. CPU catches stay real;
    // a bounded retry provides another consistent incoming throw if it was caught.
    for(int Attempt=0;Attempt<8&&G.Data.Mode==Dodge::Phase::Playing;++Attempt) {
        for(auto& P:G.Data.Players) P.HasBall=false;
        auto& P=G.Data.Players[static_cast<std::size_t>(Victim)];P.ThrowCooldown=30;
        const double Velocity=HumanWins?4:-4;
        auto& B=G.Data.DodgeBall;B={};B.X=P.X-Velocity;B.Y=P.Y;B.Vx=Velocity;B.InAir=true;
        B.ThrowColor=Dodge::Countries[HumanWins?G.Data.SelectedCountry:G.Data.OpponentCountry].Tint;
        G.Step({});
    }
    const bool End=G.Data.Mode==(HumanWins?Dodge::Phase::Won:Dodge::Phase::Lost);
    Check(End&&G.Data.Players[static_cast<std::size_t>(Victim)].Health==0,"actual lethal Step ends the intended match within eight incoming balls");return End;
}
Dodge Tournament(unsigned WinsMask) {
    Dodge G;G.Reset(730+WinsMask);Input Confirm;Confirm.FirePressed=true;
    G.Step(Confirm);G.Step({});G.Step(Confirm);
    Check(G.Data.Mode==Dodge::Phase::Playing&&G.Data.Round==1&&G.Data.HumanScore==0&&G.Data.CpuScore==0,"fresh title and country confirmation begin a clean tournament");
    int Human=0,Cpu=0;
    for(int Round=1;Round<=4;++Round) {
        if(Round==4) {Frame Live;G.Render(Live);Check(G.Data.Mode==Dodge::Phase::Playing&&!G.GetStatus().Over&&!Text(Live,"TOURNAMENT COMPLETE"),"fourth round stays live until its actual last hit");}
        const bool Win=(WinsMask&(1u<<(Round-1)))!=0;if(!FinishRound(G,Win)) return G;
        if(Win) ++Human;else ++Cpu;
        const auto S=G.GetStatus();Frame F;G.Render(F);
        Check(G.Data.Round==Round&&G.Data.HumanScore==Human&&G.Data.CpuScore==Cpu&&S.Score==Human&&S.Over&&S.Won==Win,"each real match increments one total while status flags retain last-match meaning");
        if(Round<4) {
            Check(Text(F,Win?"YOU WIN THE MATCH!":"YOU LOSE THE MATCH!")&&!Text(F,"TOURNAMENT COMPLETE"),"earlier rounds retain the existing match-result heading");
            Check(S.Note.find(Win?"YOU won this match.":"CPU won this match.")!=std::string::npos&&S.Note.find(Outcome(G))==std::string::npos,"earlier status keeps match context without an early tournament outcome");
            Input Continue;Continue.ActionPressed=true;G.Step(Continue);
            Check(G.Data.Mode==Dodge::Phase::Playing&&G.Data.Round==Round+1&&G.Data.HumanScore==Human&&G.Data.CpuScore==Cpu,"fresh continuation retains totals and starts the next actual round");
        }
    }return G;
}
void ScorecardAndRecovery(unsigned WinsMask) {
    auto G=Tournament(WinsMask);const bool LastWin=(WinsMask&8u)!=0;const auto S=G.GetStatus();Frame F;G.Render(F);
    const auto Headline=Outcome(G);const auto* Heading=Text(F,Headline);
    Check(G.Data.Round==4&&Text(F,"TOURNAMENT COMPLETE")&&Heading&&S.Note.find(Headline)!=std::string::npos,"final frame and status report the aggregate tournament outcome");
    const auto* Human=Text(F,std::string("YOU / ")+Dodge::Countries[G.Data.SelectedCountry].Name);const auto* Opponents=Text(F,"OPPONENTS");
    Check(Human&&Opponents&&Text(F,std::to_string(G.Data.HumanScore)+" match wins")&&Text(F,std::to_string(G.Data.CpuScore)+" match wins"),"score panels identify the chosen country, opponent group and both exact totals");
    int Segments[2]={0,0},Filled[2]={0,0};
    if(Human&&Opponents) for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle&&C.B.X==52&&C.B.Y==12) {
        const int Team=C.A.X<400?0:1;++Segments[Team];if(SameColor(C.Tint,Team==0?Human->Tint:Opponents->Tint)) ++Filled[Team];
    }
    Check(Segments[0]==4&&Segments[1]==4&&Filled[0]==G.Data.HumanScore&&Filled[1]==G.Data.CpuScore,"two four-segment bars encode the accumulated match wins");
    const std::string Last=std::string("Last match: ")+Dodge::Countries[G.Data.SelectedCountry].Name+" vs "+Dodge::Countries[G.Data.OpponentCountry].Name+(LastWin?" - YOU won.":" - CPU won.");
    const auto* Context=Text(F,Last);
    Check(Context&&Heading&&Context->Size<Heading->Size&&S.Won==LastWin&&S.Note.find(LastWin?"YOU won this match.":"CPU won this match.")!=std::string::npos,"smaller last-match context and match-based flags remain distinct from the overall result");
    auto Quiet=G;const auto Before=Snapshot(G);const auto Note=S.Note;Frame Again;
    for(int N=0;N<4;++N) {G.Render(Again);G.GetStatus();}
    Check(Snapshot(G)==Before&&SameFrame(F,Again)&&G.GetStatus().Note==Note,"scorecard rendering and status preserve complete public game state");
    Input Held;Held.Fire=Held.Jump=Held.Action=Held.Dash=true;Held.Up=Held.Right=true;
    for(int N=0;N<8;++N) {G.Step(Held);Quiet.Step(Held);}G.Render(Again);
    Check(Snapshot(G)==Before&&SameFrame(F,Again),"held movement and actions cannot change terminal totals, players, ball or particles");
    const int HumanWins=G.Data.HumanScore,CpuWins=G.Data.CpuScore;Input Fresh;Fresh.FirePressed=true;
    G.Step(Fresh);Quiet.Step(Fresh);
    Check(G.Data.Mode==Dodge::Phase::Title&&G.Data.Round==1&&G.Data.HumanScore==HumanWins&&G.Data.CpuScore==CpuWins,"fresh continuation uses the existing title path without prematurely clearing totals");
    G.Step({});Quiet.Step({});G.Step(Fresh);Quiet.Step(Fresh);
    Check(G.Data.Mode==Dodge::Phase::CountrySelect&&G.Data.HumanScore==HumanWins&&G.Data.CpuScore==CpuWins,"country selection retains totals until explicit confirmation");
    G.Step({});Quiet.Step({});G.Step(Fresh);Quiet.Step(Fresh);
    Check(G.Data.Mode==Dodge::Phase::Playing&&G.Data.Round==1&&G.Data.HumanScore==0&&G.Data.CpuScore==0&&G.LivingPlayers()==3&&G.LivingPlayers(true)==3,"fresh country confirmation starts a new four-round score with both teams restored");
    Check(Snapshot(G)==Snapshot(Quiet)&&G.GetStatus().Note==Quiet.GetStatus().Note,"extra scorecard reads preserve future opponent selection, players and RNG-driven state");
}
}
int main() {
    // 3-1 with final loss, 1-3 with final win, draw, and both clean sweeps.
    for(unsigned Mask:{7u,8u,5u,15u,0u}) ScorecardAndRecovery(Mask);
    std::cout<<"Dodge tournament scorecard: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
