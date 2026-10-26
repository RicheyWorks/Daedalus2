// SPDX-License-Identifier: MIT
// Lanternwild viewing: a dark outline sits behind the hero so the tunic reads on the grass.
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void Toast(ZeldaGame& G) { G.Message="+1 Trinket"; G.MessageTimer=40; }
    static void DropKey(ZeldaGame& G) { G.AddPickup(400,240,ZeldaGame::PickupKind::Key); }
};
}}

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
    std::size_t Border=F.Commands.size(),Road=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Rectangle) continue;
        if(C.A.X==96 && C.A.Y==196 && C.B.X==608 && C.B.Y==88
            && C.Tint.R==120 && C.Tint.G==86 && C.Tint.B==48) Border=N;
        if(C.A.X==100 && C.A.Y==200 && C.B.X==600 && C.B.Y==80
            && C.Tint.R==210 && C.Tint.G==180 && C.Tint.B==140) Road=N;
    }
    Check(Border<Road && Road<F.Commands.size(),"the cross road keeps a dark border on the grass");
    std::size_t Shore=F.Commands.size(),Pond=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=610 || C.A.Y!=355) continue;
        if(C.Size==62 && C.Tint.R==12 && C.Tint.G==64 && C.Tint.B==28) Shore=N;
        if(C.Size==55 && C.Tint.R==30 && C.Tint.G==144 && C.Tint.B==255) Pond=N;
    }
    Check(Shore<Pond && Pond<F.Commands.size(),"the pond keeps a dark shore on the grass");
    std::size_t Wall=F.Commands.size(),Door=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Rectangle) continue;
        if(C.A.X==380 && C.A.Y==80 && C.B.X==40 && C.B.Y==50
            && C.Tint.R==60 && C.Tint.G==40 && C.Tint.B==20) Wall=N;
        if(C.A.X==394 && C.A.Y==104 && C.B.X==12 && C.B.Y==26
            && C.Tint.R==24 && C.Tint.G==16 && C.Tint.B==8) Door=N;
    }
    Check(Wall<Door && Door<F.Commands.size(),"the cabin keeps a door on its wall");
    std::size_t Plate=F.Commands.size(),Hint=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle && C.A.X==0 && C.A.Y==70 && C.B.X==800 && C.B.Y==26
            && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) Plate=N;
        if(C.Kind==Shape::Text && C.A.Y==78 && C.Label.rfind("HINT",0)==0) Hint=N;
    }
    Check(Plate<Hint && Hint<F.Commands.size(),"the hint sits on a dark plate over the trees");
    std::size_t Status=F.Commands.size(),Health=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle && C.A.X==0 && C.A.Y==4 && C.B.X==800 && C.B.Y==48
            && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) Status=N;
        if(C.Kind==Shape::Text && C.A.Y==10 && C.Label.rfind("HEALTH",0)==0) Health=N;
    }
    Check(Status<Health && Health<F.Commands.size(),"health and the objective sit on a dark plate over the trees");
    std::size_t Footer=F.Commands.size(),Score=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle && C.A.X==0 && C.A.Y==552 && C.B.X==800 && C.B.Y==48
            && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) Footer=N;
        if(C.Kind==Shape::Text && C.A.Y==559 && C.Label.rfind("SCORE",0)==0) Score=N;
    }
    Check(Footer<Score && Score<F.Commands.size(),"the score sits on a dark plate on the grass");
    const auto& Hero=G.GetPlayer();
    std::size_t Sheath=F.Commands.size(),Blade=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Rectangle) continue;
        if(C.A.X==Hero.X-7 && C.A.Y==Hero.Y-3 && C.B.X==14 && C.B.Y==10
            && C.Tint.R==24 && C.Tint.G==28 && C.Tint.B==40) Sheath=N;
        if(C.A.X==Hero.X-6 && C.A.Y==Hero.Y-2 && C.B.X==12 && C.B.Y==8
            && C.Tint.R==180 && C.Tint.G==180 && C.Tint.B==200) Blade=N;
    }
    Check(Sheath<Blade && Blade<F.Commands.size(),"the sheathed sword keeps a dark edge on the road");
    std::size_t Brim=F.Commands.size(),Cap=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Triangle || C.B.X!=P.X) continue;
        if(C.A.X==P.X-10 && C.A.Y==P.Y-16 && C.B.Y==P.Y-32
            && C.Tint.R==12 && C.Tint.G==40 && C.Tint.B==12) Brim=N;
        if(C.A.X==P.X-8 && C.A.Y==P.Y-16 && C.B.Y==P.Y-28
            && C.Tint.R==50 && C.Tint.G==150 && C.Tint.B==50) Cap=N;
    }
    Check(Brim<Cap && Cap<F.Commands.size(),"hat keeps a dark brim on the grass");
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
    bool Trunk=false;
    for(const auto& C:F.Commands)
        if(C.Kind==Shape::Rectangle && C.A.X==38 && C.A.Y==85 && C.B.X==24 && C.B.Y==30
            && C.Tint.R==92 && C.Tint.G==58 && C.Tint.B==24) Trunk=true;
    Check(Trunk,"tree trunks are wood-colored on the grass");
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
        std::size_t Haft=F.Commands.size(),Gold=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Triangle || (C.A.Y!=Moblin->Y-10 && C.A.Y!=Moblin->Y-8)) continue;
            if(C.A.X==Moblin->X-11 && C.A.Y==Moblin->Y-10 && C.B.X==Moblin->X-22
                && C.Tint.R==48 && C.Tint.G==32 && C.Tint.B==12) Haft=N;
            if(C.A.X==Moblin->X-12 && C.A.Y==Moblin->Y-8 && C.B.X==Moblin->X-18
                && C.Tint.R==255 && C.Tint.G==200 && C.Tint.B==50) Gold=N;
        }
        Check(Haft<Gold && Gold<F.Commands.size(),"the moblin spear keeps a dark edge on the road");
        std::size_t FaceRim=F.Commands.size(),Face=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Circle || C.A.X!=Moblin->X || C.A.Y!=Moblin->Y-12) continue;
            if(C.Size==9 && C.Tint.R==48 && C.Tint.G==32 && C.Tint.B==16) FaceRim=N;
            if(C.Size==7 && C.Tint.R==200 && C.Tint.G==180 && C.Tint.B==150) Face=N;
        }
        Check(FaceRim<Face && Face<F.Commands.size(),"the moblin face keeps a dark rim on the road");
        std::size_t HpPlate=F.Commands.size(),Hp=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind==Shape::Rectangle && C.A.X==Moblin->X-18 && C.A.Y==Moblin->Y-36 && C.B.X==40 && C.B.Y==16
                && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) HpPlate=N;
            if(C.Kind==Shape::Text && C.Label.rfind("HP ",0)==0 && C.A.X==Moblin->X-15) Hp=N;
        }
        Check(HpPlate<Hp && Hp<F.Commands.size(),"the moblin health line sits on a dark plate");
    }
    const ZeldaGame::Enemy* Octo=nullptr;
    for(const auto& E:G.GetEnemies()) if(E.Kind==ZeldaGame::EnemyKind::Octorok && E.Alive && E.X>600) Octo=&E;
    Check(Octo!=nullptr,"an octorok stands in the pond");
    if(Octo) {
        std::size_t OctoRim=F.Commands.size(),OctoBody=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Circle || C.A.X!=Octo->X || C.A.Y!=Octo->Y) continue;
            if(C.Size==12 && C.Tint.R==48 && C.Tint.G==12 && C.Tint.B==16) OctoRim=N;
            if(C.Size==10 && C.Tint.R==200 && C.Tint.G==50 && C.Tint.B==50) OctoBody=N;
        }
        Check(OctoRim<OctoBody && OctoBody<F.Commands.size(),"the pond octorok keeps a dark rim on the water");
        std::size_t EyeWhite=F.Commands.size(),EyeDot=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Circle || C.A.X!=Octo->X-4 || C.A.Y!=Octo->Y-2) continue;
            if(C.Size==3 && C.Tint.R==255 && C.Tint.G==255 && C.Tint.B==255) EyeWhite=N;
            if(C.Size==2 && C.Tint.R==0 && C.Tint.G==0 && C.Tint.B==0) EyeDot=N;
        }
        Check(EyeWhite<EyeDot && EyeDot<F.Commands.size(),"the octorok pupil is large enough to see");
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
        std::size_t EyeRim=F.Commands.size(),Eye=F.Commands.size();
        for(std::size_t N=0;N<F.Commands.size();++N) {
            const auto& C=F.Commands[N];
            if(C.Kind!=Shape::Circle || C.A.X!=Armos->X || C.A.Y!=Armos->Y-4) continue;
            if(C.Size==7 && C.Tint.R==24 && C.Tint.G==24 && C.Tint.B==24) EyeRim=N;
            if(C.Size==5 && C.Tint.R==220 && C.Tint.G==220 && C.Tint.B==220) Eye=N;
        }
        Check(EyeRim<Eye && Eye<F.Commands.size(),"the armos eye keeps a dark ring on the stone");
    }
}
void Rupee() {
    ZeldaGame G;
    const ZeldaGame::Collectible* Gem=nullptr;
    for(const auto& C:G.GetCollectibles()) if(C.Kind==ZeldaGame::PickupKind::Rupee) { Gem=&C; break; }
    Check(Gem!=nullptr,"a trinket is on the fresh board");
    if(!Gem) return;
    const double Y=Gem->Y+std::sin(Gem->Bob)*3;
    Frame F;G.Render(F);
    std::size_t Edge=F.Commands.size(),GemTop=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Triangle || C.A.X!=Gem->X) continue;
        if(C.A.Y==Y-10 && C.Tint.R==12 && C.Tint.G==40 && C.Tint.B==12) Edge=N;
        if(C.A.Y==Y-8 && C.Tint.R==50 && C.Tint.G==200 && C.Tint.B==100) GemTop=N;
    }
    Check(Edge<GemTop && GemTop<F.Commands.size(),"trinket keeps a dark edge on the grass");
}
void Heart() {
    ZeldaGame G;
    const ZeldaGame::Collectible* Beat=nullptr;
    for(const auto& C:G.GetCollectibles()) if(C.Kind==ZeldaGame::PickupKind::Heart) { Beat=&C; break; }
    Check(Beat!=nullptr,"a heart is on the fresh board");
    if(!Beat) return;
    const double Y=Beat->Y+std::sin(Beat->Bob)*3;
    Frame F;G.Render(F);
    std::size_t Rim=F.Commands.size(),Lobe=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=Beat->X-4 || C.A.Y!=Y-3) continue;
        if(C.Size==7 && C.Tint.R==80 && C.Tint.G==12 && C.Tint.B==16) Rim=N;
        if(C.Size==5 && C.Tint.R==255 && C.Tint.G==50 && C.Tint.B==50) Lobe=N;
    }
    Check(Rim<Lobe && Lobe<F.Commands.size(),"the heart keeps a dark edge on the grass");
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
void Swing() {
    ZeldaGame G;
    Input Fire;Fire.FirePressed=true;G.Step(Fire);
    Check(G.GetPlayer().Attacking,"a fire press shows the swing");
    const auto& P=G.GetPlayer();
    Frame F;G.Render(F);
    std::size_t Shade=F.Commands.size(),Steel=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Line || C.A.X!=P.X || C.A.Y!=P.Y+12 || C.B.X!=P.X || C.B.Y!=P.Y+32) continue;
        if(C.Size==6 && C.Tint.R==24 && C.Tint.G==28 && C.Tint.B==40) Shade=N;
        if(C.Size==4 && C.Tint.R==200 && C.Tint.G==200 && C.Tint.B==220) Steel=N;
    }
    Check(Shade<Steel && Steel<F.Commands.size(),"the swing keeps a dark edge on the road");
}
void Toast() {
    ZeldaGame G;
    MazeTestAccess::Toast(G);
    Frame F;G.Render(F);
    std::size_t Plate=F.Commands.size(),Line=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle && C.A.X==280 && C.A.Y==50 && C.B.X==280 && C.B.Y==28
            && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) Plate=N;
        if(C.Kind==Shape::Text && C.Label=="+1 Trinket") Line=N;
    }
    Check(Plate<Line && Line<F.Commands.size(),"a pickup message sits on a dark plate over the trees");
}
void Key() {
    ZeldaGame G;
    MazeTestAccess::DropKey(G);
    Check(!G.GetCollectibles().empty(),"a dropped key is on the board");
    if(G.GetCollectibles().empty()) return;
    const auto& K=G.GetCollectibles().back();
    const double Y=K.Y+std::sin(K.Bob)*3;
    Frame F;G.Render(F);
    std::size_t Rim=F.Commands.size(),Bow=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind!=Shape::Circle || C.A.X!=K.X || C.A.Y!=Y) continue;
        if(C.Size==8 && C.Tint.R==24 && C.Tint.G==28 && C.Tint.B==16) Rim=N;
        if(C.Size==6 && C.Tint.R==255 && C.Tint.G==215 && C.Tint.B==0) Bow=N;
    }
    Check(Rim<Bow && Bow<F.Commands.size(),"the key keeps a dark rim on the road");
    std::size_t TagPlate=F.Commands.size(),Tag=F.Commands.size();
    for(std::size_t N=0;N<F.Commands.size();++N) {
        const auto& C=F.Commands[N];
        if(C.Kind==Shape::Rectangle && C.A.X==K.X-12 && C.A.Y==Y+8 && C.B.X==34 && C.B.Y==16
            && C.Tint.R==8 && C.Tint.G==36 && C.Tint.B==16) TagPlate=N;
        if(C.Kind==Shape::Text && C.Label=="KEY" && C.A.X==K.X-10) Tag=N;
    }
    Check(TagPlate<Tag && Tag<F.Commands.size(),"the key label sits on a dark plate");
}
}

int main() {
    try { View();Rupee();Heart();Shot();Swing();Toast();Key(); }
    catch(const std::exception& E) { std::cerr<<"EX "<<E.what()<<'\n';return 1; }
    if(Failed) { std::cerr<<Failed<<" failed of "<<Checks<<'\n';return 1; }
    std::cout<<Checks<<" checks passed\n";
    return 0;
}
