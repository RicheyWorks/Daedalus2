// SPDX-License-Identifier: MIT
// Direct, engine-free checks of daedalus::stage::Director (DaedalusBattleStageCore.h): each battle-line rule
// produces the documented cues, so a 3D stage can rely on them. realm_core_test.cpp covers a whole fight;
// this pins the individual rules. Build: g++ -std=c++17 -Wall -Wextra -Werror battle_stage_core_test.cpp
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusBattleStageCore.h"

#include <cstdio>
#include <string>
#include <vector>

using daedalus::stage::Cue;
using daedalus::stage::Director;
using daedalus::stage::Kind;
using daedalus::stage::LineFacts;

static int Failures = 0, Checks = 0;
static void Check(bool Ok, const char* What)
{
    ++Checks;
    if (!Ok) { ++Failures; std::printf("FAIL %s\n", What); }
}

static std::string Kinds(const std::vector<Cue>& C)
{
    std::string S;
    for (const Cue& X : C) { if (!S.empty()) S += ","; S += daedalus::stage::Name(X.K); }
    return S;
}

static LineFacts Facts(const std::string& Text, const std::string& Sound)
{
    LineFacts F; F.Text = Text; F.Sound = Sound;
    F.MemberNames = {"ARDEN", "MIRA"};
    F.FoeNames = {"SLIME", "SLIME", "DRAKE"};
    return F;
}

static std::vector<Cue> Stage(const LineFacts& F)
{
    Director D; D.OnLine(F); return D.Take();
}

int main()
{
    {   // Begin: enter + wide camera + one shiny glow per shiny foe slot that exists
        Director D; D.Begin(2, 3, {false, true, true, true});
        const auto C = D.Take();
        Check(Kinds(C) == "ENTER,CAMERA,SHINY,SHINY", "begin: enter, camera, two shinies (extra flag ignored)");
        Check(C[0].Amount == 3 && C[1].Text == "wide", "begin: foe count and wide camera");
        Check(C[2].Target == 1 && C[2].TargetIsFoe && C[3].Target == 2, "begin: shiny targets are foe slots");
        Check(D.Pending() == 0, "take empties the queue");
    }
    {   // a member attacks: step in, swing, camera on that member
        const auto C = Stage(Facts("MIRA ATTACKS!", "SWING"));
        Check(Kinds(C) == "STEP_IN,SWING,CAMERA", "attack: step in, swing, camera");
        Check(C[0].Actor == 1 && !C[0].ActorIsFoe && C[2].Text == "member:1", "attack: speaker is member 1");
        Check(C[1].At == 0.25, "attack: swing after the step");
    }
    {   // two foes share a name: the line's own Foe slot wins
        LineFacts F = Facts("SLIME ATTACKS!", "SWING"); F.Foe = 1;
        const auto C = Stage(F);
        Check(C[0].Actor == 1 && C[0].ActorIsFoe && C[2].Text == "foe:1", "duplicate foe names resolve to the line's slot");
    }
    {   // damage to a foe: flinch + pop, and things that happen TO someone have no actor
        LineFacts F = Facts("ARDEN HITS SLIME", "HURT"); F.Foe = 0; F.FoeHpBefore = 10; F.FoeHpAfter = 4;
        const auto C = Stage(F);
        Check(Kinds(C) == "FLINCH,POP", "hurt: flinch and pop");
        Check(C[0].Amount == 6 && C[0].Target == 0 && C[0].TargetIsFoe && C[0].Actor == -1, "hurt: amount, target, no actor");
    }
    {   // crit: a swing carrying the damage, then flinch and pop at 0.3s
        LineFacts F = Facts("ARDEN LANDS A CRITICAL HIT", "CRIT"); F.Foe = 2; F.FoeHpBefore = 30; F.FoeHpAfter = 12;
        const auto C = Stage(F);
        Check(Kinds(C) == "SWING,FLINCH,POP" && C[0].Text == "CRIT" && C[0].Amount == 18 && C[1].At == 0.3, "crit cues");
    }
    {   // a spell names itself and can heal a member
        LineFacts F = Facts("MIRA CASTS HEAL!", "SPELL"); F.Mem = 0; F.MemHpBefore = 5; F.MemHpAfter = 17;
        const auto C = Stage(F);
        Check(Kinds(C) == "CAST,HEAL" && C[0].Text == "HEAL" && C[1].Amount == 12 && !C[1].TargetIsFoe, "spell heal");
    }
    {   // the defeat sound with "IS DEFEATED" is a foe falling, otherwise the party is defeated
        LineFacts F = Facts("DRAKE IS DEFEATED.", "DEFEAT"); F.Foe = 2;
        Check(Kinds(Stage(F)) == "FALL", "foe defeated is a fall");
        Check(Kinds(Stage(Facts("THE PARTY HAS FALLEN.", "DEFEAT"))) == "DEFEAT", "party defeat");
    }
    {   // victory turns the camera to the party
        const auto C = Stage(Facts("YOU WIN!", "VICTORY"));
        Check(Kinds(C) == "VICTORY,CAMERA" && C[1].Text == "party", "victory");
    }
    {   // fleeing: a foe that is gone runs, else the speaker runs
        LineFacts F = Facts("SLIME RUNS AWAY", "RUN"); F.Foe = 0; F.FoeGone = true;
        const auto C = Stage(F);
        Check(Kinds(C) == "FLEE" && C[0].Target == 0 && C[0].TargetIsFoe, "foe flees");
    }
    {   // poison pops only when it hurt
        LineFacts F = Facts("ARDEN IS POISONED", "POISON"); F.Mem = 0; F.MemHpBefore = 9; F.MemHpAfter = 7;
        Check(Kinds(Stage(F)) == "POISON,POP", "poison with damage");
        LineFacts G = Facts("ARDEN IS POISONED", "POISON"); G.Mem = 0; G.MemHpBefore = 9; G.MemHpAfter = 9;
        Check(Kinds(Stage(G)) == "POISON", "poison without damage");
    }
    {   // items heal members; defend is a guard; sleep, level, call and miss
        LineFacts F = Facts("ARDEN USES HERB", "ITEM"); F.Mem = 0; F.MemHpBefore = 3; F.MemHpAfter = 13;
        Check(Kinds(Stage(F)) == "USE,HEAL", "item heal");
        Check(Kinds(Stage(Facts("MIRA DEFENDS", "BLIP"))) == "GUARD", "defend");
        Check(Kinds(Stage(Facts("SLIME FALLS ASLEEP", "BLIP"))) == "SLEEP", "sleep");
        LineFacts L = Facts("ARDEN REACHES LEVEL 3", "LEVEL"); L.Mem = 0;
        Check(Kinds(Stage(L)) == "LEVEL", "level");
        LineFacts K = Facts("A DRAKE APPEARS", "CALL"); K.Foe = 2;
        Check(Kinds(Stage(K)) == "CALL", "call");
        LineFacts M = Facts("ARDEN MISSES", "MISS"); M.Foe = 1;
        const auto C = Stage(M);
        Check(Kinds(C) == "MISS" && C[0].Target == 1 && C[0].TargetIsFoe && C[0].Actor == -1, "miss targets the foe, no actor");
    }
    {   // a plain line with no change stages nothing
        Check(Stage(Facts("THE WIND HOWLS.", "BLIP")).empty(), "quiet line");
    }
    {   // describe
        Cue C; C.K = Kind::Pop; C.Target = 2; C.TargetIsFoe = true; C.Amount = 7;
        Check(C.Describe() == "POP on foe2 7", "describe");
    }
    std::printf("%d/%d battle stage checks\n", Checks - Failures, Checks);
    return Failures ? 1 : 0;
}
