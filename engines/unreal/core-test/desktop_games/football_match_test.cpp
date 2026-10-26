// SPDX-License-Identifier: MIT
// Football match mode (Option 0): title gate, kick receipts, goals, clock
// results, pitch bounds, restart and seeded determinism. Portable, no engine.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
using Football=FootballGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Has(const std::string& Text,const std::string& Part) {return Text.find(Part)!=std::string::npos;}
Input Fire() {Input I;I.FirePressed=true;return I;}
Input Action() {Input I;I.ActionPressed=true;return I;}
Input Left() {Input I;I.Left=true;return I;}
Input PadUp() {Input I;I.PadUp=true;return I;}
Football Started() {Football G;G.Step(Fire());return G;}

void TitleWaitsForFreshPress() {
    Football G;
    for(int N=0;N<30;++N) G.Step(Input{});
    Check(G.Data.Mode==Football::Phase::Title,"title holds without a fresh press");
    Check(G.Data.Seconds==90,"title does not run the clock");
    Check(Has(G.GetStatus().Note,"90-second"),"title note explains the match");
    Check(!G.IsKickReady(),"no kick readiness on title");
    Football A;A.Step(Action());
    Check(A.Data.Mode==Football::Phase::Playing,"fresh Action also kicks off");
    auto B=Started();
    Check(B.Data.Mode==Football::Phase::Playing,"fresh Fire kicks off");
    Check(B.GetLastKickReceipt()==Football::KickReceipt::None,"kick-off press is not also a kick");
    Check(B.IsKickReady(),"kick ready right after kick-off");
}

void KickReceiptsAndCooldown() {
    auto G=Started();
    G.Step(Fire());
    Check(G.GetLastKickReceipt()==Football::KickReceipt::Accepted,"first kick accepted");
    Check(G.Data.Human.KickCooldown==11,"cooldown 12 then one movement tick");
    Check(!G.IsKickReady(),"not ready during cooldown");
    Check(Has(G.GetStatus().Note,"Kick wait"),"status shows cooldown wait");
    G.Step(Fire());
    Check(G.GetLastKickReceipt()==Football::KickReceipt::Cooldown,"kick during cooldown is a cooldown receipt");
    Check(Has(G.GetStatus().Note,"ignored: cooldown"),"status explains ignored kick");
    for(int N=0;N<20;++N) G.Step(Input{});
    Check(G.Data.Human.KickCooldown==0 && G.IsKickReady(),"cooldown expires");
    Check(G.KickReceiptFramesRemaining()==0 && G.GetLastKickReceipt()==Football::KickReceipt::None,"kick receipt clears");
}

void GoalsScoreAndReset() {
    auto G=Started();
    G.Data.Football={745,300,10,0};
    G.Step(Input{});
    Check(G.Data.HumanScore==1 && G.Data.CpuScore==0,"right goal scores for the player");
    Check(G.GetLastScorer()==Football::GoalScorer::Human,"scorer receipt is player");
    Check(G.GoalReceiptFramesRemaining()==Football::GoalReceiptFrames,"goal receipt starts full");
    Check(G.Data.Football.X==400 && G.Data.Football.Y==300 && G.Data.Football.Vx==0,"ball returns to centre");
    Check(G.Data.Human.X==200 && G.Data.Cpu.X==600,"players return to kick-off spots");
    Check(Has(G.GetStatus().Note,"YOU scored"),"status announces player goal");
    G.Data.Football={55,300,-10,0};
    G.Step(Input{});
    Check(G.Data.CpuScore==1,"left goal scores for the CPU");
    Check(G.GetLastScorer()==Football::GoalScorer::Cpu,"scorer receipt is CPU");
    auto Wide=Started();Wide.Data.Football={745,100,20,0};Wide.Step(Input{});
    Check(Wide.Data.HumanScore==0,"ball past the line outside the posts is not a goal");
    Check(Wide.Data.Football.Vx<0,"wide ball bounces off the end wall");
}

void ClockDecidesResult() {
    auto Win=Started();Win.Data.HumanScore=2;Win.Data.CpuScore=1;Win.Data.Seconds=1.0/60.0;Win.Step(Input{});
    Check(Win.Data.Mode==Football::Phase::Won && Win.GetStatus().Won && Win.GetStatus().Over,"lead at full time wins");
    Check(Win.Data.Seconds==0,"clock shows zero, never negative");
    Check(Has(Win.GetStatus().Note,"Final score 2 - 1"),"result note has the final score");
    auto Loss=Started();Loss.Data.CpuScore=1;Loss.Data.Seconds=1.0/60.0;Loss.Step(Input{});
    Check(Loss.Data.Mode==Football::Phase::Lost && !Loss.GetStatus().Won,"trailing at full time loses");
    auto Draw=Started();Draw.Data.Seconds=1.0/60.0;Draw.Step(Input{});
    Check(Draw.Data.Mode==Football::Phase::Draw && Has(Draw.GetStatus().Note,"DRAW"),"level at full time draws");
    for(int N=0;N<10;++N) Draw.Step(Input{});
    Check(Draw.Data.Mode==Football::Phase::Draw,"result holds without a fresh press");
    Draw.Step(Fire());
    Check(Draw.Data.Mode==Football::Phase::Playing && Draw.Data.HumanScore==0 && Draw.Data.CpuScore==0,"fresh press replays from 0-0");
    Check(Draw.Data.Seconds<90 && Draw.Data.Seconds>89.9,"replay restarts a full clock");
}

void PitchBoundsAndHat() {
    auto G=Started();
    for(int N=0;N<200;++N) G.Step(Left());
    Check(G.Data.Human.X==40,"player clamps at the left touchline");
    auto H=Started();const double Y0=H.Data.Human.Y;H.Step(PadUp());
    Check(H.Data.Human.Y<Y0,"d-pad hat moves the player like keys");
    auto B=Started();B.Data.Football={400,300,0,-30};
    for(int N=0;N<5;++N) B.Step(Input{});
    Check(B.Data.Football.Y>=40 && B.Data.Football.Y<=560,"ball stays on the pitch");
}

void SeededDeterminism() {
    Football A,B;
    for(int N=0;N<400;++N) {
        Input I;I.Right=(N/37)%2==0;I.Down=(N/53)%2==1;I.FirePressed=N%29==0;
        A.Step(I);B.Step(I);
    }
    Check(A.Data.Human.X==B.Data.Human.X && A.Data.Football.X==B.Data.Football.X && A.Data.Football.Vy==B.Data.Football.Vy
        && A.Data.HumanScore==B.Data.HumanScore && A.Data.Seconds==B.Data.Seconds,"same inputs give the same match");
    Check(A.GetStatus().Note==B.GetStatus().Note,"same inputs give the same status");
    Frame F;A.Render(F);
    Check(F.Width==800 && F.Height==600 && !F.Commands.empty(),"match renders a full frame");
}
}  // namespace

int main() {
    TitleWaitsForFreshPress();KickReceiptsAndCooldown();GoalsScoreAndReset();
    ClockDecidesResult();PitchBoundsAndHat();SeededDeterminism();
    std::cout<<"football match: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
