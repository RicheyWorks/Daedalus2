// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct SegaTestAccess {
    static void ContactPickup(SegaShooterGame& G,SegaShooterGame::PowerKind Kind,int Lives,bool BossContact=false,bool LastBossHit=false) {
        G.Pilot.Lives=Lives;G.Pilot.Invincible=0;G.Pilot.X=BossContact?620:150;G.Pilot.Y=300;
        G.SpawnTimer=100;G.Bullets.clear();G.Enemies.clear();G.Powerups.clear();
        // Normal drift reaches the pilot this step. The second item expires offscreen.
        G.Powerups={{G.Pilot.X+2.5,300,Kind,true},{-19,450,Kind,true}};
        // These two ordinary actors leave bounds and must still be cleaned on defeat.
        G.Enemies.push_back({-19,500,3,2,60,true,true});
        G.Bullets.push_back({815,450,10,0,true});
        if(BossContact) {
            G.Score=1500;G.BossActive=true;
            G.Boss={G.Pilot.X,300,1.5,LastBossHit?1:20,60,true,true};
            if(LastBossHit) G.Bullets.push_back({G.Boss.X-10,300,10,0,true});
        } else G.Enemies.push_back({G.Pilot.X+3,300,3,4,60,true,true});
    }
    static const std::vector<SegaShooterGame::Powerup>& Pickups(const SegaShooterGame& G) {return G.Powerups;}
    static std::size_t BulletCount(const SegaShooterGame& G) {return G.Bullets.size();}
    static bool SameHidden(const SegaShooterGame& A,const SegaShooterGame& B) {
        auto R=A.Rng,S=B.Rng;
        return A.SessionSeed==B.SessionSeed && A.SpawnTimer==B.SpawnTimer && R.Next()==S.Next();
    }
};
}}

namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return A.Background.R==B.Background.R && A.Background.G==B.Background.G
        && A.Background.B==B.Background.B && A.Background.A==B.Background.A;
}
bool Same(const SegaShooterGame& A,const SegaShooterGame& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    const auto& P=A.GetPlayer();const auto& Q=B.GetPlayer();
    return SameFrame(F,G) && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note
        && P.X==Q.X && P.Y==Q.Y && P.Speed==Q.Speed && P.Cooldown==Q.Cooldown && P.Power==Q.Power
        && P.Lives==Q.Lives && P.Invincible==Q.Invincible && SegaTestAccess::SameHidden(A,B);
}
void FrozenAndReplay(const SegaShooterGame& Terminal,std::uint32_t Seed) {
    SegaShooterGame G=Terminal;
    Input Held;Held.Right=Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
    Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(Same(G,Terminal),"held result input cannot collect remaining pickups or animate terminal actors");
    for(int Event=0;Event<4;++Event) {
        G=Terminal;Game& Core=G;
        const bool Accepted=Event<2?Core.SourceControllerButton(Event):Core.SourceKeyDown(Event==2?6:7);
        Check(Accepted,"fresh A/Start/Enter/Space retries the defeated result");
        if(!Accepted) continue;
        SegaShooterGame Fresh;Fresh.Reset(Seed);
        Check(Same(G,Fresh),"retry resets pickups terminal flags player timers and original seed");
        for(int N=0;N<6;++N) {
            Input I;I.Right=N<3;I.Fire=N<4;I.FirePressed=N==0;G.Step(I);Fresh.Step(I);
        }
        Check(Same(G,Fresh),"following replay frames retain original seeded spawns and input behavior");
    }
}
void LethalPickup(SegaShooterGame::PowerKind Kind,bool BossContact) {
    constexpr std::uint32_t Seed=12345;
    SegaShooterGame G;G.Reset(Seed);SegaTestAccess::ContactPickup(G,Kind,1,BossContact);
    G.Step({});const auto& P=G.GetPlayer();const auto S=G.GetStatus();
    Check(S.Over && !S.Won && P.Lives==0 && S.Lives==0,"lethal contact remains a zero-life defeat beside any pickup kind");
    Check(P.Power==1 && P.Speed==5 && P.Invincible==60,"post-lethal pickups grant no weapon speed or life benefits");
    const auto& Pickups=SegaTestAccess::Pickups(G);
    Check(Pickups.size()==1 && Pickups[0].Alive && Pickups[0].Kind==Kind
        && Pickups[0].X==P.X && Pickups[0].Y==P.Y,"overlapping pickup stays alive at its normally updated position");
    Check(G.GetEnemyCount()==0 && SegaTestAccess::BulletCount(G)==0 && G.GetPickupCount()==1,"contact actor and out-of-bounds actors still receive normal cleanup");
    Check(S.Score==(BossContact?1500:0) && G.HasBoss()==BossContact,"lethal guard leaves existing boss progression and score intact");
    if(BossContact) Check(G.GetBossHealth()==20,"lethal boss contact does not damage the boss");
    if(Kind==SegaShooterGame::PowerKind::Life && !BossContact) FrozenAndReplay(G,Seed);
}
void SurvivingPickup(SegaShooterGame::PowerKind Kind) {
    SegaShooterGame G;G.Reset(12345);SegaTestAccess::ContactPickup(G,Kind,2);G.Step({});
    const auto& P=G.GetPlayer();
    Check(!G.GetStatus().Over && !G.GetStatus().Won && P.Invincible==60,"nonlethal contact remains live with normal protection");
    Check(P.Lives==(Kind==SegaShooterGame::PowerKind::Life?2:1)
        && P.Power==(Kind==SegaShooterGame::PowerKind::Power?2:1)
        && P.Speed==(Kind==SegaShooterGame::PowerKind::Speed?6:5),"surviving contact still applies the same-step pickup normally");
    Check(G.GetPickupCount()==0 && G.GetEnemyCount()==0 && SegaTestAccess::BulletCount(G)==0,"live pickup and expired actors clean up normally");
}
void MutualBossDefeat() {
    constexpr std::uint32_t Seed=98765;
    SegaShooterGame G;G.Reset(Seed);SegaTestAccess::ContactPickup(G,SegaShooterGame::PowerKind::Life,1,true,true);G.Step({});
    const auto S=G.GetStatus();
    Check(S.Over && S.Won && S.Lives==0 && S.Score==2000 && !G.HasBoss(),"simultaneous last boss hit and lethal contact retain both terminal flags and 500-point reward");
    Frame F;G.Render(F);bool NamedTie=false;
    for(const auto& C:F.Commands) if(C.Label=="BOSS DOWN / SHIP LOST") NamedTie=true;
    Check(NamedTie && S.Note.find("Boss defeated; ship lost")!=std::string::npos,"intentional mutual-defeat presentation remains available");
    Check(G.GetPickupCount()==1 && SegaTestAccess::Pickups(G)[0].Alive && G.GetPlayer().Lives==0,"mutual defeat leaves overlapping Life unconsumed");
    Check(SegaTestAccess::BulletCount(G)==0 && G.GetEnemyCount()==0,"boss hit and escaped actors still clean up on the tie");
    FrozenAndReplay(G,Seed);
}
}

int main() {
    for(auto Kind:{SegaShooterGame::PowerKind::Life,SegaShooterGame::PowerKind::Power,SegaShooterGame::PowerKind::Speed}) {
        LethalPickup(Kind,false);LethalPickup(Kind,true);SurvivingPickup(Kind);
    }
    MutualBossDefeat();
    std::cout<<"Sega terminal pickups: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
