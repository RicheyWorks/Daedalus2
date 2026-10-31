// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
using StarGame = StarShooterGame;

namespace {
int Checks = 0, Failures = 0;
void Check(bool Ok, const std::string& Message) {
    ++Checks;
    if (!Ok) { ++Failures; std::cerr << "FAIL " << Message << '\n'; }
}
bool Close(double Actual, double Expected) {
    return std::isfinite(Actual) && std::isfinite(Expected)
        && std::abs(Actual - Expected) <= 1.0e-9 * std::max(1.0, std::abs(Expected));
}
double Number(bool Value) { return Value ? 1.0 : 0.0; }
double Number(int Value) { return static_cast<double>(Value); }
double Number(std::size_t Value) { return static_cast<double>(Value); }
void Compare(const std::vector<double>& Actual, const std::vector<double>& Expected,
             const std::string& Context) {
    Check(Actual.size() == Expected.size(), Context + " output shape");
    if (Actual.size() != Expected.size()) return;
    for (std::size_t Index = 0; Index < Actual.size(); ++Index) {
        if (!Close(Actual[Index], Expected[Index])) {
            std::ostringstream Detail;
            Detail << Context << " field " << Index << ": actual " << Actual[Index]
                   << ", source " << Expected[Index];
            Check(false, Detail.str());
        } else Check(true, Context + " numeric parity");
    }
}
Input DecodeInput(double MaskValue, double Ax, double Ay) {
    const int Mask = static_cast<int>(MaskValue);
    Input Result;
    Result.Left = (Mask & (1 | 8)) != 0;
    Result.Right = (Mask & (2 | 16)) != 0;
    Result.Up = (Mask & (4 | 32)) != 0;
    Result.Down = (Mask & (64 | 128)) != 0;
    Result.Fire = (Mask & 256) != 0;
    Result.AxisX = Ax; Result.AxisY = Ay;
    return Result;
}
std::vector<double> Numbers(const std::string& Value) {
    std::istringstream Stream(Value);
    std::vector<double> Result;
    double NumberValue;
    while (Stream >> NumberValue) {
        if (!std::isfinite(NumberValue)) throw std::runtime_error("nonfinite fixture input");
        Result.push_back(NumberValue);
    }
    if (!Stream.eof()) throw std::runtime_error("invalid fixture token");
    return Result;
}
void Need(const std::vector<double>& Values, std::size_t Size, const std::string& Name) {
    if (Values.size() != Size) throw std::runtime_error(Name + " input shape");
}
template<class Bullet, class Velocity> std::vector<double> PackBullets(
    const std::vector<Bullet>& Bullets, std::size_t Maximum, Velocity GetVelocity) {
    if (Bullets.size() > Maximum) throw std::runtime_error("pattern exceeds fixture capacity");
    std::vector<double> Result;
    for (const auto& B : Bullets) {
        const Vec VelocityValue = GetVelocity(B);
        Result.insert(Result.end(), {B.X, B.Y, VelocityValue.X, VelocityValue.Y});
    }
    Result.resize(Maximum * 4, 0);
    return Result;
}
template<class Bullet, class Velocity> std::vector<double> ShotResult(
    const std::vector<Bullet>& Bullets, int Cooldown, std::size_t Maximum, Velocity GetVelocity) {
    std::vector<double> Result{Number(Bullets.size()), Number(Cooldown)};
    const auto Values = PackBullets(Bullets, Maximum, GetVelocity);
    Result.insert(Result.end(), Values.begin(), Values.end());
    return Result;
}

std::vector<double> ExecuteFixture(const std::string& Label, const std::vector<double>& V) {
    if (Label == "AST_SHIP") {
        Need(V, 12, Label); DriftstoneGame::Ship S;
        S.X=V[0]; S.Y=V[1]; S.Angle=V[2]; S.Vx=V[3]; S.Vy=V[4]; S.Cooldown=static_cast<int>(V[5]);
        const Input I=DecodeInput(V[6], V[7], V[8]);
        for (int N=0; N<static_cast<int>(V[11]); ++N) {
            S.Update(I, static_cast<int>(V[9]), static_cast<int>(V[10]));
        }
        return {S.X,S.Y,S.Angle,S.Vx,S.Vy,Number(S.Cooldown),Number(S.Thrust)};
    }
    if (Label == "AST_SHOT") {
        Need(V, 4, Label); DriftstoneGame::Ship S; DriftstoneGame::Bullet B;
        S.X=V[0]; S.Y=V[1]; S.Angle=V[2]; S.Cooldown=static_cast<int>(V[3]);
        const bool Shot=DriftstoneGame::Shoot(S,B);
        if (!Shot) return {0,Number(S.Cooldown),0,0,0,0,0};
        Check(B.PlayerOwned, "driftstone player shot ownership");
        return {1,Number(S.Cooldown),B.X,B.Y,B.Vx,B.Vy,Number(B.Life)};
    }
    if (Label == "AST_BULLET") {
        Need(V, 5, Label); auto B=DriftstoneGame::Bullet::At(V[0],V[1],V[2]); B.Life=static_cast<int>(V[3]);
        for (int N=0; N<static_cast<int>(V[4]); ++N) { B.Update(); }
        return {B.X,B.Y,B.Vx,B.Vy,Number(B.Life)};
    }
    if (Label == "AST_ROCK") {
        Need(V, 8, Label); DriftstoneGame::Rock R;
        R.X=V[0];R.Y=V[1];R.Size=static_cast<int>(V[2]);R.Vx=V[3];R.Vy=V[4];R.Angle=V[5];R.Rotation=V[6];
        for (int N=0; N<static_cast<int>(V[7]); ++N) { R.Update(); }
        return {R.X,R.Y,R.Angle,R.Radius(),Number(R.SplitCount())};
    }
    if (Label == "RIFTWING_PLAYER") {
        Need(V, 9, Label); RiftwingGame::Player P;
        P.X=V[0];P.Y=V[1];P.Speed=V[2];P.Cooldown=static_cast<int>(V[3]);P.Invincible=static_cast<int>(V[4]);
        const Input I=DecodeInput(V[5],V[6],V[7]);
        for (int N=0; N<static_cast<int>(V[8]); ++N) { P.Update(I); }
        return {P.X,P.Y,P.Speed,Number(P.Cooldown),Number(P.Invincible)};
    }
    if (Label == "RIFTWING_SHOT") {
        Need(V, 4, Label); RiftwingGame::Player P;
        P.X=V[0];P.Y=V[1];P.Power=static_cast<int>(V[2]);P.Cooldown=static_cast<int>(V[3]);
        const auto Shots=P.Shoot();
        return ShotResult(Shots,P.Cooldown,3,[](const RiftwingGame::Bullet& B){return Vec{B.Vx,B.Vy};});
    }
    if (Label == "RIFTWING_ENEMY") {
        Need(V, 7, Label); RiftwingGame::Enemy E; RiftwingGame::Player P;
        E.Chaser=V[0]!=0;E.Health=E.Chaser?4:2;E.X=V[1];E.Y=V[2];E.Speed=V[3];E.ShootTimer=static_cast<int>(V[4]);P.Y=V[5];
        for (int N=0; N<static_cast<int>(V[6]); ++N) { E.Update(P); }
        return {E.X,E.Y,Number(E.Health),Number(E.ShootTimer)};
    }
    if (Label == "RIFTWING_POWER") {
        Need(V, 7, Label); RiftwingGame::Player P; RiftwingGame::Powerup U;
        U.Kind=static_cast<RiftwingGame::PowerKind>(static_cast<int>(V[0]));
        P.Power=static_cast<int>(V[1]);P.Speed=V[2];P.Lives=static_cast<int>(V[3]);U.X=V[4];U.Y=V[5];
        RiftwingGame::ApplyPower(P,U.Kind);
        for (int N=0; N<static_cast<int>(V[6]); ++N) { U.Update(); }
        return {Number(P.Power),P.Speed,Number(P.Lives),U.X,U.Y};
    }
    if (Label == "RIFTWING_BULLET") {
        Need(V, 5, Label); RiftwingGame::Bullet B{V[0],V[1],V[2],V[3],true};
        for (int N=0; N<static_cast<int>(V[4]); ++N) { B.Update(); }
        return {B.X,B.Y};
    }
    if (Label == "STAR_PLAYER") {
        Need(V, 9, Label); StarGame::Player P;
        P.X=V[0];P.Y=V[1];P.Cooldown=static_cast<int>(V[2]);P.Invincible=static_cast<int>(V[3]);P.SpeedBoost=V[4]!=0;
        const Input I=DecodeInput(V[5],V[6],V[7]);
        for (int N=0; N<static_cast<int>(V[8]); ++N) { P.Update(I); }
        return {P.X,P.Y,Number(P.Cooldown),Number(P.Invincible)};
    }
    if (Label == "STAR_SHOT") {
        Need(V, 4, Label); StarGame::Player P;
        P.X=V[0];P.Y=V[1];P.Triple=V[2]!=0;P.Cooldown=static_cast<int>(V[3]);
        const auto Shots=P.Shoot();
        for (const auto& B:Shots) { Check(B.PlayerOwned && !B.BossOwned && !B.Big, "star player bullet ownership"); }
        return ShotResult(Shots,P.Cooldown,3,[](const StarGame::Bullet& B){return Vec{B.Dx,B.Dy};});
    }
    if (Label == "STAR_HIT") {
        Need(V, 2, Label); StarGame::Player P; P.Lives=static_cast<int>(V[0]);P.Shield=V[1]!=0;
        const bool Over=P.Hit();
        // Particle count is cosmetic and belongs to the game renderer, not Player::Hit.
        return {Number(P.Lives),Number(P.Shield),Number(P.Invincible),Number(Over)};
    }
    if (Label == "STAR_WANTS") {
        Need(V, 2, Label); return {Number(StarGame::Player::WantsToShoot(V[0]!=0,V[1]))};
    }
    if (Label == "STAR_STATS") {
        Need(V, 4, Label);
        const auto Kind=static_cast<StarGame::EnemyKind>(static_cast<int>(V[0]));
        const auto Mode=static_cast<StarGame::Difficulty>(static_cast<int>(V[1]));
        const auto D=StarGame::Data(Kind);
        const auto E=StarGame::Enemy::Create(Kind,static_cast<int>(V[2]),Mode,400,-130,
            D.SpeedLow+(D.SpeedHigh-D.SpeedLow)*V[3],0,shooter_detail::Pi,80);
        return {E.Speed,Number(E.Hp),Number(E.Size),Number(D.BasePoints),Number(D.DivePoints),
                Number(E.ShootLow),Number(E.ShootHigh),D.DiveSpeed};
    }
    if (Label == "STAR_ENEMY_SHOT") {
        Need(V, 4, Label); const auto Kind=static_cast<StarGame::EnemyKind>(static_cast<int>(V[0]));
        auto E=StarGame::Enemy::Create(Kind,1,StarGame::Difficulty::Hard,V[1],V[2],2,0,0,static_cast<int>(V[3]));
        const auto Shots=E.Shoot(E.ShootLow+(E.ShootHigh-E.ShootLow)/2);
        for (const auto& B:Shots) { Check(!B.PlayerOwned && !B.BossOwned, "star enemy bullet ownership"); }
        return ShotResult(Shots,E.ShootTimer,3,[](const StarGame::Bullet& B){return Vec{B.Dx,B.Dy};});
    }
    if (Label == "STAR_DIVE") {
        Need(V, 6, Label); const auto Kind=static_cast<StarGame::EnemyKind>(static_cast<int>(V[0]));
        auto E=StarGame::Enemy::Create(Kind,1,StarGame::Difficulty::Hard,V[1],V[2],2,0,0,100);
        E.StartDive(V[3],V[4]);
        for (int N=0;N<static_cast<int>(V[5]);++N) { E.Update(V[3],V[4],1,StarGame::Difficulty::Hard,1); }
        return {E.X,E.Y,E.DiveDx,E.DiveDy,Number(E.DiveTimer),Number(E.State==StarGame::EnemyState::Dive),Number(E.Alive)};
    }
    if (Label == "STAR_BOSS") {
        Need(V, 3, Label); auto B=StarGame::Boss::Create(static_cast<int>(V[0]),
            static_cast<StarGame::Difficulty>(static_cast<int>(V[1])),410);
        B.Hp=static_cast<int>(V[2]);const int Summoned=B.CheckPhases();const int Repeated=B.CheckPhases();
        Check(Repeated==0, "boss phase summons run once");
        return {Number(B.MaxHp),B.Speed,Number(B.ShootRate),Number(static_cast<int>(B.FirePattern)),
                Number(B.Phase66),Number(B.Phase33),Number(Summoned+Repeated)};
    }
    if (Label == "STAR_BOSS_SHOT") {
        Need(V, 8, Label);auto B=StarGame::Boss::Create(static_cast<int>(V[0]),StarGame::Difficulty::Hard,410);
        B.FirePattern=static_cast<StarGame::Pattern>(static_cast<int>(V[1]));
        B.State=static_cast<StarGame::BossState>(static_cast<int>(V[2]));B.ShootTimer=static_cast<int>(V[3]);B.X=V[4];B.Y=V[5];
        const auto Shots=B.Shoot(V[6],V[7]);
        for (const auto& Shot:Shots) { Check(Shot.BossOwned && !Shot.PlayerOwned && Shot.Big, "boss bullet ownership"); }
        return ShotResult(Shots,B.ShootTimer,8,[](const StarGame::Bullet& Shot){return Vec{Shot.Dx,Shot.Dy};});
    }
    if (Label == "STAR_BOSS_MOVE") {
        Need(V, 12, Label);auto B=StarGame::Boss::Create(static_cast<int>(V[0]),StarGame::Difficulty::Hard,static_cast<int>(V[6]));
        B.State=static_cast<StarGame::BossState>(static_cast<int>(V[1]));B.X=V[2];B.Y=V[3];B.Direction=static_cast<int>(V[4]);
        B.MoveTimer=static_cast<int>(V[5]);B.ShootTimer=static_cast<int>(V[7]);B.Hp=static_cast<int>(V[8]);B.ChargeDx=0;B.ChargeDy=6;
        int Summoned=0;
        for (int N=0;N<static_cast<int>(V[11]);++N) { Summoned+=B.Update(V[9],V[10],360); }
        return {B.X,B.Y,Number(B.Direction),Number(B.MoveTimer),Number(B.ChargeTimer),Number(B.ShootTimer),
            Number(static_cast<int>(B.State)),B.Speed,Number(B.ShootRate),Number(B.Phase66),Number(B.Phase33),Number(Summoned)};
    }
    if (Label == "STAR_POWER") {
        Need(V, 7, Label);StarGame::Player P;StarGame::Powerup U;
        U.Kind=static_cast<StarGame::PowerKind>(static_cast<int>(V[0]));P.Triple=V[1]!=0;P.Shield=V[2]!=0;P.SpeedBoost=V[3]!=0;
        U.X=V[4];U.Y=V[5];U.Apply(P);
        for (int N=0;N<static_cast<int>(V[6]);++N) { U.Update(); }
        return {Number(P.Triple),Number(P.Shield),Number(P.SpeedBoost),U.X,U.Y,Number(U.Alive),U.Bob};
    }
    if (Label == "STAR_BULLET") {
        Need(V, 6, Label);StarGame::Bullet B;B.X=V[0];B.Y=V[1];B.Dx=V[2];B.Dy=V[3];B.Big=V[4]!=0;
        for (int N=0;N<static_cast<int>(V[5]);++N) { B.Update(); }
        const Rect R=B.Bounds();return {B.X,B.Y,Number(B.Alive),R.X,R.Y,R.W,R.H};
    }
    throw std::runtime_error("unknown fixture label: " + Label);
}

void SourceFixtures(const char* Filename) {
    std::ifstream File(Filename); Check(static_cast<bool>(File), "source fixture exists");
    if (!File) return;
    const std::map<std::string,int> ExpectedCounts={{"AST_SHIP",81},{"AST_SHOT",15},{"AST_BULLET",20},{"AST_ROCK",6},
        {"RIFTWING_PLAYER",60},{"RIFTWING_SHOT",9},{"RIFTWING_ENEMY",18},{"RIFTWING_POWER",9},{"RIFTWING_BULLET",9},
        {"STAR_PLAYER",42},{"STAR_SHOT",6},{"STAR_HIT",6},{"STAR_WANTS",8},{"STAR_STATS",135},
        {"STAR_ENEMY_SHOT",6},{"STAR_DIVE",18},{"STAR_BOSS",72},{"STAR_BOSS_SHOT",72},{"STAR_BOSS_MOVE",7},
        {"STAR_POWER",12},{"STAR_BULLET",24}};
    const std::vector<std::string> Pins={
        "# SOURCE asteroids_pygame_ce.py SHA256 8a46338b4d93d9447df7feab40dff21b99bfa0ce7614698681b8a5c91f0fc20b",
        "# SOURCE sega_space_shooter.py SHA256 5108b3065fa91332570445adaccbb8c5bb77e437bc0bd8e37213737e931ad0db",
        "# SOURCE star_shootergpt1_fixed.py SHA256 05ac3a0fabddab94adb3d3a7b2c6eb9f7e1543390a48805db247a3ffd40d8281"};
    std::map<std::string,int> Counts;std::vector<bool> SeenPins(Pins.size(),false);std::string Line;int CaseCount=0,LineCount=0;
    while (std::getline(File,Line)) {
        ++LineCount;if (!Line.empty() && Line.back()=='\r') Line.pop_back();
        if (Line.empty()) continue;
        if (Line[0]=='#') {
            for (std::size_t N=0;N<Pins.size();++N) {
                if (Line==Pins[N]) { SeenPins[N]=true; }
            }
            continue;
        }
        try {
            const auto First=Line.find('|'),Second=Line.find('|',First==std::string::npos?0:First+1);
            if (First==std::string::npos || Second==std::string::npos) throw std::runtime_error("missing fixture delimiter");
            const std::string Label=Line.substr(0,First);
            const auto Inputs=Numbers(Line.substr(First+1,Second-First-1));auto Expected=Numbers(Line.substr(Second+1));
            const auto Actual=ExecuteFixture(Label,Inputs);
            if (Label=="STAR_HIT") {Need(Expected,5,Label);Expected.resize(4);} // exclude only cosmetic particle count
            Compare(Actual,Expected,Label+" line "+std::to_string(LineCount));++CaseCount;++Counts[Label];
        } catch (const std::exception& Error) {Check(false,"fixture line "+std::to_string(LineCount)+": "+Error.what());}
    }
    Check(CaseCount==635,"all 635 executed-source cases consumed");
    Check(Counts==ExpectedCounts,"fixture category counts unchanged");
    for (bool Seen:SeenPins) { Check(Seen,"source SHA256 provenance present"); }
    std::cout << "Source fixtures: " << CaseCount << " (six cosmetic particle-count fields excluded)\n";
}

bool SameColor(Color A,Color B) {return A.R==B.R && A.G==B.G && A.B==B.B && A.A==B.A;}
bool SameVec(Vec A,Vec B) {return A.X==B.X && A.Y==B.Y;}
bool SameFrame(const Frame& A,const Frame& B) {
    if (A.Width!=B.Width || A.Height!=B.Height || !SameColor(A.Background,B.Background) || A.Commands.size()!=B.Commands.size()) return false;
    for (std::size_t N=0;N<A.Commands.size();++N) {
        const auto& X=A.Commands[N];const auto& Y=B.Commands[N];
        if (X.Kind!=Y.Kind || !SameVec(X.A,Y.A) || !SameVec(X.B,Y.B) || !SameVec(X.C,Y.C)
            || !SameColor(X.Tint,Y.Tint) || X.Size!=Y.Size || X.Label!=Y.Label) return false;
    }
    return true;
}
bool FiniteFrame(const Frame& F) {
    if (F.Width!=800 || F.Height!=600 || F.Commands.empty() || F.Commands.size()>Frame::MaxCommands) return false;
    for (const auto& C:F.Commands) {
        if (!std::isfinite(C.A.X) || !std::isfinite(C.A.Y) || !std::isfinite(C.B.X) || !std::isfinite(C.B.Y)
            || !std::isfinite(C.C.X) || !std::isfinite(C.C.Y) || !std::isfinite(C.Size) || C.Label.size()>256) return false;
    }
    return true;
}
bool SameStatus(const Status& A,const Status& B) {return A.Score==B.Score && A.Lives==B.Lives && A.Over==B.Over && A.Won==B.Won && A.Note==B.Note;}
bool SameSnapshot(const StarGame::RunSnapshot& A,const StarGame::RunSnapshot& B) {
    return A.Score==B.Score && A.Wave==B.Wave && A.SpawnRate==B.SpawnRate && A.Lives==B.Lives && A.Triple==B.Triple
        && A.Shield==B.Shield && A.SpeedBoost==B.SpeedBoost && A.BossKilledThisWave==B.BossKilledThisWave && A.Mode==B.Mode;
}
Input ReplayInput(int Tick) {
    Input I;I.Left=Tick%240<60;I.Right=Tick%240>=120 && Tick%240<180;
    I.Up=Tick%360<60;I.Down=Tick%360>=180 && Tick%360<240;
    I.AxisX=Tick%180<90?0.4:-0.4;I.AxisY=Tick%120<60?0.25:-0.25;
    I.Fire=true;I.FirePressed=Tick%19==0;return I;
}
template<class G> void Replay(const char* Name,std::size_t Limit,int Ticks) {
    G A,B;A.Reset(730);B.Reset(730);std::size_t Peak=0;int Restarts=0;
    for (int Tick=0;Tick<Ticks;++Tick) {
        const Input I=ReplayInput(Tick);A.Step(I);B.Step(I);
        Peak=std::max(Peak,A.EntityCount());Check(A.EntityCount()<=Limit,std::string(Name)+" entity bound");
        if (Tick%61==0) {
            Frame AF,BF;A.Render(AF);B.Render(BF);
            Check(SameFrame(AF,BF),std::string(Name)+" deterministic replay frame");
            Check(FiniteFrame(AF),std::string(Name)+" finite bounded drawing");
            Check(SameStatus(A.GetStatus(),B.GetStatus()),std::string(Name)+" deterministic replay status");
        }
        const Status S=A.GetStatus();
        if (S.Over || S.Won) {
            Frame Before,After;A.Render(Before);A.Step(I);A.Render(After);
            Check(SameFrame(Before,After),std::string(Name)+" terminal state frozen");
            ++Restarts;A.Reset(static_cast<std::uint32_t>(730+Restarts));B.Reset(static_cast<std::uint32_t>(730+Restarts));
            Check(A.GetStatus().Score==0 && !A.GetStatus().Over && !A.GetStatus().Won,std::string(Name)+" restart clears terminal state");
        }
    }
    Frame Before,After,FreshFrame;G Fresh;Fresh.Reset(99);A.Reset(99);A.Render(Before);A.Render(After);Fresh.Render(FreshFrame);
    Check(SameFrame(Before,After),std::string(Name)+" render does not mutate state");
    Check(SameFrame(Before,FreshFrame),std::string(Name)+" reset reproduces a fresh world");
    Input Bad;Bad.AxisX=std::numeric_limits<double>::quiet_NaN();Bad.AxisY=std::numeric_limits<double>::infinity();Bad.Fire=true;
    for (int N=0;N<120;++N) { A.Step(Bad); }
    A.Render(After);Check(FiniteFrame(After),std::string(Name)+" nonfinite axes sanitized");
    std::cout << Name << " replay: " << Ticks << " frames, " << Restarts << " restarts, peak " << Peak << '/' << Limit << " entities\n";
}

void StarLifecycle() {
    StarGame G;G.SetDifficulty(StarGame::Difficulty::Easy);G.Reset(42);
    Check(G.GetPlayer().Lives==5 && G.GetSpawnRate()==135,"difficulty applies to reset");
    for (int N=0;N<120;++N) { G.Step(ReplayInput(N)); }
    G.SetPaused(true);Frame Paused,After;G.Render(Paused);const auto Snapshot=G.CaptureRun();const auto Entities=G.EntityCount();
    Input Held;Held.Right=true;Held.Fire=true;Held.AxisX=0.5;
    for (int N=0;N<200;++N) { G.Step(Held); }
    G.Render(After);Check(SameFrame(Paused,After) && SameSnapshot(Snapshot,G.CaptureRun()) && Entities==G.EntityCount(),"pause freezes world and background");
    Input Confirm;Confirm.FirePressed=true;G.Step(Confirm);Check(!G.IsPaused(),"pause Resume selection resumes");
    G.SetPaused(true);Input Down;Down.Down=true;G.Step(Down);G.Step(Confirm);
    Check(G.IsPaused() && G.WantsQuit() && G.HasSaveRequest(),"pause Save and Quit raises host request");
    Check(SameSnapshot(Snapshot,G.GetSaveRequest()),"save request captures lightweight source fields");
    G.Render(Paused);
    for (int N=0;N<200;++N) { G.Step(ReplayInput(N)); }
    G.Render(After);
    Check(SameFrame(Paused,After),"quit request freezes further gameplay");
    G.ClearSaveRequest();Check(!G.HasSaveRequest() && G.WantsQuit(),"save acknowledgement clears only save request");
    G.Reset(42);Check(!G.IsPaused() && !G.WantsQuit() && !G.HasSaveRequest(),"reset clears host lifecycle requests");
    G.SetPaused(true);Input Up;Up.Up=true;G.Step(Up);G.Step(Confirm);
    Check(G.WantsQuit() && !G.HasSaveRequest(),"Quit to Menu requests no persistence write");

    StarGame::RunSnapshot S;S.Score=12345;S.Wave=5;S.SpawnRate=70;S.Lives=8;S.Triple=true;S.Shield=true;S.SpeedBoost=true;
    S.Mode=StarGame::Difficulty::Hard;S.BossKilledThisWave=false;
    Check(G.ResumeRun(S,77),"valid source lightweight snapshot restores");
    Check(SameSnapshot(S,G.CaptureRun()),"all saved source fields restored");
    Check(G.EntityCount()==0 && G.GetPlayer().X==400 && G.GetPlayer().Y==500 && G.GetPlayer().Cooldown==0
        && G.GetPlayer().Invincible==0 && !G.IsPaused() && !G.WantsQuit() && !G.HasSaveRequest(),"restore initializes a fresh world and lifecycle");
    G.Step({});Check(G.HasBoss(),"restored boss wave recreates boss when not already defeated");
    S.BossKilledThisWave=true;Check(G.ResumeRun(S,77),"defeated-boss snapshot restores");G.Step({});Check(!G.HasBoss(),"restore does not summon already defeated boss");

    StarGame A,B;A.ResumeRun(S,73);B.ResumeRun(S,73);
    for (int N=0;N<180;++N) {A.Step(ReplayInput(N));B.Step(ReplayInput(N));}
    A.SetPaused(true);B.SetPaused(true);Frame Original;A.Render(Original);const auto OriginalSnapshot=A.CaptureRun();
    const auto OriginalStatus=A.GetStatus();const auto OriginalEntities=A.EntityCount();
    std::vector<StarGame::RunSnapshot> Invalid;
    auto Add=[&](const StarGame::RunSnapshot& Bad){Invalid.push_back(Bad);};
    auto Bad=S;Bad.Score=-1;Add(Bad);Bad=S;Bad.Score=1000000000001LL;Add(Bad);
    Bad=S;Bad.Wave=0;Add(Bad);Bad=S;Bad.Wave=1000001;Add(Bad);
    Bad=S;Bad.SpawnRate=27;Add(Bad);Bad=S;Bad.SpawnRate=136;Add(Bad);
    Bad=S;Bad.Lives=0;Add(Bad);Bad=S;Bad.Lives=100;Add(Bad);
    Bad=S;Bad.Mode=static_cast<StarGame::Difficulty>(-1);Add(Bad);Bad=S;Bad.Mode=static_cast<StarGame::Difficulty>(3);Add(Bad);
    for (const auto& InvalidSnapshot:Invalid) {
        Check(!A.ResumeRun(InvalidSnapshot,999),"invalid snapshot rejected");A.Render(After);
        Check(SameFrame(Original,After) && SameSnapshot(OriginalSnapshot,A.CaptureRun()) && SameStatus(OriginalStatus,A.GetStatus())
            && OriginalEntities==A.EntityCount() && A.IsPaused() && !A.WantsQuit() && !A.HasSaveRequest(),"invalid restore leaves complete visible state unchanged");
    }
    A.SetPaused(false);B.SetPaused(false);
    for (int N=0;N<500;++N) {
        A.Step(ReplayInput(N));B.Step(ReplayInput(N));Frame AF,BF;A.Render(AF);B.Render(BF);
        Check(SameFrame(AF,BF),"rejected snapshot preserves hidden RNG and timing state");
    }
    StarGame::Player P;P.Triple=P.Shield=P.SpeedBoost=true;P.ResetPowerups();
    Check(!P.Triple && !P.Shield && !P.SpeedBoost,"boss reward powerup reset");
    auto Bee=StarGame::Enemy::Create(StarGame::EnemyKind::Bee,5,StarGame::Difficulty::Hard,400,100,2,0,0,100);
    Check(Bee.Points()==50,"descending bee score");Bee.StartDive(400,500);Check(Bee.Points()==100,"diving bee score");
    auto Cruiser=StarGame::Enemy::Create(StarGame::EnemyKind::Cruiser,5,StarGame::Difficulty::Hard,400,100,1,0,0,100);
    Cruiser.EscortsRemaining=1;Check(Cruiser.Points()==300,"escorted cruiser score");Cruiser.EscortsRemaining=0;Check(Cruiser.Points()==600,"cleared escort bonus");
    Bee.State=StarGame::EnemyState::Descend;Bee.Update(400,500,5,StarGame::Difficulty::Hard,0,true);
    Check(Bee.State==StarGame::EnemyState::Descend,"live escort blocks dive even at zero random roll");
    Bee.Update(400,500,5,StarGame::Difficulty::Hard,0,false);Check(Bee.State==StarGame::EnemyState::Dive,"released escort permits source dive");
    Cruiser.Update(400,500,5,StarGame::Difficulty::Hard,0,false);
    Check(Cruiser.State==StarGame::EnemyState::Descend,"cruiser cannot dive even at zero random roll");

    // Sustained late-wave sessions exercise bosses and renderer capacity independently
    // from the source's deliberately lightweight save/restore contract.
    S.Mode=StarGame::Difficulty::Easy;S.Lives=99;S.Wave=15;S.SpawnRate=28;S.BossKilledThisWave=false;
    StarGame LongA,LongB;LongA.ResumeRun(S,98);LongB.ResumeRun(S,98);std::size_t Peak=0;int BossFrames=0;
    const std::size_t Limit=StarGame::MaxBullets+StarGame::MaxEnemies+StarGame::MaxPowerups+StarGame::MaxEffects+StarGame::MaxPopups+1;
    for (int N=0;N<20000;++N) {
        LongA.Step(ReplayInput(N));LongB.Step(ReplayInput(N));Peak=std::max(Peak,LongA.EntityCount());
        Check(LongA.EntityCount()<=Limit,"late-wave entity bound");if (LongA.HasBoss()) ++BossFrames;
        if (N%61==0) {Frame AF,BF;LongA.Render(AF);LongB.Render(BF);Check(SameFrame(AF,BF),"late-wave deterministic replay");Check(FiniteFrame(AF),"late-wave finite bounded render");}
        if (LongA.GetStatus().Over) {S.Wave=15;LongA.ResumeRun(S,static_cast<std::uint32_t>(N+98));LongB.ResumeRun(S,static_cast<std::uint32_t>(N+98));}
    }
    Check(BossFrames>100,"late-wave replay exercises live bosses");
    std::cout << "Star late-wave replay: 20000 frames, " << BossFrames << " boss frames, peak " << Peak << '/' << Limit << " entities\n";
}

void SerializedHostContract() {
    StarGame Source,Restored;Game& Host=Source;Game& Receiver=Restored;
    StarGame::RunSnapshot S;S.Score=45678;S.Wave=10;S.SpawnRate=46;S.Lives=7;
    S.Triple=true;S.Shield=false;S.SpeedBoost=true;S.Mode=StarGame::Difficulty::Medium;S.BossKilledThisWave=true;
    Check(Source.ResumeRun(S,909),"host test source snapshot setup");
    const std::string Payload=Host.SaveState();
    Check(Payload=="DGS1 45678 10 46 7 1 0 1 1 1","serialized nine-field source contract");
    Check(Receiver.RestoreState(Payload,909),"virtual host restore accepts serialized run");
    Check(Receiver.SaveState()==Payload && SameSnapshot(S,Restored.CaptureRun()),"virtual host nine-field roundtrip");
    Check(Host.OwnPause(true) && Host.IsCorePaused(),"virtual host pause is core-owned");
    Source.SaveAndQuit();Check(Host.SavePending() && Host.WantsExit() && Host.SaveState()==Payload,"virtual host pending save serializes captured run");
    Host.ClearSavePending();Check(!Host.SavePending() && Host.WantsExit(),"virtual host acknowledges save without resuming gameplay");

    std::vector<std::string> Invalid={"", "DGS0 1 1 90 3 0 0 0 2 0", "DGS1", "DGS1 1 1 90 3 0 0 0 2",
        "DGS1 1 1 90 3 0 0 0 2 0 trailing", "DGS1 1 1 90 3 0 0 0 2 0 1", "DGS1 1.5 1 90 3 0 0 0 2 0",
        "DGS1 99999999999999999999999999 1 90 3 0 0 0 2 0", "DGS1 1 99999999999999999999 90 3 0 0 0 2 0",
        "DGS1 -1 1 90 3 0 0 0 2 0", "DGS1 1000000000001 1 90 3 0 0 0 2 0", "DGS1 1 0 90 3 0 0 0 2 0",
        "DGS1 1 1000001 90 3 0 0 0 2 0", "DGS1 1 1 27 3 0 0 0 2 0", "DGS1 1 1 136 3 0 0 0 2 0",
        "DGS1 1 1 90 0 0 0 0 2 0", "DGS1 1 1 90 100 0 0 0 2 0", "DGS1 1 1 90 3 2 0 0 2 0",
        "DGS1 1 1 90 3 0 -1 0 2 0", "DGS1 1 1 90 3 0 0 2 2 0", "DGS1 1 1 90 3 0 0 0 3 0",
        "DGS1 1 1 90 3 0 0 0 -1 0", "DGS1 1 1 90 3 0 0 0 2 2", "DGS1 1 1 90 3 false 0 0 2 0",
        std::string(257,'x')};
    StarGame Control;Control.ResumeRun(S,909);
    for (int N=0;N<200;++N) {Restored.Step(ReplayInput(N));Control.Step(ReplayInput(N));}
    Receiver.OwnPause(true);Control.SetPaused(true);Frame Before;Restored.Render(Before);
    const auto BeforeSnapshot=Restored.CaptureRun();const auto BeforeStatus=Restored.GetStatus();const auto BeforeCount=Restored.EntityCount();
    for (const auto& Bad:Invalid) {
        Check(!Receiver.RestoreState(Bad,111),"malformed/version/overflow/range payload rejects");Frame After;Restored.Render(After);
        Check(SameFrame(Before,After) && SameSnapshot(BeforeSnapshot,Restored.CaptureRun()) && SameStatus(BeforeStatus,Restored.GetStatus())
            && BeforeCount==Restored.EntityCount() && Receiver.IsCorePaused() && !Receiver.WantsExit() && !Receiver.SavePending(),"invalid serialized restore is atomic");
    }
    Receiver.OwnPause(false);Control.SetPaused(false);
    for (int N=0;N<500;++N) {
        Restored.Step(ReplayInput(N));Control.Step(ReplayInput(N));Frame AF,BF;Restored.Render(AF);Control.Render(BF);
        Check(SameFrame(AF,BF),"invalid serialized restore preserves hidden RNG/timing");
    }
    Check(Receiver.RestoreState("DGS1 0 1 28 1 0 0 0 0 0",10),"serialized valid lower boundaries");
    Check(Receiver.RestoreState("DGS1 1000000000000 1000000 135 99 1 1 1 2 1",10),"serialized valid upper boundaries");
    DriftstoneGame Driftstone;Game& NoPersistence=Driftstone;NoPersistence.Reset(10);
    Check(NoPersistence.SaveState().rfind("DAS1 ",0)==0 && !NoPersistence.RestoreState(Payload,10),"driftstone saves its own DAS1 checkpoint and rejects Star payload");
    for (int Option=0;Option<=2;++Option) {
        Check(Receiver.SetOption(Option,84) && Receiver.GetOption()==Option,"host difficulty selection accepts source mode");
        const auto Mode=static_cast<StarGame::Difficulty>(Option);const auto Configuration=StarGame::Config(Mode);
        Check(Restored.GetPlayer().Lives==Configuration.Lives && Restored.GetSpawnRate()==Configuration.SpawnRate
            && Restored.GetWave()==1 && Restored.EntityCount()==0 && !Receiver.IsCorePaused() && !Receiver.WantsExit() && !Receiver.SavePending(),"difficulty selection restarts complete world");
    }
    Frame BeforeOption;Restored.Render(BeforeOption);const auto SnapshotBeforeOption=Restored.CaptureRun();
    for (int BadOption : {-1,3,999}) {
        Check(!Receiver.SetOption(BadOption,1),"invalid host difficulty rejects");Frame AfterOption;Restored.Render(AfterOption);
        Check(SameFrame(BeforeOption,AfterOption) && SameSnapshot(SnapshotBeforeOption,Restored.CaptureRun()),"invalid difficulty is atomic");
    }
}

void CombinedDeviceInput() {
    Input I;I.Left=true;I.PadLeft=true;I.PadUp=true;I.AxisX=0.5;
    DriftstoneGame::Ship S;S.Update(I);
    Check(S.Angle==-97 && S.Thrust,"ship preserves simultaneous keyboard, stick and D-pad source input");
    DriftstoneGame Full;Full.Reset(731);Full.Step(I);
    Check(Full.GetShip().Angle==S.Angle && Full.GetShip().Thrust==S.Thrust
        && Full.GetShip().X==S.X && Full.GetShip().Y==S.Y,"full Driftstone step binds independent device inputs");
    I={};I.PadLeft=true;I.PadRight=true;I.PadUp=true;I.PadDown=true;S=DriftstoneGame::Ship{};S.Update(I);
    Check(S.Angle==-90 && !S.Thrust,"opposed D-pad directions cancel");
    I={};I.Left=true;I.Right=true;I.PadRight=true;S=DriftstoneGame::Ship{};S.Update(I);
    Check(S.Angle==-85,"keyboard opposites cancel before independent D-pad rotation");
}

void RiftwingPlayableWin() {
    bool Won=false;std::int64_t BestScore=0;int WinningSeed=0,WinningFrames=0;std::int64_t FinalScore=0;
    for (int Seed=1;Seed<=32 && !Won;++Seed) {
        RiftwingGame G;G.Reset(static_cast<std::uint32_t>(Seed));
        for (int Tick=0;Tick<18000;++Tick) {
            Frame Visible;G.Render(Visible);const auto& P=G.GetPlayer();double TargetY=300,NearestX=10000;
            for (const auto& C:Visible.Commands) {
                double X=0,Y=0;bool Enemy=false;
                if (C.Kind==Shape::Circle && C.Tint.R==255 && C.Tint.G==80 && C.Tint.B==80 && C.Size==12) {X=C.A.X;Y=C.A.Y;Enemy=true;}
                else if (C.Kind==Shape::Triangle && C.Tint.R==255 && C.Tint.G==100 && C.Tint.B==100) {X=C.A.X-10;Y=C.A.Y;Enemy=true;}
                if (Enemy && X>P.X+24 && X<NearestX) {NearestX=X;TargetY=Y;}
            }
            const double TargetX=G.HasBoss()?500:450;
            Input I;I.Fire=true;I.Right=P.X<TargetX-2;I.Left=P.X>TargetX+2;
            I.Down=P.Y<TargetY-2;I.Up=P.Y>TargetY+2;
            G.Step(I);const auto StatusValue=G.GetStatus();BestScore=std::max(BestScore,StatusValue.Score);
            if (StatusValue.Won) {
                Won=true;WinningSeed=Seed;WinningFrames=Tick+1;FinalScore=StatusValue.Score;
                Check(!StatusValue.Over && !G.HasBoss() && StatusValue.Score>=2000,"whole-game Riftwing boss victory and score");
                Frame WinFrame,After;G.Render(WinFrame);
                for (int N=0;N<240;++N) { G.Step(I); }
                G.Render(After);Check(SameFrame(WinFrame,After) && G.GetStatus().Score==FinalScore,"Riftwing boss reward and win run once");
                break;
            }
            if (StatusValue.Over) break;
        }
    }
    Check(Won,"render-driven Riftwing pilot can reach native boss victory");
    std::cout << "Riftwing playable bot: " << (Won?"won":"no victory") << ", seed " << WinningSeed << ", frames "
              << WinningFrames << ", best score " << BestScore << '\n';
}
} // namespace

int main(int Argc,char** Argv) {
    SourceFixtures(Argc>1?Argv[1]:"shooters_parity.txt");
    Replay<DriftstoneGame>("Driftstone",DriftstoneGame::MaxBullets+DriftstoneGame::MaxRocks+DriftstoneGame::MaxUfos,20000);
    Replay<RiftwingGame>("Riftwing shooter",RiftwingGame::MaxBullets+RiftwingGame::MaxEnemies+RiftwingGame::MaxPowerups+1,20000);
    Replay<StarGame>("Lumen Barrage",StarGame::MaxBullets+StarGame::MaxEnemies+StarGame::MaxPowerups+StarGame::MaxEffects+StarGame::MaxPopups+1,20000);
    StarLifecycle();
    SerializedHostContract();
    CombinedDeviceInput();
    RiftwingPlayableWin();
    std::cout << "Shooters: " << Checks-Failures << '/' << Checks << " checks passed\n";
    return Failures?1:0;
}
