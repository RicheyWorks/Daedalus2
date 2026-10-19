// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopPongCore.h"
#include "DaedalusDesktopMinesweeperCore.h"
#include "DaedalusDesktopMazeCore.h"
#include "DaedalusDesktopShootersCore.h"
#include "DaedalusDesktopSportsCore.h"
#include "DaedalusDesktopPlatformersCore.h"
#include <memory>
#include <limits>

namespace daedalus { namespace desktop {
struct Entry { std::string Id, Title, Controls; };
inline const std::vector<Entry>& Catalog() {
    static const std::vector<Entry> Entries{
        {"minesweeper","Minesweeper","Arrows/stick: select; J/Space: reveal; K: flag; Shift: chord"},
        {"pong","Twinwake Volley","A fast duel across the twinwake court. Up/Down or left stick: paddle"},
        {"dungeon","Dungeon Prototype","Light the Threadlight lanterns and unlock the exit. Move: WASD/arrows or left stick"},
        {"asteroids","Driftstone Patrol","Pilot the driftstone belt and clear the rocks. Left/Right: turn; Up: thrust; J/X: shoot"},
        {"football","Football / Soccer","A ninety-second duel on the Daedalus pitch. Move: WASD/arrows or left stick; J/X: kick"},
        {"pacman","Glowtrail Chase","Gather the glowtrail, evade pursuers, and clear the maze. Move: WASD/arrows or left stick"},
        {"sega_shooter","Riftwing Vanguard","Push the rift frontier with a changing arsenal. Move: WASD/arrows or left stick; J/X: shoot"},
        {"shadow_ninja","Shadow Ninja","Scale the ember terraces and face the sentinel. Space/pad A: jump; J/Z/X or pad B/X: sword; K/C or pad Y/RB: star; Shift/V or LB: spin; Up/Down: climb"},
        {"star_shooter","Star Shooter","Hold the starlanes through escalating waves. Move: WASD/arrows or left stick; J/X: shoot; P/Start: pause/save menu"},
        {"dodge_ball","Courtyard Clash","Lead three teammates through four courtyard rounds. Move: WASD/arrows or left stick; throw/catch/jump actions"},
        {"contra","Ironwake Advance","Run the ironwake route through platforms and enemy fire. Move: WASD/arrows or left stick; Down: crouch; J/X: shoot; Space/pad A: jump"},
        {"zelda","Lanternwild Quest","Explore Lanternwild, defeat the guardians, and recover the key. Move: WASD/arrows or left stick; J/X: sword"}
    };
    return Entries;
}
inline std::unique_ptr<Game> CreateGame(const std::string& Id) {
    if(Id=="minesweeper") return std::make_unique<MinesweeperGame>();
    if(Id=="pong") return std::make_unique<PongGame>();
    if(Id=="dungeon") return std::make_unique<DungeonGame>();
    if(Id=="asteroids") return std::make_unique<AsteroidsGame>();
    if(Id=="football") return std::make_unique<FootballGame>();
    if(Id=="pacman") return std::make_unique<PacmanGame>();
    if(Id=="sega_shooter") return std::make_unique<SegaShooterGame>();
    if(Id=="shadow_ninja") return std::make_unique<ShadowNinjaGame>();
    if(Id=="star_shooter") return std::make_unique<StarShooterGame>();
    if(Id=="dodge_ball") return std::make_unique<DodgeBallGame>();
    if(Id=="contra") return std::make_unique<ContraGame>();
    if(Id=="zelda") return std::make_unique<ZeldaGame>();
    return nullptr;
}

class Driver {
    std::unique_ptr<Game> Active;
    std::string Id;
    Frame Picture;
    Input Controls;
    std::uint32_t Seed=730;
    double PendingSeconds=0;
    std::uint64_t StepCount=0;
    bool Paused=false;
    void Refresh() { if(Active) Active->Render(Picture); }
public:
    static constexpr double StepSeconds=1.0/60.0;
    static constexpr int MaxSteps=8;
    bool Select(const std::string& NewId,std::uint32_t NewSeed) {
        auto Candidate=CreateGame(NewId);
        if(!Candidate) return false;
        Candidate->Reset(NewSeed); Candidate->EnterTitle(); Active=std::move(Candidate); Id=NewId; Seed=NewSeed;
        Controls={}; PendingSeconds=0; StepCount=0; Paused=false; Refresh(); return true;
    }
    void Restart() {
        if(!Active) return;
        Active->Reset(Seed); Controls={}; PendingSeconds=0; StepCount=0; Paused=false; Refresh();
    }
    void SetInput(const Input& New) {
        Input Next=New; Next.AxisX=Axis(Next.AxisX); Next.AxisY=Axis(Next.AxisY);
        // An event arriving then releasing before a fixed step still emits one edge.
        Next.FirePressed=Next.FirePressed||Controls.FirePressed;
        Next.JumpPressed=Next.JumpPressed||Controls.JumpPressed;
        Next.ActionPressed=Next.ActionPressed||Controls.ActionPressed;
        Next.DashPressed=Next.DashPressed||Controls.DashPressed; Controls=Next;
    }
    void ClearInput() { Controls={}; }
    void SourceKeyDown(int Key) {
        if(!Active || Paused) return;
        if(Active->SourceKeyDown(Key)) Controls={};
        Refresh();
    }
    bool SourceControllerButton(int Button) {
        if(!Active || Paused || !Active->SourceControllerButton(Button)) return false;
        Controls={}; Refresh(); return true;
    }
    void SetPaused(bool Value) { Paused=Active && Active->OwnPause(Value) ? false : Value; Controls={}; PendingSeconds=0; }
    bool IsPaused() const { return Paused || (Active && Active->IsCorePaused()); }
    int Advance(double DeltaSeconds) {
        if(!Active || Paused || !std::isfinite(DeltaSeconds) || DeltaSeconds<0) return 0;
        // Never attempt an unbounded catch-up after a stall. Dropped real time is
        // a declared host adaptation; each accepted game step remains source 60 Hz.
        PendingSeconds+=std::min(DeltaSeconds,StepSeconds*MaxSteps);
        int Count=0;
        while(PendingSeconds+1e-12>=StepSeconds && Count<MaxSteps) {
            Active->Step(Controls); PendingSeconds=std::max(0.0,PendingSeconds-StepSeconds);
            Controls.FirePressed=Controls.JumpPressed=Controls.ActionPressed=Controls.DashPressed=false;
            if(StepCount<std::numeric_limits<std::uint64_t>::max()) ++StepCount;
            ++Count;
        }
        if(Count==MaxSteps) PendingSeconds=std::min(PendingSeconds,StepSeconds);
        if(Count) Refresh();
        return Count;
    }
    const Frame& GetFrame() const { return Picture; }
    Status GetStatus() const { return Active ? Active->GetStatus() : Status{}; }
    const std::string& ActiveId() const { return Id; }
    std::uint64_t Ticks() const { return StepCount; }
    std::string CaptureSave() const { return Active ? Active->SaveState() : std::string{}; }
    bool RestoreSave(const std::string& Text) {
        if(!Active || Text.size()>4096 || !Active->RestoreState(Text,Seed)) return false;
        Controls={};PendingSeconds=0;Paused=false;Refresh();return true;
    }
    bool HasSaveRequest() const { return Active && Active->SavePending(); }
    void AcknowledgeSave() { if(Active) Active->ClearSavePending(); }
    bool WantsExit() const { return Active && Active->WantsExit(); }
    bool SetOption(int Value) {
        if(!Active || !Active->SetOption(Value,Seed)) return false;
        Controls={};PendingSeconds=0;StepCount=0;Paused=false;Refresh();return true;
    }
    int GetOption() const { return Active ? Active->GetOption() : -1; }
};
}} // daedalus::desktop
