// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <array>
#include <iostream>
#include <limits>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input KeyboardEquivalent(Input I) {
    I.Left=I.Left||I.PadLeft;I.Right=I.Right||I.PadRight;I.Up=I.Up||I.PadUp;I.Down=I.Down||I.PadDown;
    I.PadLeft=I.PadRight=I.PadUp=I.PadDown=false;
    return I;
}
bool SamePlayer(const PacmanGame::Player& A,const PacmanGame::Player& B) {
    return A.X==B.X && A.Y==B.Y && A.Dir.X==B.Dir.X && A.Dir.Y==B.Dir.Y
        && A.Next.X==B.Next.X && A.Next.Y==B.Next.Y && A.Mouth==B.Mouth;
}
bool SameFrame(const Frame& F,const Frame& G) {
    if(F.Width!=G.Width || F.Height!=G.Height || F.Commands.size()!=G.Commands.size()) return false;
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];const auto& D=G.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
bool SameStatus(const Status& A,const Status& B) {
    return A.Score==B.Score && A.Lives==B.Lives && A.Over==B.Over && A.Won==B.Won && A.Note==B.Note;
}
Input Route(int Step) {
    Input I;
    if(Step<20) I.PadRight=true;
    else if(Step<36) I.PadUp=true;
    else if(Step<52) I.PadLeft=true;
    else if(Step<68) I.PadDown=true;
    else if(Step<76) {I.PadLeft=true;I.PadRight=true;}
    else if(Step<84) {I.PadUp=true;I.PadDown=true;}
    else if(Step<92) {I.PadLeft=true;I.AxisX=.8;I.AxisY=-.5;}
    // The final neutral frames preserve the current queued direction as before.
    return I;
}
}

int main() {
    const std::array<Vec,6> Axes{{{0,0},{.2,-.3},{.8,.1},{-.2,.9},{.8,-.8},
        {std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}}};
    // Every hat combination, with and without opposing keyboard keys, uses the
    // already-established keyboard path as its source-rule oracle.
    for(int Mask=0;Mask<16;++Mask) for(bool Mixed:{false,true}) for(const auto AxisValue:Axes) {
        Input I;I.PadLeft=(Mask&1)!=0;I.PadRight=(Mask&2)!=0;I.PadUp=(Mask&4)!=0;I.PadDown=(Mask&8)!=0;
        I.Left=Mixed;I.Up=Mixed;I.AxisX=AxisValue.X;I.AxisY=AxisValue.Y;
        PacmanGame::Player Pad,Keyboard;Pad.Dir={1,0};Pad.Next={1,0};Keyboard=Pad;
        Pad.Update(I);Keyboard.Update(KeyboardEquivalent(I));
        Check(SamePlayer(Pad,Keyboard),"direct Pad and equivalent keyboard preserve turn queue, movement and animation");
    }
    PacmanGame::Player P;
    Input I;I.PadLeft=true;P.Update(I);Check(P.Next.X==-1 && P.Next.Y==0,"Pad left queues a left turn");
    P={};I={};I.PadRight=true;P.Update(I);Check(P.Next.X==1 && P.Next.Y==0,"Pad right queues a right turn");
    P={};I={};I.PadUp=true;P.Update(I);Check(P.Next.X==0 && P.Next.Y==-1,"Pad up queues an up turn even if obstructed");
    P={};I={};I.PadDown=true;P.Update(I);Check(P.Next.X==0 && P.Next.Y==1,"Pad down queues a down turn even if obstructed");
    P={};I={};I.PadLeft=I.PadRight=true;P.Update(I);Check(P.Next.X==1 && P.Next.Y==0,"opposing horizontal hats retain right-last precedence");
    P={};I={};I.PadUp=I.PadDown=true;P.Update(I);Check(P.Next.X==0 && P.Next.Y==1,"opposing vertical hats retain down-last precedence");
    P={};I={};I.Right=true;I.PadLeft=true;P.Update(I);Check(P.Next.X==1,"keyboard right retains precedence over Pad left");
    P={};I={};I.Up=true;I.PadDown=true;P.Update(I);Check(P.Next.Y==1,"Pad down retains precedence over keyboard up");
    P={};I={};I.PadLeft=true;I.AxisX=.6;I.AxisY=.9;P.Update(I);Check(P.Next.X==0 && P.Next.Y==1,"dominant analog axis still overrides hat");
    P={};I={};I.PadDown=true;I.AxisX=.8;I.AxisY=-.8;P.Update(I);Check(P.Next.X==0 && P.Next.Y==-1,"analog magnitude tie retains vertical precedence");
    P={};I={};I.PadLeft=true;I.AxisY=.3;P.Update(I);Check(P.Next.X==-1 && P.Next.Y==0,"analog threshold itself does not override hat");
    P={};I={};I.PadLeft=true;I.AxisY=.300001;P.Update(I);Check(P.Next.X==0 && P.Next.Y==1,"analog immediately above threshold still overrides hat");
    P={};P.Next={-1,0};I={};P.Update(I);Check(P.Next.X==-1 && P.Next.Y==0,"neutral hats retain queued turn");

    PacmanGame PadGame,KeyGame;PadGame.Reset(730);KeyGame.Reset(730);
    Driver PadDriver,KeyDriver;
    Check(PadDriver.Select("pacman",730) && KeyDriver.Select("pacman",730),"both drivers select existing game");
    for(int Step=0;Step<96;++Step) {
        const Input Pad=Route(Step),Keys=KeyboardEquivalent(Pad);
        PadGame.Step(Pad);KeyGame.Step(Keys);
        Frame A,B;PadGame.Render(A);KeyGame.Render(B);
        Check(SamePlayer(PadGame.GetPlayer(),KeyGame.GetPlayer()) && SameStatus(PadGame.GetStatus(),KeyGame.GetStatus())
            && SameFrame(A,B),"bounded whole-game hat route matches keyboard, pellets and ghosts");
        PadDriver.SetInput(Pad);KeyDriver.SetInput(Keys);
        PadDriver.Advance(Driver::StepSeconds);KeyDriver.Advance(Driver::StepSeconds);
        Check(SameStatus(PadDriver.GetStatus(),KeyDriver.GetStatus()) && SameFrame(PadDriver.GetFrame(),KeyDriver.GetFrame()),
            "Driver Pad API matches equivalent keyboard route");
    }
    std::cout<<"Pacman direct Pad input: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
