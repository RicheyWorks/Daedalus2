// SPDX-License-Identifier: MIT
//
// DaedalusRealmSpec.h: reads the realm spec the Java engines write (ADR-052; RetroCodec, "DRR 1"): the maps, the
// zones and their monsters, every chest's contents, every lock's tier, the townsfolk, the shops, the guardian.
// The game rules live in DaedalusRealmCore.h; what the realm holds comes from here. Standard C++17.

#pragma once

#include "DaedalusRealmDraw.h"

#include <cstdlib>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus
{
namespace realm
{

enum class ItemKind { Use, Key, Weapon, Armor, Treasure };

struct ItemDef
{
    std::string Id, Name;
    ItemKind Kind = ItemKind::Use;
    int Price = 0, Power = 0;
    int SellValue() const { return Kind == ItemKind::Treasure ? Power : Price / 2; }
};

/** Monster traits, as bits. */
namespace Trait
{
constexpr uint32_t Poison = 1, Sleep = 2, Zap = 4, Heal = 8, Call = 16, Flee = 32, Hard = 64, Double = 128, Boss = 256;
}

struct MonsterDef
{
    std::string Id, Name, Rarity;
    int Shape = 0;
    uint32_t Body = 0, Accent = 0;
    int Hp = 1, Atk = 1, Def = 0, Agi = 1, Exp = 0, Gold = 0;
    uint32_t Traits = 0;
    int Drop = -1, DropOneIn = 1;
    bool Has(uint32_t T) const { return (Traits & T) != 0; }
};

struct MapDef
{
    std::string Id, Title, Music;
    int W = 0, H = 0;
    bool Dark = false;
    int ExitMap = -1, ExitX = 0, ExitY = 0;
    std::vector<Tile> T;
    std::string Zones;   // one character per tile, '.' for none
    Tile Outside() const { return Dark ? Tile::Wall : ExitMap < 0 ? Tile::Water : Tile::Grass; }
    bool Inside(int X, int Y) const { return X >= 0 && Y >= 0 && X < W && Y < H; }
    Tile At(int X, int Y) const { return Inside(X, Y) ? T[static_cast<size_t>(Y * W + X)] : Outside(); }
    void Put(int X, int Y, Tile V) { if (Inside(X, Y)) T[static_cast<size_t>(Y * W + X)] = V; }
    char ZoneAt(int X, int Y) const { return Inside(X, Y) && !Zones.empty() ? Zones[static_cast<size_t>(Y * W + X)] : '.'; }
};

struct ZoneEntry { int Monster = 0, Weight = 1, Min = 1, Max = 1; };
struct ZoneDef { char Id = '0'; int Rate = 20; std::vector<ZoneEntry> Entries; };
struct Spot { int Map = 0, X = 0, Y = 0; bool operator==(const Spot& O) const { return Map == O.Map && X == O.X && Y == O.Y; } };
struct LinkDef { Spot From, To; };
enum class LootKind { Gold, Item, Mimic };
struct ChestDef { Spot At; LootKind Kind = LootKind::Gold; int Gold = 0, Item = -1, Mimic = -1; };
struct DoorDef { Spot At; int Tier = 1; };
enum class Role { Talk, News, Inn, Shop, Queen };
struct NpcDef
{
    Spot At;
    bool Wanders = false;
    Look L;
    Role R = Role::Talk;
    int Price = 0, Shop = -1;
    std::vector<std::string> Lines;
};
struct ShopDef { std::string Id; std::vector<int> Stock; };
struct BossDef { Spot At; int Monster = 0; };

/** A whole realm, read from the spec. */
struct Spec
{
    uint64_t Seed = 0;
    std::string Name;
    /** The window rule colour, 0xRRGGBB (optional "ui" line; 0 = the kit's default). Each realm wears its own. */
    uint32_t UiInk = 0;
    std::vector<ItemDef> Items;
    std::vector<MonsterDef> Monsters;
    std::vector<MapDef> Maps;
    std::vector<ZoneDef> Zones;
    std::vector<LinkDef> Links;
    std::vector<ChestDef> Chests;
    std::vector<DoorDef> Doors;
    std::vector<NpcDef> Npcs;
    std::vector<ShopDef> Shops;
    std::vector<BossDef> Bosses;
    std::vector<std::string> News;
    Spot Spawn, Portal;

    int ItemIndex(const std::string& Id) const { for (size_t i = 0; i < Items.size(); ++i) if (Items[i].Id == Id) return static_cast<int>(i); return -1; }
    int MonsterIndex(const std::string& Id) const { for (size_t i = 0; i < Monsters.size(); ++i) if (Monsters[i].Id == Id) return static_cast<int>(i); return -1; }
    int MapIndex(const std::string& Id) const { for (size_t i = 0; i < Maps.size(); ++i) if (Maps[i].Id == Id) return static_cast<int>(i); return -1; }
    int ShopIndex(const std::string& Id) const { for (size_t i = 0; i < Shops.size(); ++i) if (Shops[i].Id == Id) return static_cast<int>(i); return -1; }
    const ZoneDef* Zone(char Id) const { for (const ZoneDef& Z : Zones) if (Z.Id == Id) return &Z; return nullptr; }

    /** Parse the spec. Returns false with a reason on anything it can't trust. */
    bool Parse(const std::string& Text, std::string& Error)
    {
        *this = Spec();
        std::vector<std::string> Lines;
        {
            std::string L;
            std::istringstream In(Text);
            while (std::getline(In, L))
            {
                if (!L.empty() && L.back() == '\r') L.pop_back();
                Lines.push_back(L);
            }
        }
        if (Lines.empty() || Lines[0] != "DRR 1") { Error = "not a realm spec (want 'DRR 1' first)"; return false; }
        // Maps are named before they are referenced by links, chests and so on, but a map's exit names the field,
        // which comes first; ids are resolved after everything is read.
        std::vector<std::pair<std::string, int>> ExitRefs;   // map index -> exit map id
        std::vector<std::pair<std::string, std::string>> ZoneRaw;
        std::vector<std::pair<int, std::string>> NpcShops;   // npc index -> shop id
        std::vector<std::vector<std::string>> ShopRaw;
        std::vector<std::pair<int, std::string>> ChestRefs;   // chest index -> item/monster id
        std::vector<std::pair<int, std::string>> BossRefs;
        std::vector<std::pair<int, std::string>> DropRefs;
        auto Split = [](const std::string& S) {
            std::vector<std::string> F;
            std::string W;
            std::istringstream In(S);
            while (In >> W) F.push_back(W);
            return F;
        };
        auto Rest = [](const std::string& S, int Fields) {
            size_t At = 0;
            for (int k = 0; k < Fields; ++k)
            {
                At = S.find(' ', At);
                if (At == std::string::npos) return std::string();
                ++At;
            }
            return S.substr(At);
        };
        auto Num = [](const std::string& S) { return std::atoi(S.c_str()); };
        auto Hex = [](const std::string& S) { return static_cast<uint32_t>(std::strtoul(S.c_str(), nullptr, 16)); };
        // Places name their map; the names are resolved to indices once every map is read.
        std::vector<std::string> LinkFrom, LinkTo, ChestMap, DoorMap, NpcMap, BossMap;
        std::string SpawnMap, PortalMap;

        for (size_t i = 1; i < Lines.size(); ++i)
        {
            const std::string& L = Lines[i];
            if (L.empty()) continue;
            const std::vector<std::string> F = Split(L);
            const std::string& K = F[0];
            auto Need = [&](size_t N) {
                if (F.size() < N) { Error = "line " + std::to_string(i + 1) + ": too few fields in '" + K + "'"; return false; }
                return true;
            };
            if (K == "seed") { if (!Need(2)) return false; Seed = std::strtoull(F[1].c_str(), nullptr, 10); }
            else if (K == "name") Name = Rest(L, 1);
            else if (K == "ui") { if (!Need(2)) return false; UiInk = static_cast<uint32_t>(std::strtoul(F[1].c_str(), nullptr, 16)) & 0xFFFFFFu; }
            else if (K == "item")
            {
                if (!Need(6)) return false;
                ItemDef D;
                D.Id = F[1];
                D.Kind = F[2] == "KEY" ? ItemKind::Key : F[2] == "WEAPON" ? ItemKind::Weapon : F[2] == "ARMOR" ? ItemKind::Armor
                    : F[2] == "TREASURE" ? ItemKind::Treasure : ItemKind::Use;
                D.Price = Num(F[3]); D.Power = Num(F[4]); D.Name = Rest(L, 5);
                Items.push_back(D);
            }
            else if (K == "monster")
            {
                if (!Need(16)) return false;
                MonsterDef M;
                M.Id = F[1]; M.Shape = Num(F[2]); M.Body = Hex(F[3]); M.Accent = Hex(F[4]);
                M.Hp = Num(F[5]); M.Atk = Num(F[6]); M.Def = Num(F[7]); M.Agi = Num(F[8]); M.Exp = Num(F[9]); M.Gold = Num(F[10]);
                M.Rarity = F[11];
                std::string T = F[12] + ",";
                size_t P = 0;
                while ((P = T.find(',')) != std::string::npos)
                {
                    const std::string One = T.substr(0, P);
                    T.erase(0, P + 1);
                    if (One == "POISON") M.Traits |= Trait::Poison;
                    else if (One == "SLEEP") M.Traits |= Trait::Sleep;
                    else if (One == "ZAP") M.Traits |= Trait::Zap;
                    else if (One == "HEAL") M.Traits |= Trait::Heal;
                    else if (One == "CALL") M.Traits |= Trait::Call;
                    else if (One == "FLEE") M.Traits |= Trait::Flee;
                    else if (One == "HARD") M.Traits |= Trait::Hard;
                    else if (One == "DOUBLE") M.Traits |= Trait::Double;
                    else if (One == "BOSS") M.Traits |= Trait::Boss;
                }
                DropRefs.push_back({static_cast<int>(Monsters.size()), F[13]});
                M.DropOneIn = std::max(1, Num(F[14]));
                M.Name = Rest(L, 15);
                Monsters.push_back(M);
            }
            else if (K == "map")
            {
                if (!Need(10)) return false;
                MapDef M;
                M.Id = F[1]; M.W = Num(F[2]); M.H = Num(F[3]); M.Music = F[4]; M.Dark = F[5] == "1";
                if (M.W <= 0 || M.H <= 0 || M.W > 512 || M.H > 512) { Error = "map " + M.Id + " has a bad size"; return false; }
                if (F[6] != "-") { ExitRefs.push_back({F[6], static_cast<int>(Maps.size())}); M.ExitX = Num(F[7]); M.ExitY = Num(F[8]); }
                M.Title = Rest(L, 9);
                M.T.assign(static_cast<size_t>(M.W * M.H), Tile::Water);
                int Y = 0, ZY = 0;
                for (++i; i < Lines.size() && Lines[i] != "end"; ++i)
                {
                    const std::string& R = Lines[i];
                    if (R.rfind("row ", 0) == 0)
                    {
                        if (static_cast<int>(R.size()) - 4 != M.W || Y >= M.H) { Error = "map " + M.Id + " row " + std::to_string(Y) + " is the wrong size"; return false; }
                        for (int X = 0; X < M.W; ++X)
                        {
                            Tile T;
                            if (!TileFromChar(R[static_cast<size_t>(4 + X)], T)) { Error = std::string("map ") + M.Id + ": unknown tile '" + R[static_cast<size_t>(4 + X)] + "'"; return false; }
                            M.Put(X, Y, T);
                        }
                        ++Y;
                    }
                    else if (R.rfind("zrow ", 0) == 0)
                    {
                        if (M.Zones.empty()) M.Zones.assign(static_cast<size_t>(M.W * M.H), '.');
                        for (int X = 0; X < M.W && X + 5 < static_cast<int>(R.size()); ++X)
                            if (ZY < M.H) M.Zones[static_cast<size_t>(ZY * M.W + X)] = R[static_cast<size_t>(5 + X)];
                        ++ZY;
                    }
                    else { Error = "map " + M.Id + ": unexpected '" + R + "'"; return false; }
                }
                if (Y != M.H) { Error = "map " + M.Id + " has " + std::to_string(Y) + " rows, wants " + std::to_string(M.H); return false; }
                Maps.push_back(M);
            }
            else if (K == "zone")
            {
                if (!Need(4)) return false;
                ZoneDef Z;
                Z.Id = F[1][0]; Z.Rate = std::max(2, Num(F[2]));
                Zones.push_back(Z);
                for (size_t k = 3; k < F.size(); ++k) ZoneRaw.push_back({std::string(1, Z.Id), F[k]});
            }
            else if (K == "link")
            {
                if (!Need(7)) return false;
                LinkDef D;
                D.From.X = Num(F[2]); D.From.Y = Num(F[3]); D.To.X = Num(F[5]); D.To.Y = Num(F[6]);
                LinkFrom.push_back(F[1]); LinkTo.push_back(F[4]);
                Links.push_back(D);
            }
            else if (K == "chest")
            {
                if (!Need(6)) return false;
                ChestDef C;
                C.At.X = Num(F[2]); C.At.Y = Num(F[3]);
                ChestMap.push_back(F[1]);
                if (F[4] == "GOLD") { C.Kind = LootKind::Gold; C.Gold = Num(F[5]); }
                else { C.Kind = F[4] == "MIMIC" ? LootKind::Mimic : LootKind::Item; ChestRefs.push_back({static_cast<int>(Chests.size()), F[5]}); }
                Chests.push_back(C);
            }
            else if (K == "door")
            {
                if (!Need(5)) return false;
                DoorDef D;
                D.At.X = Num(F[2]); D.At.Y = Num(F[3]); D.Tier = Num(F[4]);
                DoorMap.push_back(F[1]);
                Doors.push_back(D);
            }
            else if (K == "npc")
            {
                if (!Need(14)) return false;
                NpcDef N;
                N.At.X = Num(F[2]); N.At.Y = Num(F[3]); N.Wanders = F[4] == "1";
                N.L = {Hex(F[5]), Hex(F[6]), Hex(F[7]), Hex(F[8]), Hex(F[9])};
                N.R = F[10] == "NEWS" ? Role::News : F[10] == "INN" ? Role::Inn : F[10] == "SHOP" ? Role::Shop : F[10] == "QUEEN" ? Role::Queen : Role::Talk;
                N.Price = Num(F[11]);
                if (F[12] != "-") NpcShops.push_back({static_cast<int>(Npcs.size()), F[12]});
                std::string T = Rest(L, 13) + "/";
                size_t P;
                while ((P = T.find('/')) != std::string::npos) { N.Lines.push_back(T.substr(0, P)); T.erase(0, P + 1); }
                NpcMap.push_back(F[1]);
                Npcs.push_back(N);
            }
            else if (K == "shop") ShopRaw.push_back(F);
            else if (K == "boss")
            {
                if (!Need(5)) return false;
                BossDef B;
                B.At.X = Num(F[2]); B.At.Y = Num(F[3]);
                BossMap.push_back(F[1]);
                BossRefs.push_back({static_cast<int>(Bosses.size()), F[4]});
                Bosses.push_back(B);
            }
            else if (K == "spawn") { if (!Need(4)) return false; SpawnMap = F[1]; Spawn.X = Num(F[2]); Spawn.Y = Num(F[3]); }
            else if (K == "portal") { if (!Need(4)) return false; PortalMap = F[1]; Portal.X = Num(F[2]); Portal.Y = Num(F[3]); }
            else if (K == "news") News.push_back(Rest(L, 1));
            else { Error = "line " + std::to_string(i + 1) + ": unknown '" + K + "'"; return false; }
        }

        // Resolve every name to an index; a name that isn't there is an error, not a silent zero.
        auto MapOf = [&](const std::string& Id, int& Out) {
            Out = MapIndex(Id);
            if (Out < 0) Error = "no map " + Id;
            return Out >= 0;
        };
        for (const auto& E : ExitRefs) if (!MapOf(E.first, Maps[static_cast<size_t>(E.second)].ExitMap)) return false;
        for (size_t k = 0; k < Links.size(); ++k) if (!MapOf(LinkFrom[k], Links[k].From.Map) || !MapOf(LinkTo[k], Links[k].To.Map)) return false;
        for (size_t k = 0; k < Chests.size(); ++k) if (!MapOf(ChestMap[k], Chests[k].At.Map)) return false;
        for (size_t k = 0; k < Doors.size(); ++k) if (!MapOf(DoorMap[k], Doors[k].At.Map)) return false;
        for (size_t k = 0; k < Npcs.size(); ++k) if (!MapOf(NpcMap[k], Npcs[k].At.Map)) return false;
        for (size_t k = 0; k < Bosses.size(); ++k) if (!MapOf(BossMap[k], Bosses[k].At.Map)) return false;
        if (!MapOf(SpawnMap, Spawn.Map) || !MapOf(PortalMap, Portal.Map)) return false;
        for (const auto& D : DropRefs) Monsters[static_cast<size_t>(D.first)].Drop = D.second == "-" ? -1 : ItemIndex(D.second);
        for (const auto& Z : ZoneRaw)
        {
            ZoneDef* Zd = nullptr;
            for (ZoneDef& Q : Zones) if (Q.Id == Z.first[0]) Zd = &Q;
            const std::string& E = Z.second;
            const size_t A = E.find(':'), B = E.find(':', A + 1), C = E.find(':', B + 1);
            if (!Zd || A == std::string::npos || B == std::string::npos || C == std::string::npos) { Error = "bad zone entry " + E; return false; }
            ZoneEntry En;
            En.Monster = MonsterIndex(E.substr(0, A));
            En.Weight = std::max(1, Num(E.substr(A + 1, B - A - 1)));
            En.Min = std::max(1, Num(E.substr(B + 1, C - B - 1)));
            En.Max = std::max(En.Min, std::min(3, Num(E.substr(C + 1))));
            if (En.Monster < 0) { Error = "zone names an unknown monster: " + E; return false; }
            Zd->Entries.push_back(En);
        }
        for (const auto& S : ShopRaw)
        {
            ShopDef D;
            D.Id = S.size() > 1 ? S[1] : "";
            for (size_t k = 2; k < S.size(); ++k)
            {
                const int It = ItemIndex(S[k]);
                if (It < 0) { Error = "shop " + D.Id + " sells an unknown item " + S[k]; return false; }
                D.Stock.push_back(It);
            }
            Shops.push_back(D);
        }
        for (const auto& N : NpcShops)
        {
            Npcs[static_cast<size_t>(N.first)].Shop = ShopIndex(N.second);
            if (Npcs[static_cast<size_t>(N.first)].Shop < 0) { Error = "no shop " + N.second; return false; }
        }
        for (const auto& C : ChestRefs)
        {
            ChestDef& Ch = Chests[static_cast<size_t>(C.first)];
            if (Ch.Kind == LootKind::Mimic) Ch.Mimic = MonsterIndex(C.second);
            else Ch.Item = ItemIndex(C.second);
            if (Ch.Mimic < 0 && Ch.Item < 0) { Error = "chest holds an unknown " + C.second; return false; }
        }
        for (const auto& B : BossRefs)
        {
            Bosses[static_cast<size_t>(B.first)].Monster = MonsterIndex(B.second);
            if (Bosses[static_cast<size_t>(B.first)].Monster < 0) { Error = "unknown guardian " + B.second; return false; }
        }
        if (Maps.empty() || Items.empty() || Monsters.empty()) { Error = "a realm needs maps, items and monsters"; return false; }
        return true;
    }
};

}   // namespace realm
}   // namespace daedalus
