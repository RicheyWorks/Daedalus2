// SPDX-License-Identifier: MIT
// Shardring Resonance cabinet: controls, restart, cabinet difficulty, save round trip, and Python parity
// (the fixture's recorded draws are fed through UseOracle, so the cabinet replays prism_shard.py exactly).
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Dir(int D) { Input I; if(D<0) I.Left=true; else if(D>0) I.Right=true; return I; }
Input Set() { Input I; I.FirePressed=true; return I; }
int Empty(const ShardringGame& G) { return static_cast<int>(G.CoreState().EmptyFacets().size()); }

struct FixtureOracle : daedalus::shardring::Oracle {
    std::vector<std::pair<std::string,std::string>> Events; std::size_t At=0; int Errors=0;
    daedalus::shardring::Hue Draw() override {
        if(At>=Events.size()||Events[At].first!="draw") { ++Errors; return daedalus::shardring::Hue::None; }
        return daedalus::shardring::HueFromName(Events[At++].second);
    }
    int SpiritPick(const std::vector<int>&) override {
        if(At>=Events.size()||Events[At].first!="spirit") { ++Errors; return -1; }
        return std::stoi(Events[At++].second);
    }
};
std::string Field(const std::string& Line,const std::string& Key) {
    const std::string N=" "+Key+"="; const size_t P=Line.find(N); if(P==std::string::npos) return "";
    const size_t S=P+N.size(), E=Line.find(' ',S); return Line.substr(S,E==std::string::npos?std::string::npos:E-S);
}

// Mode 0: the fixture's recorded draws drive the cabinet through UseOracle (rules parity).
// Mode 1: no oracle; the cabinet's own CPython-compatible stream, seeded from the fixture's seed and
// difficulty exactly like prism_shard.py, must reproduce the same draws, moves and end line (PRNG parity).
void Parity(const char* Path,int Mode) {
    std::ifstream In(Path);
    if(!In) { Check(false,std::string("fixture opens: ")+Path); return; }
    std::string Line, Diff; std::uint32_t Seed=0; FixtureOracle O; std::vector<std::string> Moves; std::string End; int Games=0;
    auto Run=[&]() {
        if(Diff.empty()) return;
        ShardringGame G;
        Check(G.SetCabinetDifficulty(Diff),Diff+": cabinet difficulty");
        if(Mode==0) { G.UseOracle(&O); G.Reset(730); }   // Reset deals through the fixture oracle: first two draws
        else G.Reset(Seed);
        int Turn=0; bool Ok=true;
        for(const std::string& Expected:Moves) {
            const int Facet=G.CoreState().GreedyMove();
            // steer the cursor to the greedy facet with real edge-triggered input, then set
            int Guard=0;
            while(G.CursorFacet()!=Facet && Guard++<64) { G.Step(Dir(1)); G.Step({}); }
            G.Step(Set()); G.Step({});
            ++Turn;
            std::ostringstream S; const auto& C=G.CoreState();
            S<<"move t="<<Turn<<" facet="<<Facet<<" gained="<<G.LastGain()<<" score="<<C.Score<<" chain="<<C.Chain<<" pouch="<<C.Pouch
             <<" cur="<<daedalus::shardring::HueName(C.Current)<<" next="<<daedalus::shardring::HueName(C.Next)<<" spirits="<<C.Spirits.size()
             <<" ring="<<C.RingString()<<" over="<<(C.Over?1:0)<<" won="<<(C.Won?1:0);
            if(S.str()!=Expected) { std::cerr<<"  want "<<Expected<<"\n  got  "<<S.str()<<'\n'; Ok=false; break; }
        }
        std::ostringstream E; const auto& C=G.CoreState();
        E<<"end  score="<<C.Score<<" won="<<(C.Won?1:0)<<" spirits=";
        for(std::size_t I=0;I<C.Spirits.size();++I) E<<(I?",":"")<<daedalus::shardring::SpiritName(C.Spirits[I]);
        const bool OracleDrained=Mode==1 || (O.At==O.Events.size() && O.Errors==0);
        Check(Ok && E.str()==End && OracleDrained,"fixture game "+std::to_string(Games)+" ("+Diff+" s="+std::to_string(Seed)+") replays byte-identical through the cabinet"+(Mode?" from its own CPython-compatible seed":" with injected draws"));
        ++Games; Diff.clear(); O=FixtureOracle{}; Moves.clear(); End.clear();
    };
    while(std::getline(In,Line)) {
        if(Line.empty()||Line[0]=='#') continue;
        if(Line.rfind("game ",0)==0) { Run(); Diff=Field(Line,"d"); Seed=static_cast<std::uint32_t>(std::stoul(Field(Line,"s"))); continue; }
        if(Line.rfind("rng  ",0)==0) { std::istringstream S(Line.substr(5)); std::string K,V; S>>K>>V; O.Events.emplace_back(K,V); }
        else if(Line.rfind("move ",0)==0) Moves.push_back(Line);
        else if(Line.rfind("end  ",0)==0) End=Line;
    }
    Run();
    Check(Games==30,"fixture holds 30 games");
}
}

int main(int Argc,char** Argv) {
    ShardringGame G; G.Reset(730);
    Check(G.CoreState().Facets()==10 && G.CoreState().Pouch==50 && Empty(G)==10 && !G.GetStatus().Over,"a fresh normal ring has ten empty facets and fifty shards");
    Check(G.CursorFacet()==0 && G.GetStatus().Score==0 && G.GetStatus().Lives==1,"cursor starts at facet 0");
    G.Step(Dir(1)); Check(G.CursorFacet()==1,"one right press moves to the next facet");
    G.Step(Dir(1)); Check(G.CursorFacet()==1,"held right does not move again");
    G.Step({}); G.Step(Dir(-1)); G.Step({}); G.Step(Dir(-1)); G.Step({});
    Check(G.CursorFacet()==9,"left wraps around the ring");
    G.Step(Set()); G.Step({});
    Check(G.CoreState().Pouch==49 && Empty(G)==9 && G.CoreState().Ring[9]!=daedalus::shardring::Hue::None,"confirm sets the shard in the cursor facet");
    Check(G.CursorFacet()!=9,"cursor moves off a filled facet");
    Input Hold=Set(); G.Step(Hold); G.Step(Hold);
    Check(G.CoreState().Pouch==48,"a held confirm sets once per edge and once per host edge");
    Check(G.SourceKeyDown(3)==false && G.SourceControllerButton(0) && G.CoreState().Pouch==47,"source right key and pad A set a shard");

    ShardringGame D; D.Reset(730);
    Check(D.SetCabinetDifficulty("easy") && D.CoreState().Facets()==12 && D.CoreState().Pouch==60,"easy opens twelve facets");
    Check(D.SetCabinetDifficulty("hard") && D.CoreState().Facets()==8 && D.CoreState().Pouch==40 && D.CoreState().Diff->Hues==5,"hard opens eight facets with five hues");
    Check(!D.SetCabinetDifficulty("legendary") && D.CoreState().Facets()==8,"unknown difficulty is refused");
    Check(!D.SetOption(2,730) && D.SetOption(1,730) && D.GetOption()==1 && D.HintLine().find("Practice")!=std::string::npos,"guide practice is option 1; option 2 is refused");
    { Frame GF; D.Render(GF); int Blue=0; for(const auto& C:GF.Commands) if(C.Kind==Shape::Circle && C.Tint.R==120 && C.Tint.G==225 && C.Tint.B==255) ++Blue; Check(Blue==1,"guide practice marks exactly one facet"); }
    Check(D.SetOption(0,730) && D.GetOption()==0,"option 0 returns to resonance");

    ShardringGame Lose; Lose.Reset(730);
    for(int N=0;N<400 && !Lose.GetStatus().Over;++N) { Lose.Step(Set()); Lose.Step({}); }
    Check(Lose.GetStatus().Over && Lose.GetStatus().Lives==0,"setting every shard at the cursor ends the ring");
    Check(!Lose.Place() && Lose.ContrastMark()=="MARK WAIT" && Lose.ActionCue()=="CUE Retry","a finished ring refuses more shards");
    Check(Lose.SourceKeyDown(8) && !Lose.GetStatus().Over && Lose.CoreState().Pouch==50,"R sets a new ring");
    for(int N=0;N<400 && !Lose.GetStatus().Over;++N) { Lose.Step(Set()); Lose.Step({}); }
    Check(Lose.SourceControllerButton(1) && !Lose.GetStatus().Over,"pad Start restarts a finished ring");
    Check(!Lose.SourceControllerButton(1),"pad Start is not consumed mid-game, so the host may pause");

    ShardringGame S; S.Reset(4242); S.SetCabinetDifficulty("hard");
    for(int N=0;N<7;++N) { S.Step(Dir(1)); S.Step({}); S.Step(Set()); S.Step({}); }
    const std::string Saved=S.SaveState(); const auto Before=S.GetStatus(); const std::string RingBefore=S.CoreState().RingString();
    ShardringGame R; R.Reset(1);
    Check(R.RestoreState(Saved,1) && R.CabinetDifficulty()=="hard" && R.SeedAfterRestore(1)==4242,"save text restores difficulty and seed");
    Check(R.GetStatus().Score==Before.Score && R.GetStatus().Note==Before.Note && R.CoreState().RingString()==RingBefore && R.CursorFacet()==S.CursorFacet(),"restored ring, score, note and cursor match");
    for(int N=0;N<5;++N) { S.Step(Set()); S.Step({}); R.Step(Set()); R.Step({}); }
    Check(S.CoreState().RingString()==R.CoreState().RingString() && S.GetStatus().Score==R.GetStatus().Score,"restored stream continues identically");
    Check(!R.RestoreState("shardring v1 d=normal seed=1 drawn=5 pouch=99 score=0 chain=0 cur=0 next=0 cursor=0 over=0 won=0 ring=-1, res=0,0,0,0,0, spirits=",1),"a pouch beyond the difficulty is refused");
    Check(!R.RestoreState("cairnwell v1",1) && !R.RestoreState("",1),"foreign save text is refused");

    Frame F; G.Render(F);
    Check(!F.Commands.empty() && F.Commands.size()<=Frame::MaxCommands,"render stays bounded");
    if(Argc>1) { Parity(Argv[1],0); Parity(Argv[1],1); }
    std::cout<<"shardring cabinet: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
