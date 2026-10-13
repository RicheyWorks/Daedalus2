// SPDX-License-Identifier: MIT
//
// The 8-bit realm (ADR-052) played from a command line: DaedalusRealmCore.h loads the realm the Java engines wrote
// (Content/Realm/realm-7.drr) and the test walks it the way a player would, through towns, shops, the inn, locks,
// chests, the castle, three dark cave floors and the guardian, fights by pressing buttons, saves and restores,
// and writes PNGs of what it saw.
//
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public realm_core_test.cpp -o realm_core_test
//   ./realm_core_test [spec] [png-dir]       prints n/m last; exits 1 on a failure

#include "DaedalusRealmCore.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <queue>

using namespace daedalus::realm;

static int Passed = 0, Total = 0;
static void Check(const std::string& Label, bool Ok, const std::string& Detail = "")
{
    ++Total;
    Passed += Ok;
    std::printf("%s %s%s\n", Ok ? "PASS" : "FAIL", Label.c_str(), Ok || Detail.empty() ? "" : ("  " + Detail).c_str());
}

// ---- a tiny PNG writer (stored deflate blocks), so the test needs nothing but the standard library

static uint32_t Crc(const unsigned char* B, size_t N, uint32_t C = 0xFFFFFFFFu)
{
    for (size_t i = 0; i < N; ++i)
    {
        C ^= B[i];
        for (int k = 0; k < 8; ++k) C = (C >> 1) ^ (0xEDB88320u & (0u - (C & 1u)));
    }
    return C;
}

static void Png(const Frame& F, const std::string& Path, int Scale = 2)
{
    const int W = F.W * Scale, H = F.H * Scale;
    std::vector<unsigned char> Raw;
    for (int y = 0; y < H; ++y)
    {
        Raw.push_back(0);
        for (int x = 0; x < W; ++x)
        {
            const uint32_t C = F.Get(x / Scale, y / Scale);
            Raw.push_back(static_cast<unsigned char>(C >> 16)); Raw.push_back(static_cast<unsigned char>(C >> 8)); Raw.push_back(static_cast<unsigned char>(C));
        }
    }
    std::vector<unsigned char> Z = {0x78, 0x01};
    uint32_t A = 1, B2 = 0;
    for (unsigned char c : Raw) { A = (A + c) % 65521; B2 = (B2 + A) % 65521; }
    for (size_t i = 0; i < Raw.size(); i += 65535)
    {
        const size_t N = std::min<size_t>(65535, Raw.size() - i);
        Z.push_back(i + N >= Raw.size() ? 1 : 0);
        Z.push_back(static_cast<unsigned char>(N)); Z.push_back(static_cast<unsigned char>(N >> 8));
        Z.push_back(static_cast<unsigned char>(~N)); Z.push_back(static_cast<unsigned char>(~N >> 8));
        Z.insert(Z.end(), Raw.begin() + static_cast<long>(i), Raw.begin() + static_cast<long>(i + N));
    }
    const uint32_t Ad = (B2 << 16) | A;
    for (int s = 24; s >= 0; s -= 8) Z.push_back(static_cast<unsigned char>(Ad >> s));
    std::ofstream O(Path, std::ios::binary);
    auto Be = [&](uint32_t V) { for (int s = 24; s >= 0; s -= 8) O.put(static_cast<char>(V >> s)); };
    auto Chunk = [&](const char* T, const std::vector<unsigned char>& D) {
        Be(static_cast<uint32_t>(D.size()));
        std::vector<unsigned char> All(T, T + 4);
        All.insert(All.end(), D.begin(), D.end());
        O.write(reinterpret_cast<const char*>(All.data()), static_cast<long>(All.size()));
        Be(Crc(All.data(), All.size()) ^ 0xFFFFFFFFu);
    };
    O.write("\x89PNG\r\n\x1a\n", 8);
    std::vector<unsigned char> Hd = {static_cast<unsigned char>(W >> 24), static_cast<unsigned char>(W >> 16), static_cast<unsigned char>(W >> 8), static_cast<unsigned char>(W),
                                     static_cast<unsigned char>(H >> 24), static_cast<unsigned char>(H >> 16), static_cast<unsigned char>(H >> 8), static_cast<unsigned char>(H), 8, 2, 0, 0, 0};
    Chunk("IHDR", Hd);
    Chunk("IDAT", Z);
    Chunk("IEND", {});
}

// ---- playing like a person

static void Tap(Realm& G, Button B) { G.Press(B); G.Release(B); G.Tick(0.05); }
static void Settle(Realm& G) { for (int i = 0; i < 6; ++i) G.Tick(0.05); }

/** Fight until the battle ends: FIGHT the first foe every turn. Returns true on a win. */
static bool AutoFight(Realm& G, int Guard = 4000)
{
    const int WinsBefore = G.Wins();
    for (int i = 0; i < Guard && G.CurrentMode() == Mode::Battle; ++i)
    {
        const std::string Ui = G.TopBox();
        if (Ui == "COMMAND" || Ui == "TARGET" || Ui == "INTRO" || Ui == "ENDING") Tap(G, Button::A);
        else if (Ui == "MESSAGE" || Ui == "SPELLS" || Ui == "ITEMS" || Ui == "MEMBERS") Tap(G, Button::B);
        else G.Tick(0.5);
    }
    return G.Wins() > WinsBefore;
}

/** Close whatever message is up. */
static void Dismiss(Realm& G)
{
    for (int i = 0; i < 20 && G.TopBox() == "MESSAGE"; ++i) Tap(G, Button::A);
}

/** Make the party strong enough to walk anywhere. */
static void Toughen(Realm& G, int Lvl = 30)
{
    for (Member& P : G.MembersMut())
    {
        P.Lvl = Lvl; P.MaxHp = P.Hp = 400; P.MaxMp = P.Mp = 200; P.Atk = 160; P.Def = 120; P.Agi = 80; P.Exp = ExpToNext(Lvl - 1);
    }
}

/** Walk to (X, Y) on the current map by breadth-first search, fighting through ambushes. */
static bool WalkTo(Realm& G, int TX, int TY, int MaxSteps = 600)
{
    for (int Tries = 0; Tries < MaxSteps; ++Tries)
    {
        if (G.CurrentMode() == Mode::Battle) { AutoFight(G); continue; }
        if (G.TopBox() == "MESSAGE") { Dismiss(G); continue; }
        if (G.X() == TX && G.Y() == TY) return true;
        const MapDef& M = G.World().Maps[static_cast<size_t>(G.MapIndex())];
        if (!M.Inside(TX, TY)) return false;
        std::vector<int> Prev(static_cast<size_t>(M.W * M.H), -2);
        std::queue<int> Q;
        Q.push(G.Y() * M.W + G.X());
        Prev[static_cast<size_t>(G.Y() * M.W + G.X())] = -1;
        const int DX[4] = {1, -1, 0, 0}, DY[4] = {0, 0, 1, -1};
        while (!Q.empty())
        {
            const int C = Q.front(); Q.pop();
            if (C == TY * M.W + TX) break;
            for (int k = 0; k < 4; ++k)
            {
                const int NX = C % M.W + DX[k], NY = C / M.W + DY[k];
                if (!M.Inside(NX, NY) || Prev[static_cast<size_t>(NY * M.W + NX)] != -2) continue;
                const Tile T = M.At(NX, NY);
                const bool Target = NX == TX && NY == TY;
                // Plan through the original map, but treat link tiles as walls unless they are the goal.
                bool Link = false;
                for (const LinkDef& L : G.World().Links) Link |= L.From.Map == G.MapIndex() && L.From.X == NX && L.From.Y == NY;
                if ((!Walkable(T) && T != Tile::Locked) || (Link && !Target) || T == Tile::Portal) continue;
                Prev[static_cast<size_t>(NY * M.W + NX)] = C;
                Q.push(NY * M.W + NX);
            }
        }
        if (Prev[static_cast<size_t>(TY * M.W + TX)] == -2) return false;
        int C = TY * M.W + TX;
        while (Prev[static_cast<size_t>(C)] != G.Y() * M.W + G.X()) C = Prev[static_cast<size_t>(C)];
        const int NX = C % M.W, NY = C / M.W;
        const Button B = NX > G.X() ? Button::Right : NX < G.X() ? Button::Left : NY > G.Y() ? Button::Down : Button::Up;
        G.Press(B); G.Release(B);
        Settle(G);
    }
    return G.X() == TX && G.Y() == TY;
}

/** Stand on a walkable tile beside (X, Y), facing it. */
static bool StandBeside(Realm& G, int X, int Y)
{
    const int DX[4] = {0, 0, 1, -1}, DY[4] = {-1, 1, 0, 0}, FaceTo[4] = {0, 1, 2, 3};
    const MapDef& M = G.World().Maps[static_cast<size_t>(G.MapIndex())];
    for (int k = 0; k < 4; ++k)
    {
        const int NX = X + DX[k], NY = Y + DY[k];
        if (!M.Inside(NX, NY) || !Walkable(M.At(NX, NY))) continue;
        if (WalkTo(G, NX, NY))
        {
            G.Place(G.MapId(), NX, NY, FaceTo[k]);
            return true;
        }
    }
    return false;
}

static void Face(Realm& G, int Dir)
{
    // Bump into the facing direction without moving: turn by stepping toward a wall is unreliable; use Place.
    G.Place(G.MapId(), G.X(), G.Y(), Dir);
}

static std::string ReadFile(const std::string& P)
{
    std::ifstream In(P, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(In)), std::istreambuf_iterator<char>());
}

static const LinkDef* LinkInto(const Spec& S, const std::string& Map)
{
    const int M = S.MapIndex(Map);
    for (const LinkDef& L : S.Links) if (L.To.Map == M && S.Maps[static_cast<size_t>(L.From.Map)].Id != Map) return &L;
    return nullptr;
}

int main(int Argc, char** Argv)
{
    const std::string SpecPath = Argc > 1 ? Argv[1] : "../DaedalusLink/Content/Realm/realm-7.drr";
    const std::string Out = Argc > 2 ? Argv[2] : ".";
    const std::string Text = ReadFile(SpecPath);
    Realm G;
    std::string Err;
    Check("the Java engines' spec loads", G.Load(Text, Err), Err);
    if (!G.IsLoaded()) { std::printf("%d/%d\n", Passed, Total); return 1; }
    const Spec& S = G.World();
    Check("the realm has its maps", S.Maps.size() == 7 && S.MapIndex("CAVE3") >= 0, std::to_string(S.Maps.size()));
    Check("it starts in the field by the portal", G.MapId() == "FIELD" && G.X() == S.Spawn.X && G.Y() == S.Spawn.Y
        && S.Maps[0].At(S.Portal.X, S.Portal.Y) == Tile::Portal);
    Check("a welcome message waits", G.TopBox() == "MESSAGE");
    {   // the typewriter: nothing yet, some after a quarter second, the whole page after a press of A
        const Frame F0 = G.Render();
        G.Tick(0.25);
        const Frame F1 = G.Render();
        Png(F1, Out + "/realm_11_typing.png");
        int Lit0 = 0, Lit1 = 0;
        for (int y = 168; y < 184; ++y) for (int x = 20; x < 240; ++x) { Lit0 += F0.Get(x, y) == 0xFCFCFC; Lit1 += F1.Get(x, y) == 0xFCFCFC; }
        Check("the dialogue types itself out", Lit0 == 0 && Lit1 > 0, std::to_string(Lit0) + " " + std::to_string(Lit1));
        Check("the window wears the realm's rule", F1.Get(8 + 2, 160) == Ui::Current().Ink && F1.Get(8 + 4, 160 + 3) == Ui::Current().InkDark);
    }
    Png(G.Render(), Out + "/realm_01_arrival.png");
    Dismiss(G);
    Check("the starting kit: a club, clothes, two herbs, 60 gold", G.Count("HERB") == 2 && G.Gold() == 60
        && G.Members()[0].Weapon == S.ItemIndex("CLUB") && G.Members()[2].Armor == S.ItemIndex("CLOTHES"));

    // ---- spec errors are caught, not guessed at
    {
        Spec Bad;
        std::string E;
        Check("a spec without its magic is refused", !Bad.Parse("hello\n", E) && !E.empty());
        std::string Broken = Text;
        Broken.replace(Broken.find("row ~"), 5, "row ");
        {
            Realm Tint;
            std::string E2;
            Check("a 'ui' line recolours the windows", Tint.Load("DRR 1\nseed 1\nui 60A0F8\n" + Text.substr(Text.find("item")), E2)
                && Ui::Current().Ink == 0x60A0F8u, E2);
            Realm Plain;
            Plain.Load(Text, E2);
            Check("and a realm without one gets the default rule", Ui::Current().Ink == 0xF8A070u);
        }
        {   // Sol's art plugs in: a 2-frame sprite for the first monster replaces its drawn shape in battle
            Realm Art;
            std::string E3;
            Art.Load(Text, E3);
            Dismiss(Art);
            Toughen(Art);
            const std::string Mid = Art.World().Monsters[0].Id;
            std::string Pack = "DSP 1\npalette 1 FF00FF\nsprite " + Mid + " 8 8 2\n";
            for (int k = 0; k < 16; ++k) Pack += "00000000\n";
            Check("a sprite pack loads into the realm", Art.LoadSprites(Pack, E3) && Art.SpriteCount() == 1, E3);
            Art.ForceBattle({Mid});
            Settle(Art);
            const Frame B = Art.Render();
            int Magenta = 0;
            for (int y = 0; y < ScreenH; ++y) for (int x = 0; x < ScreenW; ++x) Magenta += B.Get(x, y) == 0xFF00FFu;
            Check("the sprite is what the battle draws", Magenta >= 60, std::to_string(Magenta));
        }
        Check("a short map row is refused", !Bad.Parse(Broken, E) && E.find("wrong size") != std::string::npos, E);
        std::string NoShop = Text;
        NoShop.replace(NoShop.find("shop KEYS"), 9, "shop XEYS");
        Check("a keeper with no shop is refused", !Bad.Parse(NoShop, E) && E.find("KEYS") != std::string::npos, E);
    }

    // ---- the menu, the bag, status
    Tap(G, Button::B);
    Check("B opens the command menu", G.TopBox() == "MENU");
    Png(G.Render(), Out + "/realm_12_command.png");
    Tap(G, Button::A);   // TALK, facing nobody
    Check("TALK with no one there says so", G.LastMessage() == "THERE IS NO ONE THERE.", G.LastMessage());
    Dismiss(G);
    Tap(G, Button::B); Tap(G, Button::Down); Tap(G, Button::Down); Tap(G, Button::A);   // SEARCH
    Check("SEARCH on open ground finds nothing", G.LastMessage().find("NOTHING") != std::string::npos, G.LastMessage());
    Dismiss(G);
    Tap(G, Button::B);
    // The menu is a 2-column grid: TALK SPELL / STATUS ITEM / SEARCH EQUIP. Down moves a row, Right a column.
    Tap(G, Button::Down); Tap(G, Button::A);
    Check("STATUS shows the party", G.TopBox() == "STATUS");
    Png(G.Render(), Out + "/realm_02_status.png");
    Tap(G, Button::A); Tap(G, Button::B);
    Check("menus close", G.TopBox() == "NONE");
    G.MembersMut()[1].Hp = 5;
    Tap(G, Button::B); Tap(G, Button::Down); Tap(G, Button::Right); Tap(G, Button::A);   // ITEM
    Check("ITEM lists the bag", G.TopBox() == "ITEMS");
    Tap(G, Button::A);                       // HERB
    Check("a herb asks who", G.TopBox() == "MEMBERS");
    Tap(G, Button::Down); Tap(G, Button::A); // SAGE
    Check("the herb heals the sage and is used up", G.Members()[1].Hp > 5 && G.Count("HERB") == 1, G.Describe());
    Dismiss(G);

    // ---- poison bites each step but never kills
    G.MembersMut()[0].Poisoned = true;
    G.MembersMut()[0].Hp = 3;
    G.SetEncounterCountdown(100000);
    const int Before = G.Steps();
    for (int k = 0; k < 6; ++k) { Tap(G, k % 2 ? Button::Left : Button::Right); Settle(G); }
    Check("poison: hp falls to 1 and stops", G.Members()[0].Hp == 1 && G.Steps() > Before, G.Describe());
    G.MembersMut()[0].Poisoned = false;
    G.MembersMut()[0].Hp = G.Members()[0].MaxHp;

    // ---- the first town: inn, shop, news, the storeroom lock
    const LinkDef* T1 = LinkInto(S, "TOWN1");
    Toughen(G);
    WalkTo(G, T1->From.X, T1->From.Y);
    Check("walk to the first town", G.MapId() == "TOWN1", G.Describe());
    Check("the town plays its own music", G.MusicCue() == "TOWN");
    Dismiss(G);
    Png(G.Render(), Out + "/realm_03_town.png");
    // The innkeeper stands behind the counter at (5,3); talk across it from (5,5).
    Check("walk to the inn counter", WalkTo(G, 5, 5));
    Face(G, 1);
    G.MembersMut()[0].Hp = 10;
    const int GoldBeforeInn = G.Gold();
    Tap(G, Button::A);
    Check("the innkeeper names a price", G.TopBox() == "MESSAGE" && G.LastMessage().find("GOLD") != std::string::npos, G.LastMessage());
    Dismiss(G);
    Check("and asks yes or no", G.TopBox() == "YESNO");
    Tap(G, Button::A);
    Check("a night's rest heals and costs", G.Members()[0].Hp == G.Members()[0].MaxHp && G.Gold() < GoldBeforeInn && G.MusicCue() == "INN", G.Describe());
    Dismiss(G);
    Check("the town's music comes back", G.MusicCue() == "TOWN");
    // The item shop: keeper at (18,3).
    Check("walk to the item shop", WalkTo(G, 18, 5));
    Face(G, 1);
    G.SetGold(100);
    Tap(G, Button::A); Dismiss(G);
    Check("the merchant opens the shop", G.TopBox() == "SHOP");
    Tap(G, Button::A);   // BUY
    Check("BUY lists the stock", G.TopBox() == "BUY");
    Png(G.Render(), Out + "/realm_04_shop.png");
    Tap(G, Button::Down); Tap(G, Button::Down); Tap(G, Button::A);   // TORCH
    Check("buying a torch costs its price", G.Count("TORCH") == 1 && G.Gold() == 100 - S.Items[static_cast<size_t>(S.ItemIndex("TORCH"))].Price, G.Describe());
    Dismiss(G); Tap(G, Button::B);   // back to SHOP
    Tap(G, Button::Down); Tap(G, Button::A);   // SELL
    Check("SELL lists the bag", G.TopBox() == "SELL");
    const int GoldBeforeSell = G.Gold();
    Tap(G, Button::A);   // sell the first sellable (a herb)
    Check("selling pays half", G.Gold() == GoldBeforeSell + 5 && G.Count("HERB") == 0, G.Describe());
    Dismiss(G); Tap(G, Button::B);
    Check("leave the shop", G.TopBox() == "NONE", G.TopBox());
    // The elder wanders; find them and ask for the news.
    G.SetNews({"THE JUKEBOX PLAYS AT NOON."});
    int Elder = -1;
    for (size_t i = 0; i < S.Npcs.size(); ++i) if (S.Npcs[i].R == Role::News && S.Maps[static_cast<size_t>(S.Npcs[i].At.Map)].Id == "TOWN1") Elder = static_cast<int>(i);
    bool News = false;
    for (int Try = 0; Try < 5 && !News; ++Try)   // the elder wanders; go to where they stand now
    {
        const auto At = G.NpcPosition(Elder);
        if (StandBeside(G, At.first, At.second)) Tap(G, Button::A);
        News = G.LastMessage().find("JUKEBOX") != std::string::npos;
        Dismiss(G);
        while (G.TopBox() != "NONE") Tap(G, Button::B);
    }
    Check("the elder tells the news of the day", News, G.LastMessage());
    Dismiss(G);
    // The storeroom: a bronze lock at (8,12).
    G.Place("TOWN1", 9, 12, 2);
    Tap(G, Button::A);
    Check("a lock without a key stays locked", G.LastMessage().find("BRONZE") != std::string::npos && G.DoorsOpened() == 0, G.LastMessage());
    Dismiss(G);
    G.Give("BRONZE_KEY");
    Tap(G, Button::Left);
    Check("bumping it with a bronze key opens it, and the key is spent", G.DoorsOpened() == 1 && G.Count("BRONZE_KEY") == 0, G.Describe());
    Dismiss(G);
    int Chests = 0, GoldFound = 0;
    std::vector<std::string> Got;
    for (const ChestDef& C : S.Chests)
    {
        if (S.Maps[static_cast<size_t>(C.At.Map)].Id != "TOWN1") continue;
        ++Chests;
        const int GoldWas = G.Gold();
        const int CountWas = C.Kind == LootKind::Item ? G.Count(C.Item) : 0;
        Check("walk beside the storeroom chest", StandBeside(G, C.At.X, C.At.Y), G.Describe());
        Tap(G, Button::A);
        if (C.Kind == LootKind::Gold) GoldFound += G.Gold() - GoldWas == C.Gold;
        if (C.Kind == LootKind::Item) GoldFound += G.Count(C.Item) == CountWas + 1;
        Dismiss(G);
    }
    Check("each chest held what the Java engines rolled", GoldFound == Chests && G.ChestsOpened() == Chests, G.Describe());
    Tap(G, Button::A);
    Check("an opened chest stays open", G.ChestsOpened() == Chests);
    while (G.TopBox() != "NONE") Tap(G, Button::B);

    // ---- out to the field and the castle: the queen remembers you
    Check("leave town through the gate", WalkTo(G, 12, 19 - 1) && (Tap(G, Button::Down), Settle(G), Tap(G, Button::Down), Settle(G), G.MapId() == "FIELD"), G.Describe());
    Dismiss(G);
    Check("back on the town icon in the field", G.X() == T1->From.X && G.Y() == T1->From.Y && G.MusicCue() == "FIELD", G.Describe());
    const LinkDef* Cs = LinkInto(S, "CASTLE");
    WalkTo(G, Cs->From.X, Cs->From.Y);
    Check("walk to the castle", G.MapId() == "CASTLE", G.Describe());
    Dismiss(G);
    Check("walk up the carpet to the queen", WalkTo(G, 10, 3));
    Face(G, 1);
    G.MembersMut()[2].Hp = 0;
    Tap(G, Button::A);
    Check("the queen's blessing revives the fallen", G.Members()[2].Hp == G.Members()[2].MaxHp && G.LastMessage().find("LEVEL") != std::string::npos, G.LastMessage());
    Dismiss(G);
    Png(G.Render(), Out + "/realm_05_castle.png");
    G.Place("CASTLE", 7, 3, 2);
    Tap(G, Button::Left);
    Check("the treasury wants a silver key", G.LastMessage().find("SILVER") != std::string::npos && G.DoorsOpened() == 1, G.LastMessage());
    Dismiss(G);
    G.Give("BRONZE_KEY");
    const int Bronze = G.Count("BRONZE_KEY");
    Tap(G, Button::Left);
    Check("a bronze key does not open a silver lock", G.DoorsOpened() == 1 && G.Count("BRONZE_KEY") == Bronze && Bronze >= 1);
    Dismiss(G);

    // ---- the cave: dark, three floors, the guardian, the star key
    G.Place("CASTLE", 10, 15, 0);
    Check("leave the castle", WalkTo(G, 10, 17) && (Tap(G, Button::Down), Settle(G), G.MapId() == "FIELD"), G.Describe());
    Dismiss(G);
    const LinkDef* Cv = LinkInto(S, "CAVE1");
    WalkTo(G, Cv->From.X, Cv->From.Y, 2000);
    Check("walk to the cave mouth", G.MapId() == "CAVE1", G.Describe());
    Check("the cave is dark: you see one tile", G.Light() == 1 && G.MusicCue() == "CAVE", G.Describe());
    Dismiss(G);
    Png(G.Render(), Out + "/realm_06_cave_dark.png");
    Tap(G, Button::B); Tap(G, Button::Down); Tap(G, Button::Right); Tap(G, Button::A);   // ITEM
    {   // find the torch in the item list
        for (int k = 0; k < 12 && G.TopBox() == "ITEMS"; ++k)
        {
            Tap(G, Button::A);
            if (G.Light() == 3) break;
            Dismiss(G);
            if (G.TopBox() == "MEMBERS") Tap(G, Button::B);
            Tap(G, Button::Down);
        }
    }
    Check("a torch lights three tiles round", G.Light() == 3 && G.Count("TORCH") == 0, G.Describe());
    Dismiss(G);
    while (G.TopBox() != "NONE") Tap(G, Button::B);
    Png(G.Render(), Out + "/realm_07_cave_torch.png");
    // Down the stairs.
    for (const std::string& Floor : {std::string("CAVE1"), std::string("CAVE2")})
    {
        int DX = -1, DY = -1;
        const MapDef& M = S.Maps[static_cast<size_t>(S.MapIndex(Floor))];
        for (int y = 0; y < M.H; ++y) for (int x = 0; x < M.W; ++x) if (M.At(x, y) == Tile::StairsDown) { DX = x; DY = y; }
        WalkTo(G, DX, DY, 3000);
        Check("take the stairs down from " + Floor, G.MapId() != Floor, G.Describe());
        Dismiss(G);
    }
    Check("the torch lasts down the stairs", G.MapId() == "CAVE3" && G.Light() == 3, G.Describe());
    // The silver key was on B2; fetch it the honest way from the spec and walk there.
    const BossDef& Bo = S.Bosses[0];
    G.SetEncounterCountdown(1000000);
    Check("walk up to the guardian", StandBeside(G, Bo.At.X, Bo.At.Y), G.Describe());
    {
        const int Fc = Bo.At.X > G.X() ? 3 : Bo.At.X < G.X() ? 2 : Bo.At.Y > G.Y() ? 1 : 0;
        Tap(G, Fc == 3 ? Button::Right : Fc == 2 ? Button::Left : Fc == 1 ? Button::Down : Button::Up);
    }
    Check("bumping the guardian starts a speech", G.TopBox() == "MESSAGE" && G.LastMessage().find(S.Monsters[static_cast<size_t>(Bo.Monster)].Name) != std::string::npos, G.LastMessage());
    Png(G.Render(), Out + "/realm_08_guardian.png");
    Dismiss(G);
    Check("then a fight with boss music", G.CurrentMode() == Mode::Battle && G.MusicCue() == "BOSS", G.Describe());
    Tap(G, Button::A);   // intro
    for (int k = 0; k < 4; ++k) Tap(G, Button::Down);   // RUN
    Tap(G, Button::A);
    Check("there is no running from a guardian", G.LastMessage() == "THERE IS NO ESCAPE!", G.LastMessage());
    for (int k = 0; k < 6; ++k) Tap(G, Button::Up);
    Png(G.Render(), Out + "/realm_09_boss_battle.png");
    Check("beat the guardian", AutoFight(G) && G.BossesBeaten() == 1, G.Describe());
    Check("the victory cue played", G.CueChanges() > 3);
    Check("walk onto where it stood", WalkTo(G, Bo.At.X, Bo.At.Y), G.Describe());
    int StarX = -1, StarY = -1;
    for (const ChestDef& C : S.Chests) if (C.Kind == LootKind::Item && S.Items[static_cast<size_t>(C.Item)].Id == "STAR_KEY") { StarX = C.At.X; StarY = C.At.Y; }
    G.Place("CAVE3", Bo.At.X, Bo.At.Y, StarX > Bo.At.X ? 3 : StarX < Bo.At.X ? 2 : StarY > Bo.At.Y ? 0 : 1);
    Tap(G, Button::A);
    Check("the star key is in the guardian's chest", G.Count("STAR_KEY") == 1, G.Describe());
    Dismiss(G);

    // ---- the vault: the legends
    G.Place("CASTLE", 12, 3, 3);
    Tap(G, Button::Right);
    if (G.CurrentMode() == Mode::Battle) { AutoFight(G); Dismiss(G); G.Place("CASTLE", 12, 3, 3); Tap(G, Button::Right); }   // a wandering foe
    Dismiss(G);
    Check("the star key opens the vault", G.Count("STAR_KEY") == 0 && G.DoorsOpened() == 2, G.Describe());
    Dismiss(G);
    Check("walk into the vault", WalkTo(G, 15, 2));
    Face(G, 3);
    Tap(G, Button::A);
    Check("the vault holds the STAR BLADE", G.Count("STAR_BLADE") == 1, G.Describe());
    Dismiss(G);
    Tap(G, Button::B); Tap(G, Button::Right); Tap(G, Button::Down); Tap(G, Button::Down); Tap(G, Button::A);   // EQUIP
    Check("EQUIP asks who", G.TopBox() == "MEMBERS");
    Tap(G, Button::A);
    Check("EQUIP lists the gear", G.TopBox() == "EQUIP", G.TopBox());
    const int Wanted = S.ItemIndex("STAR_BLADE");
    for (int k = 0; k < 6 && G.Members()[0].Weapon != Wanted; ++k)
    {
        Tap(G, Button::A);
        if (G.Members()[0].Weapon == Wanted) break;
        Dismiss(G);
        Tap(G, Button::B); Tap(G, Button::B);
        Tap(G, Button::B); for (int j = 0; j < 3; ++j) Tap(G, Button::Down); Tap(G, Button::A); Tap(G, Button::A);
        for (int j = 0; j <= k; ++j) Tap(G, Button::Down);
    }
    Check("the hero wields the STAR BLADE; the club goes back in the bag", G.Members()[0].Weapon == Wanted && G.Count("CLUB") == 1, G.Describe());
    Dismiss(G);
    while (G.TopBox() != "NONE") Tap(G, Button::B);

    // ---- a mimic: a chest that bites (made from the same spec with one chest changed)
    {
        Realm M;
        std::string T2 = Text;
        const size_t At = T2.find("chest TOWN1");
        const size_t End = T2.find('\n', At);
        std::string Line = T2.substr(At, End - At);
        std::istringstream In(Line);
        std::string K, Map;
        int X = 0, Y = 0;
        In >> K >> Map >> X >> Y;
        T2.replace(At, End - At, "chest TOWN1 " + std::to_string(X) + " " + std::to_string(Y) + " MIMIC GNASHBOX");
        std::string E;
        Check("a spec with a mimic loads", M.Load(T2, E), E);
        Dismiss(M);
        Toughen(M);
        M.Place("TOWN1", X + 1, Y, 2);
        Tap(M, Button::A);
        Check("the chest bites", M.LastMessage().find("BITES") != std::string::npos, M.LastMessage());
        Dismiss(M);   // A finishes the typewriter, A again closes the page
        Check("and the mimic fights", M.CurrentMode() == Mode::Battle && M.Foes().size() == 1 && M.World().Monsters[static_cast<size_t>(M.Foes()[0].Kind)].Id == "GNASHBOX", M.Describe());
        Png(M.Render(), Out + "/realm_10_mimic.png");
        Check("beat it and the chest is done", AutoFight(M) && M.ChestsOpened() == 1, M.Describe());
    }

    // ---- ambushes: walking the field meets the zone's monsters
    {
        Realm F;
        std::string E;
        F.Load(Text, E);
        Dismiss(F);
        Toughen(F);
        std::set<std::string> Seen;
        int Steps = 0;
        const MapDef& M = F.World().Maps[0];
        for (int k = 0; k < 400 && F.Battles() < 6; ++k)
        {
            const int Dir = static_cast<int>(Mix(static_cast<uint64_t>(k)) % 4);
            const Button B = Dir == 0 ? Button::Up : Dir == 1 ? Button::Down : Dir == 2 ? Button::Left : Button::Right;
            const int NX = F.X() + (Dir == 3) - (Dir == 2), NY = F.Y() + (Dir == 1) - (Dir == 0);
            const Tile T = M.At(NX, NY);
            if (!Walkable(T) || T == Tile::Portal || T == Tile::Town || T == Tile::Castle || T == Tile::Cave) continue;
            Tap(F, B); Settle(F);
            ++Steps;
            if (F.CurrentMode() == Mode::Battle)
            {
                for (const Foe& Fo : F.Foes()) Seen.insert(F.World().Monsters[static_cast<size_t>(Fo.Kind)].Id);
                if (F.Battles() == 1) Png(F.Render(), Out + "/realm_11_ambush.png");
                AutoFight(F);
                Dismiss(F);
            }
        }
        Check("walking the field gets you ambushed", F.Battles() >= 3, F.Describe() + " steps=" + std::to_string(Steps));
        bool AllNear = true;
        for (const std::string& Id : Seen)
        {
            bool InTable = false;
            for (const ZoneDef& Z : F.World().Zones) for (const ZoneEntry& En : Z.Entries) InTable |= F.World().Monsters[static_cast<size_t>(En.Monster)].Id == Id;
            AllNear &= InTable;
        }
        Check("every ambusher comes from a zone table", AllNear && !Seen.empty());
        Check("wins pay gold and exp", F.Wins() >= 1 && F.Members()[0].Exp > ExpToNext(29) - 1, F.Describe());
    }

    // ---- a fresh party levels up, learns a spell, and casts it
    {
        Realm L;
        std::string E;
        L.Load(Text, E);
        Dismiss(L);
        L.MembersMut()[0].Atk = 60;
        L.ForceBattle({"BLIGHT_SLIME", "BLIGHT_SLIME", "BLIGHT_SLIME"});
        AutoFight(L);
        L.ForceBattle({"BLIGHT_SLIME", "BLIGHT_SLIME"});
        AutoFight(L);
        Check("two fights take a fresh hero to level 2", L.Members()[0].Lvl >= 2 && L.Members()[0].Exp >= 7, L.Describe());
        // SAGE casts ZAP at a slime: FIGHT for the hero, SPELL ZAP for the sage, DEFEND for the scout.
        L.ForceBattle({"PUFFCAP"});
        Tap(L, Button::A);              // intro
        Tap(L, Button::Down); Tap(L, Button::Down); Tap(L, Button::Down); Tap(L, Button::A);   // hero DEFENDS
        Tap(L, Button::Down); Tap(L, Button::A);   // sage: SPELL
        Check("the sage's spell list", L.TopBox() == "SPELLS", L.TopBox());
        Png(L.Render(), Out + "/realm_12_spells.png");
        const int MpBefore = L.Members()[1].Mp;
        Tap(L, Button::Down); Tap(L, Button::A);   // ZAP (single foe: no target step)
        for (int k = 0; k < 3; ++k) Tap(L, Button::Down);
        Tap(L, Button::A);              // scout DEFENDS
        for (int k = 0; k < 40 && L.TopBox() == "PLAY"; ++k) L.Tick(0.5);
        Check("ZAP costs the sage 3 MP", L.Members()[1].Mp == MpBefore - 3, L.Describe());
        AutoFight(L);
        // A lucky drip is hard: plain hits do 0 or 1.
        L.ForceBattle({"LUCKY_DRIP"});
        Tap(L, Button::A);
        const int DripHp = L.Foes()[0].Hp;
        Tap(L, Button::A); Tap(L, Button::A);   // hero FIGHT
        for (int k = 0; k < 2; ++k) { Tap(L, Button::Down); Tap(L, Button::Down); Tap(L, Button::Down); Tap(L, Button::A); }   // defend, defend
        for (int k = 0; k < 40 && L.TopBox() == "PLAY"; ++k) L.Tick(0.5);
        Check("a lucky drip shrugs off all but a mighty blow", L.Foes().empty() || L.Foes()[0].Fled || DripHp - L.Foes()[0].Hp <= 1 || L.Foes()[0].Hp <= 0, L.Describe());
        AutoFight(L);
    }

    // ---- defeat: the party wakes where the queen blessed it, with half its gold
    {
        const int GoldWas = G.Gold();
        for (Member& P : G.MembersMut()) { P.Hp = 1; P.Def = 0; P.MaxHp = 30; P.Agi = 1; P.Atk = 1; }
        G.ForceBattle({"STONE_KNIGHT", "STONE_KNIGHT", "STONE_KNIGHT"});
        Tap(G, Button::A);
        for (int k = 0; k < 2000 && G.CurrentMode() == Mode::Battle; ++k)
        {
            const std::string U = G.TopBox();
            if (U == "COMMAND") { for (int j = 0; j < 3; ++j) Tap(G, Button::Down); Tap(G, Button::A); }   // DEFEND
            else if (U == "ENDING" || U == "INTRO" || U == "TARGET") Tap(G, Button::A);
            else G.Tick(0.5);
        }
        Check("the party falls and wakes at the castle", G.MapId() == "CASTLE" && G.Members()[0].Hp == 30, G.Describe());
        Check("with half its gold", G.Gold() == GoldWas / 2, G.Describe());
        Check("to the defeat cue, then home music", G.MusicCue() == "CASTLE");
        Dismiss(G);
        Toughen(G);
    }

    // ---- saving: the team keeps its levels, gear and bag, and this realm keeps its open chests
    {
        const std::string Saved = G.Save();
        Realm Again;
        std::string E;
        Again.Load(Text, E);
        Check("a saved party restores", Again.Restore(Saved));
        Check("levels, gear, bag, gold, open chests and locks all come back",
            Again.Members()[0].Lvl == G.Members()[0].Lvl && Again.Members()[0].Weapon == G.Members()[0].Weapon
            && Again.Gold() == G.Gold() && Again.Count("CLUB") == 1 && Again.ChestsOpened() == G.ChestsOpened()
            && Again.DoorsOpened() == G.DoorsOpened() && Again.BossesBeaten() == 1 && Again.MapId() == G.MapId(), Again.Describe());
        Check("the save round-trips exactly", Again.Save() == Saved);
        // Another realm (another seed): the party comes, the chests don't.
        std::string Other = Text;
        Other.replace(Other.find("seed 7"), 6, "seed 8");
        Realm Elsewhere;
        Elsewhere.Load(Other, E);
        Elsewhere.Restore(Saved);
        Check("in another realm the team keeps its levels but the chests are fresh",
            Elsewhere.Members()[0].Lvl == G.Members()[0].Lvl && Elsewhere.ChestsOpened() == 0 && Elsewhere.MapId() == "FIELD", Elsewhere.Describe());
    }

    // ---- home through the portal
    G.Place("FIELD", S.Spawn.X, S.Spawn.Y, 1);
    Tap(G, Button::Up);
    Settle(G);
    Check("stepping on the portal says goodbye", G.TopBox() == "MESSAGE" && !G.WantsExit(), G.Describe());
    Dismiss(G);
    Check("and asks to go home", G.WantsExit());
    const std::vector<std::string> Sfx = G.TakeSfx();
    Check("sound events were raised for the jukebox", Sfx.size() > 20 && G.TakeSfx().empty(), std::to_string(Sfx.size()));
    Check("describe reports the realm for the harness", G.Describe().find("chests=") != std::string::npos);

    // ---- every monster drawing renders and differs
    {
        std::set<uint64_t> Hashes;
        Frame Sheet(256, 128);
        for (size_t i = 0; i < S.Monsters.size(); ++i)
        {
            const MonsterDef& Mo = S.Monsters[i];
            Frame One(64, 64);
            DrawMonster(One, 0, 0, Mo.Shape, Mo.Body, Mo.Accent, 0, false);
            uint64_t H = 1469598103934665603ull;
            for (uint32_t P : One.Px) H = (H ^ P) * 1099511628211ull;
            Hashes.insert(H);
            if (i < 8) DrawMonster(Sheet, static_cast<int>(i % 4) * 64, static_cast<int>(i / 4) * 64, Mo.Shape, Mo.Body, Mo.Accent, 0, false);
        }
        Check("each monster looks different", Hashes.size() == S.Monsters.size(), std::to_string(Hashes.size()));
        Png(Sheet, Out + "/realm_13_bestiary.png", 2);
    }

    std::printf("%d/%d\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
