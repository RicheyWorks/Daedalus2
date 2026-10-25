// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void IsolateGhosts(PacmanGame& G) {for(auto& E:G.Ghosts) {E.X=E.Y=-1000;E.Alive=true;E.Frightened=false;E.FrightenedTimer=0;}}
    static void Progress(PacmanGame& G,int Eaten,bool LeaveHeroDot=false) {
        for(auto& P:G.Pellets) P.Alive=true;int Taken=0;
        const auto Take=[&](PacmanGame::Pellet& P){if(P.Alive&&Taken<Eaten) {P.Alive=false;++Taken;}};
        if(!LeaveHeroDot) for(auto& P:G.Pellets) if(PacmanGame::DistanceToPellet(G.Hero,P)<12) Take(P);
        for(auto& P:G.Pellets) if(!LeaveHeroDot||PacmanGame::DistanceToPellet(G.Hero,P)>=12) Take(P);
        G.Remaining=static_cast<int>(G.Pellets.size())-Taken;G.Score=G.FruitCollected*PacmanGame::FruitPoints;
        for(const auto& P:G.Pellets) if(!P.Alive) G.Score+=P.Power?50:10;
    }
    static void At(PacmanGame& G,double X,double Y) {G.Hero.X=X;G.Hero.Y=Y;G.Hero.Dir=G.Hero.Next={};}
    static void LastFrames(PacmanGame& G,int Frames) {G.FruitFrames=Frames;} // Retained-spawn expiry boundaries only.
    static int Issued(const PacmanGame& G) {return G.FruitIssued;}
    static bool Pending(const PacmanGame& G) {return G.FruitPending;}
    static int RawFrames(const PacmanGame& G) {return G.FruitFrames;}
    static void Contact(PacmanGame& G,int Lives,bool Frightened=false,int Grace=0) {
        At(G,PacmanGame::FruitSpot.X,PacmanGame::FruitSpot.Y);G.Lives=Lives;G.RespawnFrames=Grace;
        auto& E=G.Ghosts[0];E.X=G.Hero.X;E.Y=G.Hero.Y;E.Dir={};E.Alive=true;E.Frightened=Frightened;E.FrightenedTimer=300;
    }
    static std::string Snapshot(const PacmanGame& G,bool Fruit=true) {
        std::ostringstream O;O.precision(17);if(Fruit) O<<G.Option<<' '<<G.FruitFrames<<' '<<G.FruitIssued<<' '<<G.FruitCollected<<' '<<G.FruitPending<<' ';
        O<<G.SessionSeed<<' '<<G.Score<<' '<<G.Lives<<' '<<G.Remaining<<' '<<G.Level<<' '<<G.RespawnFrames<<' '<<G.Over<<' '<<G.Won;
        O<<' '<<G.Hero.X<<' '<<G.Hero.Y<<' '<<G.Hero.Dir.X<<' '<<G.Hero.Dir.Y<<' '<<G.Hero.Next.X<<' '<<G.Hero.Next.Y<<' '<<G.Hero.Mouth;
        for(const auto& E:G.Ghosts) O<<' '<<E.X<<' '<<E.Y<<' '<<E.Dir.X<<' '<<E.Dir.Y<<' '<<static_cast<int>(E.Tint.R)<<' '<<static_cast<int>(E.Tint.G)<<' '<<static_cast<int>(E.Tint.B)<<' '<<static_cast<int>(E.Tint.A)<<' '<<E.Alive<<' '<<E.Frightened<<' '<<E.FrightenedTimer;
        O<<' '<<G.Pellets.size();for(const auto& P:G.Pellets) O<<' '<<P.X<<' '<<P.Y<<' '<<P.Power<<' '<<P.Alive;
        auto R=G.Rng;O<<' '<<R.Next();return O.str();
    }
};
}}
namespace {
using Pac=PacmanGame;
using Access=MazeTestAccess;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
Pac Bonus(std::uint32_t Seed=730) {Pac G;G.SetOption(1,Seed);return G;}
std::int64_t DotPoints(const Pac& Before,const Pac& After) {
    std::int64_t Points=0;for(std::size_t N=0;N<Before.GetPellets().size();++N) if(Before.GetPellets()[N].Alive&&!After.GetPellets()[N].Alive) Points+=Before.GetPellets()[N].Power?50:10;return Points;
}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
Pac FirstSpawn() {
    auto G=Bonus();Access::IsolateGhosts(G);Access::Progress(G,75,true);const auto Score=G.GetStatus().Score;
    Check(G.GetPellets().size()==304&&G.DotsLeft()==229&&!G.IsFruitActive()&&Access::Issued(G)==0,"consistent authored-pellet progress starts before the first milestone without assigning fruit state");
    G.Step({});Check(G.DotsLeft()==228&&G.GetStatus().Score==Score+10&&G.IsFruitActive()&&G.FruitFramesRemaining()==1200&&G.FruitsCollected()==0&&Access::Issued(G)==1,"actual spawn dot76 issues first fruit with its full active-play lifetime");return G;
}
void ModesAndPublicRoute(const Pac& Spawned) {
    Pac Classic;Classic.Reset(730);auto G=Bonus();Check(Classic.GetOption()==0&&G.GetOption()==1&&Pac::FruitLifetimeFrames==1200&&Pac::FruitPoints==100&&!G.IsFruitActive(),"Classic defaults and finite local fruit values are explicit");
    for(int N=0;N<12;++N) {Input I;I.Left=N<4;I.Up=N>=4&&N<8;Classic.Step(I);G.Step(I);}
    Check(Access::Snapshot(Classic,false)==Access::Snapshot(G,false),"short Classic and Bonus movement pellets ghosts and RNG remain identical");
    Classic.Reset(730);Access::IsolateGhosts(Classic);Access::Progress(Classic,75,true);Classic.Step({});
    Check(!Classic.IsFruitActive()&&Access::Snapshot(Classic,false)==Access::Snapshot(Spawned,false),"fruit spawning changes no ordinary milestone world state or RNG");
    G=Spawned;const auto Before=G;
    // One source-room corridor route from the untouched normal spawn. Only ghosts
    // were isolated by the progress fixture; the hero is never repositioned here.
    struct Leg {int X,Y,Steps;};int Steps=0;
    for(const auto L:std::array<Leg,5>{{{1,0,8},{0,-1,24},{1,0,24},{0,-1,24},{-1,0,40}}}) {
        Input I;I.Right=L.X>0;I.Left=L.X<0;I.Down=L.Y>0;I.Up=L.Y<0;for(int N=0;N<L.Steps;++N) {G.Step(I);++Steps;}
    }
    Check(Steps==120&&G.GetPlayer().X==Pac::FruitSpot.X&&G.GetPlayer().Y==Pac::FruitSpot.Y&&G.FruitsCollected()==1&&!G.IsFruitActive()&&G.GetStatus().Lives==3,"real public movement reaches and collects fruit from the ordinary spawn");
    Check(G.GetStatus().Score==Before.GetStatus().Score+DotPoints(Before,G)+100&&G.GetPellets().size()==304,"route awards exactly100 fruit points plus its actual ordinary pellet points");
    const auto State=Access::Snapshot(Spawned);Frame F,Again;Spawned.Render(F);for(int N=0;N<4;++N) {Spawned.Render(Again);Spawned.GetStatus();Spawned.IsFruitActive();Spawned.FruitFramesRemaining();}
    Check(Access::Snapshot(Spawned)==State&&SameFrame(F,Again),"fruit display and getters preserve active timer pellets and RNG");
    G=Spawned;for(int Value:{-1,2}) Check(!G.SetOption(Value,99)&&Access::Snapshot(G)==State,"invalid fruit mode preserves active opportunity and progress");
    G.Reset(99);Check(G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Bonus(99)),"Reset keeps Bonus mode while clearing all fruit progress");
}
void QueueAndBoundaries(const Pac& Spawned) {
    auto Queued=Spawned;Access::Progress(Queued,228);Queued.Step({});
    Check(Queued.IsFruitActive()&&Queued.FruitFramesRemaining()==1199&&Access::Issued(Queued)==2&&Access::Pending(Queued),"second threshold queues once behind the current fruit");
    auto G=Queued;Access::At(G,Pac::FruitSpot.X,Pac::FruitSpot.Y);const auto Before=G;G.Step({});
    Check(G.FruitsCollected()==1&&!G.IsFruitActive()&&Access::Pending(G)&&G.GetStatus().Score==Before.GetStatus().Score+DotPoints(Before,G)+100,"collecting the old fruit cannot replace it in the same step");
    G.Step({});Check(G.FruitsCollected()==2&&!G.IsFruitActive()&&!Access::Pending(G),"queued successor may spawn and collect on the following live step");
    for(int N=0;N<8;++N) G.Step({});Check(G.FruitsCollected()==2&&!G.IsFruitActive()&&Access::Issued(G)==2,"both one-shot milestones are finite");
    G=Queued;Access::LastFrames(G,1);G.Step({});Check(!G.IsFruitActive()&&G.FruitFramesRemaining()==0&&Access::Pending(G),"expiry leaves the queued successor waiting for a new idle-start step");
    G.Step({});Check(G.IsFruitActive()&&G.FruitFramesRemaining()==1200&&!Access::Pending(G),"idle-start successor receives its own full lifetime");
    G=Spawned;Access::LastFrames(G,2);G.Step({});Check(G.IsFruitActive()&&G.FruitFramesRemaining()==1,"retained real spawn ticks its penultimate active frame");
    G.Step({});Check(!G.IsFruitActive()&&G.FruitFramesRemaining()==0&&G.FruitsCollected()==0,"final active frame expires without awarding or renewing fruit");
    G=Spawned;Access::At(G,Pac::FruitSpot.X-12,Pac::FruitSpot.Y);G.Step({});Check(G.FruitsCollected()==0&&G.IsFruitActive(),"exact twelve-pixel collection boundary is excluded");
    G=Spawned;Access::At(G,Pac::FruitSpot.X-11.999,Pac::FruitSpot.Y);const auto Near=G;G.Step({});
    Check(G.FruitsCollected()==1&&G.GetStatus().Score==Near.GetStatus().Score+DotPoints(Near,G)+100,"inside collection radius awards fruit separately from nearby dot points");
    G=Bonus();Access::IsolateGhosts(G);Access::Progress(G,228);G.Step({});Check(Access::Issued(G)==1&&G.IsFruitActive()&&!Access::Pending(G),"a progressed fixture issues at most one milestone in one step");
    G.Step({});Check(Access::Issued(G)==2&&Access::Pending(G),"the next reached milestone is issued on the following step");
}
void CollisionAndResults(const Pac& Spawned,Pac& Result) {
    auto G=Spawned;Access::Contact(G,2);G.Step({});
    Check(G.GetStatus().Lives==1&&!G.GetStatus().Over&&G.IsFruitActive()&&G.FruitFramesRemaining()==1199&&G.FruitsCollected()==0,"nonterminal loss keeps and ticks the opportunity without fruit reward");
    G=Spawned;Access::Contact(G,2,false,1);const auto Protected=G;G.Step({});
    Check(G.GetStatus().Lives==2&&G.FruitsCollected()==1&&G.GetStatus().Score==Protected.GetStatus().Score+DotPoints(Protected,G)+100,"last protected contact permits collection because no life was lost");
    G=Spawned;Access::Contact(G,3,true);const auto Frightened=G;G.Step({});
    Check(G.GetStatus().Lives==3&&!G.GetGhosts()[0].Alive&&G.FruitsCollected()==1&&G.GetStatus().Score==Frightened.GetStatus().Score+DotPoints(Frightened,G)+300,"frightened capture and fruit retain their separate original rewards");
    G=Spawned;Access::Contact(G,1);const auto Lethal=G;G.Step({});
    Check(G.GetStatus().Over&&!G.GetStatus().Won&&!G.IsFruitActive()&&G.FruitFramesRemaining()==0&&Access::RawFrames(G)>0&&G.FruitsCollected()==0&&G.GetStatus().Score==Lethal.GetStatus().Score+DotPoints(Lethal,G),"defeat settles before fruit and hides the retained raw timer");
    Result=G;
    G=Spawned;Access::At(G,Pac::FruitSpot.X,Pac::FruitSpot.Y);Access::Progress(G,303,true);G.Step({});
    Check(G.GetStatus().Won&&!G.GetStatus().Over&&G.DotsLeft()==0&&G.GetLevel()==2&&G.FruitsCollected()==0&&!G.IsFruitActive()&&G.FruitFramesRemaining()==0&&Access::Issued(G)==1&&!Access::Pending(G),"last dot wins immediately before fruit collection or issuing another milestone");
}
void ResultAndDriver(const Pac& Result) {
    auto G=Result;const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);Input Held;Held.Up=Held.Right=Held.Fire=Held.Jump=Held.Action=true;Held.DashPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);G.Render(Again);Check(Access::Snapshot(G)==Before&&SameFrame(F,Again),"result freezes hidden fruit state alongside held movement and timers");
    Input Retry;Retry.FirePressed=true;G.Step(Retry);Check(G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Bonus()),"fresh semantic replay keeps Bonus mode and clears both opportunities");
    Driver D;Check(D.Select("pacman",730)&&D.GetOption()==0,"Driver defaults a new Glowtrail cabinet to Classic");D.Advance(Driver::StepSeconds*2.5);Input Stale;Stale.Right=Stale.FirePressed=true;D.SetInput(Stale);
    Check(D.SetOption(1)&&D.GetOption()==1&&D.Ticks()==0&&D.Advance(Driver::StepSeconds*.5)==0,"Bonus selection clears pending input and old partial time");
    auto Expected=Bonus();Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"first Bonus step has no stale movement or replay edge");
    D.SetPaused(true);D.SetInput(Stale);const auto Paused=D.GetFrame();Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Paused,D.GetFrame()),"pause freezes active-play timing");
    D.Restart();Expected=Bonus();Expected.Render(F);Check(D.GetOption()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart keeps mode and restores the original fruit-free board");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"restart discards paused input");
}
}
int main() {
    const auto Spawned=FirstSpawn();ModesAndPublicRoute(Spawned);QueueAndBoundaries(Spawned);Pac Result;CollisionAndResults(Spawned,Result);ResultAndDriver(Result);
    std::cout<<"Pacman bonus fruit: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
