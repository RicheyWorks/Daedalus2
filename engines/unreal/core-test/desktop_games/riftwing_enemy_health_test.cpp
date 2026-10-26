// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include <iostream>
#include <sstream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct RiftwingTestAccess {
    static void Fixture(RiftwingGame& G,bool Chaser,bool Rehearsal=false) {
        G.SetOption(Rehearsal?1:0,730);G.SpawnTimer=100;G.Bullets.clear();G.Powerups.clear();
        G.Enemies={{500,250,3,Chaser?4:2,60,Chaser,true}};
    }
    static const RiftwingGame::Enemy& EnemyOf(const RiftwingGame& G) {return G.Enemies.front();}
    static const RiftwingGame::Enemy& BossOf(const RiftwingGame& G) {return G.Boss;}
    static void Hit(RiftwingGame& G) {const auto E=G.Enemies.front();G.Bullets.push_back({E.X-10,E.Y,10,0,true});}
    static void Escaping(RiftwingGame& G) {G.Enemies.front().X=-19;}
    static void ClearEnemies(RiftwingGame& G) {G.Enemies.clear();}
    static bool OriginalDrop(const RiftwingGame& Before,const RiftwingGame& After) {
        auto R=Before.Rng,S=After.Rng;const bool Drops=R.Unit()<.25;const int Kind=Drops?R.Int(0,2):-1;
        return R.Next()==S.Next()&&After.Powerups.size()==(Drops?1u:0u)&&(!Drops||static_cast<int>(After.Powerups[0].Kind)==Kind);
    }
    static std::string Snapshot(const RiftwingGame& G) {
        std::ostringstream O;O.precision(17);O<<G.Option<<' '<<G.Score<<' '<<G.SessionSeed<<' '<<G.SpawnTimer<<' '<<G.Over<<' '<<G.Won<<' '<<G.BossActive;
        const auto& P=G.Pilot;O<<' '<<P.X<<' '<<P.Y<<' '<<P.Speed<<' '<<P.Cooldown<<' '<<P.Power<<' '<<P.Lives<<' '<<P.Invincible;
        const auto EnemyOut=[&](const RiftwingGame::Enemy& E){O<<' '<<E.X<<' '<<E.Y<<' '<<E.Speed<<' '<<E.Health<<' '<<E.ShootTimer<<' '<<E.Chaser<<' '<<E.Alive;};
        EnemyOut(G.Boss);O<<' '<<G.Enemies.size();for(const auto& E:G.Enemies) EnemyOut(E);
        O<<' '<<G.Bullets.size();for(const auto& B:G.Bullets) O<<' '<<B.X<<' '<<B.Y<<' '<<B.Vx<<' '<<B.Vy<<' '<<B.Alive;
        O<<' '<<G.Powerups.size();for(const auto& V:G.Powerups) O<<' '<<V.X<<' '<<V.Y<<' '<<static_cast<int>(V.Kind)<<' '<<V.Alive;
        for(const auto& S:G.Stars) O<<' '<<S.X<<' '<<S.Y<<' '<<S.Speed;
        auto Copy=G.Rng;O<<' '<<Copy.Next();return O.str();
    }
};
}}
namespace {
using Riftwing=RiftwingGame;
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& Why) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<Why<<'\n';}}
bool ColorIs(Color C,int R,int G,int B) {return C.R==R&&C.G==G&&C.B==B&&C.A==255;}
int Slots(const Frame& F) {return static_cast<int>(std::count_if(F.Commands.begin(),F.Commands.end(),[](const DrawCommand& C){return C.Kind==Shape::Rectangle&&C.B.X==6&&C.B.Y==5;}));}
const DrawCommand* RectAt(const Frame& F,double X,double Y,double W,double H) {
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle&&C.A.X==X&&C.A.Y==Y&&C.B.X==W&&C.B.Y==H) return &C;
    return nullptr;
}
bool Pips(const Frame& F,const Riftwing::Enemy& E) {
    const int Max=E.Chaser?4:2;const double Top=E.Y-(E.Chaser?23:21);const auto* Back=RectAt(F,E.X-Max*4-1,Top,Max*8+2,9);
    if(!Back||!ColorIs(Back->Tint,0,0,40)||Slots(F)!=Max) return false;
    for(int N=0;N<Max;++N) {const auto* Slot=RectAt(F,E.X-Max*4+1+N*8,Top+2,6,5);
        if(!Slot||!(N<E.Health?ColorIs(Slot->Tint,255,215,100):ColorIs(Slot->Tint,70,70,90))) return false;
    }return true;
}
bool Silhouette(const Frame& F,const Riftwing::Enemy& E) {
    for(const auto& C:F.Commands) {
        if(E.Chaser&&C.Kind==Shape::Triangle&&C.A.X==E.X+10&&C.A.Y==E.Y&&C.B.X==E.X-12&&C.B.Y==E.Y-10&&C.C.X==E.X-12&&C.C.Y==E.Y+10&&ColorIs(C.Tint,255,100,100)) return true;
        if(!E.Chaser&&C.Kind==Shape::Circle&&C.A.X==E.X+5&&C.A.Y==E.Y&&C.Size==5&&ColorIs(C.Tint,255,150,150)) return true;
    }return false;
}
void RealHits(bool Chaser) {
    Riftwing G;RiftwingTestAccess::Fixture(G,Chaser);const int Max=Chaser?4:2;Frame F;G.Render(F);
    Check(Pips(F,RiftwingTestAccess::EnemyOf(G))&&Silhouette(F,RiftwingTestAccess::EnemyOf(G)),"full health pips accompany the original enemy silhouette");
    for(int Hit=1;Hit<Max;++Hit) {
        RiftwingTestAccess::Hit(G);G.Step({});G.Render(F);
        Check(G.GetEnemyCount()==1&&RiftwingTestAccess::EnemyOf(G).Health==Max-Hit&&G.GetStatus().Score==0,"real nonlethal projectile removes one health without awarding a kill");
        if(G.GetEnemyCount()==0) return;
        const auto& E=RiftwingTestAccess::EnemyOf(G);Check(E.X<500&&E.Y!=250&&Pips(F,E)&&Silhouette(F,E),"remaining and empty pips follow the moving enemy's exact body position");
    }
    const auto Before=G;RiftwingTestAccess::Hit(G);G.Step({});G.Render(F);
    Check(G.GetEnemyCount()==0&&G.GetStatus().Score==100&&Slots(F)==0,"lethal real projectile removes the enemy and cue for the original hundred points");
    Check(RiftwingTestAccess::OriginalDrop(Before,G),"lethal hit retains the original random drop draw and optional kind draw");
}
void BossAndCull() {
    Riftwing G;RiftwingTestAccess::Fixture(G,false,true);Frame F;G.Render(F);
    Check(G.HasBoss()&&G.GetBossHealth()==20&&Pips(F,RiftwingTestAccess::EnemyOf(G)),"rehearsal ordinary enemy receives the same cue without adding boss pips");
    RiftwingTestAccess::ClearEnemies(G);G.Render(F);const auto& B=RiftwingTestAccess::BossOf(G);int Bars=0;
    for(const auto& C:F.Commands) if(C.Kind==Shape::Rectangle&&C.A.X==B.X-30&&C.A.Y==B.Y-40&&C.B.X==60&&C.B.Y==6) ++Bars;
    Check(Slots(F)==0&&Bars==2,"boss alone keeps its existing health bar and receives no ordinary health slots");
    RiftwingTestAccess::Fixture(G,true);RiftwingTestAccess::Escaping(G);G.Step({});G.Render(F);
    Check(G.GetEnemyCount()==0&&Slots(F)==0&&G.GetStatus().Score==0,"normal offscreen cleanup removes health pips without a kill reward");
}
void Purity() {
    Riftwing G;RiftwingTestAccess::Fixture(G,true);const auto Before=RiftwingTestAccess::Snapshot(G);auto Quiet=G;Frame F;
    for(int N=0;N<4;++N) {G.Render(F);G.GetStatus();}
    Check(RiftwingTestAccess::Snapshot(G)==Before,"repeated health display reads leave complete game and RNG state unchanged");
    for(int N=0;N<6;++N) {G.Render(F);Input I;I.Down=N<3;I.Fire=N<4;G.Step(I);Quiet.Step(I);}
    Check(RiftwingTestAccess::Snapshot(G)==RiftwingTestAccess::Snapshot(Quiet),"extra pip rendering preserves subsequent movement fire timers and RNG");
}
}
int main() {
    RealHits(false);RealHits(true);BossAndCull();Purity();
    std::cout<<"Riftwing enemy health: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";return Failed?1:0;
}
