// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct SegaTestAccess {
    static void Score(SegaShooterGame& G,std::int64_t Value) {G.Score=Value;}
    static const SegaShooterGame::Enemy& BossOf(const SegaShooterGame& G) {return G.Boss;}
    static void HitBoss(SegaShooterGame& G) {G.Bullets.push_back({G.Boss.X-10,G.Boss.Y,10,0,true});}
    static void Contact(SegaShooterGame& G) {
        G.Pilot.X=G.Boss.X;G.Pilot.Y=G.Boss.Y;G.Pilot.Lives=1;G.Pilot.Invincible=0;
        G.Enemies.clear();G.Bullets.clear();G.Powerups.clear();G.SpawnTimer=100;
    }
    static std::string Snapshot(const SegaShooterGame& G,bool IncludeModeScore=true) {
        std::ostringstream O;O.precision(17);if(IncludeModeScore) O<<G.Option<<' '<<G.Score<<' ';
        O<<G.SessionSeed<<' '<<G.SpawnTimer<<' '<<G.Over<<' '<<G.Won<<' '<<G.BossActive;
        const auto& P=G.Pilot;O<<' '<<P.X<<' '<<P.Y<<' '<<P.Speed<<' '<<P.Cooldown<<' '<<P.Power<<' '<<P.Lives<<' '<<P.Invincible;
        const auto EnemyOut=[&](const SegaShooterGame::Enemy& E){O<<' '<<E.X<<' '<<E.Y<<' '<<E.Speed<<' '<<E.Health<<' '<<E.ShootTimer<<' '<<E.Chaser<<' '<<E.Alive;};
        EnemyOut(G.Boss);O<<' '<<G.Enemies.size();for(const auto& E:G.Enemies) EnemyOut(E);
        O<<' '<<G.Bullets.size();for(const auto& B:G.Bullets) O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Alive;
        O<<' '<<G.Powerups.size();for(const auto& V:G.Powerups) O<<' '<<V.X<<' '<<V.Y<<' '<<static_cast<int>(V.Kind)<<' '<<V.Alive;
        O<<' '<<G.Stars.size();for(const auto& S:G.Stars) O<<' '<<S.X<<' '<<S.Y<<' '<<S.Speed;
        Random Copy=G.Rng;O<<' '<<Copy.Next();return O.str();
    }
    static bool SameStarsAndRng(const SegaShooterGame& A,const SegaShooterGame& B) {
        for(std::size_t N=0;N<A.Stars.size();++N) if(A.Stars[N].X!=B.Stars[N].X||A.Stars[N].Y!=B.Stars[N].Y||A.Stars[N].Speed!=B.Stars[N].Speed) return false;
        Random R=A.Rng,S=B.Rng;return A.Stars.size()==80&&B.Stars.size()==80&&R.Next()==S.Next();
    }
};
}}
namespace {
using Sega=SegaShooterGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    const auto ColorEqual=[](Color C,Color D){return C.R==D.R&&C.G==D.G&&C.B==D.B&&C.A==D.A;};
    if(A.Width!=B.Width||A.Height!=B.Height||!ColorEqual(A.Background,B.Background)||A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind||C.A.X!=D.A.X||C.A.Y!=D.A.Y||C.B.X!=D.B.X||C.B.Y!=D.B.Y||C.C.X!=D.C.X||C.C.Y!=D.C.Y
            ||C.Size!=D.Size||C.Label!=D.Label||!ColorEqual(C.Tint,D.Tint)) return false;
    }return true;
}
bool Text(const Frame& F,const std::string& Part) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text&&C.Label.find(Part)!=std::string::npos) return true;
    return false;
}
Sega Rehearsal() {Sega G;G.SetOption(1,730);return G;}
void ModesAndGate() {
    Sega Full;Full.Reset(730);Check(Full.GetOption()==0&&!Full.HasBoss()&&Full.GetStatus().Score==0,"full run stays the default without an immediate boss");
    auto G=Rehearsal();const auto& P=G.GetPlayer();const auto& Boss=SegaTestAccess::BossOf(G);
    Check(G.GetOption()==1&&G.HasBoss()&&G.GetBossHealth()==20&&Boss.X==750&&Boss.Y==300&&Boss.Speed==1.5&&Boss.Chaser,"rehearsal starts the original twenty-health boss immediately");
    Check(P.X==150&&P.Y==300&&P.Lives==3&&P.Power==1&&P.Speed==5&&P.Invincible==0&&G.GetStatus().Score==0,"rehearsal starts with normal ship and zero score");
    Check(SegaTestAccess::SameStarsAndRng(Full,G),"mode selection retains the same eighty seeded stars and random stream");
    Frame F;Full.Render(F);Check(!Text(F,"REHEARSAL")&&Full.GetStatus().Note.find("Boss rehearsal")==std::string::npos,"full-run presentation keeps its existing unprefixed identity");
    G.Render(F);Check(Text(F,"REHEARSAL | ENEMIES")&&G.GetStatus().Note.rfind("Boss rehearsal; ",0)==0,"live presentation identifies rehearsal without hiding normal enemies");
    G.Step({});const auto Before=SegaTestAccess::Snapshot(G);Frame Picture;G.Render(Picture);
    for(int Value:{-1,2}) {
        Check(!G.SetOption(Value,99)&&SegaTestAccess::Snapshot(G)==Before,"invalid mode is refused before changing seed state or score");
        G.Render(F);Check(SameFrame(Picture,F),"invalid mode preserves the live rehearsal picture");
    }
    Check(G.GetEnemyCount()==1&&G.HasBoss()&&G.GetBossHealth()==20,"normal initial enemy spawn remains active beside the rehearsal boss");
    Check(G.SetOption(0,730)&&SegaTestAccess::Snapshot(G)==SegaTestAccess::Snapshot(Full),"returning to full run restores its complete seeded initial state");
    for(int N=0;N<4;++N) {Input I;I.Fire=N<3;I.Down=N==1;G.Step(I);Full.Step(I);}
    Check(SegaTestAccess::Snapshot(G)==SegaTestAccess::Snapshot(Full),"default and explicitly selected full run retain identical affected steps");
    Full.Reset(730);SegaTestAccess::Score(Full,1499);Full.Step({});Check(!Full.HasBoss()&&Full.GetStatus().Score==1499,"full-run boss gate remains closed below fifteen hundred");
    Full.Reset(730);SegaTestAccess::Score(Full,1500);G=Rehearsal();Full.Step({});G.Step({});
    Check(Full.HasBoss()&&Full.GetBossHealth()==20&&Full.GetStatus().Score==1500&&SegaTestAccess::Snapshot(Full,false)==SegaTestAccess::Snapshot(G,false),"existing full-run threshold starts the identical boss without changing world RNG or timing");
}
void Frozen(const Sega& G) {
    Sega Copy=G;const auto Before=SegaTestAccess::Snapshot(Copy);Frame F,Again;Copy.Render(F);const auto Note=Copy.GetStatus().Note;
    Input Held;Held.Right=Held.Fire=Held.Jump=Held.Action=true;Held.FirePressed=Held.JumpPressed=Held.ActionPressed=true;
    for(int N=0;N<8;++N) {Copy.Step(Held);Copy.Render(Again);Copy.GetStatus();}
    Check(SegaTestAccess::Snapshot(Copy)==Before&&SameFrame(F,Again)&&Copy.GetStatus().Note==Note,"terminal held input and presentation cannot change actors timers score or RNG");
}
void BossResults() {
    auto G=Rehearsal();
    for(int Hit=1;Hit<=19;++Hit) {SegaTestAccess::HitBoss(G);G.Step({});Check(G.HasBoss()&&G.GetBossHealth()==20-Hit&&!G.GetStatus().Won,"each real projectile step removes one boss health");}
    const auto LastHit=G;SegaTestAccess::HitBoss(G);G.Step({});Frame F;G.Render(F);
    Check(!G.HasBoss()&&G.GetStatus().Won&&!G.GetStatus().Over&&G.GetStatus().Score==500&&G.GetPlayer().Lives==3,"twentieth real hit completes rehearsal for only the existing five-hundred reward");
    Check(G.GetEnemyCount()>0&&Text(F,"REHEARSAL COMPLETE!"),"ordinary spawn pressure remains present at rehearsal victory");Frozen(G);
    Check(G.SourceControllerButton(0)&&G.GetOption()==1&&SegaTestAccess::Snapshot(G)==SegaTestAccess::Snapshot(Rehearsal()),"fresh controller retry retains rehearsal and the original seeded opening");
    auto Lost=LastHit;SegaTestAccess::Contact(Lost);Lost.Step({});Lost.Render(F);
    Check(Lost.GetStatus().Over&&!Lost.GetStatus().Won&&Lost.GetStatus().Score==0&&Lost.GetPlayer().Lives==0&&Text(F,"REHEARSAL ENDED"),"real last-life boss contact ends rehearsal without fake threshold score");Frozen(Lost);
    Check(Lost.SourceKeyDown(7)&&Lost.GetOption()==1&&SegaTestAccess::Snapshot(Lost)==SegaTestAccess::Snapshot(Rehearsal()),"fresh Space retry also retains rehearsal and clears defeat");
    auto Mutual=LastHit;SegaTestAccess::Contact(Mutual);SegaTestAccess::HitBoss(Mutual);Mutual.Step({});Mutual.Render(F);
    Check(Mutual.GetStatus().Over&&Mutual.GetStatus().Won&&Mutual.GetStatus().Score==500&&Mutual.GetPlayer().Lives==0&&!Mutual.HasBoss()&&Text(F,"BOSS DOWN / SHIP LOST"),"simultaneous last boss hit and ship loss retain both original outcomes");Frozen(Mutual);
}
void PublicHeldFire() {
    auto G=Rehearsal();Input I;I.Fire=true;int Steps=0;
    // One documented opening policy and seed, no state injection or tracking bot.
    while(!G.GetStatus().Over&&!G.GetStatus().Won&&Steps<600) {G.Step(I);++Steps;}
    const auto S=G.GetStatus();std::cout<<"Rehearsal held-fire seed730: "<<Steps<<" steps, score "<<S.Score<<", lives "<<S.Lives<<", boss HP "<<G.GetBossHealth()<<", over "<<S.Over<<", won "<<S.Won<<'\n';
    Check(S.Won&&!S.Over&&!G.HasBoss()&&S.Score>=500&&Steps<=600,"bounded real opening held-fire input can complete rehearsal with normal pressure");
}
void DriverLifecycle() {
    Driver D;Check(D.Select("sega_shooter",730),"Driver selects the existing Sega engine");D.Advance(Driver::StepSeconds*2.5);
    Input Stale;Stale.Down=Stale.Fire=Stale.FirePressed=true;D.SetInput(Stale);
    Check(D.SetOption(1)&&D.GetOption()==1&&D.Ticks()==0&&D.GetSeed()==730,"Driver option selection retains seed and clears old accounting");
    Check(D.Advance(Driver::StepSeconds*.5)==0,"rehearsal selection clears previous partial time");
    auto Expected=Rehearsal();Expected.Step({});Frame F;Expected.Render(F);
    Check(D.Advance(Driver::StepSeconds*.5)==1&&SameFrame(D.GetFrame(),F),"mode selection discards stale movement and fire before first rehearsal step");
    D.SetPaused(true);D.SetInput(Stale);const auto Before=D.GetFrame();
    Check(D.Advance(Driver::StepSeconds*8)==0&&SameFrame(Before,D.GetFrame()),"normal Driver pause freezes rehearsal");
    D.Restart();Expected=Rehearsal();Expected.Render(F);
    Check(D.GetOption()==1&&!D.IsPaused()&&D.Ticks()==0&&SameFrame(D.GetFrame(),F),"Driver Restart retains rehearsal while resetting ship boss and pause");
    Expected.Step({});Expected.Render(F);Check(D.Advance(Driver::StepSeconds)==1&&SameFrame(D.GetFrame(),F),"Restart clears paused queued fire and movement");
    const auto Active=D.GetFrame();const auto Ticks=D.Ticks();
    Check(!D.SetOption(2)&&D.GetOption()==1&&D.Ticks()==Ticks&&SameFrame(Active,D.GetFrame()),"invalid Driver mode leaves the active rehearsal intact");
}
}
int main() {
    ModesAndGate();BossResults();PublicHeldFire();DriverLifecycle();
    std::cout<<"Sega boss rehearsal: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
