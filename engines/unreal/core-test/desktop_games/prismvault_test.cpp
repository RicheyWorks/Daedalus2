// SPDX-License-Identifier: MIT
// Prismvault Weigh cabinet: pans, weigh, name, restart, difficulty, options, save round trip (log replayed, not
// trusted), and Python parity from seed alone by loading each fixture weighing with real input.
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
Input Fire() { Input I; I.FirePressed=true; return I; }
Input Clear() { Input I; I.JumpPressed=true; return I; }
Input Weigh() { Input I; I.ActionPressed=true; return I; }
Input NameIt() { Input I; I.DashPressed=true; return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}
std::vector<int> Ints(const std::string& S) { std::vector<int> V; if(S=="-"||S.empty()) return V; std::string T; for(char C:S+",") { if(C==',') { V.push_back(std::stoi(T)); T.clear(); } else T.push_back(C); } return V; }
std::string Lst(const std::vector<int>& V) { return V.empty()?"-":daedalus::prismvault::Game::ListString(V); }
void Steer(PrismvaultGame& G,int Shard) { int Guard=0; while(G.CursorShard()!=Shard && Guard++<40) { G.Step(Dir(1)); G.Step({}); } }
void LoadPan(PrismvaultGame& G,int Shard,int Which) { Steer(G,Shard); int Guard=0; while(G.PanOf(Shard)!=Which && Guard++<3) { G.Step(Fire()); G.Step({}); } }

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; PrismvaultGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" shards="<<C.Shards()<<" hollow="<<C.Hollow<<" weighings="<<C.Weighings<<" candidates="<<Lst(C.Candidates);
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture vault regenerates through the cabinet"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            ++Turn;
            const auto& C=G.CoreState();
            std::ostringstream O;
            if(Field(Line,"kind")=="weigh") {
                const std::vector<int> L=Ints(Field(Line,"left")), R=Ints(Field(Line,"right"));
                for(int X:L) LoadPan(G,X,1);
                for(int X:R) LoadPan(G,X,2);
                G.Step(Weigh()); G.Step({});
                O<<"move t="<<Turn<<" kind=weigh left="<<Lst(L)<<" right="<<Lst(R)<<" shard=-1 res="<<G.LastWeighResult()<<" gained=0 score="<<C.Score<<" weighings="<<C.Weighings<<" candidates="<<Lst(C.Candidates)<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            } else {
                const int S=std::stoi(Field(Line,"shard")); Steer(G,S); G.Step(NameIt()); G.Step({});
                O<<"move t="<<Turn<<" kind=name left=- right=- shard="<<S<<" res=- gained="<<G.LastGain()<<" score="<<C.Score<<" weighings="<<C.Weighings<<" candidates="<<Lst(C.Candidates)<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            }
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture move replays through the cabinet ("+Diff+" s="+std::to_string(Seed)+" t="+std::to_string(Turn)+")"); Skip=true; }
        } else if(Line.rfind("end  ",0)==0) {
            if(Skip) continue;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"end  score="<<C.Score<<" won="<<(C.Won?1:0);
            Check(O.str()==Line && C.Over,"fixture game ends identically ("+Diff+" s="+std::to_string(Seed)+")");
        }
    }
    Check(Games==30,"fixture holds 30 games");
}
}

int main(int Argc,char** Argv) {
    PrismvaultGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Shards()==12 && C.Weighings==3 && C.Candidates.size()==12 && !C.Over && G.GetStatus().Lives==1,"a fresh normal vault has twelve shards and three weighings");
    Check(G.CursorShard()==0 && G.ActionCue()=="CUE Load the pans","cursor starts on shard 0");
    G.Step(Dir(1)); Check(G.CursorShard()==1,"one right press moves the cursor");
    G.Step(Dir(1)); Check(G.CursorShard()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(-1)); G.Step({}); G.Step(Dir(-1)); G.Step({});
    Check(G.CursorShard()==11,"left wraps to the last shard");
    Steer(G,0); G.Step(Fire()); G.Step({}); Check(G.PanOf(0)==1,"A puts the shard on the left pan");
    G.Step(Fire()); G.Step({}); Check(G.PanOf(0)==2,"A again moves it to the right pan");
    G.Step(Fire()); G.Step({}); Check(G.PanOf(0)==0,"A again clears it");
    LoadPan(G,0,1); LoadPan(G,1,1); LoadPan(G,2,2);
    G.Step(Weigh()); G.Step({}); Check(C.Weighings==3 && G.LastWeighResult()=='?',"unequal pans refuse to weigh");
    LoadPan(G,3,2);
    G.Step(Weigh()); G.Step({}); Check(C.Weighings==2 && G.LastWeighResult()!='?' && G.PanOf(0)==0 && G.PanOf(3)==0,"equal pans weigh, log and clear");
    LoadPan(G,4,1); G.Step(Clear()); G.Step({}); Check(G.PanOf(4)==0,"B clears the pans");

    PrismvaultGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Shards()==8,"easy opens eight shards");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Shards()==27,"hard opens twenty-seven shards");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Shards()==27,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& Cmd:GF.Commands) if(Cmd.Kind==Shape::Circle && Cmd.Tint.R==120 && Cmd.Tint.G==225 && Cmd.Tint.B==255) ++Blue; Check(Blue==18,"guide marks a 9 v 9 split on hard"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to weigh");

    PrismvaultGame W; W.Reset(730); W.SetCabinetDifficulty("easy");
    for(int N=0;N<10 && !W.GetStatus().Over;++N) { const auto Dm=W.CoreState().DemoAction(); if(Dm.IsName) { Steer(W,Dm.Shard); W.Step(NameIt()); W.Step({}); } else { for(int X:Dm.Left) LoadPan(W,X,1);
        for(int X:Dm.Right) LoadPan(W,X,2);
        W.Step(Weigh()); W.Step({}); } }
    Check(W.GetStatus().Over && W.GetStatus().Won && W.GetStatus().Score>=100,"the demo policy finds the hollow shard");
    Check(!W.WeighPans() && !W.NameCursor() && W.ContrastMark()=="MARK WAIT" && W.ActionCue()=="CUE Retry","a finished vault refuses more actions");
    Check(W.SourceKeyDown(8) && !W.GetStatus().Over && W.CoreState().Weighings==3,"R seals a new vault");
    PrismvaultGame Wrong; Wrong.Reset(730); Steer(Wrong,(Wrong.CoreState().Hollow+1)%12); Wrong.Step(NameIt()); Wrong.Step({});
    Check(Wrong.GetStatus().Over && !Wrong.GetStatus().Won && Wrong.GetStatus().Lives==0,"naming the wrong shard loses");
    Check(Wrong.SourceControllerButton(1) && !Wrong.GetStatus().Over,"pad Start restarts a finished vault");
    Check(!Wrong.SourceControllerButton(1),"pad Start is not consumed mid-game");

    PrismvaultGame S; S.Reset(4242); S.SetCabinetDifficulty("hard");
    { const auto Dm=S.CoreState().DemoAction(); for(int X:Dm.Left) LoadPan(S,X,1);
      for(int X:Dm.Right) LoadPan(S,X,2);
      S.Step(Weigh()); S.Step({}); }
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus();
    PrismvaultGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="hard" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().CandidatesString()==S.CoreState().CandidatesString() && R.CoreState().Hollow==S.CoreState().Hollow && R.CoreState().Log.size()==1,"restored vault replays the log and regenerates the hollow shard");
    { std::string Bad=Saved; const size_t P=Bad.find("candidates=")+11; Bad[P]=(Bad[P]=='0')?'1':'0'; Check(!R.RestoreState(Bad,1)||R.CoreState().CandidatesString()==S.CoreState().CandidatesString(),"a save whose candidates disagree with the replayed log is refused"); }
    Check(!R.RestoreState("facetlock v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"prismvault cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
