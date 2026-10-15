// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <queue>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
namespace daedalus { namespace desktop {
// Controlled boundary-state injection only; gameplay users receive const snapshots.
struct MazeTestAccess {
    static void PacStackedGhosts(PacmanGame& G,bool Frightened) {
        for(auto& E:G.Ghosts) { E.X=G.Hero.X; E.Y=G.Hero.Y; E.Frightened=Frightened; E.FrightenedTimer=300; }
        for(auto& P:G.Pellets) P.Alive=false;
        G.Remaining=1;
    }
    static void PacIsolateCollectibles(PacmanGame& G) {
        for(auto& E:G.Ghosts) { E.X=-1000; E.Y=-1000; E.Alive=true; }
    }
    static void PacTerminal(PacmanGame& G) { G.Over=true; G.Score=999; G.Lives=0; G.Remaining=0; }
    static void ZeldaCombat(ZeldaGame& G) {
        G.Hero.Face=ZeldaGame::Facing::Right;
        for(auto& E:G.Enemies) { E.X=425; E.Y=450; E.ShootTimer=1000; }
        G.Collectibles.clear();
    }
    static void ZeldaPickups(ZeldaGame& G) {
        G.Hero.Health=5; G.Collectibles.clear();
        G.Collectibles.push_back({400,450,ZeldaGame::PickupKind::Heart,0});
        G.Collectibles.push_back({400,450,ZeldaGame::PickupKind::Rupee,0});
    }
    static void ZeldaDamage(ZeldaGame& G) {
        G.Projectiles={{400,450,0,0,true},{400,450,0,0,true}};
    }
    static void ZeldaCapacity(ZeldaGame& G) {
        G.Projectiles.assign(ZeldaGame::MaxProjectiles,{700,500,0,0,true});
        G.Enemies[0].ShootTimer=1; G.Enemies[3].ShootTimer=1;
    }
    static void ZeldaTerminal(ZeldaGame& G) { G.Over=true; G.Hero.Health=0; G.Score=777; }
};
}}

static int Checks=0, Failures=0, SourceCases=0;
static bool Near(double A,double B) { return std::abs(A-B)<1e-8; }
static void Check(const std::string& Name,bool Good) {
    ++Checks;
    if(!Good) { ++Failures; std::cerr << "FAIL " << Name << '\n'; }
}
static bool SameRect(const Rect& A,double X,double Y,double W,double H) {
    return Near(A.X,X)&&Near(A.Y,Y)&&Near(A.W,W)&&Near(A.H,H);
}

static void SourceFixture(const std::string& Filename) {
    std::ifstream File(Filename);
    if(!File) throw std::runtime_error("Cannot open maze fixture "+Filename);
    std::string Line;
    if(!std::getline(File,Line) || Line!="MAZE 1") throw std::runtime_error("Bad maze fixture header");
    while(std::getline(File,Line)) {
        if(Line.empty() || Line[0]=='#') continue;
        std::istringstream In(Line); std::string Kind,Name; In>>Kind;
        bool Good=false;
        if(Kind=="DUNGEON_ROW" || Kind=="PAC_ROW") {
            int Row=0; std::string Text; In>>Row>>Text;
            Good=Kind=="DUNGEON_ROW" ? std::string(DungeonGame::Map.at(static_cast<std::size_t>(Row)))==Text : std::string(PacmanGame::Map.at(static_cast<std::size_t>(Row)))==Text;
        } else if(Kind=="DUNGEON_WALL") {
            int X=0,Y=0,Wall=0; In>>X>>Y>>Wall;
            Good=DungeonGame::IsWall(X/40,Y/40)==(Wall!=0);
        } else if(Kind=="PAC_COLLISION") {
            double X=0,Y=0; int Collision=0; In>>X>>Y>>Collision;
            Good=PacmanGame::Collides(X,Y,false)==(Collision!=0);
        } else if(Kind=="PAC_PLAYER") {
            PacmanGame::Player Hero;
            int Left=0,Right=0,Up=0,Down=0,Steps=0,Ex=0,Ey=0,Enx=0,Eny=0,Emouth=0;
            double ExpectX=0,ExpectY=0; Input I;
            In>>Name>>Hero.X>>Hero.Y>>Hero.Dir.X>>Hero.Dir.Y>>Hero.Next.X>>Hero.Next.Y>>Hero.Mouth
              >>Left>>Right>>Up>>Down>>I.AxisX>>I.AxisY>>Steps>>ExpectX>>ExpectY>>Ex>>Ey>>Enx>>Eny>>Emouth;
            I.Left=Left!=0;I.Right=Right!=0;I.Up=Up!=0;I.Down=Down!=0;
            for(int N=0;N<Steps;++N) Hero.Update(I,false);
            Good=Near(Hero.X,ExpectX)&&Near(Hero.Y,ExpectY)&&Hero.Dir.X==Ex&&Hero.Dir.Y==Ey&&Hero.Next.X==Enx&&Hero.Next.Y==Eny&&Hero.Mouth==Emouth;
        } else if(Kind=="PAC_GHOST") {
            PacmanGame::Ghost Ghost; PacmanGame::Player Hero;
            int Alive=0,Frightened=0,EAlive=0,EFright=0,ETimer=0,Ex=0,Ey=0; double Turn=0,Chase=0,ExpectX=0,ExpectY=0;
            In>>Name>>Ghost.X>>Ghost.Y>>Ghost.Dir.X>>Ghost.Dir.Y>>Alive>>Frightened>>Ghost.FrightenedTimer>>Hero.X>>Hero.Y>>Turn>>Chase
              >>ExpectX>>ExpectY>>Ex>>Ey>>EAlive>>EFright>>ETimer;
            Ghost.Alive=Alive!=0;Ghost.Frightened=Frightened!=0;
            Ghost.UpdateWithChoices(Hero,Turn,Chase,{{{1,0},{-1,0},{0,1},{0,-1}}},false);
            Good=Near(Ghost.X,ExpectX)&&Near(Ghost.Y,ExpectY)&&Ghost.Dir.X==Ex&&Ghost.Dir.Y==Ey&&Ghost.Alive==(EAlive!=0)&&Ghost.Frightened==(EFright!=0)&&Ghost.FrightenedTimer==ETimer;
        } else if(Kind=="ZELDA_PLAYER") {
            ZeldaGame::Player Hero; Input I;
            int Face=0,Attacking=0,Left=0,Right=0,Up=0,Down=0,Steps=0,EFace=0,EAttack=0,EInv=0,EAttacking=0; double Ex=0,Ey=0;
            In>>Name>>Hero.X>>Hero.Y>>Face>>Hero.AttackTimer>>Hero.Invincible>>Attacking>>Left>>Right>>Up>>Down>>I.AxisX>>I.AxisY>>Steps
              >>Ex>>Ey>>EFace>>EAttack>>EInv>>EAttacking;
            Hero.Face=static_cast<ZeldaGame::Facing>(Face);Hero.Attacking=Attacking!=0;
            I.Left=Left!=0;I.Right=Right!=0;I.Up=Up!=0;I.Down=Down!=0;
            for(int N=0;N<Steps;++N) Hero.Update(I);
            Good=Near(Hero.X,Ex)&&Near(Hero.Y,Ey)&&static_cast<int>(Hero.Face)==EFace&&Hero.AttackTimer==EAttack&&Hero.Invincible==EInv&&Hero.Attacking==(EAttacking!=0);
        } else if(Kind=="ZELDA_ATTACK") {
            ZeldaGame::Player Hero; int Face=0,Success=0,ETimer=0,EAttacking=0; double X=0,Y=0,W=0,H=0;
            In>>Face>>Hero.AttackTimer>>Hero.X>>Hero.Y>>Success>>ETimer>>EAttacking>>X>>Y>>W>>H;
            Hero.Face=static_cast<ZeldaGame::Facing>(Face);
            const bool DidAttack=Hero.Attack();
            Good=DidAttack==(Success!=0)&&Hero.AttackTimer==ETimer&&Hero.Attacking==(EAttacking!=0)&&SameRect(Hero.GetAttackRect(),X,Y,W,H);
        } else if(Kind=="ZELDA_ENEMY") {
            ZeldaGame::Enemy Enemy; ZeldaGame::Player Hero; Random Rng; Rng.Seed(0x12345678u);
            int Type=0,EHealth=0,EShoot=0,EFlash=0,Shoot=0; double Ex=0,Ey=0;
            In>>Name>>Type>>Enemy.X>>Enemy.Y>>Hero.X>>Hero.Y>>Ex>>Ey>>EHealth>>EShoot>>EFlash>>Shoot;
            Enemy.Kind=static_cast<ZeldaGame::EnemyKind>(Type);Enemy.Health=Type==1 ? 2 : 1;Enemy.ShootTimer=60;Enemy.HitFlash=12;
            const bool DidShoot=Enemy.Update(Hero,Rng);
            Good=Near(Enemy.X,Ex)&&Near(Enemy.Y,Ey)&&Enemy.Health==EHealth&&Enemy.ShootTimer==EShoot&&Enemy.HitFlash==EFlash&&DidShoot==(Shoot!=0);
        } else if(Kind=="ZELDA_PROJECTILE") {
            ZeldaGame::Projectile P; double Ex=0,Ey=0,X=0,Y=0,W=0,H=0; int Alive=0;
            In>>P.X>>P.Y>>P.Dx>>P.Dy>>Ex>>Ey>>Alive>>X>>Y>>W>>H;P.Update();
            Good=Near(P.X,Ex)&&Near(P.Y,Ey)&&P.Alive==(Alive!=0)&&SameRect(P.GetRect(),X,Y,W,H);
        } else throw std::runtime_error("Unknown fixture "+Kind);
        Check("source "+Kind+" "+Name,Good && !In.fail());
        ++SourceCases;
    }
    Check("239 source cases loaded",SourceCases==239);
}

static bool ValidFrame(const Frame& F) {
    if(F.Width<=0 || F.Height<=0 || !std::isfinite(F.Width) || !std::isfinite(F.Height) || F.Commands.size()>Frame::MaxCommands) return false;
    for(const auto& C:F.Commands) if(!std::isfinite(C.A.X)||!std::isfinite(C.A.Y)||!std::isfinite(C.B.X)||!std::isfinite(C.B.Y)||!std::isfinite(C.C.X)||!std::isfinite(C.C.Y)||!std::isfinite(C.Size)) return false;
    return true;
}

static std::vector<maze::Direction> Route(int From,int To) {
    std::array<int,PacmanGame::Columns*PacmanGame::Rows> Prev;
    Prev.fill(-1);Prev[static_cast<std::size_t>(From)]=From;
    std::queue<int> Open;Open.push(From);
    while(!Open.empty() && Prev[static_cast<std::size_t>(To)]<0) {
        const int Here=Open.front();Open.pop();
        const int Col=Here%PacmanGame::Columns,Row=Here/PacmanGame::Columns;
        for(const auto D:std::array<maze::Direction,4>{{{1,0},{-1,0},{0,1},{0,-1}}}) {
            const int X=Col+D.X,Y=Row+D.Y;
            if(PacmanGame::IsWall(X,Y)) continue;
            const int Index=Y*PacmanGame::Columns+X;
            if(Prev[static_cast<std::size_t>(Index)]>=0) continue;
            Prev[static_cast<std::size_t>(Index)]=Here;Open.push(Index);
        }
    }
    if(Prev[static_cast<std::size_t>(To)]<0) throw std::runtime_error("Repaired Pac-Man map has unreachable dot");
    std::vector<maze::Direction> Result;
    for(int Here=To;Here!=From;) {
        const int Before=Prev[static_cast<std::size_t>(Here)];
        Result.push_back({Here%PacmanGame::Columns-Before%PacmanGame::Columns,Here/PacmanGame::Columns-Before/PacmanGame::Columns});
        Here=Before;
    }
    std::reverse(Result.begin(),Result.end());return Result;
}

static void NativeLifecycle() {
    DungeonGame Dungeon;Dungeon.Reset(1);Input Move;Move.Right=true;
    for(int N=0;N<100;++N) Dungeon.Step(Move);
    Check("Dungeon full box stops before source interior wall",Near(Dungeon.GetPlayer().X,80));
    Check("Dungeon ragged missing cell is solid",DungeonGame::IsWall(19,1)&&DungeonGame::IsWall(-1,1)&&DungeonGame::IsWall(1,7));
    Move={};Move.Down=true;for(int N=0;N<30;++N) Dungeon.Step(Move);
    Move={};Move.Right=true;for(int N=0;N<1000;++N) Dungeon.Step(Move);
    Check("Dungeon retains horizontal slide along accessible floor",Near(Dungeon.GetPlayer().X,680)&&Near(Dungeon.GetPlayer().Y,200));
    Check("Dungeon has no invented win condition",!Dungeon.GetStatus().Won&&!Dungeon.GetStatus().Over);
    Move={};Move.ActionPressed=true;Dungeon.Step(Move);
    Check("Dungeon reset restores source position",Near(Dungeon.GetPlayer().X,80)&&Near(Dungeon.GetPlayer().Y,80));

    PacmanGame Pac;Pac.Reset(10);
    Check("Pac source dots conserved with4 promoted pellets",Pac.DotsLeft()==304&&std::count_if(Pac.GetPellets().begin(),Pac.GetPellets().end(),[](const PacmanGame::Pellet& P){return P.Power;})==4);
    Check("Pac repaired spawn is on same source tile without overlap",Near(Pac.GetPlayer().X,290)&&Near(Pac.GetPlayer().Y,470)&&!PacmanGame::Collides(290,470));
    Check("Pac pen repair opens exactly one source wall",PacmanGame::IsWall(9,14,false)&&!PacmanGame::IsWall(9,14,true));
    MazeTestAccess::PacStackedGhosts(Pac,false);Pac.Step({});
    Check("Pac stacked ghosts cost one life per frame",Pac.GetStatus().Lives==2&&!Pac.GetStatus().Over);
    Pac.Reset(10);MazeTestAccess::PacStackedGhosts(Pac,true);Pac.Step({});
    Check("Pac4 frightened captures score800",Pac.GetStatus().Score==800&&Pac.GetStatus().Lives==3);
    Check("Pac all captured ghosts respawn together",std::all_of(Pac.GetGhosts().begin(),Pac.GetGhosts().end(),[](const PacmanGame::Ghost& G){return G.Alive&&Near(G.X,290)&&Near(G.Y,290);}));
    Pac.Reset(10);MazeTestAccess::PacIsolateCollectibles(Pac);
    int Here=23*PacmanGame::Columns+14;bool MovesGood=true;
    const auto Targets=Pac.GetPellets();
    // Full collection replay isolates movement/scoring from the separately tested ghost AI.
    for(const auto& Target:Targets) {
        if(Pac.GetStatus().Won) break;
        const int To=static_cast<int>(Target.Y)/20*PacmanGame::Columns+static_cast<int>(Target.X)/20;
        for(const auto D:Route(Here,To)) {
            Input I;I.Right=D.X>0;I.Left=D.X<0;I.Down=D.Y>0;I.Up=D.Y<0;
            Here+=D.Y*PacmanGame::Columns+D.X;
            for(int N=0;N<8;++N) Pac.Step(I);
            if(!Pac.GetStatus().Won && (!Near(Pac.GetPlayer().X,(Here%28)*20+10)||!Near(Pac.GetPlayer().Y,(Here/28)*20+10))) MovesGood=false;
        }
    }
    Check("Pac entire repaired map is navigable by native movement",MovesGood);
    Check("Pac full304-collectible replay wins once with exact3200 score",Pac.GetStatus().Won&&Pac.GetStatus().Score==3200&&Pac.DotsLeft()==0&&Pac.GetLevel()==2);
    const auto FinalScore=Pac.GetStatus().Score;for(int N=0;N<100;++N) Pac.Step({});
    Check("Pac victory freezes rules and scoring",Pac.GetStatus().Score==FinalScore&&Pac.GetLevel()==2);
    Input Restart;Restart.ActionPressed=true;Pac.Step(Restart);
    Check("Pac restart regenerates all dots and4 pellets",Pac.DotsLeft()==304&&Pac.GetStatus().Score==0&&Pac.GetStatus().Lives==3&&!Pac.GetStatus().Won);
    MazeTestAccess::PacTerminal(Pac);Input Held;Held.Action=true;Pac.Step(Held);
    Check("Pac held action does not restart without press",Pac.GetStatus().Over);
    Pac.Step(Restart);Check("Pac gameover restart clears terminal state",!Pac.GetStatus().Over&&Pac.GetStatus().Score==0);

    ZeldaGame Zelda;Zelda.Reset(20);
    Check("Zelda source4-enemy roster and health preserved",Zelda.GetEnemies().size()==4&&Zelda.GetEnemies()[0].Kind==ZeldaGame::EnemyKind::Octorok&&Zelda.GetEnemies()[1].Health==2&&Zelda.GetEnemies()[2].Kind==ZeldaGame::EnemyKind::Armos&&Zelda.GetEnemies()[3].Kind==ZeldaGame::EnemyKind::Octorok);
    MazeTestAccess::ZeldaPickups(Zelda);Zelda.Step({});
    Check("Zelda heart clamps at6 and rupee gives10 once",Zelda.GetPlayer().Health==6&&Zelda.GetPlayer().Rupees==1&&Zelda.GetStatus().Score==10&&Zelda.GetCollectibles().empty());
    Zelda.Step({});Check("Zelda collected item cannot reward again",Zelda.GetPlayer().Rupees==1&&Zelda.GetStatus().Score==10);
    Zelda.Reset(20);MazeTestAccess::ZeldaDamage(Zelda);Zelda.Step({});
    Check("Zelda simultaneous rocks cost one half-heart with45-frame invincibility",Zelda.GetPlayer().Health==5&&Zelda.GetPlayer().Invincible==45&&Zelda.GetProjectiles().size()==1);
    Zelda.Reset(20);MazeTestAccess::ZeldaCapacity(Zelda);Zelda.Step({});
    Check("Zelda rocks remain bounded under simultaneous shoot events",Zelda.GetProjectiles().size()==ZeldaGame::MaxProjectiles);
    Zelda.Reset(20);MazeTestAccess::ZeldaCombat(Zelda);Input Sword;Sword.FirePressed=true;Zelda.Step(Sword);
    Check("Zelda sword hits source roster immediately and moblin needs2 hits",std::count_if(Zelda.GetEnemies().begin(),Zelda.GetEnemies().end(),[](const ZeldaGame::Enemy& E){return E.Alive;})==1&&Zelda.GetEnemies()[1].Health==1&&Zelda.GetStatus().Score==150);
    Zelda.Step(Sword);Check("Zelda cooldown refuses duplicate immediate sword reward",Zelda.GetEnemies()[1].Health==1&&Zelda.GetStatus().Score==150);
    for(int N=0;N<16;++N) Zelda.Step({});
    Zelda.Step(Sword);
    Check("Zelda final enemy yields required key and reachable victory",Zelda.GetStatus().Won&&Zelda.GetKeys()==1&&Zelda.GetStatus().Score>=200&&std::all_of(Zelda.GetEnemies().begin(),Zelda.GetEnemies().end(),[](const ZeldaGame::Enemy& E){return !E.Alive;}));
    const auto VictoryScore=Zelda.GetStatus().Score;for(int N=0;N<1000;++N) Zelda.Step({});
    Check("Zelda victory stops enemy respawns and repeated rewards",Zelda.GetStatus().Score==VictoryScore&&Zelda.GetEnemies().size()==4&&Zelda.GetKeys()==1);
    Zelda.Step(Restart);Check("Zelda victory restart restores all lifecycle state",!Zelda.GetStatus().Won&&Zelda.GetStatus().Score==0&&Zelda.GetPlayer().Health==6&&Zelda.GetKeys()==0&&Zelda.GetProjectiles().empty()&&Zelda.GetCollectibles().size()==4);
    MazeTestAccess::ZeldaTerminal(Zelda);Zelda.Step(Held);Check("Zelda held action does not restart without press",Zelda.GetStatus().Over);
    Zelda.Step(Restart);Check("Zelda gameover restart restores health",!Zelda.GetStatus().Over&&Zelda.GetPlayer().Health==6);

    // Cycle1 retains the 280-pixel source room and adds a 64-pixel objective footer.
    Frame F;Dungeon.Render(F);Check("Dungeon source room plus objective footer is bounded finite",ValidFrame(F)&&F.Width==800&&F.Height==344);
    Pac.Render(F);Check("Pac frame fits whole620-pixel maze and HUD",ValidFrame(F)&&F.Width==800&&F.Height==660);
    Zelda.Render(F);Check("Zelda procedural world and source character frame is bounded finite",ValidFrame(F)&&F.Width==800&&F.Height==600);
    for(int Round=0;Round<16;++Round) {
        Pac.Reset(static_cast<std::uint32_t>(Round));Zelda.Reset(static_cast<std::uint32_t>(Round));Dungeon.Reset(static_cast<std::uint32_t>(Round));
        for(int N=0;N<3000;++N) {
            Input I;I.Left=N%240<60;I.Up=N%240>=60&&N%240<120;I.Right=N%240>=120&&N%240<180;I.Down=N%240>=180;
            I.FirePressed=N%19==0;I.AxisX=N%100==0 ? std::numeric_limits<double>::quiet_NaN() : 0;
            Dungeon.Step(I);Pac.Step(I);Zelda.Step(I);
        }
        Check("bounded long run seed"+std::to_string(Round),Zelda.GetProjectiles().size()<=ZeldaGame::MaxProjectiles&&Zelda.GetCollectibles().size()<=ZeldaGame::MaxCollectibles&&Zelda.GetEnemies().size()==4&&Pac.GetPellets().size()==304&&DungeonGame::Collides(Dungeon.GetPlayer().X,Dungeon.GetPlayer().Y)==false);
    }
}

int main(int argc,char** argv) {
    try {
        SourceFixture(argc>1 ? argv[1] : "maze_parity.txt");NativeLifecycle();
    } catch(const std::exception& E) { std::cerr<<E.what()<<'\n';return 1; }
    std::cout<<"Maze: "<<Checks-Failures<<'/'<<Checks<<" checks PASS ("<<SourceCases<<" pinned-source cases)\n";
    return Failures==0 ? 0 : 1;
}
