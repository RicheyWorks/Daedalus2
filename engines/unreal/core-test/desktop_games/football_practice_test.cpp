// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
namespace {
using Football=FootballGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A) && std::isfinite(B) && std::abs(A-B)<=1e-9*(1+std::abs(B));}
bool SamePlayer(const Football::Player& A,const Football::Player& B) {
    return A.X==B.X && A.Y==B.Y && A.Speed==B.Speed && A.Cpu==B.Cpu && A.KickCooldown==B.KickCooldown;
}
bool SameBall(const Football::Ball& A,const Football::Ball& B) {return A.X==B.X && A.Y==B.Y && A.Vx==B.Vx && A.Vy==B.Vy;}
bool SameData(const Football::State& A,const Football::State& B) {
    return SamePlayer(A.Human,B.Human) && SamePlayer(A.Cpu,B.Cpu) && SameBall(A.Football,B.Football)
        && A.HumanScore==B.HumanScore && A.CpuScore==B.CpuScore && A.Seconds==B.Seconds && A.Mode==B.Mode;
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
bool SameGame(const Football& A,const Football& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    return SameData(A.Data,B.Data) && SameFrame(F,G) && A.GetOption()==B.GetOption()
        && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note
        && A.IsKickReady()==B.IsKickReady() && A.GoalReceiptFramesRemaining()==B.GoalReceiptFramesRemaining()
        && A.KickReceiptFramesRemaining()==B.KickReceiptFramesRemaining() && A.GetLastScorer()==B.GetLastScorer()
        && A.GetLastKickReceipt()==B.GetLastKickReceipt();
}
std::string Lower(std::string Text) {for(char& C:Text) if(C>='A' && C<='Z') C=static_cast<char>(C-'A'+'a');return Text;}
bool HasText(const Frame& F,const std::string& Part) {
    const auto Wanted=Lower(Part);for(const auto& C:F.Commands) if(C.Kind==Shape::Text && Lower(C.Label).find(Wanted)!=std::string::npos) return true;
    return false;
}
bool NoteHas(const Football& G,const std::string& Part) {return Lower(G.GetStatus().Note).find(Lower(Part))!=std::string::npos;}
Input Fire() {Input I;I.FirePressed=true;return I;}
Input Action() {Input I;I.ActionPressed=true;return I;}
Football Practice() {Football G;Game& Core=G;Core.SetOption(1,730);return G;}
Football Aim() {auto G=Practice();G.Step(Fire());return G;}
Football Flight(int Targets=0) {
    auto G=Aim();G.Data.HumanScore=Targets;G.Step(Fire());return G;
}
bool Racked(const Football& G,int Targets) {
    return G.Data.Mode==Football::Phase::Playing && G.Data.HumanScore==Targets && G.Data.CpuScore==0
        && G.Data.Human.X==560 && G.Data.Human.Y==300 && G.Data.Human.KickCooldown==0
        && G.Data.Football.X==600 && G.Data.Football.Y==300 && G.Data.Football.Vx==0 && G.Data.Football.Vy==0 && G.IsKickReady();
}
Input Controls(double Left,double Right,double Up,double Down,double Ax,double Ay) {
    Input I;I.Left=Left!=0;I.Right=Right!=0;I.Up=Up!=0;I.Down=Down!=0;I.AxisX=Ax;I.AxisY=Ay;return I;
}
void SourceFootball(const char* Filename) {
    std::ifstream File(Filename);Check(static_cast<bool>(File),"existing sports fixture file is readable");if(!File) return;
    std::string Line;int Moves=0,Kicks=0,Balls=0,LineNumber=0;
    while(std::getline(File,Line)) {
        ++LineNumber;std::istringstream In(Line);std::string Tag;In>>Tag;
        if(Tag!="F_MOVE" && Tag!="F_KICK" && Tag!="F_BALL") continue; // No Dodge case is executed.
        std::vector<double> V;double N;while(In>>N) V.push_back(N);
        const auto Label=Tag+" line "+std::to_string(LineNumber);
        if(!In.eof()) {Check(false,Label+" invalid numeric token");continue;}
        if(Tag=="F_MOVE") {
            Check(V.size()==15,Label+" field count");if(V.size()!=15) continue;
            Football::Player P{V[7],V[8],V[0]!=0?2.8:3.5,V[0]!=0,static_cast<int>(V[11])};
            Football::Ball B{V[9],V[10],0,0};Football::MovePlayer(P,Controls(V[1],V[2],V[3],V[4],V[5],V[6]),B);
            Check(Close(P.X,V[12]),Label+" source x");Check(Close(P.Y,V[13]),Label+" source y");Check(Close(P.KickCooldown,V[14]),Label+" source cooldown");++Moves;
        } else if(Tag=="F_KICK") {
            Check(V.size()==9,Label+" field count");if(V.size()!=9) continue;
            Football::Player P{V[0],V[1],3.5,false,static_cast<int>(V[4])};Football::Ball B{V[2],V[3],0,0};
            Check(Football::Kick(P,B)==(V[5]!=0),Label+" source acceptance");Check(Close(B.Vx,V[6]),Label+" source vx");
            Check(Close(B.Vy,V[7]),Label+" source vy");Check(Close(P.KickCooldown,V[8]),Label+" source cooldown");++Kicks;
        } else {
            Check(V.size()==8,Label+" field count");if(V.size()!=8) continue;
            Football::Ball B{V[0],V[1],V[2],V[3]};Football::UpdateBall(B);
            Check(Close(B.X,V[4]),Label+" source x");Check(Close(B.Y,V[5]),Label+" source y");
            Check(Close(B.Vx,V[6]),Label+" source vx");Check(Close(B.Vy,V[7]),Label+" source vy");++Balls;
        }
    }
    Check(Moves==64 && Kicks==4 && Balls==6,"all 74 existing Football-only source cases are consumed unchanged");
}
void ModesAndStart() {
    Football G;Game& Core=G;Check(Core.GetOption()==0,"default Football remains Match");
    Check(Core.SetOption(1,730) && Core.GetOption()==1 && G.Data.Mode==Football::Phase::Title,"existing option API opens practice at its title");
    Check(G.Data.HumanScore==0 && G.Data.CpuScore==0 && G.Data.Football.X==600 && G.Data.Football.Y==300,"practice title prepares its centered shot without session progress");
    Input Held;Held.Fire=Held.Action=true;const auto Title=G;for(int N=0;N<8;++N) G.Step(Held);
    Check(SameGame(G,Title),"held controls alone cannot start practice");
    G.Step(Fire());Check(Racked(G,0) && G.GetLastKickReceipt()==Football::KickReceipt::None,"fresh start enters Aim without an implicit kick");
    const auto Ready=G;for(int N=0;N<8;++N) G.Step(Held);
    Check(SameGame(G,Ready),"held Fire and Action cannot kick or repeatedly rack Aim");
    Input Move;Move.PadDown=true;G.Step(Move);Check(G.Data.Human.Y==303.5 && G.Data.Football.Vx==0,"existing direct D-pad movement adjusts the aim before any kick");
    const auto Before=G;
    for(int Value:{-1,2,std::numeric_limits<int>::min(),std::numeric_limits<int>::max()}) {
        Check(!Core.SetOption(Value,12) && SameGame(G,Before),"invalid mode preserves the entire current practice");
    }
    G.Data.HumanScore=2;G.Reset(17);
    Check(G.GetOption()==1 && G.Data.Mode==Football::Phase::Title && G.Data.HumanScore==0,"Restart retains practice mode but clears this session's targets");
    G.Step(Action());Check(Racked(G,0),"fresh Action also starts from Title without kicking");
    Check(Core.SetOption(0,17),"mode selector can return to Match");Football Fresh;
    Check(SameData(G.Data,Fresh.Data),"Match mode restores its original State defaults");
    Frame F,H;G.Render(F);Fresh.Render(H);Check(SameFrame(F,H),"Match title rendering remains unchanged");
}
void KickFlightAndRerack() {
    auto G=Aim();const auto Cpu=G.Data.Cpu;const double Clock=G.Data.Seconds;
    Input Down;Down.Down=true;for(int N=0;N<4;++N) G.Step(Down);
    auto ExpectedHuman=G.Data.Human;auto ExpectedBall=G.Data.Football;Input Kick=Fire();Kick.Down=true;
    Football::MovePlayer(ExpectedHuman,Kick,ExpectedBall);Football::Kick(ExpectedHuman,ExpectedBall);G.Step(Kick);
    Check(SamePlayer(G.Data.Human,ExpectedHuman) && SameBall(G.Data.Football,ExpectedBall),"Aim kick first moves human then sets launch velocity without advancing the ball");
    Check(!G.IsKickReady() && NoteHas(G,"flight") && G.KickReceiptFramesRemaining()==Football::KickReceiptFrames,"accepted kick enters a distinct one-shot Flight state");
    ExpectedBall=G.Data.Football;Football::UpdateBall(ExpectedBall);G.Step(Fire());
    Check(SameBall(G.Data.Football,ExpectedBall) && G.Data.Human.KickCooldown==11,"next fixed frame begins physics and ignores a remote repeat kick");
    for(int N=0;N<11;++N) G.Step(Fire());
    Frame F;G.Render(F);
    Check(G.Data.Human.KickCooldown==0 && !G.IsKickReady() && NoteHas(G,"flight") && !HasText(F,"Kick READY"),"Flight stays one-shot after cooldown even under fresh repeated kick presses");
    Check(SamePlayer(G.Data.Cpu,Cpu) && G.Data.Seconds==Clock && G.Data.CpuScore==0,"practice never advances CPU or a match clock");
    G=Flight(1);Input Both=Fire();Both.ActionPressed=true;Both.Right=true;G.Step(Both);
    Check(Racked(G,1) && G.GetLastKickReceipt()==Football::KickReceipt::None,"live Action takes priority over simultaneous movement and Fire while preserving targets");
    Down={};Down.Down=true;G.Step(Down);G.Step(Action());Check(Racked(G,1),"Aim reset also keeps the same target and clears positioning");
    G=Flight();G.Data.Football={500,300,2,0};G.Data.Human.X=490;G.Data.Human.Y=300;G.Step({});
    Check(Close(G.Data.Football.X,502) && Close(G.Data.Football.Vx,6),"ordinary human contact can still deflect the ball during Flight");
    G=Flight();G.Data.Football={500,300,2,0};G.Data.Cpu.X=502;G.Data.Cpu.Y=300;const auto Hidden=G.Data.Cpu;G.Step({});
    Check(Close(G.Data.Football.Vx,1.92) && SamePlayer(G.Data.Cpu,Hidden),"hidden stationary CPU never deflects the practice ball");
}
void PocketBoundary() {
    auto G=Flight();G.Data.Football={749,322,2,0};G.Step({});
    Check(G.Data.HumanScore==1 && G.Data.CpuScore==0,"right-goal pocket includes its exact 22-pixel tolerance");
    G=Flight();G.Data.Football={749,322.01,2,0};G.Step({});
    Check(G.Data.HumanScore==0 && G.Data.CpuScore==0 && !G.GetStatus().Over && NoteHas(G,"missed the gold pocket"),"goal just outside the required pocket is a friendly miss");
}
void Presentation() {
    auto G=Aim();Frame F;G.Render(F);
    Check(F.Width==800 && F.Height==600 && HasText(F,"TARGET PRACTICE") && HasText(F,"Targets 0/3"),"practice has a compact session-target HUD");
    Check(!HasText(F,"CPU") && !HasText(F,"TIME:"),"practice draws no opponent or timed-match labels");
    int Markers=0,Gold=0,Mint=0,Muted=0;bool Direction=false;
    const auto D=sports_detail::Unit(G.Data.Football.X-G.Data.Human.X,G.Data.Football.Y-G.Data.Human.Y);
    for(const auto& C:F.Commands) {
        if(C.Kind==Shape::Rectangle && C.A.X==750 && C.B.X==20 && C.B.Y==44) {
            ++Markers;if(C.Tint.R==255 && C.Tint.G==210 && C.Tint.B==70) ++Gold;
            if(C.Tint.R==90 && C.Tint.G==220 && C.Tint.B==160) ++Mint;
            if(C.Tint.R==85 && C.Tint.G==125 && C.Tint.B==100) ++Muted;
        }
        if(C.Kind==Shape::Line && C.A.X==G.Data.Football.X && C.A.Y==G.Data.Football.Y) {
            const double X=C.B.X-C.A.X,Y=C.B.Y-C.A.Y;
            Direction=Direction || (Close(X*D.Y-Y*D.X,0) && X*D.X+Y*D.Y>0 && std::hypot(X,Y)<=40);
        }
    }
    Check(Markers==3 && Gold==1 && Mint==0 && Muted==2,"three pocket markers distinguish required and future targets");
    Check(Direction && HasText(F,"not a full path"),"Aim shows only the initial Unit direction with an honest short-cue explanation");
    const auto Before=G;Frame Again;for(int N=0;N<8;++N) {G.Render(Again);G.GetStatus();}
    Check(SameGame(G,Before) && SameFrame(F,Again),"practice rendering and status queries cannot change the session");
    G=Flight();G.Data.Football={749,300,2,0};G.Step({});G.Render(F);int Completed=0;
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle && C.A.X==750 && C.B.Y==44 && C.Tint.R==90 && C.Tint.G==220 && C.Tint.B==160) ++Completed;
    Check(Completed==1 && G.GetStatus().Score==1,"a completed pocket is marked while status exposes only session targets");
}
void CompleteRealRoute() {
    auto G=Practice();G.Step(Fire());int FlightSteps=0;
    const auto Shoot=[&G,&FlightSteps]() {
        G.Step(Fire());int Steps=0;
        while(G.Data.Mode==Football::Phase::Playing && G.GoalReceiptFramesRemaining()==0 && Steps<240) {G.Step({});++Steps;++FlightSteps;}
        return Steps;
    };
    for(int Target=0;Target<3;++Target) {
        if(Target==1) {
            Input Across;Across.Right=true;for(int N=0;N<11;++N) G.Step(Across);
            Input Above;Above.Up=true;for(int N=0;N<11;++N) G.Step(Above);
            const int Settled=Shoot(); // A nearly vertical real kick cannot reach either goal.
            Check(Settled>0 && Settled<=240 && G.Data.HumanScore==1 && G.Data.CpuScore==0
                && !G.GetStatus().Over && NoteHas(G,"slowed"),"ordinary off-goal kick settles into a bounded friendly retry without losing targets");
            G.Step(Action());Check(Racked(G,1),"fresh continuation after a settled ball restores Aim instead of locking Fire");
            Shoot(); // Deliberately kick straight while the required pocket is now above center.
            Check(G.Data.HumanScore==1 && G.Data.CpuScore==0 && !G.GetStatus().Over && NoteHas(G,"missed the gold pocket"),"a normal off-target goal offers a friendly retry with progress intact");
            const auto ResultBall=G.Data.Football;Input Wait;Wait.Fire=Wait.Action=true;
            for(int N=0;N<59;++N) G.Step(Wait);
            Check(G.GoalReceiptFramesRemaining()==1 && SameBall(G.Data.Football,ResultBall) && !G.IsKickReady(),"held controls cannot skip or kick during the feedback window");
            G.Step(Wait);Check(Racked(G,1),"sixty feedback frames automatically prepare the same unfinished target");
            Input Reposition;Reposition.Down=true;G.Step(Reposition);Input Rerack=Fire();Rerack.ActionPressed=Rerack.Right=true;G.Step(Rerack);
            Check(Racked(G,1),"deliberate rerack keeps the earned target and suppresses a simultaneous kick");
        }
        Input Move;Move.Down=Target==1;Move.Up=Target==2;
        if(Target>0) for(int N=0;N<4;++N) G.Step(Move);
        const int ThisShot=Shoot();
        const bool Hit=G.Data.HumanScore==Target+1 && G.Data.CpuScore==0;
        Check(Hit,"normal movement kick and flight hit the middle upper then lower target");if(!Hit) return;
        Check(ThisShot>0 && ThisShot<=240,"each real target attempt resolves within its bounded flight");
        if(Target<2) {G.Step(Target==0?Fire():Action());Check(Racked(G,Target+1),"normal fresh continuation keeps targets and gives another deliberate aim");}
    }
    Check(FlightSteps<=1200 && G.Data.Mode==Football::Phase::Won && G.GetStatus().Over && G.GetStatus().Won && G.GetStatus().Score==3,"three actual pocket goals complete the session at exactly three targets");
    const auto Complete=G;Input Held;Held.Fire=Held.Action=Held.Right=true;for(int N=0;N<8;++N) G.Step(Held);
    Check(SameGame(G,Complete),"completed practice ignores held controls and freezes its result");
    auto Again=G;Again.Step(Fire());Check(Racked(Again,0) && Again.GetOption()==1,"fresh Fire replays completion directly into clean Aim without a kick");
    G.Step(Action());Check(Racked(G,0) && G.GetOption()==1,"fresh Action offers the same one-press clean replay");
    G.Reset(730);Check(G.Data.Mode==Football::Phase::Title && G.Data.HumanScore==0 && G.GetOption()==1,"host Restart remains a deliberate return to practice title");
}
void DriverAndMatchEnd() {
    Driver D;Check(D.Select("football",730),"existing Driver selects Football");D.SetPaused(true);
    Input Stale=Fire();Stale.ActionPressed=Stale.Right=true;D.SetInput(Stale);
    Check(D.SetOption(1) && D.GetOption()==1 && !D.IsPaused() && D.Ticks()==0,"mode selection restarts practice and clears driver pause");
    auto Expected=Practice();Frame F;Expected.Render(F);D.Advance(Driver::StepSeconds*8);
    Check(SameFrame(D.GetFrame(),F),"mode change clears stale start reset and movement input");
    Input Start=Fire();Start.Fire=true;D.SetInput(Start);D.Advance(Driver::StepSeconds*8);
    Expected.Step(Fire());Input Held;Held.Fire=true;for(int N=0;N<7;++N) Expected.Step(Held);Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F) && Racked(Expected,0),"catch-up consumes one start edge without immediately kicking");
    D.SetInput(Start);D.Advance(Driver::StepSeconds*8);Expected.Step(Fire());for(int N=0;N<7;++N) Expected.Step(Held);Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F),"a later kick edge is consumed only once across flight catch-up");
    const auto Before=D.GetFrame();D.SetPaused(true);D.SetInput(Stale);
    Check(D.Advance(Driver::StepSeconds*8)==0 && SameFrame(Before,D.GetFrame()),"normal pause freezes the practice attempt");
    Check(!D.SetOption(2) && D.GetOption()==1 && D.IsPaused() && SameFrame(Before,D.GetFrame()),"invalid driver option preserves practice and pause");
    D.Restart();Expected=Practice();Expected.Render(F);
    Check(D.GetOption()==1 && !D.IsPaused() && SameFrame(D.GetFrame(),F),"Driver Restart clears the session and pending input while retaining mode");
    Football Match;Match.Step(Fire());int Steps=1;
    while(!Match.GetStatus().Over && Steps<5500) {Match.Step({});++Steps;}
    const auto End=Match.GetStatus();
    Check(End.Over && Match.Data.Seconds==0 && Steps<=5500,"unchanged default Match still reaches its real ninety-second result");
    Check(Match.Data.Mode==(Match.Data.HumanScore>Match.Data.CpuScore?Football::Phase::Won:
        (Match.Data.CpuScore>Match.Data.HumanScore?Football::Phase::Lost:Football::Phase::Draw)),"default result still follows the original score comparison");
    std::cout<<"Football default match ended after "<<Steps<<" fixed steps\n";
}
}
int main(int Argc,char** Argv) {
    if(Argc!=2) {std::cerr<<"Usage: football_practice_test <sports_parity.txt>\n";return 2;}
    SourceFootball(Argv[1]);ModesAndStart();KickFlightAndRerack();PocketBoundary();Presentation();CompleteRealRoute();DriverAndMatchEnd();
    std::cout<<"Football practice: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
