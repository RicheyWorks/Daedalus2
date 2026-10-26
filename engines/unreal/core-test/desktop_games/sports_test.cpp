// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopSportsCore.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
namespace {
int Checks=0,SourceCases=0;
void Check(bool V,const std::string& Label) {
    ++Checks;if(!V) throw std::runtime_error(Label);
}
void Near(double A,double B,const std::string& Label) {
    Check(std::isfinite(A) && std::abs(A-B)<=1e-9*(1+std::abs(B)),Label);
}
Input Controls(double Left,double Right,double Up,double Down,double Ax,double Ay,double Jump=0) {
    Input I;I.Left=Left!=0;I.Right=Right!=0;I.Up=Up!=0;I.Down=Down!=0;
    I.AxisX=Ax;I.AxisY=Ay;I.Jump=Jump!=0;return I;
}
void Fixtures(const char* Path) {
    std::ifstream File(Path);Check(File.good(),"sports fixture file opened");
    std::string Line;
    while(std::getline(File,Line)) {
        if(Line.empty() || Line[0]=='#') continue;
        std::istringstream Stream(Line);std::string Tag;Stream>>Tag;
        std::vector<double> V;double N;
        while(Stream>>N) { V.push_back(N); }
        const std::string Label=Tag+" case "+std::to_string(++SourceCases);
        if(Tag=="F_MOVE") {
            Check(V.size()==15,Label+" columns");
            FootballGame::Player P{V[7],V[8],V[0]!=0 ? 2.8 : 3.5,V[0]!=0,static_cast<int>(V[11])};
            FootballGame::Ball B{V[9],V[10],0,0};
            FootballGame::MovePlayer(P,Controls(V[1],V[2],V[3],V[4],V[5],V[6]),B);
            Near(P.X,V[12],Label+" x");Near(P.Y,V[13],Label+" y");Near(P.KickCooldown,V[14],Label+" cooldown");
        } else if(Tag=="F_KICK") {
            Check(V.size()==9,Label+" columns");
            FootballGame::Player P{V[0],V[1],3.5,false,static_cast<int>(V[4])};
            FootballGame::Ball B{V[2],V[3],0,0};
            Check(FootballGame::Kick(P,B)==(V[5]!=0),Label+" kick");
            Near(B.Vx,V[6],Label+" vx");Near(B.Vy,V[7],Label+" vy");Near(P.KickCooldown,V[8],Label+" cooldown");
        } else if(Tag=="F_BALL") {
            Check(V.size()==8,Label+" columns");FootballGame::Ball B{V[0],V[1],V[2],V[3]};
            FootballGame::UpdateBall(B);Near(B.X,V[4],Label+" x");Near(B.Y,V[5],Label+" y");
            Near(B.Vx,V[6],Label+" vx");Near(B.Vy,V[7],Label+" vy");
        } else if(Tag=="D_TEAM") {
            Check(V.size()==9,Label+" columns");
            const auto P=DodgeBallGame::MakePlayer(static_cast<int>(V[0]),static_cast<int>(V[1]),V[2]!=0);
            Near(P.X,V[3],Label+" x");Near(P.Y,V[4],Label+" y");Near(P.Power,V[5],Label+" power");
            Near(P.Speed,V[6],Label+" speed");Near(P.Health,V[7],Label+" hp");Check(P.FacingRight==(V[8]!=0),Label+" facing");
        } else if(Tag=="D_THROW") {
            Check(V.size()==10,Label+" columns");
            auto P=DodgeBallGame::MakePlayer(static_cast<int>(V[0]),0,false,static_cast<int>(V[1]));
            P.Charge=static_cast<int>(V[2]);P.HasBall=true;DodgeBallGame::Ball B;B.Owner=0;
            DodgeBallGame::CountryThrow(B,P,{0.6,0.8},V[3]!=0 || P.Charge>30);
            Near(B.Vx,V[4],Label+" vx");Near(B.Vy,V[5],Label+" vy");Check(B.PowerBall==(V[6]!=0),Label+" power flag");
            Near(P.ThrowCooldown,V[7],Label+" cooldown");Near(P.Charge,V[8],Label+" charge");
            Check(P.HasBall==(V[9]!=0),Label+" possession");Check(B.Owner==-1 && B.InAir,Label+" throw state");
        } else if(Tag=="D_HUMAN") {
            Check(V.size()==30,Label+" columns");
            auto P=DodgeBallGame::MakePlayer(static_cast<int>(V[0]),static_cast<int>(V[1]),false);
            P.X=V[2];P.Y=V[3];P.BaseY=V[4];P.HasBall=V[5]!=0;P.Charge=static_cast<int>(V[6]);
            P.OnGround=V[7]!=0;P.JumpVelocity=V[8];P.JumpCooldown=static_cast<int>(V[9]);P.JumpWasDown=V[10]!=0;P.ThrowCooldown=4;
            Input I=Controls(V[11],V[12],V[13],V[14],V[15],V[16],V[17]);
            I.PadLeft=V[18]!=0;I.PadRight=V[19]!=0;I.PadUp=V[20]!=0;I.PadDown=V[21]!=0;
            DodgeBallGame::MoveHuman(P,I);DodgeBallGame::BoundAndCooldown(P);
            Near(P.X,V[22],Label+" x");Near(P.Y,V[23],Label+" y");Check(P.FacingRight==(V[24]!=0),Label+" facing");
            Near(P.Charge,V[25],Label+" charge");Check(P.OnGround==(V[26]!=0),Label+" grounded");Near(P.JumpVelocity,V[27],Label+" jump");
            Near(P.JumpCooldown,V[28],Label+" jump cooldown");Near(P.ThrowCooldown,V[29],Label+" throw cooldown");
        } else if(Tag=="D_BALL") {
            Check(V.size()==11,Label+" columns");DodgeBallGame::Ball B;
            B.X=V[0];B.Y=V[1];B.Vx=V[2];B.Vy=V[3];B.PowerBall=V[4]!=0;B.InAir=true;
            std::array<DodgeBallGame::Player,6> Team{};DodgeBallGame::UpdateBall(B,Team);
            Near(B.X,V[5],Label+" x");Near(B.Y,V[6],Label+" y");Near(B.Vx,V[7],Label+" vx");Near(B.Vy,V[8],Label+" vy");
            Check(B.InAir==(V[9]!=0),Label+" airborne");Check(B.PowerBall==(V[10]!=0),Label+" power flag");
        } else if(Tag=="D_CATCH") {
            Check(V.size()==8,Label+" columns");auto P=DodgeBallGame::MakePlayer(0,0,false);
            P.OnGround=V[0]!=0;P.Health=static_cast<int>(V[2]);DodgeBallGame::Ball B;
            B.PowerBall=V[1]!=0;B.X=P.X+V[3];B.Y=P.Y;B.InAir=true;
            Check(DodgeBallGame::Catch(B,P,0)==(V[4]!=0),Label+" catch");
            Check(B.InAir==(V[5]!=0),Label+" airborne");Check(B.PowerBall==(V[6]!=0),Label+" power flag");
            Check(P.HasBall==(V[7]!=0),Label+" possession");Check((B.Owner==0)==(V[4]!=0),Label+" owner");
        } else if(Tag=="D_PICKUP") {
            Check(V.size()==6,Label+" columns");auto P=DodgeBallGame::MakePlayer(0,0,false);
            P.Health=static_cast<int>(V[1]);DodgeBallGame::Ball B;B.X=P.X+V[0];B.Y=P.Y;
            B.InAir=V[2]!=0;B.Owner=V[3]!=0 ? 0 : -1;
            Check(DodgeBallGame::Pickup(B,P,0)==(V[4]!=0),Label+" pickup");Check(P.HasBall==(V[5]!=0),Label+" possession");
        } else if(Tag=="D_DAMAGE") {
            Check(V.size()==3,Label+" columns");auto P=DodgeBallGame::MakePlayer(0,0,false);
            P.Health=static_cast<int>(V[0]);DodgeBallGame::Ball B;B.X=P.X;B.Y=P.Y;B.InAir=true;B.PowerBall=V[1]!=0;B.Vx=8;B.Vy=-3;
            Check(DodgeBallGame::Hit(B,P),Label+" hit");Near(P.Health,V[2],Label+" health");
            Check(!B.InAir && !B.PowerBall && B.Owner==-1,Label+" ball released");Near(B.Vx,-3.2,Label+" hit vx");Near(B.Vy,1.2,Label+" hit vy");
        } else throw std::runtime_error("Unknown fixture "+Tag);
    }
    Check(SourceCases==299,"all 299 source cases consumed");
}
void FootballLifecycle() {
    FootballGame G;Check(G.Data.Mode==FootballGame::Phase::Title,"Football title");
    Input Start;Start.ActionPressed=true;G.Step(Start);Check(G.Data.Mode==FootballGame::Phase::Playing,"Football kickoff");
    Check(G.Data.HumanScore==0 && G.Data.CpuScore==0,"Football clean score");
    G.Data.Football={751,300,0,0};G.Step({});Check(G.Data.HumanScore==1,"Football right goal scores human");
    Near(G.Data.Football.X,400,"Football ball reset");Near(G.Data.Human.X,200,"Football human reset");Near(G.Data.Cpu.X,600,"Football CPU reset");
    G.Step({});Check(G.Data.HumanScore==1,"Football goal once");
    G.Data.Football={49,300,0,0};G.Step({});Check(G.Data.CpuScore==1,"Football left goal scores CPU");
    for(double Boundary:{220.0,380.0}) { G.Data.Football={751,Boundary,0,0};G.Step({});Check(G.Data.HumanScore==1,"Football goal y strict boundary"); }
    G.Data.Seconds=1.0/60.0;G.Data.HumanScore=2;G.Step({});
    Check(G.GetStatus().Over && G.GetStatus().Won,"Football timer win");
    for(int N=0;N<60;++N) { G.Step({}); }
    Check(G.Data.HumanScore==2,"Football result frozen");
    G.Step(Start);Check(!G.GetStatus().Over && G.Data.HumanScore==0 && G.Data.CpuScore==0,"Football restart cleared scores");
    G.Data.Seconds=0.001;G.Step({});Check(G.Data.Mode==FootballGame::Phase::Draw,"Football timer draw");
    G.Step(Start);G.Data.CpuScore=1;G.Data.Seconds=0.001;G.Step({});Check(G.Data.Mode==FootballGame::Phase::Lost,"Football timer loss");
    G.Reset(123);Check(G.Data.Mode==FootballGame::Phase::Title && G.Data.Seconds==90,"Football reset lifecycle");
    FootballGame::Ball B{220,300,1,2};FootballGame::Player P;
    Check(!FootballGame::Deflect(P,B),"Football deflection strict radius");B.X=219.99;
    Check(FootballGame::Deflect(P,B),"Football deflection inside radius");Near(B.Vx,6,"Football deflection speed");
    Input Malformed;Malformed.AxisX=std::numeric_limits<double>::infinity();Malformed.AxisY=std::numeric_limits<double>::quiet_NaN();
    FootballGame::MovePlayer(P,Malformed,B);Check(std::isfinite(P.X) && std::isfinite(P.Y),"Football nonfinite input bounded");
}
void StartDodge(DodgeBallGame& G) { Input I;I.ActionPressed=true;G.Step(I);G.Step(I); }
void DodgeLifecycle() {
    DodgeBallGame G;Check(G.Data.Mode==DodgeBallGame::Phase::Title,"Dodge title");
    Input Confirm;Confirm.ActionPressed=true;G.Step(Confirm);
    Input Up;Up.Up=true;G.Step(Up);Check(G.Data.SelectedCountry==7,"Dodge wraps country up");
    G.Step(Up);Check(G.Data.SelectedCountry==7,"Dodge selection edge triggers");
    G.Step({});Input Down;Down.Down=true;G.Step(Down);Check(G.Data.SelectedCountry==0,"Dodge wraps country down");
    G.Step({});Input PadUp;PadUp.PadUp=true;G.Step(PadUp);Check(G.Data.SelectedCountry==7,"Dodge D-pad selection up");
    G.Step({});Input PadDown;PadDown.PadDown=true;G.Step(PadDown);Check(G.Data.SelectedCountry==0,"Dodge D-pad selection down");
    G.Step(Confirm);Check(G.Data.Mode==DodgeBallGame::Phase::Playing,"Dodge starts selected roster");
    Check(G.Data.OpponentCountry!=G.Data.SelectedCountry,"Dodge opponent differs");
    Check(G.Data.DodgeBall.Owner==1 && G.Data.Players[1].HasBall,"Dodge front player starts possessing");
    Near(G.Data.DodgeBall.X,200,"Dodge attachment x");Near(G.Data.DodgeBall.Y,295,"Dodge attachment y");
    Input Move;Move.Right=true;const auto Before=G.Data.Players;
    G.Step(Move);
    for(int N=0;N<3;++N) { Near(G.Data.Players[N].X,Before[N].X+Before[N].Speed,"Dodge simultaneous trio input"); }
    G.Reset(730);StartDodge(G);
    G.Data.Players[0].Health=1;G.Data.Players[1].Health=G.Data.Players[2].Health=0;
    G.Data.DodgeBall={199,200,1,0,-1,true,false,White};G.Data.Players[1].HasBall=false;
    G.Step({});Check(G.Data.Mode==DodgeBallGame::Phase::Lost && G.Data.CpuScore==1,"Dodge team knockout loss");
    G.Step({});G.Step({});Check(G.Data.CpuScore==1,"Dodge knockout reward once");
    for(int Round=2;Round<=4;++Round) {
        G.Step(Confirm);Check(G.Data.Mode==DodgeBallGame::Phase::Playing && G.Data.Round==Round,"Dodge four-round continuation");
        Check(G.Data.CpuScore==Round-1,"Dodge score persists tournament");
        G.Data.Players[0].Health=1;G.Data.Players[1].Health=G.Data.Players[2].Health=0;
        G.Data.Players[1].HasBall=false;G.Data.DodgeBall={199,200,1,0,-1,true,false,White};G.Step({});
        Check(G.Data.Mode==DodgeBallGame::Phase::Lost,"Dodge next match knockout");
    }
    G.Step(Confirm);Check(G.Data.Mode==DodgeBallGame::Phase::Title && G.Data.Round==1,"Dodge fourth match returns title");
    G.Step(Confirm);G.Step(Confirm);Check(G.Data.HumanScore==0 && G.Data.CpuScore==0,"Dodge new tournament clears cumulative score");
    bool Won=false;
    for(std::uint32_t Seed=1;Seed<=32 && !Won;++Seed) {
        G.Reset(Seed);StartDodge(G);
        for(int N=3;N<6;++N) { G.Data.Players[N].Health=N==3 ? 1 : 0;G.Data.Players[N].HasBall=false; }
        G.Data.Players[1].HasBall=false;G.Data.DodgeBall={599,200,1,0,-1,true,true,White};G.Step({});
        if(G.Data.Mode==DodgeBallGame::Phase::Won) { Won=true;Check(G.Data.HumanScore==1,"Dodge team knockout win");G.Step({});Check(G.Data.HumanScore==1,"Dodge win reward once"); }
    }
    Check(Won,"Dodge knockout win exists despite probabilistic CPU catch");
    auto P=DodgeBallGame::MakePlayer(0,0,false);DodgeBallGame::Ball B;P.HasBall=true;P.ThrowCooldown=5;B.Owner=0;
    Check(!DodgeBallGame::Throw(B,P,{1,0}) && B.Owner==0 && P.HasBall,"Dodge throw cooldown holds possession");
    B.InAir=true;B.Owner=-1;B.X=P.X+18;B.Y=P.Y;
    Check(!DodgeBallGame::Hit(B,P),"Dodge hit radius strict");
    Check(!DodgeBallGame::Catch(B,P,-1) && !DodgeBallGame::Pickup(B,P,6),"Dodge invalid ownership rejected");
    B={400,300,0,0,-1,false,false,White};
    P.X=360;P.Y=300;
    Check(!DodgeBallGame::Pickup(B,P,0),"Source center-strip loose ball is unreachable");
    Check(DodgeBallGame::RecoverLooseBall(B),"Dodge center-strip stall repaired");
    Near(B.X,380,"Dodge repaired left pickup edge");Check(DodgeBallGame::Pickup(B,P,0),"Dodge recovered ball reachable");
    B={416,300,0,0,-1,false,false,White};Check(DodgeBallGame::RecoverLooseBall(B),"Dodge strip right boundary repaired");
    Near(B.X,420,"Dodge repaired right pickup edge");P.X=440;Check(DodgeBallGame::Pickup(B,P,3),"Dodge right recovery reachable");
    for(double X:{383.99,416.01}) { B={X,300,0,0,-1,false,false,White};Check(!DodgeBallGame::RecoverLooseBall(B),"Dodge reachable loose ball preserved"); }
    B={400,300,1,0,-1,true,false,White};Check(!DodgeBallGame::RecoverLooseBall(B),"Dodge airborne center crossing preserved");
    G.Reset(999);Check(G.Data.Particles.empty() && G.Data.DodgeBall.Owner==-1 && G.Data.Mode==DodgeBallGame::Phase::Title,"Dodge reset clears lifecycle");
}
std::string Snapshot(const DodgeBallGame& G) {
    std::ostringstream S;S.precision(17);
    S<<static_cast<int>(G.Data.Mode)<<' '<<G.Data.Round<<' '<<G.Data.HumanScore<<' '<<G.Data.CpuScore<<' '
     <<G.Data.SelectedCountry<<' '<<G.Data.OpponentCountry<<' '<<G.Data.Particles.size()<<' ';
    const auto& B=G.Data.DodgeBall;S<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Owner<<' '<<B.InAir<<' '<<B.PowerBall<<' ';
    for(const auto& P:G.Data.Players) {
        S<<P.X<<' '<<P.Y<<' '<<P.Health<<' '<<P.Charge<<' '<<P.ThrowCooldown<<' '<<P.JumpVelocity<<' '<<P.JumpCooldown<<' '<<P.OnGround<<' '<<P.HasBall<<' ';
    }
    for(const auto& P:G.Data.Particles) { S<<P.X<<' '<<P.Y<<' '<<P.Size<<' '<<P.Life<<' '; }
    return S.str();
}
void ReplayAndBounds() {
    DodgeBallGame A,B;A.Reset(12345);B.Reset(12345);Random Inputs;Inputs.Seed(9852);
    FootballGame F;Input Start;Start.ActionPressed=true;F.Step(Start);
    for(int Tick=0;Tick<12000;++Tick) {
        Input I;I.Left=Inputs.Int(0,5)==0;I.Right=Inputs.Int(0,5)==0;I.Up=Inputs.Int(0,3)==0;I.Down=Inputs.Int(0,5)==0;
        I.AxisX=Inputs.Between(-1,1);I.AxisY=Inputs.Between(-1,1);
        I.Fire=Inputs.Int(0,3)==0;I.FirePressed=Inputs.Int(0,17)==0;I.ActionPressed=Inputs.Int(0,31)==0;
        I.Jump=Inputs.Int(0,4)==0;I.JumpPressed=I.Jump && Tick%8==0;
        A.Step(I);B.Step(I);F.Step(I);
        Check(Snapshot(A)==Snapshot(B),"Dodge deterministic replay "+std::to_string(Tick));
        Check(A.Data.Particles.size()<=DodgeBallGame::MaxParticles,"Dodge particles bounded");
        if(A.Data.Mode==DodgeBallGame::Phase::Playing) {
            for(const auto& P:A.Data.Players) {
                Check(std::isfinite(P.X) && std::isfinite(P.Y),"Dodge finite coordinates");
                Check(P.X>=(P.Cpu ? 440 : 60) && P.X<=(P.Cpu ? 740 : 360) && P.Y>=80 && P.Y<=510,"Dodge court restrictions");
                Check(P.Health>=0 && P.Health<=3 && P.Charge>=0 && P.Charge<=60,"Dodge HP/charge bounds");
            }
        }
        Check(F.Data.Human.X>=40 && F.Data.Human.X<=760 && F.Data.Human.Y>=40 && F.Data.Human.Y<=560,"Football field restriction");
        if(Tick%100==0) {
            Frame Out;A.Render(Out);Check(Out.Commands.size()<Frame::MaxCommands,"Dodge render bounded");
            for(const auto& Cmd:Out.Commands) { Check(std::isfinite(Cmd.A.X) && std::isfinite(Cmd.A.Y),"Dodge finite render"); }
            F.Render(Out);Check(Out.Commands.size()<Frame::MaxCommands,"Football render bounded");
        }
    }
    A.Reset(12345);B.Reset(12345);StartDodge(A);StartDodge(B);Check(Snapshot(A)==Snapshot(B),"Dodge reset reproduces fresh replay");
    for(int Country=0;Country<8;++Country) { A.Data.SelectedCountry=Country;A.Data.OpponentCountry=(Country+1)%8;A.StartMatch();Frame Out;A.Render(Out);Check(Out.Commands.size()>100,"Dodge country visuals present"); }
}
}
int main(int Argc,char** Argv) {
    try {
        Check(Argc==2,"usage: sports_test sports_parity.txt");Fixtures(Argv[1]);
        FootballLifecycle();DodgeLifecycle();ReplayAndBounds();
        std::cout<<"Sports: "<<Checks<<" checks passed; "<<SourceCases<<" executed-Python source cases; two portable games.\n";
        return 0;
    } catch(const std::exception& E) { std::cerr<<"FAIL: "<<E.what()<<'\n';return 1; }
}
