// SPDX-License-Identifier: MIT
// Observable regression boundaries for the native polish passes. No Unreal,
// Python, external fixtures, services, or wall-clock timers are required.
#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include "DesktopGames/DaedalusDesktopPlatformersCore.h"
#include "DesktopGames/DaedalusDesktopPongCore.h"
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include "DesktopGames/DaedalusDesktopSportsCore.h"
#include <iostream>
#include <queue>
#include <stdexcept>

using namespace daedalus::desktop;

// The same existing friend seams as the family suites, scoped to this executable.
// Inject adversarial boundary states; exercise transitions only through Step.
namespace daedalus { namespace desktop {
struct MazeTestAccess {
    static void PacContact(PacmanGame& G,bool Frightened=false,bool Power=false) {
        G.Hero.X=290;G.Hero.Y=470;G.Hero.Dir={};G.Hero.Next={};
        G.Pellets={{30,30,false,true}};G.Remaining=1;
        if(Power) {G.Pellets.push_back({290,470,true,true});++G.Remaining;}
        for(auto& E:G.Ghosts) {E.X=30;E.Y=30;E.Dir={};E.Alive=true;E.Frightened=false;E.FrightenedTimer=0;}
        G.Ghosts[0].X=290;G.Ghosts[0].Y=470;
        G.Ghosts[0].Frightened=Frightened;G.Ghosts[0].FrightenedTimer=Frightened?300:0;
    }
    static void PacStack(PacmanGame& G) {
        PacContact(G);for(auto& E:G.Ghosts) {E.X=290;E.Y=470;}
    }
    static void PacTerminal(PacmanGame& G) {G.Over=true;G.Lives=0;G.Score=777;}
    static void PacLastDot(PacmanGame& G) {
        PacContact(G);for(auto& E:G.Ghosts) {E.X=30;E.Y=30;}
        G.Pellets={{290,470,false,true}};G.Remaining=1;
    }
    static void ZeldaLastEnemy(ZeldaGame& G) {
        G.Hero={};G.Hero.Face=ZeldaGame::Facing::Right;G.Collectibles.clear();G.Projectiles.clear();
        for(auto& E:G.Enemies) E.Alive=false;
        G.Enemies[0]={425,450,ZeldaGame::EnemyKind::Octorok,1,1000,0,true};
    }
    static void ZeldaProjectile(ZeldaGame& G,int Grace,int Health=6) {
        G.Hero={};G.Hero.Invincible=Grace;G.Hero.Health=Health;
        G.Projectiles={{400,450,0,0,true},{400,450,0,0,true}};G.Collectibles.clear();
        for(auto& E:G.Enemies) E.Alive=false;
        G.Enemies[0]={100,100,ZeldaGame::EnemyKind::Octorok,1,1000,0,true};
    }
};
namespace platformers {
struct TestAccess {
    static void ContraClear(ContraGame& G) {
        G.Enemies.clear();G.Bullets.clear();G.EnemyBullets.clear();G.Powerups.clear();G.Particles.clear();
        G.Player.Y=472;G.Player.VY=0;G.Player.OnGround=true;G.Player.Invincible=100;
    }
    static void ContraAtFinish(ContraGame& G) {ContraClear(G);G.Player.X=2800;}
    static void ContraSpreadCap(ContraGame& G,std::size_t Count,int Timer=100) {
        ContraClear(G);G.Player.Spread=true;G.Player.SpreadTimer=Timer;G.Player.Cooldown=0;
        G.Bullets.assign(Count,{100,100,0,0,60});
    }
    static void ContraRapid(ContraGame& G) {ContraClear(G);G.Powerups={{G.Player.X,G.Player.Y,0,true}};}
    static void NinjaBossState(ShadowNinjaGame& G,int Timer,double PlayerX=175,int Grace=0,int Health=5) {
        G.Player={};G.Player.X=PlayerX;G.Player.Invincible=Grace;G.Player.Health=Health;
        G.Boss={600,380,0,25,Timer};G.BossActive=true;G.Attacks.clear();G.Enemies.clear();G.Gold.clear();G.SpawnTimer=100000;
    }
    static void NinjaQuiet(ShadowNinjaGame& G) {
        G.Enemies.clear();G.Gold.clear();G.Attacks.clear();G.SpawnTimer=100000;
    }
    static void NinjaAttackCap(ShadowNinjaGame& G) {
        NinjaQuiet(G);G.Attacks.assign(64,{700,100,1,100,true,0});
    }
    static void NinjaFatalEnemyBeforePulse(ShadowNinjaGame& G) {
        NinjaBossState(G,1,175,0,1);G.Enemies={{175,380,0,0,2,false}};
    }
};
}
}}

namespace {
int Checks=0,Failures=0;
void Check(bool Ok,const std::string& Message) {
    ++Checks;if(!Ok) {++Failures;std::cerr<<"FAIL "<<Message<<'\n';}
}
bool Near(double A,double B) {return std::isfinite(A)&&std::isfinite(B)&&std::abs(A-B)<1e-8;}
bool Has(const std::string& Text,const std::string& Part) {return Text.find(Part)!=std::string::npos;}
bool HasText(const Frame& F,const std::string& Part) {
    return std::any_of(F.Commands.begin(),F.Commands.end(),[&](const DrawCommand& C){return C.Kind==Shape::Text&&Has(C.Label,Part);});
}
Frame Draw(const Game& G) {Frame F;G.Render(F);return F;}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width||A.Height!=B.Height||A.Commands.size()!=B.Commands.size()) return false;
    const auto SameColor=[](Color X,Color Y){return X.R==Y.R&&X.G==Y.G&&X.B==Y.B&&X.A==Y.A;};
    if(!SameColor(A.Background,B.Background)) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& X=A.Commands[N];const auto& Y=B.Commands[N];
        if(X.Kind!=Y.Kind||X.A.X!=Y.A.X||X.A.Y!=Y.A.Y||X.B.X!=Y.B.X||X.B.Y!=Y.B.Y||X.C.X!=Y.C.X||X.C.Y!=Y.C.Y||
           X.Size!=Y.Size||X.Label!=Y.Label||!SameColor(X.Tint,Y.Tint)) return false;
    }
    return true;
}
bool FiniteFrame(const Frame& F) {
    if(F.Width<=0||F.Height<=0||!std::isfinite(F.Width)||!std::isfinite(F.Height)||F.Commands.empty()||F.Commands.size()>Frame::MaxCommands) return false;
    for(const auto& C:F.Commands) if(!std::isfinite(C.A.X)||!std::isfinite(C.A.Y)||!std::isfinite(C.B.X)||!std::isfinite(C.B.Y)||
        !std::isfinite(C.C.X)||!std::isfinite(C.C.Y)||!std::isfinite(C.Size)||C.Label.size()>256) return false;
    return true;
}
Input FreshFire() {Input I;I.FirePressed=true;return I;}
Input FreshAction() {Input I;I.ActionPressed=true;return I;}
Input FreshJump() {Input I;I.JumpPressed=true;return I;}

void WalkDungeon(DungeonGame& G,Vec Target) {
    // BFS over real 40-pixel player footprints. Every edge is eight public
    // 5-pixel Steps; no core state or mutable player reference is exposed.
    constexpr int Cells=DungeonGame::Columns*DungeonGame::Rows;
    std::array<int,Cells> Prev;Prev.fill(-1);
    const int From=static_cast<int>(G.GetPlayer().Y/40)*DungeonGame::Columns+static_cast<int>(G.GetPlayer().X/40);
    const int To=static_cast<int>(Target.Y/40)*DungeonGame::Columns+static_cast<int>(Target.X/40);
    std::queue<int> Open;Open.push(From);Prev[static_cast<std::size_t>(From)]=From;
    while(!Open.empty()&&Prev[static_cast<std::size_t>(To)]<0) {
        const int Here=Open.front();Open.pop();const int X=Here%DungeonGame::Columns,Y=Here/DungeonGame::Columns;
        for(const auto D:std::array<maze::Direction,4>{{{1,0},{-1,0},{0,1},{0,-1}}}) {
            const int Nx=X+D.X,Ny=Y+D.Y;
            if(Nx<0||Nx>=DungeonGame::Columns||Ny<0||Ny>=DungeonGame::Rows||DungeonGame::Collides(Nx*40,Ny*40)) continue;
            const int Next=Ny*DungeonGame::Columns+Nx;
            if(Prev[static_cast<std::size_t>(Next)]>=0) continue;
            Prev[static_cast<std::size_t>(Next)]=Here;Open.push(Next);
        }
    }
    if(Prev[static_cast<std::size_t>(To)]<0) throw std::runtime_error("Dungeon objective has no traversable player-footprint route");
    std::vector<int> Path;for(int N=To;N!=From;N=Prev[static_cast<std::size_t>(N)]) Path.push_back(N);
    std::reverse(Path.begin(),Path.end());int Here=From;
    for(const int Next:Path) {
        Input I;I.PadRight=Next%DungeonGame::Columns>Here%DungeonGame::Columns;I.PadLeft=Next%DungeonGame::Columns<Here%DungeonGame::Columns;
        I.PadDown=Next/DungeonGame::Columns>Here/DungeonGame::Columns;I.PadUp=Next/DungeonGame::Columns<Here/DungeonGame::Columns;
        for(int N=0;N<8;++N) G.Step(I);
        Here=Next;
    }
    Check(Near(G.GetPlayer().X,Target.X)&&Near(G.GetPlayer().Y,Target.Y),"Dungeon route arrives using public D-pad movement");
}
void DungeonPolicies() {
    DungeonGame G;G.Reset(0);G.Step({});Check(G.GetElapsedFrames()==0,"Dungeon idle does not start its run clock");
    WalkDungeon(G,{640,120});G.Step(FreshFire());
    Check(G.GetLitCount()==0&&Has(G.GetStatus().Note,"Not yet"),"Dungeon wrong order rejects without losing progress");
    WalkDungeon(G,{120,40});G.Step(FreshFire());Check(G.GetLitCount()==1,"Dungeon seed zero starts at Hall");
    Input Held;Held.Fire=true;G.Step(Held);Check(G.GetLitCount()==1,"Dungeon held interaction cannot light another objective");
    G.Step(FreshJump());Check(G.GetLitCount()==1&&Has(G.GetStatus().Note,"already lit"),"Dungeon already-lit feedback preserves progress");
    WalkDungeon(G,{640,120});G.Step(FreshJump());WalkDungeon(G,{360,200});G.Step(FreshFire());
    Check(G.GetLitCount()==3&&G.GetCircuitStage()==DungeonGame::CircuitStage::ExitUnlocked&&!G.GetStatus().Over,"Dungeon three ordered lanterns unlock but do not finish");
    WalkDungeon(G,{40,200});G.Step(FreshFire());const Frame Finished=Draw(G);const auto Elapsed=G.GetElapsedFrames();
    Check(G.GetStatus().Over&&G.GetStatus().Won&&G.GetStatus().Score==0,"Dungeon exit produces local completion without invented score");
    Input Move;Move.Right=true;Move.Fire=true;for(int N=0;N<12;++N) G.Step(Move);
    Check(SameFrame(Finished,Draw(G))&&G.GetElapsedFrames()==Elapsed,"Dungeon completion freezes movement, notice and elapsed time");
    G.Step(FreshAction());Check(!G.GetStatus().Over&&G.GetLitCount()==0&&G.GetElapsedFrames()==0&&Near(G.GetPlayer().X,80),"Dungeon deliberate Action clears complete run");
    for(std::uint32_t Seed=0;Seed<6;++Seed) {
        G.Reset(Seed);
        for(const int Lantern:DungeonGame::Routes[Seed]) {const Vec P=DungeonGame::Lanterns[static_cast<std::size_t>(Lantern)];WalkDungeon(G,{P.X-20,P.Y-20});G.Step(FreshFire());}
        WalkDungeon(G,{40,200});G.Step(FreshFire());Check(G.GetStatus().Won,"Dungeon all six seeded orders have a playable exit route");
    }
}
void PongPolicies() {
    PongGame G;G.Reset(0);Check(Draw(G).Commands.size()==6,"Pong retains its original opening frame");
    G.S.BallX=61;G.S.BallY=300;G.S.BallVX=-5;G.Step({});
    Check(G.S.Rally==1&&G.S.BestRally==1&&G.S.ContactFrames==8&&G.S.BallVX==5,"Pong real paddle contact records one rally return");
    G.S.BallX=739;G.S.BallY=300;G.Step({});Check(G.S.Rally==2&&G.S.BestRally==2,"Pong other paddle advances same rally");
    G.S.BallX=799;G.S.BallVX=5;G.Step({});
    Check(G.S.PlayerScore==1&&G.S.ServeFrames==45&&Near(G.S.BallX,400)&&G.S.Rally==0&&G.S.BestRally==2,"Pong point resets rally and starts 45-step serve preparation");
    Check(HasText(Draw(G),"Your point")&&Has(G.GetStatus().Note,"serves early"),"Pong point and serve feedback follow actual score");
    Input Held;Held.Fire=true;Held.PadUp=true;const double BeforeY=G.S.PlayerY;
    for(int N=0;N<45;++N) G.Step(Held);
    Check(G.S.ServeFrames==0&&Near(G.S.BallX,400)&&G.S.PlayerY<BeforeY,"Pong held button waits all 45 steps while paddles remain live");
    G.Step({});Check(Near(G.S.BallX,395),"Pong timed serve launches on the following step");
    G.S.BallX=-1;G.S.BallVX=-5;G.Step({});G.Step(FreshAction());
    Check(G.S.ServeFrames==0&&Near(G.S.BallX,400),"Pong fresh Action ends preparation without moving ball on that step");
    G.Step({});Check(Near(G.S.BallX,405),"Pong early serve launches next step with source direction");
    G.Reset(9);Check(G.S.BestRally==0&&G.S.PointFrames==0&&G.S.ServeFrames==0,"Pong reset clears feedback and session best");
}
void PacmanPolicies() {
    PacmanGame G;G.Reset(7);MazeTestAccess::PacStack(G);G.Step({});
    Check(G.GetStatus().Lives==2&&G.RespawnFramesRemaining()==90,"Pac-Man stacked ghosts consume one life and arm 90 subsequent steps");
    Check(HasText(Draw(G),"Respawn grace: 90")&&Has(G.GetStatus().Note,"90 steps"),"Pac-Man grace is visible in frame and status");
    bool Protected=true;for(int N=1;N<=90;++N) {
        MazeTestAccess::PacContact(G);G.Step({});Protected=Protected&&G.GetStatus().Lives==2&&G.RespawnFramesRemaining()==90-N;
    }
    Check(Protected,"Pac-Man all 90 subsequent lethal overlaps remain protected including countdown-zero frame");
    MazeTestAccess::PacContact(G);G.Step({});Check(G.GetStatus().Lives==1&&G.RespawnFramesRemaining()==90,"Pac-Man 91st overlap can take the next life");
    for(int N=0;N<90;++N) {MazeTestAccess::PacContact(G);G.Step({});}
    MazeTestAccess::PacContact(G);G.Step({});
    Check(G.GetStatus().Over&&G.GetStatus().Lives==0&&G.RespawnFramesRemaining()==0&&!HasText(Draw(G),"Respawn grace"),"Pac-Man final actual death ends run without a new grace period");
    G.Reset(7);MazeTestAccess::PacContact(G);G.Step({});MazeTestAccess::PacContact(G,true,true);G.Step({});
    Check(G.GetStatus().Lives==2&&G.GetStatus().Score==250&&!G.GetGhosts()[0].Alive&&G.DotsLeft()==1&&G.PowerPelletsLeft()==0,"Pac-Man grace leaves power collection and frightened capture authoritative");
    G.Reset(7);Check(G.RespawnFramesRemaining()==0&&G.GetStatus().Score==0&&G.GetStatus().Lives==3&&G.PowerPelletsLeft()==4,"Pac-Man reset removes grace and restores original collectibles");
    MazeTestAccess::PacTerminal(G);Input Held;Held.Fire=true;G.Step(Held);
    Check(G.GetStatus().Over&&G.GetStatus().Score==777,"Pac-Man held fire cannot replay terminal state");
    G.Step(FreshJump());Check(!G.GetStatus().Over&&G.GetStatus().Lives==3&&G.GetStatus().Score==0,"Pac-Man fresh terminal Jump replays cleanly");
    MazeTestAccess::PacLastDot(G);G.Step({});Check(G.GetStatus().Won&&G.GetLevel()==2&&G.DotsLeft()==0&&HasText(Draw(G),"YOU WIN"),"Pac-Man last real pellet publishes win and retry cues");
}
void ContraPolicies() {
    ContraGame G;G.Reset(3);platformers::TestAccess::ContraAtFinish(G);G.Step({});
    Check(!G.GetStatus().Won&&Has(G.GetStatus().Note,"cross the line"),"Contra exact X 2800 remains short of strict source victory");
    Input Right;Right.PadRight=true;G.Step(Right);Check(G.GetStatus().Won&&Near(G.GetPlayer().X,2805)&&HasText(Draw(G),"MISSION COMPLETE"),"Contra public D-pad crosses the original world-X finish");
    const Frame End=Draw(G);Input Held;Held.Fire=true;G.Step(Held);Check(SameFrame(End,Draw(G)),"Contra terminal feedback and world freeze together");
    G.Reset(3);platformers::TestAccess::ContraSpreadCap(G,95);G.Step(FreshFire());
    Check(G.BulletCount()==95&&G.GetPlayer().Cooldown==0&&HasText(Draw(G),"bullet limit"),"Contra rejects real three-shot burst when only one slot is free");
    platformers::TestAccess::ContraSpreadCap(G,93);G.Step(FreshFire());
    Check(G.BulletCount()==96&&G.GetPlayer().Cooldown==7,"Contra complete spread burst fills exact capacity with pre-update fire timing");
    G.Reset(3);platformers::TestAccess::ContraSpreadCap(G,0,1);G.Step(FreshFire());
    Check(G.BulletCount()==3&&!G.GetPlayer().Spread&&HasText(Draw(G),"NORMAL SHOT"),"Contra event uses last spread step before player update expires its timer");
    G.Reset(3);platformers::TestAccess::ContraRapid(G);G.Step({});
    Check(G.GetPlayer().FireRate==4&&HasText(Draw(G),"RAPID"),"Contra real pickup publishes persistent rapid-fire mode");
    G.Reset(3);Check(G.GetPlayer().FireRate==8&&!G.GetPlayer().Spread&&!G.GetStatus().Over,"Contra reset clears weapon upgrades and terminal state");
}
void NinjaPolicies() {
    ShadowNinjaGame G;platformers::TestAccess::NinjaBossState(G,13);G.Step({});
    Check(G.GetBoss().AttackTimer==12&&Has(G.GetStatus().Note,"pulse in 12")&&HasText(Draw(G),"PULSE IN 12"),"Ninja warning begins at the existing 12-step boundary");
    bool Warnings=true;for(int N=0;N<11;++N) {G.Step({});Warnings=Warnings&&Has(G.GetStatus().Note,"pulse in ");}
    Check(Warnings&&G.GetBoss().AttackTimer==1&&G.GetPlayer().Health==5,"Ninja telegraph never applies early damage");
    G.Step({});Check(G.GetBoss().AttackTimer==50&&G.PulseReceiptFramesRemaining()==8&&G.GetPlayer().Health==5&&HasText(Draw(G),"instant strike; hit not implied"),"Ninja missed pulse still emits eight-step instant-strike receipt");
    bool Receipt=true;for(int N=1;N<=8;++N) {G.Step({});Receipt=Receipt&&G.PulseReceiptFramesRemaining()==8-N;}
    Check(Receipt&&!HasText(Draw(G),"Boss pulse fired"),"Ninja receipt expires without extending strike damage");
    G.Reset(2);platformers::TestAccess::NinjaBossState(G,1,400);G.Step({});
    Check(G.GetPlayer().Health==4&&G.GetPlayer().Invincible==60&&G.PulseReceiptFramesRemaining()==8,"Ninja existing in-range pulse still damages exactly once");
    G.Reset(2);platformers::TestAccess::NinjaBossState(G,1,400,2);G.Step({});
    Check(G.GetPlayer().Health==5&&G.GetPlayer().Invincible==1&&G.PulseReceiptFramesRemaining()==8,"Ninja protected pulse reports receipt without claiming health loss");
    G.Reset(2);platformers::TestAccess::NinjaBossState(G,1,400,1);G.Step({});
    Check(G.GetPlayer().Health==4&&G.GetPlayer().Invincible==60,"Ninja player timer expires before boss damage check");
    G.Reset(2);platformers::TestAccess::NinjaBossState(G,1,400,0,1);G.Step({});
    Check(G.GetStatus().Over&&G.PulseReceiptFramesRemaining()==8&&HasText(Draw(G),"GAME OVER")&&!HasText(Draw(G),"Boss pulse fired"),"Ninja fatal pulse shows terminal result while cosmetic receipt cannot prolong gameplay");
    G.Reset(2);platformers::TestAccess::NinjaFatalEnemyBeforePulse(G);G.Step({});
    Check(G.GetStatus().Over&&G.GetBoss().AttackTimer==1&&G.PulseReceiptFramesRemaining()==0,"Ninja fatal enemy contact ends step before boss pulse");
    G.Reset(2);platformers::TestAccess::NinjaAttackCap(G);G.Step(FreshFire());
    Check(G.AttackCount()==64&&G.GetPlayer().AttackCooldown==0&&Has(G.GetStatus().Note,"attacks full"),"Ninja full attack collection rejects input without spending cooldown");
    G.Reset(2);platformers::TestAccess::NinjaQuiet(G);Input Held;Held.Fire=true;G.Step(Held);
    Check(G.AttackCount()==1&&G.GetPlayer().AttackCooldown==17,"Ninja held rising sword produces source edge attack");
    for(int N=0;N<30;++N) G.Step(Held);
    Check(G.AttackCount()==0&&G.GetPlayer().AttackCooldown==0,"Ninja sword does not auto-repeat after cooldown while held");
    G.Step({});G.Step(Held);Check(G.AttackCount()==1,"Ninja release then press can attack again");
    G.Reset(2);platformers::TestAccess::NinjaQuiet(G);Input Jump;Jump.Jump=true;G.Step(Jump);
    Check(G.GetPlayer().DoubleJump&&Has(G.GetStatus().Note,"air jump ready"),"Ninja first ground jump exposes real air-jump readiness");
    G.Step(Jump);G.Step({});G.Step(Jump);Check(!G.GetPlayer().DoubleJump&&Near(G.GetPlayer().VY,-9)&&Has(G.GetStatus().Note,"air jump used"),"Ninja second fresh jump spends the air jump");
    G.Reset(2);Check(G.PulseReceiptFramesRemaining()==0&&!G.HasBoss(),"Ninja reset clears cosmetic boss pulse receipt");
}
void FootballPolicies() {
    FootballGame G;Input Held;Held.Fire=true;G.Step(Held);Check(G.Data.Mode==FootballGame::Phase::Title,"Football title requires a fresh confirmation");
    G.Step(FreshAction());Check(G.Data.Mode==FootballGame::Phase::Playing&&Near(G.Data.Seconds,90-1.0/60),"Football kickoff immediately consumes original clock step");
    G.Step(Held);Check(G.GetLastKickReceipt()==FootballGame::KickReceipt::None&&G.Data.Human.KickCooldown==0,"Football held fire without edge cannot kick");
    G.Step(FreshFire());Check(G.GetLastKickReceipt()==FootballGame::KickReceipt::Accepted&&G.KickReceiptFramesRemaining()==12&&G.Data.Human.KickCooldown==11&&Near(G.Data.Football.Vx,7.68),"Football accepts original remote kick before cooldown tick and friction");
    G.Step(FreshFire());Check(G.GetLastKickReceipt()==FootballGame::KickReceipt::Cooldown&&G.KickReceiptFramesRemaining()==12&&HasText(Draw(G),"ignored: cooldown"),"Football fresh cooldown rejection has an independent input receipt");
    for(int N=0;N<12;++N) G.Step({});
    Check(G.KickReceiptFramesRemaining()==0&&G.GetLastKickReceipt()==FootballGame::KickReceipt::None&&G.IsKickReady(),"Football kick receipt expires and actual cooldown becomes ready");
    G.Data.Football={751,300,0,0};G.Data.Human.KickCooldown=8;const double Seconds=G.Data.Seconds;G.Step({});
    Check(G.Data.HumanScore==1&&G.GetLastScorer()==FootballGame::GoalScorer::Human&&G.GoalReceiptFramesRemaining()==90&&Near(G.Data.Football.X,400)&&Near(G.Data.Human.X,200)&&G.Data.Human.KickCooldown==7&&Near(G.Data.Seconds,Seconds-1.0/60),"Football goal receipt preserves immediate reset, cooldown and live match clock");
    Input Move;Move.PadDown=true;G.Step(Move);Check(Near(G.Data.Human.Y,303.5)&&G.GoalReceiptFramesRemaining()==89,"Football goal cue does not pause direct D-pad control");
    for(int N=0;N<89;++N) {G.Data.Football={400,300,0,0};G.Data.Cpu={600,300,2.8,true,0};G.Step({});}
    Check(G.GoalReceiptFramesRemaining()==0&&!HasText(Draw(G),"scored; play continues"),"Football scorer cue expires after 90 subsequent playing steps");
    G.Data.Seconds=0.001;G.Step({});const Frame Result=Draw(G);
    Check(G.GetStatus().Over&&G.GetStatus().Won&&HasText(Result,"Final score"),"Football final clock publishes score and source result");
    G.Step(Held);Check(SameFrame(Result,Draw(G)),"Football held button cannot restart the result screen");
    G.Step(FreshAction());Check(!G.GetStatus().Over&&G.Data.HumanScore==0&&G.GoalReceiptFramesRemaining()==0,"Football fresh replay clears prior match and all receipts");
}
void StartDodge(DodgeBallGame& G) {G.Step(FreshAction());G.Step(FreshAction());}
void DodgePolicies() {
    DodgeBallGame G;StartDodge(G);Check(G.HumanBallHolder()==1&&G.IsHumanThrowReady()&&G.JumpReadyPlayers()==3,"Dodge source front player and shared trio readiness are visible");
    G.Data.Players[1].Charge=30;G.Step(FreshFire());
    Check(G.Data.DodgeBall.InAir&&!G.Data.DodgeBall.PowerBall&&G.Data.Players[1].ThrowCooldown==13,"Dodge fresh throw at charge 30 is normal before movement/cooldown update");
    G.Reset(4);StartDodge(G);G.Data.Players[1].Charge=31;G.Step(FreshFire());
    Check(G.Data.DodgeBall.PowerBall&&G.Data.Players[1].ThrowCooldown==21,"Dodge fresh charge 31 produces an actual super throw");
    G.Reset(4);StartDodge(G);G.Data.Players[1].Charge=30;Input HoldUp;HoldUp.Up=true;HoldUp.Fire=true;G.Step(HoldUp);
    Check(G.Data.DodgeBall.PowerBall&&G.Data.Players[1].ThrowCooldown==22,"Dodge held throw sees charge gained after movement in the same step");
    G.Reset(4);StartDodge(G);G.Data.Players[1].Charge=30;Input Hat;Hat.PadUp=true;G.Step(Hat);
    Check(G.Data.Players[1].Charge==28&&!G.IsHumanSuperCharged(),"Dodge D-pad up moves trio without inventing keyboard charge behavior");
    Input Up;Up.Up=true;G.Step(Up);G.Step(Up);Check(G.IsHumanSuperCharged()&&Has(G.GetStatus().Note,"Charge"),"Dodge actual keyboard charge crosses strict super threshold");
    G.Reset(4);StartDodge(G);G.Data.Players[0].Health=G.Data.Players[2].Health=0;
    const auto P=G.Data.Players[1];G.Data.Players[1].HasBall=false;G.Data.DodgeBall={P.X+19,P.Y,1,0,-1,true,false,White};Input Hold;Hold.Fire=true;G.Step(Hold);
    Check(G.Data.DodgeBall.InAir&&G.Data.DodgeBall.Owner==-1&&!G.Data.Players[1].HasBall&&G.Data.Players[1].ThrowCooldown==14,"Dodge held Fire catches and rethrows in one real step");
    G.Reset(4);StartDodge(G);G.Data.Players[0].Health=G.Data.Players[2].Health=0;
    const auto Q=G.Data.Players[1];G.Data.Players[1].HasBall=false;G.Data.DodgeBall={Q.X+19,Q.Y,1,0,-1,true,false,White};G.Step(FreshFire());
    Check(G.Data.DodgeBall.InAir&&G.Data.DodgeBall.Owner==-1&&G.Data.Players[1].ThrowCooldown==0,"Dodge fresh throw edge alone does not invent held ground catch");
    G.Data.Mode=DodgeBallGame::Phase::Won;G.Data.Round=1;G.Data.HumanScore=1;G.Step(Hold);
    Check(G.Data.Round==1&&G.Data.Mode==DodgeBallGame::Phase::Won,"Dodge held Fire cannot advance terminal match");
    G.Step(FreshJump());Check(G.Data.Round==2&&G.Data.HumanScore==1&&G.Data.Mode==DodgeBallGame::Phase::Playing,"Dodge fresh round advance retains tournament score");
    G.Data.Mode=DodgeBallGame::Phase::Won;G.Data.Round=4;G.Step(FreshAction());
    Check(G.Data.Mode==DodgeBallGame::Phase::Title&&G.Data.Round==1,"Dodge fourth match returns to title rather than a fifth round");
}
void ZeldaPolicies() {
    ZeldaGame G;MazeTestAccess::ZeldaLastEnemy(G);Input Attack=FreshFire();Attack.PadUp=true;G.Step(Attack);
    Check(G.LivingEnemyCount()==0&&G.GetPlayer().Face==ZeldaGame::Facing::Up&&G.GetPlayer().AttackTimer==17&&G.HasGroundKey()&&!G.GetStatus().Won,"Zelda sword hits old right facing before D-pad moves and turns upward");
    Check(HasText(Draw(G),"Collect the gold KEY")&&!G.IsSwordReady(),"Zelda last kill reveals real ground-key objective and sword cooldown");
    Input Held;Held.Fire=true;for(int N=0;N<17;++N) G.Step(Held);
    Check(G.IsSwordReady()&&G.GetPlayer().AttackTimer==0,"Zelda held sword does not repeat after its 18-step source timer");
    Input Right;Right.PadRight=true;for(int N=0;N<8&&!G.GetStatus().Won;++N) G.Step(Right);
    Check(G.GetKeys()==1&&G.GetStatus().Won&&!G.HasGroundKey()&&HasText(Draw(G),"VICTORY"),"Zelda public movement collects roster key and finishes");
    const Frame Victory=Draw(G);G.Step(Held);Check(SameFrame(Victory,Draw(G)),"Zelda terminal key victory freezes held gameplay");
    G.Step(FreshJump());Check(!G.GetStatus().Won&&G.LivingEnemyCount()==4&&G.GetKeys()==0&&G.IsSwordReady(),"Zelda fresh replay restores roster, sword and key lifecycle");
    MazeTestAccess::ZeldaProjectile(G,2);G.Step({});Check(G.GetPlayer().Health==6&&G.GetPlayer().Invincible==1&&Has(G.GetStatus().Note,"expires next live step"),"Zelda final existing hurt-grace frame is described accurately");
    G.Step({});Check(G.GetPlayer().Health==5&&G.GetPlayer().Invincible==45,"Zelda pre-collision timer expiry admits one of two overlapping shots");
    G.Reset(4);MazeTestAccess::ZeldaProjectile(G,1,1);G.Step({});Check(G.GetStatus().Over&&!G.GetStatus().Won&&HasText(Draw(G),"GAME OVER"),"Zelda fatal projectile publishes defeat without key victory");
}
void ShooterPublicPolicies() {
    // These cores deliberately expose no mutable container seam. Exercise real
    // seeded sessions and public saves, not fabricated full bullet collections.
    AsteroidsGame A;A.Reset(1);Check(A.GetRockCount()==6&&A.IsFireReady(),"Asteroids original six-rock opening and real fire readiness");
    Input Fire=FreshFire();Fire.PadUp=true;A.Step(Fire);
    Check(A.GetShip().Thrust&&A.GetShip().Cooldown==7&&!A.IsFireReady()&&HasText(Draw(A),"COOLDOWN 7"),"Asteroids D-pad thrust and event-before-update shot remain bound");
    A.Reset(1);bool AsteroidLoss=false;
    for(int N=0;N<10000&&!AsteroidLoss;++N) {A.Step({});AsteroidLoss=A.GetStatus().Lives<3;}
    Check(AsteroidLoss&&A.GetStatus().Lives==2&&A.GetProtectionFrames()==60,"Asteroids real seeded collision emits original 60-timer protection");
    bool AsteroidProtected=true;for(int N=0;N<59;++N) {A.Step({});AsteroidProtected=AsteroidProtected&&A.GetStatus().Lives==2;}
    Check(AsteroidProtected&&A.GetProtectionFrames()==1&&Has(A.GetStatus().Note,"EXPIRES NEXT LIVE STEP"),"Asteroids countdown expires before collision and describes its last protected step");
    A.Reset(1);Check(A.GetProtectionFrames()==0&&A.GetStatus().Lives==3,"Asteroids reset clears protection feedback");

    SegaShooterGame S;S.Reset(1);Input Move;Move.PadDown=true;Move.Fire=true;S.Step(Move);
    Check(Near(S.GetPlayer().Y,305)&&S.GetPlayer().Cooldown==6&&!S.IsFireReady()&&HasText(Draw(S),"COOLDOWN 6"),"Sega direct D-pad and held-after-update firing preserve source cadence");
    S.Reset(1);bool SegaLoss=false;for(int N=0;N<6000&&!SegaLoss;++N) {S.Step({});SegaLoss=S.GetPlayer().Lives<3;}
    Check(SegaLoss&&S.GetPlayer().Lives==2&&S.GetPlayer().Invincible==60,"Sega real enemy contact publishes original damage protection");
    bool SegaProtected=true;for(int N=0;N<59;++N) {S.Step({});SegaProtected=SegaProtected&&S.GetPlayer().Lives==2;}
    Check(SegaProtected&&S.GetPlayer().Invincible==1&&Has(S.GetStatus().Note,"EXPIRES NEXT LIVE STEP"),"Sega protected live steps retain lives and honest expiry feedback");

    StarShooterGame T;StarShooterGame::RunSnapshot Snapshot;Snapshot.Mode=StarShooterGame::Difficulty::Easy;
    Snapshot.Score=1234;Snapshot.Wave=4;Snapshot.SpawnRate=28;Snapshot.Lives=99;Snapshot.Triple=true;Snapshot.Shield=true;Snapshot.SpeedBoost=true;
    Check(T.ResumeRun(Snapshot,17),"Star public saved run can set a bounded late-wave fixture");
    Input Held;Held.Fire=true;Held.PadRight=true;T.Step(Held);
    Check(Near(T.GetPlayer().X,409.6)&&T.GetPlayer().Cooldown==10&&HasText(Draw(T),"TRIPLE")&&HasText(Draw(T),"COOLDOWN 10"),"Star restored power and D-pad drive real triple-shot cooldown");
    for(int N=1;N<1199;++N) T.Step({});
    Check(T.GetWave()==4&&T.GetWaveFramesRemaining()==1&&!T.HasBoss(),"Star wave countdown exposes last pre-transition step");
    T.Step({});Check(T.GetWave()==5&&T.GetWaveFramesRemaining()==1200&&T.HasBoss()&&HasText(Draw(T),"BOSS INCOMING"),"Star 1200th live step advances to actual fifth-wave boss entry");
    Game& Host=T;Check(Host.OwnPause(true)&&!T.IsFireReady(),"Star host pause owns readiness");
    const Frame Paused=Draw(T);const auto Saved=Host.SaveState();const int WaveTime=T.GetWaveFramesRemaining();
    for(int N=0;N<20;++N) T.Step(Held);
    Check(SameFrame(Paused,Draw(T))&&T.GetWaveFramesRemaining()==WaveTime&&Host.SaveState()==Saved,"Star paused held controls freeze world and lightweight save fields");
    Input Down;Down.Down=true;T.Step(Down);T.Step(FreshFire());
    Check(Host.SavePending()&&Host.WantsExit()&&Host.IsCorePaused()&&Host.SaveState()==Saved&&Has(T.GetStatus().Note,"persistence pending"),"Star Save and Quit raises actual pending host contract without claiming disk success");
    const Frame Quit=Draw(T);T.Step(Held);Check(SameFrame(Quit,Draw(T)),"Star quit request prevents additional gameplay");
    Host.ClearSavePending();Check(!Host.SavePending()&&Host.WantsExit(),"Star save acknowledgement clears only pending flag");
    StarShooterGame Restored;Game& Receiver=Restored;Check(Receiver.RestoreState(Saved,17)&&Receiver.SaveState()==Saved&&Restored.EntityCount()==0&&Restored.GetWaveFramesRemaining()==1200,"Star host restore preserves lightweight fields and starts a fresh world");
    const Frame BeforeBad=Draw(Restored);Check(!Receiver.RestoreState(Saved+" extra",99)&&SameFrame(BeforeBad,Draw(Restored)),"Star malformed save rejection is atomic");

    // Real firing pressure remains bounded. This is not a claim that ordinary
    // play filled every private vector to its exact saturation threshold.
    A.Reset(21);S.Reset(21);Restored.Reset(21);bool Bounds=true;std::size_t PeakA=0,PeakS=0,PeakT=0;
    for(int N=0;N<1800;++N) {
        Input I;I.Fire=true;I.PadRight=N%120<60;I.PadLeft=!I.PadRight;I.PadUp=N%180<90;I.PadDown=!I.PadUp;
        A.Step(I);S.Step(I);Restored.Step(I);
        PeakA=std::max(PeakA,A.EntityCount());PeakS=std::max(PeakS,S.EntityCount());PeakT=std::max(PeakT,Restored.EntityCount());
        Bounds=Bounds&&A.EntityCount()<=AsteroidsGame::MaxBullets+AsteroidsGame::MaxRocks+AsteroidsGame::MaxUfos&&
            S.EntityCount()<=SegaShooterGame::MaxBullets+SegaShooterGame::MaxEnemies+SegaShooterGame::MaxPowerups+1&&
            Restored.EntityCount()<=StarShooterGame::MaxBullets+StarShooterGame::MaxEnemies+StarShooterGame::MaxPowerups+StarShooterGame::MaxEffects+StarShooterGame::MaxPopups+1;
        if(N%60==0) Bounds=Bounds&&FiniteFrame(Draw(A))&&FiniteFrame(Draw(S))&&FiniteFrame(Draw(Restored));
    }
    Check(Bounds&&PeakA>6&&PeakS>1&&PeakT>1,"All three shooter real sessions retain finite bounded entities and frames under sustained controls");
    std::cout<<"Shooter observed entity peaks: "<<PeakA<<", "<<PeakS<<", "<<PeakT<<" (exact container saturation not forced)\n";
}
void AllElevenFrames() {
    DungeonGame Dungeon;PongGame Pong;PacmanGame Pac;ContraGame Contra;ShadowNinjaGame Ninja;
    FootballGame Football;DodgeBallGame Dodge;AsteroidsGame Asteroids;SegaShooterGame Sega;ZeldaGame Zelda;StarShooterGame Star;
    const std::array<Game*,11> Games{{&Dungeon,&Pong,&Pac,&Contra,&Ninja,&Football,&Dodge,&Asteroids,&Sega,&Zelda,&Star}};
    for(std::size_t N=0;N<Games.size();++N) {
        Game& G=*Games[N];G.Reset(730);Check(FiniteFrame(Draw(G)),"Family "+std::to_string(N)+" reset frame is finite and bounded");
        G.Step(FreshAction());G.Step(FreshAction());
        for(int Tick=0;Tick<120;++Tick) {Input I;I.Fire=Tick%3!=0;I.PadRight=Tick<60;I.PadLeft=Tick>=60;G.Step(I);}
        Check(FiniteFrame(Draw(G))&&!G.GetStatus().Note.empty(),"Family "+std::to_string(N)+" active feedback is finite, bounded and nonempty");
    }
}
}
int main() {
    try {
        DungeonPolicies();PongPolicies();PacmanPolicies();ContraPolicies();NinjaPolicies();FootballPolicies();DodgePolicies();ZeldaPolicies();ShooterPublicPolicies();AllElevenFrames();
    } catch(const std::exception& E) {Check(false,std::string("uncaught boundary setup error: ")+E.what());}
    std::cout<<"Native polish: "<<Checks-Failures<<'/'<<Checks<<" checks passed\n";
    return Failures?1:0;
}
