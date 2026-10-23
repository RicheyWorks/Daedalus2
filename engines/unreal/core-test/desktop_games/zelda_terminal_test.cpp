// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <iostream>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
// Existing friend seam: arrange a single ordinary pickup/projectile overlap,
// then let the real Step settle damage, pickups and the terminal result.
struct MazeTestAccess {
    static void ProjectileAtPickup(ZeldaGame& G,ZeldaGame::PickupKind Kind,int Health) {
        G.Hero.Health=Health;G.Hero.Invincible=0;
        if(Kind==ZeldaGame::PickupKind::Heart) {G.Hero.X=150;G.Hero.Y=420;}
        else if(Kind==ZeldaGame::PickupKind::Rupee) {G.Hero.X=250;G.Hero.Y=280;}
        else {
            // A last-defeated enemy can leave its key while a previously fired rock is in flight.
            G.Hero.X=620;G.Hero.Y=350;
            for(auto& E:G.Enemies) {E.Alive=false;E.Health=0;}
            G.KeySpawned=true;G.Score=200;
            G.Collectibles.push_back({620,350,ZeldaGame::PickupKind::Key,0});
        }
        // Source rock speed is 2.5 pixels/step; this one reaches the hero on this step.
        G.Projectiles={{G.Hero.X,G.Hero.Y-2.5,0,2.5,true}};
    }
    static void HeartBeforeContact(ZeldaGame& G) {
        G.Hero.X=150;G.Hero.Y=420;G.Hero.Health=1;G.Hero.Invincible=0;
        // Preserve the source ordering: a heart is collected before enemy contact damage.
        G.Enemies[1].X=150;G.Enemies[1].Y=420;
    }
};
}}

namespace {
int Checks=0,Failed=0;
void Check(bool Good,const char* What) {++Checks;if(!Good){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
bool SamePickups(const std::vector<ZeldaGame::Collectible>& A,const std::vector<ZeldaGame::Collectible>& B) {
    if(A.size()!=B.size()) return false;
    for(std::size_t N=0;N<A.size();++N)
        if(A[N].X!=B[N].X || A[N].Y!=B[N].Y || A[N].Kind!=B[N].Kind || A[N].Bob!=B[N].Bob) return false;
    return true;
}
bool SameState(ZeldaGame& A,ZeldaGame& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    return SameFrame(F,G) && S.Score==T.Score && S.Lives==T.Lives && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note
        && A.GetKeys()==B.GetKeys() && A.GetProjectiles().size()==B.GetProjectiles().size()
        && SamePickups(A.GetCollectibles(),B.GetCollectibles());
}
void LethalPickup(ZeldaGame::PickupKind Kind) {
    ZeldaGame G;G.Reset(730);MazeTestAccess::ProjectileAtPickup(G,Kind,1);
    const auto Pickups=G.GetCollectibles();const auto Score=G.GetStatus().Score;
    const int Rupees=G.GetPlayer().Rupees,Keys=G.GetKeys();
    G.Step({});
    Check(G.GetStatus().Over && !G.GetStatus().Won && G.GetPlayer().Health==0,"lethal rock settles defeat without same-step healing or victory");
    Check(G.GetProjectiles().empty(),"the impacting projectile is cleaned before the terminal return");
    Check(G.GetStatus().Score==Score && G.GetPlayer().Rupees==Rupees && G.GetKeys()==Keys,"no pickup score trinket or key is granted after defeat");
    Check(SamePickups(G.GetCollectibles(),Pickups),"defeat leaves every overlapping pickup untouched");
    ZeldaGame Frozen=G;
    Input Held;Held.Left=Held.Up=Held.Fire=Held.Action=Held.Jump=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(SameState(G,Frozen),"held terminal inputs cannot animate collect heal or replay");
    for(int Event=0;Event<3;++Event) {
        auto Retry=Frozen;Input Press;
        Press.FirePressed=Event==0;Press.ActionPressed=Event==1;Press.JumpPressed=Event==2;
        Retry.Step(Press);ZeldaGame Fresh;Fresh.Reset(730);
        Check(SameState(Retry,Fresh) && Retry.GetPlayer().Health==6,"fresh Fire Action or Jump completely replays the original seed");
        Input Move;Move.Right=true;
        for(int N=0;N<4;++N) {Retry.Step(Move);Fresh.Step(Move);}
        Check(SameState(Retry,Fresh),"replay preserves following native RNG and movement behavior");
    }
    G.Reset(730);ZeldaGame Fresh;Fresh.Reset(730);
    Check(SameState(G,Fresh),"explicit reset clears the defeated overlap and restores the original run");
}
void NonlethalPickup(ZeldaGame::PickupKind Kind) {
    ZeldaGame G;G.Reset(730);MazeTestAccess::ProjectileAtPickup(G,Kind,2);
    const auto Count=G.GetCollectibles().size();const auto Score=G.GetStatus().Score;
    G.Step({});
    Check(!G.GetStatus().Over && G.GetPlayer().Invincible==45 && G.GetProjectiles().empty(),"nonlethal rock retains normal damage grace and projectile cleanup");
    Check(G.GetCollectibles().size()+1==Count,"normal same-step pickup is still collected after surviving a rock");
    if(Kind==ZeldaGame::PickupKind::Heart)
        Check(G.GetPlayer().Health==3 && G.GetStatus().Score==Score,"surviving damage then the authored heart retains its healing order");
    else if(Kind==ZeldaGame::PickupKind::Rupee)
        Check(G.GetPlayer().Health==1 && G.GetPlayer().Rupees==1 && G.GetStatus().Score==Score+10,"surviving damage still grants the authored trinket exactly once");
    else
        Check(G.GetPlayer().Health==1 && G.GetKeys()==1 && G.GetStatus().Won,"surviving the final rock permits the normal key victory");
}
}

int main() {
    for(auto Kind:{ZeldaGame::PickupKind::Heart,ZeldaGame::PickupKind::Rupee,ZeldaGame::PickupKind::Key}) {
        LethalPickup(Kind);NonlethalPickup(Kind);
    }
    ZeldaGame G;G.Reset(730);MazeTestAccess::HeartBeforeContact(G);G.Step({});
    Check(!G.GetStatus().Over && G.GetPlayer().Health==2 && G.GetPlayer().Invincible==45,"heart-before-enemy-contact ordering remains unchanged");
    std::cout<<"Zelda terminal pickups: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
