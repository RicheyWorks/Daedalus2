// SPDX-License-Identifier: MIT

#pragma once

// The battle stage director (hub 28710, Richey 2026-10-13: the old-school realm must look far better than Dragon
// Warrior while keeping its mechanics). The 8-bit core decides the fight; this turns its battle lines into timed,
// named cues a 3D stage can play with Sol's models: who steps in, who swings, who flinches, who falls, where the
// camera looks, when a number pops. The sprite battle ignores it; a 3D stage subscribes. Pure C++17, so the cue
// sequence for any fight is proven headlessly (realm_core_test.cpp) before any model exists.
//
// Cues are relative to the line's playback time; the stage schedules them against its own clock.

#include <string>
#include <vector>

namespace daedalus
{
namespace stage
{

enum class Kind
{
    Enter,      // the stage opens: Foes foes face Members members
    Shiny,      // foe Foe glitters: a glow and sparks (ADR-065 rule 9)
    StepIn,     // actor steps forward to act
    Swing,      // actor attacks Target
    Cast,       // actor casts (Text says what) at Target or everyone (Target -1)
    Use,        // actor uses an item
    Guard,      // actor braces
    Flinch,     // Target takes Amount
    Miss,       // the blow whiffs past Target
    Heal,       // Target gains Amount
    Fall,       // Target goes down
    Flee,       // Target runs
    Call,       // a new foe arrives at slot Target
    Sleep,      // Target sleeps
    Poison,     // Target is stung
    Pop,        // a damage number Amount over Target (foe or member)
    Level,      // member Target levels up
    Victory,
    Defeat,
    Camera      // look at Text: "wide", "foe:<i>", "member:<i>", "party"
};

inline const char* Name(Kind K)
{
    static const char* N[] = {"ENTER", "SHINY", "STEP_IN", "SWING", "CAST", "USE", "GUARD", "FLINCH", "MISS", "HEAL", "FALL", "FLEE", "CALL", "SLEEP", "POISON", "POP", "LEVEL", "VICTORY", "DEFEAT", "CAMERA"};
    return N[static_cast<int>(K)];
}

/** One beat. Actor/Target: a member (IsFoe false) or a foe (IsFoe true) by slot; -1 for nobody / everyone. */
struct Cue
{
    Kind K = Kind::Enter;
    int Actor = -1; bool ActorIsFoe = false;
    int Target = -1; bool TargetIsFoe = false;
    int Amount = 0;
    double At = 0.0, Dur = 0.3;   // seconds after the line starts; how long the beat lasts
    std::string Text;

    std::string Describe() const
    {
        std::string S = Name(K);
        if (Actor >= 0) S += std::string(" by ") + (ActorIsFoe ? "foe" : "member") + std::to_string(Actor);
        if (Target >= 0) S += std::string(" on ") + (TargetIsFoe ? "foe" : "member") + std::to_string(Target);
        if (Amount) S += " " + std::to_string(Amount);
        if (!Text.empty()) S += " '" + Text + "'";
        return S;
    }
};

/** What the director needs to know about one battle line, lifted from the realm's Line + what showed before. */
struct LineFacts
{
    std::string Text, Sound;
    int Foe = -1, FoeHpBefore = 0, FoeHpAfter = 0; bool FoeGone = false;
    int Mem = -1, MemHpBefore = 0, MemHpAfter = 0;
    std::vector<std::string> MemberNames, FoeNames;   // upper case, by slot, to find who spoke
};

class Director
{
public:
    void Begin(int Members, int Foes, const std::vector<bool>& Shiny)
    {
        Out.clear();
        NMembers = Members; NFoes = Foes;
        Cue E; E.K = Kind::Enter; E.Amount = Foes; E.Dur = 0.8; Out.push_back(E);
        Cue C; C.K = Kind::Camera; C.Text = "wide"; C.At = 0.0; Out.push_back(C);
        for (int i = 0; i < Foes && i < static_cast<int>(Shiny.size()); ++i)
            if (Shiny[static_cast<size_t>(i)]) { Cue S; S.K = Kind::Shiny; S.Target = i; S.TargetIsFoe = true; S.At = 0.4; S.Dur = 1.0; Out.push_back(S); }
    }

    /** A line is about to play: stage it. */
    void OnLine(const LineFacts& F)
    {
        const std::string& T = F.Text;
        int Actor = -1; bool ActorFoe = false;
        FindSpeaker(F, Actor, ActorFoe);
        auto Push = [&](Kind K, double At, double Dur, int Target = -1, bool TargetFoe = false, int Amount = 0, const std::string& Text = "") {
            Cue C; C.K = K; C.Actor = Actor; C.ActorIsFoe = ActorFoe; C.Target = Target; C.TargetIsFoe = TargetFoe; C.Amount = Amount; C.At = At; C.Dur = Dur; C.Text = Text;
            // A thing that happens TO someone has no actor: the one it happens to is the target.
            if (K == Kind::Flinch || K == Kind::Pop || K == Kind::Heal || K == Kind::Miss || K == Kind::Poison || K == Kind::Call || K == Kind::Level || K == Kind::Victory || K == Kind::Defeat) C.Actor = -1;
            Out.push_back(C);
        };
        const int FoeDrop = F.Foe >= 0 ? F.FoeHpBefore - F.FoeHpAfter : 0;
        const int MemDrop = F.Mem >= 0 ? F.MemHpBefore - F.MemHpAfter : 0;
        const std::string& S = F.Sound;

        if (S == "VICTORY") { Push(Kind::Victory, 0.0, 1.5); Cue C; C.K = Kind::Camera; C.Text = "party"; Out.push_back(C); return; }
        if (S == "DEFEAT")
        {
            if (Has(T, " IS DEFEATED")) { Push(Kind::Fall, 0.0, 0.9, Actor, ActorFoe); return; }   // a foe's end shares the sound
            Push(Kind::Defeat, 0.0, 2.0);
            return;
        }
        if (S == "LEVEL") { Push(Kind::Level, 0.0, 1.0, F.Mem, false); return; }
        if (S == "CALL") { Push(Kind::Call, 0.0, 0.8, F.Foe, true); return; }
        if (S == "RUN")
        {
            if (F.FoeGone) Push(Kind::Flee, 0.0, 0.6, F.Foe, true);
            else if (Actor >= 0) Push(Kind::Flee, 0.0, 0.6, Actor, ActorFoe);
            return;
        }
        if (S == "SPORES") { Push(Kind::Cast, 0.0, 0.5, -1, false, 0, "SPORES"); return; }
        if (S == "POISON") { Push(Kind::Poison, 0.0, 0.5, F.Mem, false, MemDrop); if (MemDrop > 0) Push(Kind::Pop, 0.2, 0.9, F.Mem, false, MemDrop); return; }
        if (Has(T, " FALLS ASLEEP")) { Push(Kind::Sleep, 0.0, 0.6, Actor, ActorFoe); return; }
        if (S == "FALL") { Push(Kind::Fall, 0.0, 0.9, Actor, ActorFoe); return; }
        if (Actor >= 0 && (Has(T, " ATTACKS!") || Has(T, " STRIKES"))) { Push(Kind::StepIn, 0.0, 0.25); Push(Kind::Swing, 0.25, 0.3); Cue C; C.K = Kind::Camera; C.Text = ActorFoe ? "foe:" + std::to_string(Actor) : "member:" + std::to_string(Actor); Out.push_back(C); return; }
        if (S == "SWING" && Actor >= 0) { Push(Kind::StepIn, 0.0, 0.25); Push(Kind::Swing, 0.25, 0.3); return; }
        if (S == "CRIT") { Push(Kind::Swing, 0.0, 0.3, F.Foe, true, FoeDrop, "CRIT"); if (FoeDrop > 0) { Push(Kind::Flinch, 0.3, 0.4, F.Foe, true, FoeDrop); Push(Kind::Pop, 0.3, 0.9, F.Foe, true, FoeDrop); } return; }
        if (S == "MISS") { Push(Kind::Miss, 0.0, 0.4, F.Foe >= 0 ? F.Foe : F.Mem, F.Foe >= 0); return; }
        if (S == "SPELL" || S == "ZAP")
        {
            if (Has(T, " CASTS ")) { Push(Kind::Cast, 0.0, 0.6, F.Foe >= 0 ? F.Foe : F.Mem, F.Foe >= 0, 0, After(T, " CASTS ")); }
            if (FoeDrop > 0) { Push(Kind::Flinch, 0.5, 0.4, F.Foe, true, FoeDrop); Push(Kind::Pop, 0.5, 0.9, F.Foe, true, FoeDrop); }
            if (MemDrop > 0) { Push(Kind::Flinch, 0.5, 0.4, F.Mem, false, MemDrop); Push(Kind::Pop, 0.5, 0.9, F.Mem, false, MemDrop); }
            if (F.Foe >= 0 && FoeDrop < 0) Push(Kind::Heal, 0.5, 0.6, F.Foe, true, -FoeDrop);
            if (F.Mem >= 0 && MemDrop < 0) Push(Kind::Heal, 0.5, 0.6, F.Mem, false, -MemDrop);
            return;
        }
        if (S == "ITEM") { Push(Kind::Use, 0.0, 0.6, F.Mem, false, MemDrop < 0 ? -MemDrop : 0); if (MemDrop < 0) Push(Kind::Heal, 0.4, 0.6, F.Mem, false, -MemDrop); return; }
        if (Has(T, " DEFENDS")) { Push(Kind::Guard, 0.0, 0.4); return; }
        if (S == "HURT" || FoeDrop > 0 || MemDrop > 0)
        {
            if (FoeDrop > 0) { Push(Kind::Flinch, 0.0, 0.4, F.Foe, true, FoeDrop); Push(Kind::Pop, 0.0, 0.9, F.Foe, true, FoeDrop); }
            if (MemDrop > 0) { Push(Kind::Flinch, 0.0, 0.4, F.Mem, false, MemDrop); Push(Kind::Pop, 0.0, 0.9, F.Mem, false, MemDrop); }
            return;
        }
        if (FoeDrop < 0) Push(Kind::Heal, 0.0, 0.6, F.Foe, true, -FoeDrop);
        if (MemDrop < 0) Push(Kind::Heal, 0.0, 0.6, F.Mem, false, -MemDrop);
    }

    /** Cues staged since the last take, in order. */
    std::vector<Cue> Take() { std::vector<Cue> C; C.swap(Out); return C; }
    size_t Pending() const { return Out.size(); }

private:
    static bool Has(const std::string& T, const std::string& P) { return T.find(P) != std::string::npos; }
    static std::string After(const std::string& T, const std::string& P)
    {
        const size_t I = T.find(P);
        if (I == std::string::npos) return "";
        std::string R = T.substr(I + P.size());
        while (!R.empty() && (R.back() == '!' || R.back() == '.' || R.back() == ' ')) R.pop_back();
        const size_t Sp = R.find(' ');
        return Sp == std::string::npos ? R : R.substr(0, Sp);
    }
    /** The line starts with a name: a member's or a foe's. Foes share a name when two of a kind stand there; the
     *  line's own Foe slot wins then. */
    static void FindSpeaker(const LineFacts& F, int& Actor, bool& IsFoe)
    {
        Actor = -1; IsFoe = false;
        for (size_t i = 0; i < F.MemberNames.size(); ++i)
            if (!F.MemberNames[i].empty() && F.Text.rfind(F.MemberNames[i], 0) == 0) { Actor = static_cast<int>(i); IsFoe = false; return; }
        for (size_t i = 0; i < F.FoeNames.size(); ++i)
            if (!F.FoeNames[i].empty() && F.Text.rfind(F.FoeNames[i], 0) == 0)
            {
                Actor = F.Foe >= 0 && F.FoeNames[static_cast<size_t>(F.Foe)] == F.FoeNames[i] ? F.Foe : static_cast<int>(i);
                IsFoe = true;
                return;
            }
    }

    std::vector<Cue> Out;
    int NMembers = 0, NFoes = 0;
};

} // namespace stage
} // namespace daedalus
