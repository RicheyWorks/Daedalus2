// SPDX-License-Identifier: MIT
// The bestiary per realm (BASE-LAYER row 6): the table matches the session realms, the picker is weighted, bosses
// come alone. g++ -std=c++17 -I ../DaedalusLink/Source/DaedalusLink/Public bestiary_core_test.cpp -o b && ./b
#include "DaedalusBestiaryCore.h"
#include "DaedalusRealmSessionCore.h"
#include <iostream>
#include <map>
#include <set>
using namespace daedalus::bestiary;
static int Ok = 0, Total = 0;
static void Check(const std::string& N, bool C, const std::string& W = "") { ++Total; Ok += C; std::cout << (C ? "PASS " : "FAIL ") << N << (C || W.empty() ? "" : "  " + W) << "\n"; }
int main()
{
    Check("every row names a session realm with a land bestiary", [] { for (const Foe& F : Table()) if (!daedalus::session::Find(F.Realm) || F.Realm == "WORLD-ZERO") return false; return true; }());
    Check("kinds are unique", [] { std::set<std::string> S; for (const Foe& F : Table()) if (!S.insert(F.Kind).second) return false; return true; }());
    Check("each of the four realms has at least eight foes and one boss", [] {
        for (const char* R : {"GALLERY-CITY", "PARCELS", "BRICKS", "LABYRINTH"}) { int B = 0; auto V = ForRealm(R); for (const Foe* F : V) B += F->Boss(); if (V.size() < 8 || B < 1) return false; } return true; }());
    Check("art ids follow Sol's export spelling per realm", Find("SMUDGELING")->ArtId == "Mob_Gallery_Smudgeling" && Find("BRICKBUG")->ArtId == "Mob_Bricks_Brickbug" && Find("CHALK_EATER")->ArtId == "Mob_Lab_ChalkEater" && Find("BURROW_VOLE")->ArtId == "Mob_Parcels_BurrowVole");
    Check("World Zero has no bestiary: the server's foe rules stay", Pick("WORLD-ZERO", 0.5) == nullptr && Pack("WORLD-ZERO", {0.1, 0.2}).empty());
    {
        std::map<std::string, int> N;
        for (int i = 0; i < 10000; ++i) N[Pick("GALLERY-CITY", (i + 0.5) / 10000.0)->Kind]++;
        Check("the picker is weighted: smudgelings common, the boss about one in fifty", N["SMUDGELING"] > N["SENTINEL_BUST"] * 4 && N["GREY_WASH"] >= 150 && N["GREY_WASH"] <= 250, std::to_string(N["SMUDGELING"]) + " " + std::to_string(N["GREY_WASH"]));
    }
    Check("a boss roll makes a pack of one", Pack("BRICKS", {0.0, 0.999, 0.0}).size() == 1 && Pack("BRICKS", {0.0, 0.999, 0.0})[0]->Boss());
    Check("three ordinary rolls make a pack of three", Pack("PARCELS", {0.05, 0.3, 0.5}).size() == 3);
    Check("rolls outside [0,1) are clamped, never out of range", Pick("LABYRINTH", -3.0) && Pick("LABYRINTH", 7.0));
    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
