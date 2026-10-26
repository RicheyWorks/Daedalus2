// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void PlayerAt(PacmanGame& G,double X,double Y=290) { G.Hero={};G.Hero.X=X;G.Hero.Y=Y; }
    static void Scene(PacmanGame& G,bool Frightened=false,int Lives=3,int Grace=0) {
        G.Reset(730);PlayerAt(G,2);G.Score=70;G.Level=3;G.Lives=Lives;G.RespawnFrames=Grace;
        for(auto& P:G.Pellets) P.Alive=false;
        G.Pellets.front().Alive=true;G.Remaining=1; // Preserve one unrelated authored power pellet.
        for(auto& E:G.Ghosts) E.Alive=false;
        auto& E=G.Ghosts[0];E.Alive=true;E.X=558;E.Y=290;E.Dir={};E.Frightened=Frightened;E.FrightenedTimer=300;
        G.Ghosts[3].Alive=true; // Unrelated living ghost prevents all-dead group respawn.
        G.Rng.Seed(0x80000000u); // First turn sample > .05: stationary frightened contact stays exact.
    }
    static void GhostAt(PacmanGame& G,std::size_t Index,double X,double Y=290) { G.Ghosts[Index].X=X;G.Ghosts[Index].Y=Y; }
    static void Stacked(PacmanGame& G) { G.Ghosts[1]=G.Ghosts[0];G.Ghosts[1].X=557; }
    static void Grace(PacmanGame& G,int Frames) { G.RespawnFrames=Frames; }
    static std::string Snapshot(const PacmanGame& G) {
        std::ostringstream O;O.precision(17);
        O<<G.SessionSeed<<' '<<G.Score<<' '<<G.Lives<<' '<<G.Remaining<<' '<<G.Level<<' '<<G.RespawnFrames<<' '<<G.Over<<' '<<G.Won;
        O<<' '<<G.Hero.X<<' '<<G.Hero.Y<<' '<<G.Hero.Dir.X<<' '<<G.Hero.Dir.Y<<' '<<G.Hero.Next.X<<' '<<G.Hero.Next.Y<<' '<<G.Hero.Mouth;
        for(const auto& E:G.Ghosts) O<<' '<<E.X<<' '<<E.Y<<' '<<E.Dir.X<<' '<<E.Dir.Y<<' '<<E.Alive<<' '<<E.Frightened<<' '<<E.FrightenedTimer;
        for(const auto& P:G.Pellets) O<<' '<<P.X<<' '<<P.Y<<' '<<P.Power<<' '<<P.Alive;
        Random Copy=G.Rng;O<<' '<<Copy.Next();return O.str();
    }
};
}}
namespace {
int Checks=0,Failures=0,SourceCases=0;
bool Near(double A,double B) { return std::abs(A-B)<1e-8; }
void Check(bool Good,const std::string& What) { ++Checks;if(!Good) {++Failures;std::cerr<<"FAIL "<<What<<'\n';} }
void SourceFixtures(const char* Path) {
    std::ifstream File(Path);std::string Line;
    if(!File || !std::getline(File,Line)) throw std::runtime_error("Cannot read maze source fixtures");
    if(!Line.empty() && Line.back()=='\r') Line.pop_back();
    if(Line!="MAZE 1") throw std::runtime_error("Bad maze fixture header");
    while(std::getline(File,Line)) {
        std::istringstream In(Line);std::string Kind,Name;In>>Kind;
        if(Kind.rfind("PAC_",0)!=0) continue;
        bool Good=false;
        if(Kind=="PAC_ROW") {
            int Row=0;std::string Text;In>>Row>>Text;Good=std::string(PacmanGame::Map.at(static_cast<std::size_t>(Row)))==Text;
        } else if(Kind=="PAC_COLLISION") {
            double X=0,Y=0;int Hit=0;In>>X>>Y>>Hit;Good=PacmanGame::Collides(X,Y,false,false)==(Hit!=0);
        } else if(Kind=="PAC_PLAYER") {
            PacmanGame::Player P;Input I;int L=0,R=0,U=0,D=0,Steps=0,Dx=0,Dy=0,Nx=0,Ny=0,M=0;double X=0,Y=0;
            In>>Name>>P.X>>P.Y>>P.Dir.X>>P.Dir.Y>>P.Next.X>>P.Next.Y>>P.Mouth>>L>>R>>U>>D>>I.AxisX>>I.AxisY
              >>Steps>>X>>Y>>Dx>>Dy>>Nx>>Ny>>M;
            I.Left=L!=0;I.Right=R!=0;I.Up=U!=0;I.Down=D!=0;
            if(Steps<0 || Steps>1000) throw std::runtime_error("Unbounded PAC player fixture");
            for(int N=0;N<Steps;++N) P.Update(I,false,false);
            Good=Near(P.X,X)&&Near(P.Y,Y)&&P.Dir.X==Dx&&P.Dir.Y==Dy&&P.Next.X==Nx&&P.Next.Y==Ny&&P.Mouth==M;
        } else if(Kind=="PAC_GHOST") {
            PacmanGame::Ghost G;PacmanGame::Player P;int Alive=0,Fright=0,Dx=0,Dy=0,EAlive=0,EFright=0,Timer=0;double Turn=0,Chase=0,X=0,Y=0;
            In>>Name>>G.X>>G.Y>>G.Dir.X>>G.Dir.Y>>Alive>>Fright>>G.FrightenedTimer>>P.X>>P.Y>>Turn>>Chase>>X>>Y>>Dx>>Dy>>EAlive>>EFright>>Timer;
            G.Alive=Alive!=0;G.Frightened=Fright!=0;
            G.UpdateWithChoices(P,Turn,Chase,{{{1,0},{-1,0},{0,1},{0,-1}}},false,false);
            Good=Near(G.X,X)&&Near(G.Y,Y)&&G.Dir.X==Dx&&G.Dir.Y==Dy&&G.Alive==(EAlive!=0)&&G.Frightened==(EFright!=0)&&G.FrightenedTimer==Timer;
        } else throw std::runtime_error("Unknown PAC fixture "+Kind);
        Check(Good&&!In.fail(),"source "+Kind+" "+Name);++SourceCases;
    }
    Check(SourceCases==60,"all 60 PAC-only source fixtures loaded");
}
void Motion() {
    Check(PacmanGame::IsWall(-1,14)&&PacmanGame::IsWall(28,14),"IsWall still rejects out-of-map cells");
    Check(!PacmanGame::Collides(0,290)&&!PacmanGame::Collides(560,290),"paired row14 edges are open");
    Check(!PacmanGame::Collides(-8,290)&&!PacmanGame::Collides(568,290)&&PacmanGame::Collides(-8.01,290)&&PacmanGame::Collides(568.01,290),"only bounded tunnel candidates wrap");
    Check(!PacmanGame::Collides(0,288)&&!PacmanGame::Collides(0,292.5)&&PacmanGame::Collides(0,287.5)&&PacmanGame::Collides(0,293),"quantized full body must occupy only row14");
    Check(PacmanGame::Collides(0,270)&&PacmanGame::Collides(560,310)&&PacmanGame::Collides(-550,290)&&PacmanGame::Collides(1110,290),"adjacent rows and distant aliases stay solid");
    Check(PacmanGame::Collides(0,290,false,false),"source mode retains original edge obstruction");
    Input Left,Right;Left.Left=true;Right.Right=true;PacmanGame::Player P;P.X=0;P.Y=290;
    P.Update(Left);Check(Near(P.X,557.5)&&Near(P.Y,290),"left player crossing retains 2.5px overshoot");
    P.Update(Right);Check(Near(P.X,0)&&P.Dir.X==1,"immediate reversal crosses back without clamp");
    P.X=558.75;P.Update(Right);Check(Near(P.X,1.25),"right player crossing retains fractional overshoot");
    P={};P.X=10;P.Y=293;P.Update(Left);Check(Near(P.X,10)&&Near(P.Y,293),"off-row player cannot leak around a corner");
    const std::array<maze::Direction,4> Dirs{{{-1,0},{1,0},{0,-1},{0,1}}};
    PacmanGame::Ghost G;G.X=.5;G.Y=290;G.Dir={-1,0};G.Frightened=true;G.FrightenedTimer=40;
    G.UpdateWithChoices(P,1,1,Dirs);Check(Near(G.X,558.5)&&G.FrightenedTimer==39,"living ghost commits left overshoot and ticks once");
    G.X=559.5;G.Dir={1,0};G.UpdateWithChoices(P,1,1,Dirs);Check(Near(G.X,1.5),"living ghost commits right overshoot");
    G.X=.5;G.Dir={};G.UpdateWithChoices(P,0,1,Dirs);Check(Near(G.X,558.5)&&G.Dir.X==-1,"turn-choice probe agrees with seam commit");
    G.X=559;G.Y=293;G.Dir={1,0};G.UpdateWithChoices(P,0,1,Dirs);Check(Near(G.X,559)&&Near(G.Y,291)&&G.Dir.Y==-1,"blocked corner probes find only a valid row-entry direction");
    G={};G.X=.5;G.Y=290;P.X=550;P.Y=290;G.UpdateWithChoices(P,1,0,Dirs);
    Check(Near(G.X,558.5)&&G.Dir.X==-1,"chase takes the shorter clear passage toward the opposite edge");
    Random A,B,Expected;A.Seed(123);B=A;Expected=A;for(int N=0;N<5;++N) Expected.Next();
    PacmanGame::Ghost Seam,Inside;Seam.X=1;Seam.Y=290;Seam.Dir={-1,0};Inside=Seam;Inside.X=70;
    Seam.Update(P,A);Inside.Update(P,B);const auto Sixth=Expected.Next();
    Check(A.Next()==Sixth&&B.Next()==Sixth,"seam and interior living updates consume identical five source random calls");
    G.Alive=false;G.Frightened=true;G.FrightenedTimer=17;const auto Dead=G;Random R;R.Seed(42);Expected=R;
    G.Update(P,R);Check(Near(G.X,Dead.X)&&Near(G.Y,Dead.Y)&&G.FrightenedTimer==17&&R.Next()==Expected.Next(),"dead ghost neither moves nor ticks nor consumes randomness");
}
void Settlement() {
    PacmanGame G;MazeTestAccess::Scene(G);MazeTestAccess::Stacked(G);G.Step({});
    Check(G.GetStatus().Lives==2&&G.RespawnFramesRemaining()==90&&!G.GetStatus().Over,"two lethal seam contacts settle one life and normal grace");
    Check(G.GetStatus().Score==70&&G.GetLevel()==3&&G.DotsLeft()==1&&G.PowerPelletsLeft()==1,"lethal crossing retains unrelated progress and power pellet");
    MazeTestAccess::Scene(G,true);G.Step({});
    Check(!G.GetGhosts()[0].Alive&&G.GetGhosts()[3].Alive&&G.GetStatus().Score==270&&G.GetStatus().Lives==3,"frightened seam capture awards once without group respawn");
    G.Step({});Check(G.GetStatus().Score==270&&G.GetGhosts()[0].FrightenedTimer==299,"captured ghost cannot score or tick again");
    MazeTestAccess::Scene(G,false,3,1);G.Step({});Check(G.GetStatus().Lives==3&&G.RespawnFramesRemaining()==0,"last grace step still protects the seam contact");
    G.Step({});Check(G.GetStatus().Lives==2&&G.RespawnFramesRemaining()==90,"following unprotected seam step settles once");
    MazeTestAccess::Scene(G,true);MazeTestAccess::PlayerAt(G,14);MazeTestAccess::GhostAt(G,0,558.5);G.Step({});
    Check(G.GetStatus().Score==70&&G.GetGhosts()[0].Alive,"shifted quantized ghost rectangle touching at x6 is not re-quantized into overlap");
    MazeTestAccess::Scene(G,true);MazeTestAccess::PlayerAt(G,14);MazeTestAccess::GhostAt(G,0,-550);G.Step({});
    Check(G.GetStatus().Score==70&&G.GetGhosts()[0].Alive,"noncanonical distant ghost cannot contact through a periodic alias");
    MazeTestAccess::Scene(G,true);MazeTestAccess::PlayerAt(G,70,110);MazeTestAccess::GhostAt(G,0,70,110);G.Step({});
    Check(G.GetStatus().Score==270&&!G.GetGhosts()[0].Alive&&!G.GetStatus().Won,"ordinary rectangle contact outside the passage is preserved");
    G.Reset(730);MazeTestAccess::PlayerAt(G,0);G.Step({});
    Check(G.GetPellets().size()==304&&G.DotsLeft()==302&&G.GetStatus().Score==20,"both authored edge dots collect once with all 304 retained");
    G.Step({});Check(G.DotsLeft()==302&&G.GetStatus().Score==20,"remaining on seam does not recollect either dot");
    G.Reset(730);MazeTestAccess::PlayerAt(G,2);G.Step({});Check(G.DotsLeft()==303&&G.GetStatus().Score==10,"exactly twelve periodic pixels is outside original strict pickup radius");
    MazeTestAccess::PlayerAt(G,1.5);G.Step({});Check(G.DotsLeft()==302&&G.GetStatus().Score==20,"fractional approach collects the opposite dot inside radius");
    G.Reset(730);MazeTestAccess::PlayerAt(G,1.9,292.5);G.Step({});Check(G.DotsLeft()==303,"vertical offset keeps an otherwise near periodic dot outside the circular radius");
    MazeTestAccess::PlayerAt(G,0,292.5);G.Step({});Check(G.DotsLeft()==302,"row-aligned quantized body still collects an opposite dot inside the circular radius");
    MazeTestAccess::Scene(G,false,1);G.Step({});Check(G.GetStatus().Over&&!G.GetStatus().Won&&G.GetStatus().Lives==0,"real seam loss reaches terminal result");
    const auto End=MazeTestAccess::Snapshot(G);Input Held;Held.Left=Held.Fire=Held.Jump=Held.Action=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(MazeTestAccess::Snapshot(G)==End,"terminal held inputs freeze position, dots, timers and RNG");
    G.Reset(123);PacmanGame Fresh;Fresh.Reset(123);
    Check(MazeTestAccess::Snapshot(G)==MazeTestAccess::Snapshot(Fresh)&&G.DotsLeft()==304,"seeded Reset restores the original full run");
}
bool Circle(const Frame& F,double X,double Radius) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Circle&&Near(C.A.X,X)&&Near(C.A.Y,290)&&Near(C.Size,Radius);});
}
void Presentation() {
    PacmanGame G;MazeTestAccess::Scene(G,true);MazeTestAccess::Grace(G,5);Frame F;G.Render(F);
    Check(Circle(F,2,10)&&Circle(F,562,10)&&Circle(F,2,14)&&Circle(F,562,14),"hero and grace rings mirror at the left passage");
    Check(Circle(F,558,9)&&Circle(F,-2,9),"ghost visible extent mirrors at the right passage");
    std::size_t Gate=F.Commands.size(),Dot=Gate,Mask=Gate,Hud=Gate,LastActor=0;
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle&&Near(C.B.X,6)&&Near(C.B.Y,2)&&Near(C.A.Y,282)) Gate=std::min(Gate,N);
        if(C.Kind==Shape::Circle) {Dot=std::min(Dot,N);LastActor=N;}
        if(C.Kind==Shape::Triangle) LastActor=N;
        if(C.Kind==Shape::Rectangle&&Near(C.A.X,560)&&Near(C.A.Y,0)&&Near(C.B.X,240)&&Near(C.B.Y,620)&&C.Tint.R==0&&C.Tint.G==0&&C.Tint.B==0) Mask=N;
        if(C.Kind==Shape::Text) Hud=std::min(Hud,N);
    }
    Check(Gate<Dot&&LastActor<Mask&&Mask<Hud,"passage brackets precede actors and gutter clips scene before HUD");
    Check(Near(F.Width,800)&&Near(F.Height,660)&&F.Commands.size()<Frame::MaxCommands,"tunnel presentation stays inside existing frame budget");
    MazeTestAccess::PlayerAt(G,558);G.Render(F);Check(Circle(F,-2,10)&&Circle(F,-2,14),"hero and grace also mirror at the right passage");
    MazeTestAccess::PlayerAt(G,11);G.Render(F);Check(Circle(F,571,14),"grace ring uses its full fourteen-pixel visible extent");
    MazeTestAccess::Grace(G,0);G.Render(F);Check(!Circle(F,571,10),"ordinary hero does not mirror beyond its ten-pixel extent");
    MazeTestAccess::GhostAt(G,0,8.5);G.Render(F);Check(Circle(F,568.5,9),"ghost drawing uses nine-pixel extent rather than collision radius");
    MazeTestAccess::GhostAt(G,0,10);G.Render(F);Check(!Circle(F,570,9),"ghost outside visible seam extent has no mirror");
    MazeTestAccess::PlayerAt(G,-550);G.Render(F);Check(!Circle(F,10,10),"invalid actor coordinates do not acquire a rendered alias");
    const auto Before=MazeTestAccess::Snapshot(G);PacmanGame Unobserved=G;
    for(int N=0;N<4;++N) {G.Render(F);G.GetStatus();}
    Check(MazeTestAccess::Snapshot(G)==Before,"render and status preserve all seam gameplay and random state");
    G.Step({});Unobserved.Step({});Check(MazeTestAccess::Snapshot(G)==MazeTestAccess::Snapshot(Unobserved),"presentation does not change the following simulation");
}
}
int main(int Argc,char** Argv) {
    try {SourceFixtures(Argc>1?Argv[1]:"maze_parity.txt");Motion();Settlement();Presentation();}
    catch(const std::exception& E) {std::cerr<<E.what()<<'\n';return 1;}
    std::cout<<"Pacman paired tunnel: "<<Checks-Failures<<'/'<<Checks<<" checks passed ("<<SourceCases<<" source cases)\n";
    return Failures?1:0;
}
