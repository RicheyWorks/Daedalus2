// SPDX-License-Identifier: MIT
// Lanternwild viewing: a dark outline sits behind the hero so the tunic reads on the grass.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Outline(const DrawCommand& C,const ZeldaGame::Player& P) {
    return C.Kind==Shape::Rectangle && C.A.X==P.X-10 && C.A.Y==P.Y-6 && C.B.X==20 && C.B.Y==24
        && C.Tint.R==12 && C.Tint.G==40 && C.Tint.B==12;
}
bool Tunic(const DrawCommand& C,const ZeldaGame::Player& P) {
    return C.Kind==Shape::Rectangle && C.A.X==P.X-8 && C.A.Y==P.Y-4 && C.B.X==16 && C.B.Y==20
        && C.Tint.R==50 && C.Tint.G==150 && C.Tint.B==50;
}
void View() {
    ZeldaGame G;
    const auto Note=G.GetStatus().Note;
    Frame F;G.Render(F);
    Check(G.GetStatus().Note==Note,"view render leaves status unchanged");
    const auto& P=G.GetPlayer();
    std::size_t Rim=F.Commands.size(),Body=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        if(Outline(F.Commands[N],P)) Rim=N;
        if(Tunic(F.Commands[N],P)) Body=N;
    }
    Check(Rim<Body && Body<F.Commands.size(),"dark outline draws behind the tunic");
    std::size_t RockRim=F.Commands.size(),Rock=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=200 || C.A.Y!=150) continue;
        if(C.Size==16 && C.Tint.R==24 && C.Tint.G==24 && C.Tint.B==24) RockRim=N;
        if(C.Size==14 && C.Tint.R==128 && C.Tint.G==128 && C.Tint.B==128) Rock=N;
    }
    Check(RockRim<Rock && Rock<F.Commands.size(),"rock keeps a dark rim on the grass");
    std::size_t Edge=F.Commands.size(),Canopy=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Triangle || C.A.X!=50) continue;
        if(C.A.Y==52 && C.Tint.R==170 && C.Tint.G==220 && C.Tint.B==90) Edge=N;
        if(C.A.Y==55 && C.Tint.R==0 && C.Tint.G==100 && C.Tint.B==0) Canopy=N;
    }
    Check(Edge<Canopy && Canopy<F.Commands.size(),"tree canopy keeps a light edge on the grass");
    const ZeldaGame::Enemy* Moblin=nullptr;
    for(const auto& E:G.GetEnemies()) if(E.Kind==ZeldaGame::EnemyKind::Moblin && E.Alive) Moblin=&E;
    Check(Moblin!=nullptr,"a living moblin is on the fresh board");
    if(Moblin) {
        std::size_t Shade=F.Commands.size(),Coat=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Rectangle) continue;
            if(C.A.X==Moblin->X-12 && C.A.Y==Moblin->Y-14 && C.B.X==24 && C.B.Y==28
                && C.Tint.R==16 && C.Tint.G==36 && C.Tint.B==16) Shade=N;
            if(C.A.X==Moblin->X-10 && C.A.Y==Moblin->Y-12 && C.B.X==20 && C.B.Y==24
                && C.Tint.R==80 && C.Tint.G==120 && C.Tint.B==80) Coat=N;
        }
        Check(Shade<Coat && Coat<F.Commands.size(),"moblin keeps a dark body behind the green tunic");
    }
    const ZeldaGame::Enemy* Armos=nullptr;
    for(const auto& E:G.GetEnemies()) if(E.Kind==ZeldaGame::EnemyKind::Armos && E.Alive) Armos=&E;
    Check(Armos!=nullptr,"a living armos is on the fresh board");
    if(Armos) {
        std::size_t Shade=F.Commands.size(),Stone=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Rectangle) continue;
            if(C.A.X==Armos->X-14 && C.A.Y==Armos->Y-16 && C.B.X==28 && C.B.Y==32
                && C.Tint.R==24 && C.Tint.G==24 && C.Tint.B==24) Shade=N;
            if(C.A.X==Armos->X-12 && C.A.Y==Armos->Y-14 && C.B.X==24 && C.B.Y==28
                && C.Tint.R==128 && C.Tint.G==128 && C.Tint.B==128) Stone=N;
        }
        Check(Shade<Stone && Stone<F.Commands.size(),"armos keeps a dark rim behind the gray stone");
    }
}
void Shot() {
    ZeldaGame G;
    for(int N=0;N<160 && G.GetProjectiles().empty();++N) G.Step({});
    Check(!G.GetProjectiles().empty(),"an enemy shot appears before the octorok timer runs out");
    if(G.GetProjectiles().empty()) return;
    const auto& S=G.GetProjectiles().front();
    Frame F;G.Render(F);
    std::size_t Rim=F.Commands.size(),Stone=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=S.X || C.A.Y!=S.Y) continue;
        if(C.Size==7 && C.Tint.R==24 && C.Tint.G==24 && C.Tint.B==24) Rim=N;
        if(C.Size==5 && C.Tint.R==128 && C.Tint.G==128 && C.Tint.B==128) Stone=N;
    }
    Check(Rim<Stone && Stone<F.Commands.size(),"enemy shot keeps a dark rim on the grass");
}
}

int main() {
    try { View();Shot(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
