// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
struct StarTerminalTestAccess {
    enum class Contact { Bullet, Enemy, Boss };
    static void Arrange(StarShooterGame& G,StarShooterGame::PowerKind Kind,Contact Hit,int Lives,bool Shield=false) {
        G.Pilot.Lives=Lives;G.Pilot.Invincible=0;G.Pilot.Shield=Shield;
        G.Score=300;G.Wave=Hit==Contact::Boss?5:4;G.WaveTimer=12;
        const double X=G.Pilot.X,Y=G.Pilot.Y;
        // Ordinary pickup drift reaches the pilot; a companion expires normally.
        G.Powerups={{X,Y-2,0,Kind,true},{60,619,0,Kind,true}};
        G.Bullets.push_back({819,100,2,0});
        StarShooterGame::Enemy Escaped;Escaped.Kind=StarShooterGame::EnemyKind::Cruiser;
        Escaped.X=100;Escaped.Y=640;Escaped.Speed=1;G.Enemies.push_back(Escaped);
        if(Hit==Contact::Bullet) {
            StarShooterGame::Enemy Bee;Bee.X=X;Bee.Y=Y-18;Bee.ShootTimer=0;
            const auto Shots=Bee.Shoot(100);G.Bullets.insert(G.Bullets.end(),Shots.begin(),Shots.end());
        }
        else if(Hit==Contact::Enemy) {
            StarShooterGame::Enemy E;E.X=X;E.Y=Y-5.5;E.StartDive(X,Y);G.Enemies.push_back(E);
        } else {
            G.BossActive=true;G.BossActor=StarShooterGame::Boss::Create(5,G.Mode,400);
            G.BossActor.Y=120;G.BossActor.State=StarShooterGame::BossState::Pacing;G.BossActor.ChargeTimer=1;
            G.BossActor.Update(X,Y,400);
            for(int N=0;N<54;++N) G.BossActor.Update(X,Y,400);
        }
        G.Effects.push_back({100,100,1,2,1,White});
        G.Popups.push_back({100,100,"expired",1,White});
    }
    static bool RetainedPickup(const StarShooterGame& G,StarShooterGame::PowerKind Kind) {
        return G.Powerups.size()==1 && G.Powerups[0].Alive && G.Powerups[0].Kind==Kind
            && G.Powerups[0].X==G.Pilot.X && G.Powerups[0].Y==G.Pilot.Y && G.Powerups[0].Bob==0.1;
    }
    static bool Cleaned(const StarShooterGame& G) {
        return G.Bullets.empty() && G.Enemies.empty() && G.Popups.empty()
            && std::all_of(G.Effects.begin(),G.Effects.end(),[](const auto& P){return P.Life>0;});
    }
    static bool SameHidden(const StarShooterGame& A,const StarShooterGame& B) {
        auto R=A.Rng,S=B.Rng;
        return R.Next()==S.Next() && A.WaveTimer==B.WaveTimer && A.SpawnTimer==B.SpawnTimer
            && A.NextId==B.NextId && A.Effects.size()==B.Effects.size() && A.Popups.size()==B.Popups.size();
    }
    static void ExistingLoadout(StarShooterGame& G) {G.Pilot.Triple=G.Pilot.SpeedBoost=true;}
};
}}

namespace {
using Star=StarShooterGame;
using Access=StarTerminalTestAccess;
int Checks=0,Failed=0;
void Check(bool Ok,const char* What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool HasLabel(const Frame& F,const char* Label) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[Label](const auto& C){return C.Kind==Shape::Text && C.Label==Label;});
}
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
bool Same(const Star& A,const Star& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    const auto& P=A.GetPlayer();const auto& Q=B.GetPlayer();
    return SameFrame(F,G) && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note
        && A.SaveState()==B.SaveState() && A.EntityCount()==B.EntityCount()
        && P.X==Q.X && P.Y==Q.Y && P.Cooldown==Q.Cooldown && P.Invincible==Q.Invincible
        && A.IsPaused()==B.IsPaused() && A.WantsQuit()==B.WantsQuit() && A.HasSaveRequest()==B.HasSaveRequest()
        && Access::SameHidden(A,B);
}
void FrozenAndReset(const Star& Terminal,Star::Difficulty Mode,std::uint32_t Seed) {
    Star G=Terminal;
    Input Held;Held.Right=Held.Fire=Held.Jump=Held.Action=Held.Dash=true;
    Held.FirePressed=Held.JumpPressed=Held.ActionPressed=Held.DashPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(Same(G,Terminal),"held terminal input cannot consume deferred pickups or change frozen result");
    Frame Result,PausedResult;G.Render(Result);G.OwnPause(true);G.Render(PausedResult);
    Check(G.IsCorePaused() && G.GetStatus().Over && HasLabel(Result,"GAME OVER"),"host can retain its pause flag on a real game-over result");
    Check(SameFrame(Result,PausedResult),"host pause leaves the final result visible without an inert menu over it");
    G.Reset(Seed);Star Fresh;Fresh.SetDifficulty(Mode);Fresh.Reset(Seed);
    Check(Same(G,Fresh),"existing reset clears final actors while retaining chosen difficulty and seeded state");
    for(int N=0;N<6;++N) {Input I;I.Right=N<3;I.Fire=N<4;G.Step(I);Fresh.Step(I);}
    Check(Same(G,Fresh),"following reset frames preserve seeded gameplay");
}
void ContactCase(Star::PowerKind Kind,Access::Contact Hit,int Lives,bool Shield=false) {
    constexpr std::uint32_t Seed=12345;
    Star G;G.Reset(Seed);Access::Arrange(G,Kind,Hit,Lives,Shield);G.Step({});
    const bool Lethal=Lives==1 && !Shield;const auto& P=G.GetPlayer();const auto S=G.GetStatus();
    Check(S.Over==Lethal && !S.Won && S.Lives==(Shield?Lives:Lives-1),"ordinary contact determines final lives and terminal flag");
    Check(P.Invincible==(Shield?60:90),"normal damage or shield absorption protection remains intact");
    Check(P.Triple==(!Lethal && Kind==Star::PowerKind::Triple)
        && P.Shield==(!Lethal && Kind==Star::PowerKind::Shield)
        && P.SpeedBoost==(!Lethal && Kind==Star::PowerKind::Speed),"only surviving contacts receive same-step upgrades");
    Check(Lethal?Access::RetainedPickup(G,Kind):G.GetPickupCount()==0,"lethal contact retains overlapping item; survivors consume it");
    Check(Access::Cleaned(G),"consumed contacts and expired bullets enemies pickups effects and popups still clean up");
    Check(S.Score==300 && G.GetWave()==(Hit==Access::Contact::Boss?5:4) && G.GetWaveFramesRemaining()==1187
        && G.HasBoss()==(Hit==Access::Contact::Boss),"pickup guard leaves existing score wave and boss ordering intact");
}
void RetainLoadoutAndReset(Star::Difficulty Mode) {
    constexpr std::uint32_t Seed=UINT32_MAX;
    Star G;G.SetDifficulty(Mode);G.Reset(Seed);
    Access::Arrange(G,Star::PowerKind::Shield,Access::Contact::Bullet,1);
    Access::ExistingLoadout(G);G.Step({});
    Check(G.GetStatus().Over && G.GetPlayer().Triple && G.GetPlayer().SpeedBoost && !G.GetPlayer().Shield,
        "defeat preserves earlier upgrades without granting the overlapping shield");
    FrozenAndReset(G,Mode,Seed);
}
void LivePauseMenu() {
    Star G;G.Reset(730);G.OwnPause(true);Frame Paused;G.Render(Paused);
    Check(G.IsCorePaused() && !G.GetStatus().Over && HasLabel(Paused,"PAUSED"),"live pause still renders its working menu");
    Input Confirm;Confirm.FirePressed=true;G.Step(Confirm);
    Check(!G.IsCorePaused() && !G.GetStatus().Over && !G.WantsQuit() && !G.HasSaveRequest(),"fresh confirmation still resumes the live default menu choice");
}
}
int main() {
    for(auto Kind:{Star::PowerKind::Triple,Star::PowerKind::Shield,Star::PowerKind::Speed}) {
        for(auto Hit:{Access::Contact::Bullet,Access::Contact::Enemy,Access::Contact::Boss}) ContactCase(Kind,Hit,1);
        ContactCase(Kind,Access::Contact::Bullet,2);ContactCase(Kind,Access::Contact::Bullet,1,true);
    }
    for(auto Mode:{Star::Difficulty::Easy,Star::Difficulty::Medium,Star::Difficulty::Hard}) RetainLoadoutAndReset(Mode);
    LivePauseMenu();
    std::cout<<"Star terminal pickups: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
