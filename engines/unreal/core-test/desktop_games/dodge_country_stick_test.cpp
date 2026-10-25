// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopSportsCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace {
using Dodge=DodgeBallGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
void Stick(Dodge& G,double X,double Y) {Input I;I.AxisX=X;I.AxisY=Y;G.Step(I);}
Dodge ButtonEntry() {Dodge G;G.Reset(730);Input I;I.FirePressed=true;G.Step(I);return G;}
bool Selected(const Dodge& G,int Country) {return G.Data.Mode==Dodge::Phase::CountrySelect&&G.Data.SelectedCountry==Country;}
void TitleEntry() {
    for(bool Horizontal:{false,true}) {
        Dodge G;G.Reset(730);Stick(G,Horizontal?.8:0,Horizontal?0:.8);
        Check(Selected(G,0),"analog title gesture opens country selection without choosing a country");
        for(int N=0;N<8;++N) Stick(G,Horizontal?.8:0,Horizontal?0:.8);
        Check(Selected(G,0),"held title-opening gesture cannot repeat a selection");
        Stick(G,0,-.8);Check(Selected(G,0),"changing title tilt direction without centering remains consumed");
        Stick(G,.31,0);Stick(G,0,.8);Check(Selected(G,0),"horizontal title entry requires both axes centered before a choice");
        Stick(G,.3,-.3);Stick(G,0,.8);Check(Selected(G,1),"inclusive centered sample arms one subsequent vertical flick");
    }
    auto G=ButtonEntry();Check(Selected(G,0),"fresh button entry returns before country confirmation");
    Stick(G,0,.8);Check(Selected(G,1),"centered button entry already counts as the neutral sample");
    G.Reset(730);Input Opening;Opening.FirePressed=true;Opening.Up=true;G.Step(Opening);
    Check(Selected(G,0),"keyboard Up held while opening does not also select");
    Opening.FirePressed=false;G.Step(Opening);Check(Selected(G,0),"opening keyboard direction retains existing held-edge behavior");
    G.Step({});G.Step(Opening);Check(Selected(G,7),"fresh keyboard Up still selects after release");
}
void HysteresisAndWrap() {
    auto G=ButtonEntry();Stick(G,0,.6);Check(Selected(G,0),"exact engage boundary does not choose a country");
    Stick(G,0,.600001);Check(Selected(G,1),"first tilt strictly beyond engage boundary selects down once");
    for(int N=0;N<8;++N) Stick(G,0,.9);Check(Selected(G,1),"holding the stick never autorepeats");
    Stick(G,0,-.9);Check(Selected(G,1),"opposite tilt without neutral does not choose another country");
    for(double Y:{.4,.300001,-.300001,-.6,-.9}) Stick(G,0,Y);
    Check(Selected(G,1),"jitter outside release threshold neither rearms nor repeats");
    Stick(G,.300001,0);Stick(G,0,-.9);Check(Selected(G,1),"vertical neutral alone cannot rearm while the horizontal axis is outside release");
    Stick(G,-.3,.3);Stick(G,0,-.600001);Check(Selected(G,0),"both exact release boundaries rearm an up flick");
    Stick(G,0,0);Stick(G,0,-.8);Check(Selected(G,7),"up wraps from the first country to the last");
    Stick(G,0,0);Stick(G,0,.8);Check(Selected(G,0),"down wraps from the last country to the first");
    Stick(G,0,0);Stick(G,0,-.6);Check(Selected(G,0),"negative exact engage boundary remains neutral for selection");
}
void DigitalPriority() {
    for(bool Hat:{false,true}) {
        auto G=ButtonEntry();Input I;I.AxisY=.8;I.Up=!Hat;I.PadUp=Hat;G.Step(I);
        Check(Selected(G,7),"fresh keyboard or hat Up wins over simultaneous downward stick flick");
        I.Up=I.PadUp=false;G.Step(I);Check(Selected(G,7),"losing stick flick was consumed rather than delayed until digital release");
        Stick(G,0,-.8);Check(Selected(G,7),"consumed simultaneous tilt still requires a centered sample");
        Stick(G,0,0);I={};I.AxisY=-.8;I.Down=!Hat;I.PadDown=Hat;G.Step(I);
        Check(Selected(G,0),"fresh keyboard or hat Down wins over simultaneous upward stick flick");
        I.Down=I.PadDown=false;G.Step(I);Check(Selected(G,0),"upward losing flick also cannot create a delayed selection");
    }
    auto G=ButtonEntry();Input Both;Both.Up=true;Both.PadDown=true;Both.AxisY=.8;G.Step(Both);
    Check(Selected(G,7),"existing Up-before-Down priority is retained for opposing digital edges");
    Stick(G,0,.8);Check(Selected(G,7),"opposing digital edges still consume the simultaneous analog gesture");
}
void ResetAndConfirmation() {
    auto G=ButtonEntry();Stick(G,0,.8);G.Reset(730);
    Check(G.Data.Mode==Dodge::Phase::Title&&G.Data.SelectedCountry==0,"Reset restores title and initial country");
    Stick(G,0,-.8);Stick(G,0,.8);Check(Selected(G,0),"new analog title entry requires a fresh center after Reset");
    Stick(G,0,0);Stick(G,0,.8);Check(Selected(G,1),"selection works normally after Reset and rearming");
    Frame F;G.Render(F);
    Check(G.GetStatus().Note.find("stick")!=std::string::npos&&std::any_of(F.Commands.begin(),F.Commands.end(),[](const DrawCommand& C){
        return C.Kind==Shape::Text&&C.Label.find("stick")!=std::string::npos;}),"selection status and rendered controls teach stick selection");
    Input Confirm;Confirm.FirePressed=true;G.Step(Confirm);
    Check(G.Data.Mode==Dodge::Phase::Playing&&G.Data.SelectedCountry==1&&G.Data.OpponentCountry!=1,"confirmation starts the chosen country against an eligible opponent");
    Check(G.Data.HumanScore==0&&G.Data.CpuScore==0&&G.Data.Round==1,"country confirmation retains fresh four-round tournament accounting");
    bool HumanCountry=true;for(int N=0;N<3;++N) HumanCountry=HumanCountry&&G.Data.Players[static_cast<std::size_t>(N)].CountryIndex==1;
    Check(HumanCountry&&G.Data.DodgeBall.Owner==1&&G.Data.Players[1].HasBall,"confirmed roster and original human ball possession remain intact");
    const auto Before=G.Data.Players[1];auto Analog=G,HatOnly=G,Mixed=G,Boundary=G;
    Input UpStick;UpStick.AxisY=-.7;Analog.Step(UpStick);
    Check(Analog.Data.Players[1].Charge==2&&Analog.Data.Players[1].Y<Before.Y,"live original stick Up still moves and charges");
    Input UpHat;UpHat.PadUp=true;HatOnly.Step(UpHat);
    Check(HatOnly.Data.Players[1].Charge==0&&HatOnly.Data.Players[1].Y<Before.Y,"live hat-only Up still moves without charging");
    UpStick.PadRight=true;Mixed.Step(UpStick);
    Check(Mixed.Data.Players[1].Charge==2&&Mixed.Data.Players[1].X>Before.X&&Mixed.Data.Players[1].Y==Before.Y,"live hat movement wins while original stick Up independently charges");
    Input Exact;Exact.AxisY=-.5;Boundary.Step(Exact);
    Check(Boundary.Data.Players[1].Charge==0&&Boundary.Data.Players[1].Y<Before.Y,"existing strict live charge threshold remains separate from menu thresholds");
}
}
int main() {
    TitleEntry();HysteresisAndWrap();DigitalPriority();ResetAndConfirmation();
    std::cout<<"Dodge country stick: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
