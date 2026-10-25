// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopShootersCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

using namespace daedalus::desktop;
namespace {
int Checks=0,Failed=0;
void Check(bool Ok,const std::string& What) {++Checks;if(!Ok){++Failed;std::cerr<<"FAIL "<<What<<'\n';}}
bool Close(double A,double B) {
    return std::isfinite(A) && std::isfinite(B) && std::abs(A-B)<=1e-9*std::max(1.0,std::abs(B));
}
bool SameShip(const AsteroidsGame::Ship& A,const AsteroidsGame::Ship& B) {
    // Deliberately use only pre-brake public fields so this test compiles against the preceding header.
    return A.X==B.X && A.Y==B.Y && A.Angle==B.Angle && A.Vx==B.Vx && A.Vy==B.Vy
        && A.Thrust==B.Thrust && A.Cooldown==B.Cooldown;
}
bool SameFrame(const Frame& A,const Frame& B) {
    if(A.Width!=B.Width || A.Height!=B.Height || A.Commands.size()!=B.Commands.size()
        || A.Background.R!=B.Background.R || A.Background.G!=B.Background.G
        || A.Background.B!=B.Background.B || A.Background.A!=B.Background.A) return false;
    for(std::size_t N=0;N<A.Commands.size();++N) {
        const auto& C=A.Commands[N];const auto& D=B.Commands[N];
        if(C.Kind!=D.Kind || C.A.X!=D.A.X || C.A.Y!=D.A.Y || C.B.X!=D.B.X || C.B.Y!=D.B.Y
            || C.C.X!=D.C.X || C.C.Y!=D.C.Y || C.Size!=D.Size || C.Label!=D.Label
            || C.Tint.R!=D.Tint.R || C.Tint.G!=D.Tint.G || C.Tint.B!=D.Tint.B || C.Tint.A!=D.Tint.A) return false;
    }
    return true;
}
bool SameGame(const AsteroidsGame& A,const AsteroidsGame& B) {
    Frame F,G;A.Render(F);B.Render(G);const auto S=A.GetStatus(),T=B.GetStatus();
    return SameFrame(F,G) && SameShip(A.GetShip(),B.GetShip()) && S.Score==T.Score && S.Lives==T.Lives
        && S.Over==T.Over && S.Won==T.Won && S.Note==T.Note && A.EntityCount()==B.EntityCount()
        && A.GetLevel()==B.GetLevel() && A.GetRockCount()==B.GetRockCount() && A.GetUfoCount()==B.GetUfoCount()
        && A.GetProtectionFrames()==B.GetProtectionFrames() && A.IsFireReady()==B.IsFireReady();
}
std::string Lower(std::string Text) {
    for(char& C:Text) if(C>='A' && C<='Z') C=static_cast<char>(C-'A'+'a');
    return Text;
}
bool HasText(const Frame& F,const std::string& Part) {
    const auto Wanted=Lower(Part);
    for(const auto& C:F.Commands) if(C.Kind==Shape::Text && Lower(C.Label).find(Wanted)!=std::string::npos) return true;
    return false;
}
bool StatusBraking(const AsteroidsGame& G) {return Lower(G.GetStatus().Note).find("braking")!=std::string::npos;}
std::size_t GeometryCount(const Frame& F) {
    std::size_t Count=0;for(const auto& C:F.Commands) if(C.Kind!=Shape::Text) ++Count;
    return Count;
}
Input DecodeInput(double MaskValue,double Ax,double Ay) {
    // Same key-mask translation as the existing shooters_test.cpp AST_SHIP runner.
    const int Mask=static_cast<int>(MaskValue);Input I;
    I.Left=(Mask&(1|8))!=0;I.Right=(Mask&(2|16))!=0;I.Up=(Mask&(4|32))!=0;
    I.Down=(Mask&(64|128))!=0;I.Fire=(Mask&256)!=0;I.AxisX=Ax;I.AxisY=Ay;return I;
}
std::vector<double> Numbers(const std::string& Text) {
    std::istringstream In(Text);std::vector<double> Out;double Value;
    while(In>>Value) {if(!std::isfinite(Value)) throw std::runtime_error("nonfinite fixture value");Out.push_back(Value);}
    if(!In.eof()) throw std::runtime_error("invalid fixture token");return Out;
}
void SourceShipParity(const char* Filename) {
    std::ifstream File(Filename);Check(static_cast<bool>(File),"existing source fixture file is readable");if(!File) return;
    const std::string Pin="# SOURCE asteroids_pygame_ce.py SHA256 8a46338b4d93d9447df7feab40dff21b99bfa0ce7614698681b8a5c91f0fc20b";
    std::string Line;bool SeenPin=false;int Cases=0,LineNumber=0;
    while(std::getline(File,Line)) {
        ++LineNumber;if(!Line.empty() && Line.back()=='\r') Line.pop_back();
        if(Line==Pin) SeenPin=true;
        if(Line.compare(0,9,"AST_SHIP|")!=0) continue; // No other shooter category is executed.
        try {
            const auto Second=Line.find('|',9);if(Second==std::string::npos) throw std::runtime_error("missing output delimiter");
            const auto V=Numbers(Line.substr(9,Second-9)),Expected=Numbers(Line.substr(Second+1));
            if(V.size()!=12 || Expected.size()!=7) throw std::runtime_error("unexpected AST_SHIP field count");
            if(V[11]<0 || V[11]>6000 || std::floor(V[11])!=V[11]) throw std::runtime_error("unbounded fixture step count");
            AsteroidsGame::Ship S;S.X=V[0];S.Y=V[1];S.Angle=V[2];S.Vx=V[3];S.Vy=V[4];S.Cooldown=static_cast<int>(V[5]);
            const Input I=DecodeInput(V[6],V[7],V[8]);
            for(int N=0;N<static_cast<int>(V[11]);++N) S.Update(I,static_cast<int>(V[9]),static_cast<int>(V[10]));
            const std::vector<double> Actual={S.X,S.Y,S.Angle,S.Vx,S.Vy,static_cast<double>(S.Cooldown),static_cast<double>(S.Thrust)};
            for(std::size_t N=0;N<Expected.size();++N) Check(Close(Actual[N],Expected[N]),"brake-off AST_SHIP source parity line "+std::to_string(LineNumber)+" field "+std::to_string(N));
            ++Cases;
        } catch(const std::exception& Error) {Check(false,"AST_SHIP line "+std::to_string(LineNumber)+": "+Error.what());}
    }
    Check(Cases==81,"all 81 existing Asteroids ship cases are consumed unchanged");
    Check(SeenPin,"Asteroids fixture retains its source provenance pin");
}
void BrakePhysics() {
    AsteroidsGame::Ship Base;Base.Angle=30;Base.Vx=3;Base.Vy=-4;Base.Cooldown=5;
    auto Coast=Base,Braked=Base;Input Brake;Brake.Action=true;Coast.Update({});Braked.Update(Brake);
    Check(Close(Coast.Vx,3*.985) && Close(Coast.Vy,-4*.985),"ordinary coasting retains original friction");
    Check(Close(Braked.Vx,3*.985*.8) && Close(Braked.Vy,-4*.985*.8),"braking adds damping after original friction on both axes");
    Check(Close(Braked.X,Base.X+Braked.Vx) && Close(Braked.Y,Base.Y+Braked.Vy),"brake changes displacement on the same simulation step");
    Check(Braked.Vx>0 && Braked.Vy<0 && Braked.Angle==Base.Angle && Braked.Cooldown==4,"brake preserves drift direction facing and cooldown progress");
    auto Edge=Base;Input Tap;Tap.ActionPressed=true;Edge.Update(Tap);
    Check(SameShip(Edge,Braked),"a queued action tap brakes once even after its held state was released");
    const auto AfterTap=Edge;Edge.Update({});
    Check(Close(Edge.Vx,AfterTap.Vx*.985) && Close(Edge.Vy,AfterTap.Vy*.985),"releasing brake immediately restores ordinary coasting");
    auto Down=Base;Input OldDown;OldDown.Down=true;OldDown.PadDown=true;Down.Update(OldDown);
    Check(SameShip(Down,Coast),"existing down inputs are not silently repurposed into a brake");
    AsteroidsGame::Ship Tiny;Tiny.Vx=.025;Tiny.Vy=-.026;const double X=Tiny.X,Y=Tiny.Y;Tiny.Update(Brake);
    Check(Tiny.Vx==0 && Tiny.X==X && Close(Tiny.Vy,-.026*.985*.8) && Close(Tiny.Y,Y+Tiny.Vy),"only components below the post-damping stop threshold snap to rest");
    Tiny=AsteroidsGame::Ship{};Tiny.Vx=.025;Tiny.Update({});
    Check(Tiny.Vx!=0 && Close(Tiny.Vx,.025*.985),"small unbraked drift is never snapped away");
    AsteroidsGame::Ship Stop;Stop.Vx=8;Stop.Vy=-5;
    for(int N=0;N<60;++N) Stop.Update(Brake);
    Check(Stop.Vx==0 && Stop.Vy==0,"holding brake reaches a complete stop within one second");
    const auto Rest=Stop;Stop.Update(Brake);
    Check(Stop.X==Rest.X && Stop.Y==Rest.Y && Stop.Vx==0 && Stop.Vy==0,"braking at rest cannot introduce movement");
    Stop.Angle=0;Input Thrust;Thrust.Up=true;Stop.Update(Thrust);
    Check(Stop.Thrust && Close(Stop.Vx,.15*.985) && Close(Stop.Vy,0),"releasing brake lets ordinary thrust accelerate again");
}
void PriorityTurnWrapAndFire() {
    Input Both;Both.Action=true;Both.Up=true;Both.AxisY=-1;Both.PadUp=true;
    AsteroidsGame::Ship S;S.Vx=3;S.Vy=-4;S.Update(Both,0,1);
    Check(!S.Thrust && Close(S.Vx,3*.985*.8) && Close(S.Vy,-4*.985*.8),"braking suppresses keyboard stick and hat thrust together");
    S=AsteroidsGame::Ship{};S.Update(Both,0,1);
    Check(!S.Thrust && S.Vx==0 && S.Vy==0,"opposing thrust cannot restart a stationary braking ship");
    S=AsteroidsGame::Ship{};Input Turn;Turn.Action=true;Turn.Left=true;Turn.AxisX=.5;Turn.PadRight=true;S.Update(Turn);
    Check(S.Angle==-87 && S.Vx==0 && S.Vy==0,"keyboard analog and D-pad rotation remain independent while braking");
    S=AsteroidsGame::Ship{};Input Brake;Brake.Action=true;S.Update(Brake,-1,1);
    Check(S.Angle==-95 && !S.Thrust && S.Vx==0 && S.Vy==0,"explicit source hat rotation works while hat thrust is suppressed");
    S=AsteroidsGame::Ship{};S.X=799;S.Y=1;S.Vx=4;S.Vy=-4;S.Update(Brake);
    Check(S.X==0 && S.Y==600 && Close(S.Vx,4*.985*.8) && Close(S.Vy,-4*.985*.8),"slowing drift preserves existing wrap behavior on both axes");
    S=AsteroidsGame::Ship{};S.Angle=0;S.Vx=3;S.Vy=4;S.Update(Brake);AsteroidsGame::Bullet Shot;
    Check(AsteroidsGame::Shoot(S,Shot) && S.Cooldown==8 && Shot.PlayerOwned && Shot.Life==45,
        "braking leaves the existing firing facility available");
    Check(Close(Shot.X,S.X+15) && Close(Shot.Y,S.Y) && Close(Shot.Vx,8) && Close(Shot.Vy,0),"brake does not alter projectile origin or velocity rules");
    S.Update(Brake);AsteroidsGame::Bullet Another;
    Check(S.Cooldown==7 && !AsteroidsGame::Shoot(S,Another),"braking advances cooldown without bypassing fire rate");
}
void RealGameAndPresentation() {
    AsteroidsGame G;G.Reset(730);Input Thrust;Thrust.Up=true;
    for(int N=0;N<4;++N) G.Step(Thrust);
    Check(!G.GetStatus().Over && G.GetStatus().Lives==3 && std::hypot(G.GetShip().Vx,G.GetShip().Vy)>0,"four ordinary opening thrust steps build safe observable drift");
    auto Coast=G,Braked=G;Input Brake;Brake.Action=true;Coast.Step({});Braked.Step(Brake);
    Check(std::hypot(Braked.GetShip().Vx,Braked.GetShip().Vy)<std::hypot(Coast.GetShip().Vx,Coast.GetShip().Vy)
        && Close(Braked.GetShip().Vy,Coast.GetShip().Vy*.8),"new control reduces drift through a real full-game Step");
    Check(Braked.GetStatus().Lives==Coast.GetStatus().Lives && Braked.GetStatus().Score==Coast.GetStatus().Score
        && Braked.EntityCount()==Coast.EntityCount() && Braked.GetLevel()==Coast.GetLevel(),"short brake input leaves unrelated opening progression intact");
    Frame F,CoastFrame;Braked.Render(F);Coast.Render(CoastFrame);
    Check(StatusBraking(Braked) && HasText(F,"BRAKING") && GeometryCount(F)>GeometryCount(CoastFrame),"held brake has readable status and visible ship feedback beyond a helper label");
    Check(HasText(F,"K/LT"),"rendered primary controls name the new keyboard and trigger brake");
    const auto Before=Braked;Frame Again;for(int N=0;N<8;++N) {Braked.Render(Again);Braked.GetStatus();}
    Check(SameGame(Before,Braked) && SameFrame(F,Again),"brake rendering and status reads cannot advance the simulation");
    Braked.Step({});Braked.Render(F);
    Check(!StatusBraking(Braked) && !HasText(F,"BRAKING"),"release clears active brake feedback on the next live step");
    G.Reset(730);Input Tap;Tap.ActionPressed=true;G.Step(Tap);G.Render(F);
    Check(StatusBraking(G) && HasText(F,"BRAKING"),"quick press feedback is visible even when no held input remains");
    G.Reset(730);AsteroidsGame Fresh;Fresh.Reset(730);G.Render(F);
    Check(SameGame(G,Fresh) && !StatusBraking(G) && !HasText(F,"BRAKING"),"Reset clears prior braking without changing seeded opening state");
    Input Fire;Fire.Action=Fire.Fire=Fire.FirePressed=true;const auto Entities=G.EntityCount();G.Step(Fire);
    Check(G.EntityCount()==Entities+1 && G.GetShip().Cooldown==7 && !G.GetShip().Thrust,
        "full-game brake and fire still create one ordered shot and normal cooldown");
}
void RespawnAndTerminal() {
    AsteroidsGame G;G.Reset(730);Input Brake;Brake.Action=true;int Steps=0;
    // At rest braking cannot change this existing deterministic idle-contact route.
    // One bounded run covers first respawn and eventual loss, with no per-step rendering.
    while(G.GetStatus().Lives==3 && !G.GetStatus().Over && Steps<6000) {G.Step(Brake);++Steps;}
    Check(G.GetStatus().Lives==2 && !G.GetStatus().Over,"ordinary contact supplies a real first respawn within the bounded idle route");
    if(G.GetStatus().Lives==2 && !G.GetStatus().Over) {
        Check(SameShip(G.GetShip(),AsteroidsGame::Ship{}) && G.GetProtectionFrames()>0 && !StatusBraking(G),
            "respawn clears the held brake state with the new ship and existing protection");
        G.Step(Brake);++Steps;Check(StatusBraking(G),"a later live brake input can engage again after respawn");
    }
    while(!G.GetStatus().Over && Steps<6000) {G.Step(Brake);++Steps;}
    Check(G.GetStatus().Over,"same bounded idle route reaches a genuine terminal state");
    std::cout<<"Asteroids idle terminal at "<<Steps<<" steps\n";
    if(!G.GetStatus().Over) return;
    Frame Result;G.Render(Result);
    Check(!StatusBraking(G) && !HasText(Result,"BRAKING"),"terminal presentation never advertises an active brake");
    const auto Terminal=G;Input Held;Held.Up=Held.Right=Held.Fire=Held.Action=true;Held.FirePressed=Held.ActionPressed=true;
    for(int N=0;N<8;++N) G.Step(Held);
    Check(SameGame(G,Terminal),"terminal Step stays frozen even with thrust turn fire and brake held");
    G.Reset(730);AsteroidsGame Fresh;Fresh.Reset(730);
    Check(SameGame(G,Fresh) && !StatusBraking(G),"explicit restart after the brake-held result restores the seeded clean opening");
}
}
int main(int Argc,char** Argv) {
    if(Argc!=2) {std::cerr<<"Usage: asteroids_brake_test <shooters_parity.txt>\n";return 2;}
    SourceShipParity(Argv[1]);BrakePhysics();PriorityTurnWrapAndFire();RealGameAndPresentation();RespawnAndTerminal();
    std::cout<<"Asteroids brake: "<<Checks-Failed<<'/'<<Checks<<" checks passed\n";
    return Failed?1:0;
}
