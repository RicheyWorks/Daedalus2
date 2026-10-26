// SPDX-License-Identifier: MIT
// Star Shooter: difficulty options, pause menu (resume / save-and-quit / quit),
// DGS1 save round trip and strict restore validation, seeded determinism.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
using Star=StarShooterGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
Input Pause() {Input I;I.ActionPressed=true;return I;}
Input Confirm() {Input I;I.FirePressed=true;return I;}
Input Down() {Input I;I.Down=true;return I;}
Input Back() {Input I;I.DashPressed=true;return I;}

void DifficultyOptions() {
    Star G;
    Check(G.SetOption(0,7) && G.GetPlayer().Lives==5 && G.GetOption()==0,"easy gives 5 lives");
    Check(G.SetOption(1,7) && G.GetPlayer().Lives==4,"medium gives 4 lives");
    Check(G.SetOption(2,7) && G.GetOption()==2,"hard is selectable");
    Check(!G.SetOption(3,7) && !G.SetOption(-1,7) && G.GetOption()==2,"out-of-range option is refused and keeps the mode");
    Check(G.GetSpawnRate()==Star::Config(Star::Difficulty::Hard).SpawnRate,"reset uses the mode spawn rate");
}

void PauseFreezesAndResumes() {
    Star G;G.SetOption(1,11);
    for(int N=0;N<10;++N) G.Step(Input{});
    G.Step(Pause());
    Check(G.IsPaused() && G.IsCorePaused(),"Action pauses");
    Check(!G.IsFireReady(),"fire not ready while paused");
    const int Left=G.GetWaveFramesRemaining();
    for(int N=0;N<60;++N) G.Step(Input{});
    Check(G.GetWaveFramesRemaining()==Left,"wave clock frozen while paused");
    G.Step(Back());
    Check(!G.IsPaused(),"Dash/back resumes");
    G.Step(Input{});
    Check(G.GetWaveFramesRemaining()==Left-1,"wave clock runs again after resume");
    G.Step(Pause());G.Step(Confirm());
    Check(!G.IsPaused(),"confirm on Resume resumes");
    G.Step(Pause());G.Step(Pause());
    Check(!G.IsPaused(),"second Action unpauses");
}

void SaveAndQuitFromMenu() {
    Star G;G.SetOption(0,21);
    for(int N=0;N<30;++N) G.Step(Input{});
    G.Step(Pause());G.Step(Down());G.Step(Confirm());
    Check(G.HasSaveRequest() && G.SavePending(),"Save & Quit raises a save request");
    Check(G.WantsQuit() && G.WantsExit(),"Save & Quit asks the host to exit");
    const auto S=G.GetSaveRequest();
    Check(S.Mode==Star::Difficulty::Easy && S.Lives==5 && S.Wave==1,"save captures mode, lives and wave");
    const int Left=G.GetWaveFramesRemaining();
    for(int N=0;N<20;++N) G.Step(Input{});
    Check(G.GetWaveFramesRemaining()==Left,"no simulation after quit");
    G.ClearSavePending();
    Check(!G.HasSaveRequest(),"host can clear the save request");

    Star Q;Q.SetOption(1,5);Q.Step(Pause());Q.Step(Down());
    for(int N=0;N<16;++N) Q.Step(Input{});
    Q.Step(Down());Q.Step(Confirm());
    Check(Q.WantsQuit() && !Q.HasSaveRequest(),"Quit option exits without saving");
}

void SaveRoundTrip() {
    Star G;G.SetOption(2,99);
    for(int N=0;N<50;++N) G.Step(Input{});
    const std::string S=G.SaveState();
    Check(S.rfind("DGS1 ",0)==0,"save payload is DGS1");
    Star H;
    Check(H.RestoreState(S,3),"own payload restores");
    Check(H.SaveState()==S,"restore then save round-trips");
    Check(H.GetOption()==2 && H.GetPlayer().Lives==G.GetPlayer().Lives,"restore keeps mode and lives");
    Check(H.RestoreState("DGS1 1200 7 60 3 1 0 1 0 1",3),"hand-written payload restores");
    Check(H.GetWave()==7 && H.GetSpawnRate()==60 && H.GetPlayer().Triple && H.GetPlayer().SpeedBoost && !H.GetPlayer().Shield,"payload fields applied");
}

void RestoreRejectsBadPayloads() {
    const char* Bad[]={
        "", "DGS2 0 1 110 4 0 0 0 1 0", "DGS1 0 1 110 4 0 0 0 1", "DGS1 0 1 110 4 0 0 0 1 0 extra",
        "DGS1 0 1 110 4 2 0 0 1 0", "DGS1 0 1 110 4 0 0 0 3 0", "DGS1 0 1 110 4 0 0 0 1 2",
        "DGS1 -1 1 110 4 0 0 0 1 0", "DGS1 0 0 110 4 0 0 0 1 0", "DGS1 0 1 27 4 0 0 0 1 0",
        "DGS1 0 1 136 4 0 0 0 1 0", "DGS1 0 1 110 0 0 0 0 1 0", "DGS1 0 1 110 100 0 0 0 1 0",
        "DGS1 x 1 110 4 0 0 0 1 0"};
    for(const char* P:Bad) {
        Star G;G.SetOption(0,1);
        Check(!G.RestoreState(P,1),std::string("rejects payload: '")+P+"'");
        Check(G.GetOption()==0 && G.GetWave()==1,std::string("rejected payload leaves run untouched: '")+P+"'");
    }
    Star G;Check(!G.RestoreState(std::string(300,' ')+"DGS1 0 1 110 4 0 0 0 1 0",1),"rejects oversized payload");
}

void SeededDeterminism() {
    Star A,B;A.SetOption(1,4242);B.SetOption(1,4242);
    for(int N=0;N<600;++N) {
        Input I;I.Left=(N/40)%2==0;I.Right=!I.Left;I.Fire=N%3==0;
        A.Step(I);B.Step(I);
    }
    Check(A.SaveState()==B.SaveState(),"same seed and inputs give the same run");
    Check(A.GetEnemyCount()==B.GetEnemyCount() && A.EntityCount()==B.EntityCount(),"same entity counts");
    Check(A.GetStatus().Note==B.GetStatus().Note,"same status text");
}
}  // namespace

int main() {
    DifficultyOptions();PauseFreezesAndResumes();SaveAndQuitFromMenu();
    SaveRoundTrip();RestoreRejectsBadPayloads();SeededDeterminism();
    std::cout<<"star save/pause: "<<(Checks-Failed)<<"/"<<Checks<<" checks\n";
    return Failed==0?0:1;
}
