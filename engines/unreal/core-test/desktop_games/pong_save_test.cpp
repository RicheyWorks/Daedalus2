// SPDX-License-Identifier: MIT
// Twinwake Volley checkpoint save (DPS1): round trip in every mode, strict
// restore validation, finished matches are not saved, Driver integration.
// catalog-capability: save_restore: pong
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}

void RoundTrip() {
    for(int Mode=0;Mode<4;++Mode) {
        PongGame G;G.SetOption(Mode,3);
        G.S.PlayerScore=Mode==3?2:4;G.S.ComputerScore=Mode==3?0:3;G.S.BestRally=17;
        const std::string Save=G.SaveState();
        const std::string Tag="mode "+std::to_string(Mode)+": ";
        Check(Save.rfind("DPS1 ",0)==0,Tag+"payload is DPS1");
        PongGame H;
        Check(H.RestoreState(Save,3),Tag+"own payload restores");
        Check(H.GetOption()==Mode && H.S.PlayerScore==G.S.PlayerScore && H.S.ComputerScore==G.S.ComputerScore
            && H.S.BestRally==17,Tag+"mode, scores and best rally restored");
        Check(H.SaveState()==Save,Tag+"restore then save round-trips");
        PongGame Fresh;Fresh.SetOption(Mode,3);
        Check(H.S.BallX==Fresh.S.BallX && H.S.PlayerY==Fresh.S.PlayerY && H.S.ServeFrames==Fresh.S.ServeFrames,
            Tag+"restore starts a fresh serve");
        Check(!H.GetStatus().Over,Tag+"restored match is live");
    }
}

void FinishedNotSaved() {
    PongGame Q;Q.SetOption(2,1);Q.S.PlayerScore=5;
    Check(Q.SaveState().empty(),"finished quick match is not saved");
    PongGame T;T.SetOption(3,1);T.S.PlayerScore=3;
    Check(T.SaveState().empty(),"finished target rally is not saved");
}

void RejectsBadPayloads() {
    const char* Bad[]={"","DPS2 0 1 1 1","DPS1 0 1 1","DPS1 0 1 1 1 extra","DPS1 4 0 0 0","DPS1 -1 0 0 0",
        "DPS1 0 -1 0 0","DPS1 0 0 0 -1","DPS1 0 1000000001 0 0","DPS1 2 5 0 0","DPS1 2 0 5 0",
        "DPS1 3 3 0 0","DPS1 3 1 1 0","DPS1 x 0 0 0","DPS1 0 1.5 0 0"};
    for(const char* P:Bad) {
        PongGame G;G.SetOption(1,1);G.S.PlayerScore=2;
        Check(!G.RestoreState(P,1),std::string("rejects '")+P+"'");
        Check(G.GetOption()==1 && G.S.PlayerScore==2,std::string("rejected payload leaves the match untouched: '")+P+"'");
    }
    PongGame G;Check(!G.RestoreState(std::string(200,' ')+"DPS1 0 0 0 0",1),"rejects oversized payload");
}

void ThroughDriver() {
    Driver D;D.Select("pong",5);D.SetOption(2);
    for(int N=0;N<40;++N) D.Advance(Driver::StepSeconds);
    const std::string Save=D.CaptureSave();
    Check(!Save.empty(),"driver captures a pong save");
    Driver E;E.Select("pong",5);
    Check(E.RestoreSave(Save),"driver restores a pong save");
    Check(E.GetOption()==2 && E.CaptureSave()==Save,"driver restore keeps mode and payload");
    Check(E.Advance(Driver::StepSeconds)==1,"restored run steps");
}
}  // namespace

int main() {
    RoundTrip();FinishedNotSaved();RejectsBadPayloads();ThroughDriver();
    std::cout<<"pong save: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
