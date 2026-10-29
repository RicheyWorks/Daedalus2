// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopCairnwellCore.h"
#include "DaedalusDesktopReedbeatCore.h"
#include "DaedalusDesktopGloamLatchCore.h"
#include "DaedalusDesktopTwinwakeCore.h"
#include "DaedalusDesktopBeaconSweepCore.h"
#include "DaedalusDesktopMazeCore.h"
#include "DaedalusDesktopShootersCore.h"
#include "DaedalusDesktopSportsCore.h"
#include "DaedalusDesktopPlatformersCore.h"
#include "DaedalusDesktopShardringCore.h"
#include "DaedalusDesktopLumenpathCore.h"
#include "DaedalusDesktopWardensAccordCore.h"
#include "DaedalusDesktopFacetlockCore.h"
#include "DaedalusDesktopPrismcairnCore.h"
#include "DaedalusDesktopPrismvaultCore.h"
#include "DaedalusDesktopShardfallCore.h"
#include "DaedalusDesktopSaveSlots.h"
#include <memory>
#include <limits>

namespace daedalus { namespace desktop {
struct Entry { std::string Id, Title, Controls; };
inline const std::vector<Entry>& Catalog() {
    static const std::vector<Entry> Entries{
        {"beacon_sweep","Beacon Sweep","Arrows/stick: select; J/Space: reveal; K: flag; Shift: chord"},
        {"twinwake","Twinwake Volley","A fast duel across the twinwake court. Up/Down or left stick: paddle"},
        {"dungeon","Dungeon Prototype","Light the Threadlight lanterns and unlock the exit. Move: WASD/arrows or left stick; Shift/pad Y: trail"},
        {"driftstone","Driftstone Patrol","Pilot the driftstone belt and clear the rocks. Left/Right: turn; Up: thrust; K/LT: brake; J/X: shoot"},
        {"football","Football / Soccer","A ninety-second duel on the Daedalus pitch. Move: WASD/arrows or left stick; J/X: kick"},
        {"glowtrail","Glowtrail Chase","Gather the glowtrail, evade pursuers, and clear the maze. Move: WASD/arrows or left stick"},
        {"riftwing","Riftwing Vanguard","Push the rift frontier with a changing arsenal. Move: WASD/arrows or left stick; J/X: shoot"},
        {"emberstep","Emberstep Ascent","Scale the ember terraces and face the sentinel. Space/pad A: jump; J/Z/X or pad B/X: sword; K/C or pad Y/RB: star; Shift/V or LB: spin; Up/Down: climb"},
        {"star_shooter","Star Shooter","Hold the starlanes through escalating waves. Move: WASD/arrows or left stick; J/X: shoot; P/Start: pause/save menu"},
        {"dodge_ball","Courtyard Clash","Lead three teammates through four courtyard rounds. Move: WASD/arrows or left stick; throw/catch/jump actions"},
        {"ironwake","Ironwake Advance","Run the ironwake route through platforms and enemy fire. Move: WASD/arrows or left stick; Down: crouch; J/X: shoot; Space/pad A: jump"},
        {"lanternwild","Lanternwild Quest","Explore Lanternwild, defeat the guardians, and recover the key. Move: WASD/arrows or left stick; J/X: sword"},
        {"gloam_latch","Gloam Latch","Darken every lamp. Arrows or stick: move; J/Space or pad A: flip a lamp and its neighbors"},
        {"reedbeat","Reedbeat","Strike the reed when it glows. J/Space or pad A: strike"},
        {"cairnwell","Cairnwell","Stack stones in the well. Left/Right or stick: slide; Down: drop"},
        {"shardring","Shardring Resonance","Set Prism Shards in the sphere ring; three of one hue resonate. Left/Right or stick: pick a facet; J/Space or pad A: set"},
        {"lumenpath","Lumenpath Refraction","Bend the prism beam through every crystal with shard mirrors. Arrows or stick: move; J/Space or pad A: toggle a mirror"},
        {"wardens_accord","Wardens' Accord","Take altar shards and spend them to summon Warden spirits. Left/Right or stick: pick; J/Space or pad A: take or summon"},
        {"facetlock","Facetlock Lattice","Slide wrapping rows and columns until each row is one hue. Arrows or stick: cursor; J/K or pad A/B: slide row; Space/Shift or pad X/Y: slide column"},
        {"prismcairn","Prismcairn Duel","Out-think the Warden at the shard cairns; lift the last shard. Left/Right or stick: pick a cairn; J/K/Space/Shift or pad A/B/X/Y: take 1/2/3/4"},
        {"prismvault","Prismvault Weigh","Find the hollow shard with the Warden's balance. Left/Right or stick: pick; J or pad A: pan it; Space or pad X: weigh; Shift or pad Y: name"},
        {"shardfall","Shardfall Gamble","Draw glowing shards from the seam and bank before it cracks. J/Space or pad A: draw; K/Shift or pad B/X: bank"}
    };
    return Entries;
}
inline std::unique_ptr<Game> CreateGame(const std::string& RawId) {
    const std::string Id=CanonicalGameId(RawId);
    if(Id=="beacon_sweep") return std::make_unique<BeaconSweepGame>();
    if(Id=="twinwake") return std::make_unique<TwinwakeGame>();
    if(Id=="dungeon") return std::make_unique<DungeonGame>();
    if(Id=="driftstone") return std::make_unique<DriftstoneGame>();
    if(Id=="football") return std::make_unique<FootballGame>();
    if(Id=="glowtrail") return std::make_unique<GlowtrailGame>();
    if(Id=="riftwing") return std::make_unique<RiftwingGame>();
    if(Id=="emberstep") return std::make_unique<EmberstepGame>();
    if(Id=="star_shooter") return std::make_unique<StarShooterGame>();
    if(Id=="dodge_ball") return std::make_unique<DodgeBallGame>();
    if(Id=="ironwake") return std::make_unique<IronwakeGame>();
    if(Id=="lanternwild") return std::make_unique<LanternwildGame>();
    if(Id=="gloam_latch") return std::make_unique<GloamLatchGame>();
    if(Id=="reedbeat") return std::make_unique<ReedbeatGame>();
    if(Id=="cairnwell") return std::make_unique<CairnwellGame>();
    if(Id=="shardring") return std::make_unique<ShardringGame>();
    if(Id=="lumenpath") return std::make_unique<LumenpathGame>();
    if(Id=="wardens_accord") return std::make_unique<WardensAccordGame>();
    if(Id=="facetlock") return std::make_unique<FacetlockGame>();
    if(Id=="prismcairn") return std::make_unique<PrismcairnGame>();
    if(Id=="prismvault") return std::make_unique<PrismvaultGame>();
    if(Id=="shardfall") return std::make_unique<ShardfallGame>();
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
        Candidate->Reset(NewSeed); Candidate->EnterTitle(); Active=std::move(Candidate); Id=CanonicalGameId(NewId); Seed=NewSeed;
        Controls={}; PendingSeconds=0; StepCount=0; Paused=false; Refresh(); return true;
    }
    void Restart() {
        if(!Active) return;
        Active->Reset(Seed); Controls={}; PendingSeconds=0; StepCount=0; Paused=false; Refresh();
    }
    // Explicit fresh puzzle, separate from same-seed Restart. Never writes a saved board.
    bool NewBeaconSweepPuzzle(std::uint32_t SeedCandidate) {
        if(!Active || Id!="beacon_sweep" || HasSaveRequest()) return false;
        // Keep native int32 seed presentation nonnegative. Existing uint32 saves stay readable.
        std::uint32_t NextSeed=SeedCandidate&0x7fffffffu;
        if(Random::InitialState(NextSeed)==Random::InitialState(Seed)) NextSeed=(NextSeed+1u)&0x7fffffffu;
        Seed=NextSeed;Restart();return true;
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
    bool SourcePointerButton(double X,double Y,int Button) {
        if(!Active || IsPaused() || HasSaveRequest() || Button<0 || Button>2 || !std::isfinite(X) || !std::isfinite(Y)
            || !Active->SourcePointerButton(X,Y,Button)) return false;
        Controls={};Refresh();return true;
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
    std::uint32_t GetSeed() const { return Seed; }
    std::uint64_t Ticks() const { return StepCount; }
    std::string CaptureSave() const { return Active ? Active->SaveState() : std::string{}; }
    bool RestoreSave(const std::string& Text) {
        if(!Active || Text.size()>4096 || !Active->RestoreState(Text,Seed)) return false;
        Seed=Active->SeedAfterRestore(Seed);
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
