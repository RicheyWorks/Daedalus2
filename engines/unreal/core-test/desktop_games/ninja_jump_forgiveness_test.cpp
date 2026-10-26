// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop { namespace platformers {
struct TestAccess { static NinjaPlayer& PlayerOf(EmberstepGame& G) {return G.Player;} };
}}}
namespace {
using Player=platformers::NinjaPlayer;
const std::vector<Rect> Floor{{100,300,100,12}},Empty;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {return std::isfinite(A) && std::isfinite(B) && std::abs(A-B)<1e-8;}
std::array<double,15> OriginalState(const Player& P) {
    return {{P.X,P.Y,P.VX,P.VY,static_cast<double>(P.OnGround),static_cast<double>(P.Facing),static_cast<double>(P.AttackCooldown),
        static_cast<double>(P.Health),static_cast<double>(P.Invincible),static_cast<double>(P.DoubleJump),static_cast<double>(P.Spinning),
        static_cast<double>(P.SpinCooldown),static_cast<double>(P.OnWall),static_cast<double>(P.WallDir),static_cast<double>(P.JumpWasDown)}};
}
Player ReadPlayer(const std::vector<double>& V) {
    Player P;P.X=V[0];P.Y=V[1];P.VX=V[2];P.VY=V[3];P.OnGround=V[4]!=0;P.Facing=static_cast<int>(V[5]);
    P.AttackCooldown=static_cast<int>(V[6]);P.Health=static_cast<int>(V[7]);P.Invincible=static_cast<int>(V[8]);
    P.DoubleJump=V[9]!=0;P.Spinning=static_cast<int>(V[10]);P.SpinCooldown=static_cast<int>(V[11]);
    P.OnWall=V[12]!=0;P.WallDir=static_cast<int>(V[13]);P.JumpWasDown=V[14]!=0;return P;
}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()
        || A.Background.R!=B.Background.R || A.Background.G!=B.Background.G || A.Background.B!=B.Background.B || A.Background.A!=B.Background.A) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y || C.C.X!=D.C.X || C.C.Y!=D.C.Y
            || C.Size!=D.Size || C.Label!=D.Label || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }return true;
}
Input Tap() {Input I;I.JumpPressed=true;return I;}
Player WalkedOff() {
    Player P;P.X=200;P.Y=300;P.Update({},Floor);Input Right;Right.Right=true;P.Update(Right,Floor);return P;
}
void SourceNinjaSteps(const char* Filename) {
    std::ifstream File(Filename);Check(static_cast<bool>(File),"existing platformer fixture is readable");if(!File) return;
    std::string Line;int Cases=0;
    while(std::getline(File,Line)) {
        std::istringstream In(Line);std::string Tag,Label;In>>Tag>>Label;if(Tag!="NSTEP") continue;
        std::vector<double> V;double N;while(In>>N) V.push_back(N);
        const bool Shape=In.eof() && V.size()==38;Check(Shape,"NSTEP "+Label+" retains original input/output shape");if(!Shape) continue;
        auto P=ReadPlayer(V);const int Frames=static_cast<int>(V[15]),Preset=static_cast<int>(V[16]),Keys=static_cast<int>(V[17]);
        if(Frames<0 || Frames>6000) {Check(false,"NSTEP steps remain bounded");continue;}
        Input I;I.Left=(Keys&1)!=0;I.Right=(Keys&2)!=0;I.Up=(Keys&4)!=0;I.Down=(Keys&8)!=0;I.Jump=(Keys&16)!=0 || V[22]!=0;
        I.AxisX=V[18];I.AxisY=V[19];std::vector<Rect> Platforms;
        if(Preset==1) {
            EmberstepGame G;G.Reset(10);platformers::TestAccess::PlayerOf(G)=P;
            I.PadLeft=V[20]<0;I.PadRight=V[20]>0;I.PadDown=V[21]<0;I.PadUp=V[21]>0;
            for(int F=0;F<Frames;++F) G.Step(I);
            P=G.GetPlayer();
        } else {
            if(Preset==2) Platforms={{100,300,200,12}};
            for(int F=0;F<Frames;++F) P.Update(I,Platforms,V[20],V[21]);
        }
        const auto Actual=OriginalState(P);
        for(std::size_t F=0;F<Actual.size();++F) Check(Close(Actual[F],V[F+23]),"NSTEP "+Label+" original field "+std::to_string(F));
        ++Cases;
    }
    Check(Cases==83,"all 83 NSTEP source cases consumed without other platformer tags");
}
void GraceAndImmediateJumps() {
    auto P=WalkedOff();Check(!P.OnGround && !P.DoubleJump && Close(P.X,205),"normal movement leaves a real platform without spending an air jump");
    for(int N=0;N<5;++N) P.Update({},Floor);
    P.Update(Tap(),Floor);
    Check(P.VY==-11 && !P.OnGround && P.DoubleJump,"sixth decision after walkoff still allows the normal ground jump");
    P.Update({},Floor);P.Update(Tap(),Floor);
    Check(P.VY==-9 && !P.DoubleJump,"successful ledge jump consumes grace so the next fresh jump is the normal air jump");
    P=WalkedOff();for(int N=0;N<6;++N) P.Update({},Floor);P.Update(Tap(),Floor);
    Check(P.VY>0 && !P.DoubleJump,"seventh walkoff decision is too late for ground grace");
    P=Player{};P.X=150;P.Y=300;P.Update(Tap(),Floor);
    Check(P.VY==-11 && P.Y==289 && !P.OnGround && P.DoubleJump,"immediate ground jump keeps its original first-frame trajectory");
    P.Update({},Floor);P.Update(Tap(),Floor);
    Check(P.VY==-9 && Close(P.Y,269.6) && !P.DoubleJump,"normal second jump retains its original air trajectory");
    Input Held;Held.Jump=true;P.Update(Held,Floor);Check(Close(P.VY,-8.4) && !P.DoubleJump,"held jump cannot generate another fresh air jump");
    P=Player{};P.X=35;P.Y=200;P.VY=2;P.OnGround=false;P.DoubleJump=false;P.Update(Tap(),Empty);
    Check(P.X==45 && Close(P.Y,202.6) && P.VX==7 && P.VY==-10 && !P.OnWall && P.DoubleJump,"fresh wall jump preserves original movement then push trajectory");
}
void LandingQueue() {
    Player P;P.X=150;P.Y=260;P.OnGround=false;P.DoubleJump=true;P.Update(Tap(),Floor);
    Check(P.VY==-9 && !P.DoubleJump,"early landing fixture first spends a real air jump");
    int Wait=0;while(!(P.VY>0 && P.Y>=265) && !P.OnGround && Wait<60) {P.Update({},Floor);++Wait;}
    Check(Wait<60 && !P.OnGround && !P.DoubleJump,"ordinary gravity supplies a descending player with no air jump left");
    P.Update(Tap(),Floor);Check(P.VY>0 && !P.OnGround,"unavailable tap queues instead of inventing another air jump");P.Update({},Floor);
    Check(P.Y==289 && P.VY==-11 && !P.OnGround && P.DoubleJump,"queued landing snaps to the platform then launches upward in that same step");
    P=Player{};P.X=150;P.Y=277;P.OnGround=false;P.DoubleJump=false;P.Update(Tap(),Floor);Input Held;Held.Jump=true;
    for(int N=0;N<5;++N) P.Update(Held,Floor);
    Check(P.Y==289 && P.VY==-11 && !P.OnGround,"landing on the sixth buffer frame still consumes the original tap");
    P=Player{};P.X=150;P.Y=273;P.OnGround=false;P.DoubleJump=false;P.Update(Tap(),Floor);
    for(int N=0;N<6;++N) P.Update(Held,Floor);
    Check(P.Y==300 && P.VY==0 && P.OnGround && !P.DoubleJump,"landing after the sixth buffer frame cannot revive an expired tap");
    for(int N=0;N<8;++N) P.Update(Held,Floor);
    Check(P.Y==300 && P.VY==0 && P.OnGround,"holding an expired tap through landing never automatically hops");
}
void WallCancellationAndArrival() {
    const std::vector<Rect> Landing{{30,220,200,12}};Player P;P.X=45;P.Y=200;P.OnGround=false;P.DoubleJump=false;P.Update(Tap(),Landing);
    Input Left;Left.Left=true;P.Update(Left,Landing);P.Update(Left,Landing);
    Check(P.OnWall && P.X==35 && P.VY==1,"pending ground tap cannot become a delayed wall jump");
    Input Right;Right.Right=true;P.Update(Right,Landing);
    Check(!P.OnWall && P.DoubleJump && P.VY>0,"leaving the wall cannot turn the pending tap into a delayed air jump");
    P.Update(Right,Landing);P.Update(Right,Landing);
    Check(P.OnGround && P.Y==220 && P.VY==0,"wall attachment cancels the ground queue before a nearby landing");
    P=Player{};P.X=730;P.Y=220;P.Update({},platformers::NinjaPlatforms());
    for(int N=0;N<6;++N) P.Update(Right,platformers::NinjaPlatforms());
    Check(P.X==760 && Close(P.Y,232.6),"ordinary walkoff reaches the right wall with its last grace decision available");
    Right.JumpPressed=true;P.Update(Right,platformers::NinjaPlatforms());
    Check(P.X==755 && Close(P.Y,236.8) && P.VX==-7 && P.VY==-10 && !P.OnWall,"wall arrival keeps the original wall trajectory instead of using ledge grace first");
    auto Land=P;Land.X=150;Land.Y=295;Land.VY=1;Land.OnGround=false;Land.OnWall=false;Land.DoubleJump=false;Land.Update({},Floor);
    Check(Land.OnGround && Land.Y==300 && Land.VY==0,"successful wall jump consumes any pending landing tap");
    P.Update(Tap(),Empty);Check(P.VY==-9,"successful wall jump clears grace before the next fresh air jump");
}
void ResetWindows() {
    EmberstepGame G;G.Reset(730);auto& P=platformers::TestAccess::PlayerOf(G);
    P=Player{};P.X=150;P.Y=200;P.OnGround=false;P.DoubleJump=false;P.Update(Tap(),Empty);
    auto Probe=P;Probe.Y=295;Probe.VY=1;Probe.Update({},Floor);
    Check(Probe.VY==-11 && Probe.Y==289,"reset fixture contains an actual pending landing tap");
    G.Reset(730);Probe=G.GetPlayer();Probe.X=150;Probe.Y=295;Probe.VY=1;Probe.OnGround=false;Probe.DoubleJump=false;Probe.Update({},Floor);
    Check(Probe.OnGround && Probe.Y==300 && Probe.VY==0,"game Reset clears a real pending landing window");
    platformers::TestAccess::PlayerOf(G)=WalkedOff();G.Reset(730);Probe=G.GetPlayer();
    Probe.X=205;Probe.Y=200;Probe.VY=0;Probe.OnGround=false;Probe.DoubleJump=false;Probe.Update(Tap(),Floor);
    Check(Probe.VY>0 && !Probe.DoubleJump,"game Reset also clears a real walkoff grace window");
}
void DriverEdges() {
    Driver D;Check(D.Select("emberstep",730),"existing Driver selects Ninja");EmberstepGame Expected;Expected.Reset(730);
    Input Jump=Tap();Jump.Jump=true;D.SetInput(Jump);D.Advance(Driver::StepSeconds*8);Expected.Step(Jump);
    Input Held;Held.Jump=true;for(int N=0;N<7;++N) Expected.Step(Held);Frame F;Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F),"catch-up consumes one jump edge and preserves held input without requeuing");
    const auto Before=D.GetFrame();D.SetPaused(true);D.SetInput(Tap());
    Check(D.Advance(Driver::StepSeconds*8)==0 && SameFrame(Before,D.GetFrame()),"pause freezes the existing jump trajectory");
    D.SetPaused(false);D.Advance(Driver::StepSeconds);Expected.Step({});Expected.Render(F);
    Check(SameFrame(D.GetFrame(),F),"resume clears a stale queued input edge instead of performing an air jump");
    D.SetInput(Tap());D.Restart();EmberstepGame Fresh;Fresh.Reset(730);Fresh.Render(F);
    Check(SameFrame(D.GetFrame(),F),"Driver restart clears pending edges and player forgiveness state");
}
}
int main(int Argc,char** Argv) {
    if(Argc!=2) {std::cerr<<"Usage: ninja_jump_forgiveness_test <platformers_parity.txt>\n";return 2;}
    SourceNinjaSteps(Argv[1]);GraceAndImmediateJumps();LandingQueue();WallCancellationAndArrival();ResetWindows();DriverEdges();
    std::cout<<"Ninja jump forgiveness: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
