// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
// Position shots without a bot; only real Step collisions remove or split rocks.
struct AsteroidsTestAccess {
    static int Aim(AsteroidsGame& G) {
        for(std::size_t N=0;N<G.Rocks.size();++N) {
            auto& A=G.Rocks[N];A.X=50+static_cast<double>(N%8)*90;A.Y=60+static_cast<double>(N/8)*90;A.Vx=A.Vy=0;
        }
        const auto& A=G.Rocks.front();G.Bullets.push_back({A.X,A.Y,0,0,45,true});G.RespawnGrace=2;return A.Size;
    }
    static void Ufo(AsteroidsGame& G) {G.Ufos.push_back({100,500,0,60});}
    static void LethalLastRock(AsteroidsGame& G) {
        G.Lives=1;G.RespawnGrace=0;G.Player=AsteroidsGame::Ship{};
        auto& A=G.Rocks.front();A.X=400;A.Y=300;A.Vx=A.Vy=0;G.Bullets.push_back({400,300,0,0,45,true});
    }
    static std::string Snapshot(const AsteroidsGame& G) {
        std::ostringstream O;O.precision(17);auto R=G.Rng;const auto& P=G.Player;
        O<<G.SessionSeed<<' '<<G.Score<<' '<<G.Lives<<' '<<G.Level<<' '<<G.UfoTimer<<' '<<G.RespawnGrace<<' '<<G.Over<<' '<<R.Next();
        O<<' '<<P.X<<' '<<P.Y<<' '<<P.Angle<<' '<<P.Vx<<' '<<P.Vy<<' '<<P.Thrust<<' '<<P.Cooldown<<' '<<P.Braking;
        O<<' '<<G.Rocks.size();for(const auto& A:G.Rocks) {O<<' '<<A.X<<' '<<A.Y<<' '<<A.Vx<<' '<<A.Vy<<' '<<A.Angle<<' '<<A.Rotation<<' '<<A.Size;for(double V:A.Shape) O<<' '<<V;}
        O<<' '<<G.Bullets.size();for(const auto& B:G.Bullets) O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Life<<' '<<B.PlayerOwned;
        O<<' '<<G.Ufos.size();for(const auto& U:G.Ufos) O<<' '<<U.X<<' '<<U.Y<<' '<<U.Vx<<' '<<U.ShootTimer;
        for(const auto& S:G.Stars) O<<' '<<S.X<<' '<<S.Y<<' '<<S.Speed;return O.str();
    }
};
}}
namespace {
using Access=AsteroidsTestAccess;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Tint(Color A,Color B) {return A.R==B.R&&A.G==B.G&&A.B==B.B&&A.A==B.A;}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
bool Text(const Frame& F,const std::string& Part) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Text&&C.Label.find(Part)!=std::string::npos;});
}
void Modes() {
    AsteroidsGame G;G.Reset(730);const auto Original=Access::Snapshot(G);
    Check(G.GetOption()==0&&G.GetLevel()==1&&G.GetRockCount()==6&&!G.GetStatus().Won,"default remains an endless six-rock opening");
    const bool Accepted=G.SetOption(1,730);Check(Accepted,"three-wave voyage is selectable");if(!Accepted) return;
    Check(G.GetOption()==1&&Access::Snapshot(G)==Original,"voyage opens with identical original ship rocks timers and random state");
    Frame BeforeFrame;G.Render(BeforeFrame);const auto Before=Access::Snapshot(G);
    for(int Invalid:{-1,3}) {
        Check(!G.SetOption(Invalid,99)&&G.GetOption()==1&&Access::Snapshot(G)==Before,"invalid option preserves the complete voyage simulation");
        Frame After;G.Render(After);Check(SameFrame(BeforeFrame,After),"invalid option preserves presentation");
    }
    Input Move;Move.Up=Move.Fire=true;G.Step(Move);G.Reset(99);AsteroidsGame Fresh;Fresh.SetOption(1,99);
    Check(G.GetOption()==1&&Access::Snapshot(G)==Access::Snapshot(Fresh),"Reset retains voyage and replaces progress using the requested seed");
    Check(G.SetOption(0,730)&&G.GetOption()==0&&Access::Snapshot(G)==Original,"explicit mode selection returns to unchanged endless opening");
}
void ActualVoyage() {
    AsteroidsGame Voyage,Endless,LastSmall;Endless.Reset(730);
    const bool Accepted=Voyage.SetOption(1,730);Check(Accepted,"real split route selects voyage");if(!Accepted) return;
    int Hits=0,Large=0,Medium=0,Small=0;std::int64_t ExpectedScore=0;bool HaveLastSmall=false;
    for(int Wave=1;Wave<=3;++Wave) {
        Check(Voyage.GetLevel()==Wave&&Voyage.GetRockCount()==static_cast<std::size_t>(Wave==3?7:6),"authored wave opens with the original six/six/seven large rocks");
        while(Voyage.GetLevel()==Wave&&!Voyage.GetStatus().Over&&!Voyage.GetStatus().Won&&Hits<140) {
            const auto Count=Voyage.GetRockCount();if(Count==0) {Check(false,"active wave must have a real rock to shoot");return;}
            if(Wave==3&&Count==1) {
                LastSmall=Voyage;HaveLastSmall=true;Access::Ufo(Voyage);Access::Ufo(Endless);
            }
            const int Size=Access::Aim(Voyage);Check(Access::Aim(Endless)==Size,"paired endless route shoots the same real rock size");
            ++Hits;Large+=Size==3;Medium+=Size==2;Small+=Size==1;ExpectedScore+=AsteroidsGame::RockPoints(Size);
            Voyage.Step({});Endless.Step({});
            Check(Voyage.GetStatus().Score==ExpectedScore,"each actual collision awards only the original size-based score");
            if(Size>1 || Count>1) {
                const auto ExpectedCount=Size>1?Count+1:Count-1;
                Check(Voyage.GetRockCount()==ExpectedCount&&!Voyage.GetStatus().Won,"splitting children must be destroyed before a wave can clear");
            }
            if(Wave<3 || !Voyage.GetStatus().Won) Check(Access::Snapshot(Voyage)==Access::Snapshot(Endless),"precompletion voyage preserves paired endless physics splitting and RNG");
        }
        if(Wave<3) Check(!Voyage.GetStatus().Over&&!Voyage.GetStatus().Won&&Voyage.GetLevel()==Wave+1,"first two real clearances advance without victory");
    }
    Check(Hits==133&&Large==19&&Medium==38&&Small==76,"all nineteen original large rocks and their full split trees were actually destroyed");
    Check(Voyage.GetStatus().Won&&!Voyage.GetStatus().Over&&Voyage.GetStatus().Lives==3&&Voyage.GetLevel()==3&&Voyage.GetRockCount()==0,"third completed wave wins without spawning wave four or consuming a life");
    Check(Voyage.GetStatus().Score==20900&&Voyage.GetUfoCount()==1,"victory adds no bonus and surviving UFO does not block original rock-clear rule");
    Check(Endless.GetLevel()==4&&Endless.GetRockCount()==8&&!Endless.GetStatus().Won&&!Endless.GetStatus().Over,"default companion continues normally into its eight-rock fourth wave");
    Frame F;Voyage.Render(F);Check(Text(F,"THREE WAVES CLEARED!")&&Text(F,"Pad A")&&Text(F,"Enter")&&Text(F,"R/Restart")&&!Voyage.IsFireReady(),"finish presents completion and existing retry controls while firing is disabled");
    const auto Frozen=Access::Snapshot(Voyage);const auto Picture=F;const auto Note=Voyage.GetStatus().Note;
    Input Held;Held.Up=Held.Right=Held.Fire=Held.Action=true;Held.FirePressed=Held.ActionPressed=true;
    for(int N=0;N<6;++N) Voyage.Step(Held);Voyage.Render(F);
    Check(Access::Snapshot(Voyage)==Frozen&&SameFrame(Picture,F)&&Voyage.GetStatus().Note==Note,"won state freezes movement bullets UFOs timers score and presentation");
    for(bool Controller:{false,true}) {
        auto Replay=Voyage;const bool Retried=Controller?Replay.SourceControllerButton(0):Replay.SourceKeyDown(6);AsteroidsGame Fresh;Fresh.SetOption(1,730);
        Check(Retried&&Replay.GetOption()==1&&!Replay.GetStatus().Won&&!Replay.GetStatus().Over&&Access::Snapshot(Replay)==Access::Snapshot(Fresh),"fresh A or Enter replays the voyage with its original seed and mode");
    }
    Check(HaveLastSmall,"actual split route retained a one-small-rock companion for lethal settlement");
    if(HaveLastSmall) {
        Access::LethalLastRock(LastSmall);LastSmall.Step({});
        Check(LastSmall.GetStatus().Over&&!LastSmall.GetStatus().Won&&LastSmall.GetStatus().Lives==0&&LastSmall.GetRockCount()==0&&LastSmall.GetLevel()==3
            &&LastSmall.GetStatus().Score==20900,"last-life collision wins over simultaneous actual final-rock clearance");
    }
}
void DriverCleanup() {
    Driver D;Check(D.Select("asteroids",730),"Driver selects existing Asteroids");D.Advance(Driver::StepSeconds*2.5);
    Input Stale;Stale.Up=Stale.Fire=Stale.Action=true;Stale.FirePressed=Stale.ActionPressed=true;D.SetInput(Stale);
    const bool Accepted=D.SetOption(1);Check(Accepted&&D.GetOption()==1&&D.Ticks()==0&&D.GetSeed()==730,"Driver mode selection retains seed and resets accounting");if(!Accepted) return;
    Check(D.Advance(Driver::StepSeconds*.5)==0,"mode selection clears prior fractional time");
    AsteroidsGame Expected;Expected.SetOption(1,730);Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"mode selection clears stale thrust brake and fire before the first step");
    D.SetPaused(true);D.SetInput(Stale);D.Restart();Expected.Reset(730);Expected.Render(F);
    Check(D.GetOption()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart retains voyage while clearing pause and progress");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"Restart discards old held and fresh controls");
}
}
int main() {
    Modes();ActualVoyage();DriverCleanup();
    std::cout<<"Asteroids voyage: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
