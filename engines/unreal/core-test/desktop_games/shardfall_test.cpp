// SPDX-License-Identifier: MIT
// Shardfall Gamble cabinet: draw/bank edges, collapse, restart, difficulty, options, save round trip, and Python
// parity from seed alone by pressing each fixture action with real input.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input DrawIn() { Input I; I.FirePressed=true; return I; }
Input BankIn() { Input I; I.JumpPressed=true; return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; ShardfallGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" round="<<C.Round<<" bag="<<C.BagString();
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture seam regenerates through the cabinet"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            const bool Bank=Field(Line,"act")=="bank";
            G.Step(Bank?BankIn():DrawIn()); G.Step({});
            ++Turn;
            const auto& C=G.CoreState();
            std::string R=G.LastResultText(); for(char& Ch:R) if(Ch==' ') Ch='_';
            std::ostringstream O; O<<"move t="<<Turn<<" act="<<(Bank?"bank":"draw")<<" res="<<R<<" round="<<C.Round<<" pot="<<C.Pot<<" cracks="<<C.Cracks<<" score="<<C.Score<<" bag="<<C.BagString()<<" history="<<C.HistoryString()<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture move replays through the cabinet ("+Diff+" s="+std::to_string(Seed)+" t="+std::to_string(Turn)+")"); Skip=true; }
        } else if(Line.rfind("end  ",0)==0) {
            if(Skip) continue;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"end  score="<<C.Score<<" won="<<(C.Won?1:0)<<" rounds="<<C.Round;
            Check(O.str()==Line && C.Over,"fixture game ends identically ("+Diff+" s="+std::to_string(Seed)+")");
        }
    }
    Check(Games==30,"fixture holds 30 games");
}
}

int main(int Argc,char** Argv) {
    ShardfallGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Bag.size()==15 && C.Round==1 && C.Pot==0 && !C.Over && G.GetStatus().Lives==1,"a fresh normal seam holds fifteen shards");
    Check(G.ActionCue()=="CUE Draw","a fresh seam cues a draw");
    G.Step(DrawIn()); G.Step({});
    Check(C.Bag.size()==14 && !G.LastResultText().empty(),"A draws one shard");
    { ShardfallGame H; H.Reset(730); const size_t N0=H.CoreState().Bag.size(); Input Hold=DrawIn(); H.Step(Hold); H.Step(Hold);
      const auto& HC=H.CoreState(); Check(HC.Bag.size()==N0-1 || HC.Round==2 || HC.Over,"held draw draws once per edge"); }
    { ShardfallGame Bk; Bk.Reset(730); Bk.Step(DrawIn()); Bk.Step({}); const auto& BC=Bk.CoreState();
      if(!BC.Over && BC.Round==1) { const int Pot0=BC.Pot; Bk.Step(BankIn()); Bk.Step({}); Check(BC.Score==Pot0 && BC.Round==2 && BC.Pot==0 && BC.Bag.size()==15,"B banks the pot and opens the next seam"); }
      else Check(true,"B banks the pot and opens the next seam (first draw ended the round)"); }
    { ShardfallGame Pa; Pa.Reset(730); Check(Pa.SourceControllerButton(0) && Pa.CoreState().Bag.size()==14,"pad A draws"); }

    ShardfallGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Bag.size()==14 && D.CoreState().Diff->Rounds==6,"easy opens a seam with two cracked shards and six rounds");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Bag.size()==16 && D.CoreState().Diff->Target==32,"hard opens four cracked shards and target 32");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Bag.size()==16,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Bar=0; for(const auto& Cmd:GF.Commands) if(Cmd.Kind==Shape::Rectangle && Cmd.B.X==340 && Cmd.B.Y==6) ++Bar; Check(Bar==1,"guide draws exactly one counsel bar"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to gamble");

    ShardfallGame X; X.Reset(730); X.SetCabinetDifficulty("hard");
    for(int N=0;N<200 && !X.GetStatus().Over;++N) { X.Step(DrawIn()); X.Step({}); if(X.CoreState().Bag.empty() && !X.GetStatus().Over) { X.Step(BankIn()); X.Step({}); } }
    Check(X.GetStatus().Over,"drawing every shard ends the game");
    Check(!X.DrawShard() && !X.BankPot() && X.ContrastMark()=="MARK WAIT" && X.ActionCue()=="CUE Retry","a finished seam refuses more actions");
    Check(X.SourceKeyDown(8) && !X.GetStatus().Over && X.CoreState().Round==1,"R opens a new seam");
    for(int N=0;N<200 && !X.GetStatus().Over;++N) { X.Step(DrawIn()); X.Step({}); if(X.CoreState().Bag.empty() && !X.GetStatus().Over) { X.Step(BankIn()); X.Step({}); } }
    Check(X.SourceControllerButton(1) && !X.GetStatus().Over,"pad Start restarts a finished seam");
    Check(!X.SourceControllerButton(1),"pad Start is not consumed mid-game");

    ShardfallGame S; S.Reset(4242); S.SetCabinetDifficulty("easy");
    S.Step(DrawIn()); S.Step({}); S.Step(DrawIn()); S.Step({}); S.Step(BankIn()); S.Step({}); S.Step(DrawIn()); S.Step({});
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus();
    ShardfallGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="easy" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().BagString()==S.CoreState().BagString() && R.CoreState().HistoryString()==S.CoreState().HistoryString(),"restored seam, pot, history and note match");
    for(int N=0;N<30 && !S.GetStatus().Over;++N) { const bool B=S.CoreState().DemoBank(); S.Step(B?BankIn():DrawIn()); S.Step({}); R.Step(B?BankIn():DrawIn()); R.Step({}); }
    Check(S.CoreState().BagString()==R.CoreState().BagString() && S.GetStatus().Score==R.GetStatus().Score && S.CoreState().Round==R.CoreState().Round,"restored stream reshuffles later seams identically");
    Check(!R.RestoreState("shardfall v1 d=easy seed=1 drawn=5 round=1 pot=0 cracks=0 score=0 over=0 won=0 bag=0,0,0,0 history=-",1),"a bag with too many cracked shards is refused");
    Check(!R.RestoreState("prismvault v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"shardfall cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
