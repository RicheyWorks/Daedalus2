// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include <array>
#include <cstring>
#include <limits>
#include <sstream>
#include <string>

// Desktop-only canonical sources: PythonGames/main.py, pacman.py and zelda.py.
// See core-test/desktop_games/maze_notes.md for source pins and deliberate fixes.
// Every Step is one 60 Hz frame; callers own the bounded accumulator. Dungeon's
// Threadlight circuit is an original native extension, not Python-source parity.
namespace daedalus { namespace desktop {
namespace maze {
inline Rect PixelRect(double X, double Y, double W, double H) {
    // pygame.Rect truncates float positions toward zero before collision tests.
    return {std::trunc(X), std::trunc(Y), std::trunc(W), std::trunc(H)};
}
struct Direction { int X=0, Y=0; };
inline Direction KeyboardDirection(const Input& I) {
    Direction D;
    if(I.Left) D.X=-1;
    if(I.Right) D.X=1;
    if(I.Up) D.Y=-1;
    if(I.Down) D.Y=1;
    return D;
}
inline bool RestartPressed(const Input& I) { return I.ActionPressed || I.FirePressed || I.JumpPressed; }
inline constexpr Color Green{0,255,0,255}, Wall{0,0,180,255}, Yellow{255,255,0,255};
}

class DungeonGame final : public Game {
public:
    static constexpr int Tile=40, Columns=20, Rows=7;
    inline static constexpr std::array<const char*,Rows> Map{{
        "####################", "#.................#", "#..######.........#",
        "#.................#", "#.........####....#", "#.................#",
        "####################"
    }};
    inline static constexpr std::array<const char*,Rows> SwitchbackMap{{
        "####################", "#..................#", "#..##########.####.#",
        "#..................#", "########.#########.#", "#..................#",
        "####################"
    }};
    struct Player { double X=80, Y=80; };
    enum class CircuitStage { Lanterns, ExitUnlocked, Complete };
    static constexpr int LanternCount=3;
    // Original cabinet chapter within the existing source room; no realm quest or reward.
    inline static constexpr std::array<Vec,LanternCount> Lanterns{{{140,60},{660,140},{380,220}}};
    inline static constexpr std::array<const char*,LanternCount> LanternNames{{"Hall lantern","Watch lantern","Root lantern"}};
    inline static constexpr std::array<std::array<int,LanternCount>,6> Routes{{
        {{0,1,2}},{{0,2,1}},{{1,0,2}},{{1,2,0}},{{2,0,1}},{{2,1,0}}
    }};
    static constexpr std::uint32_t CircuitNumber(std::uint32_t Seed) {
        return Seed%static_cast<std::uint32_t>(Routes.size())+1;
    }
    static constexpr std::uint32_t NextCircuitSeed(std::uint32_t Seed) {
        // Canonical small seeds avoid signed host-seed overflow and visit every order.
        return CircuitNumber(Seed)%static_cast<std::uint32_t>(Routes.size());
    }
    inline static constexpr Vec Exit{60,220};
    static bool IsWall(int Col,int Row,int Room=0) {
        // Ragged source rows and all out-of-map coordinates are solid.
        const auto& Layout=Room==1?SwitchbackMap:Map;
        return Row<0 || Row>=Rows || Col<0 || Col>=Columns ||
            Col>=static_cast<int>(std::strlen(Layout[static_cast<std::size_t>(Row)])) ||
            Layout[static_cast<std::size_t>(Row)][Col]=='#';
    }
    static bool Collides(double X,double Y,int Room=0) {
        const int Left=static_cast<int>(std::floor(X/Tile));
        const int Right=static_cast<int>(std::floor((X+Tile-0.001)/Tile));
        const int Top=static_cast<int>(std::floor(Y/Tile));
        const int Bottom=static_cast<int>(std::floor((Y+Tile-0.001)/Tile));
        return IsWall(Left,Top,Room)||IsWall(Right,Top,Room)||IsWall(Left,Bottom,Room)||IsWall(Right,Bottom,Room);
    }
    void Reset(std::uint32_t Seed) override {
        SessionSeed=Seed; Hero={}; Order=Routes[Seed%Routes.size()];
        Lit={}; LitCount=0; RunFrames=0; Started=false; Complete=false; TrailEnabled=false;
        Notice.clear(); NoticeFrames=0;
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    void Step(const Input& I) override {
        if(I.ActionPressed) { Reset(SessionSeed); return; }
        if(Complete) return; // A fresh reset is deliberate; held interaction cannot replay.
        if(I.DashPressed) TrailEnabled=!TrailEnabled;
        if(NoticeFrames>0 && --NoticeFrames==0) Notice.clear();
        auto D=maze::KeyboardDirection(I);
        // Slate already merges hats for ordinary games; direct portable/Blueprint
        // input can provide the separate Pad fields without synthesizing keyboard keys.
        if(!I.Left && !I.Right) D.X=(I.PadRight?1:0)-(I.PadLeft?1:0);
        if(!I.Up && !I.Down) D.Y=(I.PadDown?1:0)-(I.PadUp?1:0);
        // Analog support is an adapter enhancement; digital speed remains 5/frame.
        const double X=std::abs(Axis(I.AxisX))>0.2 ? Axis(I.AxisX) : static_cast<double>(D.X);
        const double Y=std::abs(Axis(I.AxisY))>0.2 ? Axis(I.AxisY) : static_cast<double>(D.Y);
        const double Dx=X*5, Dy=Y*5;
        const Player Before=Hero;
        if(!Collides(Hero.X+Dx,Hero.Y,Option)) Hero.X+=Dx;
        if(!Collides(Hero.X,Hero.Y+Dy,Option)) Hero.Y+=Dy;
        const bool Interact=I.FirePressed || I.JumpPressed;
        Started=Started || Hero.X!=Before.X || Hero.Y!=Before.Y || Interact;
        if(Started && RunFrames<std::numeric_limits<std::uint64_t>::max()) ++RunFrames;
        if(Interact) InteractWithCircuit();
    }
    // Checkpoint save: room, circuit seed, lanterns lit in order, trail and run time.
    // Restore returns to the start tile with those lanterns lit. Completed runs are not saved.
    std::string SaveState() const override {
        if(Complete) return {};
        return "DDS1 "+std::to_string(Option)+" "+std::to_string(SessionSeed)+" "+std::to_string(LitCount)
            +" "+(TrailEnabled?"1":"0")+" "+std::to_string(RunFrames);
    }
    bool RestoreState(const std::string& Payload,std::uint32_t) override {
        if(Payload.size()>128) return false;
        std::istringstream In(Payload);std::string Version,Extra;long long Room=-1,SeedValue=-1,Count=-1,Trail=-1,Frames=-1;
        if(!(In>>Version>>Room>>SeedValue>>Count>>Trail>>Frames) || Version!="DDS1" || (In>>Extra)) return false;
        if(Room<0 || Room>1 || SeedValue<0 || SeedValue>0x7fffffffLL || Count<0 || Count>LanternCount
            || (Trail!=0 && Trail!=1) || Frames<0 || Frames>1000000000000LL) return false;
        Option=static_cast<int>(Room);Reset(static_cast<std::uint32_t>(SeedValue));
        for(int N=0;N<Count;++N) Lit[static_cast<std::size_t>(Order[static_cast<std::size_t>(N)])]=true;
        LitCount=static_cast<int>(Count);TrailEnabled=Trail==1;RunFrames=static_cast<std::uint64_t>(Frames);
        Started=Count>0 || Frames>0;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    const Player& GetPlayer() const { return Hero; }
    int GetLitCount() const { return LitCount; }
    std::uint64_t GetElapsedFrames() const { return RunFrames; }
    CircuitStage GetCircuitStage() const {
        return Complete?CircuitStage::Complete:(LitCount==LanternCount?CircuitStage::ExitUnlocked:CircuitStage::Lanterns);
    }
    void Render(Frame& Out) const override {
        Out.Clear(Columns*Tile,Rows*Tile+64,Option==1?Color{10,24,32,255}:Black);
        for(int Y=0;Y<Rows;++Y) for(int X=0;X<Columns;++X)
            if(IsWall(X,Y,Option)) {
                Out.AddRect(X*Tile,Y*Tile,Tile,Tile,Option==1?Color{110,83,55,255}:Color{100,100,100,255});
                Out.AddRect(X*Tile,Y*Tile,Tile,6,Option==1?Color{160,125,72,255}:Color{176,176,176,255});
            }
        if(TrailEnabled && !Complete) {
            const auto Path=TrailPath();
            const Color Trail{135,180,205,255};
            if(!Path.empty()) Out.AddCircle(Path[0].X,Path[0].Y,3,Trail);
            for(std::size_t N=1;N<Path.size();++N) {
                const Vec A=Path[N-1],B=Path[N];
                const int Dots=std::max(1,static_cast<int>(std::ceil((std::abs(B.X-A.X)+std::abs(B.Y-A.Y))/10.0)));
                for(int D=1;D<=Dots;++D) {
                    const double T=static_cast<double>(D)/Dots;
                    Out.AddCircle(A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T,3,Trail);
                }
            }
        }
        Out.AddRect(Hero.X,Hero.Y,Tile,Tile,maze::Green);
        for(int L=0;L<LanternCount;++L) {
            const Vec P=Lanterns[static_cast<std::size_t>(L)];
            const bool Next=LitCount<LanternCount && Order[static_cast<std::size_t>(LitCount)]==L;
            const Color Tint=Lit[static_cast<std::size_t>(L)]?Color{90,220,160,255}:(Next?maze::Yellow:Color{120,135,155,255});
            Out.AddCircle(P.X,P.Y,19,{24,28,40,255});
            Out.AddCircle(P.X,P.Y,16,Tint);
            int Number=1;
            for(int N=0;N<LanternCount;++N) if(Order[static_cast<std::size_t>(N)]==L) Number=N+1;
            const bool Dim=!Lit[static_cast<std::size_t>(L)] && !Next;
            Out.AddText(P.X-5,P.Y-10,std::to_string(Number),Dim?White:Black,17);
            if(Lit[static_cast<std::size_t>(L)]) Out.AddText(P.X-14,P.Y+18,"LIT",White,12);
            else if(Next) Out.AddText(P.X-18,P.Y+18,"NEXT",White,12);
        }
        const bool ExitOpen=LitCount==LanternCount;
        Out.AddRect(Exit.X-20,Exit.Y-20,40,40,{24,28,40,255});
        Out.AddRect(Exit.X-16,Exit.Y-16,32,32,ExitOpen?Color{80,200,255,255}:Color{95,100,120,255});
        Out.AddText(Exit.X-15,Exit.Y-8,"EXIT",ExitOpen?Black:White,12);
        DrawHeroMark(Out);
        const std::string Circuit=std::string(Option==1?"Switchback | ":"")+"Circuit "+std::to_string(CircuitNumber(SessionSeed))+"/"+std::to_string(Routes.size());
        const std::string Progress=Circuit+(Complete?" clear in "+std::to_string(RunFrames/60)+"s. K/Enter/pad B or R: replay."
            :(LitCount==LanternCount?": exit unsealed. Approach EXIT and light it."
                :": "+std::to_string(LitCount)+"/3 lit. Next: "+LanternNames[static_cast<std::size_t>(Order[static_cast<std::size_t>(LitCount)])]));
        Out.AddText(12,Rows*Tile+8,Progress,White,16);
        const std::string Controls=std::string("Move: WASD/arrows/stick/hat. J/Space/pad A/X: light. K/Enter/pad B: reset. Shift/pad Y: trail ")+(TrailEnabled?"ON":"OFF");
        Out.AddText(12,Rows*Tile+35,Notice.empty()?Controls:Notice,White,14);
        Out.AddText(12,Rows*Tile+54,HintLine(),Color{255,236,180,255},14);
        Out.AddText(520,Rows*Tile+54,ActionCue(),Color{120,225,255,255},14);
    }
    std::string HintLine() const {
        if(Complete) return "HINT Action or R replays this circuit.";
        if(LitCount==LanternCount) return "HINT Walk to the cyan EXIT and press Fire or Jump.";
        return "HINT Light the lantern marked NEXT. Shift or pad Y shows the trail.";
    }
    std::string ActionCue() const {
        if(Complete) return "CUE Replay";
        if(LitCount==LanternCount) return "CUE Exit";
        return "CUE Next lantern";
    }
    // White corners paint after lanterns and the exit so the player tile stays
    // readable when it overlaps them. The green body stays underneath.
    void DrawHeroMark(Frame& Out) const {
        const double X=Hero.X, Y=Hero.Y;
        const Color Ink{255,255,255,255};
        constexpr double Arm=8, Thick=3;
        Out.AddRect(X,Y,Arm,Thick,Ink); Out.AddRect(X,Y,Thick,Arm,Ink);
        Out.AddRect(X+Tile-Arm,Y,Arm,Thick,Ink); Out.AddRect(X+Tile-Thick,Y,Thick,Arm,Ink);
        Out.AddRect(X,Y+Tile-Thick,Arm,Thick,Ink); Out.AddRect(X,Y+Tile-Arm,Thick,Arm,Ink);
        Out.AddRect(X+Tile-Arm,Y+Tile-Thick,Arm,Thick,Ink); Out.AddRect(X+Tile-Thick,Y+Tile-Arm,Thick,Arm,Ink);
    }
    Status GetStatus() const override {
        std::string Text=std::string(Option==1?"Threadlight Switchback circuit ":"Threadlight circuit ")+std::to_string(CircuitNumber(SessionSeed))+"/"+std::to_string(Routes.size())+": ";
        Text+=Complete?"complete; Action/R replays."
            :(LitCount==LanternCount?"Exit unlocked; approach EXIT and press Fire/Jump."
                :std::to_string(LitCount)+"/3: seek "+LanternNames[static_cast<std::size_t>(Order[static_cast<std::size_t>(LitCount)])]+"; Fire/Jump lights, Action resets.");
        if(!Complete) Text+=TrailEnabled?" Trail ON; Shift/pad Y toggles.":" Trail OFF; Shift/pad Y toggles.";
        if(!Notice.empty()) Text+=" "+Notice;
        return {0,1,Complete,Complete,Text}; // Local completion only; no invented score/reward.
    }
private:
    std::vector<Vec> TrailPath() const {
        // The room has only 140 possible player-sized anchors. Each is queued once.
        constexpr int Count=Columns*Rows;
        const int StartX=static_cast<int>(std::floor(Hero.X/Tile));
        const int StartY=static_cast<int>(std::floor(Hero.Y/Tile));
        const Vec Target=LitCount<LanternCount?Lanterns[static_cast<std::size_t>(Order[static_cast<std::size_t>(LitCount)])]:Exit;
        const int GoalX=static_cast<int>(Target.X/Tile),GoalY=static_cast<int>(Target.Y/Tile);
        if(Collides(Hero.X,Hero.Y,Option) || Collides(StartX*Tile,StartY*Tile,Option) || Collides(GoalX*Tile,GoalY*Tile,Option)) return {};
        const int Start=StartY*Columns+StartX,Goal=GoalY*Columns+GoalX;
        std::array<int,Count> Parent{},Queue{};Parent.fill(-1);
        int Head=0,Tail=0;Queue[static_cast<std::size_t>(Tail++)]=Start;Parent[static_cast<std::size_t>(Start)]=Start;
        constexpr std::array<maze::Direction,4> Directions{{{1,0},{0,1},{-1,0},{0,-1}}};
        while(Head<Tail && Parent[static_cast<std::size_t>(Goal)]<0) {
            const int Node=Queue[static_cast<std::size_t>(Head++)];
            for(const auto D:Directions) {
                const int X=Node%Columns+D.X,Y=Node/Columns+D.Y;
                if(X<0 || X>=Columns || Y<0 || Y>=Rows || Collides(X*Tile,Y*Tile,Option)) continue;
                const int Next=Y*Columns+X;
                if(Parent[static_cast<std::size_t>(Next)]>=0) continue;
                Parent[static_cast<std::size_t>(Next)]=Node;Queue[static_cast<std::size_t>(Tail++)]=Next;
            }
        }
        if(Parent[static_cast<std::size_t>(Goal)]<0) return {};
        std::array<int,Count> Reverse{};int Length=0;
        for(int Node=Goal;Node!=Start;Node=Parent[static_cast<std::size_t>(Node)]) Reverse[static_cast<std::size_t>(Length++)]=Node;
        std::vector<Vec> Path;Path.reserve(static_cast<std::size_t>(Length)+3);
        Path.push_back({Hero.X+Tile/2.0,Hero.Y+Tile/2.0});
        const auto Append=[&Path](Vec P) {if(P.X!=Path.back().X || P.Y!=Path.back().Y) Path.push_back(P);};
        // Decreasing X then Y removes occupied edge cells; it cannot cut a blocked corner.
        Append({StartX*Tile+Tile/2.0,Hero.Y+Tile/2.0});
        Append({StartX*Tile+Tile/2.0,StartY*Tile+Tile/2.0});
        for(int N=Length-1;N>=0;--N) {
            const int Node=Reverse[static_cast<std::size_t>(N)];
            Append({(Node%Columns)*Tile+Tile/2.0,(Node/Columns)*Tile+Tile/2.0});
        }
        return Path;
    }
    bool Near(Vec P) const { return Distance(Hero.X+Tile/2.0,Hero.Y+Tile/2.0,P.X,P.Y)<=Tile*0.8; }
    void Say(const std::string& Text) { Notice=Text; NoticeFrames=90; }
    void InteractWithCircuit() {
        if(Near(Exit)) {
            if(LitCount==LanternCount) { Complete=true; Say("The way home is lit. Circuit complete."); }
            else Say("The exit is sealed. Light all three numbered lanterns in order.");
            return;
        }
        for(int L=0;L<LanternCount;++L) {
            if(!Near(Lanterns[static_cast<std::size_t>(L)])) continue;
            if(Lit[static_cast<std::size_t>(L)]) Say("This lantern is already lit.");
            else if(LitCount<LanternCount && Order[static_cast<std::size_t>(LitCount)]==L) {
                Lit[static_cast<std::size_t>(L)]=true; ++LitCount;
                Say(LitCount==LanternCount?"All three lanterns are lit. The exit is unsealed."
                    :std::string(LanternNames[static_cast<std::size_t>(L)])+" lit. Follow the next numbered lantern.");
            }
            else Say("Not yet: follow the lantern marked NEXT. No progress was lost.");
            return;
        }
        Say("Move close to a numbered lantern or EXIT, then press J/Space or pad A/X.");
    }
    Player Hero;
    std::uint32_t SessionSeed=0;
    std::array<int,LanternCount> Order{{0,1,2}};
    friend struct MazeTestAccess; // Controlled test seam, as for Pac-Man and Zelda.
    std::array<bool,LanternCount> Lit{};
    int LitCount=0, NoticeFrames=0,Option=0;
    std::uint64_t RunFrames=0;
    bool Started=false, Complete=false, TrailEnabled=false;
    std::string Notice;
};

class PacmanGame final : public Game {
public:
    static constexpr int Tile=20, Columns=28, Rows=31;
    static constexpr int RespawnGraceFrames=90; // Native rule extension after a nonterminal death.
    static constexpr int FruitLifetimeFrames=1200,FruitPoints=100;
    inline static constexpr Vec FruitSpot{270,350};
    inline static constexpr std::array<const char*,Rows> Map{{
        "############################", "#............##............#",
        "#.####.#####.##.#####.####.#", "#.####.#####.##.#####.####.#",
        "#.####.#####.##.#####.####.#", "#..........................#",
        "#.####.##.########.##.####.#", "#.####.##.########.##.####.#",
        "#......##....##....##......#", "######.#####.##.#####.######",
        "######.#####.##.#####.######", "######.##..........##.######",
        "######.##.########.##.######", "######.##.########.##.######",
        "........##........##........", "######.##.########.##.######",
        "######.##.########.##.######", "######.##..........##.######",
        "######.##.########.##.######", "######.##.########.##.######",
        "#............##............#", "#.####.#####.##.#####.####.#",
        "#.####.#####.##.#####.####.#", "#...##................##...#",
        "###.##.##.########.##.##.###", "###.##.##.########.##.##.###",
        "#......##....##....##......#", "#.##########.##.##########.#",
        "#.##########.##.##########.#", "#..........................#",
        "############################"
    }};
    static bool IsWall(int Col,int Row,bool RepairDoor=true) {
        if(Row<0 || Row>=Rows || Col<0 || Col>=Columns) return true;
        return !(RepairDoor && Row==14 && Col==9) && Map[static_cast<std::size_t>(Row)][Col]=='#';
    }
    static bool IsTunnelBody(double X,double Y) {
        if(!(X>=-8 && X<=Columns*Tile+8)) return false;
        const Rect R=maze::PixelRect(X-8,Y-8,16,16);
        return R.Y>=14*Tile && R.Y+15<15*Tile;
    }
    static bool IsTunnelActor(double X,double Y) {
        return X>=0 && X<Columns*Tile && IsTunnelBody(X,Y);
    }
    static double WrapTunnelX(double X) {
        return X<0 ? X+Columns*Tile : X>=Columns*Tile ? X-Columns*Tile : X;
    }
    static bool ClearTunnelApproach(double X,bool Left,bool RepairDoor=true) {
        // Canonical actors only. Row 14 also contains walls around the center room.
        const Rect Body=maze::PixelRect(X-8,14*Tile,16,16);
        for(int Col=0;Col<Columns;++Col) {
            const bool OnRoute=Left?Col*Tile<=Body.X+15:(Col+1)*Tile>Body.X;
            if(OnRoute && IsWall(Col,14,RepairDoor)) return false;
        }
        return true;
    }
    static bool Collides(double X,double Y,bool RepairDoor=true,bool UseTunnels=true) {
        const Rect R=maze::PixelRect(X-8,Y-8,16,16);
        const int C0=static_cast<int>(std::floor(R.X/Tile)), C1=static_cast<int>(std::floor((R.X+15)/Tile));
        const int R0=static_cast<int>(std::floor(R.Y/Tile)), R1=static_cast<int>(std::floor((R.Y+15)/Tile));
        const bool Wrap=UseTunnels && IsTunnelBody(X,Y);
        for(int Row=R0;Row<=R1;++Row) for(int Col=C0;Col<=C1;++Col) {
            const int WallCol=Wrap ? (Col+Columns)%Columns : Col;
            if(IsWall(WallCol,Row,RepairDoor)) return true;
        }
        return false;
    }
    struct Player {
        double X=290, Y=470;
        maze::Direction Dir, Next;
        int Mouth=0;
        Rect GetRect() const { return maze::PixelRect(X-8,Y-8,16,16); }
        void Update(const Input& I,bool RepairDoor=true,bool UseTunnels=true) {
            // Match the cabinet's digital merge for direct portable/Blueprint Pad input.
            if(I.Left || I.PadLeft) Next={-1,0};
            if(I.Right || I.PadRight) Next={1,0};
            if(I.Up || I.PadUp) Next={0,-1};
            if(I.Down || I.PadDown) Next={0,1};
            const double Sx=Axis(I.AxisX), Sy=Axis(I.AxisY);
            if(std::abs(Sx)>0.3 || std::abs(Sy)>0.3)
                Next=std::abs(Sx)>std::abs(Sy) ? maze::Direction{Sx>0 ? 1 : -1,0} : maze::Direction{0,Sy>0 ? 1 : -1};
            if(!Collides(X+Next.X*2.5,Y+Next.Y*2.5,RepairDoor,UseTunnels)) Dir=Next;
            const double Nx=X+Dir.X*2.5, Ny=Y+Dir.Y*2.5;
            if(!Collides(Nx,Ny,RepairDoor,UseTunnels)) {
                X=UseTunnels && IsTunnelBody(Nx,Ny) ? WrapTunnelX(Nx) : Nx; Y=Ny;
            }
            // Source slide branches only vary a zero component; retain no movement on obstruction.
            Mouth=(Mouth+1)%20;
            if(!UseTunnels || !IsTunnelActor(X,Y)) X=Clamp(X,10,Columns*Tile-10);
            Y=Clamp(Y,10,Rows*Tile-10);
        }
    };
    struct Ghost {
        double X=290, Y=230;
        maze::Direction Dir;
        Color Tint{255,0,0,255};
        bool Alive=true, Frightened=false;
        int FrightenedTimer=0;
        Rect GetRect() const { return maze::PixelRect(X-8,Y-8,16,16); }
        void UpdateWithChoices(const Player& TargetPlayer,double TurnSample,double ChaseSample,
                const std::array<maze::Direction,4>& Dirs,bool RepairDoor=true,bool UseTunnels=true) {
            if(!Alive) return;
            if(Frightened && --FrightenedTimer<=0) Frightened=false;
            if(TurnSample<0.05 || Collides(X+Dir.X*2,Y+Dir.Y*2,RepairDoor,UseTunnels)) {
                for(const auto D:Dirs) if(!Collides(X+D.X*2,Y+D.Y*2,RepairDoor,UseTunnels)) { Dir=D; break; }
            }
            if(!Frightened && ChaseSample<0.6) {
                double Dx=TargetPlayer.X-X;
                const double Dy=TargetPlayer.Y-Y;
                if(UseTunnels && IsTunnelActor(X,Y) && IsTunnelActor(TargetPlayer.X,TargetPlayer.Y)) {
                    const double Width=Columns*Tile;
                    if(Dx>Width/2 && ClearTunnelApproach(X,true,RepairDoor) && ClearTunnelApproach(TargetPlayer.X,false,RepairDoor)) Dx-=Width;
                    else if(Dx<-Width/2 && ClearTunnelApproach(X,false,RepairDoor) && ClearTunnelApproach(TargetPlayer.X,true,RepairDoor)) Dx+=Width;
                }
                const maze::Direction D=std::abs(Dx)>std::abs(Dy) ? maze::Direction{Dx>0 ? 1 : -1,0} : maze::Direction{0,Dy>0 ? 1 : -1};
                if(!Collides(X+D.X*2,Y+D.Y*2,RepairDoor,UseTunnels)) Dir=D;
            }
            const double Nx=X+Dir.X*2, Ny=Y+Dir.Y*2;
            if(!Collides(Nx,Ny,RepairDoor,UseTunnels)) {
                X=UseTunnels && IsTunnelBody(Nx,Ny) ? WrapTunnelX(Nx) : Nx; Y=Ny;
            }
        }
        void Update(const Player& TargetPlayer,Random& RandomStream) {
            if(!Alive) return;
            const double TurnSample=RandomStream.Unit(), ChaseSample=RandomStream.Unit();
            std::array<maze::Direction,4> Dirs{{{1,0},{-1,0},{0,1},{0,-1}}};
            for(int I=3;I>0;--I) std::swap(Dirs[static_cast<std::size_t>(I)],Dirs[static_cast<std::size_t>(RandomStream.Int(0,I))]);
            UpdateWithChoices(TargetPlayer,TurnSample,ChaseSample,Dirs);
        }
    };
    struct Pellet { double X=0, Y=0; bool Power=false, Alive=true; };
    static double DistanceToPellet(const Player& P,const Pellet& Dot) {
        if(!IsTunnelActor(P.X,P.Y) || Dot.Y!=14*Tile+Tile/2 || Dot.X<0 || Dot.X>=Columns*Tile)
            return Distance(P.X,P.Y,Dot.X,Dot.Y);
        const double Dx=std::abs(P.X-Dot.X), Dy=P.Y-Dot.Y;
        const double WrappedDx=std::min(Dx,Columns*Tile-Dx);
        return std::sqrt(WrappedDx*WrappedDx+Dy*Dy);
    }
    static bool TouchesGhost(const Player& P,const Ghost& G) {
        const Rect A=P.GetRect(); Rect B=G.GetRect();
        if(A.Overlaps(B)) return true;
        if(!IsTunnelActor(P.X,P.Y) || !IsTunnelActor(G.X,G.Y)) return false;
        B.X+=Columns*Tile;
        if(A.Overlaps(B)) return true;
        B.X-=2*Columns*Tile;
        return A.Overlaps(B);
    }
    PacmanGame() { Reset(730); }
    void Reset(std::uint32_t Seed) override {
        SessionSeed=Seed; Rng.Seed(Seed); Hero={}; Score=0; Lives=3; Over=false; Won=false; Level=1; RespawnFrames=0;
        Pellets.clear();
        for(int Row=0;Row<Rows;++Row) for(int Col=0;Col<Columns;++Col) if(Map[static_cast<std::size_t>(Row)][Col]=='.') {
            const bool Power=(Row==1 || Row==29) && (Col==1 || Col==26);
            Pellets.push_back({Col*Tile+10.0,Row*Tile+10.0,Power,true});
        }
        Remaining=static_cast<int>(Pellets.size());
        Ghosts={{{290,230,{}, {255,0,0,255}}, {250,290,{}, {255,182,193,255}},
                 {290,290,{}, {0,255,255,255}}, {330,290,{}, {255,165,0,255}}}};
        const std::array<maze::Direction,4> Dirs{{{1,0},{-1,0},{0,1},{0,-1}}};
        for(auto& G:Ghosts) G.Dir=Dirs[static_cast<std::size_t>(Rng.Int(0,3))];
        FruitFrames=FruitIssued=FruitCollected=0;FruitPending=false;
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    // Checkpoint save: mode, score and lives. Restore starts a fresh maze on the
    // session seed with that score and lives. Finished runs are not saved.
    std::string SaveState() const override {
        if(Over || Won) return {};
        return "DMS1 "+std::to_string(Option)+" "+std::to_string(Score)+" "+std::to_string(Lives);
    }
    bool RestoreState(const std::string& Payload,std::uint32_t Seed) override {
        if(Payload.size()>128) return false;
        std::istringstream In(Payload);std::string Version,Extra;long long Mode=-1,Points=-1,Left=-1;
        if(!(In>>Version>>Mode>>Points>>Left) || Version!="DMS1" || (In>>Extra)) return false;
        if(Mode<0 || Mode>1 || Points<0 || Points>1000000000LL || Left<1 || Left>3) return false;
        Option=static_cast<int>(Mode);Reset(Seed);Score=static_cast<decltype(Score)>(Points);Lives=static_cast<int>(Left);
        return true;
    }
    bool IsFruitActive() const { return Option==1 && !Over && !Won && FruitFrames>0; }
    int FruitFramesRemaining() const { return IsFruitActive()?FruitFrames:0; }
    int FruitsCollected() const { return FruitCollected; }
    void Step(const Input& I) override {
        if(Over || Won) { if(maze::RestartPressed(I)) Reset(SessionSeed); return; }
        const bool FruitIdleAtStart=FruitFrames==0;
        const int LivesAtStart=Lives;
        if(Option==1 && FruitFrames>0) --FruitFrames;
        // Snapshot before ticking: a new 90-step guard protects exactly the next
        // 90 live collision steps. Movement, pellets, frightened captures and RNG stay live.
        const bool ProtectedThisStep=RespawnFrames>0;
        if(ProtectedThisStep) --RespawnFrames;
        Hero.Update(I);
        for(auto& G:Ghosts) G.Update(Hero,Rng);
        for(auto& P:Pellets) if(P.Alive && DistanceToPellet(Hero,P)<12) {
            P.Alive=false; --Remaining; Score+=P.Power ? 50 : 10;
            if(P.Power) for(auto& G:Ghosts) { G.Frightened=true; G.FrightenedTimer=300; }
        }
        for(auto& G:Ghosts) if(G.Alive && TouchesGhost(Hero,G)) {
            if(G.Frightened) { G.Alive=false; Score+=200; }
            else if(!ProtectedThisStep) {
                --Lives;
                if(Lives<=0) Over=true;
                else { Hero={}; RespawnFrames=RespawnGraceFrames; }
                // One lethal collision per frame; source could consume all lives in one stacked collision.
                break;
            }
        }
        if(!Over && Remaining==0) { Won=true; ++Level; }
        if(std::all_of(Ghosts.begin(),Ghosts.end(),[](const Ghost& G){return !G.Alive;}))
            for(auto& G:Ghosts) { G.Alive=true; G.X=290; G.Y=290; }
        if(Option==1) UpdateFruit(FruitIdleAtStart,Lives==LivesAtStart);
    }
    const Player& GetPlayer() const { return Hero; }
    const std::array<Ghost,4>& GetGhosts() const { return Ghosts; }
    const std::vector<Pellet>& GetPellets() const { return Pellets; }
    int DotsLeft() const { return Remaining; }
    int GetLevel() const { return Level; }
    int RespawnFramesRemaining() const { return RespawnFrames; }
    int PowerPelletsLeft() const {
        return static_cast<int>(std::count_if(Pellets.begin(),Pellets.end(),[](const Pellet& P){return P.Alive && P.Power;}));
    }
    // Presentation only: the shortest living timer marks first recovery, not group safety.
    struct PowerWindow {
        int Alive=0,Frightened=0,Frames=0;
        int Seconds() const { return Frames/60+(Frames%60>0?1:0); }
    };
    PowerWindow GetPowerWindow() const {
        PowerWindow Out;
        for(const auto& G:Ghosts) if(G.Alive) {
            ++Out.Alive;
            if(G.Frightened) {
                const int Frames=std::max(0,G.FrightenedTimer);
                if(Out.Frightened==0 || Frames<Out.Frames) Out.Frames=Frames;
                ++Out.Frightened;
            }
        }
        return Out;
    }
    void Render(Frame& Out) const override {
        // Source map is 620 pixels tall but its 600-pixel viewport clipped the bottom wall.
        Out.Clear(800,660,Black);
        for(int Row=0;Row<Rows;++Row) for(int Col=0;Col<Columns;++Col)
            if(IsWall(Col,Row)) {
                Out.AddRect(Col*Tile,Row*Tile,Tile,Tile,maze::Wall);
                Out.AddRect(Col*Tile,Row*Tile,Tile,4,{110,150,255,255});
            }
        const Color Gate{80,200,255,255};
        for(int Side=0;Side<2;++Side) {
            const double X=Side==0 ? 1 : Columns*Tile-7;
            Out.AddRect(X,14*Tile+2,6,2,Gate); Out.AddRect(X,15*Tile-4,6,2,Gate);
            Out.AddRect(Side==0 ? X : X+4,14*Tile+2,2,16,Gate);
        }
        for(const auto& P:Pellets) if(P.Alive) Out.AddCircle(P.X,P.Y,P.Power ? 6 : 3,P.Power ? Color{255,204,40,255} : White);
        if(IsFruitActive()) {
            const double X=FruitSpot.X,Y=FruitSpot.Y;
            Out.AddCircle(X,Y,11,{95,50,40,255});
            Out.AddCircle(X-3,Y+1,7,{255,120,85,255});Out.AddCircle(X+3,Y+1,7,{255,95,100,255});
            Out.AddTriangle({X,Y-5},{X+8,Y-12},{X+4,Y-4},{75,215,100,255});
            Out.AddCircle(X-4,Y-2,2,White);
        }
        const bool ShowGrace=RespawnFrames>0 && !Over && !Won;
        const double Angle=Hero.Dir.X<0 ? 3.141592653589793 : Hero.Dir.Y<0 ? -1.5707963267948966 : Hero.Dir.Y>0 ? 1.5707963267948966 : 0;
        const double Mouth=(30+std::abs(std::sin(Hero.Mouth/5.0)*25))*3.141592653589793/180;
        const auto DrawHero=[&](double X) {
            if(ShowGrace) Out.AddCircle(X,Hero.Y,14,{80,200,255,255});
            Out.AddCircle(X,Hero.Y,12,{24,24,24,255});
            Out.AddCircle(X,Hero.Y,10,maze::Yellow);
            Out.AddTriangle({X,Hero.Y},{X+10*std::cos(Angle-Mouth),Hero.Y+10*std::sin(Angle-Mouth)},
                {X+10*std::cos(Angle+Mouth),Hero.Y+10*std::sin(Angle+Mouth)},Black);
        };
        DrawHero(Hero.X);
        if(IsTunnelActor(Hero.X,Hero.Y)) {
            const double Extent=ShowGrace ? 14 : 10;
            if(Hero.X<Extent) DrawHero(Hero.X+Columns*Tile);
            else if(Hero.X+Extent>Columns*Tile) DrawHero(Hero.X-Columns*Tile);
        }
        for(const auto& G:Ghosts) if(G.Alive) {
            const Color C=G.Frightened ? Color{190,210,255,255} : G.Tint;
            const auto DrawGhost=[&](double X) {
                Out.AddCircle(X,G.Y,12,{12,16,48,255});
                if(G.Frightened) Out.AddCircle(X,G.Y,11,White);
                Out.AddCircle(X,G.Y,9,C); Out.AddRect(X-9,G.Y,18,8,C);
                Out.AddCircle(X-4,G.Y-3,4,{24,28,48,255}); Out.AddCircle(X+4,G.Y-3,4,{24,28,48,255});
                Out.AddCircle(X-4,G.Y-3,3,White); Out.AddCircle(X+4,G.Y-3,3,White);
                Out.AddCircle(X-4,G.Y-3,1,Black); Out.AddCircle(X+4,G.Y-3,1,Black);
            };
            DrawGhost(G.X);
            if(IsTunnelActor(G.X,G.Y)) {
                if(G.X<9) DrawGhost(G.X+Columns*Tile);
                else if(G.X+9>Columns*Tile) DrawGhost(G.X-Columns*Tile);
            }
        }
        Out.AddRect(Columns*Tile,0,800-Columns*Tile,Rows*Tile,Black);
        const std::string Footer="SCORE "+std::to_string(Score)+"  LIVES "+std::to_string(Lives)+"  LEVEL "+std::to_string(Level);
        Out.AddText(10,630,Footer+(Option==1?"  |  "+FruitNote():""),White,Option==1?17:20);
        Out.AddText(580,136,"GLOWTRAIL",maze::Yellow,22);
        Out.AddText(580,162,"CHASE",maze::Yellow,22);
        Out.AddText(580,190,"Move: arrows / WASD / stick",White,14);
        Out.AddText(580,225,"Dots left: "+std::to_string(Remaining),White,16);
        Out.AddText(580,250,"Power pellets: "+std::to_string(PowerPelletsLeft()),White,14);
        if(!Over && !Won) {
            const auto Window=GetPowerWindow();
            Out.AddText(580,275,"Frightened: "+std::to_string(Window.Frightened)+"/"+std::to_string(Window.Alive)+" alive",White,14);
            if(Window.Frightened>0) {
                Out.AddText(580,297,"First recovery: "+std::to_string(Window.Seconds())+"s",White,13);
                if(Window.Frames<=60) Out.AddText(580,319,"FINAL SECOND",{255,180,80,255},13);
            }
            else Out.AddText(580,297,"No active fright window",White,13);
            if(RespawnFrames>0)
                Out.AddText(580,345,"Respawn grace: "+std::to_string(RespawnFrames)+" steps",{80,200,255,255},13);
        }
        if(Over || Won) Out.AddText(580,320,Won ? "YOU WIN!" : "GAME OVER",maze::Yellow,24);
        if(Over || Won) Out.AddText(580,360,"Pad A / Space / Enter",White,14);
        if(Over || Won) Out.AddText(580,383,"or R / Restart: replay",White,14);
    }
    Status GetStatus() const override {
        std::string Text=Won?"All dots cleared. Pad A / Space / Enter / R: replay."
            :(Over?"Game over. Pad A / Space / Enter / R: replay."
                :"Glowtrail Chase: "+std::to_string(Remaining)+" dots left; "+std::to_string(PowerPelletsLeft())+" power pellets.");
        if(!Over && !Won) {
            const auto Window=GetPowerWindow();
            Text+=" Frightened "+std::to_string(Window.Frightened)+"/"+std::to_string(Window.Alive)+" alive.";
            if(Window.Frightened>0) Text+=" First recovery: "+std::to_string(Window.Seconds())+"s"+(Window.Frames<=60?" (final second).":".");
            if(RespawnFrames>0) Text+=" Respawn grace: "+std::to_string(RespawnFrames)+" steps.";
        }
        if(Option==1) Text+=" "+FruitNote()+".";
        return {Score,Lives,Over,Won,Text};
    }
private:
    friend struct MazeTestAccess;
    std::uint32_t SessionSeed=730;
    Random Rng;
    Player Hero;
    std::array<Ghost,4> Ghosts;
    std::vector<Pellet> Pellets;
    std::int64_t Score=0;
    int Lives=3, Remaining=0, Level=1, RespawnFrames=0;
    bool Over=false, Won=false;
    int Option=0,FruitFrames=0,FruitIssued=0,FruitCollected=0;
    bool FruitPending=false;
    inline static constexpr std::array<int,2> FruitMilestones{{76,228}};
    void UpdateFruit(bool IdleAtStart,bool MayCollect) {
        if(Over || Won) return; // Dot-clear/death results settle before optional fruit.
        const int Eaten=static_cast<int>(Pellets.size())-Remaining;
        if(FruitIssued<static_cast<int>(FruitMilestones.size()) && Eaten>=FruitMilestones[static_cast<std::size_t>(FruitIssued)]) {
            ++FruitIssued;FruitPending=true;
        }
        if(IdleAtStart && FruitFrames==0 && FruitPending) { FruitFrames=FruitLifetimeFrames;FruitPending=false; }
        if(MayCollect && IsFruitActive() && Distance(Hero.X,Hero.Y,FruitSpot.X,FruitSpot.Y)<12) {
            Score+=FruitPoints;FruitFrames=0;++FruitCollected;
        }
    }
    std::string FruitNote() const {
        const std::string Count="FRUIT "+std::to_string(FruitCollected)+"/2";
        if(Over || Won) return Count;
        if(IsFruitActive()) return Count+" "+std::to_string(FruitPoints)+"pt / "+std::to_string((FruitFrames+59)/60)+"s"+(FruitPending?" +1 queued":"");
        if(FruitPending) return Count+" queued";
        if(FruitIssued<static_cast<int>(FruitMilestones.size()))
            return Count+" in "+std::to_string(FruitMilestones[static_cast<std::size_t>(FruitIssued)]-(static_cast<int>(Pellets.size())-Remaining))+" dots";
        return Count;
    }
};

class ZeldaGame final : public Game {
public:
    enum class Facing { Right, Left, Up, Down };
    enum class EnemyKind { Octorok, Moblin, Armos };
    enum class PickupKind { Rupee, Heart, Key };
    static constexpr std::size_t MaxProjectiles=128, MaxCollectibles=16;
    struct Player {
        double X=400, Y=450;
        int Health=6, MaxHealth=6, AttackTimer=0, Invincible=0, Rupees=0;
        Facing Face=Facing::Down;
        bool Attacking=false;
        Rect GetRect() const { return maze::PixelRect(X-10,Y-10,20,24); }
        Rect GetAttackRect() const {
            if(Face==Facing::Right) return maze::PixelRect(X+5,Y-8,30,16);
            if(Face==Facing::Left) return maze::PixelRect(X-35,Y-8,30,16);
            if(Face==Facing::Up) return maze::PixelRect(X-8,Y-45,16,30);
            return maze::PixelRect(X-8,Y+10,16,30);
        }
        bool Attack() {
            if(AttackTimer!=0) return false;
            Attacking=true; AttackTimer=18; return true;
        }
        void Update(const Input& I) {
            double Dx=0, Dy=0;
            // Direct Pad input mirrors the existing Slate merge; preserve the
            // source's direction/facing precedence, then its analog override.
            if(I.Left || I.PadLeft) { Dx=-1; Face=Facing::Left; }
            if(I.Right || I.PadRight) { Dx=1; Face=Facing::Right; }
            if(I.Up || I.PadUp) { Dy=-1; Face=Facing::Up; }
            if(I.Down || I.PadDown) { Dy=1; Face=Facing::Down; }
            const double RawX=Axis(I.AxisX), RawY=Axis(I.AxisY);
            const double Sx=std::abs(RawX)>0.15 ? RawX : 0, Sy=std::abs(RawY)>0.15 ? RawY : 0;
            if(std::abs(Sx)>0.2 || std::abs(Sy)>0.2) {
                Face=std::abs(Sx)>std::abs(Sy) ? (Sx>0 ? Facing::Right : Facing::Left) : (Sy>0 ? Facing::Down : Facing::Up);
                Dx=Sx; Dy=Sy;
            }
            if(Dx!=0 && Dy!=0) { Dx*=0.707; Dy*=0.707; }
            X=Clamp(X+Dx*3.5,20,780); Y=Clamp(Y+Dy*3.5,20,580);
            if(AttackTimer>0) --AttackTimer;
            if(Attacking && AttackTimer==0) Attacking=false;
            if(Invincible>0) --Invincible;
        }
    };
    struct Enemy {
        double X=0, Y=0;
        EnemyKind Kind=EnemyKind::Octorok;
        int Health=1, ShootTimer=60, HitFlash=0;
        bool Alive=true;
        Rect GetRect() const { return maze::PixelRect(X-10,Y-10,20,20); }
        bool Update(const Player& TargetPlayer,Random& RandomStream) {
            if(!Alive) return false;
            if(HitFlash>0) --HitFlash;
            if(Kind==EnemyKind::Octorok) {
                if(RandomStream.Unit()<0.03) { X+=RandomStream.Int(-1,1)*0.9*8; Y+=RandomStream.Int(-1,1)*0.9*8; }
                if(--ShootTimer<=0) { ShootTimer=RandomStream.Int(80,140); return true; }
            } else {
                const double Dx=TargetPlayer.X-X, Dy=TargetPlayer.Y-Y;
                const double Dist=Distance(TargetPlayer.X,TargetPlayer.Y,X,Y);
                if(Kind==EnemyKind::Moblin || Dist<120) {
                    const double Speed=Kind==EnemyKind::Moblin ? 1.2 : 2.2;
                    const double Denom=Dist==0 ? 1 : Dist;
                    X+=Dx/Denom*Speed; Y+=Dy/Denom*Speed;
                }
            }
            X=Clamp(X,30,770); Y=Clamp(Y,30,570);
            return false;
        }
    };
    struct Projectile {
        double X=0, Y=0, Dx=0, Dy=0;
        bool Alive=true;
        Rect GetRect() const { return maze::PixelRect(X-5,Y-5,10,10); }
        void Update() { X+=Dx; Y+=Dy; if(!(X>0 && X<800 && Y>0 && Y<600)) Alive=false; }
    };
    struct Collectible {
        double X=0, Y=0;
        PickupKind Kind=PickupKind::Rupee;
        double Bob=0;
        Rect GetRect() const { return maze::PixelRect(X-8,Y-8,16,16); }
    };
    ZeldaGame() { Reset(730); }
    void Reset(std::uint32_t Seed) override {
        // Preserve the player's optional control preference across same-cabinet retries.
        SessionSeed=Seed; Rng.Seed(Seed); Hero={}; Score=0; Keys=0; KeySpawned=false; Over=false; Won=false;
        Message.clear(); MessageTimer=0; Projectiles.clear(); Collectibles.clear();
        Enemies={{{200,150,EnemyKind::Octorok,1,Rng.Int(60,120)},
                  {550,200,EnemyKind::Moblin,2,0}, {300,380,EnemyKind::Armos,1,0},
                  {620,350,EnemyKind::Octorok,1,Rng.Int(60,120)}}};
        AddPickup(250,280,PickupKind::Rupee); AddPickup(500,150,PickupKind::Rupee);
        AddPickup(150,420,PickupKind::Heart); AddPickup(680,280,PickupKind::Rupee);
    }
    // Option 1 presets held-sword assistance for cabinets that want it on from the start.
    // Shift/pad Y still toggles it live; option 0 keeps the original fresh-press default.
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value;SwordAssist=Value==1;Reset(Seed);return true;
    }
    int GetOption() const override { return Option; }
    void Step(const Input& I) override {
        if(Over || Won) { if(maze::RestartPressed(I)) Reset(SessionSeed); return; }
        if(I.DashPressed) SwordAssist=!SwordAssist;
        // Default source KEYDOWNs and optional held assistance share the same attack gate and order.
        const bool Swing=maze::RestartPressed(I) || (SwordAssist && (I.Fire || I.Action || I.Jump));
        if(Swing && Hero.Attack()) {
            const Rect Attack=Hero.GetAttackRect();
            Vec LastDefeated{Hero.X,Hero.Y};
            for(auto& E:Enemies) if(E.Alive && Attack.Overlaps(E.GetRect())) {
                --E.Health; E.HitFlash=12;
                if(E.Health<=0) {
                    E.Alive=false; Score+=50; LastDefeated={E.X,E.Y};
                    if(Rng.Unit()<0.4) AddPickup(E.X,E.Y,PickupKind::Rupee);
                }
            }
            if(!KeySpawned && AllEnemiesDead()) {
                // Repair: the source key pickup logic exists but no key is created.
                AddPickup(LastDefeated.X,LastDefeated.Y,PickupKind::Key); KeySpawned=true;
            }
        }
        Hero.Update(I);
        for(auto& E:Enemies) if(E.Update(Hero,Rng) && Projectiles.size()<MaxProjectiles) {
            const double Dx=Hero.X-E.X, Dy=Hero.Y-E.Y;
            const double Dist=Distance(Hero.X,Hero.Y,E.X,E.Y), Denom=Dist==0 ? 1 : Dist;
            Projectiles.push_back({E.X,E.Y,Dx/Denom*2.5,Dy/Denom*2.5,true});
        }
        for(auto& P:Projectiles) {
            P.Update();
            if(P.Alive && P.GetRect().Overlaps(Hero.GetRect()) && Hero.Invincible==0) {
                Damage(); P.Alive=false;
            }
        }
        Projectiles.erase(std::remove_if(Projectiles.begin(),Projectiles.end(),[](const Projectile& P){return !P.Alive;}),Projectiles.end());
        // Settle lethal projectile damage before a same-step pickup can heal or reward.
        if(Over) return;
        for(auto It=Collectibles.begin();It!=Collectibles.end();) {
            It->Bob=std::fmod(It->Bob+0.1,6.283185307179586); // bounded animation phase
            if(It->GetRect().Overlaps(Hero.GetRect())) {
                if(It->Kind==PickupKind::Rupee) { ++Hero.Rupees; Score+=10; Message="+1 Trinket"; }
                else if(It->Kind==PickupKind::Heart) { Hero.Health=std::min(Hero.MaxHealth,Hero.Health+2); Message="+1 Heart"; }
                else { ++Keys; Message="Key Found!"; }
                MessageTimer=40; It=Collectibles.erase(It);
            } else ++It;
        }
        for(const auto& E:Enemies) if(E.Alive && E.GetRect().Overlaps(Hero.GetRect()) && Hero.Invincible==0) Damage();
        // No unbounded source moblin respawn: the four original enemies now yield the required key.
        if(!Over && AllEnemiesDead() && Keys>=1) Won=true;
        if(MessageTimer>0) --MessageTimer;
    }
    const Player& GetPlayer() const { return Hero; }
    const std::array<Enemy,4>& GetEnemies() const { return Enemies; }
    const std::vector<Projectile>& GetProjectiles() const { return Projectiles; }
    const std::vector<Collectible>& GetCollectibles() const { return Collectibles; }
    int GetKeys() const { return Keys; }
    int LivingEnemyCount() const {
        return static_cast<int>(std::count_if(Enemies.begin(),Enemies.end(),[](const Enemy& E){return E.Alive;}));
    }
    bool HasGroundKey() const {
        return std::any_of(Collectibles.begin(),Collectibles.end(),[](const Collectible& C){return C.Kind==PickupKind::Key;});
    }
    bool IsSwordReady() const { return !Over && !Won && Hero.AttackTimer==0; }
    bool IsSwordAssistEnabled() const { return SwordAssist; }
    // Checkpoint save: option, score, health, trinkets and the live assist toggle.
    // Restore starts a fresh roster on the session seed. Finished runs are not saved.
    std::string SaveState() const override {
        if(Over || Won) return {};
        return "DZS1 "+std::to_string(Option)+" "+std::to_string(Score)+" "+std::to_string(Hero.Health)
            +" "+std::to_string(Hero.Rupees)+" "+(SwordAssist?"1":"0");
    }
    bool RestoreState(const std::string& Payload,std::uint32_t Seed) override {
        if(Payload.size()>128) return false;
        std::istringstream In(Payload);std::string Version,Extra;long long Mode=-1,Points=-1,Life=-1,Trinkets=-1,Assist=-1;
        if(!(In>>Version>>Mode>>Points>>Life>>Trinkets>>Assist) || Version!="DZS1" || (In>>Extra)) return false;
        const Player Fresh{};
        if(Mode<0 || Mode>1 || Points<0 || Points>1000000000LL || Life<1 || Life>Fresh.MaxHealth
            || Trinkets<0 || Trinkets>1000000LL || (Assist!=0 && Assist!=1)) return false;
        Option=static_cast<int>(Mode);Reset(Seed);
        Score=Points;Hero.Health=static_cast<int>(Life);Hero.Rupees=static_cast<int>(Trinkets);SwordAssist=Assist==1;
        return true;
    }
    void Render(Frame& Out) const override {
        Out.Clear(800,600,{34,139,34,255});
        Out.AddRect(96,196,608,88,{120,86,48,255}); Out.AddRect(346,96,88,408,{120,86,48,255});
        Out.AddRect(100,200,600,80,{210,180,140,255}); Out.AddRect(350,100,80,400,{210,180,140,255});
        for(const Vec T:std::array<Vec,6>{{{50,80},{120,60},{650,90},{720,70},{80,480},{700,450}}}) {
            Out.AddRect(T.X-12,T.Y+5,24,30,{92,58,24,255});
            Out.AddTriangle({T.X,T.Y-28},{T.X-23,T.Y+7},{T.X+23,T.Y+7},{170,220,90,255});
            Out.AddTriangle({T.X,T.Y-25},{T.X-20,T.Y+5},{T.X+20,T.Y+5},{0,100,0,255});
        }
        for(const Vec R:std::array<Vec,4>{{{200,150},{580,180},{180,380},{620,420}}}) {
            Out.AddCircle(R.X,R.Y,16,{24,24,24,255});
            Out.AddCircle(R.X,R.Y,14,{128,128,128,255}); Out.AddCircle(R.X,R.Y,9,{100,100,100,255});
        }
        Out.AddCircle(610,355,62,{12,64,28,255});
        Out.AddCircle(610,355,55,{30,144,255,255}); Out.AddCircle(610,355,42,{20,100,180,255});
        Out.AddRect(380,80,40,50,{60,40,20,255}); Out.AddTriangle({380,80},{400,50},{420,80},{40,30,10,255});
        Out.AddRect(394,104,12,26,{24,16,8,255});
        for(const auto& E:Enemies) if(E.Alive) DrawEnemy(Out,E);
        for(const auto& P:Projectiles) {
            Out.AddCircle(P.X,P.Y,7,{24,24,24,255});
            Out.AddCircle(P.X,P.Y,5,{128,128,128,255}); Out.AddCircle(P.X,P.Y,3,{80,80,80,255});
        }
        for(const auto& C:Collectibles) {
            const double X=C.X, Y=C.Y+std::sin(C.Bob)*3;
            if(C.Kind==PickupKind::Rupee) {
                Out.AddTriangle({X,Y-10},{X-7,Y},{X+7,Y},{12,40,12,255});
                Out.AddTriangle({X,Y+10},{X-7,Y},{X+7,Y},{12,40,12,255});
                Out.AddTriangle({X,Y-8},{X-5,Y},{X+5,Y},{50,200,100,255});
                Out.AddTriangle({X,Y+8},{X-5,Y},{X+5,Y},{30,150,70,255});
            } else if(C.Kind==PickupKind::Heart) {
                Out.AddCircle(X-4,Y-3,7,{80,12,16,255}); Out.AddCircle(X+4,Y-3,7,{80,12,16,255});
                Out.AddTriangle({X-11,Y-2},{X+11,Y-2},{X,Y+10},{80,12,16,255});
                Out.AddCircle(X-4,Y-3,5,{255,50,50,255}); Out.AddCircle(X+4,Y-3,5,{255,50,50,255});
                Out.AddTriangle({X-9,Y-2},{X+9,Y-2},{X,Y+8},{255,50,50,255});
            } else {
                Out.AddCircle(X,Y,8,{24,28,16,255}); Out.AddRect(X+2,Y-4,14,8,{24,28,16,255});
                Out.AddCircle(X,Y,6,{255,215,0,255}); Out.AddRect(X+3,Y-3,12,6,{255,215,0,255});
                Out.AddText(X-10,Y+11,"KEY",maze::Yellow,12);
            }
        }
        DrawPlayer(Out,Hero);
        Out.AddRect(0,4,800,48,{8,36,16,255});
        Out.AddText(10,10,"HEALTH "+std::to_string(Hero.Health)+"/"+std::to_string(Hero.MaxHealth)+"  TRINKETS "+std::to_string(Hero.Rupees)+"  KEY "+std::to_string(Keys));
        Out.AddText(10,35,ObjectiveText(),White,15);
        if(MessageTimer>0) {
            Out.AddRect(280,50,280,28,{8,36,16,255});
            Out.AddText(330,58,Message,maze::Yellow,18);
        }
        Out.AddRect(0,552,800,48,{8,36,16,255});
        Out.AddText(10,559,"SCORE "+std::to_string(Score)+" | "+CombatText(),White,13);
        Out.AddText(10,582,(Over || Won)?"Run ended. Pad A / Space / Enter / R: replay."
            :std::string("Move: keys/stick/hat | Sword: Space/J/pad A/X | Shift/pad Y: toggle assist ")+(SwordAssist?"ON":"OFF")+" | R: restart.",White,12);
        if(Over || Won) {
            Out.AddRect(170,245,470,125,{0,55,0,230});
            Out.AddText(280,270,Won ? "VICTORY!" : "GAME OVER",maze::Yellow,38);
            Out.AddText(195,325,"Pad A / Space / Enter / R: replay",White,17);
        }
        Out.AddRect(0,70,800,26,{8,36,16,255});
        Out.AddText(10,78,HintLine(),Color{255,236,180,255},14);
        Out.AddText(520,78,ActionCue(),Color{120,225,255,255},14);
    }
    std::string HintLine() const {
        if(Won) return "HINT Press Fire or R to walk Lanternwild again.";
        if(Over) return "HINT Press Fire or R to retry. Hearts on the ground heal.";
        if(LivingEnemyCount()>0) {
            return Hero.AttackTimer==0
                ? "HINT Press J or pad A once to swing. Shift toggles held-sword assist."
                : "HINT The sword is recovering. Step away from rocks.";
        }
        if(Keys>0) return "HINT The roster is clear and the key is yours.";
        return "HINT Walk onto the gold KEY.";
    }
    std::string ActionCue() const {
        if(Won) return "CUE Replay";
        if(Over) return "CUE Retry";
        if(LivingEnemyCount()>0) return Hero.AttackTimer==0 ? "CUE Swing" : "CUE Wait";
        if(Keys>0) return "CUE Clear";
        return "CUE Key";
    }
    Status GetStatus() const override {
        const std::string Text=Won?"Victory: roster defeated and key collected. Pad A / Space / Enter / R: replay."
            :(Over?"Defeated. Pad A / Space / Enter / R: replay.":ObjectiveText()+" "+CombatText());
        return {Score,Hero.Health,Over,Won,Text};
    }
private:
    friend struct MazeTestAccess;
    std::uint32_t SessionSeed=730;
    Random Rng;
    Player Hero;
    std::array<Enemy,4> Enemies;
    std::vector<Projectile> Projectiles;
    std::vector<Collectible> Collectibles;
    std::int64_t Score=0;
    int Keys=0, MessageTimer=0;
    int Option=0;
    bool KeySpawned=false, Over=false, Won=false, SwordAssist=false;
    std::string Message;
    std::string ObjectiveText() const {
        const int Living=LivingEnemyCount();
        if(Living>0) return "Enemies left: "+std::to_string(Living)+"/4. Defeat the roster to reveal its key.";
        if(Keys>0) return "Key collected; roster cleared.";
        return HasGroundKey()?"Roster cleared. Collect the gold KEY to finish.":"Roster cleared; no key on the ground.";
    }
    std::string CombatText() const {
        if(Over || Won) return "Run ended | Shield decorative";
        std::string Text=Hero.AttackTimer==0?"Sword READY":"Sword wait "+std::to_string(Hero.AttackTimer)+" steps";
        Text+=SwordAssist?" (hold sword)":" (fresh press)";
        if(Hero.Invincible==1) Text+=" | Hurt grace expires next live step";
        else if(Hero.Invincible>1) Text+=" | Hurt grace timer "+std::to_string(Hero.Invincible);
        return Text+" | Shield decorative";
    }
    bool AllEnemiesDead() const { return std::all_of(Enemies.begin(),Enemies.end(),[](const Enemy& E){return !E.Alive;}); }
    void AddPickup(double X,double Y,PickupKind Kind) {
        if(Collectibles.size()<MaxCollectibles) Collectibles.push_back({X,Y,Kind,Rng.Unit()*6.283185307179586});
    }
    void Damage() { Hero.Health=std::max(0,Hero.Health-1); Hero.Invincible=45; if(Hero.Health==0) Over=true; }
    static void DrawEnemy(Frame& F,const Enemy& E) {
        if(E.Kind==EnemyKind::Octorok) {
            F.AddCircle(E.X,E.Y,12,{48,12,16,255});
            F.AddCircle(E.X,E.Y,10,{200,50,50,255}); F.AddCircle(E.X,E.Y+1,6,{150,30,30,255});
            F.AddCircle(E.X-4,E.Y-2,3,White); F.AddCircle(E.X+4,E.Y-2,3,White);
            F.AddCircle(E.X-4,E.Y-2,1,Black); F.AddCircle(E.X+4,E.Y-2,1,Black);
        } else if(E.Kind==EnemyKind::Moblin) {
            F.AddRect(E.X-12,E.Y-14,24,28,{16,36,16,255});
            F.AddRect(E.X-10,E.Y-12,20,24,{80,120,80,255}); F.AddCircle(E.X,E.Y-12,7,{200,180,150,255});
            F.AddTriangle({E.X-11,E.Y-10},{E.X-22,E.Y},{E.X-11,E.Y+10},{48,32,12,255});
            F.AddTriangle({E.X-12,E.Y-8},{E.X-18,E.Y},{E.X-12,E.Y+8},{255,200,50,255});
        } else {
            F.AddRect(E.X-14,E.Y-16,28,32,{24,24,24,255});
            F.AddRect(E.X-12,E.Y-14,24,28,{128,128,128,255}); F.AddRect(E.X-8,E.Y-10,16,20,{100,100,100,255});
            F.AddCircle(E.X,E.Y-4,5,{220,220,220,255});
        }
        if(E.HitFlash>0) { F.AddLine(E.X-14,E.Y-16,E.X+14,E.Y-16,White,2); F.AddLine(E.X-14,E.Y+16,E.X+14,E.Y+16,White,2); }
        if(E.Kind==EnemyKind::Moblin) F.AddText(E.X-15,E.Y-33,"HP "+std::to_string(E.Health),White,12);
    }
    static void DrawPlayer(Frame& F,const Player& P) {
        const Color Tunic{50,150,50,255}, Gold{255,215,0,255}, Steel{200,200,220,255};
        const Color Outline{12,40,12,255};
        F.AddRect(P.X-10,P.Y-6,20,24,Outline); F.AddCircle(P.X,P.Y-11,9,Outline);
        F.AddRect(P.X-8,P.Y-4,16,20,Tunic); F.AddCircle(P.X,P.Y-11,7,{255,218,185,255});
        F.AddTriangle({P.X-10,P.Y-16},{P.X,P.Y-32},{P.X+10,P.Y-16},Outline);
        F.AddTriangle({P.X-8,P.Y-16},{P.X,P.Y-28},{P.X+8,P.Y-16},Tunic);
        F.AddCircle(P.X-3,P.Y-13,1,Black); F.AddCircle(P.X+3,P.Y-13,1,Black);
        if(P.Attacking) {
            const auto Swing=[&](double X,double Y,double X2,double Y2) {
                F.AddLine(X,Y,X2,Y2,{24,28,40,255},6);
                F.AddLine(X,Y,X2,Y2,Steel,4);
            };
            if(P.Face==Facing::Right) { Swing(P.X+8,P.Y-5,P.X+28,P.Y-5); F.AddTriangle({P.X+28,P.Y-8},{P.X+35,P.Y-5},{P.X+28,P.Y-2},Gold); }
            else if(P.Face==Facing::Left) { Swing(P.X-8,P.Y-5,P.X-28,P.Y-5); F.AddTriangle({P.X-28,P.Y-8},{P.X-35,P.Y-5},{P.X-28,P.Y-2},Gold); }
            else if(P.Face==Facing::Up) { Swing(P.X,P.Y-18,P.X,P.Y-38); F.AddTriangle({P.X-4,P.Y-38},{P.X,P.Y-45},{P.X+4,P.Y-38},Gold); }
            else { Swing(P.X,P.Y+12,P.X,P.Y+32); F.AddTriangle({P.X-4,P.Y+32},{P.X,P.Y+40},{P.X+4,P.Y+32},Gold); }
        } else {
            const bool Side=P.Face==Facing::Right || P.Face==Facing::Left;
            const double X=P.Face==Facing::Right ? P.X-12 : P.Face==Facing::Left ? P.X+4 : P.X-6;
            const double W=Side?8:12, H=Side?14:8;
            F.AddRect(X-1,P.Y-3,W+2,H+2,{24,28,40,255});
            F.AddRect(X,P.Y-2,W,H,{180,180,200,255});
        }
        if(P.Invincible>0 && (P.Invincible/4)%2==0) F.AddCircle(P.X,P.Y,18,{255,255,255,90});
    }
};
}} // daedalus::desktop
