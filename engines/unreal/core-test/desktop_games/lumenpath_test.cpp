// SPDX-License-Identifier: MIT
// Lumenpath Refraction cabinet: controls, restart, difficulty, options, save round trip, and Python parity from
// seed + difficulty alone (CPython-compatible seeding) by steering the cursor to each fixture move with real input.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Dir(int DR,int DC) { Input I; if(DC<0) I.Left=true; else if(DC>0) I.Right=true; if(DR<0) I.Up=true; else if(DR>0) I.Down=true; return I; }
Input Set() { Input I; I.FirePressed=true; return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}
void Steer(LumenpathGame& G,int R,int C) {
    int Guard=0;
    while(G.CursorRow()!=R && Guard++<16) { G.Step(Dir(1,0)); G.Step({}); }
    while(G.CursorCol()!=C && Guard++<32) { G.Step(Dir(0,1)); G.Step({}); }
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; LumenpathGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" size="<<C.Size()<<" src="<<C.SourceRow<<" moves="<<C.Moves<<" lit="<<C.Lit<<" grid="<<C.GridString();
            if(Line.rfind(O.str(),0)!=0) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture lattice regenerates through the cabinet ("+Diff+" s="+std::to_string(Seed)+")"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            const int R=std::stoi(Field(Line,"r")), Col=std::stoi(Field(Line,"c"));
            Steer(G,R,Col);
            G.Step(Set()); G.Step({});
            ++Turn;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"move t="<<Turn<<" r="<<R<<" c="<<Col<<" gained="<<G.LastGain()<<" score="<<C.Score<<" lit="<<C.Lit<<" moves="<<C.Moves<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0)<<" grid="<<C.GridString();
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
    LumenpathGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Size()==6 && C.Crystals.size()==3 && !C.Over && G.GetStatus().Lives==1,"a fresh normal lattice is 6x6 with three crystals");
    Check(G.CursorRow()==C.SourceRow && G.CursorCol()==0,"cursor starts where the beam enters");
    G.Step(Dir(0,1)); Check(G.CursorCol()==1,"one right press moves the cursor");
    G.Step(Dir(0,1)); Check(G.CursorCol()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(0,-1)); G.Step({}); G.Step(Dir(0,-1)); G.Step({});
    Check(G.CursorCol()==5,"left wraps around the lattice");
    // find a free cell and toggle it three times: . -> / -> \ -> .
    int FR=-1,FC=-1; for(int R=0;R<6&&FR<0;++R) for(int Cc=0;Cc<6;++Cc) if(C.Grid[static_cast<size_t>(R)][static_cast<size_t>(Cc)]=='.') { FR=R; FC=Cc; break; }
    { int Guard=0; while(G.CursorRow()!=FR && Guard++<12) { G.Step(Dir(1,0)); G.Step({}); } while(G.CursorCol()!=FC && Guard++<24) { G.Step(Dir(0,1)); G.Step({}); } }
    const int Moves0=C.Moves;
    G.Step(Set()); G.Step({}); Check(C.Grid[static_cast<size_t>(FR)][static_cast<size_t>(FC)]=='/' && C.Moves==Moves0-1,"confirm sets a / mirror and spends a move");
    G.Step(Set()); G.Step({}); Check(C.Grid[static_cast<size_t>(FR)][static_cast<size_t>(FC)]=='\\',"second confirm turns it to \\");
    Input Hold=Set(); G.Step(Hold); G.Step(Hold); Check(C.Grid[static_cast<size_t>(FR)][static_cast<size_t>(FC)]=='.' && C.Moves==Moves0-3,"held confirm toggles once per edge");

    LumenpathGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Size()==5 && D.CoreState().Crystals.size()==2,"easy opens a 5x5 lattice");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Size()==7 && D.CoreState().Crystals.size()==4,"hard opens a 7x7 lattice");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Size()==7,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& Cmd:GF.Commands) if(Cmd.Kind==Shape::Rectangle && Cmd.Tint.R==120 && Cmd.Tint.G==225 && Cmd.Tint.B==255) ++Blue; Check(Blue==1,"guide marks exactly one cell"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to refraction");

    LumenpathGame Lose; Lose.Reset(730); Lose.SetCabinetDifficulty("easy");
    for(int N=0;N<200 && !Lose.GetStatus().Over;++N) { Steer(Lose,0,1); Lose.Step(Set()); Lose.Step({}); if(Lose.CoreState().Grid[0][1]=='*'||Lose.CoreState().Grid[0][1]=='#') { Steer(Lose,1,1); Lose.Step(Set()); Lose.Step({}); } }
    Check(Lose.GetStatus().Over && Lose.GetStatus().Lives==0,"running out of moves ends the lattice");
    Check(!Lose.Toggle() && Lose.ContrastMark()=="MARK WAIT" && Lose.ActionCue()=="CUE Retry","a finished lattice refuses more toggles");
    Check(Lose.SourceKeyDown(8) && !Lose.GetStatus().Over,"R lays a new lattice");
    for(int N=0;N<200 && !Lose.GetStatus().Over;++N) { Steer(Lose,0,1); Lose.Step(Set()); Lose.Step({}); if(Lose.CoreState().Grid[0][1]=='*'||Lose.CoreState().Grid[0][1]=='#') { Steer(Lose,1,1); Lose.Step(Set()); Lose.Step({}); } }
    Check(Lose.SourceControllerButton(1) && !Lose.GetStatus().Over,"pad Start restarts a finished lattice");
    Check(!Lose.SourceControllerButton(1),"pad Start is not consumed mid-game");

    LumenpathGame S; S.Reset(4242); S.SetCabinetDifficulty("hard");
    { const auto Sol=S.CoreState().Solution.front(); Steer(S,Sol.R,Sol.C); S.Step(Set()); S.Step({}); }
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus(); const std::string GridBefore=S.CoreState().GridString();
    LumenpathGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="hard" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().GridString()==GridBefore && R.CursorRow()==S.CursorRow() && R.CursorCol()==S.CursorCol(),"restored lattice, score, note and cursor match");
    Check(R.CoreState().Solution.size()==S.CoreState().Solution.size() && R.CoreState().Crystals==S.CoreState().Crystals,"restored solution and crystals regenerate from the seed");
    std::string Tampered=Saved; { const size_t P=Tampered.find("grid="); Tampered[P+5]=(Tampered[P+5]=='*')?'.':'*'; }
    Check(!R.RestoreState(Tampered,1),"a save that moves a crystal is refused");
    Check(!R.RestoreState("shardring v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"lumenpath cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
