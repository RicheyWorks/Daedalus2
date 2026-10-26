// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopBeaconSweepCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Good,const char* What) {++Checks;if(!Good){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
std::vector<std::string> Fields(const BeaconSweepGame& G) {
    std::istringstream In(G.SaveState());std::vector<std::string> Out;std::string Token;
    while(In>>Token) Out.push_back(Token);
    return Out;
}
bool NoteHas(const BeaconSweepGame& G,const std::string& Text) {return G.GetStatus().Note.find(Text)!=std::string::npos;}
bool FrameHas(const BeaconSweepGame& G,const std::string& Text) {
    Frame F;G.Render(F);
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && C.Label.find(Text)!=std::string::npos) return true;
    return false;
}
void Move(BeaconSweepGame& G,int X,int Y) {
    const auto Before=Fields(G);const int StartX=std::stoi(Before[3]),StartY=std::stoi(Before[4]);
    for(int N=0;N<std::abs(X-StartX);++N) {
        Input I;I.Left=X<StartX;I.Right=X>StartX;G.Step(I);G.Step({});
    }
    for(int N=0;N<std::abs(Y-StartY);++N) {
        Input I;I.Up=Y<StartY;I.Down=Y>StartY;G.Step(I);G.Step({});
    }
}
void Reveal(BeaconSweepGame& G) {Input I;I.FirePressed=true;G.Step(I);}
void Flag(BeaconSweepGame& G) {Input I;I.ActionPressed=true;G.Step(I);}
void Chord(BeaconSweepGame& G) {Input I;I.DashPressed=true;G.Step(I);}
int Bits(const std::string& Layout,int I) {return Layout[static_cast<std::size_t>(I)]-'0';}
std::vector<int> Neighbours(int I) {
    std::vector<int> Out;
    for(int Dy=-1;Dy<=1;++Dy) for(int Dx=-1;Dx<=1;++Dx) {
        const int X=I%9+Dx,Y=I/9+Dy;
        if((Dx||Dy) && X>=0 && X<9 && Y>=0 && Y<9) Out.push_back(Y*9+X);
    }
    return Out;
}
int MineCount(const std::string& Layout,int I) {
    int Count=0;for(int N:Neighbours(I)) if(Bits(Layout,N)&1) ++Count;return Count;
}
// Inspect the saved layout only to choose a test route. Every reveal/flag/chord uses Step.
int ChordTarget(const std::string& Layout) {
    for(int I=0;I<81;++I) {
        if((Bits(Layout,I)&1) || MineCount(Layout,I)==0) continue;
        for(int N:Neighbours(I)) if((Bits(Layout,N)&3)==0) return I;
    }
    return -1;
}
void BlockedStepPreserves(const BeaconSweepGame& Before,const Input& Attempt,const char* What) {
    auto Tried=Before,Idle=Before;Tried.Step(Attempt);Idle.Step({});
    Check(Tried.SaveState()==Idle.SaveState(),What);
}
}

int main() {
    BeaconSweepGame G;G.Reset(730);
    const std::string Fresh=G.SaveState();
    Check(NoteHas(G,"Row 1, column 1: covered."),"selected covered cell has readable coordinates");
    Check(NoteHas(G,"First reveal and its neighbours are mine-free"),"first-opening protection is explained before play");
    Check(FrameHas(G,"First reveal and its neighbours are mine-free"),"first-opening cue is in the playable frame");
    Check(G.SaveState()==Fresh,"reading status and drawing do not change DGM1 bytes");
    Flag(G);const std::string Flagged=G.SaveState();
    Check(NoteHas(G,"Row 1, column 1: flagged.") && NoteHas(G,"Unflag before revealing"),"flag marker has a clear reveal recovery action");
    Input Fire;Fire.FirePressed=true;
    BlockedStepPreserves(G,Fire,"flagged reveal keeps board seed cursor timer and flags exactly like idle");
    Reveal(G);
    Check(G.SaveState()==Flagged && Fields(G)[6]=="0","flagged first reveal does not plant mines or start the clock");
    Check(FrameHas(G,"Unflag before revealing"),"refused flagged reveal has visible guidance");
    Move(G,1,0);
    Check(NoteHas(G,"Row 1, column 2: covered.") && !NoteHas(G,"Unflag before revealing"),"moving away removes obsolete flagged-cell advice");
    Check(G.RestoreState(Flagged,99) && NoteHas(G,"flagged."),"restored flag derives matching guidance without a new save field");
    const std::string BeforeBadRestore=G.GetStatus().Note;
    Check(!G.RestoreState("invalid",99) && G.GetStatus().Note==BeforeBadRestore && G.SaveState()==Flagged,"failed restore preserves current guidance and saved board");
    Check(G.RestoreState(Fresh,99) && NoteHas(G,"First reveal") && !NoteHas(G,"Unflag before revealing"),"successful restore does not retain obsolete guidance");
    Flag(G);G.Reset(730);
    Check(G.SaveState()==Fresh && NoteHas(G,"covered.") && !NoteHas(G,"Unflag before revealing"),"reset derives the fresh opening cue and retains the save format");

    Reveal(G);
    Check(Fields(G)[6]=="1" && !G.GetStatus().Over,"real first reveal plants a playable board");
    const int Target=ChordTarget(Fields(G)[9]);
    Check(Target>=0,"real board has a numbered chord target with a covered safe neighbour");
    if(Target>=0) {
        Move(G,Target%9,Target/9);
        if(!(Bits(Fields(G)[9],Target)&2)) Reveal(G);
        const std::string Layout=Fields(G)[9];const int Near=MineCount(Layout,Target);
        Check(NoteHas(G,"open "+std::to_string(Near)+". Neighbour flags 0/"+std::to_string(Near)),"open number and visible flag count are readable");
        Check(FrameHas(G,"Neighbour flags 0/"),"selected-number context appears beside the board");
        Input Mark;Mark.ActionPressed=true;
        BlockedStepPreserves(G,Mark,"flagging an open number preserves board and ordinary elapsed time");
        Flag(G);
        Check(NoteHas(G,"Open cells cannot be flagged"),"blocked open-cell flag explains why");
        Input OpenAround;OpenAround.DashPressed=true;
        BlockedStepPreserves(G,OpenAround,"mismatched chord changes neither board nor ordinary elapsed time");
        Chord(G);
        Check(NoteHas(G,"Match neighbour flags to the open number before chording"),"mismatched chord explains the required visible count");
        Check(Fields(G)[9]==Layout,"both refused actions preserve the entire actual mine/reveal/flag layout");

        auto Correct=G,Wrong=G;
        int UnflaggedMine=-1,WrongFlag=-1,SafeTargets=0;
        for(int N:Neighbours(Target)) {
            if(Bits(Layout,N)&1) {
                Move(Correct,N%9,N/9);Flag(Correct);
                if(UnflaggedMine<0) UnflaggedMine=N;
                else {Move(Wrong,N%9,N/9);Flag(Wrong);}
            } else if(!(Bits(Layout,N)&2)) {
                ++SafeTargets;if(WrongFlag<0) WrongFlag=N;
            }
        }
        Move(Correct,Target%9,Target/9);
        Check(NoteHas(Correct,"Neighbour flags "+std::to_string(Near)+"/"+std::to_string(Near)),"matching visible flags update immediately at the selected number");
        Check(NoteHas(Correct,"wrong flags can hit mines") && !NoteHas(Correct,"Match neighbour flags to the open number before chording"),"matched count permits chord without claiming flags are true");
        Chord(Correct);
        bool Opened=SafeTargets>0;
        for(int N:Neighbours(Target)) if(!(Bits(Layout,N)&1)) Opened=Opened&&((Bits(Fields(Correct)[9],N)&2)!=0);
        Check(Opened && (!Correct.GetStatus().Over || Correct.GetStatus().Won),"correctly flagged chord still reveals every unflagged safe neighbour");
        Check(UnflaggedMine>=0 && WrongFlag>=0,"wrong-flag test has one visible marker to misplace");
        if(UnflaggedMine>=0 && WrongFlag>=0) {
            Move(Wrong,WrongFlag%9,WrongFlag/9);Flag(Wrong);Move(Wrong,Target%9,Target/9);
            Check(NoteHas(Wrong,"Neighbour flags "+std::to_string(Near)+"/"+std::to_string(Near)) && NoteHas(Wrong,"wrong flags can hit mines"),"misplaced matching flags get the same visible-state advice");
            Chord(Wrong);
            Check(Wrong.GetStatus().Over && !Wrong.GetStatus().Won && (Bits(Fields(Wrong)[9],UnflaggedMine)&3)==3,"matching wrong flags retain the existing mine-hit loss rule");
            Check(NoteHas(Wrong,"Mine hit. Restart to try again"),"loss replaces active-cell chord advice with recovery guidance");
        }
    }
    std::cout<<"Beacon Sweep guidance: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
