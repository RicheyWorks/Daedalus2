// SPDX-License-Identifier: MIT
// Facetlock Lattice cabinet: cursor, four slide edges, restart, difficulty, options, save round trip, and Python parity
// from seed alone by steering the cursor to each fixture move with real input.
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
Input Edge(bool Row,int D) { Input I; if(Row) { if(D>0) I.FirePressed=true; else I.JumpPressed=true; } else { if(D>0) I.ActionPressed=true; else I.DashPressed=true; } return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}
void Steer(FacetlockGame& G,bool Row,int Index) {
    int Guard=0;
    if(Row) while(G.CursorRow()!=Index && Guard++<12) { G.Step(Dir(1,0)); G.Step({}); }
    else while(G.CursorCol()!=Index && Guard++<12) { G.Step(Dir(0,1)); G.Step({}); }
}

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; FacetlockGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" size="<<C.Size()<<" moves="<<C.Moves<<" board="<<C.BoardString()<<" solution="<<C.SolutionString();
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture scramble regenerates through the cabinet ("+Diff+" s="+std::to_string(Seed)+")"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            const bool Row=Field(Line,"kind")=="r"; const int I=std::stoi(Field(Line,"i")); const int D=std::stoi(Field(Line,"d"));
            Steer(G,Row,I);
            G.Step(Edge(Row,D)); G.Step({});
            ++Turn;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"move t="<<Turn<<" kind="<<(Row?'r':'c')<<" i="<<I<<" d="<<D<<" gained="<<G.LastGain()<<" score="<<C.Score<<" moves="<<C.Moves<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0)<<" board="<<C.BoardString()<<" solution="<<C.SolutionString();
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
    FacetlockGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Size()==4 && C.Moves==9 && !C.Solved() && !C.Over && G.GetStatus().Lives==1,"a fresh normal lattice is 4x4, scrambled, with nine moves");
    Check(G.CursorRow()==0 && G.CursorCol()==0,"cursor starts top-left");
    G.Step(Dir(0,1)); Check(G.CursorCol()==1,"one right press moves the cursor");
    G.Step(Dir(0,1)); Check(G.CursorCol()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(-1,0)); G.Step({}); Check(G.CursorRow()==3,"up wraps to the bottom row");
    const std::string Row3=C.Board[3];
    G.Step(Edge(true,1)); G.Step({});
    Check(C.Board[3]!=Row3 && C.Moves==8 && C.Board[3][1]==Row3[0],"A slides the cursor row right and spends a move");
    G.Step(Edge(true,-1)); G.Step({});
    Check(C.Board[3]==Row3 && C.Moves==7,"B slides it back left");
    const std::string Col1=std::string()+C.Board[0][1]+C.Board[1][1]+C.Board[2][1]+C.Board[3][1];
    G.Step(Edge(false,1)); G.Step({});
    Check(C.Board[1][1]==Col1[0] && C.Moves==6,"X slides the cursor column down");
    G.Step(Edge(false,-1)); G.Step({});
    Check(C.Board[0][1]==Col1[0] && C.Moves==5,"Y slides it back up");
    Check(G.SourceControllerButton(0) && C.Moves==4,"pad A slides the row");

    FacetlockGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Size()==3 && D.CoreState().Moves==7,"easy opens a 3x3 lattice with seven moves");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Size()==5 && D.CoreState().Moves==10,"hard opens a 5x5 lattice with ten moves");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Size()==5,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& Cmd:GF.Commands) if(Cmd.Kind==Shape::Rectangle && Cmd.Tint.R==120 && Cmd.Tint.G==225 && Cmd.Tint.B==255 && !(Cmd.B.X==16 && Cmd.B.Y==4)) ++Blue; Check(Blue==1,"guide marks exactly one row or column"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to lattice");

    FacetlockGame W; W.Reset(730); W.SetCabinetDifficulty("easy");
    for(int N=0;N<20 && !W.GetStatus().Over;++N) { const auto M=W.CoreState().DemoAction(); Steer(W,M.Row,M.Index); W.Step(Edge(M.Row,M.Dir)); W.Step({}); }
    Check(W.GetStatus().Over && W.GetStatus().Won && W.GetStatus().Score>=100,"following the solution opens the lock");
    FacetlockGame L; L.Reset(730);
    for(int N=0;N<40 && !L.GetStatus().Over;++N) { L.Step(Edge(true,1)); L.Step({}); }
    Check(L.GetStatus().Over && !L.GetStatus().Won && L.GetStatus().Lives==0,"burning the budget seals the lock");
    Check(!L.Slide(true,1) && L.ContrastMark()=="MARK WAIT" && L.ActionCue()=="CUE Retry","a sealed lock refuses slides");
    Check(L.SourceKeyDown(8) && !L.GetStatus().Over && L.CoreState().Moves==9,"R scrambles a new lattice");
    for(int N=0;N<40 && !L.GetStatus().Over;++N) { L.Step(Edge(true,1)); L.Step({}); }
    Check(L.SourceControllerButton(1) && !L.GetStatus().Over,"pad Start restarts a sealed lock");
    Check(!L.SourceControllerButton(1),"pad Start is not consumed mid-game");

    FacetlockGame S; S.Reset(4242); S.SetCabinetDifficulty("hard");
    S.Step(Edge(true,1)); S.Step({}); S.Step(Dir(1,0)); S.Step({}); S.Step(Edge(false,-1)); S.Step({});
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus(); const std::string BoardBefore=S.CoreState().BoardString();
    FacetlockGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="hard" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().BoardString()==BoardBefore && R.CoreState().SolutionString()==S.CoreState().SolutionString() && R.CursorRow()==S.CursorRow() && R.CursorCol()==S.CursorCol(),"restored board, solution, note and cursor match");
    { std::string Bad=Saved; const size_t P=Bad.find("board=")+6; Bad[P]='Q'; Check(!R.RestoreState(Bad,1),"a save with a foreign facet is refused"); }
    { std::string Bad=Saved; const size_t P=Bad.find("board=")+6; const char A=Bad[P]; const char B=Bad[P+1]; if(A!=B) { Bad[P+1]=A; Check(!R.RestoreState(Bad,1),"a save that duplicates a facet is refused"); } else Check(true,"skip"); }
    Check(!R.RestoreState("lumenpath v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"facetlock cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
