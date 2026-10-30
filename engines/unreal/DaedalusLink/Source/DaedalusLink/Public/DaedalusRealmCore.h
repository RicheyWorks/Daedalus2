// SPDX-License-Identifier: MIT
//
// DaedalusRealmCore.h: the 8-bit realm behind a portal (ADR-052), with no engine in it.
//
// Step through a portal and the world turns into an NES-era top-down RPG. The Java engines generate the realm (the
// field, two towns, the castle, a three-floor cave from the maze generators, every chest's contents, every lock,
// every monster table: RetroRealmGenerator, carried here as the "DRR 1" spec); this file plays it:
//
//   * walking with the party in a line; townsfolk who wander, talk, sell, and give the news of the day;
//   * a shared bag; keys that open locks of their tier and are used up; chests of gold, gear and keys, and chests
//     that bite (mimics); inns, shops that buy and sell, equipment that changes attack and defence;
//   * random encounters by zone, terrain and rarity, counted down in steps like the classics; groups that mix;
//   * turn-based battles: FIGHT, SPELL, ITEM, DEFEND, RUN; spells HEAL, ZAP, CURE, BLAZE learned by level; monsters
//     that poison, put you to sleep, cast bolts, heal each other, call for help, run away, or shrug off all but a
//     mighty blow; drops; levels; the guardian at the bottom of the cave who cannot be run from;
//   * dark caves that a torch lights; poison that bites each step; swamps that sting;
//   * jukebox cues (MusicCue) and sound events (TakeSfx) for the team's jukebox; Save()/Restore() so the party
//     keeps its levels and gear between trips through the portal.
//
// Standard C++17 only. The Unreal wrapper copies Render() into a texture with nearest-pixel filtering and feeds
// Press/Release from the keyboard or pad.

#pragma once

#include "DaedalusBattleStageCore.h"
#include "DaedalusRealmLook.h"
#include "DaedalusRealmSpec.h"
#include "DaedalusRealmSprites.h"

#include <cstdio>
#include <deque>
#include <functional>
#include <set>
#include <sstream>

namespace daedalus
{
namespace realm
{

enum class Button { Up, Down, Left, Right, A, B, Start };
enum class Mode { Field, Battle };

enum Spell { SpHeal, SpZap, SpCure, SpBlaze, SpCount };
inline const char* SpellName(int S) { static const char* N[SpCount] = {"HEAL", "ZAP", "CURE", "BLAZE"}; return N[S]; }
inline int SpellCost(int S) { static const int C[SpCount] = {4, 3, 2, 8}; return C[S]; }
/** The level each class learns each spell at (99: never). Classes: 0 hero, 1 sage, 2 scout, 3 drake (hatched). */
inline int LearnsAt(int Class, int S)
{
    static const int L[4][SpCount] = {{1, 4, 99, 99}, {1, 1, 3, 6}, {99, 99, 5, 99}, {99, 99, 99, 1}};
    return L[std::min(std::max(Class, 0), 3)][S];
}

struct Member
{
    std::string Name;
    Look L;
    int Class = 0;
    int Lvl = 1, Hp = 20, MaxHp = 20, Mp = 0, MaxMp = 0, Atk = 8, Def = 4, Agi = 5, Exp = 0;
    int Weapon = -1, Armor = -1;
    bool Poisoned = false;
    int Asleep = 0;
    /** A shiny member (ADR-065 rule 9): rolled when the egg hatches; every stat x1.5 and the card sparkles. */
    bool Shiny = false;
    bool Alive() const { return Hp > 0; }
    bool Knows(int S) const { return Lvl >= LearnsAt(Class, S); }
};

/** Experience needed to reach level L + 1. */
inline int ExpToNext(int L) { return 5 * L * L * L / 2 + 5 * L; }

struct Foe
{
    int Kind = 0;
    int Hp = 1, MaxHp = 1;
    bool Fled = false;
    /** Shiny (ADR-065): 1 in 256 of any kind. Every stat x1.5, double the exp and gold, a sparkle in battle. */
    bool Shiny = false;
    bool Down() const { return Hp <= 0 || Fled; }
};

class Realm
{
public:
    // ------------------------------------------------------------------------------------------------ setup

    Realm()
    {
        Party = {
            MakeMember("HERO", {0x7C4C14, Pal::Teal, Pal::NavyBlue, 0, Pal::Red}, 0, 30, 6, 10, 4, 6),
            MakeMember("SAGE", {0xF8F8F8, Pal::Purple, Pal::NavyBlue, Pal::Purple, 0}, 1, 20, 14, 6, 3, 5),
            MakeMember("SCOUT", {Pal::Orange, 0x2C8C18, 0x603008, 0, 0}, 2, 24, 0, 9, 4, 9),
        };
    }

    /** Load a realm spec (the Java engines' "DRR 1" text). Puts the party at the spawn. */
    /** Sol's pixel art (DSP 1). Empty = the procedural shapes. Keyed by monster id, "MEMBER:<name>", "NPC:<role>". */
    SpritePack Art;

    bool LoadSprites(const std::string& PackText, std::string& Error) { return Art.Parse(PackText, Error); }
    int SpriteCount() const { return static_cast<int>(Art.Sprites.size()); }

    static const char* RoleKey(Role R)
    {
        switch (R) { case Role::News: return "NPC:NEWS"; case Role::Inn: return "NPC:INN"; case Role::Shop: return "NPC:SHOP";
                     case Role::Queen: return "NPC:QUEEN"; default: return "NPC:TALK"; }
    }

    /** A person: the pack's 8-frame sprite when it has one (down/up/left/right x 2 steps), else the drawn figure.
     * Sprites are drawn with their feet on the tile's bottom edge, centred, so a taller sprite stands up out of it. */
    void Person(Frame& F, int X, int Y, const std::string& Key, const Look& L, int Dir, int Step) const
    {
        if (const Sprite* S = Art.Find(Key))
        {
            const int Fr = (Dir == 0 ? 0 : Dir == 1 ? 2 : Dir == 2 ? 4 : 6) + (Step % 2);
            SpritePack::Draw(F, X + (TileSize - S->W) / 2, Y + TileSize - S->H, *S, S->Frames >= 8 ? Fr : Step % S->Frames);
            return;
        }
        DrawPerson(F, X, Y, L, Dir, Step);
    }

    /** A monster in battle: the pack's sprite (rarity tier ":2"/":3" first, then the base id), else the drawn shape. */
    void Monster(Frame& F, int X, int Y, const MonsterDef& M, int Anim, bool Hurt) const
    {
        const Sprite* S = nullptr;
        if (M.Rarity == "RARE") S = Art.Find(M.Id + ":2");
        else if (M.Rarity == "LEGENDARY" || M.Rarity == "ULTRA") S = Art.Find(M.Id + ":3");
        if (!S) S = Art.Find(M.Id);
        if (S) { SpritePack::Draw(F, X + (64 - S->W) / 2, Y + 64 - S->H, *S, (Anim / 8) % std::max(1, S->Frames), Hurt); return; }
        DrawMonster(F, X, Y, M.Shape, M.Body, M.Accent, Anim, Hurt);
    }

    bool Load(const std::string& SpecText, std::string& Error)
    {
        Spec S;
        if (!S.Parse(SpecText, Error)) return false;
        W = std::move(S);
        {
            Ui::Style& St = Ui::Current();
            St = Ui::Style();
            if (W.UiInk) { St.Ink = W.UiInk; St.InkDark = Shade(W.UiInk, 2, 3); }
        }
        R = Rng(W.Seed ^ 0x51EDull);
        Opened.assign(W.Chests.size(), false);
        DoorOpen.assign(W.Doors.size(), false);
        BossDown.assign(W.Bosses.size(), false);
        DeedTaken.assign(W.Lands.size(), false);
        LandHere = -1;
        Tiles.clear();
        for (const MapDef& M : W.Maps) Tiles.push_back(M.T);
        NpcPos.clear();
        for (const NpcDef& N : W.Npcs) NpcPos.push_back({N.At.X, N.At.Y});
        NpcTimer.assign(W.Npcs.size(), 1.0);
        // Starting kit: a club for the hero, clothes all round, a little gold, two herbs.
        const int Club = W.ItemIndex("CLUB"), Clothes = W.ItemIndex("CLOTHES"), Herb = W.ItemIndex("HERB");
        for (Member& P : Party)
        {
            if (P.Armor < 0) P.Armor = Clothes;
            if (P.Class == 0 && P.Weapon < 0) P.Weapon = Club;
        }
        if (Bag.empty() && Herb >= 0) Give(Herb, 2);
        RespawnMap = W.Spawn.Map; RespawnX = W.Spawn.X; RespawnY = W.Spawn.Y;
        Start();
        Loaded = true;
        return true;
    }

    /** Stand at the spawn, below the portal, in the field. */
    void Start()
    {
        Enter(W.Spawn.Map, W.Spawn.X, W.Spawn.Y);
        Facing = 0;
        ExitRequested = false;
        TitleT = TitleHold;
        Say("A PORTAL HUMS. THE WORLD TURNS TO PIXELS.");
    }

    // ------------------------------------------------------------------------------------------ the interface

    void Press(Button B);
    void Release(Button B);
    void Tick(double Dt);
    const Frame& Render();
    std::string Describe() const;
    std::string MusicCue() const { return Cue; }
    int CueChanges() const { return CueCount; }
    /** Sound events since the last call (CHEST, DOOR, LOCKED, HIT, MISS, SPELL, LEVEL, INN, BUMP, STAIRS...). */
    std::vector<std::string> TakeSfx() { std::vector<std::string> S; S.swap(Sfx); return S; }
    bool WantsExit() const { return ExitRequested; }
    Mode CurrentMode() const { return ModeNow; }
    bool IsLoaded() const { return Loaded; }
    /** True while a message, a menu or a battle's playback waits for the player. */
    bool Busy() const { return !Boxes.empty() || ModeNow == Mode::Battle; }
    void SetNews(const std::vector<std::string>& Lines) { if (!Lines.empty()) W.News = Lines; }
    /** Your team becomes this party: up to three names, in order. */
    void SetPartyNames(const std::vector<std::string>& Names)
    {
        for (size_t i = 0; i < Names.size() && i < Party.size(); ++i)
            if (!Names[i].empty()) Party[i].Name = Upper(Names[i].substr(0, 6));
    }
    std::string Save() const;

    // ---------------------------------------------------------------------------- the dragon egg (ADR-065)
    // A land's mint comes with an egg. In the realm it is a bag item: carry it EggNeed steps and it hatches
    // into a DRAKE, a fourth member who knows BLAZE from the start. The egg stirs at a third and two thirds.
    static constexpr int EggNeed = 240, MaxParty = 4;
    int EggWarmth = 0;
    int Warmth() const { return EggWarmth; }

    // ---- lands (ADR-065): plots of the overworld with deeds. Standing on one shows whose it is; the owner's first
    // visit hands over the deed's DRAGON EGG. The hero's name on a deed is the party's first member's.
    std::vector<bool> DeedTaken;   // per land: its egg has been handed over
    int LandHere = -1;             // the land under the party, -1 for none
    int LandAt(int M, int X, int Y) const
    {
        for (size_t i = 0; i < W.Lands.size(); ++i) if (W.Lands[i].Contains(M, X, Y)) return static_cast<int>(i);
        return -1;
    }
    int LandIndex(int Number) const
    {
        for (size_t i = 0; i < W.Lands.size(); ++i) if (W.Lands[i].Number == Number) return static_cast<int>(i);
        return -1;
    }
    /** The deed's name, as the realm compares it: upper case, the party leader's name. */
    bool Owns(const LandDef& L) const { return !L.Owner.empty() && !Party.empty() && Upper(L.Owner) == Upper(Party[0].Name); }
    int DeedsTaken() const { int N = 0; for (bool B : DeedTaken) N += B; return N; }
    /** The server's deed table changed (a mint, a tug): the realm follows it. */
    void SetOwner(int Number, const std::string& Owner) { const int I = LandIndex(Number); if (I >= 0) W.Lands[static_cast<size_t>(I)].Owner = Owner; }

    void CrossLands()
    {
        const int Now = LandAt(Cur, PX, PY);
        if (Now == LandHere) return;
        LandHere = Now;
        if (Now < 0) return;
        LandDef& L = W.Lands[static_cast<size_t>(Now)];
        const std::string Who = L.Owner.empty() ? "FOR SALE" : Owns(L) ? "YOURS" : Upper(L.Owner) + "'S";
        Sfx.push_back("LAND");
        if (Owns(L) && !DeedTaken[static_cast<size_t>(Now)] && W.ItemIndex("DRAGON_EGG") >= 0)
        {
            DeedTaken[static_cast<size_t>(Now)] = true;
            Give(W.ItemIndex("DRAGON_EGG"), 1);
            Sfx.push_back("DEED");
            Say("LAND " + std::to_string(L.Number) + ". YOURS. THE DEED'S DRAGON EGG IS IN THE BAG.");
            return;
        }
        Say("LAND " + std::to_string(L.Number) + ". " + Who + ".");
    }
    bool HasDrake() const { for (const Member& P : Party) if (P.Class == 3) return true; return false; }

    void WarmEgg()
    {
        const int Egg = W.ItemIndex("DRAGON_EGG");
        if (Egg < 0 || Count(Egg) == 0 || Party.size() >= static_cast<size_t>(MaxParty)) return;
        ++EggWarmth;
        if (EggWarmth == EggNeed / 3) { Say("THE EGG STIRS IN THE BAG."); Sfx.push_back("EGG"); }
        else if (EggWarmth == EggNeed * 2 / 3) { Say("THE EGG IS WARM. SOMETHING TAPS INSIDE."); Sfx.push_back("EGG"); }
        else if (EggWarmth >= EggNeed) Hatch(Egg);
    }

    void Hatch(int Egg)
    {
        Take(Egg);
        Member D = MakeMember("DRAKE", {Pal::Lime, 0x2C8C18, 0x603008, 0, Pal::Red}, 3, 26, 8, 9, 5, 7);
        D.Shiny = R.Chance(256);
        if (D.Shiny) { D.Hp = D.MaxHp = D.MaxHp * 3 / 2; D.Mp = D.MaxMp = D.MaxMp * 3 / 2; D.Atk = D.Atk * 3 / 2; D.Def = D.Def * 3 / 2; D.Agi = D.Agi * 3 / 2; }
        Party.push_back(D);
        EggWarmth = 0;
        Sfx.push_back("HATCH");
        Say(D.Shiny ? "THE EGG CRACKS! A SHINY DRAKE HATCHES AND GLITTERS AT YOUR SIDE." : "THE EGG CRACKS! A DRAKE HATCHES AND JOINS YOU.");
    }
    bool Restore(const std::string& Text);

    // ---- for tests and the harness

    const Spec& World() const { return W; }
    int MapIndex() const { return Cur; }
    std::string MapId() const { return W.Maps[static_cast<size_t>(Cur)].Id; }
    int X() const { return PX; }
    int Y() const { return PY; }
    int Gold() const { return GoldHeld; }
    int Steps() const { return StepCount; }
    int Battles() const { return BattleCount; }
    int Wins() const { return WinCount; }
    int Light() const { return LightRadius(); }
    const std::vector<Member>& Members() const { return Party; }
    std::vector<Member>& MembersMut() { return Party; }
    const std::vector<Foe>& Foes() const { return Enemies; }
    std::string LastMessage() const { return LastSaid; }
    double TitleLeft() const { return TitleT; }
    /** The harness: make every foe of the next battle shiny; how many shinies have shown; the live damage numbers. */
    void ForceShinyNext(bool On) { ForceShiny = On; }
    int ShiniesSeen() const { return ShinySeen; }
    int PopCount() const { return static_cast<int>(Pops.size()); }
    /** The battle stage director (hub 28710): cues for a 3D stage, lifted from the battle lines as they play. */
    std::vector<stage::Cue> TakeStage() { return Stage.Take(); }
    size_t StagePending() const { return Stage.Pending(); }
    int Count(int Item) const { for (const auto& E : Bag) if (E.first == Item) return E.second; return 0; }
    int Count(const std::string& Id) const { return Count(W.ItemIndex(Id)); }
    int ChestsOpened() const { int N = 0; for (bool O : Opened) N += O; return N; }
    int DoorsOpened() const { int N = 0; for (bool O : DoorOpen) N += O; return N; }
    int BossesBeaten() const { int N = 0; for (bool O : BossDown) N += O; return N; }
    void SetGold(int G) { GoldHeld = std::max(0, G); }
    bool Give(int Item, int N = 1)
    {
        if (Item < 0) return false;
        for (auto& E : Bag) if (E.first == Item) { E.second = std::min(99, E.second + N); return true; }
        if (Bag.size() >= BagSlots) return false;
        Bag.push_back({Item, N});
        return true;
    }
    bool Give(const std::string& Id, int N = 1) { return Give(W.ItemIndex(Id), N); }
    /** Stand on a tile of a map, facing a way (0 down 1 up 2 left 3 right). */
    void Place(const std::string& MapId, int X, int Y, int Face = 0)
    {
        const int M = W.MapIndex(MapId);
        if (M < 0) return;
        Enter(M, X, Y);
        Facing = Face;
        Boxes.clear();
    }
    /** Start a battle with these monsters now (ids, at most three). */
    void ForceBattle(const std::vector<std::string>& Ids, bool Boss = false)
    {
        std::vector<int> K;
        for (const std::string& Id : Ids) { const int I = W.MonsterIndex(Id); if (I >= 0) K.push_back(I); }
        if (!K.empty()) StartBattle(K, Boss, -1, -1);
    }
    /** Steps left before the next ambush (in half-steps). */
    int EncounterCountdown() const { return Countdown; }
    void SetEncounterCountdown(int N) { Countdown = N; }
    std::string TopBox() const;
    /** Where townsperson I stands now (they wander). */
    std::pair<int, int> NpcPosition(int I) const { return I >= 0 && I < static_cast<int>(NpcPos.size()) ? NpcPos[static_cast<size_t>(I)] : std::pair<int, int>(-1, -1); }

    static constexpr size_t BagSlots = 12;

private:
    // ---- the party

    static Member MakeMember(const char* Name, Look L, int Class, int Hp, int Mp, int Atk, int Def, int Agi)
    {
        Member M;
        M.Name = Name; M.L = L; M.Class = Class;
        M.Hp = M.MaxHp = Hp; M.Mp = M.MaxMp = Mp; M.Atk = Atk; M.Def = Def; M.Agi = Agi;
        return M;
    }
    int AtkOf(const Member& P) const { return P.Atk + (P.Weapon >= 0 ? W.Items[static_cast<size_t>(P.Weapon)].Power : 0); }
    int DefOf(const Member& P) const { return P.Def + (P.Armor >= 0 ? W.Items[static_cast<size_t>(P.Armor)].Power : 0); }
    static std::string Upper(std::string S) { for (char& C : S) if (C >= 'a' && C <= 'z') C = static_cast<char>(C - 32); return S; }
    const ItemDef& Item(int I) const { return W.Items[static_cast<size_t>(I)]; }
    const MonsterDef& Mon(int I) const { return W.Monsters[static_cast<size_t>(I)]; }
    bool Take(int ItemI, int N = 1)
    {
        for (size_t i = 0; i < Bag.size(); ++i)
            if (Bag[i].first == ItemI && Bag[i].second >= N)
            {
                Bag[i].second -= N;
                if (Bag[i].second == 0) Bag.erase(Bag.begin() + static_cast<long>(i));
                return true;
            }
        return false;
    }
    int KeyOfTier(int Tier) const
    {
        for (const auto& E : Bag)
            if (Item(E.first).Kind == ItemKind::Key && Item(E.first).Power == Tier) return E.first;
        return -1;
    }

    // ---- maps and moving

    const MapDef& Map() const { return W.Maps[static_cast<size_t>(Cur)]; }
    Tile TileAt(int M, int X, int Y) const
    {
        const MapDef& D = W.Maps[static_cast<size_t>(M)];
        return D.Inside(X, Y) ? Tiles[static_cast<size_t>(M)][static_cast<size_t>(Y * D.W + X)] : D.Outside();
    }
    Tile TileHere(int X, int Y) const { return TileAt(Cur, X, Y); }
    void SetTile(int M, int X, int Y, Tile T)
    {
        const MapDef& D = W.Maps[static_cast<size_t>(M)];
        if (D.Inside(X, Y)) Tiles[static_cast<size_t>(M)][static_cast<size_t>(Y * D.W + X)] = T;
    }
    int NpcAt(int X, int Y) const
    {
        for (size_t i = 0; i < W.Npcs.size(); ++i)
            if (W.Npcs[i].At.Map == Cur && NpcPos[i].first == X && NpcPos[i].second == Y) return static_cast<int>(i);
        return -1;
    }
    int BossAt(int X, int Y) const
    {
        for (size_t i = 0; i < W.Bosses.size(); ++i)
            if (!BossDown[i] && W.Bosses[i].At.Map == Cur && W.Bosses[i].At.X == X && W.Bosses[i].At.Y == Y) return static_cast<int>(i);
        return -1;
    }
    int ChestAt(int X, int Y) const
    {
        for (size_t i = 0; i < W.Chests.size(); ++i)
            if (W.Chests[i].At.Map == Cur && W.Chests[i].At.X == X && W.Chests[i].At.Y == Y) return static_cast<int>(i);
        return -1;
    }
    int DoorAt(int X, int Y) const
    {
        for (size_t i = 0; i < W.Doors.size(); ++i)
            if (W.Doors[i].At.Map == Cur && W.Doors[i].At.X == X && W.Doors[i].At.Y == Y) return static_cast<int>(i);
        return -1;
    }
    const LinkDef* LinkAt(int X, int Y) const
    {
        for (const LinkDef& L : W.Links) if (L.From.Map == Cur && L.From.X == X && L.From.Y == Y) return &L;
        return nullptr;
    }
    int LightRadius() const { return Map().Dark ? (Torch ? 3 : 1) : 99; }

    void Enter(int M, int X, int Y)
    {
        const bool WasDark = Cur >= 0 && Map().Dark;
        Cur = M; PX = X; PY = Y;
        Trail.clear();
        if (!Map().Dark) Torch = false;
        else if (!WasDark) Torch = false;   // a new trip underground needs a new torch
        SetCue(Map().Music);
        LandHere = LandAt(Cur, PX, PY);   // arriving onto a land by stairs or wings is not a crossing
        if (Countdown <= 0) ResetCountdown();
    }

    void ResetCountdown()
    {
        const ZoneDef* Z = W.Zone(Map().ZoneAt(PX, PY));
        const int Rate = Z ? Z->Rate : 20;
        Countdown = R.Range(Rate, Rate * 3);
    }

    void TryStep(int DX, int DY)
    {
        Facing = DX > 0 ? 3 : DX < 0 ? 2 : DY < 0 ? 1 : 0;
        const int NX = PX + DX, NY = PY + DY;
        const MapDef& M = Map();
        if (!M.Inside(NX, NY))
        {
            if (M.ExitMap >= 0) { Enter(M.ExitMap, M.ExitX, M.ExitY); Sfx.push_back("STAIRS"); }
            else Bumped();
            return;
        }
        if (NpcAt(NX, NY) >= 0) { Bumped(); return; }
        const int Bo = BossAt(NX, NY);
        if (Bo >= 0) { MeetBoss(Bo); return; }
        const Tile T = TileHere(NX, NY);
        if (T == Tile::Locked) { TryUnlock(NX, NY); return; }
        if (!Walkable(T)) { Bumped(); return; }
        Trail.push_front({PX, PY});
        if (Trail.size() > 4) Trail.pop_back();
        PX = NX; PY = NY;
        MoveT = 0.0;
        Idle = 0.0;
        ++StepCount;
        ++WalkFrame;
        Arrive(T);
        WarmEgg();
        if (Boxes.empty()) CrossLands();
    }

    void Bumped() { Bump = 0.15; Sfx.push_back("BUMP"); }

    void Arrive(Tile T)
    {
        if (const LinkDef* L = LinkAt(PX, PY))
        {
            Sfx.push_back(T == Tile::StairsDown || T == Tile::StairsUp ? "STAIRS" : "ENTER");
            Enter(L->To.Map, L->To.X, L->To.Y);
            if (!Map().Dark && Map().ExitMap >= 0) Say("WELCOME TO " + Map().Title + ".");
            else if (Map().Dark && !Torch) Say("IT IS DARK. A TORCH WOULD HELP.");
            return;
        }
        if (T == Tile::Portal)
        {
            Say("THE PORTAL PULLS YOU HOME.", [this]() { ExitRequested = true; });
            Sfx.push_back("PORTAL");
            return;
        }
        // Poison and swamps bite each step, but never kill: you limp home on 1.
        bool Hurt = false;
        for (Member& P : Party)
        {
            if (!P.Alive()) continue;
            if (P.Poisoned && P.Hp > 1) { --P.Hp; Hurt = true; }
            if (T == Tile::Swamp && P.Hp > 1) { --P.Hp; Hurt = true; }
        }
        if (Hurt) { Flash = 0.12; Sfx.push_back("HURT"); }
        // The ambush countdown: forests, hills and swamps count for more.
        const char Z = Map().ZoneAt(PX, PY);
        if (Z != '.' && W.Zone(Z))
        {
            Countdown -= (T == Tile::Tree || T == Tile::Hill || T == Tile::Swamp) ? 3 : 2;
            if (Countdown <= 0) { Ambush(*W.Zone(Z)); ResetCountdown(); }
        }
    }

    void Ambush(const ZoneDef& Z)
    {
        auto Pick = [&]() -> const ZoneEntry& {
            int Total = 0;
            for (const ZoneEntry& E : Z.Entries) Total += E.Weight;
            int Roll = R.Range(0, Total - 1);
            for (const ZoneEntry& E : Z.Entries) { Roll -= E.Weight; if (Roll < 0) return E; }
            return Z.Entries.back();
        };
        const ZoneEntry& Lead = Pick();
        std::vector<int> Group(static_cast<size_t>(R.Range(Lead.Min, Lead.Max)), Lead.Monster);
        if (Group.size() < 3 && R.Chance(3)) Group.push_back(Pick().Monster);
        StartBattle(Group, false, -1, -1);
    }

    // ---- what A does in the field

    void Interact()
    {
        static const int DXs[4] = {0, 0, -1, 1}, DYs[4] = {1, -1, 0, 0};
        const int NX = PX + DXs[Facing], NY = PY + DYs[Facing];
        int N = NpcAt(NX, NY);
        if (N < 0 && TileHere(NX, NY) == Tile::Counter) N = NpcAt(NX + DXs[Facing], NY + DYs[Facing]);
        if (N >= 0) { Talk(N); return; }
        const int Bo = BossAt(NX, NY);
        if (Bo >= 0) { MeetBoss(Bo); return; }
        const Tile T = TileHere(NX, NY);
        if (T == Tile::Chest) { OpenChest(NX, NY); return; }
        if (T == Tile::Locked) { TryUnlock(NX, NY); return; }
        OpenCommand();
    }

    static std::string Quote(const std::string& L) { return L.empty() ? L : "'" + L + "'"; }

    void Talk(int N)
    {
        const NpcDef& D = W.Npcs[static_cast<size_t>(N)];
        // What a person says is in quotes, a paragraph a line, the way the genre marks speech from narration.
        std::string S;
        for (const std::string& L : D.Lines) S += Quote(L) + "\n";
        switch (D.R)
        {
        case Role::News:
            S += Quote("NEWS OF THE DAY:") + "\n";
            for (const std::string& L : W.News) S += Quote("* " + L) + "\n";
            Say(S);
            break;
        case Role::Inn:
        {
            const int Price = D.Price;
            Say(S + Quote("A NIGHT IS " + std::to_string(Price) + " GOLD. WILL YOU STAY?"), [this, Price]() { AskInn(Price); });
            break;
        }
        case Role::Shop:
        {
            const int Sh = D.Shop;
            Say(S, [this, Sh]() { OpenShop(Sh); });
            break;
        }
        case Role::Queen:
        {
            for (Member& P : Party) { P.Hp = P.MaxHp; P.Mp = P.MaxMp; P.Poisoned = false; P.Asleep = 0; }
            RespawnMap = Cur; RespawnX = D.At.X; RespawnY = D.At.Y + 1;
            const Member& H = Party[0];
            Say(S + Quote("MAY THE STARS GUARD YOU. I WILL REMEMBER YOU HERE.") + "\n" + Quote(H.Name + " NEEDS "
                + std::to_string(std::max(0, ExpToNext(H.Lvl) - H.Exp)) + " EXP TO REACH LEVEL " + std::to_string(H.Lvl + 1) + "."));
            Sfx.push_back("BLESS");
            break;
        }
        default:
            Say(S);
            break;
        }
        ++Talks;
    }

    void OpenChest(int X, int Y)
    {
        const int C = ChestAt(X, Y);
        if (C < 0 || Opened[static_cast<size_t>(C)]) return;
        const ChestDef& D = W.Chests[static_cast<size_t>(C)];
        if (D.Kind == LootKind::Mimic)
        {
            Sfx.push_back("CHEST");
            Say("THE CHEST OPENS... AND BITES!", [this, C, D]() { StartBattle({D.Mimic}, false, -1, C); });
            return;
        }
        if (D.Kind == LootKind::Item)
        {
            if (!Give(D.Item)) { Say("THE BAG IS FULL. THE CHEST STAYS SHUT."); return; }
            Say("INSIDE IS " + Article(Item(D.Item).Name) + "!");
        }
        else
        {
            GoldHeld += D.Gold;
            Say("INSIDE ARE " + std::to_string(D.Gold) + " GOLD PIECES!");
        }
        Opened[static_cast<size_t>(C)] = true;
        SetTile(Cur, X, Y, Tile::ChestOpen);
        Sfx.push_back("CHEST");
    }

    static std::string Article(const std::string& Name)
    {
        return (std::string("AEIOU").find(Name[0]) != std::string::npos ? "AN " : "A ") + Name;
    }

    void TryUnlock(int X, int Y)
    {
        const int D = DoorAt(X, Y);
        if (D < 0) return;
        const int Tier = W.Doors[static_cast<size_t>(D)].Tier;
        static const char* Metal[4] = {"", "BRONZE", "SILVER", "STAR"};
        const int Key = KeyOfTier(Tier);
        if (Key < 0)
        {
            Say(std::string("IT IS LOCKED. THE LOCK IS ") + Metal[std::min(3, std::max(1, Tier))] + ".");
            Sfx.push_back("LOCKED");
            return;
        }
        Take(Key);
        DoorOpen[static_cast<size_t>(D)] = true;
        SetTile(Cur, X, Y, Tile::Door);
        Say("THE " + Item(Key).Name + " TURNS. THE DOOR OPENS.");
        Sfx.push_back("DOOR");
    }

    void MeetBoss(int Bo)
    {
        const BossDef& B = W.Bosses[static_cast<size_t>(Bo)];
        Say("THE " + Mon(B.Monster).Name + " BLOCKS THE WAY! THERE IS NO TURNING BACK.",
            [this, Bo, B]() { StartBattle({B.Monster}, true, Bo, -1); });
    }

    // ---- boxes: messages, menus, shops

    enum class BoxKind { Message, Command, Items, Members, Spells, Status, Equip, ShopTop, ShopBuy, ShopSell, YesNo };
    enum EPurpose { PNone, PUseOn, PCaster, PSpellOn, PEquipWho, PEquipItem, PBattleAlly = 10 };
    struct Box
    {
        BoxKind Kind = BoxKind::Message;
        std::vector<std::string> Rows;   // menu rows, or the message's lines
        std::vector<int> Ids;            // what each row stands for
        int Cursor = 0, Page = 0;
        int Purpose = PNone, Arg = -1, Arg2 = -1;
        double Shown = 0.0;              // typewriter: characters of this page revealed so far (Message boxes)
        std::function<void()> OnClose;
    };
    static constexpr double TypeSpeed = 60.0;   // characters per second
    std::vector<Box> Boxes;

    void Say(const std::string& Text, std::function<void()> Then = nullptr)
    {
        Box B;
        B.Kind = BoxKind::Message;
        B.Rows = Wrap(Text, 28);
        while (!B.Rows.empty() && B.Rows.back().empty()) B.Rows.pop_back();
        B.OnClose = std::move(Then);
        LastSaid = Text;
        Boxes.push_back(std::move(B));
    }

    void Push(BoxKind K, std::vector<std::string> Rows, std::vector<int> Ids, int Purpose = PNone, int Arg = -1, int Arg2 = -1)
    {
        Box B;
        B.Kind = K; B.Rows = std::move(Rows); B.Ids = std::move(Ids); B.Purpose = Purpose; B.Arg = Arg; B.Arg2 = Arg2;
        Boxes.push_back(std::move(B));
    }

    void Close()
    {
        if (Boxes.empty()) return;
        std::function<void()> Then = std::move(Boxes.back().OnClose);
        Boxes.pop_back();
        if (Then) Then();
    }

    void CloseAllMenus()
    {
        while (!Boxes.empty() && Boxes.back().Kind != BoxKind::Message) Boxes.pop_back();
    }

    void OpenCommand() { Push(BoxKind::Command, {"TALK", "SPELL", "STATUS", "ITEM", "SEARCH", "EQUIP"}, {4, 1, 2, 0, 5, 3}); }

    /** TALK from the menu: whoever is ahead, else nobody. */
    void TalkAhead()
    {
        static const int DXs[4] = {0, 0, -1, 1}, DYs[4] = {1, -1, 0, 0};
        const int NX = PX + DXs[Facing], NY = PY + DYs[Facing];
        int N = NpcAt(NX, NY);
        if (N < 0 && TileHere(NX, NY) == Tile::Counter) N = NpcAt(NX + DXs[Facing], NY + DYs[Facing]);
        CloseAllMenus();
        if (N >= 0) Talk(N);
        else Say("THERE IS NO ONE THERE.");
    }

    /** SEARCH from the menu: what is underfoot or ahead. */
    void SearchHere()
    {
        static const int DXs[4] = {0, 0, -1, 1}, DYs[4] = {1, -1, 0, 0};
        const int NX = PX + DXs[Facing], NY = PY + DYs[Facing];
        CloseAllMenus();
        const Tile Here = TileHere(PX, PY), Ahead = TileHere(NX, NY);
        if (Here == Tile::StairsDown) { Say("THERE ARE STAIRS GOING DOWN."); return; }
        if (Here == Tile::StairsUp) { Say("THERE ARE STAIRS GOING UP."); return; }
        if (Here == Tile::Portal) { Say("THE PORTAL HUMS UNDERFOOT."); return; }
        if (Ahead == Tile::Chest) { OpenChest(NX, NY); return; }
        if (Ahead == Tile::Locked) { TryUnlock(NX, NY); return; }
        if (Ahead == Tile::ChestOpen) { Say("THE CHEST IS EMPTY."); return; }
        Say(std::string(Party[0].Name) + " SEARCHED THE GROUND.\nNOTHING HERE.");
    }

    void OpenItems(int Purpose)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        for (const auto& E : Bag)
        {
            if (Purpose == 1 && Item(E.first).Kind != ItemKind::Use) continue;   // battle: usable things only
            char B[40];
            std::snprintf(B, sizeof(B), "%-12s%3d", Item(E.first).Name.c_str(), E.second);
            Rows.push_back(B);
            Ids.push_back(E.first);
        }
        if (Rows.empty()) { Say(Purpose == 1 ? "NOTHING TO USE." : "THE BAG IS EMPTY."); return; }
        Push(BoxKind::Items, Rows, Ids, Purpose);
    }

    void OpenMembers(int Purpose, int Arg = -1, int Arg2 = -1)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        for (size_t i = 0; i < Party.size(); ++i)
        {
            if (Purpose == PCaster)
            {
                bool Any = false;
                for (int S : {SpHeal, SpCure}) Any |= Party[i].Knows(S);
                if (!Any || !Party[i].Alive()) continue;
            }
            Rows.push_back(Party[i].Name);
            Ids.push_back(static_cast<int>(i));
        }
        if (Rows.empty()) { Say("NOBODY KNOWS A SPELL TO CAST HERE."); return; }
        Push(BoxKind::Members, Rows, Ids, Purpose, Arg, Arg2);
    }

    void OpenSpells(int Caster, bool InBattle)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        const Member& P = Party[static_cast<size_t>(Caster)];
        for (int S = 0; S < SpCount; ++S)
        {
            if (!P.Knows(S) || (!InBattle && (S == SpZap || S == SpBlaze))) continue;
            char B[32];
            std::snprintf(B, sizeof(B), "%-6s %2d", SpellName(S), SpellCost(S));
            Rows.push_back(B);
            Ids.push_back(S);
        }
        if (Rows.empty()) { Say(P.Name + " KNOWS NO SPELLS YET."); return; }
        Push(BoxKind::Spells, Rows, Ids, PNone, Caster);
    }

    void OpenEquip(int Who)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        for (const auto& E : Bag)
        {
            const ItemDef& D = Item(E.first);
            if (D.Kind != ItemKind::Weapon && D.Kind != ItemKind::Armor) continue;
            char B[40];
            std::snprintf(B, sizeof(B), "%-12s %s%d", D.Name.c_str(), D.Kind == ItemKind::Weapon ? "A+" : "D+", D.Power);
            Rows.push_back(B);
            Ids.push_back(E.first);
        }
        if (Rows.empty()) { Say("NO GEAR IN THE BAG."); return; }
        Push(BoxKind::Equip, Rows, Ids, PNone, Who);
    }

    void OpenShop(int Shop)
    {
        Push(BoxKind::ShopTop, {"BUY", "SELL", "LEAVE"}, {0, 1, 2}, PNone, Shop);
    }

    void OpenBuy(int Shop)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        for (int I : W.Shops[static_cast<size_t>(Shop)].Stock)
        {
            char B[40];
            std::snprintf(B, sizeof(B), "%-12s%5d", Item(I).Name.c_str(), Item(I).Price);
            Rows.push_back(B);
            Ids.push_back(I);
        }
        Push(BoxKind::ShopBuy, Rows, Ids, PNone, Shop);
    }

    void OpenSell(int Shop)
    {
        std::vector<std::string> Rows;
        std::vector<int> Ids;
        for (const auto& E : Bag)
        {
            const ItemDef& D = Item(E.first);
            if (D.SellValue() <= 0) continue;   // found-only keys and the like: no shop will take them
            char B[40];
            std::snprintf(B, sizeof(B), "%-12s%5d", D.Name.c_str(), D.SellValue());
            Rows.push_back(B);
            Ids.push_back(E.first);
        }
        if (Rows.empty()) { Say("YOU HAVE NOTHING I CAN BUY."); return; }
        Push(BoxKind::ShopSell, Rows, Ids, PNone, Shop);
    }

    void AskInn(int Price) { Push(BoxKind::YesNo, {"YES", "NO"}, {1, 0}, PNone, Price); }

    void BoxChoose()
    {
        Box& B = Boxes.back();
        if (B.Kind == BoxKind::Message)
        {
            if (B.Shown < Ui::PageChars(B.Rows, B.Page)) { B.Shown = 1e9; return; }   // show the rest of the page
            if ((B.Page + 1) * 4 < static_cast<int>(B.Rows.size())) { ++B.Page; B.Shown = 0.0; return; }
            Close();
            return;
        }
        if (B.Kind == BoxKind::Status) { Boxes.pop_back(); return; }
        if (B.Ids.empty()) { Boxes.pop_back(); return; }
        const int Id = B.Ids[static_cast<size_t>(B.Cursor)];
        const int Purpose = B.Purpose, Arg = B.Arg, Arg2 = B.Arg2;
        switch (B.Kind)
        {
        case BoxKind::Command:
            if (Id == 0) OpenItems(0);
            else if (Id == 1) OpenMembers(PCaster);
            else if (Id == 2) Push(BoxKind::Status, {}, {});
            else if (Id == 4) TalkAhead();
            else if (Id == 5) SearchHere();
            else OpenMembers(PEquipWho);
            break;
        case BoxKind::Items:
            if (Purpose == 1) { BattleItemChosen(Id); break; }
            UseFromBag(Id);
            break;
        case BoxKind::Members:
            if (Purpose == PUseOn) { CloseAllMenus(); ApplyItem(Arg, Id); }
            else if (Purpose == PCaster) OpenSpells(Id, false);
            else if (Purpose == PSpellOn) { CloseAllMenus(); FieldCast(Arg2, Arg, Id); }
            else if (Purpose == PEquipWho) OpenEquip(Id);
            else if (Purpose == PEquipItem) { CloseAllMenus(); Equip(Id, Arg); }
            else if (Purpose == PBattleAlly) BattleTargetAlly(Id);
            break;
        case BoxKind::Spells:
            if (ModeNow == Mode::Battle) { BattleSpellChosen(Id); break; }
            if (Party[static_cast<size_t>(Arg)].Mp < SpellCost(Id)) { Say("NOT ENOUGH MP."); break; }
            OpenMembers(PSpellOn, Id, Arg);
            break;
        case BoxKind::Equip:
            CloseAllMenus();
            Equip(Arg, Id);
            break;
        case BoxKind::ShopTop:
            if (Id == 0) OpenBuy(Arg);
            else if (Id == 1) OpenSell(Arg);
            else { Boxes.pop_back(); Say("COME AGAIN!"); }
            break;
        case BoxKind::ShopBuy:
        {
            const ItemDef& D = Item(Id);
            if (GoldHeld < D.Price) { Say("YOU CAN'T AFFORD THAT."); break; }
            if (!Give(Id)) { Say("YOUR BAG IS FULL."); break; }
            GoldHeld -= D.Price;
            Sfx.push_back("BUY");
            Say("HERE IS YOUR " + D.Name + ". ANYTHING ELSE?");
            break;
        }
        case BoxKind::ShopSell:
        {
            const ItemDef& D = Item(Id);
            Take(Id);
            GoldHeld += D.SellValue();
            Sfx.push_back("BUY");
            Boxes.pop_back();
            Say("I'LL GIVE YOU " + std::to_string(D.SellValue()) + " GOLD. THANK YOU!");
            break;
        }
        case BoxKind::YesNo:
            Boxes.pop_back();
            if (Id == 0) { Say("COME AGAIN, TRAVELERS."); break; }
            if (GoldHeld < Arg) { Say("YOU CAN'T AFFORD A ROOM. SORRY."); break; }
            GoldHeld -= Arg;
            for (Member& P : Party) { P.Hp = P.MaxHp; P.Mp = P.MaxMp; P.Poisoned = false; P.Asleep = 0; }
            SetCue("INN");
            Sfx.push_back("INN");
            Say("GOOD MORNING! YOUR PARTY IS RESTED.", [this]() { SetCue(Map().Music); });
            break;
        default:
            break;
        }
    }

    void UseFromBag(int I)
    {
        const ItemDef& D = Item(I);
        if (D.Kind == ItemKind::Weapon || D.Kind == ItemKind::Armor) { OpenMembers(PEquipItem, I); return; }
        if (D.Kind == ItemKind::Key) { Say("FACE A LOCKED DOOR AND PRESS A."); return; }
        if (D.Kind == ItemKind::Treasure) { Say("IT GLITTERS. A SHOP WOULD PAY WELL FOR IT."); return; }
        if (D.Kind == ItemKind::Egg)
        {
            if (Party.size() >= static_cast<size_t>(MaxParty)) { Say("IT IS WARM, BUT THE PARTY IS FULL."); return; }
            Say(EggWarmth * 3 >= EggNeed * 2 ? "IT ROCKS IN YOUR HANDS. NOT LONG NOW." : EggWarmth * 3 >= EggNeed ? "IT IS WARM. KEEP WALKING." : "A DRAGON EGG. CARRY IT AND IT WILL HATCH.");
            return;
        }
        if (D.Id == "TORCH")
        {
            if (!Map().Dark) { Say("IT IS BRIGHT ENOUGH HERE."); return; }
            Take(I);
            Torch = true;
            CloseAllMenus();
            Say("THE TORCH FLARES. THE CAVE OPENS UP AROUND YOU.");
            Sfx.push_back("TORCH");
            return;
        }
        if (D.Id == "WINGS")
        {
            if (Map().Dark) { Say("THE WINGS CAN'T FLY UNDER STONE."); return; }
            Take(I);
            CloseAllMenus();
            Enter(W.Spawn.Map, W.Spawn.X, W.Spawn.Y);
            Say("THE WINGS CARRY YOU TO THE PORTAL.");
            Sfx.push_back("WINGS");
            return;
        }
        OpenMembers(PUseOn, I);
    }

    /** HERB, TONIC, ANTIDOTE, the seeds: on one member. Returns the line it says. */
    std::string ItemEffect(int I, int Who)
    {
        const ItemDef& D = Item(I);
        Member& P = Party[static_cast<size_t>(Who)];
        Take(I);
        if (!P.Alive()) return P.Name + " CAN'T USE IT NOW.";
        if (D.Id == "HERB") { const int H = std::min(P.MaxHp - P.Hp, D.Power + R.Range(0, 5)); P.Hp += H; return P.Name + " EATS A HERB. +" + std::to_string(H) + " HP."; }
        if (D.Id == "TONIC") { const int M = std::min(P.MaxMp - P.Mp, D.Power); P.Mp += M; return P.Name + " DRINKS A TONIC. +" + std::to_string(M) + " MP."; }
        if (D.Id == "ANTIDOTE") { P.Poisoned = false; P.Asleep = 0; return P.Name + " IS CURED."; }
        if (D.Id == "MIGHT_SEED") { P.Atk += D.Power; return P.Name + "'S ATTACK RISES BY " + std::to_string(D.Power) + "!"; }
        if (D.Id == "LIFE_SEED") { P.MaxHp += D.Power; P.Hp += D.Power; return P.Name + "'S MAX HP RISES BY " + std::to_string(D.Power) + "!"; }
        return "NOTHING HAPPENS.";
    }

    void ApplyItem(int I, int Who) { Say(ItemEffect(I, Who)); Sfx.push_back("ITEM"); }

    void FieldCast(int Caster, int S, int Who)
    {
        Member& C = Party[static_cast<size_t>(Caster)];
        if (C.Mp < SpellCost(S)) { Say("NOT ENOUGH MP."); return; }
        C.Mp -= SpellCost(S);
        Member& P = Party[static_cast<size_t>(Who)];
        Sfx.push_back("SPELL");
        if (!P.Alive()) { Say("THE SPELL CAN'T REACH THE FALLEN."); return; }
        if (S == SpHeal)
        {
            const int H = std::min(P.MaxHp - P.Hp, 10 + R.Range(0, 7) + C.Lvl * 2);
            P.Hp += H;
            Say(C.Name + " CASTS HEAL. " + P.Name + " +" + std::to_string(H) + " HP.");
        }
        else { P.Poisoned = false; P.Asleep = 0; Say(C.Name + " CASTS CURE. " + P.Name + " IS CURED."); }
    }

    void Equip(int Who, int I)
    {
        Member& P = Party[static_cast<size_t>(Who)];
        const ItemDef& D = Item(I);
        int& Slot = D.Kind == ItemKind::Weapon ? P.Weapon : P.Armor;
        if (!Take(I)) return;
        if (Slot >= 0) Give(Slot);
        Slot = I;
        Say(P.Name + " EQUIPS THE " + D.Name + ". ATK " + std::to_string(AtkOf(P)) + " DEF " + std::to_string(DefOf(P)) + ".");
        Sfx.push_back("EQUIP");
    }

    // ---- battles

    struct Line
    {
        std::string Text;
        int Foe = -1, FoeHp = 0;      // after this line, foe Foe shows FoeHp
        int Mem = -1, MemHp = 0;      // after this line, member Mem shows MemHp
        bool Gone = false;            // the foe ran away
        std::string Sound;
    };
    struct Act { int Who = 0; int What = 0; int Target = -1; int Arg = -1; };   // What: 0 fight 1 spell 2 item 3 defend 4 run
    /** A number that pops where a hit landed and rises away: foe slot or member card, amount, life left. */
    struct Pop { int Foe = -1, Mem = -1, Amount = 0; double Life = 0.0; };
    std::vector<Pop> Pops;
    bool ForceShiny = false;   // the harness: every foe of the next battle is shiny
    stage::Director Stage;
    int ShinySeen = 0;

    enum class Phase { Intro, Command, Target, Play, Ending };
    Phase Ph = Phase::Intro;
    std::vector<Foe> Enemies;
    std::vector<int> FoeShown, MemShown;
    std::vector<bool> FoeGoneShown;
    std::vector<Act> Picks;
    std::deque<Line> Queue;
    std::vector<std::string> Log;
    int Actor = 0, Menu = 0, TargetI = 0, Pending = -1, PendingArg = -1;
    int FightBoss = -1, FightChest = -1;
    bool NoRun = false, Won = false, Lost = false, Fled = false;
    double PlayT = 0.0;
    std::vector<int> FoeFlash;
    mutable std::vector<int> FoeSlotX;   // where each foe was drawn this frame (for the damage numbers)

    void StartBattle(const std::vector<int>& Kinds, bool Boss, int BossIndex, int ChestIndex)
    {
        Enemies.clear();
        for (size_t i = 0; i < Kinds.size() && i < 3; ++i)
        {
            const MonsterDef& M = Mon(Kinds[i]);
            Foe F;
            F.Kind = Kinds[i];
            F.Hp = F.MaxHp = M.Hp + R.Range(0, M.Hp / 8);
            F.Shiny = ForceShiny || R.Chance(256);
            if (F.Shiny) { F.Hp = F.MaxHp = F.MaxHp * 3 / 2; ++ShinySeen; }
            Enemies.push_back(F);
        }
        FoeShown.clear(); FoeGoneShown.clear();
        for (const Foe& F : Enemies) { FoeShown.push_back(F.Hp); FoeGoneShown.push_back(false); }
        FoeFlash.assign(Enemies.size(), 0);
        FoeSlotX.assign(Enemies.size(), 0);
        Pops.clear();
        MemShown.clear();
        for (const Member& P : Party) MemShown.push_back(P.Hp);
        ModeNow = Mode::Battle;
        ++BattleCount;
        FightBoss = BossIndex; FightChest = ChestIndex;
        NoRun = Boss || Mon(Kinds[0]).Has(Trait::Boss);
        Won = Lost = Fled = false;
        Picks.clear(); Queue.clear(); Log.clear();
        Boxes.clear();
        SetCue(NoRun ? "BOSS" : "BATTLE");
        Sfx.push_back("AMBUSH");
        std::string Names = Mon(Enemies[0].Kind).Name;
        {
            std::vector<bool> Sh;
            for (const Foe& F : Enemies) Sh.push_back(F.Shiny);
            Stage.Begin(static_cast<int>(Party.size()), static_cast<int>(Enemies.size()), Sh);
        }
        for (const Foe& F : Enemies) if (F.Shiny) { Log.push_back("A SHINY " + Mon(F.Kind).Name + " GLITTERS!"); Sfx.push_back("SHINY"); }
        if (Enemies.size() > 1) Log.push_back("MONSTERS APPEAR!");
        else
        {
            const MonsterDef& M = Mon(Enemies[0].Kind);
            Log.push_back((M.Rarity == "RARE" && !NoRun ? "A RARE " : "") + M.Name + " APPEARS!");
        }
        Ph = Phase::Intro;
        LastSaid = Log.back();
    }

    /** A line in the battle log that needs no playback (a refused command). */
    void Note(const std::string& T) { Log.push_back(T); LastSaid = T; Sfx.push_back("BUMP"); }

    bool FoesLeft() const { for (const Foe& F : Enemies) if (!F.Down()) return true; return false; }
    bool PartyStanding() const { for (const Member& P : Party) if (P.Alive()) return true; return false; }
    int FirstFoe() const { for (size_t i = 0; i < Enemies.size(); ++i) if (!Enemies[i].Down()) return static_cast<int>(i); return -1; }

    void NextActor(int From)
    {
        Actor = From;
        while (Actor < static_cast<int>(Party.size()) && (!Party[static_cast<size_t>(Actor)].Alive() || Party[static_cast<size_t>(Actor)].Asleep > 0))
        {
            if (Party[static_cast<size_t>(Actor)].Alive()) Picks.push_back({Actor, 5, -1, -1});   // asleep: skips
            ++Actor;
        }
        Menu = 0;
        if (Actor >= static_cast<int>(Party.size())) { Resolve(); return; }
        Ph = Phase::Command;
    }

    void BattleCommand(int Which)
    {
        Member& P = Party[static_cast<size_t>(Actor)];
        switch (Which)
        {
        case 0:
            Pending = 0; PendingArg = -1;
            BeginFoeTarget();
            break;
        case 1:
        {
            bool Any = false;
            for (int S = 0; S < SpCount; ++S) Any |= P.Knows(S);
            if (!Any) { Note(P.Name + " KNOWS NO SPELLS."); return; }
            OpenSpells(Actor, true);
            break;
        }
        case 2: OpenItems(1); break;
        case 3: Picks.push_back({Actor, 3, -1, -1}); NextActor(Actor + 1); break;
        default:
            if (NoRun) { Note("THERE IS NO ESCAPE!"); return; }
            Picks.push_back({Actor, 4, -1, -1});
            Resolve();
            break;
        }
    }

    void BeginFoeTarget()
    {
        int Alive = 0;
        for (const Foe& F : Enemies) Alive += !F.Down();
        TargetI = FirstFoe();
        if (Alive <= 1) { ChooseTarget(); return; }
        Ph = Phase::Target;
    }

    void ChooseTarget()
    {
        Picks.push_back({Actor, Pending, TargetI, PendingArg});
        Pending = -1;
        NextActor(Actor + 1);
    }

    void BattleSpellChosen(int S)
    {
        Member& P = Party[static_cast<size_t>(Actor)];
        if (P.Mp < SpellCost(S)) { Boxes.clear(); Note("NOT ENOUGH MP."); return; }
        Boxes.clear();
        if (S == SpZap) { Pending = 1; PendingArg = S; BeginFoeTarget(); return; }
        if (S == SpBlaze) { Picks.push_back({Actor, 1, -1, S}); NextActor(Actor + 1); return; }
        OpenMembers(PBattleAlly, S, 1);   // HEAL / CURE: on whom
    }

    void BattleItemChosen(int I)
    {
        Boxes.clear();
        OpenMembers(PBattleAlly, I, 2);
    }

    void BattleTargetAlly(int Who)
    {
        const Box& B = Boxes.back();
        const int Arg = B.Arg, Kind = B.Arg2;   // Kind 1 spell, 2 item
        Boxes.clear();
        Picks.push_back({Actor, Kind, Who, Arg});
        NextActor(Actor + 1);
    }

    int Damage(int Atk, int Def)
    {
        const int Base = Atk - Def / 2;
        if (Base <= 0) return R.Range(0, 1);
        return std::max(1, Base / 2 + R.Range(0, std::max(1, Base / 2)));
    }

    void Emit(const std::string& T, const char* Sound = "") { Line L; L.Text = T; L.Sound = Sound; Queue.push_back(L); }
    void EmitFoe(const std::string& T, int F, const char* Sound = "") { Line L; L.Text = T; L.Foe = F; L.FoeHp = Enemies[static_cast<size_t>(F)].Hp; L.Gone = Enemies[static_cast<size_t>(F)].Fled; L.Sound = Sound; Queue.push_back(L); }
    void EmitMem(const std::string& T, int M, const char* Sound = "") { Line L; L.Text = T; L.Mem = M; L.MemHp = Party[static_cast<size_t>(M)].Hp; L.Sound = Sound; Queue.push_back(L); }

    void HitFoe(int F, int D, const std::string& What)
    {
        Foe& E = Enemies[static_cast<size_t>(F)];
        const MonsterDef& M = Mon(E.Kind);
        E.Hp = std::max(0, E.Hp - D);
        EmitFoe(What + M.Name + " TAKES " + std::to_string(D) + ".", F, D > 0 ? "HIT" : "MISS");
        if (E.Hp <= 0) Emit(M.Name + " IS DEFEATED!", "DEFEAT");
    }

    void Resolve()
    {
        Ph = Phase::Play;
        struct Turn { int Agi; bool IsFoe; int Index; };
        std::vector<Turn> Order;
        for (size_t i = 0; i < Picks.size(); ++i) Order.push_back({Party[static_cast<size_t>(Picks[i].Who)].Agi + R.Range(0, 5), false, static_cast<int>(i)});
        for (size_t i = 0; i < Enemies.size(); ++i)
        {
            if (Enemies[i].Down()) continue;
            const MonsterDef& M = Mon(Enemies[i].Kind);
            Order.push_back({M.Agi + R.Range(0, 5), true, static_cast<int>(i)});
            if (M.Has(Trait::Double)) Order.push_back({M.Agi / 2 + R.Range(0, 5), true, static_cast<int>(i)});
        }
        std::stable_sort(Order.begin(), Order.end(), [](const Turn& A, const Turn& B) { return A.Agi > B.Agi; });
        std::vector<bool> Defending(Party.size(), false);
        for (const Act& A : Picks) if (A.What == 3) Defending[static_cast<size_t>(A.Who)] = true;
        // Running happens first or not at all.
        for (const Act& A : Picks)
            if (A.What == 4)
            {
                int Best = 0, Ours = 0, N = 0;
                for (const Foe& F : Enemies) if (!F.Down()) Best = std::max(Best, Mon(F.Kind).Agi);
                for (const Member& P : Party) if (P.Alive()) { Ours += P.Agi; ++N; }
                const int Chance = std::min(90, std::max(25, 55 + (N ? Ours / N : 0) * 4 - Best * 4));
                if (R.Range(1, 100) <= Chance) { Emit("THE PARTY ESCAPES!", "RUN"); Fled = true; Picks.clear(); FinishRound(); return; }
                Emit("BUT THE WAY IS BLOCKED!", "MISS");
                Order.erase(std::remove_if(Order.begin(), Order.end(), [](const Turn& T) { return !T.IsFoe; }), Order.end());
                break;
            }
        for (const Turn& T : Order)
        {
            if (!FoesLeft() || !PartyStanding()) break;
            if (T.IsFoe) FoeTurn(T.Index, Defending);
            else PartyTurn(Picks[static_cast<size_t>(T.Index)]);
        }
        // Poison bites at the end of each round.
        for (size_t i = 0; i < Party.size(); ++i)
        {
            Member& P = Party[i];
            if (P.Alive() && P.Poisoned && FoesLeft())
            {
                P.Hp = std::max(0, P.Hp - 2);
                EmitMem("POISON STINGS " + P.Name + ".", static_cast<int>(i), "HURT");
                if (!P.Alive()) Emit(P.Name + " FALLS!", "FALL");
            }
            if (P.Asleep > 0) --P.Asleep;
        }
        Picks.clear();
        FinishRound();
    }

    void PartyTurn(const Act& A)
    {
        Member& P = Party[static_cast<size_t>(A.Who)];
        if (!P.Alive()) return;
        if (A.What == 5) { Emit(P.Name + " IS FAST ASLEEP."); return; }
        if (A.What == 3) { Emit(P.Name + " DEFENDS."); return; }
        if (A.What == 2)
        {
            if (Count(A.Arg) <= 0) { Emit(P.Name + " FINDS NOTHING IN THE BAG."); return; }
            EmitMem(ItemEffect(A.Arg, A.Target), A.Target, "ITEM");
            return;
        }
        if (A.What == 1)
        {
            const int S = A.Arg;
            if (P.Mp < SpellCost(S)) { Emit(P.Name + " IS OUT OF MP."); return; }
            P.Mp -= SpellCost(S);
            Emit(P.Name + " CASTS " + SpellName(S) + "!", "SPELL");
            if (S == SpHeal || S == SpCure)
            {
                Member& T = Party[static_cast<size_t>(A.Target)];
                if (!T.Alive()) { Emit("BUT " + T.Name + " HAS FALLEN."); return; }
                if (S == SpHeal)
                {
                    const int H = std::min(T.MaxHp - T.Hp, 10 + R.Range(0, 7) + P.Lvl * 2);
                    T.Hp += H;
                    EmitMem(T.Name + " +" + std::to_string(H) + " HP.", A.Target);
                }
                else { T.Poisoned = false; T.Asleep = 0; EmitMem(T.Name + " IS CURED.", A.Target); }
                return;
            }
            std::vector<int> Targets;
            if (S == SpBlaze) { for (size_t i = 0; i < Enemies.size(); ++i) if (!Enemies[i].Down()) Targets.push_back(static_cast<int>(i)); }
            else Targets.push_back(Retarget(A.Target));
            for (int F : Targets)
            {
                if (F < 0) continue;
                if (Mon(Enemies[static_cast<size_t>(F)].Kind).Has(Trait::Hard)) { EmitFoe("THE SPELL BOUNCES OFF " + Mon(Enemies[static_cast<size_t>(F)].Kind).Name + "!", F, "MISS"); continue; }
                const int D = (S == SpBlaze ? 14 + R.Range(0, 8) : 8 + R.Range(0, 6)) + P.Lvl * 2;
                HitFoe(F, D, "");
            }
            return;
        }
        const int F = Retarget(A.Target);
        if (F < 0) return;
        const MonsterDef& M = Mon(Enemies[static_cast<size_t>(F)].Kind);
        Emit(P.Name + " ATTACKS!", "SWING");
        int D;
        if (R.Chance(16)) { D = AtkOf(P) + R.Range(0, AtkOf(P) / 4); Emit("A MIGHTY BLOW!", "CRIT"); }
        else if (M.Has(Trait::Hard)) D = R.Range(0, 1);
        else D = Damage(AtkOf(P), M.Def);
        if (D == 0) { EmitFoe("A MISS! " + M.Name + " DODGES.", F, "MISS"); return; }
        HitFoe(F, D, "");
    }

    int Retarget(int T) const
    {
        if (T >= 0 && T < static_cast<int>(Enemies.size()) && !Enemies[static_cast<size_t>(T)].Down()) return T;
        return FirstFoe();
    }

    void FoeTurn(int I, const std::vector<bool>& Defending)
    {
        Foe& E = Enemies[static_cast<size_t>(I)];
        if (E.Down()) return;
        const MonsterDef& M = Mon(E.Kind);
        std::vector<int> Alive;
        for (size_t i = 0; i < Party.size(); ++i) if (Party[i].Alive()) Alive.push_back(static_cast<int>(i));
        if (Alive.empty()) return;
        if (M.Has(Trait::Flee) && R.Chance(3)) { E.Fled = true; EmitFoe(M.Name + " RUNS AWAY!", I, "RUN"); return; }
        if (M.Has(Trait::Heal) && R.Chance(2))
        {
            int Worst = -1;
            for (size_t k = 0; k < Enemies.size(); ++k)
                if (!Enemies[k].Down() && Enemies[k].Hp * 2 < Enemies[k].MaxHp && (Worst < 0 || Enemies[k].Hp < Enemies[static_cast<size_t>(Worst)].Hp)) Worst = static_cast<int>(k);
            if (Worst >= 0)
            {
                Foe& T = Enemies[static_cast<size_t>(Worst)];
                const int H = std::min(T.MaxHp - T.Hp, 15 + M.Atk / 2);
                T.Hp += H;
                EmitFoe(M.Name + " CASTS HEAL. " + Mon(T.Kind).Name + " +" + std::to_string(H) + ".", Worst, "SPELL");
                return;
            }
        }
        if (M.Has(Trait::Call) && Enemies.size() < 3 && R.Chance(4))
        {
            Foe F;
            F.Kind = E.Kind;
            F.Hp = F.MaxHp = M.Hp;
            Enemies.push_back(F);
            FoeShown.push_back(0); FoeGoneShown.push_back(false); FoeFlash.push_back(0); FoeSlotX.push_back(0);
            EmitFoe(M.Name + " CALLS FOR HELP! ANOTHER APPEARS.", static_cast<int>(Enemies.size()) - 1, "CALL");
            return;
        }
        const int Who = Alive[static_cast<size_t>(R.Range(0, static_cast<int>(Alive.size()) - 1))];
        Member& P = Party[static_cast<size_t>(Who)];
        if (M.Has(Trait::Sleep) && P.Asleep == 0 && R.Chance(4))
        {
            P.Asleep = R.Range(2, 3);
            Emit(M.Name + " BREATHES SPORES!", "SPORES");
            Emit(P.Name + " FALLS ASLEEP.");
            return;
        }
        if (M.Has(Trait::Zap) && R.Chance(3))
        {
            const int D = 6 + R.Range(0, 6) + M.Atk / 3;
            P.Hp = std::max(0, P.Hp - D);
            Emit(M.Name + " CASTS A BOLT!", "ZAP");
            EmitMem(P.Name + " LOSES " + std::to_string(D) + ".", Who, "HURT");
            if (!P.Alive()) Emit(P.Name + " FALLS!", "FALL");
            return;
        }
        int D = Damage(E.Shiny ? M.Atk * 3 / 2 : M.Atk, DefOf(P));
        if (Defending[static_cast<size_t>(Who)]) D = D / 2;
        P.Hp = std::max(0, P.Hp - D);
        Emit(M.Name + " ATTACKS!", "SWING");
        if (D == 0) { Emit(P.Name + " DODGES!", "MISS"); return; }
        EmitMem(P.Name + " LOSES " + std::to_string(D) + ".", Who, "HURT");
        if (P.Asleep > 0 && R.Chance(2)) { P.Asleep = 0; Emit(P.Name + " WAKES UP!"); }
        if (P.Alive() && M.Has(Trait::Poison) && !P.Poisoned && R.Chance(3)) { P.Poisoned = true; Emit(P.Name + " IS POISONED!", "POISON"); }
        if (!P.Alive()) Emit(P.Name + " FALLS!", "FALL");
    }

    /** After a round: won, lost, fled, or on to the next round of commands (once the lines have played). */
    void FinishRound()
    {
        if (Fled) { Ph = Phase::Play; return; }
        if (!FoesLeft())
        {
            Won = true;
            int Exp = 0, GoldWon = 0;
            std::vector<int> Drops;
            for (const Foe& F : Enemies)
            {
                if (F.Fled) continue;
                const MonsterDef& M = Mon(F.Kind);
                Exp += F.Shiny ? M.Exp * 2 : M.Exp; GoldWon += F.Shiny ? M.Gold * 2 : M.Gold;
                if (M.Drop >= 0 && R.Chance(F.Shiny ? std::max(1, M.DropOneIn / 2) : M.DropOneIn)) Drops.push_back(M.Drop);
            }
            if (Exp == 0 && GoldWon == 0) { Emit("THE MONSTERS ARE GONE."); return; }
            GoldHeld += GoldWon;
            Emit("VICTORY! " + std::to_string(Exp) + " EXP, " + std::to_string(GoldWon) + " GOLD.", "VICTORY");
            for (int D : Drops)
            {
                if (Give(D)) Emit("THE FOE DROPPED " + Article(Item(D).Name) + "!", "CHEST");
                else Emit("A DROP IS LEFT BEHIND: THE BAG IS FULL.");
            }
            for (size_t i = 0; i < Party.size(); ++i)
            {
                Member& P = Party[i];
                if (!P.Alive()) continue;
                P.Exp += Exp;
                while (P.Exp >= ExpToNext(P.Lvl) && P.Lvl < 99) LevelUp(P, static_cast<int>(i));
            }
            return;
        }
        if (!PartyStanding()) { Lost = true; Emit("THE PARTY HAS FALLEN...", "DEFEAT"); return; }
    }

    void LevelUp(Member& P, int Index)
    {
        ++P.Lvl;
        int Hp, Mp, Atk, Def, Agi;
        switch (P.Class)
        {
        case 0: Hp = R.Range(4, 7); Mp = 2; Atk = R.Range(2, 3); Def = R.Range(1, 2); Agi = 1; break;
        case 1: Hp = R.Range(2, 4); Mp = R.Range(3, 5); Atk = 1; Def = 1; Agi = R.Range(1, 2); break;
        case 3: Hp = R.Range(5, 8); Mp = R.Range(2, 4); Atk = R.Range(2, 4); Def = R.Range(1, 2); Agi = R.Range(1, 2); break;
        default: Hp = R.Range(3, 6); Mp = P.Lvl >= 5 ? 2 : 0; Atk = R.Range(2, 3); Def = 1; Agi = R.Range(2, 3); break;
        }
        P.MaxHp += Hp; P.Hp += Hp; P.MaxMp += Mp; P.Mp += Mp; P.Atk += Atk; P.Def += Def; P.Agi += Agi;
        EmitMem(P.Name + " REACHES LEVEL " + std::to_string(P.Lvl) + "!", Index, "LEVEL");
        for (int S = 0; S < SpCount; ++S)
            if (LearnsAt(P.Class, S) == P.Lvl) Emit(P.Name + " LEARNS " + SpellName(S) + "!");
    }

    void PlayNext()
    {
        if (Queue.empty()) return;
        Line L = Queue.front();
        Queue.pop_front();
        {
            stage::LineFacts F;
            F.Text = L.Text; F.Sound = L.Sound;
            F.Foe = L.Foe; F.FoeGone = L.Gone;
            if (L.Foe >= 0 && L.Foe < static_cast<int>(FoeShown.size())) { F.FoeHpBefore = FoeShown[static_cast<size_t>(L.Foe)]; F.FoeHpAfter = L.FoeHp; }
            F.Mem = L.Mem;
            if (L.Mem >= 0 && L.Mem < static_cast<int>(MemShown.size())) { F.MemHpBefore = MemShown[static_cast<size_t>(L.Mem)]; F.MemHpAfter = L.MemHp; }
            for (const Member& P : Party) F.MemberNames.push_back(P.Name);
            for (const Foe& E : Enemies) F.FoeNames.push_back(Mon(E.Kind).Name);
            Stage.OnLine(F);
        }
        Log.push_back(L.Text);
        if (Log.size() > 40) Log.erase(Log.begin());
        LastSaid = L.Text;
        if (L.Foe >= 0 && L.Foe < static_cast<int>(FoeShown.size()))
        {
            if (L.FoeHp < FoeShown[static_cast<size_t>(L.Foe)])
            {
                FoeFlash[static_cast<size_t>(L.Foe)] = 6;
                Pops.push_back({L.Foe, -1, FoeShown[static_cast<size_t>(L.Foe)] - L.FoeHp, 0.9});
            }
            FoeShown[static_cast<size_t>(L.Foe)] = L.FoeHp;
            FoeGoneShown[static_cast<size_t>(L.Foe)] = L.Gone;
        }
        if (L.Mem >= 0)
        {
            if (L.MemHp < MemShown[static_cast<size_t>(L.Mem)]) { Flash = 0.12; Pops.push_back({-1, L.Mem, MemShown[static_cast<size_t>(L.Mem)] - L.MemHp, 0.9}); }
            MemShown[static_cast<size_t>(L.Mem)] = L.MemHp;
        }
        if (!L.Sound.empty()) Sfx.push_back(L.Sound);
        PlayT = 0.0;
    }

    /** Called when the queue has played out. */
    void AfterPlay()
    {
        for (size_t i = 0; i < Party.size(); ++i) MemShown[i] = Party[i].Hp;
        if (Won || Lost || Fled)
        {
            if (Won) SetCue("VICTORY");
            if (Lost) SetCue("DEFEAT");
            Ph = Phase::Ending;
            return;
        }
        NextActor(0);
    }

    void EndBattle()
    {
        ModeNow = Mode::Field;
        Enemies.clear();
        Log.clear();
        if (Won)
        {
            ++WinCount;
            if (FightBoss >= 0) BossDown[static_cast<size_t>(FightBoss)] = true;
            if (FightChest >= 0)
            {
                Opened[static_cast<size_t>(FightChest)] = true;
                const ChestDef& C = W.Chests[static_cast<size_t>(FightChest)];
                SetTile(C.At.Map, C.At.X, C.At.Y, Tile::ChestOpen);
            }
        }
        if (Lost)
        {
            for (Member& P : Party) { P.Hp = P.MaxHp; P.Mp = P.MaxMp; P.Poisoned = false; P.Asleep = 0; }
            GoldHeld /= 2;
            Enter(RespawnMap, RespawnX, RespawnY);
            Facing = 1;
            Say("YOU WAKE, HEALED, BUT YOUR PURSE IS LIGHTER.");
        }
        for (Member& P : Party) P.Asleep = 0;
        SetCue(Map().Music);
        Won = Lost = Fled = false;
        FightBoss = FightChest = -1;
    }

    // ---- messages, music, state

    void SetCue(const std::string& C) { if (C != Cue) { Cue = C; ++CueCount; } }

    Spec W;
    Rng R{1};
    bool Loaded = false;
    std::vector<std::vector<Tile>> Tiles;
    std::vector<bool> Opened, DoorOpen, BossDown;
    std::vector<std::pair<int, int>> NpcPos;
    std::vector<double> NpcTimer;
    std::vector<Member> Party;
    std::vector<std::pair<int, int>> Bag;   // item, count
    std::deque<std::pair<int, int>> Trail;
    std::vector<std::string> Sfx;
    std::string Cue = "FIELD", LastSaid;
    Mode ModeNow = Mode::Field;
    int Cur = -1, PX = 0, PY = 0, Facing = 0, WalkFrame = 0;
    int RespawnMap = 0, RespawnX = 0, RespawnY = 0;
    int CueCount = 1, StepCount = 0, BattleCount = 0, WinCount = 0, Talks = 0, GoldHeld = 60, Countdown = 0;
    bool Torch = false, ExitRequested = false;
    bool Held[4] = {false, false, false, false};
    double MoveT = 1.0, Bump = 0.0, Clock = 0.0, Idle = 0.0, Flash = 0.0;
    /** The title card: the realm's name on black when the portal drops you in; A, B or 2.5 s clears it. */
    double TitleT = 0.0;
    static constexpr double TitleHold = 2.5;
    Frame Screen;

    void WanderNpcs(double Dt);
    void RenderField(Frame& F, int Anim);
    void RenderBattle(Frame& F, int Anim);
    void RenderBoxes(Frame& F, int Anim);
    void ListBox(Frame& F, int X, int Y, int WW, const Box& B, int Anim, int MaxRows);
    void RenderTitle(Frame& F, int Anim);
};

// --------------------------------------------------------------------------------------------- input and time

inline void Realm::Press(Button B)
{
    if (!Loaded) return;
    if (TitleT > 0.0)
    {
        if (B == Button::A || B == Button::B || B == Button::Start) TitleT = 0.0;
        return;
    }
    if (ModeNow == Mode::Battle && Boxes.empty())
    {
        switch (Ph)
        {
        case Phase::Intro:
            if (B == Button::A || B == Button::B) NextActor(0);
            return;
        case Phase::Play:
            if (B == Button::A || B == Button::B) PlayT = 1.0;   // hurry the lines along
            return;
        case Phase::Ending:
            if ((B == Button::A || B == Button::B) && Queue.empty()) EndBattle();
            return;
        case Phase::Target:
        {
            const int N = static_cast<int>(Enemies.size());
            if (B == Button::Left || B == Button::Up || B == Button::Right || B == Button::Down)
            {
                const int Step = (B == Button::Left || B == Button::Up) ? N - 1 : 1;
                for (int k = 0; k < N; ++k) { TargetI = (TargetI + Step) % N; if (!Enemies[static_cast<size_t>(TargetI)].Down()) break; }
            }
            else if (B == Button::A) ChooseTarget();
            else if (B == Button::B) { Ph = Phase::Command; Pending = -1; }
            return;
        }
        case Phase::Command:
            if (B == Button::Up) Menu = (Menu + 4) % 5;
            else if (B == Button::Down) Menu = (Menu + 1) % 5;
            else if (B == Button::A) BattleCommand(Menu);
            else if (B == Button::B)
            {
                // Take back the last member's pick.
                while (!Picks.empty())
                {
                    const Act Last = Picks.back();
                    Picks.pop_back();
                    if (Last.What != 5) { Actor = Last.Who; Menu = 0; break; }
                }
            }
            return;
        }
        return;
    }
    if (!Boxes.empty())
    {
        Box& Top = Boxes.back();
        const int N = static_cast<int>(Top.Rows.size());
        if (Top.Kind == BoxKind::Message || Top.Kind == BoxKind::Status)
        {
            if (B == Button::A || B == Button::B) BoxChoose();
            return;
        }
        const int Cols = Top.Kind == BoxKind::Command ? 2 : 1;
        if (B == Button::Up && N > 0) Top.Cursor = (Top.Cursor + N - Cols) % N;
        else if (B == Button::Down && N > 0) Top.Cursor = (Top.Cursor + Cols) % N;
        else if (Cols > 1 && B == Button::Left && N > 0) Top.Cursor = Top.Cursor % Cols == 0 ? std::min(N - 1, Top.Cursor + Cols - 1) : Top.Cursor - 1;
        else if (Cols > 1 && B == Button::Right && N > 0) Top.Cursor = Top.Cursor % Cols == Cols - 1 || Top.Cursor + 1 >= N ? Top.Cursor - Top.Cursor % Cols : Top.Cursor + 1;
        else if (B == Button::A) BoxChoose();
        else if (B == Button::B) Boxes.pop_back();
        return;
    }
    switch (B)
    {
    case Button::Up: Held[0] = true; if (MoveT >= 1.0) TryStep(0, -1); break;
    case Button::Down: Held[1] = true; if (MoveT >= 1.0) TryStep(0, 1); break;
    case Button::Left: Held[2] = true; if (MoveT >= 1.0) TryStep(-1, 0); break;
    case Button::Right: Held[3] = true; if (MoveT >= 1.0) TryStep(1, 0); break;
    case Button::A: Interact(); break;
    case Button::B: case Button::Start: OpenCommand(); break;
    default: break;
    }
}

inline void Realm::Release(Button B)
{
    if (B == Button::Up) Held[0] = false;
    if (B == Button::Down) Held[1] = false;
    if (B == Button::Left) Held[2] = false;
    if (B == Button::Right) Held[3] = false;
}

inline void Realm::WanderNpcs(double Dt)
{
    for (size_t i = 0; i < W.Npcs.size(); ++i)
    {
        const NpcDef& N = W.Npcs[i];
        if (!N.Wanders || N.At.Map != Cur) continue;
        NpcTimer[i] -= Dt;
        if (NpcTimer[i] > 0) continue;
        NpcTimer[i] = 1.0 + R.Range(0, 10) / 10.0;
        static const int DXs[4] = {0, 0, -1, 1}, DYs[4] = {1, -1, 0, 0};
        const int D = R.Range(0, 3);
        const int NX = NpcPos[i].first + DXs[D], NY = NpcPos[i].second + DYs[D];
        if (std::abs(NX - N.At.X) > 2 || std::abs(NY - N.At.Y) > 2) continue;
        const Tile T = TileHere(NX, NY);
        if (!Walkable(T) || T == Tile::Door || LinkAt(NX, NY) || NpcAt(NX, NY) >= 0 || (NX == PX && NY == PY)) continue;
        bool OnTrail = false;
        for (const auto& P : Trail) OnTrail |= P.first == NX && P.second == NY;
        if (OnTrail) continue;
        NpcPos[i] = {NX, NY};
    }
}

inline void Realm::Tick(double Dt)
{
    if (TitleT > 0.0) { Clock += Dt; TitleT -= Dt; return; }   // the card holds the world, the welcome types after it
    for (Box& B : Boxes)
        if (B.Kind == BoxKind::Message && B.Shown < Ui::PageChars(B.Rows, B.Page)) B.Shown += Dt * TypeSpeed;
    if (!Loaded) return;
    Clock += Dt;
    if (Bump > 0.0) Bump -= Dt;
    if (Flash > 0.0) Flash -= Dt;
    if (MoveT < 1.0) MoveT = std::min(1.0, MoveT + Dt / 0.2);
    for (int& F : FoeFlash) if (F > 0) --F;
    for (Pop& P : Pops) P.Life -= Dt;
    Pops.erase(std::remove_if(Pops.begin(), Pops.end(), [](const Pop& P) { return P.Life <= 0.0; }), Pops.end());
    if (ModeNow == Mode::Battle)
    {
        if (Ph == Phase::Play || (Ph == Phase::Ending && !Queue.empty()))
        {
            PlayT += Dt;
            if (PlayT >= 0.45)
            {
                if (!Queue.empty()) PlayNext();
                else if (Ph == Phase::Play) AfterPlay();
            }
        }
        return;
    }
    WanderNpcs(Dt);
    if (Boxes.empty()) Idle += Dt;
    if (MoveT >= 1.0 && Boxes.empty())
    {
        if (Held[0]) TryStep(0, -1);
        else if (Held[1]) TryStep(0, 1);
        else if (Held[2]) TryStep(-1, 0);
        else if (Held[3]) TryStep(1, 0);
    }
}

// ----------------------------------------------------------------------------------------------- drawing

inline void Realm::RenderField(Frame& F, int Anim)
{
    const double Slide = 1.0 - MoveT;
    static const int DXs[4] = {0, 0, -1, 1}, DYs[4] = {1, -1, 0, 0};
    const int OffX = static_cast<int>(-DXs[Facing] * Slide * TileSize), OffY = static_cast<int>(-DYs[Facing] * Slide * TileSize);
    const int CamX = PX * TileSize + OffX - (ScreenW / 2 - 8), CamY = PY * TileSize + OffY - (ScreenH / 2 - 8);
    const int Light = LightRadius();
    F.Clear(Pal::Black);
    for (int ty = -1; ty <= ScreenH / TileSize + 1; ++ty)
        for (int tx = -1; tx <= ScreenW / TileSize + 1; ++tx)
        {
            const int MX = static_cast<int>(std::floor((CamX + tx * TileSize) / static_cast<double>(TileSize)));
            const int MY = static_cast<int>(std::floor((CamY + ty * TileSize) / static_cast<double>(TileSize)));
            if (std::abs(MX - PX) > Light || std::abs(MY - PY) > Light) continue;   // the dark
            const int SX = MX * TileSize - CamX, SY = MY * TileSize - CamY;
            const Tile T = TileHere(MX, MY);
            int Tier = 1;
            if (T == Tile::Locked) { const int D = DoorAt(MX, MY); if (D >= 0) Tier = W.Doors[static_cast<size_t>(D)].Tier; }
            const uint64_t Salt = static_cast<uint64_t>(MX * 131 + MY * 7919) ^ W.Seed;
            if (T == Tile::Tree) DrawForest(F, SX, SY, Salt);
            else if (T == Tile::Grass) DrawMeadow(F, SX, SY, Salt);
            else if (T == Tile::Cobble) DrawFlagstones(F, SX, SY);
            else if (T == Tile::Stone) DrawBlockWall(F, SX, SY);
            else DrawTile(F, SX, SY, T, Salt, Anim, Tier);
        }
    auto Visible = [&](int X, int Y) { return std::abs(X - PX) <= Light && std::abs(Y - PY) <= Light; };
    for (size_t i = 0; i < W.Npcs.size(); ++i)
    {
        if (W.Npcs[i].At.Map != Cur || !Visible(NpcPos[i].first, NpcPos[i].second)) continue;
        int Face = 0;
        if (std::abs(NpcPos[i].first - PX) + std::abs(NpcPos[i].second - PY) <= 2)   // they look at you when you're near
            Face = PX < NpcPos[i].first ? 2 : PX > NpcPos[i].first ? 3 : PY < NpcPos[i].second ? 1 : 0;
        Person(F, NpcPos[i].first * TileSize - CamX, NpcPos[i].second * TileSize - CamY, RoleKey(W.Npcs[i].R), W.Npcs[i].L, Face, Anim / 4);
    }
    for (size_t i = 0; i < W.Bosses.size(); ++i)
    {
        const BossDef& B = W.Bosses[i];
        if (BossDown[i] || B.At.Map != Cur || !Visible(B.At.X, B.At.Y)) continue;
        Frame Big(64, 64);
        const MonsterDef& Mo = Mon(B.Monster);
        Monster(Big, 0, 0, Mo, Anim, false);
        F.BlitSmall(Big, B.At.X * TileSize - CamX, B.At.Y * TileSize - CamY, 4, Pal::Black);
    }
    for (size_t i = Party.size(); i-- > 1;)
    {
        if (i - 1 >= Trail.size() || !Party[i].Alive()) continue;
        const auto& T = Trail[i - 1];
        if (!Visible(T.first, T.second)) continue;
        Person(F, T.first * TileSize - CamX, T.second * TileSize - CamY, "MEMBER:" + Party[i].Name, Party[i].L, Facing, WalkFrame + static_cast<int>(i));
    }
    const int Shake = Bump > 0.0 ? ((Anim % 2) ? 1 : -1) : 0;
    Person(F, ScreenW / 2 - 8 + Shake, ScreenH / 2 - 8, "MEMBER:" + Party[0].Name, Party[0].L, Facing, (Anim / 2) % 2 + WalkFrame);
    if (Flash > 0.0)   // hurt: the screen blinks red at the edges
        for (int k = 0; k < 3; ++k) { F.Rect(0, k, ScreenW, 1, Pal::Red); F.Rect(0, ScreenH - 1 - k, ScreenW, 1, Pal::Red); F.Rect(k, 0, 1, ScreenH, Pal::Red); F.Rect(ScreenW - 1 - k, 0, 1, ScreenH, Pal::Red); }
    if (Boxes.empty() && Idle > 1.0) Ui::PartyStrip(F, Party, -1);
}

inline void Realm::ListBox(Frame& F, int X, int Y, int WW, const Box& B, int Anim, int MaxRows)
{
    const int N = static_cast<int>(B.Rows.size());
    const int Shown = std::min(N, MaxRows);
    const int First = std::max(0, std::min(B.Cursor - Shown + 1, N - Shown));
    std::string Title = B.Kind == BoxKind::Items ? "ITEM" : B.Kind == BoxKind::Spells ? "SPELL" : B.Kind == BoxKind::Equip ? "EQUIP"
        : B.Kind == BoxKind::ShopBuy ? "BUY" : B.Kind == BoxKind::ShopSell ? "SELL" : B.Kind == BoxKind::Members ? "WHO" : "";
    std::vector<bool> Can;
    if (B.Kind == BoxKind::Spells && B.Arg >= 0 && B.Arg < static_cast<int>(Party.size()))
    {
        // A spell the caster can't pay for is dimmed, and the window says how much MP they hold.
        const Member& C = Party[static_cast<size_t>(B.Arg)];
        for (int i = First; i < First + Shown; ++i) Can.push_back(C.Mp >= SpellCost(B.Ids[static_cast<size_t>(i)]));
        Title += " MP" + std::to_string(C.Mp);
    }
    Ui::Window(F, X, Y, WW, Shown * 12 + 20, Title);
    std::vector<std::string> Rows(B.Rows.begin() + First, B.Rows.begin() + First + Shown);
    Ui::Grid(F, X + 4, Y + 9, Rows, 1, 0, B.Cursor - First, &B == &Boxes.back(), Anim, Can.empty() ? nullptr : &Can);
    if (First > 0) Ui::TextB(F, X + WW - 16, Y + 2, "+", Ui::Current().Ink);
    if (First + Shown < N) Ui::TextB(F, X + WW - 16, Y + Shown * 12 + 10, "+", Ui::Current().Ink);
}

/** The realm's name on black, the way a cartridge opens: the name in the realm's ink, a rule under it, a hint that
 * blinks once the fade is done. The first 0.4 s fade the name in so the portal's flash reads as the cut. */
inline void Realm::RenderTitle(Frame& F, int Anim)
{
    F.Clear(Pal::Black);
    const Ui::Style& St = Ui::Current();
    const double Age = TitleHold - TitleT;
    const uint32_t Ink = Age < 0.4 ? Shade(St.Ink, static_cast<int>(Age * 10) + 1, 4) : St.Ink;
    const std::string Name = W.Name.empty() ? "A PORTAL REALM" : W.Name;
    const int NX = 128 - static_cast<int>(Name.size()) * 4;
    Ui::TextB(F, NX, 100, Name, Ink);
    Ui::TextB(F, NX, 100, Name, Ink);   // twice: the bold pass of the kit doubles the stroke on the second draw
    for (int x = NX - 8; x < NX + static_cast<int>(Name.size()) * 8 + 8; ++x) { F.Set(x, 112, Ink); F.Set(x, 113, St.InkDark); }
    Ui::TextB(F, 128 - 7 * 4, 120, "A REALM", St.Dim);
    for (int i = 0; i < 5; ++i) Ui::Sparkle(F, 40 + i * 44, 60 + ((i * 7) % 3) * 6, Anim + i * 5);
    if (Age > 0.8 && (Anim / 6) % 2 == 0) Ui::TextB(F, 128 - 7 * 4, 180, "PRESS A", St.Text);
}

inline void Realm::RenderBoxes(Frame& F, int Anim)
{
    bool Shop = false;
    for (const Box& B : Boxes) Shop |= B.Kind == BoxKind::ShopTop || B.Kind == BoxKind::ShopBuy || B.Kind == BoxKind::ShopSell || B.Kind == BoxKind::YesNo;
    if (Shop)
    {
        Ui::Window(F, 8, 8, 104, 32, "GOLD");
        Ui::TextB(F, 20, 16, std::to_string(GoldHeld));
    }
    for (const Box& B : Boxes)
    {
        switch (B.Kind)
        {
        case BoxKind::Message:
        {
            const bool More = &B == &Boxes.back() && ((B.Page + 1) * 4 < static_cast<int>(B.Rows.size()) || B.OnClose);
            const int Chars = B.Shown >= Ui::PageChars(B.Rows, B.Page) ? 1000000 : static_cast<int>(B.Shown);
            Ui::Dialogue(F, B.Rows, B.Page, Chars, More, Anim);
            break;
        }
        case BoxKind::Command:
            Ui::Window(F, 56, 8, 152, 48, "COMMAND");
            Ui::Grid(F, 60, 18, B.Rows, 2, 9, B.Cursor, &B == &Boxes.back(), Anim);
            break;
        case BoxKind::ShopTop: ListBox(F, 160, 8, 88, B, Anim, 4); break;
        case BoxKind::Members: ListBox(F, 112, 72, 80, B, Anim, 3); break;
        case BoxKind::YesNo: ListBox(F, 184, 124, 64, B, Anim, 2); break;
        case BoxKind::Items: case BoxKind::Equip: case BoxKind::ShopBuy: case BoxKind::ShopSell: ListBox(F, 40, 40, 192, B, Anim, 8); break;
        case BoxKind::Spells: ListBox(F, 72, 56, 112, B, Anim, 4); break;
        case BoxKind::Status:
        {
            Ui::Window(F, 8, 8, 240, 168, "STATUS");
            int Y = 18;
            for (const Member& P : Party)
            {
                char Row[96];
                std::snprintf(Row, sizeof(Row), "%-6s LV%2d %s\n H%3d/%-3d M%3d/%-3d\n A%3d D%3d G%3d E%d", P.Name.c_str(), P.Lvl,
                    P.Poisoned ? "POISON" : P.Alive() ? "" : "FALLEN", P.Hp, P.MaxHp, P.Mp, P.MaxMp, AtkOf(P), DefOf(P), P.Agi, P.Exp);
                Ui::TextB(F, 18, Y, Row, P.Alive() ? Ui::Current().Text : Pal::Red);
                Y += 40;
            }
            char G[64];
            std::snprintf(G, sizeof(G), "GOLD %d   STEPS %d", GoldHeld, StepCount);
            Ui::TextB(F, 18, Y + 2, G, Ui::Current().Hot);
            break;
        }
        }
    }
}

inline void Realm::RenderBattle(Frame& F, int Anim)
{
    F.Clear(Pal::Black);
    {
        const int Hot = (Ph == Phase::Command || Ph == Phase::Target || !Boxes.empty()) ? Actor : -1;
        Ui::PartyStrip(F, Party, Hot, &MemShown);
    }
    // The scene: a framed picture of where the fight is.
    DrawBattleScene(F, Map().Dark ? 2 : Map().Id == "FIELD" ? 0 : 1, Anim);
    const int N = static_cast<int>(Enemies.size());
    int Shown = 0;
    for (int i = 0; i < N; ++i) Shown += (FoeShown[static_cast<size_t>(i)] > 0 && !FoeGoneShown[static_cast<size_t>(i)]);
    int Slot = 0;
    for (int i = 0; i < N; ++i)
    {
        if (FoeShown[static_cast<size_t>(i)] <= 0 || FoeGoneShown[static_cast<size_t>(i)]) continue;
        const int X = 128 - Shown * 29 + Slot * 58 - 3;
        ++Slot;
        const MonsterDef& M = Mon(Enemies[static_cast<size_t>(i)].Kind);
        Monster(F, X, 74, M, Anim + i * 5, FoeFlash[static_cast<size_t>(i)] > 0 && (FoeFlash[static_cast<size_t>(i)] % 2));
        if (Enemies[static_cast<size_t>(i)].Shiny) Ui::Sparkle(F, X + 32, 106, Anim + i * 3);
        if (Ph == Phase::Target && TargetI == i && (Anim / 2) % 2) Ui::Cursor(F, X + 28, 140, Ui::Current().Hot);
        FoeSlotX[static_cast<size_t>(i)] = X;
    }
    for (const Pop& P : Pops)
    {
        const int Rise = static_cast<int>((0.9 - P.Life) * 30.0);
        const std::string T = std::to_string(P.Amount);
        if (P.Foe >= 0 && P.Foe < static_cast<int>(FoeSlotX.size()))
            Ui::TextB(F, FoeSlotX[static_cast<size_t>(P.Foe)] + 32 - static_cast<int>(T.size()) * 4, 96 - Rise, T, P.Life > 0.3 ? Pal::White : Ui::Current().Dim);
        else if (P.Mem >= 0)
        {
            const int PartyN = static_cast<int>(Party.size());
            const int CardX = (ScreenW - (PartyN * 56 + (PartyN - 1) * 4)) / 2 + P.Mem * 60;
            Ui::TextB(F, CardX + 16, 40 - Rise / 3, T, Pal::Red);
        }
    }
    // Commands (left) and the log (right).
    Ui::Window(F, 8, 152, 76, 80, "FIGHT");
    static const char* Cmds[5] = {"FIGHT", "SPELL", "ITEM", "DEFEND", "RUN"};
    {
        std::vector<std::string> Rows(Cmds, Cmds + 5);
        const bool Active = Ph == Phase::Command || Ph == Phase::Target;
        std::vector<bool> On(5, Active);
        Ui::Grid(F, 12, 163, Rows, 1, 0, Ph == Phase::Command && Boxes.empty() ? Menu : -1, true, Anim, &On);
    }
    Ui::Window(F, 84, 152, 164, 80);
    std::vector<std::string> Wrapped;
    for (const std::string& L : Log) for (const std::string& W2 : Wrap(L, 18)) Wrapped.push_back(W2);
    const size_t From = Wrapped.size() > 6 ? Wrapped.size() - 6 : 0;
    for (size_t k = From; k < Wrapped.size(); ++k) Ui::TextB(F, 94, 161 + static_cast<int>(k - From) * 12, Wrapped[k]);
    if ((Ph == Phase::Ending || Ph == Phase::Intro) && Queue.empty() && (Anim / 4) % 2) Ui::PageArrow(F, 162, 224);
}

inline const Frame& Realm::Render()
{
    Frame& F = Screen;
    const int Anim = static_cast<int>(Clock * 8);
    if (!Loaded) { F.Clear(Pal::Black); Text(F, 60, 116, "NO REALM LOADED"); return F; }
    if (TitleT > 0.0) { RenderTitle(F, Anim); return F; }
    if (ModeNow == Mode::Battle) RenderBattle(F, Anim);
    else RenderField(F, Anim);
    RenderBoxes(F, Anim);
    return F;
}

inline std::string Realm::TopBox() const
{
    if (TitleT > 0.0) return "TITLE";
    if (Boxes.empty()) return ModeNow == Mode::Battle ? (Ph == Phase::Command ? "COMMAND" : Ph == Phase::Target ? "TARGET" : Ph == Phase::Play ? "PLAY" : Ph == Phase::Ending ? "ENDING" : "INTRO") : "NONE";
    static const char* Names[] = {"MESSAGE", "MENU", "ITEMS", "MEMBERS", "SPELLS", "STATUS", "EQUIP", "SHOP", "BUY", "SELL", "YESNO"};
    return Names[static_cast<int>(Boxes.back().Kind)];
}

inline std::string Realm::Describe() const
{
    if (!Loaded) return "loaded=0";
    std::ostringstream S;
    S << "mode=" << (ModeNow == Mode::Battle ? "BATTLE" : "FIELD") << " map=" << MapId() << " x=" << PX << " y=" << PY
      << " facing=" << Facing << " tile=" << TileChars()[static_cast<int>(TileHere(PX, PY))] << " ui=" << TopBox()
      << " party=" << Party.size() << " egg=" << EggWarmth << " land=" << (LandHere >= 0 ? W.Lands[static_cast<size_t>(LandHere)].Number : -1) << " deeds=" << DeedsTaken() << "/" << W.Lands.size() << " gold=" << GoldHeld << " steps=" << StepCount << " battles=" << BattleCount << " wins=" << WinCount
      << " chests=" << ChestsOpened() << "/" << W.Chests.size() << " doors=" << DoorsOpened() << "/" << W.Doors.size()
      << " bosses=" << BossesBeaten() << "/" << W.Bosses.size() << " light=" << LightRadius() << " cue=" << Cue
      << " cue_changes=" << CueCount << " exit=" << (ExitRequested ? 1 : 0) << " talks=" << Talks << " party=";
    for (size_t i = 0; i < Party.size(); ++i)
    {
        const Member& P = Party[i];
        S << (i ? "," : "") << P.Name << ":L" << P.Lvl << ":" << P.Hp << "/" << P.MaxHp << ":M" << P.Mp << (P.Poisoned ? ":PSN" : "") << (P.Asleep ? ":SLP" : "");
    }
    S << " bag=";
    for (size_t i = 0; i < Bag.size(); ++i) S << (i ? "," : "") << Item(Bag[i].first).Id << "x" << Bag[i].second;
    if (ModeNow == Mode::Battle)
    {
        S << " foes=";
        for (size_t i = 0; i < Enemies.size(); ++i) S << (i ? "," : "") << Mon(Enemies[i].Kind).Id << ":" << Enemies[i].Hp << (Enemies[i].Fled ? ":FLED" : "");
    }
    std::string M = LastSaid.substr(0, 60);
    std::replace(M.begin(), M.end(), '\n', ' ');
    S << " msg=" << M;
    return S.str();
}

// ----------------------------------------------------------------------------------------------- saving

inline std::string Realm::Save() const
{
    std::ostringstream S;
    S << "DRS 1\nseed " << W.Seed << "\ngold " << GoldHeld << "\nplace " << MapId() << " " << PX << " " << PY << " " << Facing << "\n";
    S << "respawn " << W.Maps[static_cast<size_t>(RespawnMap)].Id << " " << RespawnX << " " << RespawnY << "\n";
    S << "counts " << StepCount << " " << BattleCount << " " << WinCount << "\n";
    S << "egg " << EggWarmth << "\n";
    for (const Member& P : Party) if (P.Class == 3) S << "drake " << (P.Shiny ? 1 : 0) << "\n";
    for (const Member& P : Party)
        S << "member " << P.Lvl << " " << P.Hp << " " << P.MaxHp << " " << P.Mp << " " << P.MaxMp << " " << P.Atk << " " << P.Def
          << " " << P.Agi << " " << P.Exp << " " << (P.Weapon >= 0 ? Item(P.Weapon).Id : "-") << " " << (P.Armor >= 0 ? Item(P.Armor).Id : "-")
          << " " << (P.Poisoned ? 1 : 0) << "\n";
    S << "bag";
    for (const auto& E : Bag) S << " " << Item(E.first).Id << ":" << E.second;
    auto Flags = [&](const char* Name, const std::vector<bool>& V) {
        S << "\n" << Name;
        for (size_t i = 0; i < V.size(); ++i) if (V[i]) S << " " << i;
    };
    Flags("chests", Opened);
    Flags("doors", DoorOpen);
    Flags("bosses", BossDown);
    Flags("deeds", DeedTaken);
    S << "\n";
    return S.str();
}

/** Bring back a saved party. Levels, gear, the bag and gold always come back; where you stood and which chests
 *  and locks are open come back only in the same realm (the same seed). */
inline bool Realm::Restore(const std::string& Text)
{
    if (!Loaded) return false;
    std::istringstream In(Text);
    std::string L;
    if (!std::getline(In, L) || L != "DRS 1") return false;
    bool Same = false;
    size_t Mi = 0;
    std::vector<std::pair<int, int>> NewBag;
    while (std::getline(In, L))
    {
        std::istringstream F(L);
        std::string K;
        F >> K;
        if (K == "seed") { uint64_t Sd = 0; F >> Sd; Same = Sd == W.Seed; }
        else if (K == "gold") F >> GoldHeld;
        else if (K == "egg") F >> EggWarmth;
        else if (K == "drake" && !HasDrake() && Party.size() < static_cast<size_t>(MaxParty))
        {
            int Sh = 0; F >> Sh;
            Member D = MakeMember("DRAKE", {Pal::Lime, 0x2C8C18, 0x603008, 0, Pal::Red}, 3, 26, 8, 9, 5, 7);
            D.Shiny = Sh != 0;
            Party.push_back(D);   // its numbers follow on its member line
        }
        else if (K == "member" && Mi < Party.size())
        {
            Member& P = Party[Mi++];
            std::string Wp, Ar;
            int Psn = 0;
            F >> P.Lvl >> P.Hp >> P.MaxHp >> P.Mp >> P.MaxMp >> P.Atk >> P.Def >> P.Agi >> P.Exp >> Wp >> Ar >> Psn;
            P.Weapon = Wp == "-" ? -1 : W.ItemIndex(Wp);
            P.Armor = Ar == "-" ? -1 : W.ItemIndex(Ar);
            P.Poisoned = Psn != 0;
            P.Hp = std::max(1, std::min(P.Hp, P.MaxHp));
        }
        else if (K == "bag")
        {
            std::string E;
            while (F >> E)
            {
                const size_t C = E.find(':');
                const int I = W.ItemIndex(E.substr(0, C));
                if (I >= 0 && C != std::string::npos && NewBag.size() < BagSlots) NewBag.push_back({I, std::max(1, std::atoi(E.c_str() + C + 1))});
            }
        }
        else if (Same && K == "place")
        {
            std::string M;
            int X = 0, Y = 0, Fc = 0;
            F >> M >> X >> Y >> Fc;
            const int Mx = W.MapIndex(M);
            if (Mx >= 0) { Enter(Mx, X, Y); Facing = Fc; }
        }
        else if (Same && K == "respawn")
        {
            std::string M;
            F >> M >> RespawnX >> RespawnY;
            RespawnMap = std::max(0, W.MapIndex(M));
        }
        else if (Same && K == "counts") F >> StepCount >> BattleCount >> WinCount;
        else if (Same && (K == "chests" || K == "doors" || K == "bosses" || K == "deeds"))
        {
            size_t I;
            while (F >> I)
            {
                if (K == "chests" && I < Opened.size())
                {
                    Opened[I] = true;
                    const ChestDef& C = W.Chests[I];
                    SetTile(C.At.Map, C.At.X, C.At.Y, Tile::ChestOpen);
                }
                if (K == "doors" && I < DoorOpen.size())
                {
                    DoorOpen[I] = true;
                    const DoorDef& D = W.Doors[I];
                    SetTile(D.At.Map, D.At.X, D.At.Y, Tile::Door);
                }
                if (K == "bosses" && I < BossDown.size()) BossDown[I] = true;
                if (K == "deeds" && I < DeedTaken.size()) DeedTaken[I] = true;
            }
        }
    }
    Bag = NewBag;
    Boxes.clear();
    return true;
}

}   // namespace realm
}   // namespace daedalus
