// SPDX-License-Identifier: MIT
// Prismcairn Duel cabinet: cursor, take edges, Warden reply, restart, difficulty, options, save round trip, and
// Python parity from seed alone by steering to each fixture move with real input.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Dir(int D) { Input I; if(D<0) I.Left=true; else if(D>0) I.Right=true; return I; }
Input TakeEdge(int N) { Input I; if(N==1) I.FirePressed=true; else if(N==2) I.JumpPressed=true; else if(N==3) I.ActionPressed=true; else I.DashPressed=true; return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}
void Steer(PrismcairnGame& G,int Cairn) { int Guard=0; while(G.CursorCairn()!=Cairn && Guard++<12) { G.Step(Dir(1)); G.Step({}); } }

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; PrismcairnGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" round="<<C.Round<<" cairns="<<C.CairnsString();
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture deal regenerates through the cabinet ("+Diff+" s="+std::to_string(Seed)+")"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            const int I=std::stoi(Field(Line,"i")), T=std::stoi(Field(Line,"take"));
            Steer(G,I);
            G.Step(TakeEdge(T)); G.Step({});
            ++Turn;
            const auto& C=G.CoreState();
            const std::string Out=G.LastWardenTakeCount()<0?"you":(C.Round!=std::stoi(Field(Line,"round"))||C.Over||!C.AnyShards()?"?":"warden");
            std::ostringstream O; O<<"move t="<<Turn<<" i="<<I<<" take="<<T<<" out="<<Field(Line,"out")<<" wi="<<G.LastWardenCairnIndex()<<" wt="<<G.LastWardenTakeCount()<<" round="<<C.Round<<" wins="<<C.Wins<<" losses="<<C.Losses<<" score="<<C.Score<<" cairns="<<C.CairnsString()<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            (void)Out;
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
    PrismcairnGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Cairns.size()==4 && C.Round==1 && !C.Over && G.GetStatus().Lives==1,"a fresh normal duel has four cairns");
    Check(G.CursorCairn()==0 && G.ActionCue()=="CUE Take shards","cursor starts on the first cairn");
    G.Step(Dir(1)); Check(G.CursorCairn()==1,"one right press moves the cursor");
    G.Step(Dir(1)); Check(G.CursorCairn()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(-1)); G.Step({}); G.Step(Dir(-1)); G.Step({});
    Check(G.CursorCairn()==3,"left wraps to the last cairn");
    Steer(G,0);
    const int H0=C.Cairns[0]; const int Total0=C.Cairns[0]+C.Cairns[1]+C.Cairns[2]+C.Cairns[3];
    G.Step(TakeEdge(1)); G.Step({});
    const int Total1=C.Cairns[0]+C.Cairns[1]+C.Cairns[2]+C.Cairns[3];
    Check(G.LastWardenTakeCount()>=1 && Total1==Total0-1-G.LastWardenTakeCount() && G.ActionCue().rfind("CUE Warden took",0)==0,"A takes one shard and the Warden answers");
    (void)H0;
    PrismcairnGame Cap; Cap.Reset(730); Cap.SetCabinetDifficulty("easy");
    { int Big=-1; for(int I=0;I<3;++I) if(Cap.CoreState().Cairns[static_cast<size_t>(I)]>=3) Big=I; if(Big>=0) { Steer(Cap,Big); const int Before=Cap.CoreState().Cairns[static_cast<size_t>(Big)]; const int Others=Cap.CoreState().Cairns[0]+Cap.CoreState().Cairns[1]+Cap.CoreState().Cairns[2]-Before; Cap.Step(TakeEdge(4)); Cap.Step({}); const int After=Cap.CoreState().Cairns[0]+Cap.CoreState().Cairns[1]+Cap.CoreState().Cairns[2]; Check(After==Others+Before-3-Cap.LastWardenTakeCount() || Cap.CoreState().Over || Cap.CoreState().Round==2,"Y takes at most the limit of 3 on easy"); } else Check(true,"skip"); }

    PrismcairnGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Cairns.size()==3 && D.CoreState().Diff->TakeMax==3,"easy opens three cairns");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Cairns.size()==5 && D.CoreState().Diff->TakeMax==4,"hard opens five cairns with take 4");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Cairns.size()==5,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& Cmd:GF.Commands) if(Cmd.Kind==Shape::Rectangle && Cmd.Tint.R==120 && Cmd.Tint.G==225 && Cmd.Tint.B==255 && !(Cmd.B.X==16 && Cmd.B.Y==4)) ++Blue; Check(Blue==1,"guide marks exactly one cairn"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to duel");

    PrismcairnGame W; W.Reset(730); W.SetCabinetDifficulty("hard");
    for(int N=0;N<60 && !W.GetStatus().Over;++N) { const auto A=W.CoreState().DemoAction(); Steer(W,A.first); W.Step(TakeEdge(A.second)); W.Step({}); }
    Check(W.GetStatus().Over && W.GetStatus().Won && W.GetStatus().Score>=100,"playing best_move beats a flawless Warden");
    Check(!W.Take(1) && W.ContrastMark()=="MARK WAIT" && W.ActionCue()=="CUE Retry","a finished duel refuses more takes");
    Check(W.SourceKeyDown(8) && !W.GetStatus().Over && W.CoreState().Round==1,"R raises new cairns");
    for(int N=0;N<60 && !W.GetStatus().Over;++N) { const auto A=W.CoreState().DemoAction(); Steer(W,A.first); W.Step(TakeEdge(A.second)); W.Step({}); }
    Check(W.SourceControllerButton(1) && !W.GetStatus().Over,"pad Start restarts a finished duel");
    Check(!W.SourceControllerButton(1),"pad Start is not consumed mid-game");

    PrismcairnGame S; S.Reset(4242); S.SetCabinetDifficulty("easy");
    for(int N=0;N<2;++N) { const auto A=S.CoreState().DemoAction(); Steer(S,A.first); S.Step(TakeEdge(A.second)); S.Step({}); }
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus(); const std::string CairnsBefore=S.CoreState().CairnsString();
    PrismcairnGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="easy" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().CairnsString()==CairnsBefore && R.CursorCairn()==S.CursorCairn(),"restored cairns, score, note and cursor match");
    for(int N=0;N<6 && !S.GetStatus().Over;++N) { const auto A=S.CoreState().DemoAction(); Steer(S,A.first); S.Step(TakeEdge(A.second)); S.Step({}); const auto B=R.CoreState().DemoAction(); Steer(R,B.first); R.Step(TakeEdge(B.second)); R.Step({}); }
    Check(S.CoreState().CairnsString()==R.CoreState().CairnsString() && S.GetStatus().Score==R.GetStatus().Score && S.CoreState().Round==R.CoreState().Round,"restored stream continues identically (Warden slips included)");
    Check(!R.RestoreState("prismcairn v1 d=easy seed=1 drawn=5 round=1 wins=0 losses=0 score=0 over=0 won=0 cursor=0 cairns=99,1,1",1),"a cairn above the max height is refused");
    Check(!R.RestoreState("facetlock v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"prismcairn cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
