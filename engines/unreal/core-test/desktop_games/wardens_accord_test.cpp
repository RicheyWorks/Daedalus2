// SPDX-License-Identifier: MIT
// Wardens' Accord cabinet: controls, restart, difficulty, options, save round trip, and Python parity from seed alone
// by steering one cursor over altar shards and spirits with real input.
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
Input Set() { Input I; I.FirePressed=true; return I; }
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}
void Steer(WardensAccordGame& G,int Slot) { int Guard=0; while(G.CursorSlot()!=Slot && Guard++<16) { G.Step(Dir(1)); G.Step({}); } }
std::string State(const daedalus::wardens::Game& C) { return "pouch="+C.PouchString()+" offer="+C.OfferString()+" spirits="+C.SpiritsString(); }

void Parity(const char* Path) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line; WardensAccordGame G; std::uint32_t Seed=0; std::string Diff; int Turn=0; bool Skip=false; int Games=0;
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) {
            Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); Diff=Field(Line,"d"); Turn=0; Skip=false; ++Games;
            G.SetCabinetDifficulty(Diff); G.Reset(Seed);
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"game s="<<Seed<<" d="<<Diff<<" rounds="<<C.Rounds<<" target="<<C.Diff->Target<<" "<<State(C);
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture altar regenerates through the cabinet ("+Diff+" s="+std::to_string(Seed)+")"); Skip=true; }
        } else if(Line.rfind("move ",0)==0) {
            if(Skip) continue;
            const bool Summon=Field(Line,"kind")=="summon"; const int I=std::stoi(Field(Line,"i"));
            Steer(G,Summon?3+I:I);
            G.Step(Set()); G.Step({});
            ++Turn;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"move t="<<Turn<<" kind="<<(Summon?"summon":"take")<<" i="<<I<<" gained="<<G.LastGain()<<" score="<<C.Score<<" rounds="<<C.Rounds<<" "<<State(C)<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            if(O.str()!=Line) { std::cerr<<"  want "<<Line<<"\n  got  "<<O.str()<<'\n'; Check(false,"fixture move replays through the cabinet ("+Diff+" s="+std::to_string(Seed)+" t="+std::to_string(Turn)+")"); Skip=true; }
        } else if(Line.rfind("end  ",0)==0) {
            if(Skip) continue;
            const auto& C=G.CoreState();
            std::ostringstream O; O<<"end  score="<<C.Score<<" won="<<(C.Won?1:0)<<" summoned="; for(size_t K=0;K<C.Summoned.size();++K) O<<(K?",":"")<<C.Summoned[K];
            Check(O.str()==Line && C.Over,"fixture game ends identically ("+Diff+" s="+std::to_string(Seed)+")");
        }
    }
    Check(Games==30,"fixture holds 30 games");
}
}

int main(int Argc,char** Argv) {
    WardensAccordGame G; G.Reset(730);
    const auto& C=G.CoreState();
    Check(C.Spirits.size()==4 && C.Offer.size()==3 && C.Rounds==14 && !C.Over && G.GetStatus().Lives==1,"a fresh normal altar has four spirits and fourteen rounds");
    Check(G.CursorSlot()==0 && G.ActionCue()=="CUE Take shard","cursor starts on the first altar shard");
    G.Step(Dir(1)); Check(G.CursorSlot()==1,"one right press moves the cursor");
    G.Step(Dir(1)); Check(G.CursorSlot()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(-1)); G.Step({}); G.Step(Dir(-1)); G.Step({});
    Check(G.CursorSlot()==6,"left wraps to the last spirit");
    Check(G.ActionCue()=="CUE Need shards" && !G.Act() && C.Rounds==14,"an unaffordable spirit refuses to summon and spends nothing");
    Steer(G,0);
    const int Hue=C.Offer[0];
    G.Step(Set()); G.Step({});
    Check(C.Rounds==13 && C.Pouch[Hue]==1,"confirm takes the shard under the cursor and spends a round");
    Input Hold=Set(); G.Step(Hold); G.Step(Hold);
    Check(C.Rounds==12,"held confirm takes once per edge");
    Check(G.SourceControllerButton(0) && C.Rounds==11,"pad A takes a shard");

    WardensAccordGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Hues()==3 && D.CoreState().Rounds==16,"easy opens three hues and sixteen rounds");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Hues()==5 && D.CoreState().Spirits.size()==3,"hard opens five hues and three spirits");
    Check(!D.SetCabinetDifficulty("mythic") && D.CoreState().Hues()==5,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& Cmd:GF.Commands) if((Cmd.Kind==Shape::Circle||Cmd.Kind==Shape::Rectangle) && Cmd.Tint.R==120 && Cmd.Tint.G==225 && Cmd.Tint.B==255 && Cmd.Label.empty() && !(Cmd.Kind==Shape::Rectangle && Cmd.B.X==16 && Cmd.B.Y==4)) ++Blue; Check(Blue==1,"guide marks exactly one slot"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to accord");

    WardensAccordGame End; End.Reset(730); End.SetCabinetDifficulty("hard");
    for(int N=0;N<400 && !End.GetStatus().Over;++N) { const auto A=End.CoreState().DemoAction(); Steer(End,A.first?3+A.second:A.second); End.Step(Set()); End.Step({}); }
    Check(End.GetStatus().Over && End.GetStatus().Lives==0,"the demo policy finishes a hard altar");
    Check(!End.Act() && End.ContrastMark()=="MARK WAIT" && End.ActionCue()=="CUE Retry","a finished altar refuses more actions");
    Check(End.SourceKeyDown(8) && !End.GetStatus().Over && End.CoreState().Rounds==12,"R lights the altar again");
    for(int N=0;N<400 && !End.GetStatus().Over;++N) { const auto A=End.CoreState().DemoAction(); Steer(End,A.first?3+A.second:A.second); End.Step(Set()); End.Step({}); }
    Check(End.SourceControllerButton(1) && !End.GetStatus().Over,"pad Start restarts a finished altar");
    Check(!End.SourceControllerButton(1),"pad Start is not consumed mid-game");

    WardensAccordGame S; S.Reset(4242); S.SetCabinetDifficulty("hard");
    for(int N=0;N<5;++N) { const auto A=S.CoreState().DemoAction(); Steer(S,A.first?3+A.second:A.second); S.Step(Set()); S.Step({}); }
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus(); const std::string StateBefore=State(S.CoreState());
    WardensAccordGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="hard" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && State(R.CoreState())==StateBefore && R.CursorSlot()==S.CursorSlot(),"restored altar, pouch, spirits, score, note and cursor match");
    for(int N=0;N<4;++N) { const auto A=S.CoreState().DemoAction(); Steer(S,A.first?3+A.second:A.second); S.Step(Set()); S.Step({}); const auto B=R.CoreState().DemoAction(); Steer(R,B.first?3+B.second:B.second); R.Step(Set()); R.Step({}); }
    Check(State(S.CoreState())==State(R.CoreState()) && S.GetStatus().Score==R.GetStatus().Score,"restored stream continues identically");
    { std::string Bad=Saved; const size_t P=Bad.find(" spirits="); Bad=Bad.substr(0,P)+" spirits=0:0=9:99"; Check(!R.RestoreState(Bad,1),"a save with an impossible spirit is refused"); }
    Check(!R.RestoreState("lumenpath v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) Parity(Argv[1]);
    std::cout<<"wardens accord cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
