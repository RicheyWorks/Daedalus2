// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void Trinket(ZeldaGame& G) {G.Hero.X=250;G.Hero.Y=280;G.Hero.AttackTimer=5;G.Hero.Attacking=true;}
    static void Roster(ZeldaGame& G) {G.Hero.Face=ZeldaGame::Facing::Right;for(auto& E:G.Enemies) {E.X=440;E.Y=450;}}
    static std::string Snapshot(const ZeldaGame& G,bool Preference=true) {
        std::ostringstream O;O.precision(17);if(Preference) O<<G.IsSwordAssistEnabled()<<' ';
        O<<G.SessionSeed<<' '<<G.Score<<' '<<G.Keys<<' '<<G.KeySpawned<<' '<<G.Over<<' '<<G.Won<<' '<<G.MessageTimer<<' '<<G.Message;
        const auto& P=G.Hero;O<<' '<<P.X<<' '<<P.Y<<' '<<P.Health<<' '<<P.MaxHealth<<' '<<P.AttackTimer<<' '<<P.Invincible<<' '<<P.Rupees<<' '<<static_cast<int>(P.Face)<<' '<<P.Attacking;
        for(const auto& E:G.Enemies) O<<' '<<E.X<<' '<<E.Y<<' '<<static_cast<int>(E.Kind)<<' '<<E.Health<<' '<<E.ShootTimer<<' '<<E.HitFlash<<' '<<E.Alive;
        O<<' '<<G.Projectiles.size();for(const auto& Pj:G.Projectiles) O<<' '<<Pj.X<<' '<<Pj.Y<<' '<<Pj.Dx<<' '<<Pj.Dy<<' '<<Pj.Alive;
        O<<' '<<G.Collectibles.size();for(const auto& C:G.Collectibles) O<<' '<<C.X<<' '<<C.Y<<' '<<static_cast<int>(C.Kind)<<' '<<C.Bob;
        auto Copy=G.Rng;O<<' '<<Copy.Next();return O.str();
    }
};
}}
namespace {
using Zelda=ZeldaGame;
using Access=MazeTestAccess;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
Input Toggle() {Input I;I.DashPressed=true;return I;}
Input Sword(int Alias,bool Fresh=false) {
    Input I;if(Fresh) {I.FirePressed=Alias==0;I.ActionPressed=Alias==1;I.JumpPressed=Alias==2;}
    else {I.Fire=Alias==0;I.Action=Alias==1;I.Jump=Alias==2;}return I;
}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto Tint=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!Tint(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y||C.Size!=D.Size||C.Label!=D.Label||!Tint(C.Tint,D.Tint)) return false;
    }return true;
}
void AliasesAndCadence() {
    for(int Alias=0;Alias<3;++Alias) {
        Zelda Off;Off.Reset(730);for(int N=0;N<36;++N) Off.Step(Sword(Alias));
        Check(!Off.IsSwordAssistEnabled()&&Off.GetPlayer().AttackTimer==0&&!Off.GetPlayer().Attacking,"default held Fire Action and Jump aliases never swing");
        Off.Step(Sword(Alias,true));Check(Off.GetPlayer().AttackTimer==17&&Off.GetPlayer().Attacking,"each fresh alias retains its original attack and same-frame timer tick with assist off");
        Zelda On;On.Reset(730);int Attacks=0;
        for(int N=0;N<55;++N) {
            Input I=Sword(Alias);I.DashPressed=N==0;On.Step(I);const int Timer=On.GetPlayer().AttackTimer;
            if(Timer==17) ++Attacks;
            if(N%18==0||N%18==17) Check(Timer==17-N%18,"assisted held alias uses exactly the original eighteen-step cadence");
        }
        Check(On.IsSwordAssistEnabled()&&Attacks==4,"toggle applies before held request and each held alias repeats without extra swings");
        On.Reset(99);Check(On.IsSwordAssistEnabled()&&On.GetPlayer().AttackTimer==0&&On.GetStatus().Score==0&&On.GetKeys()==0,"Reset clears the run while preserving the selected sword preference");
    }
    Zelda Fresh;Check(!Fresh.IsSwordAssistEnabled(),"fresh game object defaults sword assist off");
}
void ToggleProgressAndParity() {
    Zelda G;G.Reset(730);Access::Trinket(G);G.Step({});Check(G.GetPlayer().Rupees==1&&G.GetStatus().Score==10&&G.GetPlayer().AttackTimer==4,"toggle fixture collects an authored trinket through normal pickup logic");
    auto Plain=G;G.Step(Toggle());Plain.Step({});
    Check(G.IsSwordAssistEnabled()&&G.GetPlayer().AttackTimer==3&&Access::Snapshot(G,false)==Access::Snapshot(Plain,false),"toggle retains progress cooldown seed and the ordinary world step");
    Input HeldToggle;HeldToggle.Dash=true;for(int N=0;N<8;++N) {G.Step(HeldToggle);Plain.Step({});}
    Check(G.IsSwordAssistEnabled()&&Access::Snapshot(G,false)==Access::Snapshot(Plain,false),"held toggle cannot flip the preference repeatedly");
    G.Step(Toggle());Plain.Step({});Check(!G.IsSwordAssistEnabled()&&Access::Snapshot(G,false)==Access::Snapshot(Plain,false),"next fresh toggle disables assist without restarting progress");
    Zelda Assisted,Manual;Assisted.Reset(730);Manual.Reset(730);Assisted.Step(Toggle());Manual.Step({});
    for(int N=0;N<72;++N) {
        Input I;I.Right=N<8;I.Up=N>=8&&N<16;I.Down=N>=16&&N<24;Input Fresh=I;I.Fire=true;Fresh.FirePressed=N%18==0;
        Assisted.Step(I);Manual.Step(Fresh);
        Check(Access::Snapshot(Assisted,false)==Access::Snapshot(Manual,false),"held assist matches manual fresh swings including movement damage drops timers and RNG");
    }
    const auto Before=Access::Snapshot(Assisted);Frame F,Again;Assisted.Render(F);const auto Note=Assisted.GetStatus().Note;
    for(int N=0;N<4;++N) {Assisted.Render(Again);Assisted.GetStatus();Assisted.IsSwordAssistEnabled();}
    Check(Access::Snapshot(Assisted)==Before&&SameFrame(F,Again)&&Assisted.GetStatus().Note==Note,"presentation and preference reads cannot advance assisted combat");
    for(int N=0;N<8;++N) {Assisted.Step({});Manual.Step({});}
    Check(Access::Snapshot(Assisted,false)==Access::Snapshot(Manual,false),"equivalent manual and assisted play preserve future random decisions after release");
}
bool OriginalRosterRoute(Zelda& Victory) {
    Zelda G;G.Reset(730);Access::Roster(G);Input First=Sword(0);First.DashPressed=true;First.Left=true;G.Step(First);
    Check(G.IsSwordAssistEnabled()&&G.GetPlayer().X==396.5&&G.GetPlayer().Face==Zelda::Facing::Left&&G.LivingEnemyCount()==1&&G.GetEnemies()[1].Health==1&&G.GetStatus().Score==150,"assisted swing hits the original roster to the right before Left movement changes facing");
    Input Restore=Sword(0);Restore.Right=true;G.Step(Restore);int Steps=2;
    while(G.LivingEnemyCount()>0&&Steps<36) {G.Step(Sword(0));++Steps;}
    Check(Steps==19&&G.LivingEnemyCount()==0&&G.GetStatus().Score==200&&G.HasGroundKey()&&G.GetKeys()==0&&!G.GetStatus().Won,"second original-cadence hit defeats the original two-health Moblin and reveals a real uncollected key");
    if(G.LivingEnemyCount()!=0||!G.HasGroundKey()) return false;
    Input Collect;Collect.Right=true;G.Step(Collect);
    Check(G.GetStatus().Won&&!G.GetStatus().Over&&G.GetKeys()==1&&!G.HasGroundKey()&&G.GetStatus().Score==200+10*G.GetPlayer().Rupees,"normal Right movement collects the spawned key and completes the original victory rule");
    std::cout<<"Assisted original roster: "<<Steps<<" combat steps then one key-collection step\n";Victory=G;return G.GetStatus().Won;
}
void TerminalAndDriver(const Zelda& Victory) {
    auto G=Victory;const auto Before=Access::Snapshot(G);Frame F,Again;G.Render(F);Input Held;Held.Right=Held.Fire=Held.Action=Held.Jump=Held.Dash=true;Held.DashPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);G.Render(Again);
    Check(Access::Snapshot(G)==Before&&SameFrame(F,Again)&&G.IsSwordAssistEnabled(),"terminal handling freezes held attacks movement and toggle without replaying or changing preference");
    Input Retry;Retry.FirePressed=Retry.DashPressed=true;G.Step(Retry);auto Expected=Victory;Expected.Reset(730);
    Check(G.IsSwordAssistEnabled()&&G.GetPlayer().AttackTimer==0&&Access::Snapshot(G)==Access::Snapshot(Expected),"fresh retry preserves preference and returns before toggling or implicitly swinging");
    Driver D;Check(D.Select("zelda",730),"Driver selects the existing Lanternwild engine");Zelda Model;Model.Reset(730);D.SetInput(Toggle());D.Advance(Driver::StepSeconds*2.5);Model.Step(Toggle());Model.Step({});Model.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&Model.IsSwordAssistEnabled(),"catch-up consumes one fresh assist toggle edge");
    const auto Paused=D.GetFrame();Input Queued=Toggle();Queued.Fire=Queued.FirePressed=true;D.SetPaused(true);D.SetInput(Queued);
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Paused,D.GetFrame()),"pause freezes queued preference and sword input");
    D.SetPaused(false);D.Advance(Driver::StepSeconds);Model.Step({});Model.Render(F);Check(SameFrame(D.GetFrame(),F),"resume discards paused toggle and sword input");
    D.SetInput(Sword(0));D.Advance(Driver::StepSeconds*8);for(int N=0;N<8;++N) Model.Step(Sword(0));Model.Render(F);
    Check(SameFrame(D.GetFrame(),F),"Driver catch-up preserves assisted held cadence across fixed steps");
    D.SetInput(Queued);D.Restart();Model.Reset(730);Model.Render(F);
    Check(D.Ticks()==0&&!D.IsPaused()&&SameFrame(D.GetFrame(),F)&&Model.IsSwordAssistEnabled(),"same-cabinet Driver Restart keeps assist while clearing queued input and run state");
    D.Advance(Driver::StepSeconds);Model.Step({});Model.Render(F);Check(SameFrame(D.GetFrame(),F),"restart prevents stale held input from swinging or toggling immediately");
    D.SetInput(Queued);Check(D.Select("zelda",730),"fresh selection creates a new cabinet instance");Zelda Fresh;Fresh.Reset(730);Fresh.Render(F);
    Check(SameFrame(D.GetFrame(),F)&&!Fresh.IsSwordAssistEnabled(),"new Driver Select defaults assist off instead of retaining another instance's preference");
    D.Advance(Driver::StepSeconds);Fresh.Step({});Fresh.Render(F);Check(SameFrame(D.GetFrame(),F),"fresh selection also clears queued sword and toggle input");
}
}
int main() {
    AliasesAndCadence();ToggleProgressAndParity();Zelda Victory;if(OriginalRosterRoute(Victory)) TerminalAndDriver(Victory);
    std::cout<<"Zelda sword assist: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
